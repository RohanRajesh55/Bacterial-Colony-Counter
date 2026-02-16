#!/bin/bash
# End-to-end RunPod training workflow for Phase 1
# Orchestrates: setup, data re-staging, D-FINE training, YOLOv8 training, and evaluation
#
# Usage:
#   cd /workspace/CFU-counter/rtdetr_v4
#   bash tools/runpod_train.sh --data-dir /workspace/data
#
# Flags:
#   --data-dir DIR       Data directory (default: /workspace/data)
#   --skip-dfine         Skip D-FINE training (useful for re-runs)
#   --skip-yolo          Skip YOLOv8 training (useful for re-runs)
#   --skip-restage       Skip data re-staging (if already done)
#
# This script determines if Phase 1 succeeds.
# Success criteria: D-FINE count within-5% accuracy > 90% (user threshold, stricter than YOLOv8's 88.73%)

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
DATA_DIR="/workspace/data"
SKIP_DFINE=false
SKIP_YOLO=false
SKIP_RESTAGE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --data-dir) DATA_DIR="$2"; shift 2 ;;
        --skip-dfine) SKIP_DFINE=true; shift ;;
        --skip-yolo) SKIP_YOLO=true; shift ;;
        --skip-restage) SKIP_RESTAGE=true; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RTDETR_DIR="$(dirname "$SCRIPT_DIR")"

# Track timing for each stage
declare -A STAGE_START_TIMES
declare -A STAGE_DURATIONS

# Cleanup handler
cleanup() {
    if [[ $? -ne 0 ]]; then
        echo ""
        echo "=============================================="
        echo "TRAINING FAILED"
        echo "=============================================="
        echo "Check logs above for errors."
        echo ""
        echo "Debugging tips:"
        echo "  - GPU memory: nvidia-smi"
        echo "  - Data paths: ls data/agar/images/train/ | wc -l"
        echo "  - Resume D-FINE: add -r outputs/dfine_hgnetv2_x_agar_1cls/checkpoint.pth"
        echo "  - Re-run only eval: bash tools/runpod_train.sh --skip-dfine --skip-yolo --skip-restage"
        echo ""
    fi
}
trap cleanup EXIT

# Helper function to print stage banners
print_stage() {
    local stage_num="$1"
    local stage_name="$2"
    echo ""
    echo "=============================================="
    echo "Stage $stage_num: $stage_name"
    echo "=============================================="
    STAGE_START_TIMES[$stage_num]=$(date +%s)
}

# Helper function to record stage completion
finish_stage() {
    local stage_num="$1"
    local start_time="${STAGE_START_TIMES[$stage_num]}"
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    STAGE_DURATIONS[$stage_num]=$duration
    echo "Stage $stage_num completed in ${duration}s"
}

# ---------------------------------------------------------------------------
# Stage 0: Environment setup
# ---------------------------------------------------------------------------
print_stage 0 "Environment setup"

echo "Working directory: $RTDETR_DIR"
echo "Data directory:    $DATA_DIR"
echo ""

cd "$RTDETR_DIR"

# Run existing setup script
echo "Running runpod_setup.sh..."
bash tools/runpod_setup.sh --data-dir "$DATA_DIR"

# Install ultralytics for YOLOv8 baseline (AGPL - research only)
echo ""
echo "Installing ultralytics (AGPL - research only)..."
pip install ultralytics --quiet
echo "ultralytics installed"

finish_stage 0

# ---------------------------------------------------------------------------
# Stage 1: Re-stage data to single-class
# ---------------------------------------------------------------------------
if [[ "$SKIP_RESTAGE" == "false" ]]; then
    print_stage 1 "Re-stage data to single-class"

    echo "Converting 7-class annotations to single-class..."
    echo "Creating 20% test split from validation set..."
    bash tools/restage_single_class.sh --data-dir "$DATA_DIR" --test-pct 20

    finish_stage 1
else
    echo ""
    echo "[Stage 1 SKIPPED] Data re-staging"
fi

# ---------------------------------------------------------------------------
# Stage 2: Train D-FINE
# ---------------------------------------------------------------------------
if [[ "$SKIP_DFINE" == "false" ]]; then
    print_stage 2 "Train D-FINE HGNetv2-X"

    echo "Model:      D-FINE HGNetv2-X"
    echo "Config:     configs/dfine/dfine_hgnetv2_x_agar.yml"
    echo "Pretrained: pretrain/dfine_hgnetv2_x_coco.pth"
    echo "Epochs:     42"
    echo "Batch size: 16 total (4 per GPU on 4x A100)"
    echo "Resolution: 1024x1024"
    echo ""
    echo "Estimated time: 3-6 hours on 4x A100 with ~5k images at 1024px"
    echo ""

    DFINE_START=$(date +%s)

    # Check for existing checkpoint
    CHECKPOINT_PATH="outputs/dfine_hgnetv2_x_agar_1cls/checkpoint.pth"
    if [[ -f "$CHECKPOINT_PATH" ]]; then
        echo "Found existing checkpoint: $CHECKPOINT_PATH"
        echo "Resuming from checkpoint..."
        torchrun --nproc_per_node=4 train.py \
            -c configs/dfine/dfine_hgnetv2_x_agar.yml \
            -r "$CHECKPOINT_PATH"
    else
        echo "Starting from COCO pretrained weights..."
        torchrun --nproc_per_node=4 train.py \
            -c configs/dfine/dfine_hgnetv2_x_agar.yml \
            -t pretrain/dfine_hgnetv2_x_coco.pth
    fi

    DFINE_END=$(date +%s)
    DFINE_DURATION=$((DFINE_END - DFINE_START))
    echo ""
    echo "D-FINE training completed in ${DFINE_DURATION}s ($((DFINE_DURATION / 60)) minutes)"

    # Run D-FINE test-only evaluation to get predictions
    echo ""
    echo "Running D-FINE evaluation on test set..."

    # Check which checkpoint exists (best.pth is primary, checkpoint.pth is fallback)
    BEST_CHECKPOINT="outputs/dfine_hgnetv2_x_agar_1cls/best.pth"
    LATEST_CHECKPOINT="outputs/dfine_hgnetv2_x_agar_1cls/checkpoint.pth"

    if [[ -f "$BEST_CHECKPOINT" ]]; then
        DFINE_WEIGHTS="$BEST_CHECKPOINT"
        echo "Using best checkpoint: $BEST_CHECKPOINT"
    elif [[ -f "$LATEST_CHECKPOINT" ]]; then
        DFINE_WEIGHTS="$LATEST_CHECKPOINT"
        echo "Using latest checkpoint: $LATEST_CHECKPOINT"
    else
        echo "ERROR: No checkpoint found at outputs/dfine_hgnetv2_x_agar_1cls/"
        exit 1
    fi

    python train.py --test-only \
        -c configs/dfine/dfine_hgnetv2_x_agar.yml \
        -r "$DFINE_WEIGHTS"

    # D-FINE framework saves predictions during test-only run
    # The path is typically outputs/dfine_hgnetv2_x_agar_1cls/results_test.json
    DFINE_PREDS="outputs/dfine_hgnetv2_x_agar_1cls/results_test.json"
    if [[ ! -f "$DFINE_PREDS" ]]; then
        # Fallback: check alternative paths
        DFINE_PREDS="outputs/dfine_hgnetv2_x_agar_1cls/coco_instances_results.json"
    fi

    finish_stage 2
else
    echo ""
    echo "[Stage 2 SKIPPED] D-FINE training"

    # Still need to locate predictions for evaluation
    BEST_CHECKPOINT="outputs/dfine_hgnetv2_x_agar_1cls/best.pth"
    LATEST_CHECKPOINT="outputs/dfine_hgnetv2_x_agar_1cls/checkpoint.pth"

    if [[ -f "$BEST_CHECKPOINT" ]]; then
        DFINE_WEIGHTS="$BEST_CHECKPOINT"
    elif [[ -f "$LATEST_CHECKPOINT" ]]; then
        DFINE_WEIGHTS="$LATEST_CHECKPOINT"
    else
        echo "ERROR: No checkpoint found at outputs/dfine_hgnetv2_x_agar_1cls/"
        exit 1
    fi

    DFINE_PREDS="outputs/dfine_hgnetv2_x_agar_1cls/results_test.json"
fi

# ---------------------------------------------------------------------------
# Stage 3: Train YOLOv8
# ---------------------------------------------------------------------------
if [[ "$SKIP_YOLO" == "false" ]]; then
    print_stage 3 "Train YOLOv8-X Baseline"

    echo "Model:      YOLOv8-X (AGPL - research only)"
    echo "Data:       data/agar (single-class COCO)"
    echo "Epochs:     50"
    echo "Batch size: 16"
    echo "Resolution: 1024x1024"
    echo "Devices:    0,1,2,3 (4x A100)"
    echo ""

    YOLO_START=$(date +%s)

    python tools/train_yolov8_baseline.py \
        --data-dir data/agar \
        --single-class \
        --imgsz 1024 \
        --epochs 50 \
        --batch 16 \
        --device 0,1,2,3

    YOLO_END=$(date +%s)
    YOLO_DURATION=$((YOLO_END - YOLO_START))
    echo ""
    echo "YOLOv8 training completed in ${YOLO_DURATION}s ($((YOLO_DURATION / 60)) minutes)"

    # Run YOLOv8 validation to get predictions
    echo ""
    echo "Running YOLOv8 evaluation on test set..."

    # YOLOv8 saves predictions during validation
    # The path is typically outputs/yolov8x_agar_1cls/predictions.json
    YOLO_PREDS="outputs/yolov8x_agar_1cls/predictions.json"

    finish_stage 3
else
    echo ""
    echo "[Stage 3 SKIPPED] YOLOv8 training"
    YOLO_PREDS="outputs/yolov8x_agar_1cls/predictions.json"
fi

# ---------------------------------------------------------------------------
# Stage 4: Run count-accuracy evaluation
# ---------------------------------------------------------------------------
print_stage 4 "Count-accuracy evaluation"

echo "Evaluation metric: COUNT ACCURACY (not mAP)"
echo "Primary metric:    Count within-5% accuracy"
echo "Success criteria:  D-FINE within-5% > 90% (user threshold)"
echo ""

# Ground truth test annotations
GT_ANNOTATIONS="data/agar/annotations/instances_test.json"

if [[ ! -f "$GT_ANNOTATIONS" ]]; then
    echo "ERROR: Test annotations not found: $GT_ANNOTATIONS"
    echo "Did Stage 1 (re-staging) create the test split?"
    exit 1
fi

# Prepare output directory
EVAL_OUTPUT_DIR="outputs/evaluation"
mkdir -p "$EVAL_OUTPUT_DIR"

# Check if we have both model predictions for comparison
if [[ -f "$DFINE_PREDS" && -f "$YOLO_PREDS" ]]; then
    echo "Running head-to-head comparison: D-FINE vs YOLOv8"
    echo "  D-FINE predictions: $DFINE_PREDS"
    echo "  YOLOv8 predictions: $YOLO_PREDS"
    echo ""

    python tools/evaluate_count_accuracy.py \
        --gt-annotations "$GT_ANNOTATIONS" \
        --pred-annotations "$DFINE_PREDS" \
        --model-name "D-FINE HGNetv2-X" \
        --compare-with "$YOLO_PREDS" \
        --output-dir "$EVAL_OUTPUT_DIR" \
        --checkpoint "$DFINE_WEIGHTS" \
        --config configs/dfine/dfine_hgnetv2_x_agar.yml

elif [[ -f "$DFINE_PREDS" ]]; then
    echo "Running D-FINE evaluation only"
    echo "  D-FINE predictions: $DFINE_PREDS"
    echo ""

    python tools/evaluate_count_accuracy.py \
        --gt-annotations "$GT_ANNOTATIONS" \
        --pred-annotations "$DFINE_PREDS" \
        --model-name "D-FINE HGNetv2-X" \
        --output-dir "$EVAL_OUTPUT_DIR" \
        --checkpoint "$DFINE_WEIGHTS" \
        --config configs/dfine/dfine_hgnetv2_x_agar.yml
else
    echo "ERROR: No predictions found for evaluation"
    echo "  D-FINE predictions: $DFINE_PREDS (not found)"
    echo "  YOLOv8 predictions: $YOLO_PREDS (not found)"
    exit 1
fi

echo ""
echo "Full evaluation report saved to: $EVAL_OUTPUT_DIR/"

finish_stage 4

# ---------------------------------------------------------------------------
# Stage 5: Summary
# ---------------------------------------------------------------------------
print_stage 5 "Summary"

echo "Timing breakdown:"
echo "  Stage 0 (Setup):      ${STAGE_DURATIONS[0]}s"
if [[ "$SKIP_RESTAGE" == "false" ]]; then
    echo "  Stage 1 (Re-stage):   ${STAGE_DURATIONS[1]}s"
fi
if [[ "$SKIP_DFINE" == "false" ]]; then
    echo "  Stage 2 (D-FINE):     ${STAGE_DURATIONS[2]}s ($((STAGE_DURATIONS[2] / 60)) minutes)"
fi
if [[ "$SKIP_YOLO" == "false" ]]; then
    echo "  Stage 3 (YOLOv8):     ${STAGE_DURATIONS[3]}s ($((STAGE_DURATIONS[3] / 60)) minutes)"
fi
echo "  Stage 4 (Evaluation): ${STAGE_DURATIONS[4]}s"

# Calculate total time
TOTAL_TIME=0
for duration in "${STAGE_DURATIONS[@]}"; do
    TOTAL_TIME=$((TOTAL_TIME + duration))
done
echo ""
echo "Total time: ${TOTAL_TIME}s ($((TOTAL_TIME / 60)) minutes)"
echo ""

# Parse evaluation results to determine pass/fail
EVAL_REPORT="$EVAL_OUTPUT_DIR/evaluation_report.json"
if [[ -f "$EVAL_REPORT" ]]; then
    # Extract count within-5% accuracy for D-FINE
    WITHIN_5_PCT=$(python3 -c "
import json
with open('$EVAL_REPORT') as f:
    data = json.load(f)
    # Handle different JSON structures
    if 'count_metrics' in data:
        print(data['count_metrics'].get('within_5_pct', 0))
    elif 'within_5_pct' in data:
        print(data['within_5_pct'])
    else:
        print(0)
" 2>/dev/null || echo "0")

    echo "D-FINE count within-5% accuracy: ${WITHIN_5_PCT}%"
    echo ""

    # Check against threshold (90% for user, stricter than YOLOv8's 88.73%)
    THRESHOLD=90
    if (( $(echo "$WITHIN_5_PCT >= $THRESHOLD" | bc -l) )); then
        echo "=============================================="
        echo "VERDICT: PASS"
        echo "=============================================="
        echo "D-FINE meets success criteria (within-5% > ${THRESHOLD}%)"
        echo ""
        echo "Phase 1 complete. Proceed to Phase 2."
    else
        echo "=============================================="
        echo "VERDICT: FAIL"
        echo "=============================================="
        echo "D-FINE does not meet success criteria (within-5% <= ${THRESHOLD}%)"
        echo ""
        echo "Options:"
        echo "  1. Iterate on training (increase epochs, adjust batch size)"
        echo "  2. Try different backbone freezing strategy"
        echo "  3. Re-evaluate the 90% threshold"
    fi
else
    echo "WARNING: Could not parse evaluation report: $EVAL_REPORT"
    echo "Check the report manually to determine pass/fail."
fi

echo ""
echo "Full evaluation report: $EVAL_OUTPUT_DIR/"
echo "  - evaluation_report.json (machine-readable)"
echo "  - evaluation_report.txt (human-readable)"
echo ""

finish_stage 5

echo ""
echo "=============================================="
echo "ALL STAGES COMPLETE"
echo "=============================================="
echo ""
