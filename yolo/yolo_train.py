#!/usr/bin/env python3
"""
yolo_train.py

Enhanced YOLOv8 training script with built-in anti-overfitting defaults
and support for real-world bacterial colony detection.

Usage:
    python yolo_train.py --config data.yaml
    python yolo_train.py --config data.yaml --epochs 50 --patience 15
"""

import argparse
import yaml
import logging
import sys
from pathlib import Path
from ultralytics import YOLO

# Professional logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Dataset-specific keys (not training arguments)
DATASET_KEYS = ['path', 'train', 'val', 'test', 'nc', 'names']

# Recommended defaults for bacterial colony detection with anti-overfitting
RECOMMENDED_DEFAULTS = {
    # Training
    "epochs": 100,
    "patience": 20,           # Early stopping
    "imgsz": 1024,
    "batch": 16,
    
    # Optimizer with regularization
    "optimizer": "AdamW",
    "lr0": 0.001,
    "lrf": 0.01,              # Final LR = lr0 * lrf
    "cos_lr": True,           # Cosine annealing
    "weight_decay": 0.0005,   # L2 regularization
    "warmup_epochs": 3,       # Gradual warmup
    
    # Augmentation (anti-overfitting)
    "hsv_h": 0.015,
    "hsv_s": 0.5,
    "hsv_v": 0.4,
    "degrees": 15.0,
    "translate": 0.1,
    "scale": 0.4,
    "shear": 2.0,
    "flipud": 0.5,
    "fliplr": 0.5,
    "mosaic": 1.0,
    "mixup": 0.15,
    "copy_paste": 0.1,
    "close_mosaic": 10,       # Disable mosaic last 10 epochs for fine-tuning
    
    # Regularization
    "dropout": 0.1,
    "label_smoothing": 0.05,
    
    # Performance
    "amp": True,
    "cache": True,
    "workers": 8,
    
    # Validation
    "plots": True,
    "iou": 0.5,
    "val": True,
}


def merge_configs(yaml_config: dict, cli_overrides: dict) -> dict:
    """
    Merges configurations with priority: CLI > YAML > Defaults.
    """
    # Start with defaults
    final_config = RECOMMENDED_DEFAULTS.copy()
    
    # Override with YAML values
    for key, value in yaml_config.items():
        if key not in DATASET_KEYS:
            final_config[key] = value
    
    # Override with CLI arguments (skip None values)
    for key, value in cli_overrides.items():
        if value is not None:
            final_config[key] = value
    
    return final_config


def train_model(config_path: str, cli_overrides: dict):
    """
    Loads configuration and trains a YOLOv8 model with robust defaults.
    """
    # 1. Load YAML configuration
    try:
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
    except Exception as e:
        logger.error(f"Error loading YAML file: {e}")
        return

    # 2. Merge configurations
    train_args = merge_configs(yaml_config, cli_overrides)
    
    # 3. Initialize model
    model_name = yaml_config.get('model', 'yolov8m.pt')
    try:
        model = YOLO(model_name)
        logger.info(f"Model '{model_name}' loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return

    # 4. Log effective configuration
    logger.info("=" * 50)
    logger.info("Effective Training Configuration (after merging):")
    logger.info("=" * 50)
    for key, value in sorted(train_args.items()):
        logger.info(f"  {key}: {value}")
    logger.info("=" * 50)

    # 5. Start training
    logger.info("Starting model training...")
    try:
        results = model.train(data=config_path, **train_args)
        logger.info("Training completed successfully!")
        
        # Log final metrics
        if hasattr(results, 'results_dict'):
            logger.info("Final Metrics:")
            for metric, value in results.results_dict.items():
                logger.info(f"  {metric}: {value}")
                
    except Exception as e:
        logger.error(f"Error during training: {e}", exc_info=True)


def main():
    parser = argparse.ArgumentParser(
        description="Train YOLOv8 for bacterial colony detection with anti-overfitting defaults."
    )
    
    # Required
    parser.add_argument("--config", type=str, required=True, help="Path to data.yaml")
    
    # CLI overrides for common hyperparameters
    parser.add_argument("--epochs", type=int, help="Number of training epochs")
    parser.add_argument("--patience", type=int, help="Early stopping patience")
    parser.add_argument("--batch", type=int, help="Batch size")
    parser.add_argument("--imgsz", type=int, help="Image size")
    parser.add_argument("--device", type=str, help="Device (e.g., '0' or 'cpu')")
    parser.add_argument("--lr0", type=float, help="Initial learning rate")
    parser.add_argument("--weight_decay", type=float, help="Weight decay (L2 regularization)")
    parser.add_argument("--dropout", type=float, help="Dropout rate")
    parser.add_argument("--mosaic", type=float, help="Mosaic augmentation probability")
    parser.add_argument("--mixup", type=float, help="MixUp augmentation probability")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--workers", type=int, help="Number of data loader workers")
    
    args = parser.parse_args()
    
    # Validate config file
    config_file = Path(args.config)
    if not config_file.is_file():
        logger.error(f"Config file not found: {args.config}")
        return
    
    # Build CLI overrides dict
    cli_overrides = {
        "epochs": args.epochs,
        "patience": args.patience,
        "batch": args.batch,
        "imgsz": args.imgsz,
        "device": args.device,
        "lr0": args.lr0,
        "weight_decay": args.weight_decay,
        "dropout": args.dropout,
        "mosaic": args.mosaic,
        "mixup": args.mixup,
        "resume": args.resume if args.resume else None,
        "workers": args.workers,
    }
    
    train_model(args.config, cli_overrides)


if __name__ == "__main__":
    main()