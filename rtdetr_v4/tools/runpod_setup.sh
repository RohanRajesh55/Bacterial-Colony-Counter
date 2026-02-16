#!/bin/bash
# RunPod GPU pod setup for RT-DETRv4 D-FINE training.
#
# Expects data on a RunPod Network Volume (staged via stage_agar_data.sh).
# Creates symlinks so the training config finds data at the expected paths.
#
# Usage:
#   git clone <repo> /workspace/CFU-counter
#   cd /workspace/CFU-counter/rtdetr_v4
#   bash tools/runpod_setup.sh --data-dir /workspace/data
#
# Then launch training:
#   torchrun --nproc_per_node=4 train.py \
#       -c configs/dfine/dfine_hgnetv2_x_agar.yml \
#       -t pretrain/dfine_hgnetv2_x_coco.pth

set -euo pipefail

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
DATA_DIR="/workspace/data"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --data-dir) DATA_DIR="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; echo "Usage: $0 [--data-dir DIR]"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RTDETR_DIR="$(dirname "$SCRIPT_DIR")"

echo "=============================================="
echo "RT-DETRv4 RunPod Setup"
echo "=============================================="
echo "  rtdetr_v4 dir:  $RTDETR_DIR"
echo "  data dir:       $DATA_DIR"

# ---------------------------------------------------------------------------
# 1. GPU verification
# ---------------------------------------------------------------------------
echo ""
echo "[1/5] Checking GPU environment..."

if ! command -v nvidia-smi &> /dev/null; then
    echo "ERROR: nvidia-smi not found. Is this a GPU pod?"
    exit 1
fi

GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l | tr -d ' ')
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | tr -d ' \n')
GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1 | tr -d ' \n')

echo "  GPUs found:    $GPU_COUNT x $GPU_NAME ($GPU_MEM each)"

# Check CUDA via PyTorch
CUDA_OK=$(python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "False")
if [[ "$CUDA_OK" != "True" ]]; then
    echo "ERROR: torch.cuda.is_available() returned False"
    echo "  PyTorch may need reinstalling with CUDA support"
    exit 1
fi

TORCH_VER=$(python3 -c "import torch; print(torch.__version__)")
CUDA_VER=$(python3 -c "import torch; print(torch.version.cuda)")
echo "  PyTorch:       $TORCH_VER (CUDA $CUDA_VER)"

# Check NCCL for multi-GPU DDP
if [[ "$GPU_COUNT" -gt 1 ]]; then
    NCCL_OK=$(python3 -c "import torch.distributed; print(torch.distributed.is_nccl_available())" 2>/dev/null || echo "False")
    if [[ "$NCCL_OK" != "True" ]]; then
        echo "WARNING: NCCL not available. Multi-GPU DDP will not work."
    else
        echo "  NCCL:          available (multi-GPU ready)"
    fi
fi

# ---------------------------------------------------------------------------
# 2. Install dependencies
# ---------------------------------------------------------------------------
echo ""
echo "[2/5] Installing dependencies..."

pip install -r "$RTDETR_DIR/requirements.txt" --quiet 2>&1 | tail -1
echo "  Dependencies installed"

# ---------------------------------------------------------------------------
# 3. Symlink data from network volume
# ---------------------------------------------------------------------------
echo ""
echo "[3/5] Linking data from network volume..."

if [[ ! -d "$DATA_DIR" ]]; then
    echo "ERROR: Data directory not found: $DATA_DIR"
    echo "  Is the network volume mounted?"
    exit 1
fi

# Symlink agar dataset
if [[ -d "$DATA_DIR/agar" ]]; then
    mkdir -p "$RTDETR_DIR/data"
    # Remove existing link/dir if present (idempotent re-runs)
    rm -rf "$RTDETR_DIR/data/agar"
    ln -s "$DATA_DIR/agar" "$RTDETR_DIR/data/agar"
    echo "  data/agar -> $DATA_DIR/agar"
else
    echo "ERROR: $DATA_DIR/agar not found on network volume"
    exit 1
fi

# Symlink pretrained weights
if [[ -d "$DATA_DIR/pretrain" ]]; then
    rm -rf "$RTDETR_DIR/pretrain"
    ln -s "$DATA_DIR/pretrain" "$RTDETR_DIR/pretrain"
    echo "  pretrain -> $DATA_DIR/pretrain"
else
    echo "ERROR: $DATA_DIR/pretrain not found on network volume"
    exit 1
fi

# ---------------------------------------------------------------------------
# 4. Validate dataset integrity
# ---------------------------------------------------------------------------
echo ""
echo "[4/5] Validating dataset..."

ERRORS=0

# Check train images
TRAIN_DIR="$RTDETR_DIR/data/agar/images/train"
if [[ -d "$TRAIN_DIR" ]]; then
    TRAIN_COUNT=$(find "$TRAIN_DIR" -name "*.jpg" | wc -l | tr -d ' ')
    echo "  Train images:  $TRAIN_COUNT"
    if [[ "$TRAIN_COUNT" -lt 5000 ]]; then
        echo "  WARNING: Expected ~5,241 train images, found $TRAIN_COUNT"
    fi
else
    echo "  ERROR: Train image directory missing: $TRAIN_DIR"
    ERRORS=$((ERRORS + 1))
fi

# Check val images
VAL_DIR="$RTDETR_DIR/data/agar/images/val"
if [[ -d "$VAL_DIR" ]]; then
    VAL_COUNT=$(find "$VAL_DIR" -name "*.jpg" | wc -l | tr -d ' ')
    echo "  Val images:    $VAL_COUNT"
    if [[ "$VAL_COUNT" -lt 1500 ]]; then
        echo "  WARNING: Expected ~1,747 val images, found $VAL_COUNT"
    fi
else
    echo "  ERROR: Val image directory missing: $VAL_DIR"
    ERRORS=$((ERRORS + 1))
fi

# Check annotations
for ann in "instances_train.json" "instances_val.json"; do
    ANN_PATH="$RTDETR_DIR/data/agar/annotations/$ann"
    if [[ -f "$ANN_PATH" ]]; then
        ANN_SIZE=$(du -h "$ANN_PATH" | cut -f1)
        echo "  $ann: $ANN_SIZE"
    else
        echo "  ERROR: Missing annotation: $ANN_PATH"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check pretrained weights
WEIGHTS_PATH="$RTDETR_DIR/pretrain/dfine_hgnetv2_x_coco.pth"
if [[ -f "$WEIGHTS_PATH" ]]; then
    W_SIZE=$(du -h "$WEIGHTS_PATH" | cut -f1)
    echo "  Pretrained weights: $W_SIZE"
else
    echo "  ERROR: Missing weights: $WEIGHTS_PATH"
    ERRORS=$((ERRORS + 1))
fi

if [[ "$ERRORS" -gt 0 ]]; then
    echo ""
    echo "ERROR: $ERRORS validation errors found. Fix before training."
    exit 1
fi

# ---------------------------------------------------------------------------
# 5. Print training command
# ---------------------------------------------------------------------------
echo ""
echo "[5/5] Environment ready"

# Estimate VRAM usage
echo ""
echo "Estimated VRAM per GPU:"
echo "  Model (D-FINE X):         ~2 GB"
echo "  Batch (1024px, 2/GPU):    ~30 GB"
echo "  AMP overhead:             ~5 GB"
echo "  Total:                    ~37 GB (fits 80 GB A100)"

echo ""
echo "=============================================="
echo "All checks passed -- ready to train"
echo "=============================================="

if [[ "$GPU_COUNT" -gt 1 ]]; then
    echo ""
    echo "Multi-GPU training ($GPU_COUNT GPUs):"
    echo "  torchrun --nproc_per_node=$GPU_COUNT train.py \\"
    echo "      -c configs/dfine/dfine_hgnetv2_x_agar.yml \\"
    echo "      -t pretrain/dfine_hgnetv2_x_coco.pth"
else
    echo ""
    echo "Single-GPU training:"
    echo "  python train.py \\"
    echo "      -c configs/dfine/dfine_hgnetv2_x_agar.yml \\"
    echo "      -t pretrain/dfine_hgnetv2_x_coco.pth"
fi

echo ""
echo "Monitor with TensorBoard:"
echo "  tensorboard --logdir outputs/dfine_hgnetv2_x_agar --port 6006"
echo ""
echo "Resume from checkpoint:"
echo "  Add -r outputs/dfine_hgnetv2_x_agar/checkpoint.pth to the command above"
echo ""
