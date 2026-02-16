#!/bin/bash
# Stage AGAR dataset and pretrained weights for RunPod Network Volume upload.
#
# Copies only the higher-resolution subset (6,988 images) into the COCO
# directory structure expected by agar_detection.yml, along with pre-converted
# COCO annotations and D-FINE pretrained weights.
#
# Output structure:
#   <output-dir>/
#     agar/
#       images/train/   (5,241 JPGs)
#       images/val/     (1,747 JPGs)
#       annotations/instances_train.json
#       annotations/instances_val.json
#     pretrain/
#       dfine_hgnetv2_x_coco.pth
#
# Usage:
#   bash tools/stage_agar_data.sh \
#       --images-dir /path/to/agar/images \
#       --train-list /path/to/higher_resolution_train.txt \
#       --val-list /path/to/higher_resolution_val.txt \
#       --coco-ann-dir /path/to/coco_annotations \
#       --weights /path/to/dfine_hgnetv2_x_coco.pth \
#       --output-dir /tmp/staging
#
# After staging, create the upload archive:
#   tar -czf staging.tar.gz -C /tmp/staging .

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
IMAGES_DIR=""
TRAIN_LIST=""
VAL_LIST=""
COCO_ANN_DIR=""
WEIGHTS=""
OUTPUT_DIR=""

usage() {
    echo "Usage: $0 --images-dir DIR --train-list FILE --val-list FILE --coco-ann-dir DIR --weights FILE --output-dir DIR"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --images-dir)   IMAGES_DIR="$2";   shift 2 ;;
        --train-list)   TRAIN_LIST="$2";   shift 2 ;;
        --val-list)     VAL_LIST="$2";     shift 2 ;;
        --coco-ann-dir) COCO_ANN_DIR="$2"; shift 2 ;;
        --weights)      WEIGHTS="$2";      shift 2 ;;
        --output-dir)   OUTPUT_DIR="$2";   shift 2 ;;
        *) echo "Unknown argument: $1"; usage ;;
    esac
done

if [[ -z "$IMAGES_DIR" || -z "$TRAIN_LIST" || -z "$VAL_LIST" || -z "$COCO_ANN_DIR" || -z "$WEIGHTS" || -z "$OUTPUT_DIR" ]]; then
    echo "ERROR: All arguments are required."
    usage
fi

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------
for f in "$TRAIN_LIST" "$VAL_LIST" "$WEIGHTS"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: File not found: $f"
        exit 1
    fi
done

for d in "$IMAGES_DIR" "$COCO_ANN_DIR"; do
    if [[ ! -d "$d" ]]; then
        echo "ERROR: Directory not found: $d"
        exit 1
    fi
done

for ann in "instances_train.json" "instances_val.json"; do
    if [[ ! -f "$COCO_ANN_DIR/$ann" ]]; then
        echo "ERROR: Annotation file not found: $COCO_ANN_DIR/$ann"
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Create output directories
# ---------------------------------------------------------------------------
echo "Staging to: $OUTPUT_DIR"

TRAIN_IMG_DIR="$OUTPUT_DIR/agar/images/train"
VAL_IMG_DIR="$OUTPUT_DIR/agar/images/val"
ANN_DIR="$OUTPUT_DIR/agar/annotations"
PRETRAIN_DIR="$OUTPUT_DIR/pretrain"

mkdir -p "$TRAIN_IMG_DIR" "$VAL_IMG_DIR" "$ANN_DIR" "$PRETRAIN_DIR"

# ---------------------------------------------------------------------------
# Copy images listed in train/val splits
# ---------------------------------------------------------------------------
copy_images() {
    local list_file="$1"
    local dest_dir="$2"
    local split_name="$3"
    local count=0
    local missing=0

    echo ""
    echo "Copying $split_name images..."

    while IFS= read -r image_id || [[ -n "$image_id" ]]; do
        # Skip empty lines
        [[ -z "$image_id" ]] && continue

        # Strip whitespace and any .jpg extension if present
        image_id=$(echo "$image_id" | tr -d '[:space:]')
        image_id="${image_id%.jpg}"

        local src="$IMAGES_DIR/${image_id}.jpg"
        if [[ -f "$src" ]]; then
            cp "$src" "$dest_dir/"
            count=$((count + 1))
        else
            missing=$((missing + 1))
            if [[ $missing -le 5 ]]; then
                echo "  WARNING: Missing image: $src"
            fi
        fi
    done < "$list_file"

    echo "  Copied $count $split_name images"
    if [[ $missing -gt 0 ]]; then
        echo "  WARNING: $missing images not found"
    fi
}

copy_images "$TRAIN_LIST" "$TRAIN_IMG_DIR" "train"
copy_images "$VAL_LIST" "$VAL_IMG_DIR" "val"

# ---------------------------------------------------------------------------
# Copy COCO annotations
# ---------------------------------------------------------------------------
echo ""
echo "Copying COCO annotations..."
cp "$COCO_ANN_DIR/instances_train.json" "$ANN_DIR/"
cp "$COCO_ANN_DIR/instances_val.json" "$ANN_DIR/"
echo "  instances_train.json: $(du -h "$ANN_DIR/instances_train.json" | cut -f1)"
echo "  instances_val.json:   $(du -h "$ANN_DIR/instances_val.json" | cut -f1)"

# ---------------------------------------------------------------------------
# Copy pretrained weights
# ---------------------------------------------------------------------------
echo ""
echo "Copying pretrained weights..."
cp "$WEIGHTS" "$PRETRAIN_DIR/dfine_hgnetv2_x_coco.pth"
echo "  dfine_hgnetv2_x_coco.pth: $(du -h "$PRETRAIN_DIR/dfine_hgnetv2_x_coco.pth" | cut -f1)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TRAIN_COUNT=$(find "$TRAIN_IMG_DIR" -name "*.jpg" | wc -l | tr -d ' ')
VAL_COUNT=$(find "$VAL_IMG_DIR" -name "*.jpg" | wc -l | tr -d ' ')
TOTAL_SIZE=$(du -sh "$OUTPUT_DIR" | cut -f1)

echo ""
echo "=============================================="
echo "Staging complete"
echo "=============================================="
echo "  Train images: $TRAIN_COUNT"
echo "  Val images:   $VAL_COUNT"
echo "  Total size:   $TOTAL_SIZE"
echo ""
echo "Next step - create upload archive:"
echo "  tar -czf staging.tar.gz -C $OUTPUT_DIR ."
echo ""
echo "Then upload to RunPod Network Volume:"
echo "  rsync -avz --progress staging.tar.gz <pod-ip>:/workspace/data/"
echo "  ssh <pod-ip> \"cd /workspace/data && tar -xzf staging.tar.gz && rm staging.tar.gz\""
