#!/usr/bin/env python3
"""
preprocess.py

Preprocesses images for YOLO training to improve model performance on real-world data.
This script performs:
1. Petri dish detection and cropping (isolates the region of interest)
2. Lighting normalization (CLAHE for contrast enhancement)
3. Optional resizing to target resolution

Usage:
    python preprocess.py --input_dir ./raw_images --output_dir ./processed_images --size 1024
"""

import os
import argparse
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def detect_petri_dish(image: np.ndarray) -> tuple:
    """
    Detects the circular petri dish in an image using Hough Circle Transform.
    Returns (center_x, center_y, radius) or None if not found.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 2)
    
    h, w = gray.shape
    min_radius = int(min(h, w) * 0.20)
    max_radius = int(min(h, w) * 0.55)  # Increased to catch larger dishes
    
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=int(min(h, w) * 0.3),
        param1=50,
        param2=30,
        minRadius=min_radius,
        maxRadius=max_radius
    )
    
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        # Return the largest circle (most likely the dish)
        largest = max(circles, key=lambda c: c[2])
        return (largest[0], largest[1], largest[2])
    
    return None


def crop_to_dish(image: np.ndarray, circle: tuple, padding: float = 0.25) -> np.ndarray:
    """
    Crops image to the detected petri dish with optional padding.
    """
    cx, cy, r = circle
    h, w = image.shape[:2]
    
    # Add padding
    r_padded = int(r * (1 + padding))
    
    # Calculate crop bounds
    x1 = max(0, cx - r_padded)
    y1 = max(0, cy - r_padded)
    x2 = min(w, cx + r_padded)
    y2 = min(h, cy + r_padded)
    
    cropped = image[y1:y2, x1:x2]
    
    return cropped


def apply_white_balance(image: np.ndarray) -> np.ndarray:
    """
    Applies automatic white balance using the gray world assumption.
    Normalizes lighting across the image.
    """
    result = image.copy().astype(np.float32)
    
    # Calculate channel averages
    avg_b = np.mean(result[:, :, 0])
    avg_g = np.mean(result[:, :, 1])
    avg_r = np.mean(result[:, :, 2])
    avg_gray = (avg_b + avg_g + avg_r) / 3
    
    # Scale each channel to match gray average
    if avg_b > 0:
        result[:, :, 0] = result[:, :, 0] * (avg_gray / avg_b)
    if avg_g > 0:
        result[:, :, 1] = result[:, :, 1] * (avg_gray / avg_g)
    if avg_r > 0:
        result[:, :, 2] = result[:, :, 2] * (avg_gray / avg_r)
    
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_gamma_correction(image: np.ndarray, gamma: float = 1.2) -> np.ndarray:
    """
    Applies gamma correction to adjust overall brightness.
    gamma > 1: darken image, gamma < 1: brighten image
    """
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 
                      for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)


def apply_clahe(image: np.ndarray, clip_limit: float = 3.0, grid_size: int = 8) -> np.ndarray:
    """
    Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) for contrast enhancement.
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Apply CLAHE to L channel with higher clip limit
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    l_enhanced = clahe.apply(l_channel)
    
    # Merge and convert back
    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    result = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
    
    return result


def apply_denoising(image: np.ndarray, strength: int = 10) -> np.ndarray:
    """
    Applies bilateral filter for edge-preserving denoising.
    Good for removing noise while keeping colony edges sharp.
    """
    # Bilateral filter: preserves edges while smoothing
    denoised = cv2.bilateralFilter(image, d=9, sigmaColor=strength*2, sigmaSpace=strength)
    return denoised


def apply_unsharp_mask(image: np.ndarray, strength: float = 1.5) -> np.ndarray:
    """
    Applies unsharp masking to enhance edges (colony boundaries).
    """
    gaussian = cv2.GaussianBlur(image, (0, 0), 3)
    sharpened = cv2.addWeighted(image, 1 + strength, gaussian, -strength, 0)
    return sharpened


def preprocess_image(
    image: np.ndarray,
    target_size: int = 1024,
    detect_dish: bool = False,  # Disabled by default - causes cropping issues
    apply_enhancement: bool = True
) -> np.ndarray:
    """
    Full preprocessing pipeline for a single image.
    """
    result = image.copy()
    
    # Step 1: Detect and crop to petri dish
    if detect_dish:
        circle = detect_petri_dish(result)
        if circle is not None:
            result = crop_to_dish(result, circle)
            logger.debug(f"Detected dish at {circle}")
    
    # Step 2: Apply image enhancement
    if apply_enhancement:
        result = apply_white_balance(result)  # Fix color cast from lighting
        result = apply_gamma_correction(result, gamma=0.9)  # Brighten slightly
        result = apply_clahe(result, clip_limit=3.0)  # Stronger contrast
        result = apply_denoising(result, strength=8)  # Edge-preserving denoising
        result = apply_unsharp_mask(result, strength=0.6)  # Mild sharpening
    
    # Step 3: Resize to target size (maintain aspect ratio with padding)
    h, w = result.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    
    # Use different interpolation based on upscaling vs downscaling
    if scale > 1:
        # Upscaling - use LANCZOS4 for better quality
        # But warn if upscaling is extreme (>3x)
        if scale > 3:
            logger.warning(f"Extreme upscaling ({scale:.1f}x) from {w}x{h}. Quality may suffer.")
        resized = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    else:
        # Downscaling - use INTER_AREA for best quality
        resized = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Pad to square
    canvas = np.zeros((target_size, target_size, 3), dtype=np.uint8)
    y_offset = (target_size - new_h) // 2
    x_offset = (target_size - new_w) // 2
    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
    
    return canvas


def process_dataset(
    input_dir: str,
    output_dir: str,
    target_size: int = 1024,
    detect_dish: bool = True,
    apply_enhancement: bool = True,
    copy_labels: bool = True
):
    """
    Processes an entire YOLO dataset directory structure.
    Expected structure:
        input_dir/
            images/
                train/
                val/
            labels/
                train/
                val/
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Process each split (train, val)
    for split in ["train", "val"]:
        img_in_dir = input_path / "images" / split
        img_out_dir = output_path / "images" / split
        lbl_in_dir = input_path / "labels" / split
        lbl_out_dir = output_path / "labels" / split
        
        if not img_in_dir.exists():
            logger.warning(f"Skipping {split}: {img_in_dir} does not exist")
            continue
        
        img_out_dir.mkdir(parents=True, exist_ok=True)
        lbl_out_dir.mkdir(parents=True, exist_ok=True)
        
        image_files = list(img_in_dir.glob("*.jpg")) + list(img_in_dir.glob("*.png"))
        logger.info(f"Processing {len(image_files)} images in {split} split...")
        
        for img_file in tqdm(image_files, desc=f"Preprocessing {split}"):
            try:
                # Load and preprocess image
                img = cv2.imread(str(img_file))
                if img is None:
                    logger.warning(f"Could not read {img_file}")
                    continue
                
                processed = preprocess_image(
                    img,
                    target_size=target_size,
                    detect_dish=detect_dish,
                    apply_enhancement=apply_enhancement
                )
                
                # Save processed image
                out_file = img_out_dir / img_file.name
                cv2.imwrite(str(out_file), processed)
                
                # Copy corresponding label file (labels are resolution-independent in YOLO format)
                if copy_labels:
                    lbl_file = lbl_in_dir / f"{img_file.stem}.txt"
                    if lbl_file.exists():
                        shutil.copy(lbl_file, lbl_out_dir / lbl_file.name)
                        
            except Exception as e:
                logger.error(f"Error processing {img_file}: {e}")
    
    logger.info(f"Preprocessing complete. Output saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Preprocess images for YOLO training.")
    parser.add_argument("--input_dir", type=str, required=True, help="Input dataset directory")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for processed images")
    parser.add_argument("--size", type=int, default=1024, help="Target image size (default: 1024)")
    parser.add_argument("--no_dish_detection", action="store_true", help="Disable petri dish detection/cropping")
    parser.add_argument("--no_enhancement", action="store_true", help="Disable CLAHE/sharpening")
    parser.add_argument("--no_copy_labels", action="store_true", help="Do not copy label files")
    
    args = parser.parse_args()
    
    process_dataset(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        target_size=args.size,
        detect_dish=not args.no_dish_detection,
        apply_enhancement=not args.no_enhancement,
        copy_labels=not args.no_copy_labels
    )


if __name__ == "__main__":
    main()
