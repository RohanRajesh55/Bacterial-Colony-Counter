import cv2
import numpy as np

def generate_heatmap(image: np.ndarray, detections: list) -> np.ndarray:
    """
    Generate a heatmap based on detection centroids and overlay it on the original image.
    
    Args:
        image: Original BGR image.
        detections: List of detection dictionaries (from YOLO model).
        
    Returns:
        Heatmap overlay image (BGR).
    """
    if image is None:
        return None
        
    height, width = image.shape[:2]
    
    # Create empty mask
    # Float32 for accumulation
    density_map = np.zeros((height, width), dtype=np.float32)
    
    if not detections:
        # Return original image if no detections, or maybe a blue-ish overlay?
        # Let's just return original image but maybe slightly tinted to show "checked but empty"? 
        # No, just return original.
        return image
        
    # Scale sigma based on image size to have reasonable blob size
    # e.g., for 1000px width, sigma ~ 20-30
    sigma = max(width, height) / 40.0
    
    for det in detections:
        bbox = det["bbox"]
        x1, y1, x2, y2 = bbox
        
        # Calculate centroid
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        
        # Clip to bounds
        cx = min(max(cx, 0), width - 1)
        cy = min(max(cy, 0), height - 1)
        
        # Add point source
        density_map[cy, cx] += 1.0

    # Apply Gaussian Blur to creating smooth blobs
    # ksize=(0,0) lets opencv calculate ksize from sigma
    density_map = cv2.GaussianBlur(density_map, (0, 0), sigmaX=sigma, sigmaY=sigma)
    
    # Normalize to 0-255
    norm_map = cv2.normalize(density_map, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
    norm_map = norm_map.astype(np.uint8)
    
    # Apply colormap
    # COLORMAP_JET is standard (Blue=Low, Red=High)
    heatmap_color = cv2.applyColorMap(norm_map, cv2.COLORMAP_JET)
    
    # Overlay on original image
    # Weight: 0.6 original, 0.4 heatmap
    overlay = cv2.addWeighted(image, 0.6, heatmap_color, 0.4, 0)
    
    return overlay
