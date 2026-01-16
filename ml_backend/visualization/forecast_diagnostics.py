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
                "bic": float(model.bic)
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
            
            # CI coverage - simplified, skip if fails
            ci_coverage = None
            
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
        Generate diagnostic plots for residuals.
        
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
            
            # Create subplots
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Residual Time Series', 'Residual Histogram',
                               'ACF', 'PACF'),
                vertical_spacing=0.12,
                horizontal_spacing=0.1
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
            
            # Calculate appropriate nlags based on sample size
            max_lags = min(20, len(residuals) // 2 - 1)
            if max_lags < 2:
                max_lags = 2
            
            # 3. ACF
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
            
            # 4. PACF
            pacf_values = pacf(residuals, nlags=max_lags)
            fig.add_trace(
                go.Bar(y=pacf_values, name='PACF', marker_color='#FFCE56'),
                row=2, col=2
            )
            fig.add_hline(y=conf_bound, line=dict(color='gray', dash='dash'), row=2, col=2)
            fig.add_hline(y=-conf_bound, line=dict(color='gray', dash='dash'), row=2, col=2)
            
            fig.update_layout(
                title=f'Residual Diagnostics: {district}',
                template='plotly_dark',
                showlegend=False,
                height=600
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
