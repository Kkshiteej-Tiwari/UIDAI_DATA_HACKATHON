"""
Gender Inclusion Tracker - ML Backend
FastAPI application entry point.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

from .core.config import settings
from .api import (
    datasets_router,
    analyze_router,
    train_router,
    predict_router,
    report_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Gender Inclusion Tracker API",
    description="""
    ML-powered backend for monitoring and predicting gender inclusion gaps
    in Aadhaar enrollment across India.
    
    ## Features
    - **Dataset Management**: Connect to and analyze multiple data sources
    - **Preprocessing**: Automatic data cleaning and feature engineering
    - **ML Training**: Train LightGBM models to identify high-risk districts
    - **Predictions**: Get risk scores with explainable AI (SHAP)
    - **Reporting**: Generate reports and visualizations
    
    ## Privacy & Security
    - All outputs are aggregated at district level (no PII)
    - Differential privacy noise can be enabled for public outputs
    - API key authentication supported
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(datasets_router, prefix="/api")
app.include_router(analyze_router, prefix="/api")
app.include_router(train_router, prefix="/api")
app.include_router(predict_router, prefix="/api")
app.include_router(report_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Gender Inclusion Tracker API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "endpoints": {
            "datasets": "/api/datasets",
            "analyze": "/api/analyze",
            "train": "/api/train",
            "predict": "/api/predict",
            "report": "/api/report"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "settings": {
            "debug": settings.debug,
            "artifacts_dir": str(settings.artifacts_dir),
            "models_dir": str(settings.models_dir)
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc} at {request.url.path}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "path": request.url.path
        }
    )


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info(f"Starting Gender Inclusion Tracker API on {settings.host}:{settings.port}")
    
    # Ensure directories exist
    settings.ensure_directories()


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("Shutting down Gender Inclusion Tracker API")
    
    # Close API connectors
    from .services.connectors import get_connector
    try:
        connector = get_connector()
        await connector.close()
    except Exception:
        pass


# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
