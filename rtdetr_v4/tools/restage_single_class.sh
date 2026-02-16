#!/bin/bash
set -euo pipefail

# RunPod re-staging script for single-class COCO annotations
# Converts existing 7-class COCO annotations to single-class (colony) in-place
# Avoids re-uploading all images to the network volume

DATA_DIR="/workspace/data"
TEST_PCT=0

usage() {
    echo "Usage: $0 [--data-dir PATH] [--test-pct PCT]"
    echo "  --data-dir PATH   Data directory (default: /workspace/data)"
    echo "  --test-pct PCT    Percentage of val images to move to test split (0-100, default: 0)"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --test-pct)
            TEST_PCT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown argument: $1"
            usage
            ;;
    esac
done

echo "=========================================="
echo "RunPod Single-Class Re-staging Script"
echo "=========================================="
echo "Data directory: $DATA_DIR"
echo "Test split percentage: $TEST_PCT%"
echo ""

# Check annotations exist
TRAIN_ANN="$DATA_DIR/agar/annotations/instances_train.json"
VAL_ANN="$DATA_DIR/agar/annotations/instances_val.json"

if [[ ! -f "$TRAIN_ANN" ]]; then
    echo "Error: Training annotations not found at $TRAIN_ANN"
    exit 1
fi

if [[ ! -f "$VAL_ANN" ]]; then
    echo "Error: Validation annotations not found at $VAL_ANN"
    exit 1
fi

echo "Found existing annotations:"
echo "  - $TRAIN_ANN"
echo "  - $VAL_ANN"
echo ""

# Backup original 7-class annotations
echo "Creating backups..."
cp "$TRAIN_ANN" "${TRAIN_ANN%.json}_7cls.json"
cp "$VAL_ANN" "${VAL_ANN%.json}_7cls.json"
echo "  - instances_train_7cls.json"
echo "  - instances_val_7cls.json"
echo ""

# Convert to single-class using Python
echo "Converting to single-class..."
python3 - "$DATA_DIR" "$TEST_PCT" <<'PYTHON_SCRIPT'
import json
import sys
import random
from pathlib import Path

data_dir = Path(sys.argv[1])
test_pct = float(sys.argv[2])
ann_dir = data_dir / "agar" / "annotations"

# Single-class category
single_class_categories = [{"id": 0, "name": "colony", "supercategory": "colony"}]

def convert_to_single_class(ann_file):
    """Convert a COCO annotation file to single-class."""
    with open(ann_file) as f:
        data = json.load(f)

    # Get original stats
    orig_images = len(data["images"])
    orig_anns = len(data["annotations"])
    orig_cats = len(data["categories"])

    # Convert all annotations to category_id=0
    for ann in data["annotations"]:
        ann["category_id"] = 0

    # Replace categories
    data["categories"] = single_class_categories

    # Write back
    with open(ann_file, "w") as f:
        json.dump(data, f, indent=2)

    return orig_images, orig_anns, orig_cats

# Convert training set
train_ann = ann_dir / "instances_train.json"
print(f"  Converting {train_ann.name}...")
train_imgs, train_anns, train_cats = convert_to_single_class(train_ann)
print(f"    Before: {train_imgs} images, {train_anns} annotations, {train_cats} categories")
print(f"    After:  {train_imgs} images, {train_anns} annotations, 1 category")

# Convert validation set
val_ann = ann_dir / "instances_val.json"
print(f"  Converting {val_ann.name}...")
val_imgs, val_anns, val_cats = convert_to_single_class(val_ann)
print(f"    Before: {val_imgs} images, {val_anns} annotations, {val_cats} categories")
print(f"    After:  {val_imgs} images, {val_anns} annotations, 1 category")

# Create test split if requested
if test_pct > 0:
    print(f"\n  Creating test split ({test_pct}% of validation)...")

    with open(val_ann) as f:
        val_data = json.load(f)

    # Random sample with fixed seed for reproducibility
    random.seed(42)
    n_test = int(len(val_data["images"]) * test_pct / 100)
    test_images = random.sample(val_data["images"], n_test)
    test_image_ids = {img["id"] for img in test_images}

    # Split images
    val_images = [img for img in val_data["images"] if img["id"] not in test_image_ids]

    # Split annotations
    test_annotations = [ann for ann in val_data["annotations"] if ann["image_id"] in test_image_ids]
    val_annotations = [ann for ann in val_data["annotations"] if ann["image_id"] not in test_image_ids]

    # Create test dataset
    test_data = val_data.copy()
    test_data["images"] = test_images
    test_data["annotations"] = test_annotations
    test_data["info"]["description"] = "AGAR Colony Detection Dataset (test)"

    # Update validation dataset
    val_data["images"] = val_images
    val_data["annotations"] = val_annotations

    # Write files
    test_ann = ann_dir / "instances_test.json"
    with open(test_ann, "w") as f:
        json.dump(test_data, f, indent=2)

    with open(val_ann, "w") as f:
        json.dump(val_data, f, indent=2)

    print(f"    Test:  {len(test_images)} images, {len(test_annotations)} annotations")
    print(f"    Val:   {len(val_images)} images, {len(val_annotations)} annotations")

PYTHON_SCRIPT

if [[ $? -ne 0 ]]; then
    echo ""
    echo "Error: Python conversion failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Conversion complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Update config: num_classes=1 in your training config"
echo "  2. Launch training with the updated config"
echo ""
echo "To restore 7-class annotations:"
echo "  cp $DATA_DIR/agar/annotations/instances_train_7cls.json $TRAIN_ANN"
echo "  cp $DATA_DIR/agar/annotations/instances_val_7cls.json $VAL_ANN"
