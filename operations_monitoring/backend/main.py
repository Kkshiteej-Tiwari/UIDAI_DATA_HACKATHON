"""
Operations Monitoring Backend - FastAPI Application

Self-contained backend for UIDAI operations monitoring functionality.
Uses intent-based interaction for auditor-friendly monitoring.
"""
import logging
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path so we can import from policy, services, etc.
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info("🚀 Operations Monitoring Backend starting...")
    logger.info("📊 Monitoring API configured and ready")
    yield
    # Shutdown
    logger.info("👋 Operations Monitoring Backend shutting down...")


# Create FastAPI application
app = FastAPI(
    title="UIDAI Operations Monitoring API",
    description="""
    Intent-based monitoring system for UIDAI auditors.
    
    ## Features
    - **Intent-Based Monitoring**: Natural language intent processing
    - **AI-Powered Analysis**: Groq LLM integration for deep insights
    - **Policy Engine**: Intent resolution and strategy selection
    - **Real-time Results**: Async job processing with status tracking
    
    **Privacy:** Uses only aggregated, anonymized government data.
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8080",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include monitoring router
from routes import monitor
app.include_router(monitor.router, tags=["Monitoring"])


@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "status": "healthy",
        "service": "UIDAI Operations Monitoring API",
        "version": "1.0.0",
        "endpoints": {
            "submit_monitoring": "/api/monitor",
            "job_status": "/api/monitor/status/{job_id}",
            "job_results": "/api/monitor/results/{job_id}",
            "analyze_finding": "/api/monitor/analyze-finding"
        }
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Check if the monitoring backend is running."""
    return {
        "status": "healthy",
        "service": "UIDAI Operations Monitoring Backend",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
