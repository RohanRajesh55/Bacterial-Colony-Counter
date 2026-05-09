"""
Bacterial Colony Counter - FastAPI Backend
Main application entry point with model initialization.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import predict_router, feedback_router, history_router, reports_router, admin_router
from routers.predict import set_models
from database import engine, Base
import db_models as models



# Create database tables
Base.metadata.create_all(bind=engine)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for model loading."""
    settings = get_settings()
    
    logger.info("=" * 50)
    logger.info("Starting Bacterial Colony Counter API")
    logger.info("=" * 50)
    
    cnn_model = None
    yolo_model = None
    
    # Load CNN model
    cnn_path = Path(settings.cnn_model_path)
    if cnn_path.exists():
        try:
            from models.cnn_model import CNNModel
            cnn_model = CNNModel(
                model_path=str(cnn_path),
                class_names=settings.class_names,
                device=settings.device
            )
            cnn_model.warmup()
            logger.info(f"✓ CNN model loaded from {cnn_path}")
        except Exception as e:
            logger.warning(f"✗ Failed to load CNN model: {e}")
    else:
        logger.warning(f"✗ CNN model not found at {cnn_path}")
    
    # Load YOLO model
    yolo_path = Path(settings.yolo_model_path)
    if yolo_path.exists():
        try:
            from models.yolo_model import YOLOModel
            yolo_model = YOLOModel(
                model_path=str(yolo_path),
                class_names=settings.class_names,
                conf_threshold=settings.yolo_conf_threshold,
                img_size=settings.yolo_img_size,
                device=settings.device
            )
            yolo_model.warmup()
            logger.info(f"✓ YOLO model loaded from {yolo_path}")
        except Exception as e:
            logger.warning(f"✗ Failed to load YOLO model: {e}")
    else:
        logger.warning(f"✗ YOLO model not found at {yolo_path}")
    
    # Register models with router
    set_models(cnn_model, yolo_model)
    
    logger.info("=" * 50)
    logger.info("API Ready!")
    logger.info("=" * 50)
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Bacterial Colony Counter API",
    description="""
## Bacterial Colony Detection and Classification API

Upload petri dish images to detect and count bacterial colonies using deep learning.

### Models Available:
- **CNN**: Multi-task model for colony counting and classification
- **YOLO**: Object detection model with bounding boxes

### Supported Classes:
- B.subtilis
- C.albicans
- Contamination
- Defect
- E.coli
- P.aeruginosa
- S.aureus
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(predict_router)
app.include_router(feedback_router)
app.include_router(history_router)
app.include_router(reports_router)
app.include_router(admin_router)




@app.get("/", tags=["Health"])
async def root():
    """API root endpoint."""
    return {
        "message": "Bacterial Colony Counter API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    
    cnn_status = "loaded" if Path(settings.cnn_model_path).exists() else "not found"
    yolo_status = "loaded" if Path(settings.yolo_model_path).exists() else "not found"
    
    return {
        "status": "healthy",
        "models": {
            "cnn": cnn_status,
            "yolo": yolo_status
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
