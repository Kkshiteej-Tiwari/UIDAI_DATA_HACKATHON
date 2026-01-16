# Enrollment Forecast Module

ARIMA-based enrollment forecasting for district-level predictions using data from data.gov.in APIs.

## Structure

```
enrollment_forecast/
├── __init__.py              # Module exports
├── forecast_diagnostics.py  # Diagnostic tools & visualizations
├── models/
│   ├── __init__.py
│   └── forecast.py          # EnrollmentForecaster ARIMA class
└── api/
    ├── __init__.py
    └── forecast.py          # FastAPI endpoints
```

## Key Components

### EnrollmentForecaster (models/forecast.py)
- ARIMA-based time-series forecaster
- Trains per-district models on historical enrollment data
- Generates forecasts with confidence intervals

### API Endpoints (api/forecast.py)
- `POST /api/forecast/train` - Train models on live data
- `GET /api/forecast/predict/{district}` - Get forecast for a district
- `GET /api/forecast/districts` - List available districts

### Diagnostics (forecast_diagnostics.py)
- Model validation tests (ADF, Ljung-Box)
- Accuracy metrics (RMSE, MAE, MAPE)
- Interactive Plotly visualizations

## Usage

```python
from enrollment_forecast import get_forecaster

forecaster = get_forecaster()
result = forecaster.forecast("Mumbai", periods=6)
print(result)
```
