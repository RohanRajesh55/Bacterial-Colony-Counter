import cv2
import numpy as np
import os
import json
import logging
from pathlib import Path
from tqdm import tqdm
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from ultralytics import SAM
except ImportError:
    logger.error("Ultralytics not installed. Please run: pip install ultralytics")
    exit(1)

try:
    import torch
    DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
except ImportError:
    DEVICE = 'cpu'

def load_sam_model(model_type='mobile_sam.pt'):
    """Load the SAM model."""
    try:
        if not os.path.exists(model_type):
            logger.info(f"Downloading {model_type}...")
        model = SAM(model_type)
        return model
    except Exception as e:
        logger.error(f"Failed to load SAM model: {e}")
        return None

def get_background_stats(image, mask_poly):
    """
    Calculate background statistics (mean intensity, std dev) 
    from the area immediately surrounding the colony.
    """
    # Create a mask for the 'immediate background'
    # Dilate the colony mask to get a ring around it
    kernel = np.ones((5,5), np.uint8)
    dilated = cv2.dilate(mask_poly, kernel, iterations=3)
    bg_ring = cv2.subtract(dilated, mask_poly)
    
    # Extract pixels in the ring
    bg_pixels = image[bg_ring > 0]
    
    if bg_pixels.size == 0:
        return 0, 0
        
    mean_val = np.mean(bg_pixels, axis=0) # RGB mean
    std_val = np.std(bg_pixels, axis=0)
    
    return mean_val, std_val

def remove_text_from_image(img_bgr):
    """
    Remove BLACK marker text from a plate image before extraction.
    Uses HSV color space to detect dark, unsaturated (ink) pixels and inpaints them.
    This prevents text fragments from contaminating colony assets.
    """
    h, w = img_bgr.shape[:2]
    
    # Convert to HSV
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    s_channel = hsv[:, :, 1]
    v_channel = hsv[:, :, 2]
    
    # Estimate local brightness
    v_blur = cv2.GaussianBlur(v_channel, (51, 51), 0)
    
    # Text = darker than surroundings AND low saturation (black ink)
    v_diff = v_blur.astype(np.float32) - v_channel.astype(np.float32)
    is_dark = v_diff > 15
    is_unsaturated = s_channel < 70
    
    text_candidate = (is_dark & is_unsaturated).astype(np.uint8) * 255
    
    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    text_candidate = cv2.morphologyEx(text_candidate, cv2.MORPH_CLOSE, kernel)
    
    # Filter by connected component size
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(text_candidate)
    text_mask = np.zeros_like(text_candidate)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > 5:
            text_mask[labels == i] = 255
    
    if np.sum(text_mask) > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        text_mask = cv2.dilate(text_mask, kernel, iterations=2)
        result = cv2.inpaint(img_bgr, text_mask, 10, cv2.INPAINT_TELEA)
        logger.info("Text removed from source image before extraction.")
        return result
    
    return img_bgr

def regularize_mask(mask):
    """
    Regularize a SAM/CV mask to be a clean circle.
    
    Bacterial colonies grow radially and are inherently round.
    Instead of keeping irregular SAM boundaries, we fit a minimum 
    enclosing circle to the SAM contour. This produces the most 
    biologically accurate and visually clean result.
    """
    if mask is None or np.sum(mask) == 0:
        return mask
    
    h, w = mask.shape[:2]
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return mask
    
    # Get the largest contour
    cnt = max(contours, key=cv2.contourArea)
    
    # Use minimum enclosing circle — colonies are round
    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
    
    # Shrink by 10% to ensure we don't include background
    radius = max(1, radius * 0.90)
    
    circle_mask = np.zeros_like(mask)
    cv2.circle(circle_mask, (int(cx), int(cy)), int(radius), 255, -1)
    
    return circle_mask


def feather_alpha(mask, feather_px=3):
    """
    Create a soft-edged alpha mask by blurring the binary mask.
    Returns a mask with smooth gradient from 255 (center) to 0 (edge).
    
    For very small colonies, reduces feathering to avoid eroding them away.
    """
    if mask is None or np.sum(mask) == 0:
        return mask
    
    # Compute colony size to scale feathering
    area = np.sum(mask > 0)
    equivalent_radius = np.sqrt(area / np.pi)
    
    # Scale feathering: tiny colonies get minimal feathering
    if equivalent_radius < 5:
        feather_px = 1
    elif equivalent_radius < 10:
        feather_px = 2
    # else keep the default
    
    # Gaussian blur directly on the mask for soft edges
    blur_size = feather_px * 2 + 1  # Must be odd
    feathered = cv2.GaussianBlur(mask, (blur_size, blur_size), feather_px)
    
    return feathered


def fit_mask_cv(img_rgb):
    """
    Create a simple elliptical mask for the colony.
    Used as fallback when SAM is unavailable.
    """
    h, w = img_rgb.shape[:2]
    
    # Create a filled ellipse mask inscribed in the crop
    mask = np.zeros((h, w), dtype=np.uint8)
    center = (w // 2, h // 2)
    axes = (max(1, w // 2 - 1), max(1, h // 2 - 1))
    
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
        
    return mask

def extract_colony(image_path, bbox, class_id, output_dir, sam_model=None):
    """
    Extract a single colony using SAM or CV fallback and save as RGBA asset.
    bbox: [x_min, y_min, x_max, y_max]
    """
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return False
            
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        mask = None
        
        # Try SAM if available
        if sam_model:
            try:
                results = sam_model(img_rgb, bboxes=[bbox], verbose=False)
                if results and results[0].masks:
                    mask = results[0].masks.data[0].cpu().numpy().astype(np.uint8) * 255
            except Exception as e:
                logger.warning(f"SAM inference failed: {e}")
        
        # Fallback to CV extraction on CROP
        if mask is None:
            x1, y1, x2, y2 = map(int, bbox)
            padding = 5
            h, w = img.shape[:2]
            cx1 = max(0, x1 - padding)
            cy1 = max(0, y1 - padding)
            cx2 = min(w, x2 + padding)
            cy2 = min(h, y2 + padding)
            
            crop_rgb = img_rgb[cy1:cy2, cx1:cx2]
            
            if crop_rgb.size == 0: return False
            
            local_mask = fit_mask_cv(crop_rgb)
            
            # Embed local mask into full image size mask
            mask = np.zeros((h, w), dtype=np.uint8)
            mask[cy1:cy2, cx1:cx2] = local_mask

        # Refine mask (optional morphological ops)
        # kernel = np.ones((3,3), np.uint8)
        # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Get background stats before creating RGBA
        bg_mean, bg_std = get_background_stats(img_rgb, mask)
        
        # Crop to bbox with padding
        x1, y1, x2, y2 = map(int, bbox)
        padding = 10
        h, w = img.shape[:2]
        
        x1_nopad, y1_nopad, x2_nopad, y2_nopad = x1, y1, x2, y2
        
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)
        
        crop_img = img_rgb[y1:y2, x1:x2]
        crop_mask = mask[y1:y2, x1:x2]
        
        # Create RGBA
        b, g, r = cv2.split(crop_img) # actually it was RGB now
        rgba = cv2.merge([b, g, r, crop_mask])
        
        # Save asset
        class_dir = os.path.join(output_dir, str(class_id))
        os.makedirs(class_dir, exist_ok=True)
        
        asset_name = f"{Path(image_path).stem}_{x1_nopad}_{y1_nopad}.png"
        save_path = os.path.join(class_dir, asset_name)
        
        # Convert back to BGR for saving with cv2
        save_img = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
        cv2.imwrite(save_path, save_img)
        
        # Save metadata
        meta = {
            "source_image": str(image_path),
            "original_bbox": [x1_nopad, y1_nopad, x2_nopad, y2_nopad],
            "bg_mean": bg_mean.tolist() if isinstance(bg_mean, np.ndarray) else bg_mean,
            "bg_std": bg_std.tolist() if isinstance(bg_std, np.ndarray) else bg_std,
            "area": float(np.sum(mask > 0))
        }
        
        with open(save_path.replace('.png', '.json'), 'w') as f:
            json.dump(meta, f, indent=2)
            
        return True

    except Exception as e:
        logger.error(f"Error extracting from {image_path}: {e}")
        return False

def process_dataset(images_dir, annotations_path, output_dir, use_sam=True):
    """
    Main loop to process dataset.
    Supports COCO JSON format.
    """
    sam = load_sam_model() if use_sam else None
    # if not sam: return # Do not exit, continue with fallback

    # Load annotations
# ... (rest of function)

def process_single_image(image_path, json_path, output_dir, use_sam=True):
    """
    Process a single image with its specific JSON annotation file (AGAR format).
    JSON format expected: {"labels": [{"x": int, "y": int, "width": int, "height": int, "class": str}, ...]}
    """
    sam = load_sam_model() if use_sam else None
    # if not sam: return # Continue with fallback
    logger.info(f"Loading annotations from {annotations_path}...")
    with open(annotations_path) as f:
        coco = json.load(f)
    
    # Map image IDs to filenames
    img_map = {img['id']: img for img in coco['images']}
    
    # Process annotations
    logger.info(f"Processing {len(coco['annotations'])} annotations...")
    
    success_count = 0
    
    # Group by image to minimize IO
    anns_by_image = {}
    for ann in coco['annotations']:
        img_id = ann['image_id']
        if img_id not in anns_by_image:
            anns_by_image[img_id] = []
        anns_by_image[img_id].append(ann)
        
    for img_id, anns in tqdm(anns_by_image.items()):
        img_info = img_map.get(img_id)
        if not img_info:
            continue
            
        filename = img_info['file_name']
        img_path = os.path.join(images_dir, filename)
        
        if not os.path.exists(img_path):
            logger.warning(f"Image not found: {img_path}")
            continue
            
        # Optimize: Load image once per file
        try:
            full_img = cv2.imread(img_path)
            if full_img is None:
               continue
            full_img_rgb = cv2.cvtColor(full_img, cv2.COLOR_BGR2RGB)
        except:
            continue
            
        # Extract per annotation independently to use `extract_colony` logic or duplicate it.
        # Given we updated `extract_colony`, let's just loop and use it? 
        # But `extract_colony` reloads image. For speed we should implement inline or refactor:
        # Refactoring to use inline logic for batch efficiency
        
        bboxes = []
        class_ids = []
        
        for ann in anns:
            bbox = ann['bbox'] # [x, y, w, h]
            x, y, w, h = map(int, bbox)
            x1, y1, x2, y2 = x, y, x + w, y + h
            bboxes.append([x1, y1, x2, y2])
            class_ids.append(ann['category_id'])

        if not bboxes: continue
        
        # Batch SAM inference if available
        masks = None
        if sam:
            try:
                results = sam(full_img_rgb, bboxes=bboxes, verbose=False)
                if results and results[0].masks:
                    masks = results[0].masks.data.cpu().numpy().astype(np.uint8) * 255
            except Exception as e:
                logger.warning(f"SAM batch failed for {filename}: {e}")
        
        # Loop through bboxes
        for idx, bbox in enumerate(bboxes):
            class_id = class_ids[idx]
            
            mask = None
            if masks is not None and idx < len(masks):
                mask = masks[idx]
            
            # Fallback CV
            if mask is None:
                x1, y1, x2, y2 = bbox
                padding = 5
                h_img, w_img = full_img_rgb.shape[:2]
                cx1 = max(0, x1 - padding)
                cy1 = max(0, y1 - padding)
                cx2 = min(w_img, x2 + padding)
                cy2 = min(h_img, y2 + padding)
                
                crop_rgb = full_img_rgb[cy1:cy2, cx1:cx2]
                if crop_rgb.size == 0: continue
                
                local_mask = fit_mask_cv(crop_rgb)
                 # Embed local mask into full image size mask
                mask = np.zeros((h_img, w_img), dtype=np.uint8)
                mask[cy1:cy2, cx1:cx2] = local_mask
                
            # bg stats
            bg_mean, bg_std = get_background_stats(full_img_rgb, mask)
            
            # Crop
            x1, y1, x2, y2 = bbox
            padding = 10
            h_img, w_img = full_img_rgb.shape[:2]
            
            cx1 = max(0, x1 - padding)
            cy1 = max(0, y1 - padding)
            cx2 = min(w_img, x2 + padding)
            cy2 = min(h_img, y2 + padding)
            
            crop_rgb = full_img_rgb[cy1:cy2, cx1:cx2]
            crop_mask = mask[cy1:cy2, cx1:cx2]
            
            if crop_rgb.shape[:2] != crop_mask.shape: continue
                
            # Merge RGBA
            r, g, b = cv2.split(crop_rgb)
            rgba = cv2.merge([r, g, b, crop_mask])
            
            # Save
            class_dir = os.path.join(output_dir, str(class_id))
            os.makedirs(class_dir, exist_ok=True)
            
            clean_fname = Path(filename).stem
            asset_name = f"{clean_fname}_{int(x1)}_{int(y1)}.png"
            save_path = os.path.join(class_dir, asset_name)
            
            save_img = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
            cv2.imwrite(save_path, save_img)
            
            # Metadata
            meta = {
                "species_id": class_id,
                "source_image": filename,
                "bbox": bbox,
                "bg_mean": bg_mean.tolist() if isinstance(bg_mean, np.ndarray) else bg_mean,
                "bg_std": bg_std.tolist() if isinstance(bg_std, np.ndarray) else bg_std,
                "area_px": float(np.sum(mask > 0))
            }
                
            with open(save_path.replace('.png', '.json'), 'w') as fmeta:
                json.dump(meta, fmeta, indent=2)
                
            success_count += 1


    logger.info(f"Extraction complete. Extracted {success_count} assets.")

def process_single_image(image_path, json_path, output_dir, use_sam=True):
    """
    Process a single image with its specific JSON annotation file (AGAR format).
    JSON format expected: {"labels": [{"x": int, "y": int, "width": int, "height": int, "class": str}, ...]}
    """
    sam = load_sam_model() if use_sam else None
    # if not sam: return # Continue with fallback

    if not os.path.exists(image_path):
        logger.error(f"Image not found: {image_path}")
        return
    
    if not os.path.exists(json_path):
        logger.error(f"JSON not found: {json_path}")
        return

    logger.info(f"Processing single image: {image_path}")
    
    with open(json_path) as f:
        data = json.load(f)
        
    labels = data.get('labels', [])
    if not labels:
        logger.warning("No labels found in JSON.")
        return

    bboxes = []
    class_ids = []
    
    # AGAR format to BBox [x1, y1, x2, y2]
    for label in labels:
        x, y = label['x'], label['y']
        w, h = label['width'], label['height']
        x1, y1, x2, y2 = x, y, x + w, y + h
        bboxes.append([x1, y1, x2, y2])
        class_ids.append(label['class'])

    full_img = cv2.imread(image_path)
    if full_img is None:
        logger.error("Failed to read image")
        return
    
    # Remove text from source image BEFORE extraction
    full_img = remove_text_from_image(full_img)
    
    full_img_rgb = cv2.cvtColor(full_img, cv2.COLOR_BGR2RGB)
    
    success_count = 0
    try:
        # Process each bbox individually (SAM batch on many bboxes is unstable)
        for idx, bbox in enumerate(bboxes):
            class_id = class_ids[idx]
            
            mask = None
            
            # Try SAM for this single bbox
            if sam:
                try:
                    results = sam(full_img_rgb, bboxes=[bbox], verbose=False)
                    if results and results[0].masks:
                        mask = results[0].masks.data[0].cpu().numpy().astype(np.uint8) * 255
                except Exception as e:
                    logger.warning(f"SAM failed for bbox {idx}: {e}")
            
            # Fallback to elliptical mask
            if mask is None:
                x1, y1, x2, y2 = bbox
                padding = 5
                h_img, w_img = full_img_rgb.shape[:2]
                cx1 = max(0, x1 - padding)
                cy1 = max(0, y1 - padding)
                cx2 = min(w_img, x2 + padding)
                cy2 = min(h_img, y2 + padding)
                
                crop_rgb = full_img_rgb[cy1:cy2, cx1:cx2]
                if crop_rgb.size == 0: continue
                local_mask = fit_mask_cv(crop_rgb)
                 # Embed
                mask = np.zeros((h_img, w_img), dtype=np.uint8)
                mask[cy1:cy2, cx1:cx2] = local_mask

            # Regularize mask for roundness
            mask = regularize_mask(mask)
            
            # bg stats (before feathering)
            bg_mean, bg_std = get_background_stats(full_img_rgb, mask)
            
            # Feather alpha for soft edges
            alpha_mask = feather_alpha(mask, feather_px=3)
            
            # Crop
            x1, y1, x2, y2 = map(int, bbox)
            padding = 10
            h_img, w_img = full_img_rgb.shape[:2]
            
            cx1 = max(0, x1 - padding)
            cy1 = max(0, y1 - padding)
            cx2 = min(w_img, x2 + padding)
            cy2 = min(h_img, y2 + padding)
            
            crop_rgb = full_img_rgb[cy1:cy2, cx1:cx2]
            crop_alpha = alpha_mask[cy1:cy2, cx1:cx2]
            
            if crop_rgb.shape[:2] != crop_alpha.shape: continue
                
            # Merge RGBA with feathered alpha
            r, g, b = cv2.split(crop_rgb)
            rgba = cv2.merge([r, g, b, crop_alpha])
            
            # Save
            safe_class = "".join([c for c in str(class_id) if c.isalnum() or c in (' ', '_', '-')]).strip()
            class_dir = os.path.join(output_dir, safe_class)
            os.makedirs(class_dir, exist_ok=True)
            
            clean_fname = Path(image_path).stem
            asset_name = f"{clean_fname}_{int(x1)}_{int(y1)}.png"
            save_path = os.path.join(class_dir, asset_name)
            
            save_img = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)
            cv2.imwrite(save_path, save_img)
            
            # Metadata
            meta = {
                "species_id": class_id,
                "source_image": Path(image_path).name,
                "bbox": bbox,
                "bg_mean": bg_mean.tolist() if isinstance(bg_mean, np.ndarray) else bg_mean,
                "bg_std": bg_std.tolist() if isinstance(bg_std, np.ndarray) else bg_std,
                "area_px": float(np.sum(mask > 0))
            }
                
            with open(save_path.replace('.png', '.json'), 'w') as fmeta:
                json.dump(meta, fmeta, indent=2)
                
            success_count += 1
                
        logger.info(f"Extracted {success_count} colonies from single image.")
        
    except Exception as e:
        logger.error(f"Error during extraction: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", default="images", help="Path to images directory or single image")
    parser.add_argument("--annotations", default="annotations/annot_COCO.json", help="Path to COCO annotations or single JSON")
    parser.add_argument("--output", default="assets/colonies", help="Output directory")
    parser.add_argument("--single", action="store_true", help="Process as single image/json pair")
    parser.add_argument("--no-sam", action="store_true", help="Skip SAM loading and use CV fallback")
    args = parser.parse_args()
    
    if args.single:
        process_single_image(args.images, args.annotations, args.output, use_sam=not args.no_sam)
    else:
        process_dataset(args.images, args.annotations, args.output, use_sam=not args.no_sam)
