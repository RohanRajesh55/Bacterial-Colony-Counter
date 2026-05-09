"""
CNN Model wrapper for bacterial colony counting and classification.
Adapted from cnn/cnn_test.py for inference-only use.
"""
import torch
import torch.nn as nn
import numpy as np
import cv2
from pathlib import Path
from typing import Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class VanillaDeepCNN(nn.Module):
    """
    Multi-task CNN architecture matching the trained model.
    Has two heads: one for counting (regression) and one for classification.
    """
    def __init__(self, in_channels=3, num_conv_blocks=6, base_filters=32, 
                 fc_size=512, dropout=0.4, num_classes=7):
        super().__init__()
        # Shared Feature Extractor
        layers, c, f = [], in_channels, base_filters
        for i in range(num_conv_blocks):
            out_ch = min(f * (2**i), 512)
            layers += [
                nn.Conv2d(c, out_ch, 3, padding=1), 
                nn.BatchNorm2d(out_ch), 
                nn.ReLU(True), 
                nn.MaxPool2d(2)
            ]
            c = out_ch
        self.features = nn.Sequential(*layers)
        
        # Global Average Pooling and Shared FC Layer
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.shared_fc = nn.Sequential(
            nn.Linear(c, fc_size), 
            nn.ReLU(True), 
            nn.Dropout(dropout)
        )
        
        # Head 1: Counting (regression)
        self.head_count = nn.Sequential(
            nn.Linear(fc_size, fc_size//2), 
            nn.ReLU(True), 
            nn.Dropout(dropout/2), 
            nn.Linear(fc_size//2, 1)
        )
        # Head 2: Classification
        self.head_class = nn.Sequential(
            nn.Linear(fc_size, fc_size//2), 
            nn.ReLU(True), 
            nn.Dropout(dropout/2), 
            nn.Linear(fc_size//2, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.gap(x)
        x = x.view(x.size(0), -1)
        shared = self.shared_fc(x)
        return self.head_count(shared), self.head_class(shared)


class CNNModel:
    """Wrapper class for CNN inference with preprocessing."""
    
    # Default model hyperparameters (must match training config)
    DEFAULT_CONFIG = {
        "num_conv_blocks": 6,
        "base_filters": 32,
        "fc_size": 512,
        "dropout": 0.4,
        "image_size": (224, 224),
    }
    
    def __init__(self, model_path: str, class_names: list, device: str = "cpu", config: Optional[Dict] = None):
        """
        Initialize the CNN model.
        
        Args:
            model_path: Path to the trained .pth weights file
            class_names: List of class names in order
            device: "cpu" or "cuda"
            config: Optional config dict to override DEFAULT_CONFIG
        """
        self.device = torch.device(device)
        self.class_names = class_names
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.model = self._load_model(model_path)
        
        # ImageNet normalization (used during training)
        self.mean = np.array([0.485, 0.456, 0.406])
        self.std = np.array([0.229, 0.224, 0.225])
        
        logger.info(f"CNN Model loaded on {self.device}")
    
    def _load_model(self, model_path: str) -> nn.Module:
        """Load model weights from file."""
        model = VanillaDeepCNN(
            in_channels=3,
            num_conv_blocks=self.config["num_conv_blocks"],
            base_filters=self.config["base_filters"],
            fc_size=self.config["fc_size"],
            dropout=self.config["dropout"],
            num_classes=len(self.class_names)
        )
        
        state_dict = torch.load(model_path, map_location=self.device, weights_only=True)
        model.load_state_dict(state_dict, strict=True)
        model.to(self.device)
        model.eval()
        
        return model
    
    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for model input.
        
        Args:
            image: BGR image as numpy array (from cv2.imread)
            
        Returns:
            Preprocessed tensor ready for model
        """
        # Keep BGR order (matches training pipeline: cv2.imread -> Albumentations)
        img = image.copy()
        
        # Resize to model input size
        img = cv2.resize(img, self.config["image_size"])
        
        # Normalize to [0, 1] then apply ImageNet normalization
        img = img.astype(np.float32) / 255.0
        img = (img - self.mean) / self.std
        
        # Convert to tensor: HWC -> CHW
        img = np.transpose(img, (2, 0, 1))
        tensor = torch.from_numpy(img).float().unsqueeze(0)
        
        return tensor.to(self.device)
    
    
    def predict(self, image: np.ndarray) -> Dict:
        """
        Run inference on an image. Auto-tiles for large images.
        
        Args:
            image: BGR image as numpy array
            
        Returns:
            Dict with count, predicted_class, class_probabilities
        """
        # Preprocess the entire image as one unit (matches training where whole image is resized to 224x224)
        tensor = self.preprocess(image)
        
        # Inference
        with torch.no_grad():
            count_pred, class_logits = self.model(tensor)
        
        # Process outputs
        count = max(0, round(count_pred.item()))
        
        # Softmax for class probabilities
        probs = torch.softmax(class_logits, dim=1).squeeze().cpu().numpy()
        predicted_class_idx = int(np.argmax(probs))
        predicted_class = self.class_names[predicted_class_idx]
        
        # Build class distribution
        class_probs = {
            name: float(probs[i]) 
            for i, name in enumerate(self.class_names)
        }
        
        return {
            "total_count": count,
            "predicted_class": predicted_class,
            "class_probabilities": class_probs,
            "class_counts": {predicted_class: count},
        }

    def predict_tiled(self, image: np.ndarray, tile_size: int = 224) -> Dict:
        """
        Run inference on non-overlapping tiles and aggregate results.
        Ideal for counting on large images using the regression head.
        """
        h, w = image.shape[:2]
        
        total_count = 0
        class_counts = {name: 0 for name in self.class_names}
        
        # Sliding window (no overlap to prevent double counting)
        # Handle edges by including the partial tile? Or padding?
        # Standard: Run on grid.
        
        stride = tile_size
        
        for y in range(0, h, stride):
            for x in range(0, w, stride):
                # Crop tile
                tile = image[y:y+tile_size, x:x+tile_size]
                
                # If tile is too small (edge), pad it? 
                # Or just run it (preprocessing resizes it anyway).
                # Preprocessing resizes whatever input to 224x224.
                # So even small edge strips will be stretched to 224x224, potentially distorting features.
                # Better to PAD to 224x224 with black.
                
                th, tw = tile.shape[:2]
                if th < tile_size or tw < tile_size:
                    padded = np.zeros((tile_size, tile_size, 3), dtype=np.uint8)
                    padded[:th, :tw] = tile
                    tile = padded
                
                # Run prediction
                # Call internal predict (recursive check disabled by size check? No, extract logic)
                # We need to call the direct inference part to avoid recursion loop
                
                tensor = self.preprocess(tile)
                with torch.no_grad():
                    count_pred, class_logits = self.model(tensor)
                    
                c_val = max(0, count_pred.item())
                
                # Accumulate
                # For classification, we use the tile's predicted class to assign the count
                probs = torch.softmax(class_logits, dim=1).squeeze().cpu().numpy()
                cls_idx = int(np.argmax(probs))
                cls_name = self.class_names[cls_idx]
                
                # Add to total
                total_count += c_val
                class_counts[cls_name] += c_val
                
        # Round final totals
        total_count = round(total_count)
        for k in class_counts:
            class_counts[k] = round(class_counts[k])
            
        # Determine dominant class for "predicted_class" field
        dominant_class = max(class_counts, key=class_counts.get) if total_count > 0 else self.class_names[0]
        
        return {
            "total_count": total_count,
            "predicted_class": dominant_class,
            "class_probabilities": {}, # Hard to aggregate probs meaningfully
            "class_counts": class_counts
        }

    def warmup(self):
        """Run a dummy inference to warm up the model."""
        dummy = np.zeros((224, 224, 3), dtype=np.uint8)
        self.predict(dummy)
        logger.info("CNN Model warmed up")
