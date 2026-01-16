"""
Gender Inclusion Tracker - Datasets API Router
Endpoints for listing and selecting datasets.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ..core.security import verify_api_key
from ..services.connectors import get_connector

router = APIRouter(prefix="/datasets", tags=["Datasets"])


class DatasetSelection(BaseModel):
    """Request body for dataset selection."""
    source: Optional[str] = None  # 'api1', 'api2', 'api3'
    dataset_id: Optional[str] = None
    auto: bool = False  # If true, auto-select best dataset


class DatasetPreview(BaseModel):
    """Dataset preview response."""
    id: str
    key: str
    name: str
    source: str
    description: str
    fields: List[str]
    record_count: int
    suitability_score: float


@router.get("/", response_model=List[Dict[str, Any]])
async def list_datasets():
    """
    List all available datasets from connected APIs.
    
    Returns datasets with schema preview and suitability scores
    for gender analysis.
    """
    connector = get_connector()
    
    try:
        datasets = await connector.list_all_datasets()
        return datasets
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch datasets: {str(e)}"
        )


@router.post("/select")
async def select_dataset(selection: DatasetSelection):
    """
    Select a dataset for analysis.
    
    If `auto=true`, automatically selects the most suitable dataset
    based on column suitability scoring.
    
    Returns the selected dataset handle and preview.
    """
    connector = get_connector()
    
    try:
        if selection.auto:
            result = await connector.auto_select_best_dataset()
            if not result['success']:
                raise HTTPException(
                    status_code=400,
                    detail=result.get('error', 'Auto-selection failed')
                )
            return result
        
        elif selection.source and selection.dataset_id:
            # Manual selection
            datasets = await connector.list_all_datasets()
            selected = next(
                (d for d in datasets if d['id'] == selection.dataset_id),
                None
            )
            
            if not selected:
                raise HTTPException(
                    status_code=404,
                    detail=f"Dataset {selection.dataset_id} not found"
                )
            
            return {
                'success': True,
                'selected': selected,
                'reasoning': f"Manually selected '{selected['name']}'"
            }
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Either set 'auto=true' or provide 'source' and 'dataset_id'"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset selection failed: {str(e)}"
        )


@router.get("/{dataset_key}/preview")
async def preview_dataset(dataset_key: str, limit: int = 10):
    """
    Get a preview of the dataset content.
    
    Args:
        dataset_key: Key of the dataset ('enrolment', 'demographic', 'biometric')
        limit: Number of records to preview
    """
    connector = get_connector()
    
    if dataset_key not in connector.known_datasets:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown dataset key: {dataset_key}"
        )
    
    try:
        resource_id = connector.known_datasets[dataset_key]['resource_id']
        df = await connector.fetch_dataset('api1', resource_id, limit=limit)
        
        return {
            'dataset_key': dataset_key,
            'record_count': len(df),
            'columns': df.columns.tolist(),
            'sample_data': df.head(limit).to_dict(orient='records')
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview dataset: {str(e)}"
        )
