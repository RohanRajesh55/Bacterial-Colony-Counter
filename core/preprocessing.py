"""
Advanced Bacterial Colony Image Preprocessing Pipeline
Optimized for 18,000+ images with robustness enhancements.

Upgrade Features:
- LAB Color Space (L-channel)
- Bilateral Filtering
- Dynamic Rim Cropping
- Morphological Opening
- Robust Marker Generation (Local Maxima + Sure Background)
- Failure Logging

Usage:
    from preprocessing_pipeline import PreprocessingPipeline
    pipeline = PreprocessingPipeline(output_dir='processed_output')
    pipeline.process_directory('path/to/images', num_workers=4)
"""

import cv2
import numpy as np
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import json
import traceback
import sys # Added for path manipulation

# Add root directory to path to allow importing sisr
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from sisr import SISRUpscaler
except ImportError:
    SISRUpscaler = None
    print("Warning: Could not import SISR modules.")

class PreprocessingPipeline:
    """
    Advanced configurable preprocessing pipeline for bacterial colony images.
    """
    
    def __init__(self, output_dir='processed_output', config=None):
        """
        Initialize the pipeline.
        
        Args:
            output_dir: Directory to save processed images.
            config: Optional dict to override default parameters.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.failure_log_path = self.output_dir / 'failures.txt'
        
        # Clear failure log if exists
        if self.failure_log_path.exists():
            self.failure_log_path.unlink()
        
        # Default configuration
        self.config = {
            # Pipeline version for tracking
            'pipeline_version': 'v1.0.0',
            
            # 1. Petri Dish Detection (Dynamic)
            'min_radius_ratio': 0.25,
            'max_radius_ratio': 0.55,
            'rim_crop_ratio': 0.98,       # Keep 98% of radius (Preserve rim colonies)
            
            # 2. Denoising (Bilateral Filter)
            'bilateral_d': 9,             # Diameter of pixel neighborhood
            'bilateral_sigma_color': 75,  # Filter sigma in color space
            'bilateral_sigma_space': 75,  # Filter sigma in coordinate space
            
            # 3. Contrast Enhancement (CLAHE)
            'clahe_clip_limit': 2.0,
            'clahe_grid_size': (8, 8),
            
            # 4. Background Correction (Top-Hat)
            'tophat_kernel_size': (25, 25),
            
            # 5. Thresholding
            'threshold_method': 'adaptive',
            'adaptive_block_size': 31,
            'adaptive_c': 5,
            
            # 6. Cleaning (Morphological Opening)
            'morph_open_kernel': 3,       # Size of kernel for removing dust
            
            # 7. Marker Generation
            'dist_transform_mask_size': 5,
            'local_max_min_dist': 10,     # This is implicitly handled by dilation method now
            
            # Performance limits
            'max_dimension': 2048,        # Resize if larger
            'timeout_seconds': 2.0,       # Max preprocessing time
            
            # Output
            'save_intermediate': False,
            'output_format': 'png',
        }
        
        if config:
            self.config.update(config)

        # Initialize SISR
        self.use_sisr = self.config.get('use_sisr', False)
        if self.use_sisr and SISRUpscaler:
            print(">> [Pipeline] Initializing SISR Upscaler...")
            try:
                self.sisr = SISRUpscaler()
            except Exception as e:
                print(f"Failed to init SISR: {e}")
                self.sisr = None
        else:
            self.sisr = None
    
    def process_image(self, img: np.ndarray) -> dict:
        """
        Process a single image with simplified preprocessing:
        1. Background removal (isolate petri dish)
        2. Lighting fix (CLAHE normalization)
        
        Args:
            img: BGR numpy array (as from cv2.imread)
            
        Returns:
            dict with 'processed', 'mask', 'dish_detected', 'metadata'
        """
        import time
        start_time = time.time()
        
        result = {
            'processed': None,
            'mask': None,
            'dish_detected': False,
            'metadata': {
                'pipeline_version': self.config['pipeline_version'],
                'original_shape': tuple(int(x) for x in img.shape),
                'processing_time_ms': 0,
                'status': 'pending',
                'error': None
            }
        }
        
        try:
            # Resize if too large (performance limit)
            h, w = img.shape[:2]
            max_dim = self.config['max_dimension']
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                result['metadata']['resized'] = True
                result['metadata']['scale'] = float(scale)
            
            # 0. SISR Upscaling
            if self.sisr:
                try:
                    img = self.sisr.upscale(img)
                    result['metadata']['sisr_applied'] = True
                    result['metadata']['new_shape'] = tuple(int(x) for x in img.shape)
                except Exception as e:
                    result['metadata']['sisr_error'] = str(e)
            
            # 1. BACKGROUND REMOVAL - Isolate Petri Dish
            mask, center, radius = self.isolate_petri_dish(img)
            result['dish_detected'] = center is not None
            result['metadata']['dish_center'] = tuple(int(x) for x in center) if center else None
            result['metadata']['dish_radius'] = int(radius) if radius else None
            
            # 2. LIGHTING FIX - CLAHE on L-channel
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
            
            clahe = cv2.createCLAHE(
                clipLimit=self.config['clahe_clip_limit'],
                tileGridSize=self.config['clahe_grid_size']
            )
            enhanced_l = clahe.apply(l_channel)
            
            # Merge back to color
            merged_lab = cv2.merge([enhanced_l, a, b])
            final_color = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
            
            # Apply mask to remove background
            if mask is not None:
                final_color = cv2.bitwise_and(final_color, final_color, mask=mask)
            
            result['processed'] = final_color
            result['mask'] = mask
            result['metadata']['status'] = 'success'
            
        except Exception as e:
            result['metadata']['status'] = 'failed'
            result['metadata']['error'] = str(e)
            result['processed'] = img  # Graceful degradation
        
        result['metadata']['processing_time_ms'] = int((time.time() - start_time) * 1000)
        return result
    
    def isolate_petri_dish(self, img):
        """
        Detect and isolate the circular petri dish using dynamic cropping.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Initial blur for circle detection (median is fine for this coarse step)
        blur = cv2.medianBlur(gray, 11)
        
        h = gray.shape[0]
        min_r = int(h * self.config['min_radius_ratio'])
        max_r = int(h * self.config['max_radius_ratio'])
        
        circles = cv2.HoughCircles(
            blur,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist= int(h * self.config.get('min_dist_ratio', 0.4)), # Slight relax from 0.5
            param1=self.config.get('hough_param1', 100),
            param2=self.config.get('hough_param2', 25), # Slightly more sensitive default (was 30)
            minRadius=min_r,
            maxRadius=max_r
        )
        
        mask = np.zeros_like(gray)
        center = None
        radius = None
        
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            x, y, r = circles[0]
            
            # Dynamic Crop: Keep 92% of detected radius (or 1.02 for outerlining)
            r = int(r * self.config['rim_crop_ratio'])
            center = (x, y)
            radius = r
            print(f"[DEBUG] Hough Success: Center={center}, Radius={radius}")
            
            cv2.circle(mask, (x, y), r, 255, -1)
            return mask, center, radius
        
        # --- Fallback: Contour Detection ---
        print("[DEBUG] Hough Failed. Attempting Contour Fallback...")
        return self.find_dish_via_contours(img, gray)

    def find_dish_via_contours(self, img, gray):
        """Fallback method to find dish using contours if Hough fails."""
        try:
            h, w = gray.shape
            
            # 1. Blur and Threshold
            blur = cv2.GaussianBlur(gray, (21, 21), 0)
            # Use Otsu's thresholding (start with standard BINARY)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Auto-Polarity: Check corners to handle dark vs light background
            inverted = False
            try:
                h_img, w_img = thresh.shape
                # Safe casting to python int to avoid overflow
                corners = [
                    int(thresh[0, 0]), int(thresh[0, w_img-1]), 
                    int(thresh[h_img-1, 0]), int(thresh[h_img-1, w_img-1])
                ]
                avg_corner = sum(corners) / 4
                print(f"[DEBUG] Polarity Check: Avg Corner Brightness={avg_corner}")
                # If average corner brightness > 127, likely light background -> Invert
                if avg_corner > 127:
                    print("[DEBUG] Inverting threshold (Light Background detected)")
                    thresh = cv2.bitwise_not(thresh)
                    inverted = True
            except Exception as e:
                print(f"[DEBUG] Polarity check exception: {e}")
                pass
            
            # 2. Find Contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                print("[DEBUG] No contours found.")
                return np.ones_like(gray) * 255, None, None
                
            # 3. Find Largest Contour (assumed to be the dish)
            c = max(contours, key=cv2.contourArea)
            
            # 4. Check if it's large enough
            area = cv2.contourArea(c)
            image_area = h * w
            print(f"[DEBUG] Max Contour Area: {area} (Threshold: {image_area * 0.05})")
            
            if area < (image_area * 0.05): # Less than 5% of image -> probably noise
                 print("[DEBUG] Contour too small.")
                 return np.ones_like(gray) * 255, None, None
            
            # 5. Fit Circle
            ((x, y), r) = cv2.minEnclosingCircle(c)
            print(f"[DEBUG] Fitted Circle: r={r}, center=({x},{y})")
            
            # Apply crop ratio
            r_final = int(r * self.config['rim_crop_ratio'])
            
            # Validate radius
            min_r = int(h * self.config['min_radius_ratio'])
            max_r = int(h * self.config['max_radius_ratio'])
            print(f"[DEBUG] Radius Check: {r_final} (Range: {min_r} - {max_r})")
            
            # Relaxed validation for fallback (allow slightly larger/smaller)
            # if r < min_r * 0.8 or r > max_r * 1.2:
            #      pass 

            mask = np.zeros_like(gray)
            center = (int(x), int(y))
            radius = int(r_final)
            
            cv2.circle(mask, center, radius, 255, -1)
            
            return mask, center, radius
            
        except Exception as e:
            # If fallback crashes, fail gracefully
            print(f"[DEBUG] Contour Fallback Exception: {e}")
            return np.ones_like(gray) * 255, None, None
            
    def apply_bilateral_filter(self, img):
        """Apply Bilateral Filter for edge-preserving smoothing."""
        return cv2.bilateralFilter(
            img, 
            self.config['bilateral_d'],
            self.config['bilateral_sigma_color'],
            self.config['bilateral_sigma_space']
        )

    def generate_markers(self, binary_img):
        """
        Generate markers for Watershed using Distance Transform + Local Maxima.
        """
        # 1. Sure Background (Dilation)
        kernel = np.ones((3,3), np.uint8)
        sure_bg = cv2.dilate(binary_img, kernel, iterations=3)
        
        # 2. Distance Transform
        dist_transform = cv2.distanceTransform(binary_img, cv2.DIST_L2, 5)
        
        # 3. Local Maxima Detection (using Dilation trick)
        # This acts as a max-filter
        dilated_dist = cv2.dilate(dist_transform, kernel)
        
        # A pixel is a local max if its value equals the local max value
        # AND it's above a minimal noise threshold
        peaks = (dist_transform == dilated_dist) & (dist_transform > 0.05 * dist_transform.max())
        sure_fg = np.uint8(peaks) * 255
        
        # 4. Unknown Region
        unknown = cv2.subtract(sure_bg, sure_fg)
        
        # 5. Marker Labeling
        ret, markers = cv2.connectedComponents(sure_fg)
        
        # Add 1 to all labels so that background is 1, not 0
        markers = markers + 1
        
        # Mark unknown region as 0
        markers[unknown == 255] = 0
        
        return markers, dist_transform

    def apply_unsharp_mask(self, img, kernel_size=(5, 5), sigma=1.0, amount=1.5, threshold=0):
        """Return a sharpened version of the image using Unsharp Masking."""
        blurred = cv2.GaussianBlur(img, kernel_size, sigma)
        sharpened = float(amount + 1) * img - float(amount) * blurred
        sharpened = np.maximum(sharpened, np.zeros(sharpened.shape))
        sharpened = np.minimum(sharpened, 255 * np.ones(sharpened.shape))
        return sharpened.round().astype(np.uint8)

    def process_single(self, image_path, save=True):
        """
        Process a single image through the full advanced pipeline.
        Returns the final sharpened image optimized for model training.
        """
        image_path = Path(image_path)
        img = cv2.imread(str(image_path))
        
        if img is None:
            return {'error': f'Could not read image: {image_path}'}
        
        results = {'filename': image_path.name, 'original_shape': img.shape}
        
        try:
            # 1. Isolate Dish (Mask Generation)
            mask, center, radius = self.isolate_petri_dish(img)
            results['dish_detected'] = center is not None
            results['dish_center'] = center
            results['dish_radius'] = radius
            
            # 2. Color Space: LAB -> L-Channel
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
            
            # 3. Denoise: Bilateral Filter on L-Channel
            denoised_l = self.apply_bilateral_filter(l_channel)
            
            # 4. Enhance: CLAHE on L-Channel
            # This balances the lighting, solving the "Red vs White Agar" issue by equating their lightness distributions.
            clahe = cv2.createCLAHE(
                clipLimit=self.config['clahe_clip_limit'],
                tileGridSize=self.config['clahe_grid_size']
            )
            enhanced_l = clahe.apply(denoised_l)
            
            # 4.5. Text/Artifact Removal: Morphological Closing
            # "Closes" small dark features (text, scratches) on the bright background.
            # Kernel size needs to be larger than the stroke width of the text but smaller than colonies.
            # (15,15) is a good heuristic for standard sharpie markers on petri dishes.
            kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            clean_l = cv2.morphologyEx(enhanced_l, cv2.MORPH_CLOSE, kernel_close)
            
            # 5. Background Correction: Top-Hat Transform
            # Now applied to the "clean" text-free image.
            # Top-Hat isolates BRIGHT objects (colonies) from the background.
            kernel_tophat = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, 
                self.config['tophat_kernel_size']
            )
            tophat_img = cv2.morphologyEx(clean_l, cv2.MORPH_TOPHAT, kernel_tophat)
            
            # 6. Feature Enhancement: Normalization & Unsharp Masking
            # Normalize Top-Hat to full dynamic range (0-255)
            tophat_norm = cv2.normalize(tophat_img, None, 0, 255, cv2.NORM_MINMAX)
            
            # Sharpen the L-channel component
            sharpened_l = self.apply_unsharp_mask(tophat_norm, amount=2.0)
            
            # 7. Color Reconstruction (Crucial for Classification)
            # We combine the "Lighting Corrected" L-channel with the original Color (A, B) channels.
            # Since Top-Hat removed the background from L (making it black), 
            # the reconstructed RGB will have a black background but colored colonies.
            merged_lab = cv2.merge([sharpened_l, a, b])
            final_color = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
            
            # Generate Binary (Adaptive Threshold) for reference
            binary = self.get_binary(sharpened_l, mask)
            
            # Apply detection mask to remove rim noise
            if mask is not None:
                final_color = cv2.bitwise_and(final_color, final_color, mask=mask)
                # binary is already masked in get_binary
            
            # Store results
            results['final_processed'] = final_color # Now RGB
            results['binary'] = binary
            results['l_channel'] = l_channel
            results['enhanced_l'] = enhanced_l
            results['tophat'] = tophat_norm 
            
            # Save output (Single Optimized Image)
            if save:
                ext = self.config['output_format']
                stem = image_path.stem
                
                # The ONE output file for model training (RGB)
                cv2.imwrite(str(self.output_dir / f"{stem}_processed.{ext}"), final_color)
                
                # Save intermediates only if requested
                if self.config['save_intermediate']:
                    cv2.imwrite(str(self.output_dir / f"{stem}_binary.{ext}"), self.get_binary(tophat_img, mask))
                    cv2.imwrite(str(self.output_dir / f"{stem}_tophat.{ext}"), tophat_img)

        except Exception as e:
            return {'error': str(e), 'traceback': traceback.format_exc()}
            
        return results

    def get_binary(self, tophat_img, mask):
        """Helper to get binary mask for intermediate saving."""
        if self.config['threshold_method'] == 'otsu':
            _, binary = cv2.threshold(tophat_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            binary = cv2.adaptiveThreshold(
                tophat_img, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                self.config['adaptive_block_size'],
                self.config['adaptive_c']
            )
        if mask is not None:
            binary = cv2.bitwise_and(binary, binary, mask=mask)
        return binary

    def log_failure(self, filename, error_msg):
        """Append failure to log file."""
        with open(self.failure_log_path, 'a') as f:
            f.write(f"{filename}: {error_msg}\n")
            
    def process_directory(self, input_dir, num_workers=4, extensions=('jpg', 'jpeg', 'png')):
        """
        Process directory with failure logging and parallel execution.
        """
        input_dir = Path(input_dir)
        image_paths = []
        for ext in extensions:
            image_paths.extend(input_dir.glob(f'*.{ext}'))
            image_paths.extend(input_dir.glob(f'*.{ext.upper()}'))
        
        print(f"Found {len(image_paths)} images to process.")
        
        results = []
        failed_count = 0
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(self.process_single, p): p for p in image_paths}
            
            for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
                path = futures[future]
                try:
                    result = future.result()
                    if 'error' in result:
                        failed_count += 1
                        self.log_failure(path.name, result['error'])
                    else:
                        results.append({'filename': result['filename']})
                except Exception as e:
                    failed_count += 1
                    self.log_failure(path.name, str(e))
        
        print(f"\nProcessing complete: {len(results)} successful, {failed_count} failed.")
        print(f"Failures logged to: {self.failure_log_path}")
        
        return results

# --- Standalone execution ---
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced Bacterial Colony Image Preprocessor')
    parser.add_argument('input_dir', help='Input directory containing images')
    parser.add_argument('--output', '-o', default='processed_output', help='Output directory')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--debug', action='store_true', help='Save intermediate images')
    
    args = parser.parse_args()
    
    config = {'save_intermediate': args.debug}
    pipeline = PreprocessingPipeline(output_dir=args.output, config=config)
    pipeline.process_directory(args.input_dir, num_workers=args.workers)
