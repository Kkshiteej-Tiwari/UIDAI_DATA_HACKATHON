"""
Enrollment Forecast Module

ARIMA-based enrollment forecasting for district-level predictions.
Uses data from data.gov.in APIs.

Components:
- models/forecast.py: ARIMA EnrollmentForecaster class
- api/forecast.py: FastAPI endpoints for predictions
- forecast_diagnostics.py: Diagnostic tools and visualizations
"""

from .models.forecast import EnrollmentForecaster, get_forecaster

__all__ = [
    "EnrollmentForecaster",
    "get_forecaster",
]
