#!/usr/bin/env python3
"""
YOLOv8 Baseline Training Script

RESEARCH USE ONLY -- AGPL LICENSE
This script uses ultralytics (YOLOv8) for baseline comparison.
DO NOT import or use in production code (AGPL copyleft).

This script trains YOLOv8 on the same single-class COCO dataset used for D-FINE training,
enabling apples-to-apples comparison. It converts COCO format to YOLO format on the fly
and trains at 1024x1024 resolution to match D-FINE evaluation settings.
"""

import argparse
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


def convert_coco_to_yolo_format(
    coco_json_path: Path,
    images_dir: Path,
    labels_output_dir: Path,
    single_class: bool = True
) -> Tuple[List[str], Dict[int, int]]:
    """
    Convert COCO annotations to YOLO format.

    YOLO format: One .txt file per image with lines: <class_id> <cx> <cy> <w> <h>
    All values are normalized to [0, 1].

    Args:
        coco_json_path: Path to COCO annotations JSON
        images_dir: Directory containing images
        labels_output_dir: Directory to write YOLO .txt label files
        single_class: If True, map all category IDs to 0

    Returns:
        Tuple of (list of image filenames, category_id mapping dict)
    """
    labels_output_dir.mkdir(parents=True, exist_ok=True)

    with open(coco_json_path, 'r') as f:
        coco_data = json.load(f)

    # Build image_id -> image info mapping
    images = {img['id']: img for img in coco_data['images']}

    # Build category mapping
    if single_class:
        category_mapping = {cat['id']: 0 for cat in coco_data['categories']}
    else:
        category_mapping = {cat['id']: cat['id'] for cat in coco_data['categories']}

    # Group annotations by image_id
    annotations_by_image = {}
    for ann in coco_data['annotations']:
        img_id = ann['image_id']
        if img_id not in annotations_by_image:
            annotations_by_image[img_id] = []
        annotations_by_image[img_id].append(ann)

    # Convert each image's annotations to YOLO format
    image_filenames = []
    for img_id, img_info in images.items():
        img_filename = img_info['file_name']
        image_filenames.append(img_filename)

        img_width = img_info['width']
        img_height = img_info['height']

        # Create corresponding .txt label file
        label_filename = Path(img_filename).stem + '.txt'
        label_path = labels_output_dir / label_filename

        # Get annotations for this image
        anns = annotations_by_image.get(img_id, [])

        with open(label_path, 'w') as f:
            for ann in anns:
                # COCO bbox format: [x, y, width, height] (top-left corner)
                x, y, w, h = ann['bbox']

                # Convert to YOLO format: [cx, cy, w, h] normalized
                cx = (x + w / 2) / img_width
                cy = (y + h / 2) / img_height
                norm_w = w / img_width
                norm_h = h / img_height

                # Get class ID
                class_id = category_mapping[ann['category_id']]

                # Write line: <class_id> <cx> <cy> <w> <h>
                f.write(f"{class_id} {cx:.6f} {cy:.6f} {norm_w:.6f} {norm_h:.6f}\n")

    print(f"Converted {len(image_filenames)} images to YOLO format")
    print(f"Labels saved to: {labels_output_dir}")

    return image_filenames, category_mapping


def create_dataset_yaml(
    data_dir: Path,
    output_path: Path,
    single_class: bool = True
) -> None:
    """
    Create YOLO dataset YAML config file.

    Args:
        data_dir: Root directory containing images/ and labels/ subdirectories
        output_path: Path to write dataset.yaml
        single_class: If True, use single "colony" class
    """
    dataset_config = {
        'path': str(data_dir.absolute()),
        'train': 'images/train',
        'val': 'images/val',
        'names': {0: 'colony'} if single_class else {}
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        yaml.dump(dataset_config, f, default_flow_style=False, sort_keys=False)

    print(f"Dataset YAML created: {output_path}")


def train_yolov8(args):
    """
    Train YOLOv8 on single-class COCO dataset.
    """
    # RESEARCH USE ONLY -- AGPL LICENSE
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed.")
        print("Install with: pip install ultralytics")
        print("WARNING: ultralytics is AGPL licensed - DO NOT use in production code")
        return

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("YOLOv8 BASELINE TRAINING - RESEARCH USE ONLY (AGPL LICENSE)")
    print("=" * 70)
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Model: {args.model}")
    print(f"Image size: {args.imgsz}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch}")
    print(f"Device: {args.device}")
    print(f"Single-class mode: {args.single_class}")
    print("=" * 70)

    # Convert COCO to YOLO format
    print("\nStep 1: Converting COCO annotations to YOLO format...")

    # Create labels directories
    labels_dir = data_dir / 'labels'
    labels_train_dir = labels_dir / 'train'
    labels_val_dir = labels_dir / 'val'

    # Convert train annotations
    train_coco_json = data_dir / 'annotations' / 'instances_train.json'
    if not train_coco_json.exists():
        print(f"ERROR: Train annotations not found: {train_coco_json}")
        return

    convert_coco_to_yolo_format(
        train_coco_json,
        data_dir / 'images' / 'train',
        labels_train_dir,
        single_class=args.single_class
    )

    # Convert val annotations
    val_coco_json = data_dir / 'annotations' / 'instances_val.json'
    if not val_coco_json.exists():
        print(f"ERROR: Val annotations not found: {val_coco_json}")
        return

    convert_coco_to_yolo_format(
        val_coco_json,
        data_dir / 'images' / 'val',
        labels_val_dir,
        single_class=args.single_class
    )

    # Create dataset YAML
    print("\nStep 2: Creating dataset YAML config...")
    dataset_yaml_path = output_dir / 'dataset.yaml'
    create_dataset_yaml(data_dir, dataset_yaml_path, single_class=args.single_class)

    # Train YOLOv8
    print("\nStep 3: Training YOLOv8...")
    print(f"Loading pretrained model: {args.model}")

    model = YOLO(args.model)

    results = model.train(
        data=str(dataset_yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=str(output_dir),
        name='train',
        exist_ok=True,
        single_cls=args.single_class,
        save=True,
        save_period=10,
        verbose=True,
    )

    print("\nStep 4: Running validation...")
    metrics = model.val()

    # Save metrics to JSON
    metrics_dict = {
        'map50_95': float(metrics.box.map),
        'map50': float(metrics.box.map50),
        'map75': float(metrics.box.map75),
        'precision': float(metrics.box.mp),
        'recall': float(metrics.box.mr),
    }

    metrics_path = output_dir / 'train' / 'metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics_dict, f, indent=2)

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    print(f"Best weights: {output_dir / 'train' / 'weights' / 'best.pt'}")
    print(f"Metrics saved: {metrics_path}")
    print("\nValidation Metrics:")
    print(f"  mAP@0.5:0.95: {metrics_dict['map50_95']:.4f}")
    print(f"  mAP@0.5: {metrics_dict['map50']:.4f}")
    print(f"  Precision: {metrics_dict['precision']:.4f}")
    print(f"  Recall: {metrics_dict['recall']:.4f}")
    print("\nNext steps:")
    print("1. Run inference to generate predictions in COCO format")
    print("2. Use evaluate_count_accuracy.py to compare with D-FINE")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Train YOLOv8 baseline on single-class COCO dataset (RESEARCH ONLY - AGPL)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single GPU training
  python train_yolov8_baseline.py --data-dir data/agar --single-class

  # Multi-GPU training (4x A100)
  python train_yolov8_baseline.py --data-dir data/agar --device 0,1,2,3 --batch 64 --single-class

WARNING: This script uses ultralytics (AGPL license) and is for RESEARCH ONLY.
DO NOT use in production code.
        """
    )

    parser.add_argument(
        '--data-dir',
        type=str,
        default='data/agar',
        help='COCO dataset directory (default: data/agar)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='yolov8x.pt',
        help='YOLOv8 pretrained weights (default: yolov8x.pt)'
    )
    parser.add_argument(
        '--imgsz',
        type=int,
        default=1024,
        help='Input image size (default: 1024, must match D-FINE for fair comparison)'
    )
    parser.add_argument(
        '--epochs',
        type=int,
        default=50,
        help='Training epochs (default: 50)'
    )
    parser.add_argument(
        '--batch',
        type=int,
        default=16,
        help='Batch size (default: 16)'
    )
    parser.add_argument(
        '--device',
        type=str,
        default='0,1,2,3',
        help='GPU devices (default: 0,1,2,3)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/yolov8x_agar_1cls',
        help='Output directory (default: outputs/yolov8x_agar_1cls)'
    )
    parser.add_argument(
        '--single-class',
        action='store_true',
        help='Enable single-class mode (all categories mapped to class 0)'
    )

    args = parser.parse_args()

    if not args.single_class:
        print("WARNING: --single-class flag not provided. Training in multi-class mode.")
        print("For apples-to-apples comparison with D-FINE, use --single-class")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return

    train_yolov8(args)


if __name__ == '__main__':
    main()
