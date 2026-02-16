"""
Custom PyTorch Dataset for AGAR colony detection.

Loads images and annotations from the AGAR dataset format and prepares
them for RT-DETR training via HuggingFace Transformers.

IMPORTANT: This dataset is for RESEARCH USE ONLY due to CC BY-NC 2.0 license.
"""

import json
import logging
from pathlib import Path
from typing import Any

import albumentations as A
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset

# Add parent directory to path for shared imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.constants import CLASS_MAP, CLASSES

logger = logging.getLogger(__name__)


class AGARDataset(Dataset):
    """PyTorch Dataset for AGAR colony detection data.

    Loads petri dish images and their colony annotations, converting them
    to the COCO format expected by RT-DETR.

    Attributes:
        image_ids: List of image IDs to include in this dataset split
        images_dir: Path to directory containing image files
        annotations_dir: Path to directory containing JSON annotation files
        transform: Albumentations transform pipeline
        processor: HuggingFace image processor for RT-DETR
    """

    def __init__(
        self,
        list_file: str | Path,
        images_dir: str | Path,
        annotations_dir: str | Path,
        processor: Any,
        transform: A.Compose | None = None,
        image_size: int = 640,
    ) -> None:
        """Initialize the AGAR dataset.

        Args:
            list_file: Path to text file with image IDs (one per line)
            images_dir: Directory containing {id}.jpg image files
            annotations_dir: Directory containing {id}.json annotation files
            processor: RTDetrImageProcessor from HuggingFace
            transform: Optional albumentations transform for augmentation
            image_size: Target image size for resizing
        """
        self.images_dir = Path(images_dir)
        self.annotations_dir = Path(annotations_dir)
        self.processor = processor
        self.transform = transform
        self.image_size = image_size

        # Load image IDs from list file
        self.image_ids = self._load_image_ids(list_file)
        logger.info(f"Loaded {len(self.image_ids)} images from {list_file}")

        # Validate that files exist
        self._validate_files()

    def _load_image_ids(self, list_file: str | Path) -> list[str]:
        """Load image IDs from a text file.

        Args:
            list_file: Path to file with one image ID per line

        Returns:
            List of image ID strings
        """
        list_path = Path(list_file)
        if not list_path.exists():
            raise FileNotFoundError(f"List file not found: {list_path}")

        with open(list_path) as f:
            ids = [line.strip() for line in f if line.strip()]

        return ids

    def _validate_files(self) -> None:
        """Check that all referenced image and annotation files exist."""
        missing_images = []
        missing_annotations = []

        for img_id in self.image_ids:
            img_path = self.images_dir / f"{img_id}.jpg"
            ann_path = self.annotations_dir / f"{img_id}.json"

            if not img_path.exists():
                missing_images.append(img_id)
            if not ann_path.exists():
                missing_annotations.append(img_id)

        if missing_images:
            logger.warning(f"Missing {len(missing_images)} images: {missing_images[:5]}...")
        if missing_annotations:
            logger.warning(
                f"Missing {len(missing_annotations)} annotations: {missing_annotations[:5]}..."
            )

        # Filter to only valid samples
        valid_ids = [
            img_id
            for img_id in self.image_ids
            if (self.images_dir / f"{img_id}.jpg").exists()
            and (self.annotations_dir / f"{img_id}.json").exists()
        ]

        if len(valid_ids) < len(self.image_ids):
            logger.warning(
                f"Filtered from {len(self.image_ids)} to {len(valid_ids)} valid samples"
            )
            self.image_ids = valid_ids

    def _load_annotation(self, img_id: str) -> dict:
        """Load annotation JSON for an image.

        Args:
            img_id: Image identifier

        Returns:
            Annotation dictionary with 'labels' containing bounding boxes
        """
        ann_path = self.annotations_dir / f"{img_id}.json"
        with open(ann_path) as f:
            return json.load(f)

    def _convert_to_coco_format(
        self, annotation: dict, image_width: int, image_height: int
    ) -> dict:
        """Convert AGAR annotation format to COCO format.

        AGAR format: {x, y, width, height, class} where x,y is top-left corner
        COCO format: [x_min, y_min, width, height] with absolute pixel coordinates

        Args:
            annotation: AGAR format annotation dictionary
            image_width: Original image width in pixels
            image_height: Original image height in pixels

        Returns:
            Dictionary with 'boxes', 'labels', and 'area' in COCO format
        """
        boxes = []
        labels = []
        areas = []

        for label in annotation.get("labels", []):
            # Extract bbox coordinates (already in x, y, w, h format)
            x = label["x"]
            y = label["y"]
            w = label["width"]
            h = label["height"]

            # Ensure box is within image bounds
            x = max(0, min(x, image_width - 1))
            y = max(0, min(y, image_height - 1))
            w = max(1, min(w, image_width - x))
            h = max(1, min(h, image_height - y))

            # Get class index
            class_name = label["class"]
            if class_name not in CLASS_MAP:
                logger.warning(f"Unknown class: {class_name}, skipping")
                continue

            class_idx = CLASS_MAP[class_name]

            boxes.append([x, y, w, h])
            labels.append(class_idx)
            areas.append(w * h)

        return {
            "boxes": boxes,
            "labels": labels,
            "area": areas,
            "iscrowd": [0] * len(boxes),  # No crowd annotations
        }

    def __len__(self) -> int:
        """Return the number of samples in the dataset."""
        return len(self.image_ids)

    def __getitem__(self, idx: int) -> dict:
        """Get a single sample from the dataset.

        Args:
            idx: Sample index

        Returns:
            Dictionary with 'pixel_values', 'labels' ready for RT-DETR
        """
        img_id = self.image_ids[idx]

        # Load image
        img_path = self.images_dir / f"{img_id}.jpg"
        image = Image.open(img_path).convert("RGB")
        image_np = np.array(image)
        orig_height, orig_width = image_np.shape[:2]

        # Load and convert annotation
        annotation = self._load_annotation(img_id)
        coco_ann = self._convert_to_coco_format(annotation, orig_width, orig_height)

        # Apply augmentations if provided
        if self.transform is not None and len(coco_ann["boxes"]) > 0:
            # Albumentations expects boxes in [x_min, y_min, x_max, y_max] format
            boxes_xyxy = []
            for box in coco_ann["boxes"]:
                x, y, w, h = box
                boxes_xyxy.append([x, y, x + w, y + h])

            transformed = self.transform(
                image=image_np,
                bboxes=boxes_xyxy,
                labels=coco_ann["labels"],
            )

            image_np = transformed["image"]
            transformed_boxes = transformed["bboxes"]
            transformed_labels = transformed["labels"]

            # Convert back to x, y, w, h format
            coco_ann["boxes"] = []
            for box in transformed_boxes:
                x_min, y_min, x_max, y_max = box
                coco_ann["boxes"].append([x_min, y_min, x_max - x_min, y_max - y_min])
            coco_ann["labels"] = list(transformed_labels)
            coco_ann["area"] = [
                (b[2]) * (b[3]) for b in coco_ann["boxes"]
            ]
            coco_ann["iscrowd"] = [0] * len(coco_ann["boxes"])

            image = Image.fromarray(image_np)

        # Get new dimensions after augmentation
        new_width, new_height = image.size

        # Prepare target in COCO format expected by HuggingFace RTDetrImageProcessor
        # Format: {"image_id": int, "annotations": [{"bbox": [x,y,w,h], "category_id": int, "area": float, "iscrowd": int}]}
        annotations_list = []
        if len(coco_ann["boxes"]) > 0:
            for i, box in enumerate(coco_ann["boxes"]):
                annotations_list.append({
                    "bbox": box,  # [x, y, w, h] format
                    "category_id": coco_ann["labels"][i],
                    "area": coco_ann["area"][i],
                    "iscrowd": coco_ann["iscrowd"][i],
                })

        target = {
            "image_id": idx,
            "annotations": annotations_list,
        }

        # Process image with RT-DETR processor
        encoding = self.processor(
            images=image,
            annotations=[target],
            return_tensors="pt",
        )

        # Remove batch dimension (DataLoader will add it back)
        pixel_values = encoding["pixel_values"].squeeze(0)
        labels = encoding["labels"][0]

        return {
            "pixel_values": pixel_values,
            "labels": labels,
        }


def get_train_transform(image_size: int = 640, config: dict | None = None) -> A.Compose:
    """Create training augmentation pipeline.

    Args:
        image_size: Target image size
        config: Optional config dict with augmentation settings

    Returns:
        Albumentations Compose transform
    """
    aug_config = config.get("augmentation", {}) if config else {}

    transforms = [
        # Resize to target size
        A.LongestMaxSize(max_size=image_size),
        A.PadIfNeeded(
            min_height=image_size,
            min_width=image_size,
            border_mode=0,
            value=(114, 114, 114),
        ),
    ]

    # Horizontal flip
    if aug_config.get("horizontal_flip", 0.5) > 0:
        transforms.append(A.HorizontalFlip(p=aug_config.get("horizontal_flip", 0.5)))

    # Vertical flip
    if aug_config.get("vertical_flip", 0.5) > 0:
        transforms.append(A.VerticalFlip(p=aug_config.get("vertical_flip", 0.5)))

    # Color jitter
    color_config = aug_config.get("color_jitter", {})
    if color_config:
        transforms.append(
            A.ColorJitter(
                brightness=color_config.get("brightness", 0.2),
                contrast=color_config.get("contrast", 0.2),
                saturation=color_config.get("saturation", 0.1),
                hue=color_config.get("hue", 0.05),
                p=0.5,
            )
        )

    # Random rotate (small angles)
    transforms.append(A.Rotate(limit=15, p=0.3, border_mode=0, value=(114, 114, 114)))

    return A.Compose(
        transforms,
        bbox_params=A.BboxParams(
            format="pascal_voc",  # [x_min, y_min, x_max, y_max]
            min_visibility=0.3,
            label_fields=["labels"],
        ),
    )


def get_val_transform(image_size: int = 640) -> A.Compose:
    """Create validation transform pipeline (no augmentation).

    Args:
        image_size: Target image size

    Returns:
        Albumentations Compose transform
    """
    return A.Compose(
        [
            A.LongestMaxSize(max_size=image_size),
            A.PadIfNeeded(
                min_height=image_size,
                min_width=image_size,
                border_mode=0,
                value=(114, 114, 114),
            ),
        ],
        bbox_params=A.BboxParams(
            format="pascal_voc",
            min_visibility=0.3,
            label_fields=["labels"],
        ),
    )


def collate_fn(batch: list[dict]) -> dict:
    """Custom collate function for RT-DETR batches.

    Handles variable number of boxes per image by keeping labels as a list.

    Args:
        batch: List of sample dictionaries

    Returns:
        Batched dictionary with stacked pixel_values and list of labels
    """
    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    labels = [item["labels"] for item in batch]

    return {
        "pixel_values": pixel_values,
        "labels": labels,
    }


def create_dataloaders(
    config: dict,
    processor: Any,
    batch_size: int | None = None,
    num_workers: int | None = None,
) -> tuple:
    """Create train and validation dataloaders from config.

    Args:
        config: Configuration dictionary with dataset paths
        processor: RTDetrImageProcessor instance
        batch_size: Override batch size from config
        num_workers: Override num_workers from config

    Returns:
        Tuple of (train_dataloader, val_dataloader)
    """
    from torch.utils.data import DataLoader

    batch_size = batch_size or config.get("batch_size", 4)
    num_workers = num_workers or config.get("num_workers", 4)
    image_size = config.get("augmentation", {}).get("image_size", 640)

    # Create datasets
    train_dataset = AGARDataset(
        list_file=config["train_list"],
        images_dir=config["images_dir"],
        annotations_dir=config["annotations_dir"],
        processor=processor,
        transform=get_train_transform(image_size, config),
        image_size=image_size,
    )

    val_dataset = AGARDataset(
        list_file=config["val_list"],
        images_dir=config["images_dir"],
        annotations_dir=config["annotations_dir"],
        processor=processor,
        transform=get_val_transform(image_size),
        image_size=image_size,
    )

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        collate_fn=collate_fn,
        pin_memory=True,
        drop_last=True,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )

    logger.info(f"Created dataloaders: train={len(train_dataset)}, val={len(val_dataset)}")

    return train_loader, val_loader


if __name__ == "__main__":
    # Quick test of dataset loading
    import yaml
    from transformers import RTDetrImageProcessor

    logging.basicConfig(level=logging.INFO)

    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Initialize processor
    processor = RTDetrImageProcessor.from_pretrained(config["model_name"])

    # Test dataset
    test_dataset = AGARDataset(
        list_file=config["train_list"],
        images_dir=config["images_dir"],
        annotations_dir=config["annotations_dir"],
        processor=processor,
        transform=get_val_transform(config["augmentation"]["image_size"]),
    )

    print(f"Dataset size: {len(test_dataset)}")

    # Test single sample
    sample = test_dataset[0]
    print(f"Pixel values shape: {sample['pixel_values'].shape}")
    print(f"Labels keys: {sample['labels'].keys()}")
    print(f"Number of boxes: {len(sample['labels']['boxes'])}")
    print(f"Class labels: {sample['labels']['class_labels']}")
