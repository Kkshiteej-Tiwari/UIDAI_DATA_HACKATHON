# Gender Inclusion Tracker - ML Backend

A **machine learning-powered backend** for monitoring and predicting gender inclusion gaps in Aadhaar enrollment across India.

## 🎯 Overview

This backend provides:
- **Data Connectors**: Fetch data from data.gov.in APIs
- **Preprocessing**: Automatic cleaning, normalization, and feature engineering
- **ML Training**: LightGBM models with hyperparameter tuning via Optuna
- **Explainability**: SHAP-based feature importance and local explanations
- **Predictions**: Risk scores with actionable recommendations
- **Visualizations**: Charts, maps, and PDF reports

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd ml_backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API key from data.gov.in
```

### 3. Run the Server

```bash
# Development mode (with hot reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or using make
make dev
```

### 4. Access API Documentation

Open http://localhost:8000/docs for interactive Swagger documentation.

## 📋 API Endpoints

### Datasets
- `GET /api/datasets/` - List available datasets with suitability scores
- `POST /api/datasets/select` - Select or auto-select best dataset
- `GET /api/datasets/{key}/preview` - Preview dataset content

### Analysis
- `POST /api/analyze/` - Run EDA and preprocessing
- `GET /api/analyze/{id}` - Get analysis results
- `GET /api/analyze/{id}/data` - Get processed data

### Training
- `POST /api/train/` - Train ML model
- `GET /api/train/models` - List trained models
- `GET /api/train/models/{id}` - Get model details

### Predictions
- `POST /api/predict/` - Make predictions with explanations
- `GET /api/predict/high-risk/{model_id}` - Get high-risk districts

### Reports
- `GET /api/report/{id}` - Generate analysis report (JSON/PDF)
- `GET /api/report/map/choropleth` - Get choropleth map data
- `GET /api/report/export/{id}` - Export data for field teams

## 🔧 Example Usage

### Full Pipeline Demo

```bash
# 1. Generate sample data
python scripts/generate_sample_data.py

# 2. Start server
make dev
```

### API Calls

```bash
# Health check
curl http://localhost:8000/api/health

# List datasets
curl http://localhost:8000/api/datasets/

# Auto-select dataset
curl -X POST http://localhost:8000/api/datasets/select \
  -H "Content-Type: application/json" \
  -d '{"auto": true}'

# Run analysis
curl -X POST http://localhost:8000/api/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"dataset_key": "enrolment", "geography_level": "district", "limit": 500}'

# Train model
curl -X POST http://localhost:8000/api/train/ \
  -H "Content-Type: application/json" \
  -d '{"analysis_id": "analysis_20250113_123456", "model": "lightgbm", "tune": true}'

# Get predictions
curl -X POST http://localhost:8000/api/predict/ \
  -H "Content-Type: application/json" \
  -d '{"model_id": "model_20250113_123456_lightgbm", "analysis_id": "analysis_20250113_123456"}'
```

## 📊 Example Responses

### /api/analyze Response
```json
{
  "analysis_id": "analysis_20250113_123456",
  "dataset_key": "enrolment",
  "n_records": 500,
  "n_districts": 145,
  "statistics": {
    "female_coverage": {
      "mean": 0.471,
      "min": 0.312,
      "max": 0.519
    },
    "high_risk_count": 89,
    "high_risk_percentage": 17.8
  },
  "sanity_checklist": [
    {"status": "ok", "item": "Gender columns", "message": "Male and female enrollment data available"}
  ]
}
```

### /api/predict Response
```json
{
  "model_id": "model_20250113_lightgbm",
  "total_predictions": 145,
  "high_risk_count": 32,
  "predictions": [
    {
      "district": "Kishanganj",
      "state": "Bihar",
      "risk_probability": 0.92,
      "predicted_high_risk": 1,
      "female_coverage_ratio": 0.38,
      "top_drivers": [
        {"feature": "female_coverage_ratio", "shap_value": 0.45},
        {"feature": "gender_gap", "shap_value": 0.23}
      ],
      "recommendation": "women-only-registration-camp",
      "estimated_target_count": 12500
    }
  ]
}
```

## 🐳 Docker Deployment

```bash
# Build image
docker build -t gender-tracker-backend:latest .

# Run container
docker run -p 8000:8000 --env-file .env gender-tracker-backend:latest
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## 🔐 Privacy & Security

### Data Privacy
- **No PII**: All outputs are aggregated at district level (no individual Aadhaar data)
- **Differential Privacy**: Optional noise addition for public outputs (`ENABLE_PRIVACY_NOISE=true`)
- **Aggregated Metrics**: Only percentages and counts are shared

### Security
- API key authentication (configure `API_TOKEN_SECRET`)
- CORS middleware with configurable origins
- Non-root Docker user
- TLS recommended for production

### Retention Policy Recommendations
1. **Raw data**: Delete after processing (do not persist)
2. **Aggregated outputs**: Retain for 2 years
3. **Model artifacts**: Version and retain for audit trails
4. **Public reports**: Apply differential privacy before release

## 📁 Project Structure

```
ml_backend/
├── app/
│   ├── api/               # FastAPI routers
│   │   ├── datasets.py    # Dataset management
│   │   ├── analyze.py     # EDA and preprocessing
│   │   ├── train.py       # Model training
│   │   ├── predict.py     # Predictions
│   │   └── report.py      # Reports and exports
│   ├── core/              # Configuration
│   │   ├── config.py      # Settings management
│   │   └── security.py    # Auth and privacy
│   ├── services/          # Business logic
│   │   ├── connectors.py  # API connectors
│   │   ├── preprocessing.py
│   │   ├── models.py      # ML models
│   │   ├── explainers.py  # SHAP explanations
│   │   └── visualizations.py
│   └── main.py            # FastAPI app
├── tests/                 # Unit tests
├── scripts/               # Utilities
├── artifacts/             # Generated outputs
├── models/                # Saved models
├── requirements.txt
├── Dockerfile
├── Makefile
└── .env.example
```

## 🛠️ Assumptions

1. **Data Schema**: Datasets contain columns mappable to state, district, male/female enrollment
2. **API Access**: data.gov.in API key required for live data (sample data available for testing)
3. **Geography**: District-level is the primary analysis granularity
4. **Target Threshold**: Default 85% female coverage threshold for high-risk classification

## 📄 License

Internal use for UIDAI Data Hackathon.
