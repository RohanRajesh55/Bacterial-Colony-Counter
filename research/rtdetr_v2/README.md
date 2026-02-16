# RT-DETR Fine-Tuning for Colony Detection

Fine-tune the RT-DETR (Real-Time Detection Transformer) model on the AGAR dataset for bacterial colony detection and classification.

**IMPORTANT: Research Use Only**

Models trained with this code are for RESEARCH USE ONLY due to the CC BY-NC 2.0 license of the AGAR dataset. For commercial deployment, train on a commercially-licensed dataset (e.g., the Veterinary dataset with CC BY 4.0 license).

---

## Quick Start

### Local Training (with GPU)

```bash
# Install dependencies
pip install -r rtdetr/requirements.txt

# Start training
python rtdetr/train.py --config rtdetr/config.yaml
```

### RunPod Training (Recommended)

See **[RUNPOD_GUIDE.md](./RUNPOD_GUIDE.md)** for detailed instructions on:
- Starting/stopping/terminating pods
- Downloading data from Google Drive
- Cost management tips

Quick start:
1. Launch a RunPod instance with the PyTorch template
2. Select GPU: **RTX A40** (48GB VRAM, ~$0.39/hr) - recommended
3. Clone repository and upload dataset
4. Run setup and training:

```bash
# Setup environment
bash rtdetr/runpod_setup.sh

# Start training
python rtdetr/train.py --config rtdetr/config.yaml
```

---

## GPU Recommendations

| GPU | VRAM | Cost/hr | Batch Size | Est. Time | Est. Cost |
|-----|------|---------|------------|-----------|-----------|
| RTX A40 | 48 GB | ~$0.39 | 4-8 | 6-8 hrs | $3-5 |
| RTX A6000 | 48 GB | ~$0.79 | 4-8 | 6-8 hrs | $5-7 |
| RTX 4090 | 24 GB | ~$0.74 | 2-4 | 8-10 hrs | $6-8 |
| A100 80GB | 80 GB | ~$1.99 | 8-16 | 4-5 hrs | $8-10 |

All options stay well under the $20 budget.

---

## Directory Structure

```
rtdetr/
    config.yaml          # Training configuration
    dataset.py           # PyTorch Dataset for AGAR
    train.py             # Training script
    test.py              # Evaluation script
    requirements.txt     # Dependencies
    runpod_setup.sh      # RunPod setup script
    README.md            # This file
    checkpoints/         # Saved models (created during training)
        checkpoint_last.pt
        checkpoint_best.pt
        best_model/      # HuggingFace format (for API)
```

---

## Training Configuration

Edit `config.yaml` to customize training. Key settings:

```yaml
# Model
model_name: PekingU/rtdetr_r101vd
num_classes: 7

# Training
batch_size: 4          # Reduce for smaller GPUs
num_epochs: 30
learning_rate: 1.0e-5  # Lower LR for fine-tuning

# Memory optimization
mixed_precision: true  # FP16 training
gradient_checkpointing: false  # Enable if OOM

# Augmentation
augmentation:
  image_size: 640
  horizontal_flip: 0.5
  vertical_flip: 0.5
```

---

## Usage

### Training

```bash
# Default training (uses config.yaml)
python rtdetr/train.py --config rtdetr/config.yaml

# Override settings via CLI
python rtdetr/train.py --config rtdetr/config.yaml \
    --batch_size 2 \
    --epochs 50 \
    --lr 5e-6

# Resume from checkpoint
# Edit config.yaml: resume_from: rtdetr/checkpoints/checkpoint_last.pt
python rtdetr/train.py --config rtdetr/config.yaml
```

### Evaluation

```bash
# Evaluate best checkpoint
python rtdetr/test.py --checkpoint rtdetr/checkpoints/best_model

# With visualizations
python rtdetr/test.py --checkpoint rtdetr/checkpoints/best_model \
    --visualize \
    --num_visualizations 50

# Custom confidence threshold
python rtdetr/test.py --checkpoint rtdetr/checkpoints/best_model \
    --confidence_threshold 0.3
```

### Using Trained Model in API

After training, the model is saved in HuggingFace format at `rtdetr/checkpoints/best_model/`. To use it in the API:

```python
# In api/services/rtdetr_service.py
service = RTDetrService(model_path="rtdetr/checkpoints/best_model")
```

---

## Expected Results

### Target Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| mAP@0.5 | > 0.50 | Primary detection metric |
| mAP@0.5:0.95 | > 0.35 | Stricter IoU threshold |
| Count Exact Match | > 60% | Exact colony count |
| Count Within 5% | > 80% | Practical accuracy |

### YOLO Baseline (for comparison)

| Metric | YOLOv8 Score |
|--------|--------------|
| mAP@0.5:0.95 | 0.622 |
| Precision | 0.981 |
| Recall | 0.966 |
| Count Exact | 69.49% |
| Count Within 5% | 88.73% |

RT-DETR should achieve competitive or better results due to its transformer architecture.

---

## Training Tips

### Memory Issues (OOM)

If you run out of GPU memory:

1. **Reduce batch size**: `--batch_size 2`
2. **Enable gradient checkpointing**: Set `gradient_checkpointing: true` in config
3. **Reduce image size**: Set `augmentation.image_size: 480`

### Slow Training

If training is too slow:

1. **Increase batch size** (if VRAM allows)
2. **Reduce validation frequency**: Set `val_every: 2`
3. **Reduce logging frequency**: Set `log_every: 100`

### Poor Convergence

If loss doesn't decrease:

1. **Lower learning rate**: `--lr 5e-6`
2. **Increase warmup**: Set `warmup_epochs: 5`
3. **Check data augmentation**: Ensure images load correctly

---

## Files Generated

After training:

| File | Description |
|------|-------------|
| `checkpoints/checkpoint_last.pt` | Latest checkpoint (for resume) |
| `checkpoints/checkpoint_best.pt` | Best validation loss |
| `checkpoints/best_model/` | HuggingFace format model |
| `checkpoints/config.yaml` | Config used for training |
| `checkpoints/training_history.json` | Training statistics |

After evaluation:

| File | Description |
|------|-------------|
| `results/evaluation_results.json` | All metrics |
| `results/visualizations/` | Annotated images (if --visualize) |

---

## Troubleshooting

### "CUDA out of memory"

```bash
# Reduce batch size
python rtdetr/train.py --batch_size 2

# Or enable gradient checkpointing in config.yaml:
# gradient_checkpointing: true
```

### "No module named 'transformers'"

```bash
pip install transformers>=4.50.0
```

### "RTDetrForObjectDetection not found"

Your transformers version is too old. Update:

```bash
pip install --upgrade transformers
```

### "Dataset not found"

Ensure the AGAR dataset is in the correct location:

```
dataset/
    images/          # {id}.jpg files
    annotations/     # {id}.json files
    training_lists/  # higher_resolution_train.txt, etc.
```

---

## License

- **Training code**: Part of CFU-Counter project
- **RT-DETR model**: Apache 2.0 (commercial use allowed)
- **AGAR dataset**: CC BY-NC 2.0 (research only)
- **Trained weights**: Research use only (due to AGAR dataset)

For commercial deployment, fine-tune on a CC BY 4.0 licensed dataset.
