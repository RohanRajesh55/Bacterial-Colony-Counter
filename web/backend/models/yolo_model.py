import cv2
import numpy as np
import logging
from collections import Counter
from typing import Dict, List

logger = logging.getLogger(__name__)

class YOLOModel:
    """Bare-bone YOLO wrapper for debugging performance."""
    
    def __init__(self, model_path: str, class_names: list, 
                 conf_threshold: float = 0.4, img_size: int = 1024, 
                 device: str = "cpu"):
        self.class_names = class_names
        self.conf_threshold = conf_threshold
        self.img_size = img_size
        self.device = device
        
        from ultralytics import YOLO
        import time
        t0 = time.time()
        self.model = YOLO(model_path)
        logger.info(f"YOLO loaded in {time.time()-t0:.2f}s on {device}")
        
    def predict(self, image: np.ndarray, draw_boxes: bool = True, conf_threshold: float = None) -> Dict:
        """
        Minimal prediction function.
        """
        import time
        t_start = time.time()
        
        # Threshold logic
        threshold = conf_threshold if conf_threshold is not None else self.conf_threshold
        
        # Run inference directly
        # Let YOLO handle resizing internally
        if self.device == "cpu":
             # Try OpenVINO/ONNX if available automatically, else standard
             pass

        logger.info(f"YOLO input shape: {image.shape}")

        results = self.model(
            image, 
            conf=threshold, 
            imgsz=self.img_size, 
            device=self.device, 
            verbose=True  # Turn on verbose to see YOLO's own timing
        )
        
        t_infer = time.time() - t_start
        logger.info(f"YOLO.model() call took: {t_infer*1000:.2f}ms")
        
        detections = []
        class_counter = Counter()
        
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu().numpy())
                cls_idx = int(boxes.cls[i].cpu().numpy())
                
                cls_name = self.class_names[cls_idx] if cls_idx < len(self.class_names) else "Unknown"
                class_counter[cls_name] += 1
                
                detections.append({
                    "bbox": [float(x1), float(y1), float(x2), float(y2)],
                    "confidence": conf,
                    "class_idx": cls_idx,
                    "class_name": cls_name
                })
        
        t_process = time.time() - t_start - t_infer
        logger.info(f"Post-processing took: {t_process*1000:.2f}ms")

        return self._format_result(detections, class_counter, image, draw_boxes)

    def _format_result(self, detections, class_counter, image, draw_boxes):
        class_counts = {}
        for cls_name in self.class_names:
            count = class_counter.get(cls_name, 0)
            class_counts[cls_name] = {"count": count, "avg_confidence": 0.0} # Skip avg calc for speed debugging
        
        result = {
            "total_count": len(detections),
            "class_counts": class_counts,
            "detections": detections,
        }
        
        if draw_boxes:
            result["annotated_image"] = results[0].plot() if 'results' in locals() else image 
            # Use YOLO's optimized plotter if available, actually results[0].plot() is fast
            # But let's stick to consistent output for now or use the previous simple one
            # Using simple one is safer for consistency
            result["annotated_image"] = self._draw_boxes(image.copy(), detections)
            
        return result

    def _draw_boxes(self, image: np.ndarray, detections: List[Dict]) -> np.ndarray:
        for det in detections:
            x1, y1, x2, y2 = [int(c) for c in det["bbox"]]
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        return image
    
    def warmup(self):
        pass
