from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database import get_db
import db_models as models
from services.reporting import generate_pdf_report

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/{id}/pdf")
def get_report_pdf(
    id: int, 
    lab_name: str = None, 
    researcher_name: str = None, 
    db: Session = Depends(get_db)
):
    """Generate and download PDF report for an analysis."""
    analysis = db.query(models.Analysis).filter(models.Analysis.id == id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    pdf_bytes = generate_pdf_report(analysis, lab_name, researcher_name)
    
    filename = f"report_{analysis.filename}_{id}.pdf"
    
    return Response(
        content=bytes(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
