"""
Gender Inclusion Tracker - Visualization Service
Charts, maps, and visual reports for gender analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import base64
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


def fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 string."""
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def plotly_to_base64(fig) -> str:
    """Convert plotly figure to base64 PNG."""
    try:
        img_bytes = fig.to_image(format='png', scale=2)
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        logger.warning(f"Plotly to image failed, returning empty: {str(e)}")
        return ""


class GenderVisualization:
    """Visualization generator for gender analysis."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or settings.artifacts_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def plot_gender_coverage_bar(
        self,
        df: pd.DataFrame,
        top_n: int = 20,
        save_name: str = 'top_low_coverage.png'
    ) -> Dict[str, Any]:
        """
        Create bar chart of districts with lowest female coverage.
        
        Args:
            df: DataFrame with female_coverage_ratio
            top_n: Number of worst districts to show
            save_name: Filename to save
        
        Returns:
            Dict with path and base64 image
        """
        if 'female_coverage_ratio' not in df.columns:
            return {'error': 'female_coverage_ratio column not found'}
        
        # Sort by coverage and get worst performers
        sorted_df = df.nsmallest(top_n, 'female_coverage_ratio')
        
        # Create label (district name if available)
        if 'district' in sorted_df.columns:
            labels = sorted_df['district']
        elif 'district_code' in sorted_df.columns:
            labels = sorted_df['district_code']
        else:
            labels = [f"District {i}" for i in range(len(sorted_df))]
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        colors = ['#e74c3c' if x < 0.4 else '#f39c12' if x < 0.45 else '#3498db' 
                  for x in sorted_df['female_coverage_ratio']]
        
        bars = ax.barh(range(len(sorted_df)), sorted_df['female_coverage_ratio'] * 100, color=colors)
        ax.set_yticks(range(len(sorted_df)))
        ax.set_yticklabels(labels)
        ax.set_xlabel('Female Coverage Ratio (%)', fontsize=12)
        ax.set_title(f'Top {top_n} Districts with Lowest Female Aadhaar Coverage', fontsize=14)
        ax.axvline(x=50, color='red', linestyle='--', alpha=0.5, label='50% threshold')
        ax.legend()
        
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        base64_img = fig_to_base64(fig)
        plt.close(fig)
        
        return {
            'path': str(save_path),
            'base64': base64_img
        }
    
    def plot_correlation_heatmap(
        self,
        df: pd.DataFrame,
        save_name: str = 'correlation_heatmap.png'
    ) -> Dict[str, Any]:
        """
        Create correlation heatmap between coverage and indicators.
        """
        # Select numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Filter to relevant columns
        relevant_keywords = ['coverage', 'ratio', 'gap', 'enrolled', 'literacy', 
                            'mobile', 'bank', 'age', 'population']
        relevant_cols = [col for col in numeric_cols 
                        if any(kw in col.lower() for kw in relevant_keywords)][:15]
        
        if len(relevant_cols) < 3:
            relevant_cols = numeric_cols[:15]
        
        if len(relevant_cols) < 2:
            return {'error': 'Not enough numeric columns for correlation'}
        
        corr_matrix = df[relevant_cols].corr()
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        cmap = sns.diverging_palette(250, 10, as_cmap=True)
        
        sns.heatmap(
            corr_matrix,
            mask=mask,
            cmap=cmap,
            vmax=1,
            vmin=-1,
            center=0,
            square=True,
            linewidths=0.5,
            annot=True,
            fmt='.2f',
            annot_kws={'size': 8},
            ax=ax
        )
        
        ax.set_title('Correlation Between Gender Coverage and Indicators', fontsize=14)
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        base64_img = fig_to_base64(fig)
        plt.close(fig)
        
        return {
            'path': str(save_path),
            'base64': base64_img
        }
    
    def plot_feature_importance(
        self,
        importance_dict: Dict[str, float],
        save_name: str = 'feature_importance.png'
    ) -> Dict[str, Any]:
        """
        Create feature importance bar chart.
        """
        if not importance_dict:
            return {'error': 'No feature importances provided'}
        
        # Sort by importance
        sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        features, importances = zip(*sorted_features[:15])
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        colors = plt.cm.RdYlGn(np.linspace(0.8, 0.2, len(features)))
        
        bars = ax.barh(range(len(features)), importances, color=colors)
        ax.set_yticks(range(len(features)))
        ax.set_yticklabels(features)
        ax.set_xlabel('Importance Score', fontsize=12)
        ax.set_title('Feature Importance for Risk Prediction', fontsize=14)
        ax.invert_yaxis()
        
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        base64_img = fig_to_base64(fig)
        plt.close(fig)
        
        return {
            'path': str(save_path),
            'base64': base64_img
        }
    
    def plot_roc_pr_curves(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        save_name: str = 'roc_pr_curves.png'
    ) -> Dict[str, Any]:
        """
        Create ROC and Precision-Recall curves.
        """
        from sklearn.metrics import roc_curve, precision_recall_curve, auc
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # ROC Curve
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        roc_auc = auc(fpr, tpr)
        
        axes[0].plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
        axes[0].plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        axes[0].set_xlim([0.0, 1.0])
        axes[0].set_ylim([0.0, 1.05])
        axes[0].set_xlabel('False Positive Rate', fontsize=12)
        axes[0].set_ylabel('True Positive Rate', fontsize=12)
        axes[0].set_title('Receiver Operating Characteristic (ROC)', fontsize=14)
        axes[0].legend(loc='lower right')
        axes[0].grid(True, alpha=0.3)
        
        # Precision-Recall Curve
        precision, recall, _ = precision_recall_curve(y_true, y_prob)
        pr_auc = auc(recall, precision)
        
        axes[1].plot(recall, precision, color='purple', lw=2, label=f'PR curve (AUC = {pr_auc:.3f})')
        axes[1].set_xlim([0.0, 1.0])
        axes[1].set_ylim([0.0, 1.05])
        axes[1].set_xlabel('Recall', fontsize=12)
        axes[1].set_ylabel('Precision', fontsize=12)
        axes[1].set_title('Precision-Recall Curve', fontsize=14)
        axes[1].legend(loc='lower left')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        base64_img = fig_to_base64(fig)
        plt.close(fig)
        
        return {
            'path': str(save_path),
            'base64': base64_img,
            'roc_auc': float(roc_auc),
            'pr_auc': float(pr_auc)
        }
    
    def plot_gender_distribution_by_state(
        self,
        df: pd.DataFrame,
        save_name: str = 'gender_distribution_states.png'
    ) -> Dict[str, Any]:
        """
        Create grouped bar chart of male vs female enrollment by state.
        """
        if 'state' not in df.columns:
            return {'error': 'state column not found'}
        
        # Aggregate by state
        state_agg = df.groupby('state').agg({
            'male_enrolled': 'sum',
            'female_enrolled': 'sum'
        }).reset_index()
        
        # Sort by total enrollment
        state_agg['total'] = state_agg['male_enrolled'] + state_agg['female_enrolled']
        state_agg = state_agg.nlargest(15, 'total')
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        x = np.arange(len(state_agg))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, state_agg['male_enrolled'] / 1e6, width, label='Male', color='#3498db')
        bars2 = ax.bar(x + width/2, state_agg['female_enrolled'] / 1e6, width, label='Female', color='#e74c3c')
        
        ax.set_ylabel('Enrollment (Millions)', fontsize=12)
        ax.set_title('Aadhaar Enrollment by Gender and State', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(state_agg['state'], rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        save_path = self.output_dir / save_name
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        base64_img = fig_to_base64(fig)
        plt.close(fig)
        
        return {
            'path': str(save_path),
            'base64': base64_img
        }
    
    def create_choropleth_data(
        self,
        df: pd.DataFrame,
        geo_column: str = 'state',
        value_column: str = 'female_coverage_ratio'
    ) -> Dict[str, Any]:
        """
        Prepare data for choropleth map visualization.
        
        Note: Full choropleth rendering requires GeoJSON data.
        Returns aggregated data that can be used with frontend mapping libraries.
        """
        if geo_column not in df.columns:
            return {'error': f'{geo_column} column not found'}
        
        if value_column not in df.columns:
            return {'error': f'{value_column} column not found'}
        
        # Aggregate by geography
        agg_df = df.groupby(geo_column).agg({
            value_column: 'mean',
            'male_enrolled': 'sum' if 'male_enrolled' in df.columns else 'first',
            'female_enrolled': 'sum' if 'female_enrolled' in df.columns else 'first',
        }).reset_index()
        
        # Convert to list of dicts for JSON response
        map_data = agg_df.to_dict(orient='records')
        
        return {
            'data': map_data,
            'value_column': value_column,
            'min_value': float(agg_df[value_column].min()),
            'max_value': float(agg_df[value_column].max()),
            'mean_value': float(agg_df[value_column].mean())
        }
    
    def generate_all_visualizations(
        self,
        df: pd.DataFrame,
        feature_importance: Optional[Dict[str, float]] = None,
        y_true: Optional[np.ndarray] = None,
        y_prob: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Generate all visualization artifacts.
        """
        artifacts = {}
        
        # Gender coverage bar chart
        try:
            artifacts['coverage_bar'] = self.plot_gender_coverage_bar(df)
        except Exception as e:
            logger.error(f"Failed to create coverage bar chart: {str(e)}")
            artifacts['coverage_bar'] = {'error': str(e)}
        
        # Correlation heatmap
        try:
            artifacts['correlation_heatmap'] = self.plot_correlation_heatmap(df)
        except Exception as e:
            logger.error(f"Failed to create correlation heatmap: {str(e)}")
            artifacts['correlation_heatmap'] = {'error': str(e)}
        
        # Feature importance
        if feature_importance:
            try:
                artifacts['feature_importance'] = self.plot_feature_importance(feature_importance)
            except Exception as e:
                logger.error(f"Failed to create feature importance chart: {str(e)}")
                artifacts['feature_importance'] = {'error': str(e)}
        
        # ROC/PR curves
        if y_true is not None and y_prob is not None:
            try:
                artifacts['roc_pr_curves'] = self.plot_roc_pr_curves(y_true, y_prob)
            except Exception as e:
                logger.error(f"Failed to create ROC/PR curves: {str(e)}")
                artifacts['roc_pr_curves'] = {'error': str(e)}
        
        # State distribution
        if 'state' in df.columns:
            try:
                artifacts['state_distribution'] = self.plot_gender_distribution_by_state(df)
            except Exception as e:
                logger.error(f"Failed to create state distribution chart: {str(e)}")
                artifacts['state_distribution'] = {'error': str(e)}
        
        # Choropleth data
        try:
            artifacts['choropleth_data'] = self.create_choropleth_data(df)
        except Exception as e:
            logger.error(f"Failed to prepare choropleth data: {str(e)}")
            artifacts['choropleth_data'] = {'error': str(e)}
        
        return artifacts
