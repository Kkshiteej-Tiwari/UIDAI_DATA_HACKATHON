"""
ARIMA Forecast Diagnostics and Visualization Module

Comprehensive diagnostics, metrics, and visualizations for ARIMA enrollment forecasting.
Generates interactive Plotly charts, HTML dashboards, and CSV exports.
"""

import os
import pickle
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from scipy import stats as scipy_stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.graphics.gofplots import qqplot

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)


class ARIMADiagnostics:
    """
    Comprehensive diagnostics and visualization for ARIMA enrollment forecasts.
    
    Provides:
    - Model loading from pickle
    - Diagnostic tests (ADF, Ljung-Box)
    - Accuracy metrics (RMSE, MAE, MAPE, CI coverage)
    - Interactive Plotly visualizations
    - HTML dashboard generation
    - CSV exports
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize diagnostics module.
        
        Args:
            model_path: Path to saved ARIMA models pickle file
        """
        self.model_path = model_path or os.path.join(MODEL_DIR, "arima_enrollment_forecast.pkl")
        self.models: Dict[str, Any] = {}
        self.district_stats: Dict[str, Dict] = {}
        self.output_dir = os.path.join(OUTPUT_DIR, "diagnostics")
        
        # Ensure output directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "plots"), exist_ok=True)
    
    def load_models(self) -> bool:
        """
        Load trained ARIMA models from pickle file.
        
        Returns:
            True if loaded successfully
        """
        if not os.path.exists(self.model_path):
            logger.error(f"Model file not found: {self.model_path}")
            return False
        
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.models = model_data.get("models", {})
            self.district_stats = model_data.get("district_stats", {})
            
            logger.info(f"Loaded {len(self.models)} models from {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return False
    
    def get_districts(self) -> List[str]:
        """Get list of available districts."""
        return list(self.models.keys())
    
    def compute_diagnostics(self, district: str) -> Optional[Dict]:
        """
        Compute diagnostic tests for a district's model.
        
        Args:
            district: District name
            
        Returns:
            Dictionary with diagnostic results
        """
        if district not in self.models:
            return None
        
        model = self.models[district]
        district_stat = self.district_stats.get(district, {})
        
        try:
            # Get residuals
            residuals = model.resid
            
            # ADF Test on residuals (should be stationary)
            adf_result = adfuller(residuals.dropna(), autolag='AIC')
            
            # Ljung-Box test for autocorrelation
            lb_result = acorr_ljungbox(residuals.dropna(), lags=[10], return_df=True)
            lb_pvalue = lb_result['lb_pvalue'].values[0]
            
            # Normality test (Shapiro-Wilk)
            resid_clean = residuals.dropna()
            if len(resid_clean) <= 5000 and len(resid_clean) > 3:
                shapiro_stat, shapiro_pvalue = scipy_stats.shapiro(resid_clean)
            else:
                shapiro_stat, shapiro_pvalue = None, None
            
            # Basic residual statistics
            resid_mean = float(residuals.mean())
            resid_std = float(residuals.std())
            resid_skew = float(residuals.skew()) if hasattr(residuals, 'skew') else None
            resid_kurt = float(residuals.kurtosis()) if hasattr(residuals, 'kurtosis') else None
            
            # Extract AR and MA coefficients
            ar_coeffs = []
            ma_coeffs = []
            try:
                if hasattr(model, 'arparams') and model.arparams is not None:
                    ar_coeffs = [float(c) for c in model.arparams]
                if hasattr(model, 'maparams') and model.maparams is not None:
                    ma_coeffs = [float(c) for c in model.maparams]
            except Exception:
                pass
            
            return {
                "district": district,
                "adf_statistic": float(adf_result[0]),
                "adf_pvalue": float(adf_result[1]),
                "adf_critical_1pct": float(adf_result[4]['1%']),
                "adf_critical_5pct": float(adf_result[4]['5%']),
                "is_stationary": adf_result[1] < 0.05,
                "ljung_box_pvalue": float(lb_pvalue),
                "no_autocorrelation": lb_pvalue > 0.05,
                "shapiro_pvalue": float(shapiro_pvalue) if shapiro_pvalue else None,
                "residual_mean": resid_mean,
                "residual_std": resid_std,
                "residual_skewness": resid_skew,
                "residual_kurtosis": resid_kurt,
                "model_order": district_stat.get("order", (1, 1, 1)),
                "aic": float(model.aic),
                "bic": float(model.bic),
                "ar_coefficients": ar_coeffs,
                "ma_coefficients": ma_coeffs
            }
            
        except Exception as e:
            logger.error(f"Diagnostics failed for {district}: {e}")
            return None
    
    def compute_metrics(self, district: str, forecast_periods: int = 6) -> Optional[Dict]:
        """
        Compute accuracy metrics for a district's model (in-sample).
        
        Args:
            district: District name
            forecast_periods: Number of periods for CI coverage calculation
            
        Returns:
            Dictionary with accuracy metrics
        """
        if district not in self.models:
            return None
        
        model = self.models[district]
        stats_data = self.district_stats.get(district, {})
        
        try:
            # In-sample predictions (fitted values)
            fitted_vals = np.array(model.fittedvalues)
            actual_vals = np.array(model.model.endog).flatten()  # Flatten to 1D
            
            # Align fitted and actual
            n = min(len(fitted_vals), len(actual_vals))
            fitted_vals = fitted_vals[-n:]
            actual_vals = actual_vals[-n:]
            
            # Remove any NaN values
            valid_mask = ~(np.isnan(fitted_vals) | np.isnan(actual_vals))
            fitted_clean = fitted_vals[valid_mask]
            actual_clean = actual_vals[valid_mask]
            
            if len(fitted_clean) == 0:
                return None
            
            # Compute metrics
            errors = actual_clean - fitted_clean
            
            rmse = float(np.sqrt(np.mean(errors ** 2)))
            mae = float(np.mean(np.abs(errors)))
            
            # MAPE (avoid division by zero)
            nonzero = actual_clean != 0
            if nonzero.sum() > 0:
                mape = float(np.mean(np.abs(errors[nonzero] / actual_clean[nonzero])) * 100)
            else:
                mape = None
            
            # CI coverage - compute prediction intervals for in-sample
            ci_coverage = None
            try:
                # Get in-sample prediction intervals
                pred_result = model.get_prediction(start=0, end=len(actual_clean)-1)
                conf_int = pred_result.conf_int(alpha=0.05)
                lower = np.array(conf_int.iloc[:, 0])
                upper = np.array(conf_int.iloc[:, 1])
                # Calculate % of actuals within CI
                within_ci = (actual_clean >= lower) & (actual_clean <= upper)
                ci_coverage = float(within_ci.sum() / len(actual_clean) * 100)
            except Exception as e:
                logger.debug(f"CI coverage calculation failed for {district}: {e}")
            
            return {
                "district": district,
                "rmse": rmse,
                "mae": mae,
                "mape": mape,
                "aic": float(model.aic),
                "bic": float(model.bic),
                "ci_coverage_95": ci_coverage,
                "data_points": stats_data.get("data_points", len(actual_clean)),
                "mean_enrollment": stats_data.get("mean", float(np.mean(actual_clean))),
                "std_enrollment": stats_data.get("std", float(np.std(actual_clean)))
            }
            
        except Exception as e:
            logger.error(f"Metrics computation failed for {district}: {e}")
            return None
    
    def generate_forecast_plot(
        self,
        district: str,
        forecast_periods: int = 24,
        confidence_level: float = 0.95,
        show_fitted: bool = True
    ) -> Optional[go.Figure]:
        """
        Generate interactive Plotly forecast plot for a district.
        
        Args:
            district: District name
            forecast_periods: Number of periods to forecast
            confidence_level: Confidence level for intervals
            
        Returns:
            Plotly Figure object
        """
        if district not in self.models:
            return None
        
        model = self.models[district]
        stats_data = self.district_stats.get(district, {})
        
        try:
            # Historical data
            actual = model.model.endog
            fitted = model.fittedvalues
            
            # Create date index (synthetic if not available)
            n_actual = len(actual)
            hist_dates = pd.date_range(end=pd.Timestamp.now(), periods=n_actual, freq='M')
            
            # Generate forecast
            forecast_result = model.get_forecast(steps=forecast_periods)
            predictions = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=1 - confidence_level)
            
            forecast_dates = pd.date_range(start=hist_dates[-1] + pd.DateOffset(months=1), 
                                           periods=forecast_periods, freq='M')
            
            # Create figure
            fig = go.Figure()
            
            # Historical actual values
            fig.add_trace(go.Scatter(
                x=hist_dates,
                y=actual,
                mode='lines+markers',
                name='Historical (Actual)',
                line=dict(color='#36A2EB', width=2),
                marker=dict(size=4)
            ))
            
            # Fitted values (in-sample predictions)
            if show_fitted:
                fig.add_trace(go.Scatter(
                    x=hist_dates,
                    y=fitted,
                    mode='lines',
                    name='Fitted Values',
                    line=dict(color='#4BC0C0', width=1, dash='dot'),
                    opacity=0.7
                ))
            
            # Forecast
            fig.add_trace(go.Scatter(
                x=forecast_dates,
                y=predictions,
                mode='lines+markers',
                name='Forecast',
                line=dict(color='#FF6384', width=2, dash='dash'),
                marker=dict(size=6)
            ))
            
            # Confidence interval
            fig.add_trace(go.Scatter(
                x=list(forecast_dates) + list(forecast_dates[::-1]),
                y=list(conf_int.iloc[:, 1]) + list(conf_int.iloc[:, 0][::-1]),
                fill='toself',
                fillcolor='rgba(255, 99, 132, 0.2)',
                line=dict(color='rgba(255, 99, 132, 0)'),
                name=f'{int(confidence_level*100)}% Confidence Interval',
                showlegend=True
            ))
            
            # Layout
            fig.update_layout(
                title=f'Enrollment Forecast: {district}',
                xaxis_title='Date',
                yaxis_title='Enrollments',
                template='plotly_dark',
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                hovermode='x unified',
                height=500
            )
            
            # Add model info annotation
            fig.add_annotation(
                text=f"ARIMA{stats_data.get('order', (1,1,1))} | AIC: {model.aic:.1f}",
                xref="paper", yref="paper",
                x=1, y=1.05,
                showarrow=False,
                font=dict(size=10, color='gray')
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Forecast plot failed for {district}: {e}")
            return None
    
    def generate_residual_plots(self, district: str) -> Optional[go.Figure]:
        """
        Generate diagnostic plots for residuals including QQ plot.
        
        Args:
            district: District name
            
        Returns:
            Plotly Figure with subplots
        """
        if district not in self.models:
            return None
        
        model = self.models[district]
        
        try:
            residuals = model.resid.dropna()
            
            # Create subplots - 2x3 grid for QQ plot
            fig = make_subplots(
                rows=2, cols=3,
                subplot_titles=('Residual Time Series', 'Residual Histogram', 'QQ Plot',
                               'ACF', 'PACF', 'Model Info'),
                vertical_spacing=0.15,
                horizontal_spacing=0.08
            )
            
            # 1. Residual time series
            fig.add_trace(
                go.Scatter(y=residuals, mode='lines', name='Residuals',
                          line=dict(color='#36A2EB', width=1)),
                row=1, col=1
            )
            fig.add_hline(y=0, line=dict(color='red', dash='dash'), row=1, col=1)
            
            # 2. Histogram
            fig.add_trace(
                go.Histogram(x=residuals, nbinsx=30, name='Distribution',
                            marker_color='#4BC0C0', opacity=0.7),
                row=1, col=2
            )
            
            # 3. QQ Plot
            sorted_resid = np.sort(residuals)
            theoretical_quantiles = scipy_stats.norm.ppf(
                np.linspace(0.01, 0.99, len(sorted_resid))
            )
            fig.add_trace(
                go.Scatter(x=theoretical_quantiles, y=sorted_resid, 
                          mode='markers', name='QQ',
                          marker=dict(color='#9966FF', size=4)),
                row=1, col=3
            )
            # Add reference line for QQ
            qq_min, qq_max = theoretical_quantiles.min(), theoretical_quantiles.max()
            resid_std = np.std(sorted_resid)
            resid_mean = np.mean(sorted_resid)
            fig.add_trace(
                go.Scatter(x=[qq_min, qq_max], 
                          y=[resid_mean + qq_min * resid_std, resid_mean + qq_max * resid_std],
                          mode='lines', name='Normal Line',
                          line=dict(color='red', dash='dash')),
                row=1, col=3
            )
            
            # Calculate appropriate nlags based on sample size
            max_lags = min(20, len(residuals) // 2 - 1)
            if max_lags < 2:
                max_lags = 2
            
            # 4. ACF
            acf_values = acf(residuals, nlags=max_lags)
            fig.add_trace(
                go.Bar(y=acf_values, name='ACF', marker_color='#FF6384'),
                row=2, col=1
            )
            # Confidence bounds for ACF
            n = len(residuals)
            conf_bound = 1.96 / np.sqrt(n)
            fig.add_hline(y=conf_bound, line=dict(color='gray', dash='dash'), row=2, col=1)
            fig.add_hline(y=-conf_bound, line=dict(color='gray', dash='dash'), row=2, col=1)
            
            # 5. PACF
            pacf_values = pacf(residuals, nlags=max_lags)
            fig.add_trace(
                go.Bar(y=pacf_values, name='PACF', marker_color='#FFCE56'),
                row=2, col=2
            )
            fig.add_hline(y=conf_bound, line=dict(color='gray', dash='dash'), row=2, col=2)
            fig.add_hline(y=-conf_bound, line=dict(color='gray', dash='dash'), row=2, col=2)
            
            # 6. Model Info Panel
            stats_data = self.district_stats.get(district, {})
            diagnostics = self.compute_diagnostics(district)
            info_text = f"""<b>Model Info</b><br>
Order: {stats_data.get('order', 'N/A')}<br>
AIC: {model.aic:.1f}<br>
BIC: {model.bic:.1f}<br><br>
<b>Diagnostics</b><br>
ADF p-value: {diagnostics.get('adf_pvalue', 'N/A'):.4f}<br>
Ljung-Box p: {diagnostics.get('ljung_box_pvalue', 'N/A'):.4f}<br><br>
<b>Residual Stats</b><br>
Mean: {np.mean(residuals):.2f}<br>
Std: {np.std(residuals):.2f}"""
            
            fig.add_annotation(
                text=info_text,
                xref="x6 domain", yref="y6 domain",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=11, color='white'),
                align='left',
                bgcolor='rgba(50,50,50,0.8)',
                bordercolor='gray',
                borderwidth=1,
                borderpad=10
            )
            
            fig.update_layout(
                title=f'Residual Diagnostics: {district}',
                template='plotly_dark',
                showlegend=False,
                height=650,
                width=1100
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Residual plots failed for {district}: {e}")
            return None
    
    def generate_summary_table(self) -> pd.DataFrame:
        """
        Generate cross-district summary metrics table.
        
        Returns:
            DataFrame with metrics for all districts
        """
        rows = []
        
        for district in self.get_districts():
            diagnostics = self.compute_diagnostics(district)
            metrics = self.compute_metrics(district)
            
            if diagnostics and metrics:
                rows.append({
                    "District": district,
                    "RMSE": round(metrics["rmse"], 1),
                    "MAE": round(metrics["mae"], 1),
                    "MAPE (%)": round(metrics["mape"], 1) if metrics["mape"] else None,
                    "AIC": round(metrics["aic"], 1),
                    "BIC": round(metrics["bic"], 1),
                    "ADF p-value": round(diagnostics["adf_pvalue"], 4),
                    "Ljung-Box p-value": round(diagnostics["ljung_box_pvalue"], 4),
                    "CI Coverage (%)": round(metrics["ci_coverage_95"], 1) if metrics["ci_coverage_95"] else None,
                    "Data Points": metrics["data_points"],
                    "Order": str(diagnostics["model_order"])
                })
        
        df = pd.DataFrame(rows)
        if len(df) > 0 and 'RMSE' in df.columns:
            return df.sort_values("RMSE")
        return df
    
    def export_forecasts_csv(self, forecast_periods: int = 24) -> str:
        """
        Export all district forecasts to CSV.
        
        Returns:
            Path to saved CSV file
        """
        rows = []
        
        for district in self.get_districts():
            model = self.models[district]
            
            try:
                forecast_result = model.get_forecast(steps=forecast_periods)
                predictions = forecast_result.predicted_mean
                conf_int = forecast_result.conf_int(alpha=0.05)
                
                base_date = pd.Timestamp.now()
                
                for i in range(forecast_periods):
                    forecast_date = base_date + pd.DateOffset(months=i+1)
                    rows.append({
                        "district": district,
                        "date": forecast_date.strftime("%Y-%m-%d"),
                        "period": i + 1,
                        "forecast": round(predictions.iloc[i], 0),
                        "lower_ci_95": round(conf_int.iloc[i, 0], 0),
                        "upper_ci_95": round(conf_int.iloc[i, 1], 0)
                    })
            except Exception as e:
                logger.warning(f"Failed to export forecast for {district}: {e}")
        
        df = pd.DataFrame(rows)
        csv_path = os.path.join(self.output_dir, "forecasts.csv")
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved forecasts to {csv_path}")
        return csv_path
    
    def export_metrics_csv(self) -> str:
        """
        Export metrics summary to CSV.
        
        Returns:
            Path to saved CSV file
        """
        df = self.generate_summary_table()
        csv_path = os.path.join(self.output_dir, "metrics_summary.csv")
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Saved metrics to {csv_path}")
        return csv_path
    
    def save_plot(self, fig: go.Figure, filename: str) -> str:
        """Save Plotly figure as HTML."""
        filepath = os.path.join(self.output_dir, "plots", filename)
        fig.write_html(filepath)
        return filepath
    def generate_interactive_dashboard(self, forecast_periods: int = 24) -> str:
        """
        Generate a single-page interactive HTML dashboard with:
        - District dropdown selector
        - Forecast horizon slider
        - Toggle for forecast/fitted/actual
        - Summary metrics table
        
        Returns:
            Path to saved dashboard HTML
        """
        import json
        
        # Custom JSON encoder for numpy types
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.bool_):
                    return bool(obj)
                if isinstance(obj, (np.integer, np.int64)):
                    return int(obj)
                if isinstance(obj, (np.floating, np.float64)):
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super().default(obj)
        
        districts = self.get_districts()
        if not districts:
            logger.error("No districts available for dashboard")
            return ""
        
        # Collect all data for JavaScript
        all_data = {}
        for district in districts:
            model = self.models[district]
            stats = self.district_stats.get(district, {})
            metrics = self.compute_metrics(district)
            diagnostics = self.compute_diagnostics(district)
            
            # Historical and forecast data
            actual = model.model.endog.tolist() if hasattr(model.model.endog, 'tolist') else list(model.model.endog)
            fitted = model.fittedvalues.tolist() if hasattr(model.fittedvalues, 'tolist') else list(model.fittedvalues)
            
            forecast_result = model.get_forecast(steps=forecast_periods)
            forecast = forecast_result.predicted_mean.tolist()
            conf_int = forecast_result.conf_int(alpha=0.05)
            lower = conf_int.iloc[:, 0].tolist()
            upper = conf_int.iloc[:, 1].tolist()
            
            all_data[district] = {
                "actual": actual,
                "fitted": fitted,
                "forecast": forecast,
                "lower": lower,
                "upper": upper,
                "metrics": metrics,
                "diagnostics": diagnostics,
                "order": str(stats.get("order", "(1,1,1)"))
            }
        
        # Generate summary table data
        summary_df = self.generate_summary_table()
        summary_html = summary_df.to_html(classes='summary-table', index=False, border=0) if len(summary_df) > 0 else "<p>No data</p>"
        
        # Build the HTML dashboard
        dashboard_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARIMA Enrollment Forecast Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e5e5e5;
            min-height: 100vh;
            padding: 20px;
        }}
        .dashboard-header {{
            text-align: center;
            padding: 20px;
            margin-bottom: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }}
        .dashboard-header h1 {{
            font-size: 2rem;
            background: linear-gradient(90deg, #36A2EB, #FF6384);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .controls {{
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
        }}
        .control-group {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        .control-group label {{
            font-size: 0.85rem;
            color: #aaa;
        }}
        select, input[type="range"] {{
            padding: 8px 12px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 6px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 1rem;
            min-width: 180px;
        }}
        .toggle-group {{
            display: flex;
            gap: 15px;
            align-items: center;
        }}
        .toggle-group label {{
            display: flex;
            align-items: center;
            gap: 5px;
            cursor: pointer;
        }}
        .chart-container {{
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 1200px) {{
            .grid {{ grid-template-columns: 1fr; }}
        }}
        .summary-section {{
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 20px;
            overflow-x: auto;
        }}
        .summary-section h2 {{
            margin-bottom: 15px;
            color: #36A2EB;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        .summary-table th, .summary-table td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .summary-table th {{
            background: rgba(54, 162, 235, 0.2);
            color: #36A2EB;
            cursor: pointer;
        }}
        .summary-table th:hover {{
            background: rgba(54, 162, 235, 0.3);
        }}
        .summary-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        .metrics-cards {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 15px 20px;
            min-width: 150px;
        }}
        .metric-card .value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #36A2EB;
        }}
        .metric-card .label {{
            font-size: 0.8rem;
            color: #aaa;
        }}
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1>📊 ARIMA Enrollment Forecast Dashboard</h1>
        <p>Interactive visualization and diagnostics for district-level forecasting</p>
    </div>
    
    <div class="controls">
        <div class="control-group">
            <label>District</label>
            <select id="districtSelect" onchange="updateCharts()">
                {"".join(f'<option value="{d}">{d}</option>' for d in districts)}
            </select>
        </div>
        <div class="control-group">
            <label>Forecast Horizon: <span id="horizonValue">{forecast_periods}</span> periods</label>
            <input type="range" id="horizonSlider" min="6" max="36" value="{forecast_periods}" onchange="updateHorizon()">
        </div>
        <div class="control-group">
            <label>Toggle Series</label>
            <div class="toggle-group">
                <label><input type="checkbox" id="showActual" checked onchange="updateCharts()"> Historical</label>
                <label><input type="checkbox" id="showFitted" checked onchange="updateCharts()"> Fitted</label>
                <label><input type="checkbox" id="showForecast" checked onchange="updateCharts()"> Forecast</label>
            </div>
        </div>
    </div>
    
    <div class="metrics-cards" id="metricsCards"></div>
    
    <div class="grid">
        <div class="chart-container">
            <div id="forecastChart"></div>
        </div>
        <div class="chart-container">
            <div id="diagnosticsChart"></div>
        </div>
    </div>
    
    <div class="summary-section">
        <h2>Cross-District Summary</h2>
        {summary_html}
    </div>
    
    <script>
        const allData = {json.dumps(all_data, cls=NumpyEncoder)};
        let currentHorizon = {forecast_periods};
        
        function updateHorizon() {{
            currentHorizon = parseInt(document.getElementById('horizonSlider').value);
            document.getElementById('horizonValue').textContent = currentHorizon;
            updateCharts();
        }}
        
        function updateCharts() {{
            const district = document.getElementById('districtSelect').value;
            const data = allData[district];
            const showActual = document.getElementById('showActual').checked;
            const showFitted = document.getElementById('showFitted').checked;
            const showForecast = document.getElementById('showForecast').checked;
            
            // Update metrics cards
            const metrics = data.metrics || {{}};
            document.getElementById('metricsCards').innerHTML = `
                <div class="metric-card"><div class="value">${{(metrics.rmse || 0).toFixed(1)}}</div><div class="label">RMSE</div></div>
                <div class="metric-card"><div class="value">${{(metrics.mae || 0).toFixed(1)}}</div><div class="label">MAE</div></div>
                <div class="metric-card"><div class="value">${{(metrics.mape || 0).toFixed(1)}}%</div><div class="label">MAPE</div></div>
                <div class="metric-card"><div class="value">${{(metrics.aic || 0).toFixed(0)}}</div><div class="label">AIC</div></div>
                <div class="metric-card"><div class="value">${{(metrics.ci_coverage_95 || 0).toFixed(1)}}%</div><div class="label">CI Coverage</div></div>
                <div class="metric-card"><div class="value">${{metrics.data_points || 0}}</div><div class="label">Data Points</div></div>
            `;
            
            // Build forecast chart
            const traces = [];
            const n = data.actual.length;
            const histX = [...Array(n).keys()];
            const forecastX = [...Array(currentHorizon).keys()].map(i => n + i);
            
            if (showActual) {{
                traces.push({{
                    x: histX, y: data.actual,
                    mode: 'lines+markers', name: 'Historical',
                    line: {{color: '#36A2EB', width: 2}},
                    marker: {{size: 4}}
                }});
            }}
            if (showFitted) {{
                traces.push({{
                    x: histX, y: data.fitted,
                    mode: 'lines', name: 'Fitted',
                    line: {{color: '#4BC0C0', width: 1, dash: 'dot'}},
                    opacity: 0.7
                }});
            }}
            if (showForecast) {{
                traces.push({{
                    x: forecastX, y: data.forecast.slice(0, currentHorizon),
                    mode: 'lines+markers', name: 'Forecast',
                    line: {{color: '#FF6384', width: 2, dash: 'dash'}},
                    marker: {{size: 6}}
                }});
                // Confidence interval
                const lower = data.lower.slice(0, currentHorizon);
                const upper = data.upper.slice(0, currentHorizon);
                traces.push({{
                    x: [...forecastX, ...forecastX.slice().reverse()],
                    y: [...upper, ...lower.slice().reverse()],
                    fill: 'toself', fillcolor: 'rgba(255, 99, 132, 0.15)',
                    line: {{color: 'transparent'}},
                    name: '95% CI', showlegend: true
                }});
            }}
            
            Plotly.newPlot('forecastChart', traces, {{
                title: `Enrollment Forecast: ${{district}}`,
                template: 'plotly_dark',
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                xaxis: {{title: 'Period', gridcolor: 'rgba(255,255,255,0.1)'}},
                yaxis: {{title: 'Enrollments', gridcolor: 'rgba(255,255,255,0.1)'}},
                legend: {{x: 0, y: 1}}
            }});
            
            // Diagnostics info
            const diag = data.diagnostics || {{}};
            const diagText = `
                <b>Model: ARIMA${{data.order}}</b><br><br>
                <b>ADF Test (Stationarity)</b><br>
                Statistic: ${{(diag.adf_statistic || 0).toFixed(3)}}<br>
                p-value: ${{(diag.adf_pvalue || 0).toFixed(4)}}<br>
                Stationary: ${{diag.is_stationary ? '✓ Yes' : '✗ No'}}<br><br>
                <b>Ljung-Box (Autocorrelation)</b><br>
                p-value: ${{(diag.ljung_box_pvalue || 0).toFixed(4)}}<br>
                No Autocorr: ${{diag.no_autocorrelation ? '✓ Yes' : '✗ No'}}<br><br>
                <b>Model Coefficients</b><br>
                AR: ${{(diag.ar_coefficients || []).map(c => c.toFixed(3)).join(', ') || 'N/A'}}<br>
                MA: ${{(diag.ma_coefficients || []).map(c => c.toFixed(3)).join(', ') || 'N/A'}}<br><br>
                <b>Information Criteria</b><br>
                AIC: ${{(diag.aic || 0).toFixed(1)}}<br>
                BIC: ${{(diag.bic || 0).toFixed(1)}}
            `;
            
            Plotly.newPlot('diagnosticsChart', [{{
                type: 'indicator',
                mode: 'number',
                value: 0,
                title: {{text: ''}}
            }}], {{
                title: 'Model Diagnostics',
                template: 'plotly_dark',
                paper_bgcolor: 'transparent',
                annotations: [{{
                    text: diagText,
                    x: 0.5, y: 0.5,
                    xref: 'paper', yref: 'paper',
                    showarrow: false,
                    font: {{size: 13, color: 'white'}},
                    align: 'left'
                }}]
            }});
        }}
        
        // Sortable table
        document.querySelectorAll('.summary-table th').forEach((th, i) => {{
            th.addEventListener('click', () => sortTable(i));
        }});
        
        function sortTable(col) {{
            const table = document.querySelector('.summary-table');
            const rows = Array.from(table.querySelectorAll('tr:not(:first-child)'));
            const dir = table.dataset.sortDir === 'asc' ? 'desc' : 'asc';
            table.dataset.sortDir = dir;
            
            rows.sort((a, b) => {{
                const aVal = a.cells[col]?.textContent || '';
                const bVal = b.cells[col]?.textContent || '';
                const aNum = parseFloat(aVal);
                const bNum = parseFloat(bVal);
                if (!isNaN(aNum) && !isNaN(bNum)) {{
                    return dir === 'asc' ? aNum - bNum : bNum - aNum;
                }}
                return dir === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
            }});
            
            rows.forEach(row => table.appendChild(row));
        }}
        
        // Initial render
        updateCharts();
    </script>
</body>
</html>'''
        
        # Save dashboard
        dashboard_path = os.path.join(self.output_dir, "dashboard.html")
        with open(dashboard_path, 'w') as f:
            f.write(dashboard_html)
        
        logger.info(f"Generated interactive dashboard: {dashboard_path}")
        return dashboard_path
    
    def generate_all_outputs(self, forecast_periods: int = 24) -> Dict[str, str]:
        """
        Generate all diagnostic outputs for all districts.
        
        Returns:
            Dictionary mapping output type to file path
        """
        outputs = {}
        
        # Generate per-district plots
        for district in self.get_districts():
            # Forecast plot
            forecast_fig = self.generate_forecast_plot(district, forecast_periods)
            if forecast_fig:
                path = self.save_plot(forecast_fig, f"{district}_forecast.html")
                outputs[f"{district}_forecast"] = path
            
            # Diagnostics plot
            diag_fig = self.generate_residual_plots(district)
            if diag_fig:
                path = self.save_plot(diag_fig, f"{district}_diagnostics.html")
                outputs[f"{district}_diagnostics"] = path
        
        # Export CSVs
        outputs["forecasts_csv"] = self.export_forecasts_csv(forecast_periods)
        outputs["metrics_csv"] = self.export_metrics_csv()
        
        # Generate interactive dashboard
        outputs["dashboard"] = self.generate_interactive_dashboard(forecast_periods)
        
        logger.info(f"Generated {len(outputs)} output files")
        return outputs


def run_diagnostics():
    """Run full diagnostics and generate all outputs."""
    logging.basicConfig(level=logging.INFO)
    
    diag = ARIMADiagnostics()
    
    if not diag.load_models():
        print("Failed to load models. Make sure the forecast model has been trained.")
        return
    
    print(f"\n📊 ARIMA Forecast Diagnostics")
    print(f"{'='*50}")
    print(f"Districts: {', '.join(diag.get_districts())}")
    print()
    
    # Generate all outputs
    outputs = diag.generate_all_outputs()
    
    print(f"\n✅ Generated {len(outputs)} output files:")
    for name, path in outputs.items():
        print(f"   • {name}: {path}")
    
    # Print summary table
    print(f"\n📈 Cross-District Summary:")
    print(diag.generate_summary_table().to_string(index=False))


if __name__ == "__main__":
    run_diagnostics()
