# Multi-Task CNN for Colony Counting & Classification

A custom CNN that performs both **colony counting** (regression) and **species classification** simultaneously using a shared feature extractor with dual task-specific heads.

## Files

| File                       | Description                                                      |
| -------------------------- | ---------------------------------------------------------------- |
| `cnn_train.py`             | Full training pipeline with augmentation, logging, checkpointing |
| `cnn_test.py`              | Evaluation script with visual result generation                  |
| `architecture_and_flow.md` | Detailed architecture documentation                              |

## Architecture

```
Input Image (224×224×3)
        │
        ▼
┌───────────────────┐
│  8 Conv Blocks    │  Shared feature extractor
│  (32→512 filters) │  BatchNorm + ReLU + MaxPool
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Global Avg Pool  │
│  + Shared FC      │  512-dim feature vector
└───────────────────┘
        │
   ┌────┴────┐
   ▼         ▼
┌─────┐   ┌─────┐
│Count│   │Class│   Dual heads
│Head │   │Head │
└─────┘   └─────┘
   │         │
   ▼         ▼
Colony    Species
Count     (7 classes)
```

## Quick Start

### Training

```bash
# Train with defaults
python cnn_train.py

# Custom parameters
python cnn_train.py --epochs 100 --batch_size 64 --lr 0.0005 --image_size 224 224

# Resume or adjust paths
python cnn_train.py --dataset_dir /path/to/dataset --results_dir ./my_results
```

### Evaluation

```bash
python cnn_test.py --results_dir results_refactored
```

## Dataset Format

Expected directory structure:

```
dataset/
├── images/
│   ├── 001.jpg
│   ├── 002.jpg
│   └── ...
├── annotations/
│   ├── 001.json
│   ├── 002.json
│   └── ...
└── training_lists/
    ├── species1_train.txt
    ├── species1_val.txt
    └── ...
```

### Annotation JSON Format

```json
{
  "colonies_number": 42,
  "labels": [{ "class": "E.coli", "x": 100, "y": 150, "w": 20, "h": 20 }]
}
```

## Supported Species

The model classifies 7 bacterial species:

- B.subtilis
- C.albicans
- Contamination
- Defect
- E.coli
- P.aeruginosa
- S.aureus

## Training Configuration

| Parameter           | Default | Description                          |
| ------------------- | ------- | ------------------------------------ |
| `epochs`            | 60      | Training epochs                      |
| `batch_size`        | 32      | Samples per batch                    |
| `lr`                | 1e-3    | Learning rate (OneCycleLR)           |
| `image_size`        | 224×224 | Input resolution                     |
| `dropout`           | 0.4     | Regularization                       |
| `patience_es`       | 10      | Early stopping patience              |
| `class_loss_weight` | 0.5     | Classification vs regression balance |

### Data Augmentation

Augmentations using Albumentations:

- Random rotation (±25°) and 90° flips
- Brightness/contrast adjustment, CLAHE
- Gaussian blur and noise
- Horizontal/vertical flips
- CoarseDropout (cutout-style regularization)

## Outputs

### Training

- `results_refactored/final_best_model.pth` - Best model weights
- `results_refactored/training_metadata.json` - Config, history, class list
- `results_refactored/tb/` - TensorBoard logs

### Evaluation

- `results_refactored/evaluation_images/` - Images with predictions overlaid
- Console metrics: MAE, R², classification accuracy

## Metrics

The CNN outputs:

- **MAE** (Mean Absolute Error) for counting accuracy
- **Classification Accuracy** for species identification
- **Counting Accuracy (±10)**: % of predictions within 10 colonies of ground truth

## Requirements

```
torch>=2.0.0
albumentations
opencv-python
scikit-learn
tensorboard
tqdm
numpy
```
