"""
UIDAI ML Backend - FastAPI Application

Combines:
- Biometric Re-enrollment Risk Predictor
- ML Fraud Detection Backend

PRIVACY SAFEGUARDS:
- Uses ONLY aggregated data from public government APIs
- No individual Aadhaar numbers processed
- All operations on state/district/age-group level
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import get_settings, OUTPUT_DIR, VISUALIZATION_DIR, MODEL_DIR, REPORT_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create output directories
for directory in [OUTPUT_DIR, VISUALIZATION_DIR, MODEL_DIR, REPORT_DIR]:
    os.makedirs(directory, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("🚀 UIDAI ML Backend starting...")
    settings = get_settings()
    logger.info("📊 ML Backend configured and ready")
    yield
    # Shutdown
    logger.info("👋 UIDAI ML Backend shutting down...")


# Create FastAPI application
app = FastAPI(
    title="UIDAI ML Analytics API",
    description="""
    Unified ML-powered system for Aadhaar analytics.
    
    ## Features
    - **Biometric Risk Prediction**: Predict authentication failure risk
    - **Fraud Detection**: Automatic model selection and ensemble scoring
    - **Dataset Fusion**: Combine multiple data.gov.in APIs
    - **Explainability**: SHAP-based and human-readable explanations
    - **Visualizations**: Interactive policy-ready charts
    
    ## Models Used
    - Random Forest & XGBoost (risk prediction)
    - Isolation Forest (anomaly detection)
    - PyTorch Autoencoder (deep pattern recognition)
    - HDBSCAN (spatial clustering)
    
    **Privacy:** Uses only aggregated, anonymized government data.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount static files for visualizations
app.mount("/static", StaticFiles(directory=OUTPUT_DIR), name="static")

# Import and register routers with proper error handling
router_errors = []

# Try new API structure
try:
    from api.routes import datasets, analysis, visualizations, selection, reports
    app.include_router(datasets.router, prefix="/api", tags=["Datasets"])
    app.include_router(selection.router, prefix="/api", tags=["Selection"])
    app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
    app.include_router(visualizations.router, prefix="/api", tags=["Visualizations"])
    app.include_router(reports.router, prefix="/api", tags=["Reports"])
    logger.info("✅ Core API routes registered")
except ImportError as e:
    router_errors.append(f"Core routes: {e}")
    # Fallback to old structure
    try:
        from routers import datasets, analysis, visualizations
        app.include_router(datasets.router, prefix="/api", tags=["Datasets"])
        app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
        app.include_router(visualizations.router, prefix="/api", tags=["Visualizations"])
        logger.info("✅ Legacy API routes registered")
    except ImportError as e2:
        router_errors.append(f"Legacy routes: {e2}")

# Monitoring API
try:
    from api.routes import monitor
    app.include_router(monitor.router, tags=["Monitoring"])
    logger.info("✅ Monitoring routes registered")
except ImportError as e:
    router_errors.append(f"Monitor: {e}")

# Policy API
try:
    from api.routes import policy_api
    app.include_router(policy_api.router, prefix="/api/policy", tags=["Policy Engine"])
    logger.info("✅ Policy routes registered")
except ImportError as e:
    router_errors.append(f"Policy: {e}")

# Geospatial Hotspot Detection API - CRITICAL
try:
    from api.routes.geospatial import router as hotspots_router, forecast_router
    app.include_router(hotspots_router, tags=["Geospatial Hotspot Detection"])
    app.include_router(forecast_router, tags=["Forecasting"])
    logger.info("✅ Geospatial hotspot routes registered at /api/hotspots/*")
except Exception as e:
    logger.error(f"❌ FAILED to register geospatial routes: {e}")
    router_errors.append(f"Geospatial: {e}")

# Log any router errors
if router_errors:
    for error in router_errors:
        logger.warning(f"Router registration issue: {error}")


@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "status": "healthy",
        "project": "UIDAI ML Analytics API",
        "version": "1.0.0",
        "endpoints": {
            "datasets": "/api/datasets",
            "select_dataset": "/api/select-dataset",
            "analyze": "/api/analyze",
            "train_model": "/api/train-model",
            "risk_summary": "/api/risk-summary",
            "visualizations": "/api/visualizations",
            "explain_model": "/api/explain-model"
        }
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Check if the ML backend is running."""
    return {
        "status": "healthy",
        "service": "UIDAI ML Analytics Backend",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
