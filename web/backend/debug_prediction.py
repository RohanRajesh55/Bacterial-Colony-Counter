import sys
import os
import cv2
from pathlib import Path

# Debugging environment
print(f"Python Executable: {sys.executable}")
print(f"Python Path: {sys.path}")

# Add parent directory to path to allow importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.yolo_model import YOLOModel
from backend.config import get_settings

def debug_image(image_path):
    settings = get_settings()
    
    # Initialize model
    model_path = Path(settings.yolo_model_path)
    if not model_path.exists():
        print(f"Error: Model not found at {model_path}")
        # Try absolute path based on cwd
        model_path = Path("models/yolo/best.pt")
        if not model_path.exists():
             print(f"Error: Model also not found at {model_path}. CWD: {os.getcwd()}")
             return

    print(f"Loading model from: {model_path}")
    
    try:
        model = YOLOModel(
            model_path=str(model_path), 
            class_names=settings.class_names,
            conf_threshold=0.25,
            device="cpu"
        )
    except Exception as e:
        print(f"Failed to load model: {e}")
        return

    # Load Image
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return
        
    img = cv2.imread(image_path)
    if img is None:
        print("Error: Failed to read image using cv2")
        return
    
    print(f"Image loaded: {img.shape}")
    
    # Try converting to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Test Standard vs Tiled
    print(f"\n--- Testing Standard Inference (RGB) ---")
    try:
        result = model.predict(img_rgb, conf_threshold=0.25, draw_boxes=False)
        print(f"Standard Count: {result.get('count', 0)}")
    except Exception as e:
        print(f"Standard failed: {e}")

    print(f"\n--- Testing Tiled Inference (RGB, 320px tiles) ---")
    try:
        # Force small tile size to verify tiling logic works even on small image
        result = model.predict_tiled(img_rgb, conf_threshold=0.25, tile_size=320, draw_boxes=False) 
        print(f"Tiled Count: {result.get('total_count', 0)}")
        if result.get('total_count', 0) > 0:
             print(f"Class Distribution: {result.get('class_counts')}")
    except Exception as e:
        print(f"Tiled failed: {e}")

if __name__ == "__main__":
    # Replace this path with the image you want to analyze
    # Example: r"C:\Users\rohan\Downloads\test_image.jpg"
    img_path = r"C:\Bacterial colony counter\Sampledata\sample1.jpg" 
    
    # Check if default relative path works, else warn user
    if not os.path.exists(img_path):
        print(f"Note: Default image '{img_path}' not found. Please edit the 'img_path' variable in this file.")
    
    debug_image(img_path)
