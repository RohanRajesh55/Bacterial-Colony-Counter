"""
Unit tests for PetriDishDetector.
Tests the multi-technique dish detection cascade.
"""

import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

# Add models path
sys.path.insert(0, str(Path(__file__).parent.parent / 'models'))

from petri_dish_detector import PetriDishDetector


class TestPetriDishDetector:
    """Test cases for PetriDishDetector."""
    
    @pytest.fixture
    def detector(self):
        return PetriDishDetector(padding_ratio=0.02)
    
    def create_synthetic_dish_image(self, 
                                    size=(800, 800), 
                                    dish_center=None, 
                                    dish_radius=None,
                                    background_color=(30, 30, 30),
                                    dish_color=(200, 180, 160)):
        """Create a synthetic petri dish image for testing."""
        h, w = size
        if dish_center is None:
            dish_center = (w // 2, h // 2)
        if dish_radius is None:
            dish_radius = min(h, w) // 3
        
        # Create image with background
        img = np.full((h, w, 3), background_color, dtype=np.uint8)
        
        # Draw dish circle
        cv2.circle(img, dish_center, dish_radius, dish_color, -1)
        
        # Add some noise/texture to make it realistic
        noise = np.random.randint(-10, 10, (h, w, 3), dtype=np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return img, dish_center, dish_radius
    
    def test_detect_centered_dish(self, detector):
        """Test detection of a centered petri dish."""
        img, expected_center, expected_radius = self.create_synthetic_dish_image()
        
        result = detector.detect(img)
        
        assert result['detected'] is True
        assert result['confidence'] > 0.5
        assert result['mask'] is not None
        
        # Center should be close to expected (within 10% tolerance)
        cx, cy = result['center']
        ex, ey = expected_center
        tolerance = expected_radius * 0.1
        assert abs(cx - ex) < tolerance
        assert abs(cy - ey) < tolerance
    
    def test_detect_small_dish(self, detector):
        """Test detection when dish is far away (small in frame)."""
        img, expected_center, expected_radius = self.create_synthetic_dish_image(
            size=(1000, 1000),
            dish_radius=150  # Only 15% of image
        )
        
        result = detector.detect(img)
        
        assert result['detected'] is True
        assert result['confidence'] > 0.3
    
    def test_detect_large_dish(self, detector):
        """Test detection when dish is close (large in frame)."""
        img, expected_center, expected_radius = self.create_synthetic_dish_image(
            size=(800, 800),
            dish_radius=350  # 87.5% of image dimension
        )
        
        result = detector.detect(img)
        
        # Large dishes should still be detected
        assert result['detected'] is True
    
    def test_detect_off_center_dish(self, detector):
        """Test detection of off-center dish."""
        img, expected_center, expected_radius = self.create_synthetic_dish_image(
            size=(1000, 1000),
            dish_center=(700, 300),  # Off-center
            dish_radius=200
        )
        
        result = detector.detect(img)
        
        assert result['detected'] is True
        
        # Center should be detected correctly
        cx, cy = result['center']
        tolerance = expected_radius * 0.15
        assert abs(cx - 700) < tolerance
        assert abs(cy - 300) < tolerance
    
    def test_no_dish_returns_low_confidence(self, detector):
        """Test that images without dish return low confidence."""
        # Just a random noisy image
        img = np.random.randint(0, 255, (800, 800, 3), dtype=np.uint8)
        
        result = detector.detect(img)
        
        # Should return a result but with indication of no confident detection
        assert 'mask' in result
        # Method should be 'none' or confidence should be low
        if result['detected']:
            # Even if it thinks it detected something, confidence should be low
            assert result['confidence'] < 0.85
    
    def test_mask_shape_matches_image(self, detector):
        """Test that returned mask has same dimensions as input."""
        img, _, _ = self.create_synthetic_dish_image(size=(600, 800))
        
        result = detector.detect(img)
        
        assert result['mask'].shape == (600, 800)
    
    def test_is_inside_dish(self, detector):
        """Test the is_inside_dish helper function."""
        img, center, radius = self.create_synthetic_dish_image(
            dish_center=(400, 400),
            dish_radius=200
        )
        
        result = detector.detect(img)
        
        # Point inside dish
        inside_bbox = [350, 350, 370, 370]  # Center at (360, 360)
        assert detector.is_inside_dish(inside_bbox, result) == True
        
        # Point outside dish
        outside_bbox = [50, 50, 70, 70]  # Center at (60, 60)
        assert detector.is_inside_dish(outside_bbox, result) == False
    
    def test_draw_dish_outline(self, detector):
        """Test drawing dish outline on image."""
        img, _, _ = self.create_synthetic_dish_image()
        
        result = detector.detect(img)
        
        # Draw outline
        annotated = detector.draw_dish_outline(img.copy(), result)
        
        # Image should be modified (not identical to original)
        assert not np.array_equal(annotated, img)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
