"""
Robust Petri Dish Detection Module

Multi-technique cascading approach for detecting petri dishes regardless of 
camera distance or perspective. Uses:
1. Edge-based contour detection with ellipse fitting
2. Adaptive Hough circles with multiple parameter attempts  
3. Color-based segmentation fallback

Author: Auto-generated
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class PetriDishDetector:
    """
    Robust petri dish detector that works across variable distances and perspectives.
    Returns dish location, mask, and confidence score.
    """
    
    # Confidence threshold to skip remaining detection methods
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    
    def __init__(self, padding_ratio: float = 0.02):
        """
        Args:
            padding_ratio: Extra margin to add around detected dish (0.02 = 2%)
        """
        self.padding_ratio = padding_ratio
    
    def detect(self, image: np.ndarray) -> Dict:
        """
        Detect petri dish using multi-technique cascade.
        
        Args:
            image: BGR image (OpenCV format)
            
        Returns:
            Dict with keys:
                - center: (x, y) tuple
                - radius: int (for circles) or None
                - axes: (major, minor) tuple (for ellipses) or None
                - angle: float rotation angle (for ellipses) or 0
                - mask: np.ndarray binary mask of dish area
                - confidence: float 0.0-1.0
                - method: str name of detection method used
                - detected: bool whether dish was found
        """
        h, w = image.shape[:2]
        results = []
        
        # Stage 1: Edge-based contour detection (most reliable)
        result = self._detect_via_contours(image)
        if result:
            results.append(result)
            if result["confidence"] >= self.HIGH_CONFIDENCE_THRESHOLD:
                logger.info(f"High confidence contour detection ({result['confidence']:.2f}), skipping other methods")
                return self._finalize_result(result, image)
        
        # Stage 2: Adaptive Hough circles
        result = self._detect_via_hough(image)
        if result:
            results.append(result)
            if result["confidence"] >= self.HIGH_CONFIDENCE_THRESHOLD:
                logger.info(f"High confidence Hough detection ({result['confidence']:.2f}), skipping color method")
                return self._finalize_result(result, image)
        
        # Stage 3: Color-based segmentation (fallback)
        result = self._detect_via_color(image)
        if result:
            results.append(result)
        
        # Return best result or failure
        if results:
            best = max(results, key=lambda r: r["confidence"])
            logger.info(f"Selected {best['method']} with confidence {best['confidence']:.2f}")
            return self._finalize_result(best, image)
        
        # No detection - return empty result
        logger.warning("No petri dish detected by any method")
        return {
            "center": (w // 2, h // 2),
            "radius": min(w, h) // 2,
            "axes": None,
            "angle": 0,
            "mask": np.ones((h, w), dtype=np.uint8) * 255,  # Full image mask
            "confidence": 0.0,
            "method": "none",
            "detected": False
        }
    
    def _detect_via_contours(self, image: np.ndarray) -> Optional[Dict]:
        """
        Detect dish using edge-based contour detection with ellipse fitting.
        Handles perspective distortion well.
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            
            # Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Adaptive Canny thresholds based on image median
            median_val = np.median(blurred)
            lower = int(max(0, 0.66 * median_val))
            upper = int(min(255, 1.33 * median_val))
            edges = cv2.Canny(blurred, lower, upper)
            
            # Dilate edges to close gaps
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Filter contours by size (dish should be significant portion of image)
            min_area = (min(h, w) * 0.1) ** 2 * np.pi  # At least 10% of image dimension as radius
            valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
            
            if not valid_contours:
                return None
            
            # Get largest contour
            largest = max(valid_contours, key=cv2.contourArea)
            
            # Need at least 5 points to fit ellipse
            if len(largest) < 5:
                return None
            
            # Fit ellipse
            ellipse = cv2.fitEllipse(largest)
            center, axes, angle = ellipse
            center = (int(center[0]), int(center[1]))
            
            # Calculate circularity (minor/major axis ratio)
            major, minor = max(axes), min(axes)
            if major == 0:
                return None
            circularity = minor / major
            
            # Validate: should be reasonably circular (>0.6 allows some perspective)
            if circularity < 0.6:
                logger.debug(f"Contour rejected: circularity {circularity:.2f} < 0.6")
                return None
            
            # Validate: center should be roughly in image bounds
            if not (0 < center[0] < w and 0 < center[1] < h):
                return None
            
            # Validate: ellipse shouldn't be larger than image
            if major > max(h, w) * 0.95:
                return None
            
            # Confidence based on circularity and contour solidity
            hull = cv2.convexHull(largest)
            hull_area = cv2.contourArea(hull)
            contour_area = cv2.contourArea(largest)
            solidity = contour_area / hull_area if hull_area > 0 else 0
            
            confidence = (circularity * 0.6 + solidity * 0.4)
            
            return {
                "center": center,
                "radius": int(major / 2),  # Use major axis as radius for mask
                "axes": (major / 2, minor / 2),
                "angle": angle,
                "confidence": min(confidence, 1.0),
                "method": "contour_ellipse",
                "detected": True
            }
            
        except Exception as e:
            logger.debug(f"Contour detection failed: {e}")
            return None
    
    def _detect_via_hough(self, image: np.ndarray) -> Optional[Dict]:
        """
        Detect dish using adaptive Hough circles.
        Tries multiple param2 values for robustness.
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            min_dim = min(h, w)
            
            # Blur for noise reduction
            blurred = cv2.medianBlur(gray, 11)
            
            # Adaptive radius range: 10%-45% of smaller dimension
            min_r = int(min_dim * 0.10)
            max_r = int(min_dim * 0.45)
            
            # Try multiple param2 values (accumulator threshold)
            # Higher = fewer false positives but might miss weak circles
            param2_values = [50, 40, 30, 20]
            
            for param2 in param2_values:
                circles = cv2.HoughCircles(
                    blurred,
                    cv2.HOUGH_GRADIENT,
                    dp=1.2,
                    minDist=min_dim // 2,
                    param1=100,
                    param2=param2,
                    minRadius=min_r,
                    maxRadius=max_r
                )
                
                if circles is not None:
                    circles = np.round(circles[0, :]).astype("int")
                    
                    # Pick the largest circle (most likely the dish)
                    x, y, r = max(circles, key=lambda c: c[2])
                    
                    # Validate: center should be in image
                    if not (r < x < w - r and r < y < h - r):
                        continue
                    
                    # Calculate confidence based on edge strength along perimeter
                    confidence = self._calculate_circle_confidence(gray, x, y, r, param2)
                    
                    logger.debug(f"Hough found circle at ({x}, {y}) r={r} with param2={param2}, conf={confidence:.2f}")
                    
                    return {
                        "center": (x, y),
                        "radius": r,
                        "axes": None,
                        "angle": 0,
                        "confidence": confidence,
                        "method": "hough_circle",
                        "detected": True
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"Hough detection failed: {e}")
            return None
    
    def _calculate_circle_confidence(self, gray: np.ndarray, x: int, y: int, r: int, param2: int) -> float:
        """
        Calculate confidence score for a detected circle based on edge strength.
        """
        # Sample points along the circle perimeter
        angles = np.linspace(0, 2 * np.pi, 36)
        edge_strengths = []
        
        # Compute gradient magnitude
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(sobelx**2 + sobely**2)
        gradient_mag = (gradient_mag / gradient_mag.max() * 255).astype(np.uint8)
        
        h, w = gray.shape
        for angle in angles:
            px = int(x + r * np.cos(angle))
            py = int(y + r * np.sin(angle))
            if 0 <= px < w and 0 <= py < h:
                edge_strengths.append(gradient_mag[py, px])
        
        if not edge_strengths:
            return 0.5
        
        # Normalize edge strength to 0-1
        avg_edge = np.mean(edge_strengths) / 255
        
        # Bonus for finding circle with higher param2 (more strict)
        param2_bonus = (param2 - 20) / 40  # 0 for param2=20, 0.75 for param2=50
        
        confidence = avg_edge * 0.7 + param2_bonus * 0.3
        return min(confidence + 0.3, 1.0)  # Base confidence boost
    
    def _detect_via_color(self, image: np.ndarray) -> Optional[Dict]:
        """
        Detect dish using color-based segmentation.
        Looks for the largest uniform blob, assuming it's the dish.
        """
        try:
            h, w = image.shape[:2]
            
            # Convert to LAB color space (better for uniform regions)
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]
            
            # Blur to reduce noise
            blurred = cv2.GaussianBlur(l_channel, (15, 15), 0)
            
            # Otsu threshold to separate foreground from background
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Try both the binary and its inverse (dish could be brighter or darker)
            for mask in [binary, cv2.bitwise_not(binary)]:
                # Morphological cleanup
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if not contours:
                    continue
                
                # Get largest contour
                largest = max(contours, key=cv2.contourArea)
                contour_area = cv2.contourArea(largest)
                
                # Must be significant (at least 5% of image)
                if contour_area < h * w * 0.05:
                    continue
                
                # Fit ellipse if enough points
                if len(largest) >= 5:
                    ellipse = cv2.fitEllipse(largest)
                    center, axes, angle = ellipse
                    center = (int(center[0]), int(center[1]))
                    major, minor = max(axes), min(axes)
                    
                    # Check circularity
                    circularity = minor / major if major > 0 else 0
                    
                    if circularity > 0.65:
                        # Calculate fill ratio (how well contour fills its bounding ellipse)
                        ellipse_area = np.pi * (axes[0] / 2) * (axes[1] / 2)
                        fill_ratio = contour_area / ellipse_area if ellipse_area > 0 else 0
                        
                        confidence = fill_ratio * circularity * 0.7  # Lower base for fallback
                        
                        return {
                            "center": center,
                            "radius": int(major / 2),
                            "axes": (major / 2, minor / 2),
                            "angle": angle,
                            "confidence": min(confidence, 0.85),  # Cap fallback confidence
                            "method": "color_segmentation",
                            "detected": True
                        }
            
            return None
            
        except Exception as e:
            logger.debug(f"Color detection failed: {e}")
            return None
    
    def _finalize_result(self, result: Dict, image: np.ndarray) -> Dict:
        """
        Create the final mask and add padding buffer.
        """
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        center = result["center"]
        
        if result.get("axes"):
            # Ellipse mask
            axes = result["axes"]
            # Add padding
            padded_axes = (
                int(axes[0] * (1 + self.padding_ratio)),
                int(axes[1] * (1 + self.padding_ratio))
            )
            cv2.ellipse(mask, center, padded_axes, result["angle"], 0, 360, 255, -1)
        else:
            # Circle mask
            radius = result["radius"]
            padded_radius = int(radius * (1 + self.padding_ratio))
            cv2.circle(mask, center, padded_radius, 255, -1)
        
        result["mask"] = mask
        return result
    
    def draw_dish_outline(self, image: np.ndarray, detection_result: Dict, 
                          color: Tuple[int, int, int] = (0, 255, 0), 
                          thickness: int = 2) -> np.ndarray:
        """
        Draw the detected dish boundary on the image.
        
        Args:
            image: Image to draw on (will be modified in place)
            detection_result: Result from detect()
            color: BGR color for outline
            thickness: Line thickness
            
        Returns:
            Image with dish outline drawn
        """
        if not detection_result.get("detected", False):
            return image
        
        center = detection_result["center"]
        
        if detection_result.get("axes"):
            # Draw ellipse
            axes = (int(detection_result["axes"][0]), int(detection_result["axes"][1]))
            angle = detection_result.get("angle", 0)
            cv2.ellipse(image, center, axes, angle, 0, 360, color, thickness)
        else:
            # Draw circle
            radius = detection_result["radius"]
            cv2.circle(image, center, radius, color, thickness)
        
        return image
    
    def is_inside_dish(self, bbox: List[float], detection_result: Dict) -> bool:
        """
        Check if a bounding box center is inside the detected dish.
        
        Args:
            bbox: [x1, y1, x2, y2] bounding box
            detection_result: Result from detect()
            
        Returns:
            True if bbox center is inside dish
        """
        if not detection_result.get("detected", False):
            return True  # No dish detected, accept all
        
        # Calculate bbox center
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        
        # Check against mask
        mask = detection_result.get("mask")
        if mask is not None:
            h, w = mask.shape
            if 0 <= int(cy) < h and 0 <= int(cx) < w:
                return mask[int(cy), int(cx)] > 0
        
        return True
