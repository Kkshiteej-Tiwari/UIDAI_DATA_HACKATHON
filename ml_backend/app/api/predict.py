"""
Gender Inclusion Tracker - Prediction API Router
Endpoints for making predictions and generating recommendations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Literal
import pandas as pd
import numpy as np
import logging

from ..core.config import settings
from ..services.models import GenderRiskModel
from .train import _models_cache
from .analyze import _analysis_cache

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/predict", tags=["Predictions"])


# Action recommendations based on risk factors
RECOMMENDATIONS = {
    'low_literacy': 'language-literacy-campaign',
    'low_mobile': 'digital-literacy-workshop',
    'low_bank': 'bank-account-drive',
    'high_gender_gap': 'women-only-registration-camp',
    'default': 'mobile-outreach'
}


class PredictRequest(BaseModel):
    """Request body for prediction endpoint."""
    model_id: str
    analysis_id: Optional[str] = None  # Use data from analysis
    rows: Optional[List[Dict[str, Any]]] = None  # Or provide rows directly


class PredictionResult(BaseModel):
    """Single prediction result."""
    index: int
    district: Optional[str] = None
    state: Optional[str] = None
    risk_probability: float
    predicted_high_risk: int
    female_coverage_ratio: Optional[float] = None
    top_drivers: List[Dict[str, Any]]
    recommendation: str
    estimated_target_count: Optional[int] = None


class PredictResponse(BaseModel):
    """Prediction response."""
    model_id: str
    total_predictions: int
    high_risk_count: int
    predictions: List[PredictionResult]


@router.post("/", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Make predictions using a trained model.
    
    For each high-risk district, returns:
    - Risk probability
    - Top contributing features (from SHAP)
    - Action recommendation
    - Estimated number of women to target
    """
    # Get model
    if request.model_id not in _models_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Model {request.model_id} not found"
        )
    
    model_data = _models_cache[request.model_id]
    model = model_data['model']
    
    # Get data
    if request.analysis_id:
        if request.analysis_id not in _analysis_cache:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis {request.analysis_id} not found"
            )
        df = _analysis_cache[request.analysis_id]['df'].copy()
    elif request.rows:
        df = pd.DataFrame(request.rows)
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either 'analysis_id' or 'rows'"
        )
    
    try:
        # Make predictions
        df_pred = model.predict(df)
        
        # Try to compute SHAP explanations (optional if SHAP not installed)
        explanations_map = {}
        try:
            from ..services.explainers import explain_predictions, SHAP_AVAILABLE
            if SHAP_AVAILABLE:
                explanations = explain_predictions(
                    model.model,
                    df_pred,
                    model.feature_names,
                    output_dir=settings.artifacts_dir / f"predictions_{request.model_id}"
                )
                explanations_map = {
                    exp['index']: exp['top_drivers']
                    for exp in explanations.get('high_risk_explanations', [])
                }
        except Exception as exp_error:
            logger.warning(f"SHAP explanations failed: {str(exp_error)}")
        
        # Build predictions
        predictions = []
        for idx, row in df_pred.iterrows():
            # Get top drivers for this prediction
            top_drivers = explanations_map.get(idx, [])
            if not top_drivers and hasattr(model, 'feature_names'):
                # Fallback: use feature importances
                fi = model.metrics.feature_importances if model.metrics else {}
                top_drivers = [
                    {'feature': k, 'shap_value': v, 'contribution': 'risk factor'}
                    for k, v in sorted(fi.items(), key=lambda x: -x[1])[:3]
                ]
            
            # Determine recommendation based on top drivers
            recommendation = determine_recommendation(top_drivers, row)
            
            # Estimate target count
            estimated_count = None
            if 'female_enrolled' in row and pd.notna(row['female_enrolled']):
                if 'female_coverage_ratio' in row and pd.notna(row['female_coverage_ratio']):
                    target_coverage = settings.default_risk_threshold
                    current_coverage = row['female_coverage_ratio']
                    if current_coverage < target_coverage:
                        # Rough estimate of women to enroll
                        shortfall_pct = target_coverage - current_coverage
                        estimated_count = int(row['female_enrolled'] * shortfall_pct / current_coverage)
            
            pred = PredictionResult(
                index=int(idx) if isinstance(idx, (int, np.integer)) else 0,
                district=str(row['district']) if 'district' in row else None,
                state=str(row['state']) if 'state' in row else None,
                risk_probability=float(row['risk_probability']),
                predicted_high_risk=int(row['predicted_high_risk']),
                female_coverage_ratio=float(row['female_coverage_ratio']) if 'female_coverage_ratio' in row else None,
                top_drivers=top_drivers,
                recommendation=recommendation,
                estimated_target_count=estimated_count
            )
            predictions.append(pred)
        
        # Sort by risk probability (highest first)
        predictions.sort(key=lambda x: x.risk_probability, reverse=True)
        
        high_risk_count = sum(1 for p in predictions if p.predicted_high_risk == 1)
        
        return PredictResponse(
            model_id=request.model_id,
            total_predictions=len(predictions),
            high_risk_count=high_risk_count,
            predictions=predictions
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@router.get("/high-risk/{model_id}")
async def get_high_risk_districts(
    model_id: str,
    analysis_id: str,
    limit: int = 50
):
    """
    Get top high-risk districts from a previous prediction.
    
    Convenience endpoint that filters to only high-risk predictions.
    """
    request = PredictRequest(model_id=model_id, analysis_id=analysis_id)
    response = await predict(request)
    
    high_risk = [p for p in response.predictions if p.predicted_high_risk == 1][:limit]
    
    return {
        'model_id': model_id,
        'high_risk_count': len(high_risk),
        'districts': [
            {
                'district': p.district,
                'state': p.state,
                'risk_probability': p.risk_probability,
                'female_coverage_ratio': p.female_coverage_ratio,
                'recommendation': p.recommendation,
                'estimated_target_count': p.estimated_target_count,
                'top_drivers': [d['feature'] for d in p.top_drivers[:3]]
            }
            for p in high_risk
        ]
    }


def determine_recommendation(top_drivers: List[Dict], row: pd.Series) -> str:
    """
    Determine action recommendation based on top risk drivers.
    """
    driver_features = [d.get('feature', '').lower() for d in top_drivers]
    
    # Check for specific patterns
    if any('literacy' in f for f in driver_features):
        return RECOMMENDATIONS['low_literacy']
    
    if any('mobile' in f for f in driver_features):
        return RECOMMENDATIONS['low_mobile']
    
    if any('bank' in f for f in driver_features):
        return RECOMMENDATIONS['low_bank']
    
    if any('gap' in f or 'gender' in f for f in driver_features):
        return RECOMMENDATIONS['high_gender_gap']
    
    # Check row values if available
    if 'gender_gap' in row and pd.notna(row['gender_gap']):
        if row['gender_gap'] > 0.1:  # More than 10% gap
            return RECOMMENDATIONS['high_gender_gap']
    
    return RECOMMENDATIONS['default']
