"""
Geospatial Hotspot Detection API Routes
FastAPI router for spatial analysis, hotspot detection, and forecasting endpoints.
"""
import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hotspots", tags=["Geospatial Hotspot Detection"])


# ----- Request/Response Models -----

class SpatialAnalysisRequest(BaseModel):
    """Request model for spatial analysis."""
    states: Optional[List[str]] = Field(default=None, description="List of states to analyze (all if empty)")
    date_range: Optional[Dict[str, str]] = Field(default=None, description="Date range: {start: 'YYYY-MM', end: 'YYYY-MM'}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "states": ["Maharashtra", "Bihar", "Uttar Pradesh"],
                "date_range": {"start": "2024-01", "end": "2024-12"}
            }
        }


class AnomalyRequest(BaseModel):
    """Request model for anomaly detection."""
    threshold: float = Field(default=2.0, ge=1.0, le=5.0, description="Standard deviations for anomaly threshold")
    granularity: str = Field(default="state", description="Analysis granularity: 'state' or 'district'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "threshold": 2.0,
                "granularity": "state"
            }
        }


class ForecastRequest(BaseModel):
    """Request model for forecasting."""
    horizon_months: int = Field(default=6, ge=1, le=24, description="Forecast horizon in months")
    
    class Config:
        json_schema_extra = {
            "example": {
                "horizon_months": 6
            }
        }


class ScenarioRequest(BaseModel):
    """Request model for scenario comparison."""
    states: List[str] = Field(description="States to model")
    intervention_params: Dict = Field(
        default={"boost_percent": 10, "start_month": 0, "duration_months": 3},
        description="Intervention parameters"
    )
    horizon_months: int = Field(default=6, ge=1, le=24)
    
    class Config:
        json_schema_extra = {
            "example": {
                "states": ["Bihar", "Jharkhand"],
                "intervention_params": {
                    "boost_percent": 15,
                    "start_month": 0,
                    "duration_months": 3
                },
                "horizon_months": 6
            }
        }


# ----- Helper Functions -----

def _load_enrollment_data() -> pd.DataFrame:
    """
    Load enrollment data from the real UIDAI data.gov.in API.
    Falls back to synthetic data if API fails.
    """
    try:
        from services.uidai_api_fetcher import fetch_state_summary
        
        logger.info("Fetching real enrollment data from UIDAI API...")
        df = fetch_state_summary()
        
        if not df.empty and len(df) > 0:
            logger.info(f"Successfully loaded {len(df)} states from UIDAI API")
            
            # Ensure required columns exist
            if "penetration_rate" not in df.columns:
                df["penetration_rate"] = 0.85
            if "total_enrollments" not in df.columns:
                df["total_enrollments"] = 1000000
            
            # Add date column for time series compatibility
            df["date"] = pd.Timestamp.now().strftime("%Y-%m")
            
            return df
        else:
            logger.warning("Empty data from API, using fallback")
            return _generate_fallback_data()
            
    except Exception as e:
        logger.error(f"Failed to fetch from UIDAI API: {e}")
        return _generate_fallback_data()


def _generate_fallback_data() -> pd.DataFrame:
    """Generate fallback synthetic data when API fails."""
    np.random.seed(42)
    states = [
        "Uttar Pradesh", "Maharashtra", "Bihar", "West Bengal", "Madhya Pradesh",
        "Tamil Nadu", "Rajasthan", "Karnataka", "Gujarat", "Andhra Pradesh",
        "Odisha", "Kerala", "Jharkhand", "Assam", "Punjab", "Chhattisgarh",
        "Haryana", "NCT of Delhi", "Jammu & Kashmir", "Uttarakhand",
        "Himachal Pradesh", "Tripura", "Meghalaya", "Manipur", "Nagaland",
        "Goa", "Arunachal Pradesh", "Puducherry", "Mizoram", "Sikkim", "Telangana", "Ladakh"
    ]
    
    base_rates = {
        "Maharashtra": 0.95, "Tamil Nadu": 0.94, "Gujarat": 0.93, "Karnataka": 0.92,
        "Andhra Pradesh": 0.91, "Kerala": 0.96, "Haryana": 0.90, "Punjab": 0.89,
        "NCT of Delhi": 0.88, "Goa": 0.97, "Puducherry": 0.93, "Telangana": 0.90,
        "Uttar Pradesh": 0.85, "Madhya Pradesh": 0.84, "Rajasthan": 0.83,
        "West Bengal": 0.82, "Odisha": 0.81, "Chhattisgarh": 0.80,
        "Bihar": 0.75, "Jharkhand": 0.74, "Assam": 0.72,
        "Uttarakhand": 0.86, "Himachal Pradesh": 0.88, "Jammu & Kashmir": 0.78,
        "Tripura": 0.70, "Meghalaya": 0.68, "Manipur": 0.65,
        "Nagaland": 0.63, "Arunachal Pradesh": 0.60, "Mizoram": 0.67, "Sikkim": 0.85,
        "Ladakh": 0.55
    }
    
    data = []
    dates = pd.date_range("2024-01", periods=12, freq="M")
    
    for state in states:
        base_rate = base_rates.get(state, 0.80)
        for date in dates:
            rate = base_rate + np.random.normal(0, 0.02)
            enrollments = int(rate * np.random.randint(100000, 5000000))
            data.append({
                "state": state,
                "date": date.strftime("%Y-%m"),
                "penetration_rate": max(0.5, min(1.0, rate)),
                "total_enrollments": enrollments
            })
    
    return pd.DataFrame(data)


def _get_geo_processor():
    """Get or create GeoProcessor instance."""
    try:
        from services.geo_processor import GeoProcessor
        return GeoProcessor()
    except Exception as e:
        logger.warning(f"Could not load GeoProcessor: {e}")
        return None


# ----- API Endpoints -----

@router.post("/spatial-analysis")
async def spatial_analysis(request: SpatialAnalysisRequest) -> Dict:
    """
    Perform spatial analysis including Moran's I and hotspot detection.
    
    Returns Moran's I statistic for global spatial autocorrelation and
    GeoJSON with z-scores for each region.
    
    **Sample Request:**
    ```json
    {
        "states": ["Maharashtra", "Bihar"],
        "date_range": {"start": "2024-01", "end": "2024-12"}
    }
    ```
    
    **Sample Response:**
    ```json
    {
        "morans_i": {
            "morans_i": 0.432,
            "p_value": 0.0012,
            "interpretation": "Strong positive spatial autocorrelation"
        },
        "hotspots": [...],
        "coldspots": [...],
        "geojson": {...}
    }
    ```
    """
    try:
        from services.spatial_analysis import calculate_morans_i, detect_hotspots_getis_ord, detect_anomalies
        from services.geo_processor import GeoProcessor
        
        # Load sample data
        df = _load_enrollment_data()
        
        # Filter by states if specified
        if request.states:
            df = df[df['state'].isin(request.states)]
        
        # Aggregate to latest values per state
        latest = df.groupby('state').agg({
            'penetration_rate': 'mean',
            'total_enrollments': 'sum'
        }).reset_index()
        
        # Load GeoJSON and join data
        geo = GeoProcessor()
        try:
            gdf = geo.join_enrollment_data(latest, state_column='state', value_column='total_enrollments')
        except FileNotFoundError:
            # If no GeoJSON available, create synthetic GeoDataFrame
            import geopandas as gpd
            from shapely.geometry import Point
            
            # Create point geometries for each state (simplified)
            points = [Point(np.random.uniform(68, 97), np.random.uniform(8, 37)) for _ in range(len(latest))]
            gdf = gpd.GeoDataFrame(latest, geometry=points)
            gdf['penetration_rate'] = latest['penetration_rate']
        
        # Calculate Moran's I
        morans_result = calculate_morans_i(gdf, value_column='penetration_rate')
        
        # Detect hotspots
        hotspot_gdf = detect_hotspots_getis_ord(gdf, value_column='penetration_rate')
        
        # Extract hotspots and coldspots
        state_col = 'state' if 'state' in hotspot_gdf.columns else 'state_name' if 'state_name' in hotspot_gdf.columns else hotspot_gdf.columns[0]
        
        hotspots = hotspot_gdf[hotspot_gdf['classification'] == 'hotspot'][
            [state_col, 'penetration_rate', 'gi_z_score', 'confidence_level']
        ].rename(columns={state_col: 'state'}).to_dict(orient='records')
        
        coldspots = hotspot_gdf[hotspot_gdf['classification'] == 'coldspot'][
            [state_col, 'penetration_rate', 'gi_z_score', 'confidence_level']
        ].rename(columns={state_col: 'state'}).to_dict(orient='records')
        
        # Convert to GeoJSON for frontend with proper serialization
        geojson = None
        try:
            # Ensure all required properties are included
            properties_to_include = [state_col, 'penetration_rate', 'gi_z_score', 'classification', 'confidence_level']
            available_props = [p for p in properties_to_include if p in hotspot_gdf.columns]
            
            # Create a clean GeoDataFrame with only needed columns
            export_gdf = hotspot_gdf[available_props + ['geometry']].copy()
            export_gdf = export_gdf.rename(columns={state_col: 'state'})
            
            # Convert to GeoJSON dict
            geojson_str = export_gdf.to_json()
            geojson = json.loads(geojson_str)
            
            logger.info(f"Successfully generated GeoJSON with {len(geojson.get('features', []))} features")
        except Exception as e:
            logger.error(f"GeoJSON serialization failed: {e}")
            geojson = None
        
        return {
            "success": True,
            "morans_i": morans_result,
            "hotspots": hotspots,
            "coldspots": coldspots,
            "summary": {
                "total_regions": len(gdf),
                "hotspot_count": len(hotspots),
                "coldspot_count": len(coldspots),
                "neutral_count": len(gdf) - len(hotspots) - len(coldspots)
            },
            "geojson": geojson
        }
        
    except Exception as e:
        logger.error(f"Spatial analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Spatial analysis failed: {str(e)}")


@router.post("/anomalies")
async def detect_anomalies_endpoint(request: AnomalyRequest) -> Dict:
    """
    Detect regions with anomalous enrollment patterns.
    
    Identifies regions where penetration rates deviate significantly
    (>threshold std deviations) from the national mean.
    
    **Sample Response:**
    ```json
    {
        "anomalies": [
            {
                "region": "Nagaland",
                "value": 0.63,
                "z_score": -2.45,
                "severity": "high",
                "direction": "below"
            }
        ]
    }
    ```
    """
    try:
        from services.spatial_analysis import detect_anomalies
        from services.geo_processor import GeoProcessor
        import geopandas as gpd
        from shapely.geometry import Point
        
        # Load sample data
        df = _load_enrollment_data()
        latest = df.groupby('state').agg({
            'penetration_rate': 'mean',
            'total_enrollments': 'sum'
        }).reset_index()
        
        # Create GeoDataFrame
        try:
            geo = GeoProcessor()
            gdf = geo.join_enrollment_data(latest, state_column='state', value_column='total_enrollments')
        except FileNotFoundError:
            points = [Point(0, 0) for _ in range(len(latest))]
            gdf = gpd.GeoDataFrame(latest, geometry=points)
            gdf['state_name'] = latest['state']
        
        # Detect anomalies
        anomalies = detect_anomalies(gdf, value_column='penetration_rate', threshold=request.threshold)
        
        return {
            "success": True,
            "threshold": request.threshold,
            "granularity": request.granularity,
            "anomalies": anomalies,
            "summary": {
                "total_anomalies": len(anomalies),
                "critical": len([a for a in anomalies if a['severity'] == 'critical']),
                "high": len([a for a in anomalies if a['severity'] == 'high']),
                "medium": len([a for a in anomalies if a['severity'] == 'medium'])
            }
        }
        
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heatmap/{state}")
async def get_heatmap(
    state: str,
    include_districts: bool = Query(False, description="Include district-level data")
) -> Dict:
    """
    Get heatmap GeoJSON data for a specific state.
    
    Returns GeoJSON with penetration rates and z-scores for choropleth visualization.
    """
    try:
        from services.geo_processor import GeoProcessor
        from services.spatial_analysis import detect_hotspots_getis_ord
        import geopandas as gpd
        from shapely.geometry import Point
        
        # Load sample data for the state
        df = _load_enrollment_data()
        state_data = df[df['state'].str.lower() == state.lower()]
        
        if state_data.empty:
            raise HTTPException(status_code=404, detail=f"State '{state}' not found")
        
        latest = state_data.groupby('state').agg({
            'penetration_rate': 'mean',
            'total_enrollments': 'sum'
        }).reset_index()
        
        # Try to get GeoJSON for state
        try:
            geo = GeoProcessor()
            state_geojson = geo.get_state_geojson(state)
        except Exception:
            state_geojson = None
        
        return {
            "success": True,
            "state": state,
            "data": {
                "penetration_rate": float(latest['penetration_rate'].iloc[0]),
                "total_enrollments": int(latest['total_enrollments'].iloc[0])
            },
            "geojson": state_geojson,
            "time_series": state_data[['date', 'penetration_rate', 'total_enrollments']].to_dict(orient='records')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Heatmap generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----- Forecast Router -----

forecast_router = APIRouter(prefix="/api/forecast", tags=["Forecasting"])


@forecast_router.post("/state/{state_name}")
async def forecast_state(state_name: str, request: ForecastRequest) -> Dict:
    """
    Generate enrollment forecast for a specific state.
    
    Returns point forecasts with 95% confidence intervals for the specified horizon.
    
    **Sample Response:**
    ```json
    {
        "state": "Maharashtra",
        "forecast": {
            "forecast": [1200000, 1250000, 1300000, 1350000, 1400000, 1450000],
            "lower_ci": [1100000, 1120000, 1140000, 1160000, 1180000, 1200000],
            "upper_ci": [1300000, 1380000, 1460000, 1540000, 1620000, 1700000],
            "dates": ["2025-02", "2025-03", "2025-04", "2025-05", "2025-06", "2025-07"]
        }
    }
    ```
    """
    try:
        from services.forecasting import train_sarima_model, forecast_6_months
        
        # Load sample data
        df = _load_enrollment_data()
        state_data = df[df['state'].str.lower() == state_name.lower()]
        
        if state_data.empty:
            raise HTTPException(status_code=404, detail=f"State '{state_name}' not found")
        
        # Prepare time series
        ts = state_data.groupby('date')['total_enrollments'].sum()
        
        # Train model
        model_result = train_sarima_model(ts, auto=True)
        
        # Generate forecast
        forecast = forecast_6_months(model_result, horizon_months=request.horizon_months)
        
        return {
            "success": True,
            "state": state_name,
            "forecast": forecast,
            "model_info": {
                "order": model_result.get("order"),
                "aic": model_result.get("aic"),
                "diagnostics": model_result.get("diagnostics")
            },
            "historical": {
                "dates": state_data['date'].tolist(),
                "values": state_data['total_enrollments'].tolist()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecast error for {state_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@forecast_router.post("/scenario-comparison")
async def scenario_comparison(request: ScenarioRequest) -> Dict:
    """
    Compare baseline vs intervention scenarios for specified states.
    
    Models the impact of policy interventions (e.g., mobile enrollment camps)
    on projected enrollment numbers.
    
    **Sample Response:**
    ```json
    {
        "states": {
            "Bihar": {
                "baseline": {...},
                "intervention": {...},
                "cumulative_impact": 125000
            }
        }
    }
    ```
    """
    try:
        from services.forecasting import scenario_modeling
        
        # Load sample data
        df = _load_enrollment_data()
        
        results = {}
        for state in request.states:
            state_data = df[df['state'].str.lower() == state.lower()]
            
            if state_data.empty:
                results[state] = {"error": f"State '{state}' not found"}
                continue
            
            scenario = scenario_modeling(
                state=state,
                historical_data=state_data,
                intervention_params=request.intervention_params,
                horizon_months=request.horizon_months
            )
            results[state] = scenario
        
        # Calculate total impact across all states
        total_impact = sum(
            r.get('cumulative_impact', 0) 
            for r in results.values() 
            if isinstance(r, dict) and 'cumulative_impact' in r
        )
        
        return {
            "success": True,
            "states": results,
            "intervention_params": request.intervention_params,
            "total_impact": total_impact,
            "summary": {
                "states_analyzed": len(request.states),
                "states_with_data": len([r for r in results.values() if 'error' not in r])
            }
        }
        
    except Exception as e:
        logger.error(f"Scenario comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
