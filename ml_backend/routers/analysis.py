"""
Analysis Router - ML training, prediction, and risk assessment endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from routers.datasets import get_selected_data
from services.feature_engineering import feature_engineer
from services.model_selector import model_selector
from models.supervised import supervised_models
from models.unsupervised import unsupervised_models
from visualizations.charts import chart_generator


router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request model for analysis"""
    aggregation_level: str = "state"  # "state" or "district"
    include_proxy_labels: bool = True


class TrainRequest(BaseModel):
    """Request model for model training"""
    approach: str = "auto"  # "auto", "supervised", "unsupervised"
    model_type: str = "auto"  # "auto", "xgboost", "random_forest", "isolation_forest", "kmeans"
    target_column: str = "risk_category"


# Global state for analysis results
analysis_results: Dict[str, Any] = {}
training_results: Dict[str, Any] = {}


@router.post("/analyze")
async def run_analysis(request: AnalysisRequest):
    """
    Run feature engineering and risk analysis on selected datasets
    
    This endpoint:
    1. Processes all selected datasets
    2. Creates engineered features
    3. Generates proxy risk labels (if requested)
    4. Returns analysis summary
    """
    global analysis_results
    
    selected_data = get_selected_data()
    
    if not selected_data:
        raise HTTPException(
            status_code=400,
            detail="No datasets selected. Use POST /api/select-dataset first."
        )
    
    # Get individual dataframes
    enrol_df = selected_data.get('enrolment')
    demo_df = selected_data.get('demographic')
    bio_df = selected_data.get('biometric')
    
    # Create risk features
    features_df = feature_engineer.create_risk_features(
        enrolment_df=enrol_df,
        demographic_df=demo_df,
        biometric_df=bio_df,
        aggregation_level=request.aggregation_level
    )
    
    if features_df.empty:
        raise HTTPException(
            status_code=500,
            detail="Feature engineering produced no results"
        )
    
    # Add proxy risk labels
    if request.include_proxy_labels:
        features_df = feature_engineer.create_proxy_risk_labels(features_df)
    
    # Store results
    analysis_results = {
        'features_df': features_df,
        'feature_names': feature_engineer.get_feature_names(),
        'aggregation_level': request.aggregation_level
    }
    
    # Build response
    response = {
        "status": "success",
        "aggregation_level": request.aggregation_level,
        "records_analyzed": len(features_df),
        "features_created": len(features_df.columns),
        "feature_list": list(features_df.columns),
        "data_sources_used": list(selected_data.keys())
    }
    
    # Add risk summary if proxy labels created
    if 'risk_category' in features_df.columns:
        risk_dist = features_df['risk_category'].value_counts().to_dict()
        response["risk_distribution"] = {str(k): int(v) for k, v in risk_dist.items()}
    
    if 'proxy_risk_score' in features_df.columns:
        response["risk_score_stats"] = {
            "mean": float(features_df['proxy_risk_score'].mean()),
            "median": float(features_df['proxy_risk_score'].median()),
            "min": float(features_df['proxy_risk_score'].min()),
            "max": float(features_df['proxy_risk_score'].max())
        }
    
    # Sample of high-risk entities
    if 'proxy_risk_score' in features_df.columns:
        high_risk = features_df.nlargest(5, 'proxy_risk_score')
        if 'state' in high_risk.columns:
            response["top_high_risk"] = high_risk[['state', 'proxy_risk_score', 'risk_category']].to_dict('records')
    
    return response


@router.post("/train-model")
async def train_model(request: TrainRequest):
    """
    Train ML model on analyzed data
    
    Supports:
    - Auto model selection
    - Supervised: XGBoost, Random Forest, Logistic Regression
    - Unsupervised: Isolation Forest, KMeans, DBSCAN
    """
    global training_results
    
    if not analysis_results:
        raise HTTPException(
            status_code=400,
            detail="No analysis results. Run POST /api/analyze first."
        )
    
    features_df = analysis_results['features_df']
    
    # Run model selection and training
    results = model_selector.select_and_train(
        df=features_df,
        target_col=request.target_column if request.approach != 'unsupervised' else None,
        approach=request.approach,
        model_type=request.model_type
    )
    
    training_results = results
    
    # Generate visualizations
    charts = []
    
    if 'proxy_risk_score' in features_df.columns:
        charts.append(chart_generator.risk_distribution_histogram(
            features_df['proxy_risk_score'].values
        ))
    
    if 'risk_category' in features_df.columns:
        charts.append(chart_generator.risk_by_category_bar(features_df))
    
    if 'state' in features_df.columns and 'proxy_risk_score' in features_df.columns:
        charts.append(chart_generator.state_risk_heatmap(features_df))
    
    if results.get('feature_importance'):
        charts.append(chart_generator.feature_importance_chart(results['feature_importance']))
    
    charts.append(chart_generator.age_group_risk(features_df))
    
    return {
        "status": "success",
        "approach": results['approach'],
        "model_type": results['model_type'],
        "reason": results.get('reason'),
        "training_results": results.get('training_results'),
        "evaluation": results.get('evaluation'),
        "feature_importance": results.get('feature_importance'),
        "visualizations_generated": len(charts),
        "visualization_paths": charts
    }


@router.get("/risk-summary")
async def get_risk_summary():
    """
    Get key risk indicators and high-risk regions
    
    Returns:
    - % population at high risk
    - Top 5 high-risk states/districts
    - Average time since last biometric update
    - Elderly risk multiplier
    """
    if not analysis_results:
        raise HTTPException(
            status_code=400,
            detail="No analysis results. Run POST /api/analyze first."
        )
    
    features_df = analysis_results['features_df']
    
    summary = {
        "total_entities": len(features_df),
        "aggregation_level": analysis_results['aggregation_level']
    }
    
    # Risk category distribution
    if 'risk_category' in features_df.columns:
        risk_counts = features_df['risk_category'].value_counts()
        total = len(features_df)
        
        summary["risk_distribution"] = {
            str(k): {"count": int(v), "percentage": round(v/total*100, 2)}
            for k, v in risk_counts.items()
        }
        
        high_risk_count = risk_counts.get('High', 0) + risk_counts.get('Critical', 0)
        summary["high_risk_percentage"] = round(high_risk_count / total * 100, 2)
    
    # Top high-risk entities
    if 'proxy_risk_score' in features_df.columns:
        top_cols = ['state', 'proxy_risk_score', 'risk_category']
        if 'district' in features_df.columns:
            top_cols.insert(1, 'district')
        
        available_cols = [c for c in top_cols if c in features_df.columns]
        top_risk = features_df.nlargest(5, 'proxy_risk_score')[available_cols]
        summary["top_5_high_risk"] = top_risk.to_dict('records')
    
    # Average risk score
    if 'proxy_risk_score' in features_df.columns:
        summary["average_risk_score"] = round(features_df['proxy_risk_score'].mean(), 4)
    
    # High risk state indicator
    if 'is_high_risk_state' in features_df.columns:
        hr_states = features_df[features_df['is_high_risk_state'] == 1]
        if len(hr_states) > 0 and 'proxy_risk_score' in hr_states.columns:
            hr_avg = hr_states['proxy_risk_score'].mean()
            other_avg = features_df[features_df['is_high_risk_state'] == 0]['proxy_risk_score'].mean()
            summary["high_risk_state_multiplier"] = round(hr_avg / (other_avg + 0.01), 2)
    
    return summary


@router.get("/explain-model")
async def explain_model():
    """
    Get model explanation and feature importance
    """
    if not training_results:
        raise HTTPException(
            status_code=400,
            detail="No model trained. Run POST /api/train-model first."
        )
    
    explanation = model_selector.get_explanation()
    
    return {
        "model_explanation": explanation,
        "feature_importance": training_results.get('feature_importance', {}),
        "training_metrics": training_results.get('evaluation', {}),
        "interpretation": _generate_interpretation(
            explanation,
            training_results.get('feature_importance', {})
        )
    }


def _generate_interpretation(explanation: Dict, importance: Dict) -> str:
    """Generate human-readable interpretation"""
    lines = []
    
    lines.append(f"**Model Selection**: {explanation.get('model_type', 'Unknown')}")
    lines.append(f"**Approach**: {explanation.get('approach', 'Unknown')}")
    lines.append(f"**Reason**: {explanation.get('reason', 'Not specified')}")
    lines.append("")
    
    if importance:
        lines.append("**Key Risk Factors**:")
        top_features = list(importance.items())[:5]
        for i, (feat, imp) in enumerate(top_features, 1):
            lines.append(f"{i}. {feat}: {imp:.4f}")
    
    return "\n".join(lines)
