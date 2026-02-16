"""
RT-DETR Fine-Tuning Script for Colony Detection.

Fine-tunes a pre-trained RT-DETR model on the AGAR dataset for
bacterial colony detection and classification.

IMPORTANT: This script produces models for RESEARCH USE ONLY
due to the CC BY-NC 2.0 license of the AGAR dataset.

Usage:
    python train.py --config config.yaml
    python train.py --config config.yaml --batch_size 2 --device mps
"""

import argparse
import json
import logging
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
import yaml
from torch.cuda.amp import GradScaler, autocast
from tqdm import tqdm
from transformers import RTDetrForObjectDetection, RTDetrImageProcessor

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rtdetr_v2.dataset import collate_fn, create_dataloaders

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def detect_device(requested: str = "cuda") -> str:
    """Detect the best available device.

    Args:
        requested: Requested device (cuda, mps, cpu)

    Returns:
        Device string that is actually available
    """
    if requested == "cuda" and torch.cuda.is_available():
        device = "cuda"
        logger.info(f"Using CUDA GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    elif requested == "mps" and torch.backends.mps.is_available():
        device = "mps"
        logger.info("Using Apple Silicon MPS")
    else:
        device = "cpu"
        logger.info("Using CPU (training will be slow)")

    return device


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml

    Returns:
        Configuration dictionary
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config


def create_model(config: dict, device: str) -> RTDetrForObjectDetection:
    """Create and configure RT-DETR model for fine-tuning.

    Loads pre-trained weights and replaces the classification head
    for the target number of classes.

    Args:
        config: Configuration dictionary
        device: Target device

    Returns:
        Configured model ready for training
    """
    num_classes = config["num_classes"]
    model_name = config["model_name"]

    logger.info(f"Loading pre-trained model: {model_name}")

    # Load pre-trained model with new number of classes
    # This automatically replaces the classification head
    model = RTDetrForObjectDetection.from_pretrained(
        model_name,
        num_labels=num_classes,
        ignore_mismatched_sizes=True,  # Allow head replacement
    )

    # Enable gradient checkpointing if requested (saves memory)
    if config.get("gradient_checkpointing", False):
        model.gradient_checkpointing_enable()
        logger.info("Gradient checkpointing enabled")

    model = model.to(device)

    # Log model info
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Total parameters: {total_params:,}")
    logger.info(f"Trainable parameters: {trainable_params:,}")

    return model


def get_optimizer(model: torch.nn.Module, config: dict) -> torch.optim.Optimizer:
    """Create optimizer with layer-specific learning rates.

    Uses lower learning rate for backbone (pre-trained) and higher
    for the detection head (randomly initialized).

    Args:
        model: RT-DETR model
        config: Configuration dictionary

    Returns:
        Configured AdamW optimizer
    """
    lr = config["learning_rate"]
    weight_decay = config["weight_decay"]

    # Separate backbone and head parameters
    backbone_params = []
    head_params = []

    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        if "backbone" in name or "encoder" in name:
            backbone_params.append(param)
        else:
            head_params.append(param)

    # Use 10x lower LR for backbone (transfer learning best practice)
    param_groups = [
        {"params": backbone_params, "lr": lr * 0.1},
        {"params": head_params, "lr": lr},
    ]

    optimizer = torch.optim.AdamW(param_groups, weight_decay=weight_decay)

    logger.info(f"Optimizer: AdamW (backbone_lr={lr*0.1:.2e}, head_lr={lr:.2e})")
    logger.info(f"Backbone params: {len(backbone_params)}, Head params: {len(head_params)}")

    return optimizer


def get_scheduler(optimizer: torch.optim.Optimizer, config: dict, steps_per_epoch: int):
    """Create learning rate scheduler with warmup.

    Args:
        optimizer: Configured optimizer
        config: Configuration dictionary
        steps_per_epoch: Number of training steps per epoch

    Returns:
        Learning rate scheduler
    """
    num_epochs = config["num_epochs"]
    warmup_epochs = config.get("warmup_epochs", 3)
    scheduler_type = config.get("lr_scheduler", "cosine")

    total_steps = num_epochs * steps_per_epoch
    warmup_steps = warmup_epochs * steps_per_epoch

    if scheduler_type == "cosine":
        # Cosine annealing with warmup
        def lr_lambda(current_step: int) -> float:
            if current_step < warmup_steps:
                # Linear warmup
                return float(current_step) / float(max(1, warmup_steps))
            # Cosine annealing
            progress = float(current_step - warmup_steps) / float(
                max(1, total_steps - warmup_steps)
            )
            return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    else:
        # Step decay fallback
        scheduler = torch.optim.lr_scheduler.StepLR(
            optimizer, step_size=num_epochs // 3, gamma=0.1
        )

    logger.info(f"Scheduler: {scheduler_type} with {warmup_epochs} warmup epochs")

    return scheduler


def train_one_epoch(
    model: torch.nn.Module,
    train_loader,
    optimizer: torch.optim.Optimizer,
    scheduler,
    device: str,
    epoch: int,
    config: dict,
    scaler: GradScaler | None = None,
) -> dict:
    """Train for one epoch.

    Args:
        model: RT-DETR model
        train_loader: Training data loader
        optimizer: Configured optimizer
        scheduler: Learning rate scheduler
        device: Target device
        epoch: Current epoch number
        config: Configuration dictionary
        scaler: Gradient scaler for mixed precision

    Returns:
        Dictionary with training metrics
    """
    model.train()

    total_loss = 0.0
    num_batches = 0
    accumulation_steps = config.get("gradient_accumulation_steps", 1)
    log_every = config.get("log_every", 50)
    use_amp = config.get("mixed_precision", True) and device == "cuda"

    progress_bar = tqdm(train_loader, desc=f"Epoch {epoch}", leave=False)
    optimizer.zero_grad()

    for batch_idx, batch in enumerate(progress_bar):
        pixel_values = batch["pixel_values"].to(device)
        labels = [{k: v.to(device) for k, v in label.items()} for label in batch["labels"]]

        # Forward pass with mixed precision
        if use_amp and scaler is not None:
            with autocast():
                outputs = model(pixel_values=pixel_values, labels=labels)
                loss = outputs.loss / accumulation_steps
        else:
            outputs = model(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss / accumulation_steps

        # Backward pass
        if use_amp and scaler is not None:
            scaler.scale(loss).backward()
        else:
            loss.backward()

        # Gradient accumulation
        if (batch_idx + 1) % accumulation_steps == 0:
            if use_amp and scaler is not None:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            optimizer.zero_grad()
            scheduler.step()

        total_loss += loss.item() * accumulation_steps
        num_batches += 1

        # Update progress bar
        current_lr = scheduler.get_last_lr()[0]
        progress_bar.set_postfix(
            loss=f"{loss.item() * accumulation_steps:.4f}",
            lr=f"{current_lr:.2e}",
        )

        # Log periodically
        if batch_idx > 0 and batch_idx % log_every == 0:
            avg_loss = total_loss / num_batches
            logger.info(
                f"Epoch {epoch} [{batch_idx}/{len(train_loader)}] "
                f"Loss: {avg_loss:.4f}, LR: {current_lr:.2e}"
            )

    avg_loss = total_loss / num_batches

    return {"train_loss": avg_loss, "learning_rate": scheduler.get_last_lr()[0]}


@torch.no_grad()
def validate(
    model: torch.nn.Module,
    val_loader,
    device: str,
    config: dict,
) -> dict:
    """Validate the model.

    Args:
        model: RT-DETR model
        val_loader: Validation data loader
        device: Target device
        config: Configuration dictionary

    Returns:
        Dictionary with validation metrics
    """
    model.eval()

    total_loss = 0.0
    num_batches = 0
    all_pred_counts = []
    all_true_counts = []

    use_amp = config.get("mixed_precision", True) and device == "cuda"

    for batch in tqdm(val_loader, desc="Validating", leave=False):
        pixel_values = batch["pixel_values"].to(device)
        labels = [{k: v.to(device) for k, v in label.items()} for label in batch["labels"]]

        if use_amp:
            with autocast():
                outputs = model(pixel_values=pixel_values, labels=labels)
        else:
            outputs = model(pixel_values=pixel_values, labels=labels)

        total_loss += outputs.loss.item()
        num_batches += 1

        # Count predictions vs ground truth
        for i, label in enumerate(labels):
            true_count = len(label["class_labels"])
            all_true_counts.append(true_count)

            # Count detections above threshold (simplified - full mAP in test.py)
            # Note: This is a rough count, actual evaluation uses proper NMS
            pred_logits = outputs.logits[i]
            pred_probs = pred_logits.softmax(-1)
            # Exclude background class (last class)
            max_probs = pred_probs[..., :-1].max(-1).values
            pred_count = (max_probs > 0.5).sum().item()
            all_pred_counts.append(pred_count)

    avg_loss = total_loss / num_batches

    # Calculate count metrics
    all_pred_counts = torch.tensor(all_pred_counts)
    all_true_counts = torch.tensor(all_true_counts)

    exact_match = (all_pred_counts == all_true_counts).float().mean().item()
    within_5pct = (
        torch.abs(all_pred_counts - all_true_counts)
        <= torch.maximum(all_true_counts * 0.05, torch.ones_like(all_true_counts))
    ).float().mean().item()

    mae = torch.abs(all_pred_counts - all_true_counts).float().mean().item()

    return {
        "val_loss": avg_loss,
        "count_exact_match": exact_match,
        "count_within_5pct": within_5pct,
        "count_mae": mae,
    }


def save_checkpoint(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    scheduler,
    epoch: int,
    metrics: dict,
    config: dict,
    is_best: bool = False,
) -> str:
    """Save training checkpoint.

    Args:
        model: Trained model
        optimizer: Optimizer state
        scheduler: Scheduler state
        epoch: Current epoch
        metrics: Training metrics
        config: Configuration
        is_best: Whether this is the best model so far

    Returns:
        Path to saved checkpoint
    """
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict(),
        "metrics": metrics,
        "config": config,
    }

    # Save last checkpoint
    last_path = output_dir / "checkpoint_last.pt"
    torch.save(checkpoint, last_path)

    # Save best checkpoint
    if is_best:
        best_path = output_dir / "checkpoint_best.pt"
        torch.save(checkpoint, best_path)
        logger.info(f"New best model saved: val_loss={metrics['val_loss']:.4f}")

        # Also save in HuggingFace format for easy loading
        hf_path = output_dir / "best_model"
        model.save_pretrained(hf_path)
        logger.info(f"HuggingFace model saved to {hf_path}")

    # Save periodic checkpoints
    save_every = config.get("save_every", 5)
    if epoch % save_every == 0:
        epoch_path = output_dir / f"checkpoint_epoch_{epoch}.pt"
        torch.save(checkpoint, epoch_path)

    return str(last_path)


def load_checkpoint(
    checkpoint_path: str,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer | None = None,
    scheduler=None,
) -> tuple[int, dict]:
    """Load training checkpoint.

    Args:
        checkpoint_path: Path to checkpoint file
        model: Model to load weights into
        optimizer: Optional optimizer to restore
        scheduler: Optional scheduler to restore

    Returns:
        Tuple of (start_epoch, metrics)
    """
    logger.info(f"Loading checkpoint from {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu")

    model.load_state_dict(checkpoint["model_state_dict"])

    if optimizer is not None:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

    if scheduler is not None:
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

    epoch = checkpoint["epoch"]
    metrics = checkpoint.get("metrics", {})

    logger.info(f"Resumed from epoch {epoch}")

    return epoch, metrics


def train(config: dict, args: argparse.Namespace) -> None:
    """Main training function.

    Args:
        config: Configuration dictionary
        args: Command line arguments
    """
    # Override config with command line args
    if args.batch_size:
        config["batch_size"] = args.batch_size
    if args.epochs:
        config["num_epochs"] = args.epochs
    if args.device:
        config["device"] = args.device
    if args.lr:
        config["learning_rate"] = args.lr

    # Setup
    device = detect_device(config.get("device", "cuda"))
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save config for reproducibility
    with open(output_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)

    # Initialize wandb if requested
    if config.get("use_wandb", False):
        try:
            import wandb

            wandb.init(
                project=config.get("wandb_project", "cfu-counter-rtdetr"),
                name=config.get("wandb_run_name") or f"rtdetr-{datetime.now():%Y%m%d-%H%M}",
                config=config,
            )
        except ImportError:
            logger.warning("wandb not installed, skipping logging")
            config["use_wandb"] = False

    # Load processor and create dataloaders
    logger.info("Creating dataloaders...")
    processor = RTDetrImageProcessor.from_pretrained(config["model_name"])
    train_loader, val_loader = create_dataloaders(config, processor)

    # Create model
    logger.info("Creating model...")
    model = create_model(config, device)

    # Create optimizer and scheduler
    optimizer = get_optimizer(model, config)
    scheduler = get_scheduler(optimizer, config, len(train_loader))

    # Mixed precision scaler
    scaler = GradScaler() if config.get("mixed_precision", True) and device == "cuda" else None

    # Resume from checkpoint if specified
    start_epoch = 1
    best_val_loss = float("inf")

    if config.get("resume_from"):
        start_epoch, prev_metrics = load_checkpoint(
            config["resume_from"], model, optimizer, scheduler
        )
        start_epoch += 1
        best_val_loss = prev_metrics.get("val_loss", float("inf"))

    # Early stopping
    patience = config.get("early_stopping_patience", 10)
    epochs_without_improvement = 0

    # Training loop
    logger.info("=" * 60)
    logger.info("Starting training")
    logger.info(f"  Epochs: {config['num_epochs']}")
    logger.info(f"  Batch size: {config['batch_size']}")
    logger.info(f"  Learning rate: {config['learning_rate']}")
    logger.info(f"  Device: {device}")
    logger.info(f"  Output: {output_dir}")
    logger.info("=" * 60)

    training_start = time.time()

    for epoch in range(start_epoch, config["num_epochs"] + 1):
        epoch_start = time.time()

        # Train
        train_metrics = train_one_epoch(
            model, train_loader, optimizer, scheduler, device, epoch, config, scaler
        )

        # Validate
        val_every = config.get("val_every", 1)
        if epoch % val_every == 0:
            val_metrics = validate(model, val_loader, device, config)
        else:
            val_metrics = {}

        # Combine metrics
        metrics = {**train_metrics, **val_metrics, "epoch": epoch}

        # Check for improvement
        is_best = False
        if "val_loss" in val_metrics:
            if val_metrics["val_loss"] < best_val_loss:
                best_val_loss = val_metrics["val_loss"]
                is_best = True
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1

        # Save checkpoint
        save_checkpoint(model, optimizer, scheduler, epoch, metrics, config, is_best)

        # Log metrics
        epoch_time = time.time() - epoch_start
        logger.info(
            f"Epoch {epoch}/{config['num_epochs']} completed in {epoch_time:.1f}s"
        )
        logger.info(f"  Train Loss: {train_metrics['train_loss']:.4f}")
        if "val_loss" in val_metrics:
            logger.info(f"  Val Loss: {val_metrics['val_loss']:.4f}")
            logger.info(f"  Count Exact Match: {val_metrics['count_exact_match']:.2%}")
            logger.info(f"  Count Within 5%: {val_metrics['count_within_5pct']:.2%}")

        # Log to wandb
        if config.get("use_wandb", False):
            import wandb

            wandb.log(metrics)

        # Early stopping
        if epochs_without_improvement >= patience:
            logger.info(f"Early stopping after {epochs_without_improvement} epochs without improvement")
            break

    # Training complete
    total_time = time.time() - training_start
    logger.info("=" * 60)
    logger.info(f"Training completed in {total_time / 3600:.1f} hours")
    logger.info(f"Best validation loss: {best_val_loss:.4f}")
    logger.info(f"Best model saved to: {output_dir / 'best_model'}")
    logger.info("=" * 60)

    # Save training history
    history_path = output_dir / "training_history.json"
    with open(history_path, "w") as f:
        json.dump(
            {
                "final_epoch": epoch,
                "best_val_loss": best_val_loss,
                "total_time_hours": total_time / 3600,
                "config": config,
            },
            f,
            indent=2,
        )

    if config.get("use_wandb", False):
        import wandb

        wandb.finish()


def main():
    """Entry point for training script."""
    parser = argparse.ArgumentParser(
        description="Fine-tune RT-DETR on AGAR dataset for colony detection"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="rtdetr_v2/config.yaml",
        help="Path to configuration YAML file",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=None,
        help="Override batch size from config",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Override number of epochs from config",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cuda", "mps", "cpu"],
        help="Override device from config",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=None,
        help="Override learning rate from config",
    )

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)

    config = load_config(str(config_path))

    # Start training
    train(config, args)


if __name__ == "__main__":
    main()
