"""
Gender Inclusion Tracker - ML Models
Training and prediction for high-risk district identification.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import joblib
from pathlib import Path
import uuid

from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    classification_report
)
from sklearn.preprocessing import StandardScaler

import lightgbm as lgb
import optuna
from imblearn.over_sampling import SMOTE
<<<<<<< HEAD
import structlog

from ..core.config import settings

logger = structlog.get_logger()
=======
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)
>>>>>>> origin/ridwan/gender-tracker-v2


@dataclass
class ModelMetrics:
    """Model evaluation metrics."""
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    confusion_matrix: List[List[int]]
    feature_importances: Dict[str, float]


@dataclass
class TrainedModel:
    """Container for a trained model and its metadata."""
    model_id: str
    model_type: str
    metrics: ModelMetrics
    features: List[str]
    threshold: float
    created_at: str
    hyperparameters: Dict[str, Any] = field(default_factory=dict)


class GenderRiskModel:
    """ML model for predicting high-risk districts for female exclusion."""
    
    FEATURE_COLUMNS = [
        'female_coverage_ratio',
        'female_to_male_ratio',
        'gender_gap',
        'total_enrolled',
        'age_0_5',
        'age_5_17',
        'age_18_plus',
    ]
    
    def __init__(self, model_type: str = 'lightgbm'):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.model_id: Optional[str] = None
        self.metrics: Optional[ModelMetrics] = None
    
    def _get_available_features(self, df: pd.DataFrame) -> List[str]:
        """Get list of available feature columns from dataframe."""
        available = []
        
        for col in self.FEATURE_COLUMNS:
            if col in df.columns:
                available.append(col)
        
        # Add any additional numeric columns that might be useful
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude = ['high_risk', 'target', 'label', 'id']
        
        for col in numeric_cols:
            if col not in available and col.lower() not in exclude:
                if not col.endswith('_missing'):  # Skip missing indicator cols
                    available.append(col)
        
        return available
    
    def _create_model(self, hyperparameters: Optional[Dict] = None) -> Any:
        """Create a model instance based on model_type."""
        params = hyperparameters or {}
        
        if self.model_type == 'lightgbm':
            default_params = {
                'objective': 'binary',
                'metric': 'auc',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'n_estimators': 100,
                'class_weight': 'balanced',
                'random_state': settings.random_seed
            }
            default_params.update(params)
            return lgb.LGBMClassifier(**default_params)
        
        elif self.model_type == 'logistic':
            default_params = {
                'C': 1.0,
                'class_weight': 'balanced',
                'max_iter': 1000,
                'random_state': settings.random_seed
            }
            default_params.update(params)
            return LogisticRegression(**default_params)
        
        elif self.model_type == 'randomforest':
            default_params = {
                'n_estimators': 100,
                'max_depth': 10,
                'class_weight': 'balanced',
                'random_state': settings.random_seed
            }
            default_params.update(params)
            return RandomForestClassifier(**default_params)
        
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
    
    def _tune_hyperparameters(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_trials: int = 50
    ) -> Dict[str, Any]:
        """Use Optuna to tune hyperparameters."""
        
        def objective(trial):
            if self.model_type == 'lightgbm':
                params = {
                    'num_leaves': trial.suggest_int('num_leaves', 10, 100),
                    'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 12),
                    'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
                }
            elif self.model_type == 'logistic':
                params = {
                    'C': trial.suggest_float('C', 0.01, 10.0, log=True),
                }
            else:
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 15),
                }
            
            model = self._create_model(params)
            
            # Cross-validation
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=settings.random_seed)
            scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
            
            return scores.mean()
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        
        return study.best_params
    
    def train(
        self,
        df: pd.DataFrame,
        target_column: str = 'high_risk',
        tune: bool = True,
        use_smote: bool = True,
        test_size: float = 0.2
    ) -> TrainedModel:
        """
        Train the model on the provided dataset.
        
        Args:
            df: Preprocessed DataFrame
            target_column: Name of the target column
            tune: Whether to tune hyperparameters
            use_smote: Whether to use SMOTE for class imbalance
            test_size: Fraction of data for testing
        
        Returns:
            TrainedModel with metrics and model info
        """
        # Get available features
        self.feature_names = self._get_available_features(df)
        
        if not self.feature_names:
            raise ValueError("No valid feature columns found in the dataset")
        
        # Exclude target from features
        self.feature_names = [f for f in self.feature_names if f != target_column]
        
        logger.info("Training model", 
                   model_type=self.model_type,
                   features=self.feature_names,
                   n_samples=len(df))
        
        # Prepare features and target
        X = df[self.feature_names].values
        y = df[target_column].values
        
        # Handle any remaining NaN
        X = np.nan_to_num(X, nan=0.0)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, stratify=y, random_state=settings.random_seed
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Handle class imbalance with SMOTE
        if use_smote and len(np.unique(y_train)) > 1:
            try:
                smote = SMOTE(random_state=settings.random_seed)
                X_train_scaled, y_train = smote.fit_resample(X_train_scaled, y_train)
                logger.info("Applied SMOTE", new_samples=len(y_train))
            except Exception as e:
                logger.warning("SMOTE failed, using original data", error=str(e))
        
        # Tune hyperparameters
        hyperparameters = {}
        if tune:
            logger.info("Tuning hyperparameters...")
            hyperparameters = self._tune_hyperparameters(X_train_scaled, y_train, n_trials=30)
            logger.info("Best hyperparameters", params=hyperparameters)
        
        # Train final model
        self.model = self._create_model(hyperparameters)
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        y_prob = self.model.predict_proba(X_test_scaled)[:, 1]
        
        # Calculate metrics
        self.metrics = ModelMetrics(
            accuracy=float(accuracy_score(y_test, y_pred)),
            precision=float(precision_score(y_test, y_pred, zero_division=0)),
            recall=float(recall_score(y_test, y_pred, zero_division=0)),
            f1=float(f1_score(y_test, y_pred, zero_division=0)),
            roc_auc=float(roc_auc_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else 0.0,
            pr_auc=float(average_precision_score(y_test, y_prob)) if len(np.unique(y_test)) > 1 else 0.0,
            confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
            feature_importances=self._get_feature_importances()
        )
        
        # Generate model ID
        self.model_id = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.model_type}"
        
        return TrainedModel(
            model_id=self.model_id,
            model_type=self.model_type,
            metrics=self.metrics,
            features=self.feature_names,
            threshold=settings.default_risk_threshold,
            created_at=datetime.now().isoformat(),
            hyperparameters=hyperparameters
        )
    
    def _get_feature_importances(self) -> Dict[str, float]:
        """Get feature importance from the trained model."""
        if self.model is None:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_[0])
        else:
            return {}
        
        return {
            name: float(imp) 
            for name, imp in zip(self.feature_names, importances)
        }
    
    def predict(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Make predictions on new data.
        
        Args:
            df: DataFrame with feature columns
        
        Returns:
            DataFrame with predictions added
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        df = df.copy()
        
        # Ensure all required features are present
        available_features = [f for f in self.feature_names if f in df.columns]
        missing_features = set(self.feature_names) - set(available_features)
        
        if missing_features:
            logger.warning("Missing features, using zeros", missing=list(missing_features))
            for f in missing_features:
                df[f] = 0
        
        # Prepare features
        X = df[self.feature_names].values
        X = np.nan_to_num(X, nan=0.0)
        X_scaled = self.scaler.transform(X)
        
        # Predict
        df['risk_probability'] = self.model.predict_proba(X_scaled)[:, 1]
        df['predicted_high_risk'] = self.model.predict(X_scaled)
        
        return df
    
    def save(self, path: Optional[Path] = None) -> Path:
        """Save the model to disk."""
        if self.model is None:
            raise ValueError("No model to save")
        
        if path is None:
            path = settings.models_dir / f"{self.model_id}.pkl"
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'model_type': self.model_type,
            'model_id': self.model_id,
            'metrics': asdict(self.metrics) if self.metrics else None
        }
        
        joblib.dump(model_data, path)
        logger.info("Model saved", path=str(path))
        
        return path
    
    @classmethod
    def load(cls, path: Path) -> 'GenderRiskModel':
        """Load a model from disk."""
        model_data = joblib.load(path)
        
        instance = cls(model_type=model_data['model_type'])
        instance.model = model_data['model']
        instance.scaler = model_data['scaler']
        instance.feature_names = model_data['feature_names']
        instance.model_id = model_data['model_id']
        
        if model_data['metrics']:
            instance.metrics = ModelMetrics(**model_data['metrics'])
        
        return instance
