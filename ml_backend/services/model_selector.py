"""
Model Selector - Automatically chooses appropriate ML approach

Decision Logic:
- If labels available → Supervised (XGBoost preferred)
- If no labels → Unsupervised (Isolation Forest for anomaly, KMeans for clustering)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple

from models.supervised import supervised_models, SupervisedModels
from models.unsupervised import unsupervised_models, UnsupervisedModels


class ModelSelector:
    """Automatically selects and trains appropriate ML model"""
    
    def __init__(self):
        self.selected_approach = None
        self.selected_model_type = None
        self.reason = None
        self.trained_model = None
        
    def analyze_data(self, df: pd.DataFrame, target_col: str = None) -> Dict[str, Any]:
        """
        Analyze data to determine best approach
        
        Args:
            df: Input DataFrame
            target_col: Optional target column name
            
        Returns:
            Analysis results with recommendation
        """
        analysis = {
            'n_samples': len(df),
            'n_features': len(df.select_dtypes(include=[np.number]).columns),
            'has_target': False,
            'target_type': None,
            'target_classes': None,
            'recommended_approach': None,
            'recommended_models': [],
            'reason': None
        }
        
        # Check for target column
        if target_col and target_col in df.columns:
            analysis['has_target'] = True
            target = df[target_col]
            
            if target.dtype in ['object', 'category']:
                analysis['target_type'] = 'categorical'
                analysis['target_classes'] = target.nunique()
            else:
                # Check if numeric can be treated as categorical
                unique_vals = target.nunique()
                if unique_vals <= 10:
                    analysis['target_type'] = 'categorical'
                    analysis['target_classes'] = unique_vals
                else:
                    analysis['target_type'] = 'continuous'
        
        # Determine approach
        if analysis['has_target'] and analysis['target_type'] == 'categorical':
            analysis['recommended_approach'] = 'supervised'
            analysis['recommended_models'] = ['xgboost', 'random_forest', 'logistic_regression']
            analysis['reason'] = f"Labeled data available with {analysis['target_classes']} classes. Using supervised classification."
        elif analysis['has_target'] and analysis['target_type'] == 'continuous':
            analysis['recommended_approach'] = 'supervised'
            analysis['recommended_models'] = ['xgboost', 'random_forest']
            analysis['reason'] = "Continuous target available. Using supervised regression."
        else:
            analysis['recommended_approach'] = 'unsupervised'
            analysis['recommended_models'] = ['isolation_forest', 'kmeans', 'dbscan']
            analysis['reason'] = "No labels available. Using unsupervised anomaly detection and clustering."
        
        return analysis
    
    def select_and_train(
        self,
        df: pd.DataFrame,
        target_col: str = None,
        approach: str = 'auto',
        model_type: str = 'auto'
    ) -> Dict[str, Any]:
        """
        Select and train the best model
        
        Args:
            df: Input DataFrame with features
            target_col: Target column (optional for unsupervised)
            approach: 'supervised', 'unsupervised', or 'auto'
            model_type: Specific model or 'auto'
            
        Returns:
            Training results with model info
        """
        # Analyze data
        analysis = self.analyze_data(df, target_col)
        
        # Determine approach
        if approach == 'auto':
            approach = analysis['recommended_approach']
        
        self.selected_approach = approach
        
        results = {
            'approach': approach,
            'analysis': analysis,
            'training_results': None,
            'evaluation': None
        }
        
        if approach == 'supervised':
            results.update(self._train_supervised(df, target_col, model_type))
        else:
            results.update(self._train_unsupervised(df, model_type))
        
        return results
    
    def _train_supervised(
        self,
        df: pd.DataFrame,
        target_col: str,
        model_type: str = 'auto'
    ) -> Dict[str, Any]:
        """Train supervised model"""
        # Prepare data
        X_train, X_test, y_train, y_test = supervised_models.prepare_data(df, target_col)
        
        if model_type == 'auto':
            # Train all and select best
            comparison = supervised_models.train_all(X_train, y_train)
            self.selected_model_type = comparison['best_model']
            self.reason = f"Selected {comparison['best_model']} based on cross-validation (accuracy: {comparison['best_cv_score']:.3f})"
        else:
            # Train specific model
            if model_type == 'xgboost':
                supervised_models.train_xgboost(X_train, y_train)
            elif model_type == 'random_forest':
                supervised_models.train_random_forest(X_train, y_train)
            else:
                supervised_models.train_logistic_regression(X_train, y_train)
            
            supervised_models.trained_model = supervised_models.models[model_type]
            supervised_models.model_type = model_type
            self.selected_model_type = model_type
            comparison = None
        
        # Evaluate
        evaluation = supervised_models.evaluate(X_test, y_test)
        feature_importance = supervised_models.get_feature_importance()
        
        self.trained_model = supervised_models.trained_model
        
        return {
            'model_type': self.selected_model_type,
            'training_results': comparison,
            'evaluation': evaluation,
            'feature_importance': feature_importance,
            'reason': self.reason
        }
    
    def _train_unsupervised(
        self,
        df: pd.DataFrame,
        model_type: str = 'auto'
    ) -> Dict[str, Any]:
        """Train unsupervised model"""
        # Prepare data
        X_scaled = unsupervised_models.prepare_data(df)
        
        results = {}
        
        if model_type in ['auto', 'isolation_forest']:
            # Train Isolation Forest for anomaly detection
            unsupervised_models.train_isolation_forest(X_scaled)
            labels, scores = unsupervised_models.predict_anomaly_scores(X_scaled)
            
            results['isolation_forest'] = {
                'n_anomalies': int(np.sum(labels == -1)),
                'anomaly_percentage': float(np.mean(labels == -1) * 100),
                'mean_score': float(np.mean(scores))
            }
        
        if model_type in ['auto', 'kmeans']:
            # Find optimal clusters
            optimal = unsupervised_models.find_optimal_clusters(X_scaled)
            
            # Train KMeans with optimal k
            unsupervised_models.train_kmeans(X_scaled, optimal['optimal_k'])
            cluster_eval = unsupervised_models.evaluate_clustering(X_scaled)
            cluster_summary = unsupervised_models.get_cluster_summary(df)
            
            results['kmeans'] = {
                'optimal_k': optimal['optimal_k'],
                'cluster_evaluation': cluster_eval,
                'cluster_summary': cluster_summary
            }
        
        if model_type == 'dbscan':
            unsupervised_models.train_dbscan(X_scaled)
            cluster_eval = unsupervised_models.evaluate_clustering(X_scaled)
            
            results['dbscan'] = {
                'cluster_evaluation': cluster_eval
            }
        
        self.selected_model_type = 'isolation_forest' if 'isolation_forest' in results else 'kmeans'
        self.reason = "Using unsupervised learning: Isolation Forest for anomaly detection, KMeans for risk grouping."
        
        return {
            'model_type': self.selected_model_type,
            'training_results': results,
            'reason': self.reason
        }
    
    def predict_risk(
        self,
        df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict risk scores and categories
        
        Returns:
            Tuple of (risk_scores, risk_categories)
        """
        if self.selected_approach == 'supervised':
            feature_cols = supervised_models.feature_names
            X = df[feature_cols].values
            predictions, probabilities = supervised_models.predict(X)
            
            # Use max probability as risk score
            if probabilities is not None:
                risk_scores = np.max(probabilities, axis=1)
            else:
                risk_scores = np.zeros(len(predictions))
            
            return risk_scores, predictions
        
        else:  # Unsupervised
            X_scaled = unsupervised_models.prepare_data(df)
            
            # Get anomaly scores
            if 'isolation_forest' in unsupervised_models.models:
                _, anomaly_scores = unsupervised_models.predict_anomaly_scores(X_scaled)
                # Convert to 0-1 risk score (lower anomaly score = higher risk)
                risk_scores = 1 - (anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min() + 1e-10)
            else:
                risk_scores = np.zeros(len(df))
            
            # Get cluster-based categories
            if 'kmeans' in unsupervised_models.models:
                cluster_labels = unsupervised_models.models['kmeans'].predict(X_scaled)
                risk_categories = unsupervised_models.assign_risk_from_clusters(cluster_labels, X_scaled)
            else:
                risk_categories = np.array(['Unknown'] * len(df))
            
            return risk_scores, risk_categories
    
    def get_explanation(self) -> Dict[str, Any]:
        """Get explanation of model selection"""
        return {
            'approach': self.selected_approach,
            'model_type': self.selected_model_type,
            'reason': self.reason
        }


# Singleton instance
model_selector = ModelSelector()
