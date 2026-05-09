# YOLO Colony Detection

YOLOv8-based bacterial colony detection with anti-overfitting defaults optimized for real-world petri dish images.

## Files

| File                           | Description                                             |
| ------------------------------ | ------------------------------------------------------- |
| `yolo_train.py`                | Training script with built-in anti-overfitting defaults |
| `yolo_test.py`                 | Evaluation and visualization report generator           |
| `data.yaml`                    | Dataset configuration (paths, classes)                  |
| `preprocess.py`                | Image preprocessing utilities                           |
| `preprocessing_pipeline.ipynb` | Interactive preprocessing notebook                      |
| `architecture_and_flow.md`     | Detailed architecture documentation                     |

## Quick Start

### Training

```bash
# Basic training with defaults
python yolo_train.py --config data.yaml

# Custom hyperparameters
python yolo_train.py --config data.yaml --epochs 50 --patience 15 --imgsz 1024 --batch 8
```

### Evaluation

Edit the configuration in `yolo_test.py`:

```python
WEIGHTS_PATH = "runs/colony_yolo/weights/best.pt"
DATA_YAML_PATH = "data.yaml"
SOURCE_PATH = "/path/to/images/val"
LABELS_PATH = "/path/to/labels/val"
```

Then run:

```bash
python yolo_test.py
```

## Training Configuration

The training script includes optimized defaults for bacterial colony detection:

| Parameter   | Default | Description                              |
| ----------- | ------- | ---------------------------------------- |
| `epochs`    | 100     | Maximum training epochs                  |
| `patience`  | 20      | Early stopping patience                  |
| `imgsz`     | 1024    | Image size (high-res for small colonies) |
| `batch`     | 16      | Batch size                               |
| `optimizer` | AdamW   | Optimizer with weight decay              |
| `lr0`       | 0.001   | Initial learning rate                    |
| `dropout`   | 0.1     | Dropout regularization                   |

### Data Augmentation

Built-in augmentations to prevent overfitting:

- **Color**: HSV jitter (h=0.015, s=0.5, v=0.4)
- **Geometric**: Rotation (±15°), translation, scale, shear
- **Flips**: Horizontal/vertical (50% each)
- **Advanced**: Mosaic, MixUp (15%), Copy-Paste (10%)

### Configuration Priority

Settings are merged in order: **Defaults → YAML → CLI arguments**

## Outputs

### Training

- `runs/detect/train/weights/best.pt` - Best model weights
- `runs/detect/train/results.png` - Training curves

### Evaluation

- `runs/full_validation_report/annotated_images/` - Visualized predictions
- `runs/full_validation_report/detection_summary.csv` - Per-image results
- `runs/full_validation_report/metrics_and_plots/` - mAP, precision, recall

## Model Performance

The YOLOv8m model achieves:

- **mAP@50**: ~0.85+
- **Inference**: ~15ms per 1024×1024 image (GPU)
- **Colony detection**: Works for dense and sparse plates

## Requirements

```
ultralytics>=8.0.0
torch>=2.0.0
pyyaml
pillow
pandas
tqdm
numpy
```
