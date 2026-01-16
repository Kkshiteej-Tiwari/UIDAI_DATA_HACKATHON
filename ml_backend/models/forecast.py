"""
ARIMA-based Enrollment Forecasting Model

Uses statsmodels ARIMA to forecast Aadhaar enrollment demand at the district level.
Trained on historical data from data.gov.in APIs.
"""

import logging
import pickle
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller

import sys
sys.path.insert(0, '..')

from config import MODEL_DIR, DATASETS

logger = logging.getLogger(__name__)


class EnrollmentForecaster:
    """
    ARIMA-based time-series forecaster for district-level enrollment predictions.
    
    Uses aggregated enrollment data to train ARIMA models per district,
    then generates forecasts for future enrollment demand.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the forecaster.
        
        Args:
            model_path: Path to saved model file. If None, uses default location.
        """
        self.model_path = model_path or os.path.join(MODEL_DIR, "arima_enrollment_forecast.pkl")
        self.models: Dict[str, Any] = {}  # district -> fitted ARIMA model
        self.district_stats: Dict[str, Dict] = {}  # district -> stats (mean, std, last_date)
        self.is_trained = False
        
        # Ensure model directory exists
        os.makedirs(MODEL_DIR, exist_ok=True)
    
    def prepare_time_series(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Prepare time series data by district from enrollment records.
        
        Args:
            df: DataFrame with columns: date, state, district, age_0_5, age_5_17, age_18_greater
            
        Returns:
            Dictionary mapping district names to time series of total enrollments
        """
        if df.empty:
            logger.warning("Empty dataframe provided for time series preparation")
            return {}
        
        # Ensure date column is datetime
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Convert enrollment columns to numeric
        for col in ['age_0_5', 'age_5_17', 'age_18_greater']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Calculate total enrollments
        enrollment_cols = ['age_0_5', 'age_5_17', 'age_18_greater']
        available_cols = [c for c in enrollment_cols if c in df.columns]
        df['total_enrollment'] = df[available_cols].sum(axis=1)
        
        # Aggregate by district and date
        district_series = {}
        
        for district in df['district'].unique():
            if pd.isna(district) or str(district).strip() == '':
                continue
                
            district_df = df[df['district'] == district].copy()
            
            # Group by date and sum enrollments
            daily_enrollments = district_df.groupby('date')['total_enrollment'].sum()
            daily_enrollments = daily_enrollments.sort_index()
            
            # Need at least 10 data points for ARIMA
            if len(daily_enrollments) >= 10:
                district_series[str(district)] = daily_enrollments
                logger.debug(f"Prepared time series for {district}: {len(daily_enrollments)} points")
        
        logger.info(f"Prepared time series for {len(district_series)} districts")
        return district_series
    
    def _check_stationarity(self, series: pd.Series) -> Tuple[bool, int]:
        """
        Check if series is stationary using ADF test and determine differencing order.
        
        Returns:
            Tuple of (is_stationary, suggested_d)
        """
        try:
            result = adfuller(series.dropna(), autolag='AIC')
            p_value = result[1]
            
            if p_value < 0.05:
                return True, 0
            else:
                # Try first differencing
                diff_series = series.diff().dropna()
                if len(diff_series) > 5:
                    result_diff = adfuller(diff_series, autolag='AIC')
                    if result_diff[1] < 0.05:
                        return False, 1
                return False, 1
        except Exception as e:
            logger.warning(f"ADF test failed: {e}. Using d=1")
            return False, 1
    
    def train_arima(
        self,
        district_series: Dict[str, pd.Series],
        order: Tuple[int, int, int] = (1, 1, 1),
        max_districts: int = 50
    ) -> Dict[str, Any]:
        """
        Train ARIMA models for each district.
        
        Args:
            district_series: Dictionary of district -> enrollment time series
            order: ARIMA order (p, d, q). Default is (1, 1, 1)
            max_districts: Maximum number of districts to train (for performance)
            
        Returns:
            Training summary with success/failure counts
        """
        results = {
            "trained": [],
            "failed": [],
            "skipped": []
        }
        
        # Limit districts for performance
        districts_to_train = list(district_series.keys())[:max_districts]
        
        for district in districts_to_train:
            series = district_series[district]
            
            try:
                # Check stationarity and adjust d if needed
                _, suggested_d = self._check_stationarity(series)
                adjusted_order = (order[0], suggested_d, order[2])
                
                # Fit ARIMA model
                model = ARIMA(series, order=adjusted_order)
                fitted_model = model.fit()
                
                # Store model and stats
                self.models[district] = fitted_model
                self.district_stats[district] = {
                    "mean": float(series.mean()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "last_date": str(series.index[-1]),
                    "data_points": len(series),
                    "order": adjusted_order,
                    "aic": fitted_model.aic
                }
                
                results["trained"].append(district)
                logger.info(f"Trained ARIMA{adjusted_order} for {district}")
                
            except Exception as e:
                logger.warning(f"Failed to train ARIMA for {district}: {e}")
                results["failed"].append({"district": district, "error": str(e)})
        
        self.is_trained = len(self.models) > 0
        
        results["total_trained"] = len(results["trained"])
        results["total_failed"] = len(results["failed"])
        
        logger.info(f"Training complete: {results['total_trained']} successful, {results['total_failed']} failed")
        
        return results
    
    def forecast(
        self,
        district: str,
        periods: int = 6,
        confidence_level: float = 0.95
    ) -> Optional[Dict]:
        """
        Generate enrollment forecast for a district.
        
        Args:
            district: District name
            periods: Number of future periods to forecast
            confidence_level: Confidence level for prediction intervals
            
        Returns:
            Dictionary with forecast values and confidence intervals
        """
        if district not in self.models:
            logger.warning(f"No trained model for district: {district}")
            return None
        
        try:
            model = self.models[district]
            stats = self.district_stats[district]
            
            # Generate forecast
            forecast_result = model.get_forecast(steps=periods)
            predictions = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=1 - confidence_level)
            
            # Build forecast response
            forecast_data = {
                "district": district,
                "periods": periods,
                "confidence_level": confidence_level,
                "model_order": stats["order"],
                "historical_stats": {
                    "mean": stats["mean"],
                    "std": stats["std"],
                    "last_date": stats["last_date"],
                    "data_points": stats["data_points"]
                },
                "forecasts": []
            }
            
            for i, (pred, (lower, upper)) in enumerate(zip(predictions, conf_int.values)):
                forecast_data["forecasts"].append({
                    "period": i + 1,
                    "predicted_enrollment": round(max(0, pred), 0),  # Enrollment can't be negative
                    "lower_bound": round(max(0, lower), 0),
                    "upper_bound": round(max(0, upper), 0)
                })
            
            return forecast_data
            
        except Exception as e:
            logger.error(f"Forecast failed for {district}: {e}")
            return None
    
    def save_model(self, path: Optional[str] = None) -> str:
        """
        Save trained models to pickle file.
        
        Args:
            path: Optional custom path. Uses default if not specified.
            
        Returns:
            Path where model was saved
        """
        save_path = path or self.model_path
        
        model_data = {
            "models": self.models,
            "district_stats": self.district_stats,
            "trained_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {save_path}")
        return save_path
    
    def load_model(self, path: Optional[str] = None) -> bool:
        """
        Load trained models from pickle file.
        
        Args:
            path: Optional custom path. Uses default if not specified.
            
        Returns:
            True if loaded successfully, False otherwise
        """
        load_path = path or self.model_path
        
        if not os.path.exists(load_path):
            logger.warning(f"Model file not found: {load_path}")
            return False
        
        try:
            with open(load_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.models = model_data.get("models", {})
            self.district_stats = model_data.get("district_stats", {})
            self.is_trained = len(self.models) > 0
            
            logger.info(f"Loaded {len(self.models)} models from {load_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def get_available_districts(self) -> List[str]:
        """Get list of districts with trained models."""
        return list(self.models.keys())
    
    def get_model_info(self) -> Dict:
        """Get summary information about trained models."""
        if not self.is_trained:
            return {"status": "not_trained", "districts": 0}
        
        return {
            "status": "trained",
            "districts": len(self.models),
            "district_list": list(self.models.keys()),
            "model_path": self.model_path,
            "stats": self.district_stats,
            "model_version": getattr(self, 'model_version', "1.0.0")
        }
    
    # =========================================
    # State-Level Forecasting
    # =========================================
    
    INDIAN_STATES = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
        "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
        "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
        "Andaman and Nicobar", "Chandigarh", "Delhi", "Jammu and Kashmir", "Ladakh",
        "Lakshadweep", "Puducherry", "Dadra and Nagar Haveli"
    ]
    
    def prepare_state_series(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Aggregate district-level data to state-level time series.
        
        Args:
            df: DataFrame with columns: date, state, district, age_0_5, age_5_17, age_18_greater
            
        Returns:
            Dictionary mapping state names to time series of total enrollments
        """
        if df.empty:
            logger.warning("Empty dataframe provided for state time series")
            return {}
        
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Convert enrollment columns to numeric
        for col in ['age_0_5', 'age_5_17', 'age_18_greater']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        enrollment_cols = ['age_0_5', 'age_5_17', 'age_18_greater']
        available_cols = [c for c in enrollment_cols if c in df.columns]
        df['total_enrollment'] = df[available_cols].sum(axis=1)
        
        state_series = {}
        
        for state in df['state'].unique():
            if pd.isna(state) or str(state).strip() == '':
                continue
            
            state_df = df[df['state'] == state].copy()
            # Aggregate all districts by date
            daily_enrollments = state_df.groupby('date')['total_enrollment'].sum()
            daily_enrollments = daily_enrollments.sort_index()
            
            if len(daily_enrollments) >= 10:
                state_series[str(state)] = daily_enrollments
                logger.debug(f"Prepared state series for {state}: {len(daily_enrollments)} points")
        
        logger.info(f"Prepared time series for {len(state_series)} states")
        return state_series
    
    def train_state_models(
        self,
        state_series: Dict[str, pd.Series],
        order: Tuple[int, int, int] = (1, 1, 1)
    ) -> Dict[str, Any]:
        """
        Train ARIMA models for each state with versioning and metrics.
        
        Returns training summary with model version and backtest metrics.
        """
        version = f"2.0.0-state-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.model_version = version
        
        results = {
            "trained": [],
            "failed": [],
            "metrics": {}
        }
        
        all_mape = []
        all_mae = []
        all_rmse = []
        
        for state in state_series.keys():
            series = state_series[state]
            
            try:
                # Check stationarity
                _, suggested_d = self._check_stationarity(series)
                adjusted_order = (order[0], suggested_d, order[2])
                
                # Fit ARIMA
                model = ARIMA(series, order=adjusted_order)
                fitted_model = model.fit()
                
                # Compute in-sample metrics (backtest)
                fitted_values = fitted_model.fittedvalues
                actual = series.values
                n = min(len(fitted_values), len(actual))
                fitted_clean = np.array(fitted_values)[-n:]
                actual_clean = np.array(actual)[-n:]
                
                # Calculate metrics
                errors = actual_clean - fitted_clean
                mae = float(np.mean(np.abs(errors)))
                rmse = float(np.sqrt(np.mean(errors ** 2)))
                nonzero = actual_clean != 0
                if nonzero.sum() > 0:
                    mape = float(np.mean(np.abs(errors[nonzero] / actual_clean[nonzero])) * 100)
                else:
                    mape = None
                
                if mape is not None:
                    all_mape.append(mape)
                all_mae.append(mae)
                all_rmse.append(rmse)
                
                # Store with state prefix for distinction
                model_key = f"STATE:{state}"
                self.models[model_key] = fitted_model
                self.district_stats[model_key] = {
                    "mean": float(series.mean()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "last_date": str(series.index[-1]),
                    "data_points": len(series),
                    "order": adjusted_order,
                    "aic": fitted_model.aic,
                    "mape": mape,
                    "mae": mae,
                    "rmse": rmse
                }
                
                results["trained"].append(state)
                logger.info(f"Trained ARIMA{adjusted_order} for state {state} (MAPE: {mape:.1f}%)")
                
            except Exception as e:
                logger.warning(f"Failed to train ARIMA for state {state}: {e}")
                results["failed"].append({"state": state, "error": str(e)})
        
        self.is_trained = len(self.models) > 0
        
        # Aggregate metrics
        results["total_trained"] = len(results["trained"])
        results["total_failed"] = len(results["failed"])
        results["model_version"] = version
        results["metrics"] = {
            "avg_mape": round(np.mean(all_mape), 2) if all_mape else None,
            "avg_mae": round(np.mean(all_mae), 2) if all_mae else None,
            "avg_rmse": round(np.mean(all_rmse), 2) if all_rmse else None,
            "min_mape": round(min(all_mape), 2) if all_mape else None,
            "max_mape": round(max(all_mape), 2) if all_mape else None
        }
        
        logger.info(f"State training complete: {results['total_trained']} states, avg MAPE: {results['metrics']['avg_mape']}%")
        return results
    
    def forecast_all_states(
        self,
        periods: int = 6,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Generate forecasts for all trained states in a single response.
        
        Returns:
            Dictionary with model version, metrics, and all state forecasts
        """
        state_models = {k: v for k, v in self.models.items() if k.startswith("STATE:")}
        
        if not state_models:
            return {"error": "No state models trained", "states": []}
        
        response = {
            "model_version": getattr(self, 'model_version', "unknown"),
            "trained_at": datetime.now().isoformat(),
            "periods": periods,
            "confidence_level": confidence_level,
            "total_states": len(state_models),
            "states": []
        }
        
        for model_key in state_models:
            state_name = model_key.replace("STATE:", "")
            forecast = self._forecast_entity(model_key, periods, confidence_level)
            if forecast:
                forecast["state"] = state_name
                del forecast["district"]  # Remove district key if present
                response["states"].append(forecast)
        
        return response
    
    def _forecast_entity(
        self,
        entity_key: str,
        periods: int = 6,
        confidence_level: float = 0.95
    ) -> Optional[Dict]:
        """Internal method to forecast for any entity (district or state)."""
        if entity_key not in self.models:
            return None
        
        try:
            model = self.models[entity_key]
            stats = self.district_stats[entity_key]
            
            forecast_result = model.get_forecast(steps=periods)
            predictions = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=1 - confidence_level)
            
            forecast_data = {
                "district": entity_key.replace("STATE:", ""),
                "periods": periods,
                "confidence_level": confidence_level,
                "model_order": stats["order"],
                "historical_stats": {
                    "mean": stats["mean"],
                    "std": stats["std"],
                    "last_date": stats["last_date"],
                    "data_points": stats["data_points"]
                },
                "metrics": {
                    "mape": stats.get("mape"),
                    "mae": stats.get("mae"),
                    "rmse": stats.get("rmse")
                },
                "forecasts": []
            }
            
            for i, (pred, (lower, upper)) in enumerate(zip(predictions, conf_int.values)):
                forecast_data["forecasts"].append({
                    "period": i + 1,
                    "predicted_enrollment": round(max(0, pred), 0),
                    "lower_bound": round(max(0, lower), 0),
                    "upper_bound": round(max(0, upper), 0)
                })
            
            return forecast_data
            
        except Exception as e:
            logger.error(f"Forecast failed for {entity_key}: {e}")
            return None
    
    def get_available_states(self) -> List[str]:
        """Get list of states with trained models."""
        return [k.replace("STATE:", "") for k in self.models.keys() if k.startswith("STATE:")]


# Singleton instance
_forecaster_instance: Optional[EnrollmentForecaster] = None


def get_forecaster() -> EnrollmentForecaster:
    """Get or create EnrollmentForecaster singleton."""
    global _forecaster_instance
    if _forecaster_instance is None:
        _forecaster_instance = EnrollmentForecaster()
        # Try to load existing model
        _forecaster_instance.load_model()
    return _forecaster_instance
