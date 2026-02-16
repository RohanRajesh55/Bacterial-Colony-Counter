"""Shared application state for ML models.

This module exists to avoid circular imports between main.py and routers.
The ml_models dict is populated during app lifespan startup in main.py
and accessed by routers for inference.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global state for ML models
ml_models: dict = {}

# Global state for Rate Limiting
limiter = Limiter(key_func=get_remote_address)
