from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    filename = Column(String, index=True)
    model_used = Column(String)
    total_count = Column(Integer)
    confidence_threshold = Column(Float, nullable=True)
    
    # Storing base64 images directly in DB for simplicity (SQLite supports large text)
    # in production, file storage + path is better.
    thumbnail_base64 = Column(Text, nullable=True) 
    annotated_base64 = Column(Text, nullable=True)
    heatmap_base64 = Column(Text, nullable=True) # For Feature 2

    details = relationship("AnalysisDetail", back_populates="analysis", cascade="all, delete-orphan")

class AnalysisDetail(Base):
    __tablename__ = "analysis_details"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"))
    class_name = Column(String)
    count = Column(Integer)
    confidence = Column(Float)

    analysis = relationship("Analysis", back_populates="details")
