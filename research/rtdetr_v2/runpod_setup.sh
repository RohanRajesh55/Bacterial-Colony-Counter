#!/bin/bash
# RunPod Setup Script for RT-DETR Fine-Tuning
#
# This script sets up the training environment on a RunPod GPU instance.
#
# Recommended GPU: RTX A40 (48GB VRAM, ~$0.39/hr)
# Estimated training time: 6-8 hours
# Estimated cost: $3-5 (well under $20 budget)
#
# Usage:
#   1. Launch a RunPod instance with PyTorch template
#   2. Clone the repository
#   3. Run this script: bash rtdetr_v2/runpod_setup.sh
#   4. Start training: python rtdetr_v2/train.py --config rtdetr_v2/config.yaml

set -e  # Exit on error

echo "=============================================="
echo "RT-DETR Fine-Tuning Setup for RunPod"
echo "=============================================="

# Check GPU availability
echo ""
echo "Checking GPU..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
    echo "CUDA available: $(python -c 'import torch; print(torch.cuda.is_available())')"
else
    echo "WARNING: nvidia-smi not found. GPU may not be available."
fi

# Install CUDA-enabled PyTorch if not already installed
echo ""
echo "Installing PyTorch with CUDA support..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 --quiet

# Install training dependencies
echo ""
echo "Installing training dependencies..."
pip install -r rtdetr_v2/requirements.txt --quiet

# Verify transformers version
echo ""
echo "Verifying HuggingFace Transformers..."
python -c "from transformers import RTDetrForObjectDetection, RTDetrImageProcessor; print('RT-DETR imports OK')"

# Check dataset availability
echo ""
echo "Checking dataset..."
if [ -d "dataset/images" ] && [ -d "dataset/annotations" ]; then
    echo "Dataset directory found"
    echo "  Images: $(ls dataset/images/*.jpg 2>/dev/null | wc -l) files"
    echo "  Annotations: $(ls dataset/annotations/*.json 2>/dev/null | wc -l) files"
else
    echo "WARNING: Dataset directory not found!"
    echo "Please ensure the AGAR dataset is available at:"
    echo "  dataset/images/"
    echo "  dataset/annotations/"
    echo "  dataset/training_lists/"
fi

# Check training lists
if [ -f "dataset/training_lists/higher_resolution_train.txt" ]; then
    TRAIN_COUNT=$(wc -l < dataset/training_lists/higher_resolution_train.txt)
    VAL_COUNT=$(wc -l < dataset/training_lists/higher_resolution_val.txt)
    echo "  Training samples: $TRAIN_COUNT"
    echo "  Validation samples: $VAL_COUNT"
fi

# Create output directory
echo ""
echo "Creating output directory..."
mkdir -p rtdetr_v2/checkpoints

# Pre-download the model to cache it
echo ""
echo "Pre-downloading RT-DETR model weights (this may take a minute)..."
python -c "
from transformers import RTDetrForObjectDetection, RTDetrImageProcessor
print('Downloading model...')
processor = RTDetrImageProcessor.from_pretrained('PekingU/rtdetr_r101vd')
model = RTDetrForObjectDetection.from_pretrained('PekingU/rtdetr_r101vd')
print('Model cached successfully')
"

# Print memory usage
echo ""
echo "GPU Memory Status:"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=memory.used,memory.free,memory.total --format=csv
fi

# Print training command
echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "To start training, run:"
echo ""
echo "  python rtdetr_v2/train.py --config rtdetr_v2/config.yaml"
echo ""
echo "For A40 (48GB VRAM), recommended settings:"
echo "  --batch_size 4 (default in config)"
echo ""
echo "For RTX 4090 (24GB VRAM), reduce batch size:"
echo "  --batch_size 2"
echo ""
echo "To monitor training progress:"
echo "  tail -f rtdetr_v2/checkpoints/training.log"
echo ""
echo "To resume from checkpoint:"
echo "  Edit config.yaml and set resume_from: rtdetr_v2/checkpoints/checkpoint_last.pt"
echo ""
echo "Estimated training time: 6-8 hours (30 epochs)"
echo "=============================================="
