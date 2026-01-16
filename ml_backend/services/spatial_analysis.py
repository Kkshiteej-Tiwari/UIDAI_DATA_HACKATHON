"""
Spatial Analysis Service
Implements spatial statistics for Geospatial Hotspot Detection:
- Moran's I (global spatial autocorrelation)
- Getis-Ord Gi* (local hotspot detection)
- Anomaly detection
- Time series decomposition
"""
import logging
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def calculate_morans_i(
    gdf: gpd.GeoDataFrame,
    value_column: str = "penetration_rate",
    weights_matrix: Optional[np.ndarray] = None
) -> Dict:
    """
    Calculate global Moran's I statistic for spatial autocorrelation.
    
    Moran's I measures spatial autocorrelation - whether similar values
    cluster together (positive I) or disperse (negative I).
    
    Args:
        gdf: GeoDataFrame with values to analyze
        value_column: Column containing the values to analyze
        weights_matrix: Optional NxN spatial weights matrix (auto-generated if None)
        
    Returns:
        Dict containing:
        - morans_i: The Moran's I statistic (-1 to 1)
        - p_value: Statistical significance
        - z_score: Standard score
        - interpretation: Human-readable interpretation
        - expected_i: Expected I under null hypothesis
        
    Example:
        >>> from services.geo_processor import GeoProcessor
        >>> geo = GeoProcessor()
        >>> gdf = geo.join_enrollment_data(enrollment_df)
        >>> result = calculate_morans_i(gdf)
        >>> print(f"Moran's I: {result['morans_i']:.3f}, p-value: {result['p_value']:.4f}")
        Moran's I: 0.432, p-value: 0.0012
    """
    if value_column not in gdf.columns:
        raise ValueError(f"Column '{value_column}' not found in GeoDataFrame")
    
    values = gdf[value_column].values.astype(float)
    n = len(values)
    
    if n < 3:
        return {
            "morans_i": 0.0,
            "p_value": 1.0,
            "z_score": 0.0,
            "interpretation": "Insufficient data for analysis",
            "expected_i": 0.0,
            "n": n
        }
    
    # Generate weights matrix if not provided
    if weights_matrix is None:
        weights_matrix = _generate_simple_weights(gdf)
    
    # Ensure weights matrix matches data size
    if weights_matrix.shape[0] != n:
        weights_matrix = _generate_simple_weights(gdf)
    
    try:
        # Try using ESDA for precise calculation
        from esda.moran import Moran
        from libpysal.weights import W
        
        # Convert numpy matrix to PySAL weights
        neighbors = {}
        weights_dict = {}
        for i in range(n):
            neighbor_list = []
            weight_list = []
            for j in range(n):
                if weights_matrix[i, j] > 0:
                    neighbor_list.append(j)
                    weight_list.append(weights_matrix[i, j])
            neighbors[i] = neighbor_list
            weights_dict[i] = weight_list
        
        w = W(neighbors, weights_dict)
        mi = Moran(values, w)
        
        return {
            "morans_i": float(mi.I),
            "p_value": float(mi.p_sim) if hasattr(mi, 'p_sim') else float(mi.p_norm),
            "z_score": float(mi.z_sim) if hasattr(mi, 'z_sim') else float(mi.z_norm),
            "interpretation": _interpret_morans_i(mi.I, mi.p_norm),
            "expected_i": float(mi.EI),
            "n": n
        }
        
    except ImportError:
        logger.warning("ESDA not available, using manual calculation")
        return _calculate_morans_i_manual(values, weights_matrix)
    except Exception as e:
        logger.warning(f"ESDA calculation failed: {e}, using manual calculation")
        return _calculate_morans_i_manual(values, weights_matrix)


def _calculate_morans_i_manual(
    values: np.ndarray,
    weights: np.ndarray
) -> Dict:
    """Manual implementation of Moran's I calculation."""
    n = len(values)
    mean_val = np.mean(values)
    
    # Deviations from mean
    z = values - mean_val
    
    # Calculate Moran's I
    numerator = 0.0
    for i in range(n):
        for j in range(n):
            numerator += weights[i, j] * z[i] * z[j]
    
    denominator = np.sum(z ** 2)
    w_sum = np.sum(weights)
    
    if denominator == 0 or w_sum == 0:
        return {
            "morans_i": 0.0,
            "p_value": 1.0,
            "z_score": 0.0,
            "interpretation": "No variance in data",
            "expected_i": -1 / (n - 1),
            "n": n
        }
    
    I = (n / w_sum) * (numerator / denominator)
    
    # Expected value under null hypothesis
    EI = -1 / (n - 1)
    
    # Variance (simplified)
    S0 = w_sum
    S1 = 0.5 * np.sum((weights + weights.T) ** 2)
    S2 = np.sum(np.sum(weights, axis=1) ** 2)
    
    k = (np.sum(z ** 4) / n) / ((np.sum(z ** 2) / n) ** 2)
    
    # Variance under normality assumption
    var_I = (n ** 2 * S1 - n * S2 + 3 * S0 ** 2) / ((n ** 2 - 1) * S0 ** 2) - EI ** 2
    
    if var_I > 0:
        z_score = (I - EI) / np.sqrt(var_I)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
    else:
        z_score = 0.0
        p_value = 1.0
    
    return {
        "morans_i": float(I),
        "p_value": float(p_value),
        "z_score": float(z_score),
        "interpretation": _interpret_morans_i(I, p_value),
        "expected_i": float(EI),
        "n": n
    }


def _interpret_morans_i(I: float, p_value: float) -> str:
    """Generate human-readable interpretation of Moran's I."""
    significance = "statistically significant" if p_value < 0.05 else "not statistically significant"
    
    if I > 0.3:
        pattern = "strong positive spatial autocorrelation (clustering of similar values)"
    elif I > 0.1:
        pattern = "moderate positive spatial autocorrelation"
    elif I > 0:
        pattern = "weak positive spatial autocorrelation"
    elif I > -0.1:
        pattern = "random spatial pattern (no autocorrelation)"
    elif I > -0.3:
        pattern = "moderate negative spatial autocorrelation (dispersed pattern)"
    else:
        pattern = "strong negative spatial autocorrelation (checkerboard pattern)"
    
    return f"Shows {pattern}. Result is {significance} (p={p_value:.4f})."


def detect_hotspots_getis_ord(
    gdf: gpd.GeoDataFrame,
    value_column: str = "penetration_rate",
    weights_matrix: Optional[np.ndarray] = None,
    significance_level: float = 0.05
) -> gpd.GeoDataFrame:
    """
    Detect hotspots and coldspots using Getis-Ord Gi* statistic.
    
    Gi* identifies statistically significant spatial clusters of high values
    (hotspots) and low values (coldspots).
    
    Args:
        gdf: GeoDataFrame with values to analyze
        value_column: Column containing the values to analyze
        weights_matrix: Optional NxN spatial weights matrix
        significance_level: Threshold for statistical significance (default 0.05)
        
    Returns:
        GeoDataFrame with additional columns:
        - gi_z_score: Gi* z-score for each region
        - gi_p_value: P-value for each region
        - classification: 'hotspot', 'coldspot', or 'neutral'
        - confidence_level: '99%', '95%', '90%', or 'not_significant'
        
    Example:
        >>> gdf = geo.join_enrollment_data(enrollment_df)
        >>> result = detect_hotspots_getis_ord(gdf)
        >>> hotspots = result[result['classification'] == 'hotspot']
        >>> print(f"Found {len(hotspots)} hotspots")
    """
    if value_column not in gdf.columns:
        raise ValueError(f"Column '{value_column}' not found in GeoDataFrame")
    
    result = gdf.copy()
    values = result[value_column].values.astype(float)
    n = len(values)
    
    if n < 3:
        result['gi_z_score'] = 0.0
        result['gi_p_value'] = 1.0
        result['classification'] = 'neutral'
        result['confidence_level'] = 'not_significant'
        return result
    
    # Generate weights matrix if not provided
    if weights_matrix is None:
        weights_matrix = _generate_simple_weights(gdf)
    
    try:
        # Try using ESDA for precise calculation
        from esda.getisord import G_Local
        from libpysal.weights import W
        
        # Convert to PySAL weights
        neighbors = {}
        weights_dict = {}
        for i in range(n):
            neighbor_list = []
            weight_list = []
            for j in range(n):
                if weights_matrix[i, j] > 0:
                    neighbor_list.append(j)
                    weight_list.append(weights_matrix[i, j])
            neighbors[i] = neighbor_list
            weights_dict[i] = weight_list
        
        w = W(neighbors, weights_dict)
        gi = G_Local(values, w, star=True)
        
        result['gi_z_score'] = gi.Zs
        result['gi_p_value'] = gi.p_sim if hasattr(gi, 'p_sim') else 2 * (1 - stats.norm.cdf(np.abs(gi.Zs)))
        
    except ImportError:
        logger.warning("ESDA not available, using manual Gi* calculation")
        z_scores, p_values = _calculate_gi_star_manual(values, weights_matrix)
        result['gi_z_score'] = z_scores
        result['gi_p_value'] = p_values
    except Exception as e:
        logger.warning(f"ESDA Gi* calculation failed: {e}, using manual calculation")
        z_scores, p_values = _calculate_gi_star_manual(values, weights_matrix)
        result['gi_z_score'] = z_scores
        result['gi_p_value'] = p_values
    
    # Classify regions
    result['classification'] = result.apply(
        lambda row: _classify_gi_star(row['gi_z_score'], row['gi_p_value'], significance_level),
        axis=1
    )
    
    result['confidence_level'] = result.apply(
        lambda row: _get_confidence_level(row['gi_p_value']),
        axis=1
    )
    
    return result


def _calculate_gi_star_manual(
    values: np.ndarray,
    weights: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """Manual implementation of Getis-Ord Gi* calculation."""
    n = len(values)
    mean_val = np.mean(values)
    std_val = np.std(values)
    
    z_scores = np.zeros(n)
    p_values = np.zeros(n)
    
    for i in range(n):
        # Include self in Gi* calculation
        w_i = weights[i].copy()
        w_i[i] = 1.0  # Self-weight for Gi*
        
        numerator = np.sum(w_i * values) - mean_val * np.sum(w_i)
        
        w_sum = np.sum(w_i)
        w_sum_sq = np.sum(w_i ** 2)
        
        denominator = std_val * np.sqrt((n * w_sum_sq - w_sum ** 2) / (n - 1))
        
        if denominator > 0:
            z_scores[i] = numerator / denominator
            p_values[i] = 2 * (1 - stats.norm.cdf(abs(z_scores[i])))
        else:
            z_scores[i] = 0.0
            p_values[i] = 1.0
    
    return z_scores, p_values


def _classify_gi_star(z_score: float, p_value: float, significance_level: float) -> str:
    """Classify a region based on Gi* z-score and p-value."""
    if p_value > significance_level:
        return 'neutral'
    elif z_score > 1.96:  # Positive significant
        return 'hotspot'
    elif z_score < -1.96:  # Negative significant
        return 'coldspot'
    else:
        return 'neutral'


def _get_confidence_level(p_value: float) -> str:
    """Get confidence level from p-value."""
    if p_value <= 0.01:
        return '99%'
    elif p_value <= 0.05:
        return '95%'
    elif p_value <= 0.10:
        return '90%'
    else:
        return 'not_significant'


def detect_anomalies(
    gdf: gpd.GeoDataFrame,
    value_column: str = "penetration_rate",
    threshold: float = 2.0
) -> List[Dict]:
    """
    Detect regions with anomalous values (>threshold std deviations from mean).
    
    Args:
        gdf: GeoDataFrame with values to analyze
        value_column: Column containing the values to analyze
        threshold: Number of standard deviations for anomaly detection
        
    Returns:
        List of dicts, each containing:
        - region: Name of the region
        - value: Observed value
        - z_score: How many std deviations from mean
        - severity: 'critical' (>3), 'high' (>2.5), 'medium' (>2)
        - direction: 'above' or 'below' mean
        
    Example:
        >>> anomalies = detect_anomalies(gdf, threshold=2.0)
        >>> for a in anomalies:
        ...     print(f"{a['region']}: z={a['z_score']:.2f} ({a['severity']})")
    """
    if value_column not in gdf.columns:
        raise ValueError(f"Column '{value_column}' not found in GeoDataFrame")
    
    values = gdf[value_column].values.astype(float)
    mean_val = np.mean(values)
    std_val = np.std(values)
    
    if std_val == 0:
        return []
    
    # Get region name column
    region_col = None
    for col in ['state_name', 'normalized_state', 'NAME_1', 'name']:
        if col in gdf.columns:
            region_col = col
            break
    
    if region_col is None:
        region_col = gdf.columns[0]
    
    anomalies = []
    
    for idx, row in gdf.iterrows():
        value = row[value_column]
        z = (value - mean_val) / std_val
        
        if abs(z) >= threshold:
            severity = 'critical' if abs(z) >= 3.0 else ('high' if abs(z) >= 2.5 else 'medium')
            direction = 'above' if z > 0 else 'below'
            
            anomalies.append({
                "region": row[region_col],
                "value": float(value),
                "z_score": float(z),
                "severity": severity,
                "direction": direction,
                "mean": float(mean_val),
                "std": float(std_val),
                "threshold": threshold
            })
    
    # Sort by absolute z-score (most anomalous first)
    anomalies.sort(key=lambda x: abs(x['z_score']), reverse=True)
    
    return anomalies


def decompose_time_series(
    state_df: pd.DataFrame,
    value_column: str = "value",
    date_column: str = "date",
    period: int = 12
) -> Dict:
    """
    Decompose time series into trend, seasonal, and residual components.
    
    Uses additive decomposition: Y = Trend + Seasonal + Residual
    
    Args:
        state_df: DataFrame with time series data
        value_column: Column containing values
        date_column: Column containing dates
        period: Seasonal period (12 for monthly data)
        
    Returns:
        Dict containing:
        - trend: List of trend values
        - seasonal: List of seasonal values
        - residual: List of residual values
        - dates: List of dates
        - summary: Statistical summary
        
    Example:
        >>> from services.spatial_analysis import decompose_time_series
        >>> result = decompose_time_series(state_data)
        >>> print(f"Trend direction: {result['summary']['trend_direction']}")
    """
    df = state_df.copy()
    
    # Ensure date is datetime
    if date_column in df.columns:
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values(date_column)
    
    values = df[value_column].values.astype(float)
    n = len(values)
    
    if n < period * 2:
        # Not enough data for full decomposition
        return {
            "trend": values.tolist(),
            "seasonal": [0.0] * n,
            "residual": [0.0] * n,
            "dates": df[date_column].astype(str).tolist() if date_column in df.columns else list(range(n)),
            "summary": {
                "trend_direction": "insufficient_data",
                "seasonality_strength": 0.0,
                "mean_value": float(np.mean(values)),
                "std_value": float(np.std(values))
            }
        }
    
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # Perform decomposition
        result = seasonal_decompose(values, model='additive', period=period, extrapolate_trend='freq')
        
        trend = result.trend
        seasonal = result.seasonal
        residual = result.resid
        
        # Handle NaN values at edges
        trend = np.nan_to_num(trend, nan=np.nanmean(trend))
        seasonal = np.nan_to_num(seasonal, nan=0.0)
        residual = np.nan_to_num(residual, nan=0.0)
        
    except ImportError:
        logger.warning("statsmodels not available, using simple moving average decomposition")
        trend, seasonal, residual = _simple_decompose(values, period)
    except Exception as e:
        logger.warning(f"Decomposition failed: {e}, using simple moving average")
        trend, seasonal, residual = _simple_decompose(values, period)
    
    # Calculate trend direction
    if len(trend) >= 2:
        trend_slope = (trend[-1] - trend[0]) / max(1, len(trend) - 1)
        if trend_slope > 0.01 * np.mean(values):
            trend_direction = "increasing"
        elif trend_slope < -0.01 * np.mean(values):
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"
    else:
        trend_direction = "unknown"
    
    # Calculate seasonality strength
    if np.std(seasonal) > 0:
        seasonality_strength = np.std(seasonal) / (np.std(seasonal) + np.std(residual))
    else:
        seasonality_strength = 0.0
    
    return {
        "trend": trend.tolist(),
        "seasonal": seasonal.tolist(),
        "residual": residual.tolist(),
        "dates": df[date_column].astype(str).tolist() if date_column in df.columns else list(range(n)),
        "summary": {
            "trend_direction": trend_direction,
            "seasonality_strength": float(seasonality_strength),
            "mean_value": float(np.mean(values)),
            "std_value": float(np.std(values)),
            "min_value": float(np.min(values)),
            "max_value": float(np.max(values))
        }
    }


def _simple_decompose(
    values: np.ndarray,
    period: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simple decomposition using moving average."""
    n = len(values)
    
    # Trend: centered moving average
    trend = np.zeros(n)
    half_period = period // 2
    
    for i in range(n):
        start = max(0, i - half_period)
        end = min(n, i + half_period + 1)
        trend[i] = np.mean(values[start:end])
    
    # Detrended
    detrended = values - trend
    
    # Seasonal: average of detrended values for each period position
    seasonal = np.zeros(n)
    for i in range(period):
        positions = list(range(i, n, period))
        if positions:
            seasonal_mean = np.mean(detrended[positions])
            for pos in positions:
                seasonal[pos] = seasonal_mean
    
    # Residual
    residual = values - trend - seasonal
    
    return trend, seasonal, residual


def _generate_simple_weights(gdf: gpd.GeoDataFrame) -> np.ndarray:
    """Generate simple distance-based weights matrix."""
    n = len(gdf)
    weights = np.zeros((n, n))
    
    if 'geometry' not in gdf.columns:
        # No geometry, use equal weights
        for i in range(n):
            for j in range(n):
                if i != j:
                    weights[i, j] = 1.0 / (n - 1)
        return weights
    
    # Use centroids for distance calculation
    try:
        centroids = gdf.geometry.centroid
        
        for i in range(n):
            distances = []
            for j in range(n):
                if i != j:
                    dist = centroids.iloc[i].distance(centroids.iloc[j])
                    distances.append((j, dist))
            
            # Use 5 nearest neighbors
            distances.sort(key=lambda x: x[1])
            k_nearest = distances[:min(5, len(distances))]
            
            if k_nearest:
                # Inverse distance weighting
                for j, dist in k_nearest:
                    weights[i, j] = 1.0 / (len(k_nearest))
    except Exception as e:
        logger.warning(f"Distance calculation failed: {e}, using equal weights")
        for i in range(n):
            for j in range(n):
                if i != j:
                    weights[i, j] = 1.0 / (n - 1)
    
    return weights


def get_summary_statistics(
    gdf: gpd.GeoDataFrame,
    value_column: str = "penetration_rate"
) -> Dict:
    """Get summary statistics for the GeoDataFrame."""
    values = gdf[value_column].values.astype(float)
    
    return {
        "count": int(len(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "q25": float(np.percentile(values, 25)),
        "q75": float(np.percentile(values, 75)),
        "iqr": float(np.percentile(values, 75) - np.percentile(values, 25))
    }
