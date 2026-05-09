"""
Feedback API router.
Handles user feedback for incorrect predictions to enable model retraining.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse, Response
from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel

from datetime import datetime
import json
import logging
import shutil
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Feedback"])
from routers.admin import get_current_admin
from fastapi import Depends


# Feedback storage directory
FEEDBACK_DIR = Path("feedback_data")
FEEDBACK_DIR.mkdir(exist_ok=True)

# Retraining dataset directory
RETRAINING_DIR = Path("data/retraining")
RETRAINING_DIR.mkdir(parents=True, exist_ok=True)



@router.post("/feedback")
async def submit_feedback(
    image: UploadFile = File(..., description="Original image that was analyzed"),
    feedback_type: str = Form(..., description="Type: count, classification, both, other"),
    original_count: int = Form(..., description="Model's predicted count"),
    original_model: str = Form(..., description="Model used: cnn or yolo"),
    original_classes: str = Form("", description="JSON string of original class predictions"),
    correct_count: Optional[int] = Form(None, description="User-provided correct count"),
    correct_class: Optional[str] = Form(None, description="User-provided correct class"),
    notes: Optional[str] = Form("", description="Additional user notes")
):
    """
    Store user feedback for incorrect predictions.
    
    Saves the original image and feedback data in a structured format
    suitable for model retraining.
    
    Storage structure:
    feedback_data/
    ├── YYYYMMDD_HHMMSS_uuid/
    │   ├── image.jpg
    │   ├── feedback.json
    │   └── original_predictions.json
    """
    try:
        # Create unique folder for this feedback
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        feedback_id = f"{timestamp}_{uuid.uuid4().hex[:8]}"
        feedback_folder = FEEDBACK_DIR / feedback_id
        feedback_folder.mkdir(parents=True, exist_ok=True)
        
        # Save the image
        image_ext = Path(image.filename).suffix or ".jpg"
        image_path = feedback_folder / f"image{image_ext}"
        
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)
        
        # Parse original classes if provided
        try:
            original_class_data = json.loads(original_classes) if original_classes else []
        except json.JSONDecodeError:
            original_class_data = []
        
        # Save original predictions
        original_predictions = {
            "model_used": original_model,
            "predicted_count": original_count,
            "class_predictions": original_class_data
        }
        
        with open(feedback_folder / "original_predictions.json", "w") as f:
            json.dump(original_predictions, f, indent=2)
        
        # Save feedback/corrections
        feedback_data = {
            "feedback_id": feedback_id,
            "timestamp": datetime.now().isoformat(),
            "feedback_type": feedback_type,
            "original_count": original_count,  # Added for easier display
            "predicted_count": original_count, # Alias 

            "corrections": {
                "correct_count": correct_count,
                "correct_class": correct_class
            },
            "notes": notes,
            "image_filename": f"image{image_ext}",
            "status": "pending"  # pending, reviewed, used_for_training
        }
        
        with open(feedback_folder / "feedback.json", "w") as f:
            json.dump(feedback_data, f, indent=2)
        
        # Also append to master feedback log for easy access
        master_log = FEEDBACK_DIR / "feedback_log.jsonl"
        with open(master_log, "a") as f:
            log_entry = {
                "feedback_id": feedback_id,
                "timestamp": feedback_data["timestamp"],
                "feedback_type": feedback_type,
                "original_count": original_count,
                "correct_count": correct_count,
                "correct_class": correct_class,
                "model_used": original_model
            }
            f.write(json.dumps(log_entry) + "\n")
        
        logger.info(f"Feedback saved: {feedback_id}")
        
        return JSONResponse({
            "success": True,
            "feedback_id": feedback_id,
            "message": "Feedback saved successfully. Thank you for helping improve the model!"
        })
        
    except Exception as e:
        logger.error(f"Error saving feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")


@router.get("/feedback/stats")
async def get_feedback_stats():
    """Get statistics about collected feedback."""
    try:
        master_log = FEEDBACK_DIR / "feedback_log.jsonl"
        
        if not master_log.exists():
            return {
                "total_feedback": 0,
                "by_type": {},
                "by_model": {}
            }
        
        feedback_entries = []
        with open(master_log, "r") as f:
            for line in f:
                if line.strip():
                    feedback_entries.append(json.loads(line))
        
        # Count by type
        by_type = {}
        by_model = {}
        
        for entry in feedback_entries:
            ft = entry.get("feedback_type", "unknown")
            by_type[ft] = by_type.get(ft, 0) + 1
            
            model = entry.get("model_used", "unknown")
            by_model[model] = by_model.get(model, 0) + 1
        
        return {
            "total_feedback": len(feedback_entries),
            "by_type": by_type,
            "by_model": by_model
        }
        
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        return {"total_feedback": 0, "by_type": {}, "by_model": {}}

@router.get("/feedback/list", dependencies=[Depends(get_current_admin)])
async def list_feedback(status: str = "pending"):
    """List feedback entries by status."""
    try:
        entries = []
        # Iterate over subdirectories in FEEDBACK_DIR
        for feedback_path in FEEDBACK_DIR.iterdir():
            if feedback_path.is_dir():
                json_path = feedback_path / "feedback.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r") as f:
                            data = json.load(f)
                            if data.get("status") == status:
                                # Add ID explicitly if missing
                                data["id"] = feedback_path.name
                                
                                # Try to load "original_predictions.json" if original count missing
                                if "original_count" not in data and "predicted_count" not in data:
                                    orig_pred_path = feedback_path / "original_predictions.json"
                                    if orig_pred_path.exists():
                                        try:
                                            with open(orig_pred_path, "r") as opf:
                                                 op_data = json.load(opf)
                                                 data["original_count"] = op_data.get("predicted_count")
                                                 data["predicted_count"] = op_data.get("predicted_count")
                                        except:
                                            pass

                                entries.append(data)
                    except Exception as e:
                        logger.warning(f"Failed to read feedback JSON in {feedback_path}: {e}")
        
        # Sort by timestamp desc
        entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return entries
    except Exception as e:
        logger.error(f"Error listing feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to list feedback")

@router.get("/feedback/image/{feedback_id}")
async def get_feedback_image(feedback_id: str):
    """Serve the image associated with a feedback entry."""
    feedback_path = FEEDBACK_DIR / feedback_id
    if not feedback_path.exists():
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # helper to find image file
    for file in feedback_path.iterdir():
        if file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
             return Response(content=file.read_bytes(), media_type="image/jpeg")
            
    raise HTTPException(status_code=404, detail="Image not found")

@router.delete("/feedback/{feedback_id}", dependencies=[Depends(get_current_admin)])
async def delete_feedback(feedback_id: str):
    """Delete (reject) a feedback entry."""
    feedback_path = FEEDBACK_DIR / feedback_id
    if not feedback_path.exists():
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    try:
        shutil.rmtree(feedback_path)
        return {"success": True, "message": "Feedback deleted"}
    except Exception as e:
        logger.error(f"Error deleting feedback {feedback_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete feedback")

    
class LabelItem(BaseModel):
    class_id: int
    x_center: float
    y_center: float
    width: float
    height: float

class ApproveRequest(BaseModel):
    labels: Optional[List[LabelItem]] = None

@router.post("/feedback/{feedback_id}/approve", dependencies=[Depends(get_current_admin)])
async def approve_feedback(feedback_id: str, request: Optional[ApproveRequest] = Body(None)):

    """
    Approve feedback for retraining.
    Moves image to 'retraining_dataset' and creates a label file.
    """
    feedback_path = FEEDBACK_DIR / feedback_id
    if not feedback_path.exists():
        raise HTTPException(status_code=404, detail="Feedback not found")
        
    try:
        # Load feedback data
        with open(feedback_path / "feedback.json", "r") as f:
            data = json.load(f)
        
        # Mark as approved
        data["status"] = "approved"
        with open(feedback_path / "feedback.json", "w") as f:
            json.dump(data, f, indent=2)
            
        # Move/Copy to retraining dataset
        # Create 'images' and 'labels' folders if not exist
        (RETRAINING_DIR / "images").mkdir(exist_ok=True)
        (RETRAINING_DIR / "labels").mkdir(exist_ok=True)
        
        # Find image
        image_file = None
        for file in feedback_path.iterdir():
            if file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                image_file = file
                break
        
        if image_file:
            # Copy image
            dest_img_path = RETRAINING_DIR / "images" / f"{feedback_id}{image_file.suffix}"
            shutil.copy(image_file, dest_img_path)
            
            # Create label file (YOLO format)
            # If we received specific labels from the Annotation Tool, use them.
            # Otherwise use what we know (fallback, though we shouldn't really use fallback for detection training ideally)
            
            # Create label file (YOLO format)
            label_path = RETRAINING_DIR / "labels" / f"{feedback_id}.txt"
            
            # JSON Metadata Path (Always create this for traceability)
            json_meta_path = RETRAINING_DIR / "labels" / f"{feedback_id}.json"
            
            # Prepare metadata
            meta_data = {
                "original_feedback_id": feedback_id,
                "timestamp": datetime.now().isoformat(),
                "notes": data.get("notes", ""),
                "corrections": data.get("corrections", "")
            }

            if request and request.labels:
                # Use provided labels
                with open(label_path, "w") as f:
                    for lbl in request.labels:
                        f.write(f"{lbl.class_id} {lbl.x_center} {lbl.y_center} {lbl.width} {lbl.height}\n")
                
                # Add labels to metadata for record
                meta_data["labels"] = [lbl.dict() for lbl in request.labels]

            else:
                # Fallback: No boxes provided. 
                # Check if draft labels exist in feedback dir?
                draft_path = feedback_path / "labels.json"
                if draft_path.exists():
                     with open(draft_path, "r") as df:
                         draft_labels = json.load(df)
                         # Write YOLO txt from draft
                         with open(label_path, "w") as f:
                             for lbl in draft_labels:
                                 f.write(f"{lbl['class_id']} {lbl['x_center']} {lbl['y_center']} {lbl['width']} {lbl['height']}\n")
                         meta_data["labels"] = draft_labels
            
            # Save Metadata JSON
            with open(json_meta_path, "w") as f:
                json.dump(meta_data, f, indent=2)
                
        return {"success": True, "message": "Feedback approved for retraining"}
        
    except Exception as e:
        logger.error(f"Error approving feedback {feedback_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve feedback: {e}")

@router.post("/feedback/{feedback_id}/annotate", dependencies=[Depends(get_current_admin)])
async def save_annotation_draft(feedback_id: str, request: ApproveRequest):
    """Save annotation draft without approving (stays in feedback queue)."""
    feedback_path = FEEDBACK_DIR / feedback_id
    if not feedback_path.exists():
        raise HTTPException(status_code=404, detail="Feedback not found")
        
    try:
        # Save labels to feedback dir
        draft_path = feedback_path / "labels.json"
        
        if request.labels:
            labels_data = [lbl.dict() for lbl in request.labels]
            with open(draft_path, "w") as f:
                json.dump(labels_data, f, indent=2)
                
        return {"success": True, "message": "Draft saved"}
    except Exception as e:
        logger.error(f"Error saving draft {feedback_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save draft: {e}")

