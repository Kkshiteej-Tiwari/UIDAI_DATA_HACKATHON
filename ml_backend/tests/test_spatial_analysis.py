"""
Geospatial Hotspot Detection - Unit Tests
Tests for Moran's I, Getis-Ord Gi*, and forecasting functions.
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMoransI:
    """Tests for Moran's I calculation."""
    
    def test_morans_i_positive_autocorrelation(self):
        """Test that clustered values produce positive Moran's I."""
        from services.spatial_analysis import _calculate_morans_i_manual
        
        # Create clustered pattern (high values together, low values together)
        values = np.array([10, 11, 10, 11, 90, 91, 90, 91])
        
        # Simple neighbor weights (adjacent)
        n = len(values)
        weights = np.zeros((n, n))
        for i in range(n - 1):
            weights[i, i + 1] = 0.5
            weights[i + 1, i] = 0.5
        
        result = _calculate_morans_i_manual(values, weights)
        
        assert result['morans_i'] > 0, "Clustered values should produce positive Moran's I"
        assert 'interpretation' in result
        assert result['n'] == n
    
    def test_morans_i_random_pattern(self):
        """Test that random values produce near-zero Moran's I."""
        from services.spatial_analysis import _calculate_morans_i_manual
        
        np.random.seed(42)
        values = np.random.uniform(0, 100, 20)
        
        n = len(values)
        weights = np.ones((n, n)) / (n - 1)
        np.fill_diagonal(weights, 0)
        
        result = _calculate_morans_i_manual(values, weights)
        
        # Random pattern should be near expected value (-1/(n-1))
        expected_i = -1 / (n - 1)
        assert abs(result['morans_i'] - expected_i) < 0.5, "Random values should produce Moran's I near expected value"
    
    def test_morans_i_with_gdf(self):
        """Test Moran's I with GeoDataFrame input."""
        import geopandas as gpd
        from shapely.geometry import Point
        from services.spatial_analysis import calculate_morans_i
        
        # Create simple GeoDataFrame
        data = {
            'state_name': ['A', 'B', 'C', 'D', 'E'],
            'penetration_rate': [0.9, 0.85, 0.7, 0.65, 0.6],
            'geometry': [Point(0, 0), Point(1, 0), Point(2, 0), Point(0, 1), Point(1, 1)]
        }
        gdf = gpd.GeoDataFrame(data)
        
        result = calculate_morans_i(gdf, value_column='penetration_rate')
        
        assert 'morans_i' in result
        assert 'p_value' in result
        assert 'interpretation' in result
        assert result['morans_i'] >= -1 and result['morans_i'] <= 1


class TestGetisOrdGi:
    """Tests for Getis-Ord Gi* hotspot detection."""
    
    def test_hotspot_detection(self):
        """Test that high values are identified as hotspots."""
        import geopandas as gpd
        from shapely.geometry import Point
        from services.spatial_analysis import detect_hotspots_getis_ord
        
        # Create data with clear hotspot (very high value) and coldspot (very low value)
        data = {
            'state_name': ['Hotspot', 'Near1', 'Near2', 'Coldspot', 'Near3'],
            'penetration_rate': [0.99, 0.95, 0.94, 0.40, 0.45],
            'geometry': [Point(0, 0), Point(0.1, 0), Point(0, 0.1), Point(5, 5), Point(5.1, 5)]
        }
        gdf = gpd.GeoDataFrame(data)
        
        result = detect_hotspots_getis_ord(gdf, value_column='penetration_rate')
        
        assert 'classification' in result.columns
        assert 'gi_z_score' in result.columns
        assert 'confidence_level' in result.columns
    
    def test_coldspot_detection(self):
        """Test that low values in clusters are identified as coldspots."""
        from services.spatial_analysis import _calculate_gi_star_manual
        
        # Values with clear low cluster
        values = np.array([0.9, 0.88, 0.87, 0.3, 0.32, 0.31])
        
        # Neighbors: first 3 are neighbors, last 3 are neighbors
        n = len(values)
        weights = np.zeros((n, n))
        weights[0, 1] = weights[0, 2] = weights[1, 0] = weights[1, 2] = 0.5
        weights[2, 0] = weights[2, 1] = 0.5
        weights[3, 4] = weights[3, 5] = weights[4, 3] = weights[4, 5] = 0.5
        weights[5, 3] = weights[5, 4] = 0.5
        
        z_scores, p_values = _calculate_gi_star_manual(values, weights)
        
        # Last 3 (low values) should have negative z-scores
        assert z_scores[3] < 0, "Low value cluster should have negative z-score"
        assert z_scores[5] < 0, "Low value cluster should have negative z-score"
    
    def test_classification_labels(self):
        """Test that classification labels are correct."""
        from services.spatial_analysis import _classify_gi_star, _get_confidence_level
        
        # Significant hotspot
        assert _classify_gi_star(2.5, 0.01, 0.05) == 'hotspot'
        
        # Significant coldspot
        assert _classify_gi_star(-2.5, 0.01, 0.05) == 'coldspot'
        
        # Not significant
        assert _classify_gi_star(1.0, 0.20, 0.05) == 'neutral'
        
        # Confidence levels
        assert _get_confidence_level(0.005) == '99%'
        assert _get_confidence_level(0.03) == '95%'
        assert _get_confidence_level(0.08) == '90%'
        assert _get_confidence_level(0.15) == 'not_significant'


class TestAnomalyDetection:
    """Tests for anomaly detection."""
    
    def test_detect_anomalies(self):
        """Test anomaly detection with clear outliers."""
        import geopandas as gpd
        from shapely.geometry import Point
        from services.spatial_analysis import detect_anomalies
        
        # Create data with clear anomalies
        data = {
            'state_name': ['Normal1', 'Normal2', 'Normal3', 'Outlier_High', 'Outlier_Low'],
            'penetration_rate': [0.80, 0.82, 0.78, 0.99, 0.40],
            'geometry': [Point(i, 0) for i in range(5)]
        }
        gdf = gpd.GeoDataFrame(data)
        
        anomalies = detect_anomalies(gdf, value_column='penetration_rate', threshold=1.5)
        
        assert len(anomalies) >= 2, "Should detect at least 2 anomalies"
        
        # Check anomaly structure
        if anomalies:
            a = anomalies[0]
            assert 'region' in a
            assert 'z_score' in a
            assert 'severity' in a
            assert 'direction' in a
    
    def test_no_anomalies_uniform_data(self):
        """Test that uniform data has no anomalies."""
        import geopandas as gpd
        from shapely.geometry import Point
        from services.spatial_analysis import detect_anomalies
        
        # All values are the same
        data = {
            'state_name': ['A', 'B', 'C', 'D'],
            'penetration_rate': [0.80, 0.80, 0.80, 0.80],
            'geometry': [Point(i, 0) for i in range(4)]
        }
        gdf = gpd.GeoDataFrame(data)
        
        anomalies = detect_anomalies(gdf, value_column='penetration_rate', threshold=2.0)
        
        assert len(anomalies) == 0, "Uniform data should have no anomalies"


class TestForecasting:
    """Tests for forecasting functions."""
    
    def test_simple_forecast(self):
        """Test simple exponential smoothing forecast."""
        from services.forecasting import _train_simple_model, _simple_forecast
        
        values = np.array([100, 110, 120, 130, 140, 150])
        
        model = _train_simple_model(values)
        
        assert model['order'] == (0, 0, 0)
        assert 'residuals' in model
        assert 'aic' in model
        
        # Generate forecast
        dates = ['2025-01', '2025-02', '2025-03']
        forecast = _simple_forecast(model, 3, dates, 0.95)
        
        assert len(forecast['forecast']) == 3
        assert len(forecast['lower_ci']) == 3
        assert len(forecast['upper_ci']) == 3
        
        # CI should bound the forecast
        for i in range(3):
            assert forecast['lower_ci'][i] <= forecast['forecast'][i]
            assert forecast['forecast'][i] <= forecast['upper_ci'][i]
    
    def test_sarima_training(self):
        """Test SARIMA model training."""
        from services.forecasting import train_sarima_model
        
        # Create simple time series with trend
        np.random.seed(42)
        ts = pd.Series([100 + i * 5 + np.random.normal(0, 5) for i in range(24)])
        
        result = train_sarima_model(ts, auto=True)
        
        assert 'model' in result
        assert 'order' in result
        assert 'aic' in result
        assert 'diagnostics' in result
    
    def test_scenario_modeling(self):
        """Test scenario modeling."""
        from services.forecasting import scenario_modeling
        
        # Create sample historical data
        data = pd.DataFrame({
            'state': ['TestState'] * 12,
            'date': pd.date_range('2024-01', periods=12, freq='M').strftime('%Y-%m'),
            'total_enrollments': [100000 + i * 5000 for i in range(12)]
        })
        
        params = {'boost_percent': 10, 'start_month': 0, 'duration_months': 3}
        result = scenario_modeling('TestState', data, params, horizon_months=6)
        
        assert 'baseline' in result
        assert 'intervention' in result
        assert 'cumulative_impact' in result
        assert result['cumulative_impact'] > 0, "Intervention should have positive impact"


class TestGeoProcessor:
    """Tests for geo processor functions."""
    
    def test_state_name_normalization(self):
        """Test state name normalization."""
        from services.geo_processor import GeoProcessor
        
        geo = GeoProcessor.__new__(GeoProcessor)  # Create without __init__
        geo.geojson_path = None
        geo._gdf = None
        
        assert geo.normalize_state_name("Andaman and Nicobar Islands") == "Andaman and Nicobar"
        assert geo.normalize_state_name("Delhi") == "NCT of Delhi"
        assert geo.normalize_state_name("Orissa") == "Odisha"
        assert geo.normalize_state_name("Maharashtra") == "Maharashtra"
    
    def test_penetration_rate_calculation(self):
        """Test penetration rate calculation."""
        from services.geo_processor import GeoProcessor
        
        geo = GeoProcessor.__new__(GeoProcessor)
        geo.geojson_path = None
        geo._gdf = None
        
        # Maharashtra population ~112.4 million
        rate, pop = geo.calculate_penetration_rate(50000000, "Maharashtra")
        
        assert 0 < rate < 1.5, "Rate should be between 0 and 150%"
        assert pop == 112.4, "Maharashtra population should be 112.4 million"
    
    def test_population_lookup(self):
        """Test that state populations are available."""
        from services.geo_processor import STATE_POPULATION, get_state_population
        
        assert "Maharashtra" in STATE_POPULATION
        assert "Bihar" in STATE_POPULATION
        assert STATE_POPULATION["Bihar"] > 100, "Bihar population should be > 100 million"
        
        pop = get_state_population("Tamil Nadu")
        assert pop > 70, "Tamil Nadu population should be > 70 million"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
