"""
Gender Inclusion Tracker - Training API Router
Endpoints for ML model training.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import numpy as np

from ..core.config import settings
from ..services.models import GenderRiskModel, TrainedModel
from ..services.visualizations import GenderVisualization
from .analyze import _analysis_cache

router = APIRouter(prefix="/train", tags=["Training"])


# In-memory model storage (replace with proper storage in production)
_models_cache: Dict[str, Dict[str, Any]] = {}


class TrainRequest(BaseModel):
    """Request body for training endpoint."""
    analysis_id: str  # ID from /analyze endpoint
    labeling_strategy: Literal["coverage_threshold", "percentile"] = "coverage_threshold"
    threshold: float = 0.85  # Threshold for high-risk classification
    model: Literal["auto", "lightgbm", "logistic", "randomforest"] = "lightgbm"
    tune: bool = True  # Whether to tune hyperparameters
    use_smote: bool = True  # Whether to use SMOTE for class imbalance


class TrainResult(BaseModel):
    """Training result response."""
    model_id: str
    model_type: str
    metrics: Dict[str, Any]
    feature_importances: Dict[str, float]
    threshold: float
    training_time: str
    artifacts: Dict[str, Any]


@router.post("/", response_model=TrainResult)
async def train_model(request: TrainRequest):
    """
    Train a machine learning model to predict high-risk districts.
    
    Uses the preprocessed data from a previous analysis run.
    Supports LightGBM (recommended), Logistic Regression, and Random Forest.
    
    Returns model metrics, feature importances, and saved model ID.
    """
    # Get cached analysis data
    if request.analysis_id not in _analysis_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {request.analysis_id} not found. Run /api/analyze first."
        )
    
    cached = _analysis_cache[request.analysis_id]
    df = cached['df'].copy()
    
    try:
        # Create high-risk label if not exists
        if 'high_risk' not in df.columns:
            if 'female_coverage_ratio' not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot create label: female_coverage_ratio not found"
                )
            
            if request.labeling_strategy == 'coverage_threshold':
                df['high_risk'] = (df['female_coverage_ratio'] < request.threshold).astype(int)
            else:
                # Percentile-based
                percentile_threshold = df['female_coverage_ratio'].quantile(0.15)
                df['high_risk'] = (df['female_coverage_ratio'] < percentile_threshold).astype(int)
        
        # Check class distribution
        class_counts = df['high_risk'].value_counts()
        if len(class_counts) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Only one class found in target. Adjust threshold (current: {request.threshold})"
            )
        
        # Determine model type
        model_type = request.model if request.model != 'auto' else 'lightgbm'
        
        # Train model
        start_time = datetime.now()
        model = GenderRiskModel(model_type=model_type)
        trained = model.train(
            df,
            target_column='high_risk',
            tune=request.tune,
            use_smote=request.use_smote
        )
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Save model
        model_path = model.save()
        
        # Generate visualizations
        output_dir = settings.artifacts_dir / trained.model_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        viz = GenderVisualization(output_dir=output_dir)
        
        # Feature importance chart
        fi_artifact = viz.plot_feature_importance(
            trained.metrics.feature_importances,
            save_name='feature_importance.png'
        )
        
        # ROC/PR curves
        df_with_pred = model.predict(df)
        y_true = df_with_pred['high_risk'].values
        y_prob = df_with_pred['risk_probability'].values
        
        roc_artifact = viz.plot_roc_pr_curves(
            y_true, y_prob,
            save_name='roc_pr_curves.png'
        )
        
        # Cache model for predictions
        _models_cache[trained.model_id] = {
            'model': model,
            'trained': trained,
            'created_at': datetime.now().isoformat()
        }
        
        return TrainResult(
            model_id=trained.model_id,
            model_type=trained.model_type,
            metrics={
                'accuracy': trained.metrics.accuracy,
                'precision': trained.metrics.precision,
                'recall': trained.metrics.recall,
                'f1': trained.metrics.f1,
                'roc_auc': trained.metrics.roc_auc,
                'pr_auc': trained.metrics.pr_auc,
                'confusion_matrix': trained.metrics.confusion_matrix,
                'class_distribution': class_counts.to_dict()
            },
            feature_importances=trained.metrics.feature_importances,
            threshold=request.threshold,
            training_time=f"{training_time:.2f}s",
            artifacts={
                'model_path': str(model_path),
                'feature_importance': fi_artifact.get('path'),
                'roc_pr_curves': roc_artifact.get('path')
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Training failed: {str(e)}"
        )


@router.get("/models")
async def list_models():
    """
    List all trained models.
    """
    models = []
    for model_id, data in _models_cache.items():
        trained = data['trained']
        models.append({
            'model_id': model_id,
            'model_type': trained.model_type,
            'created_at': trained.created_at,
            'metrics': {
                'accuracy': trained.metrics.accuracy,
                'f1': trained.metrics.f1,
                'roc_auc': trained.metrics.roc_auc
            }
        })
    
    return {'models': models}


@router.get("/models/{model_id}")
async def get_model_info(model_id: str):
    """
    Get detailed information about a trained model.
    """
    if model_id not in _models_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Model {model_id} not found"
        )
    
    data = _models_cache[model_id]
    trained = data['trained']
    
    return {
        'model_id': trained.model_id,
        'model_type': trained.model_type,
        'created_at': trained.created_at,
        'threshold': trained.threshold,
        'features': trained.features,
        'hyperparameters': trained.hyperparameters,
        'metrics': {
            'accuracy': trained.metrics.accuracy,
            'precision': trained.metrics.precision,
            'recall': trained.metrics.recall,
            'f1': trained.metrics.f1,
            'roc_auc': trained.metrics.roc_auc,
            'pr_auc': trained.metrics.pr_auc,
            'confusion_matrix': trained.metrics.confusion_matrix
        },
        'feature_importances': trained.metrics.feature_importances
    }
