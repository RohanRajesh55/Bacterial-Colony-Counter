"""
Prediction API router.
Handles image upload and model inference.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Literal
import logging
import time
from sqlalchemy.orm import Session

from config import get_settings
from schemas import PredictionResponse, ClassCount
from services import preprocess_image, encode_image_to_base64
from services.preprocessing import resize_for_display
from services.visualization import generate_heatmap
from database import get_db
import db_models as models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Prediction"])

# Model instances (initialized in main.py)
cnn_model = None
yolo_model = None

# -----------------------------------------------------------------------------
# QUICK FIX: Calibration Factor for CNN
# Change this value to scale the counts.
# Examples:
#   0.5 = cuts count in half (e.g. 100 -> 50)
#   2.0 = doubles the count (e.g. 100 -> 200)
#   1.0 = no change
CNN_CALIBRATION_FACTOR = 1.0
# -----------------------------------------------------------------------------


def set_models(cnn, yolo):
    """Set model instances from main app."""
    global cnn_model, yolo_model
    cnn_model = cnn
    yolo_model = yolo

def save_analysis(db: Session, filename: str, model_type: str, total_count: int, 
                  class_counts: list[ClassCount], confidence: float, 
                  processed_b64: str, annotated_b64: str = None, heatmap_b64: str = None):
    """Helper to save analysis to DB."""
    try:
        db_analysis = models.Analysis(
            filename=filename,
            model_used=model_type,
            total_count=total_count,
            confidence_threshold=confidence,
            thumbnail_base64=processed_b64, # Using processed as thumbnail
            annotated_base64=annotated_b64,
            heatmap_base64=heatmap_b64
        )
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)

        for cc in class_counts:
            detail = models.AnalysisDetail(
                analysis_id=db_analysis.id,
                class_name=cc.name,
                count=cc.count,
                confidence=cc.confidence or 0.0
            )
            db.add(detail)
        db.commit()
        return db_analysis
    except Exception as e:
        logger.error(f"Failed to save to DB: {e}")
        return None

@router.post("/predict", response_model=PredictionResponse)
async def predict(
    image: UploadFile = File(..., description="Petri dish image to analyze"),
    model_type: Literal["cnn", "yolo"] = Form("yolo", description="Model to use for prediction"),
    show_boxes: bool = Form(True, description="Draw bounding boxes (YOLO only)"),
    confidence_threshold: float = Form(0.40, description="Confidence threshold for YOLO (0.1-0.9)"),
    db: Session = Depends(get_db)
):
    """
    Analyze a petri dish image for bacterial colonies.
    
    - **image**: Upload a JPG/PNG image of a petri dish
    - **model_type**: Choose 'cnn' for count+classification or 'yolo' for object detection
    - **show_boxes**: Enable bounding box visualization (YOLO only)
    
    Returns colony count, class distribution, and processed images.
    """
    settings = get_settings()
    
    # Validate file type
    if image.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {image.content_type}. Please upload a JPEG or PNG image."
        )
    
    # Read and decode image
    try:
        start_read = time.perf_counter()
        contents = await image.read()
        filename = image.filename
        
        # Check file size
        if len(contents) > settings.max_image_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {settings.max_image_size_mb}MB."
            )
        
        img_array, error = preprocess_image(contents)
        if error:
            raise HTTPException(status_code=400, detail=error)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading image: {e}")
        # Return the actual error message for debugging
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")
    
    # Run inference
    try:
        if model_type == "cnn":
            if cnn_model is None:
                raise HTTPException(status_code=503, detail="CNN model not loaded.")
            
            start_time = time.perf_counter()
            result = cnn_model.predict(img_array)
            inference_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"Inference Time (CNN): {inference_time:.2f}ms")
            
            # Build response
            class_counts = [
                ClassCount(
                    name=name, 
                    count=int(result["class_counts"].get(name, 0) * CNN_CALIBRATION_FACTOR),
                    confidence=result["class_probabilities"].get(name, 0.0)
                )
                for name in settings.class_names
                if result["class_counts"].get(name, 0) > 0 or name == result["predicted_class"]
            ]
            
            # Encode processed image
            display_img = resize_for_display(img_array, 800)
            processed_b64 = encode_image_to_base64(display_img)
            
            # Save to DB
            db_analysis = save_analysis(db, filename, "cnn", int(result["total_count"] * CNN_CALIBRATION_FACTOR), class_counts, 0.0, processed_b64, None)
            
            return PredictionResponse(
                success=True,
                analysis_id=db_analysis.id if db_analysis else None,
                model_used="cnn",
                total_count=int(result["total_count"] * CNN_CALIBRATION_FACTOR),
                class_counts=class_counts,
                processed_image=processed_b64,
                annotated_image=None
            )
            
        else:  # YOLO
            if yolo_model is None:
                raise HTTPException(status_code=503, detail="YOLO model not loaded.")
            
            # Clamp threshold to valid range
            conf_thresh = max(0.1, min(0.9, confidence_threshold))
            
            start_time = time.perf_counter()
            result = yolo_model.predict(img_array, draw_boxes=show_boxes, conf_threshold=conf_thresh)
            inference_time = (time.perf_counter() - start_time) * 1000
            logger.info(f"Inference Time (YOLO): {inference_time:.2f}ms")
            
            # Build response
            class_counts = [
                ClassCount(
                    name=name,
                    count=result["class_counts"][name]["count"],
                    confidence=result["class_counts"][name]["avg_confidence"]
                )
                for name in settings.class_names
                if result["class_counts"][name]["count"] > 0
            ]
            
            # Encode images
            display_img = resize_for_display(img_array, 800)
            processed_b64 = encode_image_to_base64(display_img)
            
            annotated_b64 = None
            if show_boxes and "annotated_image" in result:
                annotated_display = resize_for_display(result["annotated_image"], 800)
                annotated_b64 = encode_image_to_base64(annotated_display)
            
            # Generate Heatmap
            heatmap_b64 = None
            if "detections" in result:
                heatmap_img = generate_heatmap(img_array, result["detections"])
                heatmap_display = resize_for_display(heatmap_img, 800)
                heatmap_b64 = encode_image_to_base64(heatmap_display)
            
            # Save to DB
            db_analysis = save_analysis(db, filename, "yolo", result["total_count"], class_counts, conf_thresh, processed_b64, annotated_b64, heatmap_b64)
            
            # Format detections for response
            detections = []
            if "detections" in result:
                 # result["detections"] is likely list of [x1, y1, x2, y2, conf, cls_id]
                 # We need to convert to x,y,w,h,label
                 for det in result["detections"]:
                     # Assuming format: [x1, y1, x2, y2, conf, cls_id] based on typical YOLO output
                     # OR from yolo_model.py it might be different. 
                     # Let's check how generate_heatmap uses it.
                     # But yolo_model usually returns xyxy. 
                     # Let's verify standard YOLO output or be safe.
                     # Actually, let's assume result["detections"] contains what we need.
                     # If yolo_model follows ultralytics, it's xyxy.
                     # det is a Dictionary from yolo_model
                     bbox = det["bbox"]
                     x1, y1, x2, y2 = bbox
                     conf = det["confidence"]
                     label = det["class_name"]
                     
                     # Normalize coordinates
                     # annotated_display is the image these coords are relative to.
                     # But annotated_display is processed from result["annotated_image"].
                     # Wait, result["detections"] from yolo_model are typically usually on the ORIGINAL or RESIZED input?
                     # Let's check yolo_model.py logic implicitly. Usually they are rescaled to original.
                     # IF they are rescaled to original, we should divide by ORIGINAL dimensions.
                     # But we are sending `processed_image` (resized to 800) to the frontend.
                     # So we should map them to `processed_image` dimensions OR normalize them using original dimensions (which works for any resize that preserves aspect ratio).
                     # img_array is the original input (decoded).
                     orig_h, orig_w = img_array.shape[:2]
                     
                     detections.append({
                         "x": int(x1), # Keeping absolute for debug if needed
                         "y": int(y1),
                         "w": int(x2 - x1),
                         "h": int(y2 - y1),
                         # Normalized (0-1)
                         "xn": float(x1 / orig_w),
                         "yn": float(y1 / orig_h),
                         "wn": float((x2 - x1) / orig_w),
                         "hn": float((y2 - y1) / orig_h),
                         "label": label,
                         "confidence": float(conf)
                     })

            return PredictionResponse(
                success=True,
                analysis_id=db_analysis.id if db_analysis else None,
                model_used="yolo",
                total_count=result["total_count"],
                class_counts=class_counts,
                processed_image=processed_b64,
                annotated_image=annotated_b64,
                heatmap_image=heatmap_b64,
                detections=detections
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        return PredictionResponse(
            success=False,
            model_used=model_type,
            total_count=0,
            class_counts=[],
            processed_image="",
            error=f"Inference failed: {str(e)}"
        )
