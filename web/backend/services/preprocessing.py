"""
Image preprocessing service.
Provides utilities for image preprocessing and encoding.
Uses the shared core.preprocessing module for advanced processing.
"""
import cv2
import numpy as np
import base64
import hashlib
import sys
from pathlib import Path
from functools import lru_cache
from typing import Tuple, Optional, Dict
import logging
import os

logger = logging.getLogger(__name__)

# Add core module to path
CORE_PATH = Path(__file__).parent.parent.parent.parent / "core"
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))
    # Add root path for sisr.py and swinir_model.py
    sys.path.insert(0, str(CORE_PATH.parent))

# Import the preprocessing pipeline
PIPELINE_AVAILABLE = False
try:
    from preprocessing import PreprocessingPipeline
    PIPELINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Core preprocessing module not available: {e}")
    PIPELINE_AVAILABLE = False


# Configuration - can be overridden via environment variables
PREPROCESSING_CONFIG = {
    'pipeline_version': os.getenv('PREPROCESSING_VERSION', 'v1.0.0'),
    'max_dimension': int(os.getenv('PREPROCESSING_MAX_DIM', '2048')),
    'timeout_seconds': float(os.getenv('PREPROCESSING_TIMEOUT', '2.0')),
    'clahe_clip_limit': float(os.getenv('PREPROCESSING_CLAHE_CLIP', '2.0')),
    'rim_crop_ratio': float(os.getenv('PREPROCESSING_RIM_RATIO', '1.02')),
    # Relaxed detection for user uploads
    'min_radius_ratio': float(os.getenv('PREPROCESSING_MIN_RADIUS', '0.15')), # Was 0.25
    'max_radius_ratio': float(os.getenv('PREPROCESSING_MAX_RADIUS', '0.70')), # Was 0.55
    'hough_param2': int(os.getenv('PREPROCESSING_HOUGH_PARAM2', '25')),       # Was 30
    'min_dist_ratio': float(os.getenv('PREPROCESSING_MIN_DIST', '0.3')),      # Was 0.5
    'use_sisr': True, # Enable SwinIR Super Resolution
}

# Global pipeline instance (lazy initialization)
# Use 'object' type hint to avoid NameError when PreprocessingPipeline import fails
_pipeline: Optional[object] = None


def get_pipeline() -> Optional[object]:
    """Get or create the preprocessing pipeline instance."""
    global _pipeline
    if _pipeline is None and PIPELINE_AVAILABLE:
        try:
            _pipeline = PreprocessingPipeline(
                output_dir='temp_preprocessing',
                config=PREPROCESSING_CONFIG
            )
            logger.info(f"Preprocessing pipeline initialized: {PREPROCESSING_CONFIG['pipeline_version']}")
        except Exception as e:
            logger.error(f"Failed to initialize preprocessing pipeline: {e}")
    return _pipeline


def compute_image_hash(image: np.ndarray) -> str:
    """Compute a hash of the image for caching."""
    return hashlib.md5(image.tobytes()).hexdigest()


# Simple LRU cache for preprocessing results
_preprocess_cache: Dict[str, dict] = {}
MAX_CACHE_SIZE = 20


def enhance_image(image: np.ndarray, use_cache: bool = True) -> Tuple[np.ndarray, dict]:
    """
    Apply advanced preprocessing to an image.
    
    Args:
        image: BGR numpy array
        use_cache: Whether to use caching (default True)
        
    Returns:
        Tuple of (processed_image, metadata)
        If preprocessing fails, returns (original_image, error_metadata)
    """
    pipeline = get_pipeline()
    
    if pipeline is None:
        logger.warning("Preprocessing pipeline not available, returning original image")
        return image, {
            'status': 'skipped',
            'error': 'Pipeline not available',
            'processing_time_ms': 0
        }
    
    # Check cache
    if use_cache:
        img_hash = compute_image_hash(image)
        if img_hash in _preprocess_cache:
            cached = _preprocess_cache[img_hash]
            logger.info(f"Cache hit for image hash: {img_hash[:8]}...")
            return cached['processed'], {**cached['metadata'], 'cache_hit': True}
    
    # Process image
    try:
        result = pipeline.process_image(image)
        processed = result['processed']
        metadata = result['metadata']
        
        # Cache successful results
        if use_cache and metadata['status'] == 'success':
            # Evict oldest entry if cache full
            if len(_preprocess_cache) >= MAX_CACHE_SIZE:
                oldest_key = next(iter(_preprocess_cache))
                del _preprocess_cache[oldest_key]
            
            _preprocess_cache[img_hash] = result
            logger.info(f"Cached preprocessing result: {img_hash[:8]}...")
        
        return processed, {**metadata, 'cache_hit': False}
        
    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        return image, {
            'status': 'failed',
            'error': str(e),
            'processing_time_ms': 0,
            'cache_hit': False
        }


def isolate_petri_dish(image: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Isolate the petri dish from the background.
    
    Args:
        image: BGR numpy array
        
    Returns:
        Tuple of (masked_image, mask)
        If isolation fails, returns (original_image, None)
    """
    pipeline = get_pipeline()
    
    if pipeline is None:
        return image, None
    
    try:
        mask, center, radius = pipeline.isolate_petri_dish(image)
        if center is not None:
            masked = cv2.bitwise_and(image, image, mask=mask)
            return masked, mask
        else:
            return image, None
    except Exception as e:
        logger.warning(f"Dish isolation failed: {e}")
        return image, None


def preprocess_image(image_bytes: bytes) -> Tuple[np.ndarray, Optional[str]]:
    """
    Decode and validate an uploaded image.
    
    Args:
        image_bytes: Raw image bytes from upload
        
    Returns:
        Tuple of (BGR numpy array, error message or None)
    """
    try:
        # Decode image from bytes
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return None, "Failed to decode image. Please upload a valid image file."
        
        # Basic validation
        h, w = image.shape[:2]
        if h < 100 or w < 100:
            return None, "Image too small. Minimum size is 100x100 pixels."
        
        if h > 8000 or w > 8000:
            return None, "Image too large. Maximum size is 8000x8000 pixels."
        
        logger.info(f"Image loaded: {w}x{h}")
        return image, None
        
    except Exception as e:
        logger.error(f"Error preprocessing image: {e}")
        return None, f"Error processing image: {str(e)}"


def encode_image_to_base64(image: np.ndarray, format: str = "jpg", quality: int = 90) -> str:
    """
    Encode a numpy image to base64 string.
    
    Args:
        image: BGR numpy array
        format: Output format ("jpg" or "png")
        quality: JPEG quality (1-100)
        
    Returns:
        Base64 encoded string with data URI prefix
    """
    if format.lower() == "png":
        success, buffer = cv2.imencode(".png", image)
        mime_type = "image/png"
    else:
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        success, buffer = cv2.imencode(".jpg", image, encode_params)
        mime_type = "image/jpeg"
    
    if not success:
        raise ValueError("Failed to encode image")
    
    b64_string = base64.b64encode(buffer).decode("utf-8")
    return f"data:{mime_type};base64,{b64_string}"


def resize_for_display(image: np.ndarray, max_size: int = 1024) -> np.ndarray:
    """
    Resize image for display, maintaining aspect ratio.
    
    Args:
        image: BGR numpy array
        max_size: Maximum dimension (width or height)
        
    Returns:
        Resized image
    """
    h, w = image.shape[:2]
    
    if max(h, w) <= max_size:
        return image
    
    if w > h:
        new_w = max_size
        new_h = int(h * max_size / w)
    else:
        new_h = max_size
        new_w = int(w * max_size / h)
    
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
