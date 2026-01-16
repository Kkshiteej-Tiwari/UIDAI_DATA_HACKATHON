"""
Dataset Router - Endpoints for dataset selection and schema info
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from services.data_gov_client import data_client


router = APIRouter()


class DatasetSelection(BaseModel):
    """Request model for dataset selection"""
    datasets: List[str]  # e.g., ["enrolment", "demographic", "biometric"]
    limit_per_dataset: int = 5000


# Global state for selected datasets
selected_datasets: Dict[str, Any] = {}


@router.get("/datasets")
async def list_datasets():
    """
    List all available datasets with schema information
    
    Returns:
        List of datasets with metadata
    """
    datasets = data_client.get_available_datasets()
    
    # Add record counts by fetching sample
    for dataset in datasets:
        schema = data_client.get_schema(dataset['key'])
        if 'total_records' in schema:
            dataset['total_records'] = schema['total_records']
        if 'sample' in schema:
            dataset['sample'] = schema['sample']
    
    return {
        "available_datasets": datasets,
        "total_datasets": len(datasets),
        "instructions": "Use POST /api/select-dataset to choose datasets for analysis"
    }


@router.get("/datasets/{dataset_key}/schema")
async def get_dataset_schema(dataset_key: str):
    """
    Get detailed schema for a specific dataset
    
    Args:
        dataset_key: One of 'enrolment', 'demographic', 'biometric'
    """
    schema = data_client.get_schema(dataset_key)
    
    if 'error' in schema:
        raise HTTPException(status_code=404, detail=schema['error'])
    
    return schema


@router.get("/datasets/{dataset_key}/sample")
async def get_dataset_sample(dataset_key: str, limit: int = 10):
    """
    Get sample records from a dataset
    
    Args:
        dataset_key: Dataset to sample
        limit: Number of records (max 100)
    """
    if limit > 100:
        limit = 100
    
    result = data_client.fetch_data(dataset_key, limit=limit)
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to fetch data'))
    
    return {
        "dataset": dataset_key,
        "count": result['count'],
        "total_available": result['total'],
        "records": result['records']
    }


@router.post("/select-dataset")
async def select_datasets(selection: DatasetSelection):
    """
    Select one or more datasets for analysis
    
    This will fetch and store the data for subsequent analysis.
    """
    global selected_datasets
    
    valid_keys = ['enrolment', 'demographic', 'biometric']
    invalid = [d for d in selection.datasets if d not in valid_keys]
    
    if invalid:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid dataset keys: {invalid}. Valid options: {valid_keys}"
        )
    
    # Fetch selected datasets
    selected_datasets = data_client.fetch_multiple_datasets(
        selection.datasets,
        limit_per_dataset=selection.limit_per_dataset
    )
    
    # Build response
    response = {
        "selected_datasets": selection.datasets,
        "data_summary": {}
    }
    
    for key, df in selected_datasets.items():
        response["data_summary"][key] = {
            "records_loaded": len(df),
            "columns": list(df.columns),
            "memory_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
        }
    
    return response


@router.get("/selected-datasets")
async def get_selected_datasets():
    """
    Get information about currently selected datasets
    """
    if not selected_datasets:
        return {
            "message": "No datasets selected yet",
            "instruction": "Use POST /api/select-dataset to select datasets"
        }
    
    summary = {}
    for key, df in selected_datasets.items():
        summary[key] = {
            "records": len(df),
            "columns": list(df.columns)
        }
    
    return {
        "selected_datasets": list(selected_datasets.keys()),
        "summary": summary
    }


def get_selected_data() -> Dict[str, Any]:
    """Helper function to get selected datasets from other modules"""
    return selected_datasets
