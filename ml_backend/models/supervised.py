"""
Supervised ML Models for Biometric Risk Prediction

Models:
- Logistic Regression (baseline)
- Random Forest
- XGBoost (primary)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, roc_auc_score
)
import xgboost as xgb
import joblib
import os

from config import MODEL_CONFIG, MODEL_DIR


class SupervisedModels:
    """Supervised ML models for risk classification"""
    
    def __init__(self):
        self.models = {}
        self.trained_model = None
        self.model_type = None
        self.feature_names = []
        self.metrics = {}
        
    def prepare_data(
        self,
        df: pd.DataFrame,
        target_col: str = 'risk_category',
        feature_cols: Optional[List[str]] = None,
        test_size: float = 0.2
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare data for training
        
        Args:
            df: DataFrame with features and target
            target_col: Name of target column
            feature_cols: List of feature columns (auto-detect if None)
            test_size: Test set proportion
            
        Returns:
            X_train, X_test, y_train, y_test
        """
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found")
        
        # Auto-detect feature columns
        if feature_cols is None:
            exclude_cols = [target_col, 'state', 'district', 'proxy_risk_score']
            feature_cols = [c for c in df.columns if c not in exclude_cols and df[c].dtype in ['int64', 'float64']]
        
        self.feature_names = feature_cols
        
        X = df[feature_cols].values
        y = df[target_col].values
        
        # Encode labels if categorical
        if y.dtype == 'object' or str(y.dtype) == 'category':
            from sklearn.preprocessing import LabelEncoder
            le = LabelEncoder()
            y = le.fit_transform(y)
        
        return train_test_split(X, y, test_size=test_size, random_state=42, stratify=y)
    
    def train_logistic_regression(self, X_train: np.ndarray, y_train: np.ndarray) -> LogisticRegression:
        """Train Logistic Regression model"""
        model = LogisticRegression(max_iter=1000, random_state=42)
        model.fit(X_train, y_train)
        self.models['logistic_regression'] = model
        return model
    
    def train_random_forest(self, X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
        """Train Random Forest model"""
        config = MODEL_CONFIG['random_forest']
        model = RandomForestClassifier(**config)
        model.fit(X_train, y_train)
        self.models['random_forest'] = model
        return model
    
    def train_xgboost(self, X_train: np.ndarray, y_train: np.ndarray) -> xgb.XGBClassifier:
        """Train XGBoost model (primary)"""
        config = MODEL_CONFIG['xgboost']
        model = xgb.XGBClassifier(**config, use_label_encoder=False, eval_metric='mlogloss')
        model.fit(X_train, y_train)
        self.models['xgboost'] = model
        return model
    
    def train_all(self, X_train: np.ndarray, y_train: np.ndarray) -> Dict[str, Any]:
        """Train all supervised models and compare"""
        results = {}
        
        # Train each model
        lr = self.train_logistic_regression(X_train, y_train)
        rf = self.train_random_forest(X_train, y_train)
        xgb_model = self.train_xgboost(X_train, y_train)
        
        # Cross-validation scores
        for name, model in [('logistic_regression', lr), ('random_forest', rf), ('xgboost', xgb_model)]:
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
            results[name] = {
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
        
        # Select best model
        best_model_name = max(results.keys(), key=lambda k: results[k]['cv_mean'])
        self.trained_model = self.models[best_model_name]
        self.model_type = best_model_name
        
        return {
            'comparison': results,
            'best_model': best_model_name,
            'best_cv_score': results[best_model_name]['cv_mean']
        }
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """Evaluate trained model on test set"""
        if self.trained_model is None:
            raise ValueError("No model trained yet")
        
        y_pred = self.trained_model.predict(X_test)
        y_prob = None
        
        if hasattr(self.trained_model, 'predict_proba'):
            y_prob = self.trained_model.predict_proba(X_test)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_test, y_pred, average='weighted', zero_division=0),
            'f1': f1_score(y_test, y_pred, average='weighted', zero_division=0),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }
        
        # ROC AUC for binary classification
        if len(np.unique(y_test)) == 2 and y_prob is not None:
            metrics['roc_auc'] = roc_auc_score(y_test, y_prob[:, 1])
        
        self.metrics = metrics
        return metrics
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Make predictions with trained model"""
        if self.trained_model is None:
            raise ValueError("No model trained yet")
        
        predictions = self.trained_model.predict(X)
        probabilities = None
        
        if hasattr(self.trained_model, 'predict_proba'):
            probabilities = self.trained_model.predict_proba(X)
        
        return predictions, probabilities
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model"""
        if self.trained_model is None:
            return {}
        
        importance = {}
        
        if hasattr(self.trained_model, 'feature_importances_'):
            for name, imp in zip(self.feature_names, self.trained_model.feature_importances_):
                importance[name] = float(imp)
        elif hasattr(self.trained_model, 'coef_'):
            for name, coef in zip(self.feature_names, np.abs(self.trained_model.coef_).mean(axis=0)):
                importance[name] = float(coef)
        
        # Sort by importance
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def save_model(self, filename: str = None) -> str:
        """Save trained model to disk"""
        if self.trained_model is None:
            raise ValueError("No model to save")
        
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        if filename is None:
            filename = f"{self.model_type}_model.joblib"
        
        filepath = os.path.join(MODEL_DIR, filename)
        joblib.dump(self.trained_model, filepath)
        
        return filepath
    
    def load_model(self, filepath: str):
        """Load model from disk"""
        self.trained_model = joblib.load(filepath)
        return self.trained_model


# Singleton instance
supervised_models = SupervisedModels()
