"""
Geo Processor Service
Handles GeoJSON loading, name normalization, and penetration rate calculations
for the Geospatial Hotspot Detection system.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import shape

logger = logging.getLogger(__name__)

# Default paths
GEOJSON_DIR = Path(__file__).parent.parent / "data" / "geojson"
FALLBACK_GEOJSON = Path(__file__).parent.parent.parent / "python_backend" / "data" / "india-osm.geojson"

# State name normalization mapping (Aadhaar dataset -> GeoJSON)
STATE_NAME_MAPPING: Dict[str, str] = {
    "Andaman and Nicobar Islands": "Andaman and Nicobar",
    "Andaman & Nicobar": "Andaman and Nicobar",
    "Dadra and Nagar Haveli and Daman and Diu": "Dadra and Nagar Haveli",
    "Dadra & Nagar Haveli and Daman & Diu": "Dadra and Nagar Haveli",
    "Jammu and Kashmir": "Jammu & Kashmir",
    "Delhi": "NCT of Delhi",
    "National Capital Territory of Delhi": "NCT of Delhi",
    "Orissa": "Odisha",
    "Pondicherry": "Puducherry",
    "Uttaranchal": "Uttarakhand",
    "Chattisgarh": "Chhattisgarh",
    "Andhra Pradesh New": "Andhra Pradesh",
    "Telangana": "Telangana",  # Direct mapping
}

# Approximate population by state (Census 2011 estimates, in millions)
# Used for penetration rate calculations
STATE_POPULATION: Dict[str, float] = {
    "Uttar Pradesh": 199.8,
    "Maharashtra": 112.4,
    "Bihar": 104.1,
    "West Bengal": 91.3,
    "Madhya Pradesh": 72.6,
    "Tamil Nadu": 72.1,
    "Rajasthan": 68.5,
    "Karnataka": 61.1,
    "Gujarat": 60.4,
    "Andhra Pradesh": 49.4,
    "Odisha": 42.0,
    "Telangana": 35.0,
    "Kerala": 33.4,
    "Jharkhand": 33.0,
    "Assam": 31.2,
    "Punjab": 27.7,
    "Chhattisgarh": 25.5,
    "Haryana": 25.4,
    "NCT of Delhi": 16.8,
    "Jammu & Kashmir": 12.5,
    "Uttarakhand": 10.1,
    "Himachal Pradesh": 6.9,
    "Tripura": 3.7,
    "Meghalaya": 3.0,
    "Manipur": 2.9,
    "Nagaland": 2.0,
    "Goa": 1.5,
    "Arunachal Pradesh": 1.4,
    "Puducherry": 1.2,
    "Mizoram": 1.1,
    "Chandigarh": 1.1,
    "Sikkim": 0.6,
    "Andaman and Nicobar": 0.4,
    "Dadra and Nagar Haveli": 0.3,
    "Daman and Diu": 0.2,
    "Lakshadweep": 0.06,
    "Ladakh": 0.3,
}


class GeoProcessor:
    """
    Processor for geospatial data operations including:
    - Loading and parsing GeoJSON boundaries
    - Normalizing state/district names
    - Calculating Aadhaar penetration rates
    - Generating spatial weights matrices
    """
    
    def __init__(self, geojson_path: Optional[str] = None):
        """
        Initialize the GeoProcessor.
        
        Args:
            geojson_path: Path to India GeoJSON file. Uses default if not provided.
        """
        self.geojson_path = self._resolve_geojson_path(geojson_path)
        self._gdf: Optional[gpd.GeoDataFrame] = None
        self._weights_matrix: Optional[np.ndarray] = None
        
    def _resolve_geojson_path(self, custom_path: Optional[str] = None) -> Path:
        """Resolve the GeoJSON file path."""
        if custom_path:
            path = Path(custom_path)
            if path.exists():
                return path
            logger.warning(f"Custom GeoJSON path not found: {custom_path}")
        
        # Check default location
        default_path = GEOJSON_DIR / "india.geojson"
        if default_path.exists():
            return default_path
        
        # Check ml_backend/data/geojson for any geojson files
        alt_path = GEOJSON_DIR / "india_states.geojson"
        if alt_path.exists():
            return alt_path
            
        # Try fallback location (python_backend/data)
        if FALLBACK_GEOJSON.exists():
            logger.info(f"Using fallback GeoJSON: {FALLBACK_GEOJSON}")
            return FALLBACK_GEOJSON
        
        # Try alternative python_backend location
        alt_fallback = Path(__file__).parent.parent.parent / "python_backend" / "data" / "india-osm.geojson"
        if alt_fallback.exists():
            logger.info(f"Using python_backend GeoJSON: {alt_fallback}")
            return alt_fallback
            
        raise FileNotFoundError(
            f"No GeoJSON file found. Checked: {default_path}, {FALLBACK_GEOJSON}, {alt_fallback}"
        )
    
    def load_geojson(self, force_reload: bool = False) -> gpd.GeoDataFrame:
        """
        Load India GeoJSON and return as GeoDataFrame.
        
        Args:
            force_reload: Force reload even if already cached
            
        Returns:
            GeoDataFrame with state/district boundaries
            
        Example:
            >>> geo = GeoProcessor()
            >>> gdf = geo.load_geojson()
            >>> print(gdf.columns)
            ['NAME_1', 'geometry', ...]
        """
        if self._gdf is not None and not force_reload:
            return self._gdf
            
        logger.info(f"Loading GeoJSON from: {self.geojson_path}")
        self._gdf = gpd.read_file(self.geojson_path)
        
        # Standardize column names
        self._gdf = self._normalize_gdf_columns(self._gdf)
        
        # Ensure valid geometry
        self._gdf = self._gdf[self._gdf.geometry.is_valid]
        
        logger.info(f"Loaded {len(self._gdf)} geographic regions")
        return self._gdf
    
    def _normalize_gdf_columns(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Standardize column names in GeoDataFrame."""
        column_mapping = {}
        
        for col in gdf.columns:
            col_lower = col.lower()
            if 'name_1' in col_lower or col_lower == 'state':
                column_mapping[col] = 'state_name'
            elif 'name_2' in col_lower or col_lower == 'district':
                column_mapping[col] = 'district_name'
            elif 'name_0' in col_lower or col_lower == 'country':
                column_mapping[col] = 'country'
                
        if column_mapping:
            gdf = gdf.rename(columns=column_mapping)
            
        return gdf
    
    def normalize_state_name(self, name: str) -> str:
        """
        Normalize state name to match GeoJSON naming convention.
        
        Args:
            name: Raw state name from Aadhaar dataset
            
        Returns:
            Normalized state name
            
        Example:
            >>> geo = GeoProcessor()
            >>> geo.normalize_state_name("Andaman and Nicobar Islands")
            'Andaman and Nicobar'
        """
        if not name:
            return name
            
        # Clean the name
        cleaned = name.strip().title()
        
        # Check mapping
        if cleaned in STATE_NAME_MAPPING:
            return STATE_NAME_MAPPING[cleaned]
        if name in STATE_NAME_MAPPING:
            return STATE_NAME_MAPPING[name]
            
        return cleaned
    
    def calculate_penetration_rate(
        self, 
        enrollment_count: int, 
        state: str,
        population_override: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calculate Aadhaar penetration rate for a state.
        
        Args:
            enrollment_count: Number of Aadhaar enrollments
            state: State name
            population_override: Optional population in millions
            
        Returns:
            Tuple of (penetration_rate, population_in_millions)
            
        Example:
            >>> geo = GeoProcessor()
            >>> rate, pop = geo.calculate_penetration_rate(50000000, "Maharashtra")
            >>> print(f"Penetration: {rate:.1%}")
            Penetration: 44.5%
        """
        normalized_state = self.normalize_state_name(state)
        
        if population_override:
            population = population_override
        else:
            population = STATE_POPULATION.get(normalized_state, 10.0)  # Default 10M
            
        # Convert population to actual count (millions to units)
        population_count = population * 1_000_000
        
        rate = enrollment_count / population_count if population_count > 0 else 0
        
        return min(rate, 1.5), population  # Cap at 150% (can exceed 100% due to updates)
    
    def join_enrollment_data(
        self,
        enrollment_df: pd.DataFrame,
        state_column: str = "state",
        value_column: str = "total_enrollments"
    ) -> gpd.GeoDataFrame:
        """
        Join Aadhaar enrollment data with GeoJSON boundaries.
        
        Args:
            enrollment_df: DataFrame with enrollment data
            state_column: Column name for state in enrollment data
            value_column: Column name for enrollment counts
            
        Returns:
            GeoDataFrame with enrollment data joined to boundaries
            
        Example:
            >>> geo = GeoProcessor()
            >>> df = pd.DataFrame({
            ...     'state': ['Maharashtra', 'Bihar'],
            ...     'total_enrollments': [50000000, 30000000]
            ... })
            >>> gdf = geo.join_enrollment_data(df)
        """
        gdf = self.load_geojson()
        
        # Normalize state names in enrollment data
        enrollment_df = enrollment_df.copy()
        enrollment_df['normalized_state'] = enrollment_df[state_column].apply(
            self.normalize_state_name
        )
        
        # Determine join column in GeoJSON
        join_col = 'state_name' if 'state_name' in gdf.columns else gdf.columns[0]
        
        # Create normalized version in GeoJSON
        gdf['normalized_state'] = gdf[join_col].apply(self.normalize_state_name)
        
        # Aggregate enrollment data by state
        agg_df = enrollment_df.groupby('normalized_state').agg({
            value_column: 'sum'
        }).reset_index()
        
        # Join
        result = gdf.merge(
            agg_df,
            on='normalized_state',
            how='left'
        )
        
        # Fill missing values
        result[value_column] = result[value_column].fillna(0)
        
        # Calculate penetration rates
        result['penetration_rate'] = result.apply(
            lambda row: self.calculate_penetration_rate(
                row[value_column],
                row['normalized_state']
            )[0],
            axis=1
        )
        
        return result
    
    def generate_weights_matrix(
        self,
        gdf: Optional[gpd.GeoDataFrame] = None,
        method: str = "queen"
    ) -> np.ndarray:
        """
        Generate spatial weights matrix using Queen or KNN contiguity.
        
        Args:
            gdf: GeoDataFrame (uses loaded if not provided)
            method: 'queen' for Queen contiguity, 'knn' for k-nearest neighbors
            
        Returns:
            NxN numpy array of spatial weights
            
        Example:
            >>> geo = GeoProcessor()
            >>> weights = geo.generate_weights_matrix(method='queen')
            >>> print(f"Shape: {weights.shape}")
        """
        if gdf is None:
            gdf = self.load_geojson()
            
        n = len(gdf)
        weights = np.zeros((n, n))
        
        try:
            from libpysal.weights import Queen, KNN
            
            if method.lower() == "queen":
                w = Queen.from_dataframe(gdf, use_index=False)
            else:
                w = KNN.from_dataframe(gdf, k=5)
                
            # Convert to dense matrix
            for i in range(n):
                neighbors = w.neighbors.get(i, [])
                for j in neighbors:
                    weights[i, j] = 1.0 / len(neighbors) if neighbors else 0
                    
        except Exception as e:
            logger.warning(f"PySAL weights generation failed: {e}. Using distance-based fallback.")
            weights = self._fallback_distance_weights(gdf)
            
        self._weights_matrix = weights
        return weights
    
    def _fallback_distance_weights(self, gdf: gpd.GeoDataFrame) -> np.ndarray:
        """Generate weights based on centroid distances (fallback method)."""
        n = len(gdf)
        weights = np.zeros((n, n))
        
        centroids = gdf.geometry.centroid
        
        for i in range(n):
            distances = []
            for j in range(n):
                if i != j:
                    dist = centroids.iloc[i].distance(centroids.iloc[j])
                    distances.append((j, dist))
            
            # Use 5 nearest neighbors
            distances.sort(key=lambda x: x[1])
            k_nearest = distances[:5]
            
            if k_nearest:
                weight_sum = sum(1.0 / d[1] for d in k_nearest if d[1] > 0)
                for j, dist in k_nearest:
                    if dist > 0 and weight_sum > 0:
                        weights[i, j] = (1.0 / dist) / weight_sum
                        
        return weights
    
    def get_state_geojson(self, state: str) -> Optional[Dict]:
        """
        Get GeoJSON for a specific state.
        
        Args:
            state: State name
            
        Returns:
            Dict containing GeoJSON feature for the state
        """
        gdf = self.load_geojson()
        normalized = self.normalize_state_name(state)
        
        join_col = 'normalized_state' if 'normalized_state' in gdf.columns else 'state_name'
        
        if join_col not in gdf.columns:
            gdf['normalized_state'] = gdf.iloc[:, 0].apply(self.normalize_state_name)
            join_col = 'normalized_state'
        
        state_gdf = gdf[gdf[join_col].str.lower() == normalized.lower()]
        
        if state_gdf.empty:
            logger.warning(f"State not found: {state}")
            return None
            
        return json.loads(state_gdf.to_json())
    
    def to_geojson_with_data(
        self,
        gdf: gpd.GeoDataFrame,
        properties: List[str]
    ) -> Dict:
        """
        Convert GeoDataFrame to GeoJSON with selected properties.
        
        Args:
            gdf: GeoDataFrame with data
            properties: List of column names to include as properties
            
        Returns:
            GeoJSON dict ready for frontend visualization
        """
        # Select only desired columns + geometry
        available_props = [p for p in properties if p in gdf.columns]
        subset = gdf[available_props + ['geometry']].copy()
        
        return json.loads(subset.to_json())


# Convenience function for quick loading
def load_india_boundaries() -> gpd.GeoDataFrame:
    """Quick loader for India state boundaries."""
    processor = GeoProcessor()
    return processor.load_geojson()


def get_state_population(state: str) -> float:
    """Get population for a state in millions."""
    processor = GeoProcessor()
    normalized = processor.normalize_state_name(state)
    return STATE_POPULATION.get(normalized, 10.0)
