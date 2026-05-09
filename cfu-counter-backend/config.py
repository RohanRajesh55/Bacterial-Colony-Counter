"""
Application configuration using Pydantic Settings.
Supports environment variables and .env files.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Settings
    app_name: str = "Bacterial Colony Counter"
    app_name: str = "Bacterial Colony Counter"
    debug: bool = False
    admin_password: str = "admin123"
    
    # Model Paths (relative to project root)
    cnn_model_path: Path = Path("models/cnn/final_best.pth")
    yolo_model_path: Path = Path("models/yolo/best.pt")
    
    # Inference Settings
    device: str = "cpu"  # "cpu" or "cuda"
    yolo_conf_threshold: float = 0.40
    yolo_img_size: int = 640
    
    # Image Settings
    max_image_size_mb: int = 10
    allowed_extensions: set = {"jpg", "jpeg", "png"}
    
    # Class names for bacterial colonies
    class_names: list = [
        "B.subtilis",
        "C.albicans", 
        "Contamination",
        "Defect",
        "E.coli",
        "P.aeruginosa",
        "S.aureus"
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
