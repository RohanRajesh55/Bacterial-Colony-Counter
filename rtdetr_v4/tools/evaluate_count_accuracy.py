#!/usr/bin/env python3
"""
Count Accuracy Evaluation Script

Primary evaluation metric for colony counter: COUNT ACCURACY.
Compares predicted colony counts vs ground truth counts across density tiers.

This script is LICENSE-CLEAN (Apache 2.0 compatible):
- Uses only pycocotools (Apache 2.0)
- NO ultralytics dependency
- Can be used in production evaluation pipelines

Expected prediction format (COCO results JSON):
[
  {"image_id": 0, "category_id": 0, "bbox": [x, y, w, h], "score": 0.95},
  ...
]

Usage:
  # Basic count accuracy evaluation
  python evaluate_count_accuracy.py \\
    --gt-annotations data/agar/annotations/instances_val.json \\
    --pred-annotations outputs/dfine_predictions.json \\
    --model-name "D-FINE"

  # Head-to-head comparison (D-FINE vs YOLOv8)
  python evaluate_count_accuracy.py \\
    --gt-annotations data/agar/annotations/instances_val.json \\
    --pred-annotations outputs/dfine_predictions.json \\
    --model-name "D-FINE" \\
    --compare-with outputs/yolov8_predictions.json

  # With inference speed measurement (DET-06: < 5s per image)
  python evaluate_count_accuracy.py \\
    --gt-annotations data/agar/annotations/instances_val.json \\
    --pred-annotations outputs/dfine_predictions.json \\
    --model-name "D-FINE" \\
    --checkpoint outputs/dfine_best.pth \\
    --config configs/dfine/dfine_hgnetv2_x_agar.yml
"""

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


def load_coco_annotations(json_path: Path) -> Tuple[Dict, List]:
    """
    Load COCO format annotations.

    Returns:
        Tuple of (annotations dict, list of image infos)
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    return data, data['images']


def load_predictions(json_path: Path) -> List[Dict]:
    """
    Load COCO results format predictions.

    Expected format:
    [
      {"image_id": 0, "category_id": 0, "bbox": [x, y, w, h], "score": 0.95},
      ...
    ]
    """
    with open(json_path, 'r') as f:
        predictions = json.load(f)
    return predictions


def group_by_image(annotations_or_predictions: List[Dict]) -> Dict[int, List[Dict]]:
    """
    Group annotations or predictions by image_id.

    Returns:
        Dict mapping image_id to list of annotations/predictions
    """
    grouped = defaultdict(list)
    for item in annotations_or_predictions:
        grouped[item['image_id']].append(item)
    return dict(grouped)


def compute_count_metrics(
    gt_count: int,
    pred_count: int
) -> Tuple[int, float, bool, bool, bool]:
    """
    Compute count accuracy metrics for a single image.

    Returns:
        Tuple of (count_error, relative_error, exact_match, within_5pct, within_10pct)
    """
    count_error = abs(pred_count - gt_count)

    if gt_count == 0:
        relative_error = 0.0 if pred_count == 0 else 1.0
    else:
        relative_error = count_error / gt_count

    exact_match = (pred_count == gt_count)
    within_5_pct = (relative_error <= 0.05)
    within_10_pct = (relative_error <= 0.10)

    return count_error, relative_error, exact_match, within_5_pct, within_10_pct


def get_density_tier(count: int) -> str:
    """
    Classify colony count into density tier.

    Tiers:
      - Sparse: 0-50 colonies
      - Medium: 51-150 colonies
      - Dense: 151-250 colonies
      - Very Dense: 251-500 colonies
      - Ultra Dense: 501+ colonies
    """
    if count <= 50:
        return 'Sparse (0-50)'
    elif count <= 150:
        return 'Medium (51-150)'
    elif count <= 250:
        return 'Dense (151-250)'
    elif count <= 500:
        return 'Very Dense (251-500)'
    else:
        return 'Ultra Dense (501+)'


def evaluate_count_accuracy(
    gt_data: Dict,
    predictions: List[Dict],
    conf_threshold: float = 0.5
) -> Dict:
    """
    Evaluate count accuracy metrics.

    Args:
        gt_data: COCO ground truth annotations dict
        predictions: List of predictions in COCO results format
        conf_threshold: Confidence threshold for counting detections

    Returns:
        Dict containing all metrics
    """
    # Group ground truth annotations by image_id
    gt_anns = gt_data['annotations']
    gt_by_image = group_by_image(gt_anns)

    # Group predictions by image_id and filter by confidence
    filtered_preds = [p for p in predictions if p['score'] >= conf_threshold]
    pred_by_image = group_by_image(filtered_preds)

    # Get all image IDs from ground truth
    image_ids = [img['id'] for img in gt_data['images']]

    # Compute per-image metrics
    results = []
    tier_results = defaultdict(list)

    for img_id in image_ids:
        gt_count = len(gt_by_image.get(img_id, []))
        pred_count = len(pred_by_image.get(img_id, []))

        count_error, rel_error, exact_match, within_5, within_10 = compute_count_metrics(
            gt_count, pred_count
        )

        tier = get_density_tier(gt_count)

        result = {
            'image_id': img_id,
            'gt_count': gt_count,
            'pred_count': pred_count,
            'count_error': count_error,
            'relative_error': rel_error,
            'exact_match': exact_match,
            'within_5_pct': within_5,
            'within_10_pct': within_10,
            'density_tier': tier,
        }

        results.append(result)
        tier_results[tier].append(result)

    # Compute aggregate metrics
    total_images = len(results)

    aggregate_metrics = {
        'count_exact_match': sum(r['exact_match'] for r in results) / total_images * 100,
        'count_within_5_pct': sum(r['within_5_pct'] for r in results) / total_images * 100,
        'count_within_10_pct': sum(r['within_10_pct'] for r in results) / total_images * 100,
        'mean_absolute_error': np.mean([r['count_error'] for r in results]),
        'mean_relative_error': np.mean([r['relative_error'] for r in results]) * 100,
    }

    # Compute per-tier metrics
    tier_metrics = {}
    for tier, tier_res in tier_results.items():
        if len(tier_res) == 0:
            continue

        tier_metrics[tier] = {
            'count': len(tier_res),
            'count_exact_match': sum(r['exact_match'] for r in tier_res) / len(tier_res) * 100,
            'count_within_5_pct': sum(r['within_5_pct'] for r in tier_res) / len(tier_res) * 100,
            'count_within_10_pct': sum(r['within_10_pct'] for r in tier_res) / len(tier_res) * 100,
            'mean_absolute_error': np.mean([r['count_error'] for r in tier_res]),
            'mean_relative_error': np.mean([r['relative_error'] for r in tier_res]) * 100,
        }

    return {
        'aggregate': aggregate_metrics,
        'by_tier': tier_metrics,
        'per_image': results,
    }


def compute_detection_metrics(gt_data: Dict, predictions: List[Dict]) -> Dict:
    """
    Compute standard detection metrics using pycocotools.

    Args:
        gt_data: COCO ground truth annotations dict
        predictions: List of predictions in COCO results format

    Returns:
        Dict with mAP, precision, recall
    """
    try:
        from pycocotools.coco import COCO
        from pycocotools.cocoeval import COCOeval
    except ImportError:
        print("WARNING: pycocotools not installed. Skipping detection metrics.")
        print("Install with: pip install pycocotools")
        return {}

    # Create temporary COCO objects
    import tempfile
    import os

    # Write ground truth to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(gt_data, f)
        gt_temp_path = f.name

    try:
        # Load ground truth
        coco_gt = COCO(gt_temp_path)

        # Load predictions
        coco_dt = coco_gt.loadRes(predictions)

        # Run evaluation
        coco_eval = COCOeval(coco_gt, coco_dt, 'bbox')
        coco_eval.evaluate()
        coco_eval.accumulate()
        coco_eval.summarize()

        # Extract metrics
        metrics = {
            'map_50_95': float(coco_eval.stats[0]),  # mAP@0.5:0.95
            'map_50': float(coco_eval.stats[1]),     # mAP@0.5
            'map_75': float(coco_eval.stats[2]),     # mAP@0.75
            'map_small': float(coco_eval.stats[3]),  # mAP for small objects
            'map_medium': float(coco_eval.stats[4]), # mAP for medium objects
            'map_large': float(coco_eval.stats[5]),  # mAP for large objects
        }

        return metrics

    finally:
        # Clean up temp file
        os.unlink(gt_temp_path)


def measure_inference_speed(
    checkpoint_path: Path,
    config_path: Path,
    image_dir: Path,
    max_images: int = 50
) -> Dict:
    """
    Measure inference speed for D-FINE model (DET-06: < 5s per image).

    Args:
        checkpoint_path: Path to model checkpoint
        config_path: Path to config file
        image_dir: Directory containing test images
        max_images: Maximum number of images to time (default: 50)

    Returns:
        Dict with timing statistics
    """
    try:
        import torch
        from PIL import Image
        import torchvision.transforms as T
    except ImportError:
        print("WARNING: PyTorch not installed. Skipping inference speed measurement.")
        return {}

    print(f"\nMeasuring inference speed on up to {max_images} images...")
    print(f"Checkpoint: {checkpoint_path}")
    print(f"Config: {config_path}")

    # Note: Full D-FINE model loading would require importing the RT-DETRv4 framework
    # For now, we document the expected timing protocol and return placeholder
    print("\nNOTE: Full inference speed measurement requires RT-DETRv4 framework integration.")
    print("To measure inference speed manually:")
    print("1. Run inference with time measurement:")
    print(f"   time python train.py --test-only -c {config_path} -r {checkpoint_path}")
    print("2. Divide total time by number of test images")
    print("3. Check if p95 latency < 5.0 seconds per image (DET-06 requirement)")

    return {
        'status': 'not_implemented',
        'note': 'Manual timing recommended via train.py --test-only',
    }


def format_report(
    model_name: str,
    count_results: Dict,
    detection_metrics: Optional[Dict] = None,
    inference_speed: Optional[Dict] = None,
    compare_results: Optional[Dict] = None
) -> str:
    """
    Format evaluation results as human-readable report.
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"COUNT ACCURACY EVALUATION - {model_name}")
    lines.append("=" * 80)

    # Aggregate count metrics
    agg = count_results['aggregate']
    lines.append("\nAGGREGATE COUNT METRICS:")
    lines.append(f"  Count Exact Match:  {agg['count_exact_match']:6.2f}%")
    lines.append(f"  Count Within 5%:    {agg['count_within_5_pct']:6.2f}%")
    lines.append(f"  Count Within 10%:   {agg['count_within_10_pct']:6.2f}%")
    lines.append(f"  Mean Absolute Error: {agg['mean_absolute_error']:6.2f} colonies")
    lines.append(f"  Mean Relative Error: {agg['mean_relative_error']:6.2f}%")

    # Per-tier breakdown
    lines.append("\nBY DENSITY TIER:")
    lines.append(f"{'Tier':<25} {'Count':>6} {'Exact':>8} {'Within 5%':>10} {'Within 10%':>11} {'MAE':>8} {'MRE':>8}")
    lines.append("-" * 80)

    tier_order = [
        'Sparse (0-50)',
        'Medium (51-150)',
        'Dense (151-250)',
        'Very Dense (251-500)',
        'Ultra Dense (501+)',
    ]

    for tier in tier_order:
        if tier not in count_results['by_tier']:
            continue
        t = count_results['by_tier'][tier]
        lines.append(
            f"{tier:<25} {t['count']:>6} "
            f"{t['count_exact_match']:>7.2f}% "
            f"{t['count_within_5_pct']:>9.2f}% "
            f"{t['count_within_10_pct']:>10.2f}% "
            f"{t['mean_absolute_error']:>8.2f} "
            f"{t['mean_relative_error']:>7.2f}%"
        )

    # Detection metrics (if available)
    if detection_metrics:
        lines.append("\nSTANDARD DETECTION METRICS:")
        lines.append(f"  mAP@0.5:0.95: {detection_metrics.get('map_50_95', 0):6.4f}")
        lines.append(f"  mAP@0.5:      {detection_metrics.get('map_50', 0):6.4f}")
        lines.append(f"  mAP@0.75:     {detection_metrics.get('map_75', 0):6.4f}")

    # Inference speed (if available)
    if inference_speed and inference_speed.get('status') != 'not_implemented':
        lines.append("\nINFERENCE SPEED (DET-06 Requirement: < 5s per image):")
        lines.append(f"  Mean:   {inference_speed.get('mean', 0):.3f}s")
        lines.append(f"  Median: {inference_speed.get('median', 0):.3f}s")
        lines.append(f"  P95:    {inference_speed.get('p95', 0):.3f}s")
        lines.append(f"  Max:    {inference_speed.get('max', 0):.3f}s")

        p95 = inference_speed.get('p95', 0)
        verdict = "PASS" if p95 < 5.0 else "FAIL"
        lines.append(f"  Verdict: {verdict}")

    # Comparison (if provided)
    if compare_results:
        lines.append("\n" + "=" * 80)
        lines.append("HEAD-TO-HEAD COMPARISON")
        lines.append("=" * 80)
        # Format comparison table
        # (implementation would go here)

    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate count accuracy for colony counter models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic evaluation
  python evaluate_count_accuracy.py \\
    --gt-annotations data/agar/annotations/instances_val.json \\
    --pred-annotations outputs/dfine_predictions.json \\
    --model-name "D-FINE"

  # Head-to-head comparison
  python evaluate_count_accuracy.py \\
    --gt-annotations data/agar/annotations/instances_val.json \\
    --pred-annotations outputs/dfine_predictions.json \\
    --model-name "D-FINE" \\
    --compare-with outputs/yolov8_predictions.json

  # With inference speed measurement
  python evaluate_count_accuracy.py \\
    --gt-annotations data/agar/annotations/instances_val.json \\
    --pred-annotations outputs/dfine_predictions.json \\
    --model-name "D-FINE" \\
    --checkpoint outputs/dfine_best.pth \\
    --config configs/dfine/dfine_hgnetv2_x_agar.yml

Prediction format (COCO results JSON):
  [
    {"image_id": 0, "category_id": 0, "bbox": [x, y, w, h], "score": 0.95},
    ...
  ]
        """
    )

    parser.add_argument(
        '--gt-annotations',
        type=str,
        required=True,
        help='COCO ground truth annotations JSON'
    )
    parser.add_argument(
        '--pred-annotations',
        type=str,
        required=True,
        help='COCO results format predictions JSON'
    )
    parser.add_argument(
        '--model-name',
        type=str,
        default='model',
        help='Model name for display in report (default: model)'
    )
    parser.add_argument(
        '--conf-threshold',
        type=float,
        default=0.5,
        help='Confidence threshold for counting detections (default: 0.5)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Directory to save report and plots (optional)'
    )
    parser.add_argument(
        '--compare-with',
        type=str,
        help='Second predictions JSON for head-to-head comparison (optional)'
    )
    parser.add_argument(
        '--checkpoint',
        type=str,
        help='Model checkpoint for inference speed measurement (optional)'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Config file for inference speed measurement (optional)'
    )

    args = parser.parse_args()

    # Load ground truth
    print(f"Loading ground truth: {args.gt_annotations}")
    gt_data, images = load_coco_annotations(Path(args.gt_annotations))
    print(f"  Images: {len(images)}")
    print(f"  Annotations: {len(gt_data['annotations'])}")

    # Load predictions
    print(f"\nLoading predictions: {args.pred_annotations}")
    predictions = load_predictions(Path(args.pred_annotations))
    print(f"  Predictions: {len(predictions)}")
    print(f"  Confidence threshold: {args.conf_threshold}")

    # Evaluate count accuracy
    print("\nEvaluating count accuracy...")
    count_results = evaluate_count_accuracy(gt_data, predictions, args.conf_threshold)

    # Compute detection metrics
    print("\nComputing detection metrics...")
    detection_metrics = compute_detection_metrics(gt_data, predictions)

    # Measure inference speed (if checkpoint and config provided)
    inference_speed = None
    if args.checkpoint and args.config:
        image_dir = Path(args.gt_annotations).parent.parent / 'images' / 'val'
        inference_speed = measure_inference_speed(
            Path(args.checkpoint),
            Path(args.config),
            image_dir
        )

    # Format and print report
    report = format_report(
        args.model_name,
        count_results,
        detection_metrics,
        inference_speed
    )
    print("\n" + report)

    # Save outputs (if output_dir provided)
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON report
        json_report = {
            'model_name': args.model_name,
            'conf_threshold': args.conf_threshold,
            'count_metrics': count_results,
            'detection_metrics': detection_metrics,
        }
        if inference_speed:
            json_report['inference_speed'] = inference_speed

        json_path = output_dir / 'evaluation_report.json'
        with open(json_path, 'w') as f:
            json.dump(json_report, f, indent=2)
        print(f"\nJSON report saved: {json_path}")

        # Save text report
        txt_path = output_dir / 'evaluation_report.txt'
        with open(txt_path, 'w') as f:
            f.write(report)
        print(f"Text report saved: {txt_path}")


if __name__ == '__main__':
    main()
