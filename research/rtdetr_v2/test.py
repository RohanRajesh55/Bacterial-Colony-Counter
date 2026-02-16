"""
RT-DETR Evaluation Script for Colony Detection.

Evaluates a fine-tuned RT-DETR model on the AGAR validation/test set,
computing detection metrics (mAP) and count accuracy.

IMPORTANT: Models trained on AGAR are for RESEARCH USE ONLY
due to the CC BY-NC 2.0 license.

Usage:
    python test.py --checkpoint rtdetr/checkpoints/best_model
    python test.py --checkpoint rtdetr/checkpoints/best_model --visualize
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from torchmetrics.detection.mean_ap import MeanAveragePrecision
from tqdm import tqdm
from transformers import RTDetrForObjectDetection, RTDetrImageProcessor
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rtdetr_v2.dataset import AGARDataset, get_val_transform
from shared.constants import CLASSES

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def detect_device() -> str:
    """Detect the best available device."""
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_model(checkpoint_path: str, device: str) -> tuple:
    """Load fine-tuned RT-DETR model.

    Args:
        checkpoint_path: Path to checkpoint directory or .pt file
        device: Target device

    Returns:
        Tuple of (model, processor)
    """
    checkpoint_path = Path(checkpoint_path)

    # Check if it's a HuggingFace directory or a .pt file
    if checkpoint_path.is_dir():
        # HuggingFace format
        logger.info(f"Loading model from HuggingFace directory: {checkpoint_path}")
        model = RTDetrForObjectDetection.from_pretrained(checkpoint_path)
        processor = RTDetrImageProcessor.from_pretrained("PekingU/rtdetr_r101vd")
    elif checkpoint_path.suffix == ".pt":
        # PyTorch checkpoint
        logger.info(f"Loading model from checkpoint: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        config = checkpoint.get("config", {})

        model = RTDetrForObjectDetection.from_pretrained(
            config.get("model_name", "PekingU/rtdetr_r101vd"),
            num_labels=config.get("num_classes", 7),
            ignore_mismatched_sizes=True,
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        processor = RTDetrImageProcessor.from_pretrained(
            config.get("model_name", "PekingU/rtdetr_r101vd")
        )
    else:
        raise ValueError(f"Unknown checkpoint format: {checkpoint_path}")

    model = model.to(device)
    model.eval()

    logger.info(f"Model loaded on {device}")

    return model, processor


@torch.no_grad()
def run_inference(
    model: torch.nn.Module,
    processor,
    image: Image.Image,
    device: str,
    confidence_threshold: float = 0.5,
) -> dict:
    """Run inference on a single image.

    Args:
        model: RT-DETR model
        processor: Image processor
        image: PIL Image
        device: Target device
        confidence_threshold: Detection confidence threshold

    Returns:
        Dictionary with boxes, scores, labels
    """
    # Preprocess
    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Inference
    outputs = model(**inputs)

    # Post-process
    target_sizes = torch.tensor([[image.height, image.width]], device=device)
    results = processor.post_process_object_detection(
        outputs, target_sizes=target_sizes, threshold=confidence_threshold
    )[0]

    return {
        "boxes": results["boxes"].cpu(),
        "scores": results["scores"].cpu(),
        "labels": results["labels"].cpu(),
    }


def compute_metrics(predictions: list, targets: list) -> dict:
    """Compute detection metrics using torchmetrics.

    Args:
        predictions: List of prediction dicts with boxes, scores, labels
        targets: List of target dicts with boxes, labels

    Returns:
        Dictionary with mAP metrics
    """
    # Format for torchmetrics
    preds = []
    targs = []

    for pred, targ in zip(predictions, targets):
        preds.append(
            {
                "boxes": pred["boxes"],
                "scores": pred["scores"],
                "labels": pred["labels"],
            }
        )
        targs.append(
            {
                "boxes": targ["boxes"],
                "labels": targ["labels"],
            }
        )

    # Compute mAP
    metric = MeanAveragePrecision(iou_thresholds=[0.5, 0.75], class_metrics=True)
    metric.update(preds, targs)
    results = metric.compute()

    return {
        "mAP@0.5": results["map_50"].item(),
        "mAP@0.5:0.95": results["map"].item(),
        "mAP@0.75": results["map_75"].item(),
        "mAR@100": results["mar_100"].item(),
    }


def compute_count_metrics(pred_counts: list, true_counts: list) -> dict:
    """Compute colony count accuracy metrics.

    Args:
        pred_counts: List of predicted colony counts
        true_counts: List of ground truth counts

    Returns:
        Dictionary with count metrics
    """
    pred_counts = np.array(pred_counts)
    true_counts = np.array(true_counts)

    # Absolute error
    errors = np.abs(pred_counts - true_counts)

    # Metrics
    exact_match = np.mean(pred_counts == true_counts)

    # Within 5% (with minimum tolerance of 1)
    tolerance = np.maximum(true_counts * 0.05, 1)
    within_5pct = np.mean(errors <= tolerance)

    # Within 10%
    tolerance_10 = np.maximum(true_counts * 0.10, 1)
    within_10pct = np.mean(errors <= tolerance_10)

    mae = np.mean(errors)
    rmse = np.sqrt(np.mean(errors**2))

    return {
        "count_exact_match": exact_match,
        "count_within_5pct": within_5pct,
        "count_within_10pct": within_10pct,
        "count_mae": mae,
        "count_rmse": rmse,
        "total_predictions": int(np.sum(pred_counts)),
        "total_ground_truth": int(np.sum(true_counts)),
    }


def compute_per_class_metrics(
    predictions: list, targets: list, class_names: list
) -> dict:
    """Compute per-class detection metrics.

    Args:
        predictions: List of prediction dicts
        targets: List of target dicts
        class_names: List of class names

    Returns:
        Dictionary with per-class AP
    """
    # Group predictions and targets by class
    class_preds = defaultdict(list)
    class_targs = defaultdict(list)

    for pred, targ in zip(predictions, targets):
        pred_labels = pred["labels"].numpy()
        targ_labels = targ["labels"].numpy()

        for cls_idx in range(len(class_names)):
            # Predictions for this class
            cls_mask = pred_labels == cls_idx
            class_preds[cls_idx].append(
                {
                    "boxes": pred["boxes"][cls_mask],
                    "scores": pred["scores"][cls_mask],
                    "labels": pred["labels"][cls_mask],
                }
            )

            # Targets for this class
            cls_mask_targ = targ_labels == cls_idx
            class_targs[cls_idx].append(
                {
                    "boxes": targ["boxes"][cls_mask_targ],
                    "labels": targ["labels"][cls_mask_targ],
                }
            )

    # Compute AP per class
    per_class_ap = {}
    for cls_idx, cls_name in enumerate(class_names):
        if any(len(t["boxes"]) > 0 for t in class_targs[cls_idx]):
            metric = MeanAveragePrecision(iou_thresholds=[0.5])
            metric.update(class_preds[cls_idx], class_targs[cls_idx])
            results = metric.compute()
            per_class_ap[cls_name] = results["map_50"].item()
        else:
            per_class_ap[cls_name] = float("nan")

    return per_class_ap


def visualize_predictions(
    image: Image.Image,
    predictions: dict,
    targets: dict | None = None,
    class_names: list = CLASSES,
    output_path: str | None = None,
) -> Image.Image:
    """Draw predictions and optionally ground truth on image.

    Args:
        image: Original PIL Image
        predictions: Dict with boxes, scores, labels
        targets: Optional dict with ground truth boxes, labels
        class_names: List of class names
        output_path: Optional path to save visualization

    Returns:
        Annotated PIL Image
    """
    # Copy image
    vis = image.copy()
    draw = ImageDraw.Draw(vis)

    # Try to load a font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Colors for predictions (green) and ground truth (blue)
    pred_color = (0, 255, 0)
    gt_color = (0, 100, 255)

    # Draw ground truth if provided
    if targets is not None:
        for box, label in zip(targets["boxes"], targets["labels"]):
            x1, y1, x2, y2 = box.tolist()
            draw.rectangle([x1, y1, x2, y2], outline=gt_color, width=2)
            label_text = f"GT: {class_names[label]}"
            draw.text((x1, max(0, y1 - 15)), label_text, fill=gt_color, font=font)

    # Draw predictions
    for box, score, label in zip(
        predictions["boxes"], predictions["scores"], predictions["labels"]
    ):
        x1, y1, x2, y2 = box.tolist()
        draw.rectangle([x1, y1, x2, y2], outline=pred_color, width=2)
        label_text = f"{class_names[label]}: {score:.2f}"
        draw.text((x1, max(0, y1 - 15)), label_text, fill=pred_color, font=font)

    # Save if path provided
    if output_path:
        vis.save(output_path)
        logger.info(f"Saved visualization to {output_path}")

    return vis


def evaluate(args: argparse.Namespace) -> dict:
    """Main evaluation function.

    Args:
        args: Command line arguments

    Returns:
        Dictionary with all metrics
    """
    device = detect_device()

    # Load model
    model, processor = load_model(args.checkpoint, device)

    # Load config
    config_path = Path(args.config)
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Create dataset
    image_size = config.get("augmentation", {}).get("image_size", 640)
    dataset = AGARDataset(
        list_file=args.val_list or config["val_list"],
        images_dir=config["images_dir"],
        annotations_dir=config["annotations_dir"],
        processor=processor,
        transform=get_val_transform(image_size),
        image_size=image_size,
    )

    logger.info(f"Evaluating on {len(dataset)} images")

    # Run evaluation
    all_predictions = []
    all_targets = []
    pred_counts = []
    true_counts = []

    # Visualization setup
    vis_dir = None
    if args.visualize:
        vis_dir = Path(args.output_dir) / "visualizations"
        vis_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving visualizations to {vis_dir}")

    for idx in tqdm(range(len(dataset)), desc="Evaluating"):
        # Load raw image for inference (without dataset transforms)
        img_id = dataset.image_ids[idx]
        img_path = dataset.images_dir / f"{img_id}.jpg"
        image = Image.open(img_path).convert("RGB")

        # Load ground truth
        annotation = dataset._load_annotation(img_id)
        coco_ann = dataset._convert_to_coco_format(annotation, image.width, image.height)

        # Convert GT boxes to [x1, y1, x2, y2] format for metrics
        gt_boxes = []
        for box in coco_ann["boxes"]:
            x, y, w, h = box
            gt_boxes.append([x, y, x + w, y + h])

        target = {
            "boxes": torch.tensor(gt_boxes, dtype=torch.float32),
            "labels": torch.tensor(coco_ann["labels"], dtype=torch.int64),
        }

        # Run inference
        predictions = run_inference(
            model, processor, image, device, args.confidence_threshold
        )

        all_predictions.append(predictions)
        all_targets.append(target)

        # Count metrics
        pred_counts.append(len(predictions["boxes"]))
        true_counts.append(len(target["boxes"]))

        # Visualize if requested
        if vis_dir and idx < args.num_visualizations:
            vis_path = vis_dir / f"{img_id}_vis.jpg"
            visualize_predictions(
                image,
                predictions,
                target,
                CLASSES,
                str(vis_path),
            )

    # Compute metrics
    logger.info("Computing metrics...")

    detection_metrics = compute_metrics(all_predictions, all_targets)
    count_metrics = compute_count_metrics(pred_counts, true_counts)
    per_class_ap = compute_per_class_metrics(all_predictions, all_targets, CLASSES)

    # Combine all metrics
    all_metrics = {
        **detection_metrics,
        **count_metrics,
        "per_class_ap": per_class_ap,
    }

    # Print results
    logger.info("=" * 60)
    logger.info("EVALUATION RESULTS")
    logger.info("=" * 60)
    logger.info("\nDetection Metrics:")
    logger.info(f"  mAP@0.5:       {detection_metrics['mAP@0.5']:.4f}")
    logger.info(f"  mAP@0.5:0.95:  {detection_metrics['mAP@0.5:0.95']:.4f}")
    logger.info(f"  mAP@0.75:      {detection_metrics['mAP@0.75']:.4f}")
    logger.info(f"  mAR@100:       {detection_metrics['mAR@100']:.4f}")

    logger.info("\nCount Metrics:")
    logger.info(f"  Exact Match:   {count_metrics['count_exact_match']:.2%}")
    logger.info(f"  Within 5%:     {count_metrics['count_within_5pct']:.2%}")
    logger.info(f"  Within 10%:    {count_metrics['count_within_10pct']:.2%}")
    logger.info(f"  MAE:           {count_metrics['count_mae']:.2f}")
    logger.info(f"  RMSE:          {count_metrics['count_rmse']:.2f}")

    logger.info("\nPer-Class AP@0.5:")
    for cls_name, ap in per_class_ap.items():
        if not np.isnan(ap):
            logger.info(f"  {cls_name:15s}: {ap:.4f}")
        else:
            logger.info(f"  {cls_name:15s}: N/A (no samples)")

    logger.info("=" * 60)

    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results_path = output_dir / "evaluation_results.json"
    with open(results_path, "w") as f:
        # Convert numpy types for JSON serialization
        serializable_metrics = {
            k: (float(v) if isinstance(v, (np.floating, float)) else v)
            for k, v in all_metrics.items()
            if k != "per_class_ap"
        }
        serializable_metrics["per_class_ap"] = {
            k: (float(v) if not np.isnan(v) else None)
            for k, v in per_class_ap.items()
        }
        json.dump(serializable_metrics, f, indent=2)

    logger.info(f"\nResults saved to {results_path}")

    return all_metrics


def main():
    """Entry point for evaluation script."""
    parser = argparse.ArgumentParser(
        description="Evaluate fine-tuned RT-DETR on AGAR dataset"
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to model checkpoint (directory or .pt file)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="rtdetr_v2/config.yaml",
        help="Path to configuration YAML file",
    )
    parser.add_argument(
        "--val_list",
        type=str,
        default=None,
        help="Override validation list file from config",
    )
    parser.add_argument(
        "--confidence_threshold",
        type=float,
        default=0.5,
        help="Detection confidence threshold",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="rtdetr_v2/results",
        help="Directory to save results",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate visualizations of predictions",
    )
    parser.add_argument(
        "--num_visualizations",
        type=int,
        default=20,
        help="Number of images to visualize",
    )

    args = parser.parse_args()
    evaluate(args)


if __name__ == "__main__":
    main()
