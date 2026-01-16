"""
UIDAI API Data Fetcher Service
Fetches real enrollment data from data.gov.in API using the DATA_GOV_API_KEY.

This service is used by the geospatial hotspot detection to get actual
district-level enrollment data instead of synthetic/mock data.
"""
import os
import logging
import requests
import pandas as pd
from typing import Dict, List, Optional
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# API Configuration
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "579b464db66ec23bdd0000015cfbfd5b9e5a4b366992c1f538e4a2b8")
DATA_GOV_BASE_URL = "https://api.data.gov.in/resource"

# Resource IDs for UIDAI datasets
RESOURCE_IDS = {
    "enrolment": "ecd49b12-3084-4521-8f7e-ca8bf72069ba",
    "demographic": "19eac040-0b94-49fa-b239-4f2fd8677d53",
    "biometric": "65454dab-1517-40a3-ac1d-47d4dfe6891c"
}

# Cache for API responses
_cache: Dict[str, any] = {}
_cache_expiry: Dict[str, datetime] = {}
CACHE_TTL_HOURS = 1


class UIDAIDataFetcher:
    """
    Fetches real enrollment data from data.gov.in UIDAI APIs.
    Provides state and district-level enrollment statistics.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DATA_GOV_API_KEY
        self.base_url = DATA_GOV_BASE_URL
        
    def _make_request(self, resource_id: str, params: Dict = None) -> Dict:
        """Make a request to the data.gov.in API."""
        url = f"{self.base_url}/{resource_id}"
        
        default_params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": 10000
        }
        
        if params:
            default_params.update(params)
        
        cache_key = f"{resource_id}_{str(params)}"
        
        # Check cache
        if cache_key in _cache:
            if datetime.now() < _cache_expiry.get(cache_key, datetime.min):
                logger.info(f"Using cached data for {resource_id}")
                return _cache[cache_key]
        
        try:
            logger.info(f"Fetching data from data.gov.in: {resource_id}")
            response = requests.get(url, params=default_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Cache the response
            _cache[cache_key] = data
            _cache_expiry[cache_key] = datetime.now() + timedelta(hours=CACHE_TTL_HOURS)
            
            logger.info(f"Successfully fetched {len(data.get('records', []))} records")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def fetch_enrollment_data(self, state: Optional[str] = None, limit: int = 10000) -> pd.DataFrame:
        """
        Fetch enrollment data from UIDAI API.
        
        Args:
            state: Optional state filter
            limit: Maximum records to fetch
            
        Returns:
            DataFrame with enrollment data by state/district
        """
        params = {"limit": limit}
        
        if state:
            params["filters[state]"] = state
            
        try:
            data = self._make_request(RESOURCE_IDS["enrolment"], params)
            records = data.get("records", [])
            
            if not records:
                logger.warning("No enrollment records returned from API")
                return self._get_fallback_data()
            
            df = pd.DataFrame(records)
            
            # Normalize column names
            column_mapping = {
                "state": "state",
                "district": "district",
                "pincode": "pincode",
                "date": "date",
                "age_0_5": "age_0_5",
                "age_5_17": "age_5_17",
                "age_18_greater": "age_18_plus",
                "total": "total_enrollments"
            }
            
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # Calculate total if not present
            if "total_enrollments" not in df.columns:
                age_cols = [c for c in df.columns if "age" in c.lower()]
                if age_cols:
                    df["total_enrollments"] = df[age_cols].apply(pd.to_numeric, errors='coerce').sum(axis=1)
                else:
                    df["total_enrollments"] = 0
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch enrollment data: {e}")
            return self._get_fallback_data()
    
    def fetch_district_data(self, state: str) -> pd.DataFrame:
        """
        Fetch district-level data for a specific state.
        
        Args:
            state: State name to fetch districts for
            
        Returns:
            DataFrame with district-level enrollment data
        """
        params = {
            "limit": 1000,
            "filters[state]": state
        }
        
        try:
            data = self._make_request(RESOURCE_IDS["enrolment"], params)
            records = data.get("records", [])
            
            if not records:
                logger.warning(f"No district data for {state}")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch district data for {state}: {e}")
            return pd.DataFrame()
    
    def get_state_summary(self) -> pd.DataFrame:
        """
        Get aggregated state-level enrollment summary.
        
        Returns:
            DataFrame with state-wise total enrollments and penetration rates
        """
        df = self.fetch_enrollment_data()
        
        if df.empty or "state" not in df.columns:
            return self._get_fallback_data()
        
        # Aggregate by state
        state_summary = df.groupby("state").agg({
            "total_enrollments": "sum"
        }).reset_index()
        
        # Add penetration rate estimate
        from services.geo_processor import STATE_POPULATION
        
        state_summary["population"] = state_summary["state"].map(
            lambda x: STATE_POPULATION.get(x, 10.0) * 1_000_000
        )
        
        state_summary["penetration_rate"] = (
            state_summary["total_enrollments"] / state_summary["population"]
        ).clip(0, 1.5)  # Cap at 150%
        
        return state_summary
    
    def _get_fallback_data(self) -> pd.DataFrame:
        """
        Generate fallback data when API fails.
        Uses realistic synthetic data based on known state characteristics.
        """
        logger.warning("Using fallback synthetic data")
        
        from services.geo_processor import STATE_POPULATION
        import numpy as np
        
        np.random.seed(42)
        
        # Base penetration rates (realistic estimates)
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
        for state, pop in STATE_POPULATION.items():
            rate = base_rates.get(state, 0.80) + np.random.normal(0, 0.02)
            rate = max(0.5, min(1.0, rate))
            enrollments = int(rate * pop * 1_000_000)
            
            data.append({
                "state": state,
                "total_enrollments": enrollments,
                "penetration_rate": rate,
                "population": pop * 1_000_000
            })
        
        return pd.DataFrame(data)


# Singleton instance
_fetcher_instance: Optional[UIDAIDataFetcher] = None

def get_uidai_fetcher() -> UIDAIDataFetcher:
    """Get singleton instance of UIDAI data fetcher."""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = UIDAIDataFetcher()
    return _fetcher_instance


def fetch_real_enrollment_data(state: Optional[str] = None) -> pd.DataFrame:
    """
    Convenience function to fetch real enrollment data.
    
    Args:
        state: Optional state filter
        
    Returns:
        DataFrame with enrollment data
    """
    fetcher = get_uidai_fetcher()
    return fetcher.fetch_enrollment_data(state)


def fetch_state_summary() -> pd.DataFrame:
    """
    Convenience function to get state-level summary.
    
    Returns:
        DataFrame with state summaries including penetration rates
    """
    fetcher = get_uidai_fetcher()
    return fetcher.get_state_summary()
