"""
Gender Inclusion Tracker - Model Explainability
SHAP-based explanations for model predictions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import base64
from io import BytesIO

# Try to import SHAP (optional dependency)
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    shap = None

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)



class ModelExplainer:
    """SHAP-based model explainer for understanding predictions."""
    
    def __init__(self, model, feature_names: List[str]):
        """
        Initialize explainer with a trained model.
        
        Args:
            model: Trained sklearn-compatible model
            feature_names: List of feature column names
        """
        self.model = model
        self.feature_names = feature_names
        self.explainer = None
        self.shap_values = None
    
    def compute_shap_values(
        self,
        X: np.ndarray,
        sample_size: int = 100
    ) -> np.ndarray:
        """
        Compute SHAP values for the given data.
        
        Args:
            X: Feature matrix
            sample_size: Number of samples to use for background (for efficiency)
        
        Returns:
            SHAP values array
        """
        # Sample background data for efficiency
        if len(X) > sample_size:
            background = X[np.random.choice(len(X), sample_size, replace=False)]
        else:
            background = X
        
        # Create explainer based on model type
        try:
            if hasattr(self.model, 'predict_proba'):
                self.explainer = shap.TreeExplainer(self.model, background)
            else:
                self.explainer = shap.KernelExplainer(self.model.predict, background)
        except Exception:
            # Fallback to KernelExplainer
            self.explainer = shap.KernelExplainer(
                lambda x: self.model.predict_proba(x)[:, 1],
                background
            )
        
        self.shap_values = self.explainer.shap_values(X)
        
        # Handle multi-output (take class 1 for binary classification)
        if isinstance(self.shap_values, list):
            self.shap_values = self.shap_values[1]
        
        return self.shap_values
    
    def get_top_features_for_prediction(
        self,
        row_idx: int,
        n_features: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get the top contributing features for a specific prediction.
        
        Args:
            row_idx: Index of the row to explain
            n_features: Number of top features to return
        
        Returns:
            List of dicts with feature name, value, and contribution
        """
        if self.shap_values is None:
            raise ValueError("Call compute_shap_values() first")
        
        row_shap = self.shap_values[row_idx]
        
        # Sort by absolute contribution
        sorted_idx = np.argsort(-np.abs(row_shap))[:n_features]
        
        return [
            {
                'feature': self.feature_names[i],
                'shap_value': float(row_shap[i]),
                'contribution': 'increases risk' if row_shap[i] > 0 else 'decreases risk'
            }
            for i in sorted_idx
        ]
    
    def get_global_feature_importance(self) -> Dict[str, float]:
        """
        Get global feature importance based on mean absolute SHAP values.
        
        Returns:
            Dict mapping feature names to importance scores
        """
        if self.shap_values is None:
            raise ValueError("Call compute_shap_values() first")
        
        mean_abs_shap = np.abs(self.shap_values).mean(axis=0)
        
        return {
            name: float(importance)
            for name, importance in zip(self.feature_names, mean_abs_shap)
        }
    
    def plot_summary(
        self,
        X: np.ndarray,
        save_path: Optional[Path] = None
    ) -> Tuple[Optional[str], Optional[Path]]:
        """
        Create SHAP summary plot.
        
        Args:
            X: Feature matrix
            save_path: Optional path to save the plot
        
        Returns:
            Tuple of (base64 encoded image, save path)
        """
        if self.shap_values is None:
            self.compute_shap_values(X)
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        shap.summary_plot(
            self.shap_values,
            X,
            feature_names=self.feature_names,
            show=False,
            plot_type='bar'
        )
        
        plt.title('Feature Importance (SHAP Values)', fontsize=14)
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        base64_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Save to file if path provided
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info("SHAP summary plot saved", path=str(save_path))
        
        plt.close(fig)
        
        return base64_img, save_path
    
    def plot_waterfall(
        self,
        row_idx: int,
        X: np.ndarray,
        save_path: Optional[Path] = None
    ) -> Tuple[Optional[str], Optional[Path]]:
        """
        Create SHAP waterfall plot for a single prediction.
        
        Args:
            row_idx: Index of the row to explain
            X: Feature matrix
            save_path: Optional path to save the plot
        
        Returns:
            Tuple of (base64 encoded image, save path)
        """
        if self.shap_values is None:
            self.compute_shap_values(X)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create explanation object
        explanation = shap.Explanation(
            values=self.shap_values[row_idx],
            base_values=self.explainer.expected_value if hasattr(self.explainer, 'expected_value') else 0,
            data=X[row_idx],
            feature_names=self.feature_names
        )
        
        shap.waterfall_plot(explanation, show=False)
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        base64_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Save to file
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.close(fig)
        
        return base64_img, save_path


def explain_predictions(
    model,
    df: pd.DataFrame,
    feature_names: List[str],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Generate explanations for model predictions.
    
    Args:
        model: Trained model
        df: DataFrame with predictions
        feature_names: List of feature column names
        output_dir: Directory to save plots
    
    Returns:
        Dict with explanation artifacts
    """
    if output_dir is None:
        output_dir = settings.artifacts_dir / f"explanations_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get feature matrix
    X = df[feature_names].values
    X = np.nan_to_num(X, nan=0.0)
    
    # Create explainer
    explainer = ModelExplainer(model, feature_names)
    explainer.compute_shap_values(X)
    
    # Generate summary plot
    summary_base64, summary_path = explainer.plot_summary(
        X,
        save_path=output_dir / 'shap_summary.png'
    )
    
    # Get global importance
    global_importance = explainer.get_global_feature_importance()
    
    # Get explanations for high-risk predictions
    high_risk_explanations = []
    if 'predicted_high_risk' in df.columns:
        high_risk_idx = df[df['predicted_high_risk'] == 1].index.tolist()[:10]
        
        for idx in high_risk_idx:
            row_position = df.index.get_loc(idx)
            top_features = explainer.get_top_features_for_prediction(row_position, n_features=5)
            
            explanation = {
                'index': int(idx),
                'top_drivers': top_features
            }
            
            # Add geographic info if available
            for col in ['district', 'state', 'district_code']:
                if col in df.columns:
                    explanation[col] = str(df.loc[idx, col])
            
            high_risk_explanations.append(explanation)
    
    return {
        'global_importance': global_importance,
        'summary_plot_path': str(summary_path) if summary_path else None,
        'summary_plot_base64': summary_base64,
        'high_risk_explanations': high_risk_explanations
    }
