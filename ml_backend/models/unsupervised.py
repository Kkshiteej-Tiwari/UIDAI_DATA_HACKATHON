"""
Unsupervised ML Models for Biometric Risk Detection

Models:
- KMeans (clustering into risk groups)
- Isolation Forest (anomaly detection)
- DBSCAN (density-based clustering)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from sklearn.cluster import KMeans, DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score
import joblib
import os

from config import MODEL_CONFIG, MODEL_DIR


class UnsupervisedModels:
    """Unsupervised ML models for risk detection without labels"""
    
    def __init__(self):
        self.models = {}
        self.trained_model = None
        self.model_type = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.cluster_labels = None
        
    def prepare_data(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None
    ) -> np.ndarray:
        """
        Prepare and scale data for unsupervised learning
        
        Args:
            df: DataFrame with features
            feature_cols: List of feature columns (auto-detect if None)
            
        Returns:
            Scaled feature array
        """
        # Auto-detect numeric feature columns
        if feature_cols is None:
            exclude_cols = ['state', 'district', 'risk_category', 'proxy_risk_score']
            feature_cols = [c for c in df.columns if c not in exclude_cols and df[c].dtype in ['int64', 'float64']]
        
        self.feature_names = feature_cols
        X = df[feature_cols].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled
    
    def train_kmeans(self, X: np.ndarray, n_clusters: int = None) -> KMeans:
        """
        Train KMeans clustering
        
        Args:
            X: Scaled feature array
            n_clusters: Number of clusters (default from config)
            
        Returns:
            Trained KMeans model
        """
        if n_clusters is None:
            n_clusters = MODEL_CONFIG['kmeans']['n_clusters']
        
        model = KMeans(
            n_clusters=n_clusters,
            random_state=MODEL_CONFIG['kmeans']['random_state'],
            n_init=10
        )
        model.fit(X)
        
        self.models['kmeans'] = model
        self.cluster_labels = model.labels_
        
        return model
    
    def train_isolation_forest(self, X: np.ndarray, contamination: float = None) -> IsolationForest:
        """
        Train Isolation Forest for anomaly detection
        
        Args:
            X: Scaled feature array
            contamination: Expected proportion of anomalies
            
        Returns:
            Trained Isolation Forest model
        """
        if contamination is None:
            contamination = MODEL_CONFIG['isolation_forest']['contamination']
        
        model = IsolationForest(
            contamination=contamination,
            random_state=MODEL_CONFIG['isolation_forest']['random_state'],
            n_estimators=100
        )
        model.fit(X)
        
        self.models['isolation_forest'] = model
        
        return model
    
    def train_dbscan(self, X: np.ndarray, eps: float = 0.5, min_samples: int = 5) -> DBSCAN:
        """
        Train DBSCAN for density-based clustering
        
        Args:
            X: Scaled feature array
            eps: Maximum distance between samples
            min_samples: Minimum samples in neighborhood
            
        Returns:
            Trained DBSCAN model
        """
        model = DBSCAN(eps=eps, min_samples=min_samples)
        model.fit(X)
        
        self.models['dbscan'] = model
        self.cluster_labels = model.labels_
        
        return model
    
    def find_optimal_clusters(self, X: np.ndarray, max_k: int = 10) -> Dict[str, Any]:
        """
        Find optimal number of clusters using silhouette score
        
        Args:
            X: Scaled feature array
            max_k: Maximum clusters to try
            
        Returns:
            Dict with optimal k and scores
        """
        scores = {}
        
        for k in range(2, min(max_k + 1, len(X))):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)
            
            if len(set(labels)) > 1:  # Need at least 2 clusters for silhouette
                scores[k] = {
                    'silhouette': silhouette_score(X, labels),
                    'calinski_harabasz': calinski_harabasz_score(X, labels)
                }
        
        if not scores:
            return {'optimal_k': 2, 'scores': {}}
        
        optimal_k = max(scores.keys(), key=lambda k: scores[k]['silhouette'])
        
        return {
            'optimal_k': optimal_k,
            'scores': scores
        }
    
    def evaluate_clustering(self, X: np.ndarray, labels: np.ndarray = None) -> Dict[str, float]:
        """Evaluate clustering quality"""
        if labels is None:
            labels = self.cluster_labels
        
        if labels is None:
            return {}
        
        metrics = {}
        
        # Only calculate if we have multiple clusters
        unique_labels = set(labels)
        if len(unique_labels) > 1 and -1 not in unique_labels:
            metrics['silhouette_score'] = silhouette_score(X, labels)
            metrics['calinski_harabasz_score'] = calinski_harabasz_score(X, labels)
        
        metrics['n_clusters'] = len(unique_labels) - (1 if -1 in unique_labels else 0)
        metrics['n_noise'] = list(labels).count(-1)
        
        return metrics
    
    def predict_anomaly_scores(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get anomaly scores from Isolation Forest
        
        Returns:
            Tuple of (labels, scores) where:
            - labels: 1 for normal, -1 for anomaly
            - scores: Lower = more anomalous
        """
        if 'isolation_forest' not in self.models:
            raise ValueError("Isolation Forest not trained")
        
        model = self.models['isolation_forest']
        labels = model.predict(X)
        scores = model.score_samples(X)
        
        return labels, scores
    
    def assign_risk_from_clusters(self, cluster_labels: np.ndarray, X: np.ndarray) -> np.ndarray:
        """
        Assign risk categories based on cluster characteristics
        
        Logic: Clusters with higher mean risk features = higher risk
        """
        unique_clusters = np.unique(cluster_labels[cluster_labels >= 0])
        
        # Calculate mean feature values per cluster
        cluster_means = {}
        for c in unique_clusters:
            mask = cluster_labels == c
            cluster_means[c] = np.mean(X[mask])
        
        # Rank clusters by mean (higher = riskier)
        ranked = sorted(cluster_means.keys(), key=lambda c: cluster_means[c], reverse=True)
        
        # Map to risk categories
        risk_map = {}
        n_clusters = len(ranked)
        for i, c in enumerate(ranked):
            if i < n_clusters * 0.25:
                risk_map[c] = 'Critical'
            elif i < n_clusters * 0.5:
                risk_map[c] = 'High'
            elif i < n_clusters * 0.75:
                risk_map[c] = 'Medium'
            else:
                risk_map[c] = 'Low'
        
        # Handle noise points
        risk_map[-1] = 'Unknown'
        
        return np.array([risk_map.get(c, 'Unknown') for c in cluster_labels])
    
    def get_cluster_summary(self, df: pd.DataFrame, labels: np.ndarray = None) -> Dict[str, Any]:
        """Get summary statistics for each cluster"""
        if labels is None:
            labels = self.cluster_labels
        
        if labels is None:
            return {}
        
        df_with_labels = df.copy()
        df_with_labels['cluster'] = labels
        
        summary = {}
        for cluster in sorted(df_with_labels['cluster'].unique()):
            cluster_df = df_with_labels[df_with_labels['cluster'] == cluster]
            numeric_cols = cluster_df.select_dtypes(include=[np.number]).columns.tolist()
            
            summary[int(cluster)] = {
                'size': len(cluster_df),
                'percentage': len(cluster_df) / len(df) * 100,
                'mean_values': cluster_df[numeric_cols].mean().to_dict()
            }
        
        return summary
    
    def save_model(self, model_name: str, filename: str = None) -> str:
        """Save model to disk"""
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' not found")
        
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        if filename is None:
            filename = f"{model_name}_model.joblib"
        
        filepath = os.path.join(MODEL_DIR, filename)
        joblib.dump(self.models[model_name], filepath)
        
        return filepath


# Singleton instance
unsupervised_models = UnsupervisedModels()
