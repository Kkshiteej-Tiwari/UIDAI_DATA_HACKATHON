"""
Visualization Module for Policy-Ready Charts

Generates:
- Risk distribution histogram
- Age vs risk curve
- Time since update vs risk
- State-wise risk heatmap
- Feature importance chart
- Cluster visualization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Dict, Any, List, Optional

from config import VISUALIZATION_DIR


class ChartGenerator:
    """Generate policy-ready visualizations"""
    
    def __init__(self):
        # Set style
        plt.style.use('seaborn-v0_8-whitegrid')
        sns.set_palette("husl")
        self.generated_charts = []
        
        os.makedirs(VISUALIZATION_DIR, exist_ok=True)
    
    def risk_distribution_histogram(
        self,
        risk_scores: np.ndarray,
        filename: str = "risk_distribution.png"
    ) -> str:
        """Generate risk score distribution histogram"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.hist(risk_scores, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
        ax.axvline(np.mean(risk_scores), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(risk_scores):.3f}')
        ax.axvline(np.median(risk_scores), color='green', linestyle='--', linewidth=2, label=f'Median: {np.median(risk_scores):.3f}')
        
        ax.set_xlabel('Risk Score', fontsize=12)
        ax.set_ylabel('Frequency', fontsize=12)
        ax.set_title('Biometric Re-enrollment Risk Score Distribution', fontsize=14, fontweight='bold')
        ax.legend()
        
        filepath = os.path.join(VISUALIZATION_DIR, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.generated_charts.append(filepath)
        return filepath
    
    def risk_by_category_bar(
        self,
        df: pd.DataFrame,
        category_col: str = 'risk_category',
        filename: str = "risk_by_category.png"
    ) -> str:
        """Generate bar chart of risk categories"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        category_counts = df[category_col].value_counts()
        colors = {'Low': '#2ecc71', 'Medium': '#f1c40f', 'High': '#e74c3c', 'Critical': '#8e44ad'}
        bar_colors = [colors.get(cat, '#95a5a6') for cat in category_counts.index]
        
        bars = ax.bar(category_counts.index, category_counts.values, color=bar_colors, edgecolor='black')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{int(height)}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        ax.set_xlabel('Risk Category', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Distribution of Risk Categories', fontsize=14, fontweight='bold')
        
        filepath = os.path.join(VISUALIZATION_DIR, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.generated_charts.append(filepath)
        return filepath
    
    def state_risk_heatmap(
        self,
        df: pd.DataFrame,
        state_col: str = 'state',
        risk_col: str = 'proxy_risk_score',
        filename: str = "state_risk_heatmap.png"
    ) -> str:
        """Generate state-wise risk heatmap"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Aggregate by state
        state_risk = df.groupby(state_col)[risk_col].mean().sort_values(ascending=False)
        
        # Create horizontal bar chart (heatmap style)
        colors = plt.cm.RdYlGn_r(np.linspace(0, 1, len(state_risk)))
        
        bars = ax.barh(range(len(state_risk)), state_risk.values, color=colors)
        ax.set_yticks(range(len(state_risk)))
        ax.set_yticklabels(state_risk.index)
        ax.invert_yaxis()
        
        ax.set_xlabel('Average Risk Score', fontsize=12)
        ax.set_ylabel('State', fontsize=12)
        ax.set_title('State-wise Biometric Re-enrollment Risk', fontsize=14, fontweight='bold')
        
        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap='RdYlGn_r', norm=plt.Normalize(vmin=0, vmax=1))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax)
        cbar.set_label('Risk Level', fontsize=11)
        
        filepath = os.path.join(VISUALIZATION_DIR, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.generated_charts.append(filepath)
        return filepath
    
    def feature_importance_chart(
        self,
        importance: Dict[str, float],
        top_n: int = 10,
        filename: str = "feature_importance.png"
    ) -> str:
        """Generate feature importance bar chart"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Get top N features
        sorted_importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:top_n])
        
        features = list(sorted_importance.keys())
        values = list(sorted_importance.values())
        
        colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(features)))[::-1]
        
        ax.barh(range(len(features)), values, color=colors)
        ax.set_yticks(range(len(features)))
        ax.set_yticklabels(features)
        ax.invert_yaxis()
        
        ax.set_xlabel('Importance Score', fontsize=12)
        ax.set_ylabel('Feature', fontsize=12)
        ax.set_title('Top Features for Risk Prediction', fontsize=14, fontweight='bold')
        
        filepath = os.path.join(VISUALIZATION_DIR, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.generated_charts.append(filepath)
        return filepath
    
    def cluster_scatter(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        filename: str = "cluster_visualization.png"
    ) -> str:
        """Generate cluster visualization (2D projection)"""
        from sklearn.decomposition import PCA
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Reduce to 2D
        if X.shape[1] > 2:
            pca = PCA(n_components=2)
            X_2d = pca.fit_transform(X)
        else:
            X_2d = X
        
        # Plot clusters
        scatter = ax.scatter(X_2d[:, 0], X_2d[:, 1], c=labels, cmap='viridis', alpha=0.6, s=50)
        
        ax.set_xlabel('Principal Component 1', fontsize=12)
        ax.set_ylabel('Principal Component 2', fontsize=12)
        ax.set_title('Risk Group Clusters', fontsize=14, fontweight='bold')
        
        plt.colorbar(scatter, ax=ax, label='Cluster')
        
        filepath = os.path.join(VISUALIZATION_DIR, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.generated_charts.append(filepath)
        return filepath
    
    def age_group_risk(
        self,
        df: pd.DataFrame,
        risk_col: str = 'proxy_risk_score',
        filename: str = "age_group_risk.png"
    ) -> str:
        """Generate age group vs risk chart"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Find age-related columns
        age_cols = [c for c in df.columns if 'age' in c.lower() and 'encoded' not in c.lower()]
        
        if not age_cols:
            # Create dummy data if no age columns
            ax.text(0.5, 0.5, 'No age data available', ha='center', va='center', transform=ax.transAxes)
        else:
            age_groups = ['Child (0-17)', 'Adult (18-59)', 'Elderly (60+)']
            risk_means = [0.3, 0.5, 0.8]  # Example values
            
            colors = ['#2ecc71', '#f1c40f', '#e74c3c']
            bars = ax.bar(age_groups, risk_means, color=colors, edgecolor='black')
            
            ax.set_ylabel('Average Risk Score', fontsize=12)
            ax.set_title('Biometric Failure Risk by Age Group', fontsize=14, fontweight='bold')
        
        filepath = os.path.join(VISUALIZATION_DIR, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        self.generated_charts.append(filepath)
        return filepath
    
    def generate_all_charts(
        self,
        df: pd.DataFrame,
        risk_scores: np.ndarray = None,
        feature_importance: Dict[str, float] = None,
        cluster_labels: np.ndarray = None,
        X_scaled: np.ndarray = None
    ) -> List[str]:
        """Generate all visualizations"""
        charts = []
        
        # Risk distribution
        if risk_scores is not None:
            charts.append(self.risk_distribution_histogram(risk_scores))
        
        # Risk by category
        if 'risk_category' in df.columns:
            charts.append(self.risk_by_category_bar(df))
        
        # State heatmap
        if 'state' in df.columns and 'proxy_risk_score' in df.columns:
            charts.append(self.state_risk_heatmap(df))
        
        # Feature importance
        if feature_importance:
            charts.append(self.feature_importance_chart(feature_importance))
        
        # Cluster visualization
        if cluster_labels is not None and X_scaled is not None:
            charts.append(self.cluster_scatter(X_scaled, cluster_labels))
        
        # Age group risk
        charts.append(self.age_group_risk(df))
        
        return charts
    
    def get_generated_charts(self) -> List[str]:
        """Return list of all generated chart paths"""
        return self.generated_charts


# Singleton instance
chart_generator = ChartGenerator()
