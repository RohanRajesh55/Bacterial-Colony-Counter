"""RT-DETRv4 inference service for colony detection.

Uses the native RT-DETRv4/D-FINE framework for inference, loading weights
from the rtdetr_v4/checkpoints directory.
"""

import base64
import logging
import sys
from io import BytesIO
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.transforms as T
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Add rtdetr_v4 to path so we can import the framework
RTDETR_V4_DIR = Path(__file__).resolve().parent.parent.parent / "rtdetr_v4"
if str(RTDETR_V4_DIR) not in sys.path:
    sys.path.insert(0, str(RTDETR_V4_DIR))


def detect_device() -> str:
    """Detect the best available device for inference."""
    if torch.cuda.is_available():
        device = "cuda"
        logger.info("CUDA GPU detected, using NVIDIA GPU for inference")
    elif torch.backends.mps.is_available():
        device = "mps"
        logger.info("Apple Silicon detected, using MPS for inference")
    else:
        device = "cpu"
        logger.info("No GPU detected, using CPU for inference")
    return device


class _DeployModel(nn.Module):
    """Wrapper that combines model + postprocessor in deploy mode."""

    def __init__(self, model, postprocessor):
        super().__init__()
        self.model = model.deploy()
        self.postprocessor = postprocessor.deploy()

    def forward(self, images, orig_target_sizes):
        outputs = self.model(images)
        outputs = self.postprocessor(outputs, orig_target_sizes)
        return outputs


class RTDetrService:
    """RT-DETRv4 object detection service for colony counting."""

    def __init__(
        self,
        config_path: str | None = None,
        checkpoint_path: str | None = None,
    ) -> None:
        """Initialize the RT-DETRv4 service.

        Args:
            config_path: Path to YAML config file (e.g. configs/dfine/dfine_hgnetv2_x_coco.yml)
            checkpoint_path: Path to .pth checkpoint file
        """
        self.device = detect_device()

        # Default paths relative to rtdetr_v4 directory
        if config_path is None:
            config_path = str(RTDETR_V4_DIR / "configs" / "dfine" / "dfine_hgnetv2_x_agar.yml")
        if checkpoint_path is None:
            checkpoint_path = str(RTDETR_V4_DIR / "weights" / "dfine_hgnetv2_x_agar_1cls_best.pth")

        logger.info(f"Loading RT-DETRv4 config: {config_path}")
        logger.info(f"Loading checkpoint: {checkpoint_path}")

        from engine.core import YAMLConfig

        cfg = YAMLConfig(config_path, resume=checkpoint_path)

        # Disable pretrained download since we're loading from checkpoint
        if "HGNetv2" in cfg.yaml_cfg:
            cfg.yaml_cfg["HGNetv2"]["pretrained"] = False

        # Load checkpoint weights
        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        if "ema" in checkpoint:
            state = checkpoint["ema"]["module"]
        else:
            state = checkpoint["model"]

        cfg.model.load_state_dict(state, strict=False)

        # Build deploy-mode model
        self.model = _DeployModel(cfg.model, cfg.postprocessor).to(self.device)
        self.model.eval()

        # Image transform matching training config (eval_spatial_size)
        eval_size = cfg.yaml_cfg.get("eval_spatial_size", [640, 640])
        self.transforms = T.Compose([
            T.Resize(eval_size),
            T.ToTensor(),
        ])

        logger.info(f"RT-DETRv4 model loaded successfully on {self.device}")

    def predict(
        self, image: Image.Image, confidence_threshold: float = 0.5
    ) -> tuple[int, list[dict]]:
        """Run colony detection on an image.

        Args:
            image: PIL Image to analyze
            confidence_threshold: Minimum confidence for detections (0.0-1.0)

        Returns:
            Tuple of (count, detections) where detections is a list of dicts
            with 'box' ([x1, y1, x2, y2] in pixels) and 'confidence' keys
        """
        w, h = image.size
        orig_size = torch.tensor([[w, h]]).to(self.device)
        im_data = self.transforms(image.convert("RGB")).unsqueeze(0).to(self.device)

        with torch.no_grad():
            labels, boxes, scores = self.model(im_data, orig_size)

        # Filter by confidence threshold
        detections = []
        scores_np = scores[0].cpu().numpy()
        boxes_np = boxes[0].cpu().numpy()

        for box, score in zip(boxes_np, scores_np):
            if score >= confidence_threshold:
                detections.append(
                    {
                        "box": [float(x) for x in box],
                        "confidence": float(score),
                    }
                )

        count = len(detections)
        logger.info(f"Detected {count} colonies with threshold {confidence_threshold}")

        return count, detections

    def annotate_image(
        self, image: Image.Image, detections: list[dict]
    ) -> Image.Image:
        """Draw bounding boxes on image."""
        annotated = image.copy()
        draw = ImageDraw.Draw(annotated)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except (OSError, IOError):
            font = ImageFont.load_default()

        box_color = (0, 255, 0)

        for detection in detections:
            box = detection["box"]
            confidence = detection["confidence"]
            x1, y1, x2, y2 = box
            draw.rectangle([x1, y1, x2, y2], outline=box_color, width=2)
            label = f"{confidence:.2f}"
            label_y = max(0, y1 - 15)
            draw.text((x1, label_y), label, fill=box_color, font=font)

        return annotated

    @staticmethod
    def image_to_base64(image: Image.Image) -> str:
        """Convert PIL Image to base64 data URI."""
        if image.mode == "RGBA":
            image = image.convert("RGB")

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"
