#!/usr/bin/env python3
"""
Convert AGAR dataset format to COCO format for RT-DETR v4 training.

AGAR format:
  - Images: {images_dir}/{id}.jpg
  - Annotations: {annotations_dir}/{id}.json with structure:
    {"labels": [{"x": int, "y": int, "width": int, "height": int, "class": str}, ...]}

COCO format:
  - Images: data/agar/images/{split}/
  - Annotations: data/agar/annotations/instances_{split}.json

Usage:
    python tools/convert_agar_to_coco.py \
        --images-dir /path/to/agar/images \
        --annotations-dir /path/to/agar/annotations \
        --train-list /path/to/train.txt \
        --val-list /path/to/val.txt \
        --output-dir data/agar

RESEARCH USE ONLY: AGAR dataset is CC BY-NC 2.0 licensed.
"""

import argparse
import json
import shutil
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import sys

# Add parent directory for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.constants import CLASSES, CLASS_MAP


def load_image_ids(list_file: Path) -> list[str]:
    """Load image IDs from a text file (one ID per line)."""
    with open(list_file) as f:
        return [line.strip() for line in f if line.strip()]


def convert_agar_annotation(ann_path: Path, image_id: int, image_width: int, image_height: int, single_class: bool = False) -> list[dict]:
    """Convert a single AGAR annotation file to COCO annotation format.

    Args:
        ann_path: Path to AGAR JSON annotation file
        image_id: COCO image ID
        image_width: Image width in pixels
        image_height: Image height in pixels
        single_class: If True, merge all classes into category_id=0 (colony)

    Returns:
        List of COCO annotation dictionaries
    """
    with open(ann_path) as f:
        agar_ann = json.load(f)

    coco_annotations = []
    annotation_id_base = image_id * 10000  # Ensure unique annotation IDs

    for i, label in enumerate(agar_ann.get("labels", [])):
        # AGAR format: x, y is top-left corner, width, height
        x = label["x"]
        y = label["y"]
        w = label["width"]
        h = label["height"]

        # Clamp to image bounds
        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        w = max(1, min(w, image_width - x))
        h = max(1, min(h, image_height - y))

        # Get class ID
        class_name = label["class"]
        if class_name not in CLASS_MAP:
            print(f"  Warning: Unknown class '{class_name}', skipping")
            continue

        # Single-class mode: all classes become category_id=0
        # Multi-class mode: use original category IDs (0-indexed)
        category_id = 0 if single_class else CLASS_MAP[class_name]

        coco_annotations.append({
            "id": annotation_id_base + i,
            "image_id": image_id,
            "category_id": category_id,
            "bbox": [x, y, w, h],  # COCO format: [x, y, width, height]
            "area": w * h,
            "iscrowd": 0,
            "segmentation": [],
        })

    return coco_annotations


def create_coco_dataset(
    image_ids: list[str],
    images_dir: Path,
    annotations_dir: Path,
    output_images_dir: Path,
    split: str,
    single_class: bool = False,
) -> dict:
    """Create COCO format dataset from AGAR format.

    Args:
        image_ids: List of image IDs to include
        images_dir: Source directory with AGAR images
        annotations_dir: Source directory with AGAR annotations
        output_images_dir: Destination directory for images
        split: Dataset split name (train/val/test)
        single_class: If True, merge all classes into single "colony" category

    Returns:
        COCO format dataset dictionary
    """
    output_images_dir.mkdir(parents=True, exist_ok=True)

    # Category list depends on mode
    if single_class:
        categories = [{"id": 0, "name": "colony", "supercategory": "colony"}]
    else:
        categories = [
            {"id": i, "name": name, "supercategory": "colony"}
            for i, name in enumerate(CLASSES)
        ]

    # COCO dataset structure
    coco_dataset = {
        "info": {
            "description": f"AGAR Colony Detection Dataset ({split})",
            "version": "1.0",
            "year": 2024,
            "contributor": "CFU-Counter Project",
            "url": "",
            "date_created": "",
        },
        "licenses": [
            {
                "id": 1,
                "name": "CC BY-NC 2.0",
                "url": "https://creativecommons.org/licenses/by-nc/2.0/",
            }
        ],
        "categories": categories,
        "images": [],
        "annotations": [],
    }

    print(f"\nProcessing {split} split ({len(image_ids)} images)...")

    skipped = 0
    for idx, img_id in enumerate(tqdm(image_ids, desc=f"Converting {split}")):
        src_img_path = images_dir / f"{img_id}.jpg"
        src_ann_path = annotations_dir / f"{img_id}.json"

        # Check files exist
        if not src_img_path.exists():
            print(f"  Warning: Image not found: {src_img_path}")
            skipped += 1
            continue
        if not src_ann_path.exists():
            print(f"  Warning: Annotation not found: {src_ann_path}")
            skipped += 1
            continue

        # Get image dimensions
        with Image.open(src_img_path) as img:
            width, height = img.size

        # Symlink image to output directory (saves disk space)
        dst_img_path = output_images_dir / f"{img_id}.jpg"
        if not dst_img_path.exists():
            dst_img_path.symlink_to(src_img_path.resolve())

        # Add image entry
        coco_dataset["images"].append({
            "id": idx,
            "file_name": f"{img_id}.jpg",
            "width": width,
            "height": height,
        })

        # Convert and add annotations
        annotations = convert_agar_annotation(src_ann_path, idx, width, height, single_class)
        coco_dataset["annotations"].extend(annotations)

    print(f"  Processed: {len(coco_dataset['images'])} images, {len(coco_dataset['annotations'])} annotations")
    if skipped > 0:
        print(f"  Skipped: {skipped} images (missing files)")

    return coco_dataset


def main():
    parser = argparse.ArgumentParser(description="Convert AGAR dataset to COCO format")
    parser.add_argument("--images-dir", type=Path, required=True, help="AGAR images directory")
    parser.add_argument("--annotations-dir", type=Path, required=True, help="AGAR annotations directory")
    parser.add_argument("--train-list", type=Path, required=True, help="Text file with training image IDs")
    parser.add_argument("--val-list", type=Path, required=True, help="Text file with validation image IDs")
    parser.add_argument("--test-list", type=Path, help="Optional: Text file with test image IDs (held-out test set)")
    parser.add_argument("--output-dir", type=Path, default=Path("data/agar"), help="Output directory")
    parser.add_argument("--single-class", action="store_true", help="Merge all 7 classes into single 'colony' class (category_id=0)")
    args = parser.parse_args()

    mode = "single-class (colony)" if args.single_class else "7-class (species)"
    print("AGAR to COCO Conversion Tool")
    print("=" * 50)
    print(f"Mode: {mode}")
    print(f"Images dir: {args.images_dir}")
    print(f"Annotations dir: {args.annotations_dir}")
    print(f"Output dir: {args.output_dir}")
    if not args.single_class:
        print(f"Classes: {CLASSES}")
    print("=" * 50)

    # Create output directories
    output_ann_dir = args.output_dir / "annotations"
    output_ann_dir.mkdir(parents=True, exist_ok=True)

    # Process training set
    train_ids = load_image_ids(args.train_list)
    train_coco = create_coco_dataset(
        train_ids,
        args.images_dir,
        args.annotations_dir,
        args.output_dir / "images" / "train",
        "train",
        args.single_class,
    )

    train_ann_path = output_ann_dir / "instances_train.json"
    with open(train_ann_path, "w") as f:
        json.dump(train_coco, f, indent=2)
    print(f"Saved: {train_ann_path}")

    # Process validation set
    val_ids = load_image_ids(args.val_list)
    val_coco = create_coco_dataset(
        val_ids,
        args.images_dir,
        args.annotations_dir,
        args.output_dir / "images" / "val",
        "val",
        args.single_class,
    )

    val_ann_path = output_ann_dir / "instances_val.json"
    with open(val_ann_path, "w") as f:
        json.dump(val_coco, f, indent=2)
    print(f"Saved: {val_ann_path}")

    # Process test set (if provided)
    if args.test_list:
        test_ids = load_image_ids(args.test_list)
        test_coco = create_coco_dataset(
            test_ids,
            args.images_dir,
            args.annotations_dir,
            args.output_dir / "images" / "test",
            "test",
            args.single_class,
        )

        test_ann_path = output_ann_dir / "instances_test.json"
        with open(test_ann_path, "w") as f:
            json.dump(test_coco, f, indent=2)
        print(f"Saved: {test_ann_path}")

    print("\nConversion complete!")
    print(f"\nExpected directory structure:")
    print(f"  {args.output_dir}/")
    print(f"    images/")
    print(f"      train/  ({len(train_coco['images'])} images)")
    print(f"      val/    ({len(val_coco['images'])} images)")
    if args.test_list:
        print(f"      test/   ({len(test_coco['images'])} images)")
    print(f"    annotations/")
    print(f"      instances_train.json")
    print(f"      instances_val.json")
    if args.test_list:
        print(f"      instances_test.json")

    print("\nTo train RT-DETR v4-X on this dataset:")
    print("  cd rtdetr_v4")
    print("  python train.py -c configs/dfine/dfine_hgnetv2_x_agar.yml -t checkpoints/rtv4_hgnetv2_x_coco.pth")


if __name__ == "__main__":
    main()
