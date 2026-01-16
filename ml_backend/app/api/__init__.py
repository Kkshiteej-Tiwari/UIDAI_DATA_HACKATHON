"""
API module exports.
"""

from .datasets import router as datasets_router
from .analyze import router as analyze_router
from .train import router as train_router
from .predict import router as predict_router
from .report import router as report_router

__all__ = [
    "datasets_router",
    "analyze_router",
    "train_router",
    "predict_router",
    "report_router",
]
