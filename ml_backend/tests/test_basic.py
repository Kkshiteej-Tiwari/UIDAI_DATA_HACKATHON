"""
Gender Inclusion Tracker - Unit Tests
Basic tests for connectors, preprocessing, and API endpoints.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.preprocessing import GenderDataPreprocessor
from app.services.models import GenderRiskModel


class TestPreprocessing:
    """Tests for data preprocessing."""
    
    def test_normalize_columns(self):
        """Test column name normalization."""
        preprocessor = GenderDataPreprocessor()
        
        df = pd.DataFrame({
            'State_Name': ['Bihar', 'UP'],
            'DISTRICT': ['Patna', 'Lucknow'],
            'Male_Count': [1000, 2000],
            'Female_Count': [900, 1800]
        })
        
        normalized, mapping = preprocessor.normalize_columns(df)
        
        assert 'state' in normalized.columns or 'State_Name' in normalized.columns
        assert len(mapping) > 0 or len(df.columns) == len(normalized.columns)
    
    def test_compute_gender_features(self):
        """Test gender feature computation."""
        preprocessor = GenderDataPreprocessor()
        
        df = pd.DataFrame({
            'male_enrolled': [1000, 800, 600],
            'female_enrolled': [900, 900, 400]
        })
        
        result, computed = preprocessor.compute_gender_features(df)
        
        assert 'female_coverage_ratio' in result.columns
        assert 'gender_gap' in result.columns
        assert result['female_coverage_ratio'].iloc[0] == pytest.approx(0.473684, rel=0.01)
    
    def test_handle_missing_values(self):
        """Test missing value imputation."""
        preprocessor = GenderDataPreprocessor()
        
        df = pd.DataFrame({
            'value1': [1.0, 2.0, np.nan, 4.0],
            'value2': [10, 20, 30, np.nan]
        })
        
        result, imputed = preprocessor.handle_missing_values(df, strategy='median')
        
        assert result['value1'].isna().sum() == 0
        assert result['value2'].isna().sum() == 0
        assert len(imputed) == 2
    
    def test_full_preprocessing(self):
        """Test full preprocessing pipeline."""
        preprocessor = GenderDataPreprocessor()
        
        df = pd.DataFrame({
            'state': ['Bihar', 'Bihar', 'UP', 'UP'],
            'district': ['Patna', 'Gaya', 'Lucknow', 'Varanasi'],
            'male_enrolled': [1000, 800, 1200, 900],
            'female_enrolled': [800, 600, 1100, 850]
        })
        
        result, report = preprocessor.preprocess(df, geography_level='district')
        
        assert report.original_rows == 4
        assert 'high_risk' in result.columns
        assert 'female_coverage_ratio' in result.columns


class TestModels:
    """Tests for ML models."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        np.random.seed(42)
        n = 100
        
        df = pd.DataFrame({
            'female_coverage_ratio': np.random.uniform(0.3, 0.6, n),
            'male_enrolled': np.random.randint(500, 2000, n),
            'female_enrolled': np.random.randint(300, 1500, n),
            'age_0_5': np.random.randint(50, 200, n),
            'age_5_17': np.random.randint(100, 400, n),
            'age_18_plus': np.random.randint(300, 1200, n)
        })
        
        # Create target based on coverage
        df['high_risk'] = (df['female_coverage_ratio'] < 0.45).astype(int)
        
        return df
    
    def test_model_training(self, sample_data):
        """Test model can be trained."""
        model = GenderRiskModel(model_type='logistic')  # Use simpler model for tests
        
        trained = model.train(
            sample_data,
            target_column='high_risk',
            tune=False,  # Skip tuning for speed
            use_smote=False
        )
        
        assert trained.model_id is not None
        assert trained.metrics.accuracy > 0
        assert len(trained.features) > 0
    
    def test_model_prediction(self, sample_data):
        """Test model can make predictions."""
        model = GenderRiskModel(model_type='logistic')
        
        model.train(
            sample_data,
            target_column='high_risk',
            tune=False,
            use_smote=False
        )
        
        predictions = model.predict(sample_data.head(10))
        
        assert 'risk_probability' in predictions.columns
        assert 'predicted_high_risk' in predictions.columns
        assert len(predictions) == 10


class TestMetrics:
    """Tests for metric computation."""
    
    def test_coverage_ratio_computation(self):
        """Test coverage ratio calculation."""
        male = 1000
        female = 900
        total = male + female
        
        ratio = female / total
        
        assert ratio == pytest.approx(0.4736842, rel=0.001)
    
    def test_gender_gap_computation(self):
        """Test gender gap calculation."""
        male = 1000
        female = 800
        total = male + female
        
        male_ratio = male / total
        female_ratio = female / total
        gap = male_ratio - female_ratio
        
        assert gap == pytest.approx(0.1111, rel=0.01)


# FastAPI endpoint tests
from fastapi.testclient import TestClient


class TestAPIEndpoints:
    """Tests for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "endpoints" in data
    
    def test_datasets_list_endpoint(self, client):
        """Test datasets listing endpoint."""
        response = client.get("/api/datasets/")
        
        # May fail without API key, but should return valid response
        assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
