from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import db_models as models
from schemas import PredictionResponse, ClassCount

router = APIRouter(prefix="/api/history", tags=["History"])

@router.get("/", response_model=List[dict])
def get_history(db: Session = Depends(get_db)):
    """Get all past analyses."""
    analyses = db.query(models.Analysis).order_by(models.Analysis.timestamp.desc()).all()
    
    results = []
    for a in analyses:
        # Convert DB model to response format
        # We need to reconstruct the simplified history object for the list view
        class_counts_dict = {
            d.class_name: d.count for d in a.details
        }
        
        results.append({
            "id": a.id,
            "timestamp": a.timestamp,
            "imageName": a.filename,
            "modelType": a.model_used,
            "totalCount": a.total_count,
            "confidenceThreshold": a.confidence_threshold,
            "thumbnail": a.thumbnail_base64, # Heavy payload if list is long? 
            # Frontend expects 'thumbnail' for list view.
            # Ideally we should exclude heavy fields in list view, but sticking to existing frontend logic.
            "annotatedImage": a.annotated_base64,
            "heatmapImage": a.heatmap_base64,
            "classCounts": class_counts_dict # Frontend logic handles object format

        })
    return results

@router.delete("/{id}")
def delete_history(id: int, db: Session = Depends(get_db)):
    """Delete an analysis record."""
    analysis = db.query(models.Analysis).filter(models.Analysis.id == id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
    return {"message": "Deleted successfully"}
