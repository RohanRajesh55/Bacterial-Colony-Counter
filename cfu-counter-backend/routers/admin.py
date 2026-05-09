from fastapi import APIRouter, Depends, HTTPException, Header, Body
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
import secrets
from config import get_settings
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
import db_models as models
from datetime import datetime
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Simple token storage (in-memory for now, could be redis/db)
# Since this is a single instance app, in-memory is fine.
# Map token -> username (or just presence)
VALID_TOKENS = set()

API_KEY_HEADER = APIKeyHeader(name="X-Admin-Token", auto_error=False)

class LoginRequest(BaseModel):
    password: str

@router.post("/login")
async def admin_login(login_data: LoginRequest):
    settings = get_settings()
    if login_data.password == settings.admin_password:
        # Generate simple token
        token = secrets.token_urlsafe(32)
        VALID_TOKENS.add(token)
        return {"success": True, "token": token}
    
    raise HTTPException(status_code=401, detail="Invalid password")

@router.post("/logout")
async def admin_logout(token: str = Depends(API_KEY_HEADER)):
    if token in VALID_TOKENS:
        VALID_TOKENS.remove(token)
    return {"success": True}

async def get_current_admin(token: str = Depends(API_KEY_HEADER)):
    """Dependency to protect admin routes."""
    if not token or token not in VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token

@router.get("/stats", dependencies=[Depends(get_current_admin)])
async def get_system_stats(db: Session = Depends(get_db)):
    """
    Get aggregated system statistics for dashboard.
    """
    # 1. Total Analyses
    total_analyses = db.query(models.Analysis).count()
    
    # 2. Total Colonies Counted (sum of total_count)
    # Handle None/Null case
    total_colonies = db.query(func.sum(models.Analysis.total_count)).scalar() or 0
    
    # 3. Class Distribution
    # Group by class_name, sum count
    class_dist_query = db.query(
        models.AnalysisDetail.class_name,
        func.sum(models.AnalysisDetail.count)
    ).group_by(models.AnalysisDetail.class_name).all()
    
    class_distribution = {name: count for name, count in class_dist_query}
    
    
    # 4. Pending Feedback Count
    pending_count = 0
    feedback_dir = Path("feedback_data")
    if feedback_dir.exists():
        for feedback_path in feedback_dir.iterdir():
            if feedback_path.is_dir():
                json_path = feedback_path / "feedback.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r") as f:
                            data = json.load(f)
                            if data.get("status") == "pending":
                                pending_count += 1
                    except Exception:
                        pass
        
    return {
        "total_analyses": total_analyses,
        "total_colonies": total_colonies,
        "class_distribution": class_distribution,
        "pending_feedback": pending_count,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/history", dependencies=[Depends(get_current_admin)])
async def get_admin_history(db: Session = Depends(get_db)):
    """Get full history for database management."""
    # Return lighter objects for table view
    analyses = db.query(models.Analysis).order_by(models.Analysis.timestamp.desc()).all()
    results = []
    for a in analyses:
        results.append({
            "id": a.id,
            "timestamp": a.timestamp,
            "filename": a.filename,
            "model_used": a.model_used,
            "total_count": a.total_count,
            # We don't need heavy images for the list view in admin
        })
    return results

@router.delete("/history/{id}", dependencies=[Depends(get_current_admin)])
async def delete_admin_history_entry(id: int, db: Session = Depends(get_db)):
    """Delete a specific analysis record."""
    analysis = db.query(models.Analysis).filter(models.Analysis.id == id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
    return {"success": True, "message": "Record deleted"}

