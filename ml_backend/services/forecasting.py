"""
Forecasting Service
Implements time-series forecasting for Aadhaar enrollment projections:
- SARIMA model training with automatic parameter selection
- 6-month forecasting with confidence intervals
- Scenario modeling for policy interventions
- Spatial lag regression
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def train_sarima_model(
    ts: pd.Series,
    auto: bool = True,
    order: Tuple[int, int, int] = (1, 1, 1),
    seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 12)
) -> Dict:
    """
    Train a SARIMA model for time series forecasting.
    
    Args:
        ts: Time series data (pandas Series with datetime index or values)
        auto: If True, automatically select best parameters using AIC
        order: (p, d, q) - AR, differencing, MA orders
        seasonal_order: (P, D, Q, s) - seasonal orders and period
        
    Returns:
        Dict containing:
        - model: Fitted model object
        - order: Final (p, d, q) used
        - seasonal_order: Final (P, D, Q, s) used
        - aic: Akaike Information Criterion
        - bic: Bayesian Information Criterion
        - residuals: Model residuals
        - diagnostics: Model diagnostics
        
    Example:
        >>> ts = pd.Series(enrollment_data, index=pd.date_range('2020-01', periods=24, freq='M'))
        >>> model_result = train_sarima_model(ts, auto=True)
        >>> print(f"AIC: {model_result['aic']:.2f}")
    """
    values = ts.values if hasattr(ts, 'values') else np.array(ts)
    n = len(values)
    
    if n < 12:
        # Not enough data for SARIMA, use simple model
        return _train_simple_model(values)
    
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        
        if auto:
            # Try a few parameter combinations and select best AIC
            best_aic = np.inf
            best_model = None
            best_order = order
            best_seasonal = seasonal_order
            
            # Parameter search space (limited for speed)
            p_values = [0, 1, 2]
            d_values = [0, 1]
            q_values = [0, 1, 2]
            
            for p in p_values:
                for d in d_values:
                    for q in q_values:
                        try:
                            model = SARIMAX(
                                values,
                                order=(p, d, q),
                                seasonal_order=(1, 1, 1, 12) if n >= 24 else (0, 0, 0, 0),
                                enforce_stationarity=False,
                                enforce_invertibility=False
                            )
                            fitted = model.fit(disp=False, maxiter=100)
                            
                            if fitted.aic < best_aic:
                                best_aic = fitted.aic
                                best_model = fitted
                                best_order = (p, d, q)
                                best_seasonal = seasonal_order if n >= 24 else (0, 0, 0, 0)
                        except Exception:
                            continue
            
            if best_model is None:
                # Fallback to simple model
                return _train_simple_model(values)
            
            return {
                "model": best_model,
                "order": best_order,
                "seasonal_order": best_seasonal,
                "aic": float(best_model.aic),
                "bic": float(best_model.bic),
                "residuals": best_model.resid.tolist(),
                "diagnostics": {
                    "ljung_box_pvalue": float(_ljung_box_test(best_model.resid)),
                    "normality_pvalue": float(stats.normaltest(best_model.resid)[1]) if len(best_model.resid) >= 20 else 1.0,
                    "mape": float(_calculate_mape(values, best_model.fittedvalues))
                }
            }
        else:
            # Use specified parameters
            model = SARIMAX(
                values,
                order=order,
                seasonal_order=seasonal_order if n >= 24 else (0, 0, 0, 0),
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            fitted = model.fit(disp=False)
            
            return {
                "model": fitted,
                "order": order,
                "seasonal_order": seasonal_order,
                "aic": float(fitted.aic),
                "bic": float(fitted.bic),
                "residuals": fitted.resid.tolist(),
                "diagnostics": {
                    "ljung_box_pvalue": float(_ljung_box_test(fitted.resid)),
                    "normality_pvalue": float(stats.normaltest(fitted.resid)[1]) if len(fitted.resid) >= 20 else 1.0,
                    "mape": float(_calculate_mape(values, fitted.fittedvalues))
                }
            }
            
    except ImportError:
        logger.warning("statsmodels not available, using simple exponential smoothing")
        return _train_simple_model(values)
    except Exception as e:
        logger.warning(f"SARIMA training failed: {e}, using simple model")
        return _train_simple_model(values)


def _train_simple_model(values: np.ndarray) -> Dict:
    """Fallback simple exponential smoothing model."""
    n = len(values)
    alpha = 0.3  # Smoothing parameter
    
    # Simple exponential smoothing
    smoothed = np.zeros(n)
    smoothed[0] = values[0]
    for i in range(1, n):
        smoothed[i] = alpha * values[i] + (1 - alpha) * smoothed[i-1]
    
    residuals = values - smoothed
    
    return {
        "model": {"type": "simple_exponential", "alpha": alpha, "last_value": smoothed[-1], "values": values},
        "order": (0, 0, 0),
        "seasonal_order": (0, 0, 0, 0),
        "aic": float(n * np.log(np.var(residuals)) + 2),  # Approximate AIC
        "bic": float(n * np.log(np.var(residuals)) + np.log(n)),
        "residuals": residuals.tolist(),
        "diagnostics": {
            "ljung_box_pvalue": 1.0,
            "normality_pvalue": 1.0,
            "mape": float(_calculate_mape(values, smoothed))
        }
    }


def forecast_6_months(
    model_result: Dict,
    horizon_months: int = 6,
    confidence_level: float = 0.95
) -> Dict:
    """
    Generate forecasts for specified horizon with confidence intervals.
    
    Args:
        model_result: Result from train_sarima_model()
        horizon_months: Number of months to forecast
        confidence_level: Confidence level for intervals (default 0.95)
        
    Returns:
        Dict containing:
        - forecast: List of point forecasts
        - lower_ci: Lower confidence interval bounds
        - upper_ci: Upper confidence interval bounds
        - dates: Forecast dates
        - confidence_level: Confidence level used
        
    Example:
        >>> model = train_sarima_model(ts)
        >>> forecast = forecast_6_months(model, horizon_months=6)
        >>> for i, (date, value) in enumerate(zip(forecast['dates'], forecast['forecast'])):
        ...     print(f"{date}: {value:.0f} [{forecast['lower_ci'][i]:.0f}, {forecast['upper_ci'][i]:.0f}]")
    """
    model = model_result.get("model")
    
    if model is None:
        return _empty_forecast(horizon_months)
    
    # Generate forecast dates
    today = datetime.now()
    start_date = datetime(today.year, today.month, 1) + timedelta(days=32)
    start_date = datetime(start_date.year, start_date.month, 1)
    
    dates = []
    for i in range(horizon_months):
        forecast_date = start_date + timedelta(days=i * 30)
        dates.append(forecast_date.strftime("%Y-%m"))
    
    try:
        if isinstance(model, dict) and model.get("type") == "simple_exponential":
            # Simple model forecast
            return _simple_forecast(model, horizon_months, dates, confidence_level)
        else:
            # SARIMA model forecast
            forecast_result = model.get_forecast(steps=horizon_months)
            forecast_values = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=1 - confidence_level)
            
            return {
                "forecast": forecast_values.tolist(),
                "lower_ci": conf_int.iloc[:, 0].tolist(),
                "upper_ci": conf_int.iloc[:, 1].tolist(),
                "dates": dates,
                "confidence_level": confidence_level,
                "method": "SARIMA"
            }
    except Exception as e:
        logger.warning(f"Forecast generation failed: {e}")
        return _empty_forecast(horizon_months, dates)


def _simple_forecast(
    model: Dict,
    horizon: int,
    dates: List[str],
    confidence_level: float
) -> Dict:
    """Generate forecast from simple exponential smoothing model."""
    last_value = model.get("last_value", 0)
    values = model.get("values", [])
    
    # Simple forecast: last smoothed value with trend
    if len(values) >= 2:
        trend = (values[-1] - values[0]) / max(1, len(values) - 1)
    else:
        trend = 0
    
    forecast = []
    for i in range(horizon):
        forecast.append(last_value + trend * (i + 1))
    
    # Simple confidence intervals based on historical volatility
    if len(values) > 1:
        volatility = np.std(values)
    else:
        volatility = abs(last_value) * 0.1
    
    z_score = stats.norm.ppf((1 + confidence_level) / 2)
    
    lower_ci = [f - z_score * volatility * np.sqrt(i + 1) for i, f in enumerate(forecast)]
    upper_ci = [f + z_score * volatility * np.sqrt(i + 1) for i, f in enumerate(forecast)]
    
    return {
        "forecast": forecast,
        "lower_ci": lower_ci,
        "upper_ci": upper_ci,
        "dates": dates,
        "confidence_level": confidence_level,
        "method": "simple_exponential"
    }


def _empty_forecast(horizon: int, dates: Optional[List[str]] = None) -> Dict:
    """Return empty forecast structure."""
    if dates is None:
        today = datetime.now()
        dates = [(today + timedelta(days=30 * i)).strftime("%Y-%m") for i in range(1, horizon + 1)]
    
    return {
        "forecast": [0.0] * horizon,
        "lower_ci": [0.0] * horizon,
        "upper_ci": [0.0] * horizon,
        "dates": dates,
        "confidence_level": 0.95,
        "method": "none"
    }


def scenario_modeling(
    state: str,
    historical_data: pd.DataFrame,
    intervention_params: Dict,
    horizon_months: int = 6
) -> Dict:
    """
    Compare baseline forecast vs intervention scenario.
    
    Args:
        state: State name for analysis
        historical_data: DataFrame with historical enrollment data
        intervention_params: Dict specifying intervention:
            - boost_percent: Percentage increase in enrollment velocity
            - start_month: When intervention starts (0-based)
            - duration_months: How long intervention lasts
        horizon_months: Forecast horizon
        
    Returns:
        Dict containing:
        - baseline: Baseline forecast without intervention
        - intervention: Forecast with intervention
        - difference: Difference between scenarios
        - cumulative_impact: Total additional enrollments
        - dates: Forecast dates
        
    Example:
        >>> params = {"boost_percent": 10, "start_month": 0, "duration_months": 3}
        >>> result = scenario_modeling("Bihar", data, params)
        >>> print(f"Cumulative impact: {result['cumulative_impact']:,.0f} additional enrollments")
    """
    # Default intervention parameters
    boost_percent = intervention_params.get("boost_percent", 10)
    start_month = intervention_params.get("start_month", 0)
    duration_months = intervention_params.get("duration_months", 3)
    
    # Extract time series for state
    if 'state' in historical_data.columns:
        state_data = historical_data[historical_data['state'].str.lower() == state.lower()]
    else:
        state_data = historical_data
    
    if len(state_data) < 6:
        return _empty_scenario(state, horizon_months)
    
    # Get value column
    value_col = None
    for col in ['total_enrollments', 'enrollments', 'value', 'count']:
        if col in state_data.columns:
            value_col = col
            break
    
    if value_col is None:
        value_col = state_data.select_dtypes(include=[np.number]).columns[0]
    
    values = state_data[value_col].values.astype(float)
    
    # Train baseline model
    model_result = train_sarima_model(pd.Series(values), auto=True)
    
    # Generate baseline forecast
    baseline = forecast_6_months(model_result, horizon_months)
    
    # Apply intervention boost
    intervention_forecast = baseline['forecast'].copy()
    for i in range(horizon_months):
        if start_month <= i < start_month + duration_months:
            boost = 1 + (boost_percent / 100)
            intervention_forecast[i] = baseline['forecast'][i] * boost
    
    # Calculate difference
    difference = [
        intervention_forecast[i] - baseline['forecast'][i]
        for i in range(horizon_months)
    ]
    
    cumulative_impact = sum(difference)
    
    return {
        "state": state,
        "baseline": {
            "forecast": baseline['forecast'],
            "lower_ci": baseline['lower_ci'],
            "upper_ci": baseline['upper_ci']
        },
        "intervention": {
            "forecast": intervention_forecast,
            "boost_percent": boost_percent,
            "start_month": start_month,
            "duration_months": duration_months
        },
        "difference": difference,
        "cumulative_impact": float(cumulative_impact),
        "dates": baseline['dates'],
        "summary": {
            "baseline_total": float(sum(baseline['forecast'])),
            "intervention_total": float(sum(intervention_forecast)),
            "percent_increase": float(cumulative_impact / max(1, sum(baseline['forecast'])) * 100)
        }
    }


def _empty_scenario(state: str, horizon: int) -> Dict:
    """Return empty scenario structure."""
    dates = [(datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m") for i in range(1, horizon + 1)]
    
    return {
        "state": state,
        "baseline": {
            "forecast": [0.0] * horizon,
            "lower_ci": [0.0] * horizon,
            "upper_ci": [0.0] * horizon
        },
        "intervention": {
            "forecast": [0.0] * horizon,
            "boost_percent": 0,
            "start_month": 0,
            "duration_months": 0
        },
        "difference": [0.0] * horizon,
        "cumulative_impact": 0.0,
        "dates": dates,
        "summary": {
            "baseline_total": 0.0,
            "intervention_total": 0.0,
            "percent_increase": 0.0
        }
    }


def spatial_lag_regression(
    gdf,
    target_column: str = "penetration_rate",
    feature_columns: Optional[List[str]] = None,
    weights_matrix: Optional[np.ndarray] = None
) -> Dict:
    """
    Perform spatial lag regression to model spatial dependencies.
    
    Model: Y = ρWY + Xβ + ε
    Where W is the spatial weights matrix
    
    Args:
        gdf: GeoDataFrame with data
        target_column: Column to predict
        feature_columns: List of feature columns
        weights_matrix: Spatial weights matrix
        
    Returns:
        Dict containing:
        - coefficients: Regression coefficients
        - rho: Spatial autocorrelation parameter
        - predictions: Model predictions
        - r_squared: Model fit
        - diagnostics: Model diagnostics
    """
    import geopandas as gpd
    
    if target_column not in gdf.columns:
        return {"error": f"Column '{target_column}' not found"}
    
    y = gdf[target_column].values.astype(float)
    n = len(y)
    
    # Generate weights matrix if not provided
    if weights_matrix is None:
        from services.spatial_analysis import _generate_simple_weights
        weights_matrix = _generate_simple_weights(gdf)
    
    # Simple OLS with spatial lag
    # Calculate spatial lag of Y
    wy = weights_matrix @ y
    
    # Features
    if feature_columns:
        available_features = [f for f in feature_columns if f in gdf.columns]
        if available_features:
            X = gdf[available_features].values.astype(float)
        else:
            X = np.ones((n, 1))
    else:
        X = np.ones((n, 1))
    
    # Add spatial lag as feature
    X_with_lag = np.column_stack([X, wy])
    
    try:
        # OLS estimation
        beta, residuals, rank, s = np.linalg.lstsq(X_with_lag, y, rcond=None)
        
        predictions = X_with_lag @ beta
        
        # R-squared
        ss_res = np.sum((y - predictions) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Rho is the last coefficient (spatial lag parameter)
        rho = beta[-1]
        
        return {
            "coefficients": beta[:-1].tolist(),
            "rho": float(rho),
            "predictions": predictions.tolist(),
            "r_squared": float(r_squared),
            "n": n,
            "diagnostics": {
                "rmse": float(np.sqrt(np.mean((y - predictions) ** 2))),
                "mae": float(np.mean(np.abs(y - predictions)))
            }
        }
    except Exception as e:
        logger.warning(f"Spatial regression failed: {e}")
        return {
            "error": str(e),
            "coefficients": [],
            "rho": 0.0,
            "predictions": [],
            "r_squared": 0.0
        }


def _ljung_box_test(residuals: np.ndarray, lags: int = 10) -> float:
    """Perform Ljung-Box test for autocorrelation in residuals."""
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox
        result = acorr_ljungbox(residuals, lags=[lags], return_df=True)
        return float(result['lb_pvalue'].iloc[0])
    except Exception:
        return 1.0  # Cannot reject null hypothesis


def _calculate_mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Calculate Mean Absolute Percentage Error."""
    mask = actual != 0
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def batch_forecast_states(
    historical_data: pd.DataFrame,
    states: Optional[List[str]] = None,
    horizon_months: int = 6
) -> Dict[str, Dict]:
    """
    Generate forecasts for multiple states.
    
    Args:
        historical_data: DataFrame with columns ['state', 'date', 'value']
        states: Optional list of states to forecast (all if None)
        horizon_months: Forecast horizon
        
    Returns:
        Dict mapping state names to forecast results
    """
    if 'state' not in historical_data.columns:
        return {"error": "No 'state' column in data"}
    
    if states is None:
        states = historical_data['state'].unique().tolist()
    
    results = {}
    
    for state in states:
        state_data = historical_data[historical_data['state'] == state]
        
        if len(state_data) < 6:
            results[state] = _empty_forecast(horizon_months)
            continue
        
        # Get value column
        value_col = None
        for col in ['total_enrollments', 'enrollments', 'value', 'count']:
            if col in state_data.columns:
                value_col = col
                break
        
        if value_col is None:
            numeric_cols = state_data.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                value_col = numeric_cols[0]
            else:
                results[state] = _empty_forecast(horizon_months)
                continue
        
        values = state_data[value_col].values.astype(float)
        
        try:
            model = train_sarima_model(pd.Series(values), auto=True)
            results[state] = forecast_6_months(model, horizon_months)
        except Exception as e:
            logger.warning(f"Forecast failed for {state}: {e}")
            results[state] = _empty_forecast(horizon_months)
    
    return results
