"""
Gender Inclusion Tracker - Analysis API Router
Endpoints for EDA, preprocessing, and visualization.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import pandas as pd

from ..core.config import settings
from ..services.connectors import get_connector
from ..services.preprocessing import GenderDataPreprocessor
from ..services.visualizations import GenderVisualization

router = APIRouter(prefix="/analyze", tags=["Analysis"])


# In-memory storage for analysis results (replace with proper storage in production)
_analysis_cache: Dict[str, Any] = {}


class AnalyzeRequest(BaseModel):
    """Request body for analysis endpoint."""
    dataset_key: str  # 'enrolment', 'demographic', 'biometric'
    year: Optional[int] = None
    geography_level: str = "district"  # 'district', 'state', 'pincode'
    limit: int = 1000  # Number of records to fetch


class AnalysisResult(BaseModel):
    """Analysis result response."""
    analysis_id: str
    dataset_key: str
    n_records: int
    n_districts: int
    preprocessing_report: Dict[str, Any]
    statistics: Dict[str, Any]
    artifacts: Dict[str, Any]
    sanity_checklist: List[Dict[str, str]]


@router.post("/", response_model=AnalysisResult)
async def analyze_dataset(request: AnalyzeRequest):
    """
    Run EDA and preprocessing on the selected dataset.
    
    Performs:
    - Column normalization
    - Gender feature computation
    - Missing value handling
    - Visualization generation
    
    Returns summary statistics, warnings, and artifact paths.
    """
    connector = get_connector()
    
    if request.dataset_key not in connector.known_datasets:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown dataset key: {request.dataset_key}"
        )
    
    try:
        # Fetch data
        resource_id = connector.known_datasets[request.dataset_key]['resource_id']
        df = await connector.fetch_dataset('api1', resource_id, limit=request.limit)
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Dataset returned no records"
            )
        
        # Preprocess
        preprocessor = GenderDataPreprocessor()
        processed_df, report = preprocessor.preprocess(
            df,
            geography_level=request.geography_level,
            imputation_strategy='median'
        )
        
        # Generate visualizations
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = settings.artifacts_dir / analysis_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        viz = GenderVisualization(output_dir=output_dir)
        artifacts = viz.generate_all_visualizations(processed_df)
        
        # Compute statistics
        stats = compute_statistics(processed_df)
        
        # Generate sanity checklist
        sanity_checklist = generate_sanity_checklist(processed_df, report)
        
        # Cache the processed data
        _analysis_cache[analysis_id] = {
            'df': processed_df,
            'report': report,
            'created_at': datetime.now().isoformat()
        }
        
        # Prepare response
        result = AnalysisResult(
            analysis_id=analysis_id,
            dataset_key=request.dataset_key,
            n_records=len(processed_df),
            n_districts=processed_df['district'].nunique() if 'district' in processed_df.columns else 0,
            preprocessing_report={
                'original_rows': report.original_rows,
                'final_rows': report.final_rows,
                'columns_renamed': report.columns_renamed,
                'missing_values': report.missing_values,
                'imputed_columns': report.imputed_columns,
                'computed_features': report.computed_features,
                'warnings': report.warnings
            },
            statistics=stats,
            artifacts={
                key: {
                    'path': val.get('path'),
                    'base64': val.get('base64', '')[:100] + '...' if val.get('base64') else None  # Truncate for response
                } if isinstance(val, dict) else val
                for key, val in artifacts.items()
            },
            sanity_checklist=sanity_checklist
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str):
    """
    Get a previously run analysis by ID.
    """
    if analysis_id not in _analysis_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {analysis_id} not found"
        )
    
    cached = _analysis_cache[analysis_id]
    df = cached['df']
    
    return {
        'analysis_id': analysis_id,
        'created_at': cached['created_at'],
        'n_records': len(df),
        'columns': df.columns.tolist(),
        'statistics': compute_statistics(df)
    }


@router.get("/{analysis_id}/data")
async def get_analysis_data(
    analysis_id: str,
    limit: int = 100,
    offset: int = 0
):
    """
    Get processed data from an analysis.
    """
    if analysis_id not in _analysis_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {analysis_id} not found"
        )
    
    df = _analysis_cache[analysis_id]['df']
    
    # Paginate
    subset = df.iloc[offset:offset + limit]
    
    return {
        'analysis_id': analysis_id,
        'total_records': len(df),
        'offset': offset,
        'limit': limit,
        'data': subset.to_dict(orient='records')
    }


def compute_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute summary statistics from processed data."""
    stats = {
        'total_records': len(df)
    }
    
    if 'female_coverage_ratio' in df.columns:
        coverage = df['female_coverage_ratio'].dropna()
        stats['female_coverage'] = {
            'mean': float(coverage.mean()),
            'median': float(coverage.median()),
            'min': float(coverage.min()),
            'max': float(coverage.max()),
            'std': float(coverage.std())
        }
        
        # Identify worst districts
        worst = df.nsmallest(10, 'female_coverage_ratio')
        stats['worst_districts'] = []
        for _, row in worst.iterrows():
            district_info = {
                'coverage': float(row['female_coverage_ratio'])
            }
            if 'district' in df.columns:
                district_info['district'] = str(row['district'])
            if 'state' in df.columns:
                district_info['state'] = str(row['state'])
            stats['worst_districts'].append(district_info)
    
    if 'gender_gap' in df.columns:
        gap = df['gender_gap'].dropna()
        stats['gender_gap'] = {
            'mean': float(gap.mean()),
            'max_gap': float(gap.max()),
            'min_gap': float(gap.min())
        }
    
    if 'high_risk' in df.columns:
        stats['high_risk_count'] = int(df['high_risk'].sum())
        stats['high_risk_percentage'] = float(df['high_risk'].mean() * 100)
    
    if 'state' in df.columns:
        stats['n_states'] = int(df['state'].nunique())
    
    if 'district' in df.columns:
        stats['n_districts'] = int(df['district'].nunique())
    
    return stats


def generate_sanity_checklist(df: pd.DataFrame, report) -> List[Dict[str, str]]:
    """Generate sanity check items for the analysis."""
    checklist = []
    
    # Check for gender columns
    if 'male_enrolled' not in df.columns or 'female_enrolled' not in df.columns:
        checklist.append({
            'status': 'warning',
            'item': 'Gender columns',
            'message': 'Male/female enrollment columns were estimated from age distribution'
        })
    else:
        checklist.append({
            'status': 'ok',
            'item': 'Gender columns',
            'message': 'Male and female enrollment data available'
        })
    
    # Check for geographic columns
    if 'district' not in df.columns:
        checklist.append({
            'status': 'warning',
            'item': 'District data',
            'message': 'District column not found, analysis at higher geography level'
        })
    else:
        checklist.append({
            'status': 'ok',
            'item': 'District data',
            'message': f'{df["district"].nunique()} unique districts found'
        })
    
    # Check for missing data
    missing_count = sum(report.missing_values.values()) if report.missing_values else 0
    if missing_count > 0:
        checklist.append({
            'status': 'info',
            'item': 'Missing values',
            'message': f'{missing_count} missing values imputed using median strategy'
        })
    else:
        checklist.append({
            'status': 'ok',
            'item': 'Missing values',
            'message': 'No missing values detected'
        })
    
    # Check coverage ratio range
    if 'female_coverage_ratio' in df.columns:
        coverage = df['female_coverage_ratio']
        abnormal = ((coverage < 0) | (coverage > 1)).sum()
        if abnormal > 0:
            checklist.append({
                'status': 'error',
                'item': 'Coverage ratio',
                'message': f'{abnormal} records have invalid coverage ratio (<0 or >1)'
            })
        else:
            checklist.append({
                'status': 'ok',
                'item': 'Coverage ratio',
                'message': 'All coverage ratios within valid range [0, 1]'
            })
    
    return checklist
