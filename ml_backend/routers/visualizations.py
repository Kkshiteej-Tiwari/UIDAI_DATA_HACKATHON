"""
Visualizations Router - Endpoints for chart generation and retrieval
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import os

from visualizations.charts import chart_generator
from config import VISUALIZATION_DIR


router = APIRouter()


@router.get("/visualizations")
async def list_visualizations():
    """
    List all generated visualizations
    """
    charts = chart_generator.get_generated_charts()
    
    if not charts:
        return {
            "message": "No visualizations generated yet",
            "instruction": "Run POST /api/train-model to generate visualizations"
        }
    
    return {
        "total_charts": len(charts),
        "charts": [
            {
                "filename": os.path.basename(c),
                "path": c,
                "url": f"/static/visualizations/{os.path.basename(c)}"
            }
            for c in charts
        ]
    }


@router.get("/visualizations/{filename}")
async def get_visualization(filename: str):
    """
    Get a specific visualization file
    
    Args:
        filename: Name of the chart file (e.g., 'risk_distribution.png')
    """
    filepath = os.path.join(VISUALIZATION_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Visualization '{filename}' not found")
    
    return FileResponse(filepath, media_type="image/png")


@router.get("/visualizations/all/download")
async def download_all_visualizations():
    """
    Get list of all visualization URLs for download
    """
    charts = chart_generator.get_generated_charts()
    
    return {
        "charts": [
            {
                "name": os.path.basename(c),
                "download_url": f"/api/visualizations/{os.path.basename(c)}"
            }
            for c in charts
        ]
    }


@router.delete("/visualizations/clear")
async def clear_visualizations():
    """
    Clear all generated visualizations
    """
    charts = chart_generator.get_generated_charts()
    deleted = 0
    
    for chart in charts:
        if os.path.exists(chart):
            os.remove(chart)
            deleted += 1
    
    chart_generator.generated_charts = []
    
    return {
        "message": f"Deleted {deleted} visualizations",
        "status": "success"
    }
