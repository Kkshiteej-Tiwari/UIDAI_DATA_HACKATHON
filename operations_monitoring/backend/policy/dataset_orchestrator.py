"""
Dataset Orchestration Layer

Receives resolved analytical needs and automatically orchestrates
data retrieval from backend sources. Dataset names are NEVER exposed.

DESIGN PRINCIPLES:
- Signal-based data selection (not dataset-based)
- All dataset names internal only
- Filters applied transparently
- Multi-dataset joins handled internally
- API responses never contain dataset references
- ALL DATA FROM LIVE API - NO SYNTHETIC/SAMPLE DATA
"""
import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# INTERNAL MAPPINGS - NEVER EXPOSED
# =============================================================================

class _DataSource(str, Enum):
    """Internal data source identifiers. NEVER exposed to external systems."""
    ENROLMENT = "enrolment"
    DEMOGRAPHIC = "demographic"
    BIOMETRIC = "biometric"


# Internal API resource mapping - NEVER EXPOSED
# These are the ACTUAL data.gov.in resource IDs - kept internal
_RESOURCE_IDS = {
    _DataSource.ENROLMENT: "ecd49b12-3084-4521-8f7e-ca8bf72069ba",
    _DataSource.DEMOGRAPHIC: "19eac040-0b94-49fa-b239-4f2fd8677d53",
    _DataSource.BIOMETRIC: "65454dab-1517-40a3-ac1d-47d4dfe6891c"
}

# Signal to data source mapping - INTERNAL ONLY
_SIGNAL_TO_SOURCE_MAP = {
    # Enrollment signals
    "volume_patterns": [_DataSource.ENROLMENT],
    "geographic_distribution": [_DataSource.ENROLMENT, _DataSource.DEMOGRAPHIC],
    "temporal_patterns": [_DataSource.ENROLMENT],
    "operator_activity": [_DataSource.ENROLMENT],
    
    # Update signals
    "update_frequency": [_DataSource.DEMOGRAPHIC, _DataSource.BIOMETRIC],
    "demographic_changes": [_DataSource.DEMOGRAPHIC],
    "repeat_update_patterns": [_DataSource.DEMOGRAPHIC],
    "address_change_velocity": [_DataSource.DEMOGRAPHIC],
    
    # Biometric signals
    "biometric_update_frequency": [_DataSource.BIOMETRIC],
    "multi_device_submissions": [_DataSource.BIOMETRIC, _DataSource.ENROLMENT],
    "rejection_patterns": [_DataSource.BIOMETRIC],
    "quality_metrics": [_DataSource.BIOMETRIC],
    
    # Cross-operational signals
    "cross_operation_correlation": [_DataSource.ENROLMENT, _DataSource.DEMOGRAPHIC, _DataSource.BIOMETRIC]
}

# Analysis scope to data source mapping - INTERNAL ONLY
_SCOPE_TO_SOURCE_MAP = {
    "new_registrations": [_DataSource.ENROLMENT],
    "enrollment_volume": [_DataSource.ENROLMENT],
    "center_activity": [_DataSource.ENROLMENT],
    "demographic_updates": [_DataSource.DEMOGRAPHIC],
    "address_changes": [_DataSource.DEMOGRAPHIC],
    "field_modifications": [_DataSource.DEMOGRAPHIC],
    "fingerprint_updates": [_DataSource.BIOMETRIC],
    "iris_updates": [_DataSource.BIOMETRIC],
    "photo_updates": [_DataSource.BIOMETRIC],
    "all_operations": [_DataSource.ENROLMENT, _DataSource.DEMOGRAPHIC, _DataSource.BIOMETRIC]
}


@dataclass
class DataRequest:
    """Internal data request specification."""
    sources: List[_DataSource]
    filters: Dict[str, Any]
    time_range: Tuple[datetime, datetime]
    geographic_filter: Optional[Dict[str, str]]
    join_required: bool
    priority: int


@dataclass
class OrchestrationResult:
    """
    Result from data orchestration.
    
    Contains processed data WITHOUT any dataset name references.
    """
    data: pd.DataFrame
    record_count: int
    time_range_applied: str
    geographic_scope_applied: str
    processing_notes: List[str]
    data_source: str = "LIVE_API"  # Always live API
    # EXPLICITLY NO: dataset_names, source_ids, table_names


class DatasetOrchestrationLayer:
    """
    Orchestrates data retrieval based on analytical needs.
    
    ALL DATA IS FETCHED FROM LIVE API - NO SYNTHETIC DATA.
    
    This layer:
    - Receives resolved intents with signals
    - Determines required data sources (internally)
    - Fetches from live data.gov.in API
    - Applies filters (time, geography)
    - Joins data sources as needed
    - Returns unified data WITHOUT exposing source names
    
    CRITICAL: No dataset names in any public method returns.
    """
    
    # API Configuration - INTERNAL
    _API_BASE_URL = "https://api.data.gov.in/resource"
    _API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
    
    def __init__(self):
        """Initialize orchestration layer."""
        self._cache = {}
        logger.info("Dataset Orchestration Layer initialized - LIVE API MODE")
    
    def orchestrate(
        self,
        resolved_intent: Dict[str, Any],
        record_limit: int = 1000
    ) -> OrchestrationResult:
        """
        Orchestrate data retrieval for resolved intent.
        
        Args:
            resolved_intent: Output from IntentResolutionEngine
            record_limit: Maximum records to retrieve
        
        Returns:
            OrchestrationResult with unified data.
            NO dataset names in output.
        """
        logger.info(f"Orchestrating data for intent: {resolved_intent.get('intent', {}).get('id', 'unknown')}")
        
        # Extract analytical needs
        signals = resolved_intent.get("signals", [])
        processing = resolved_intent.get("processing", {})
        context = resolved_intent.get("context", {})
        
        # Determine required sources (INTERNAL)
        required_sources = self._determine_sources(signals, processing.get("scope", []))
        
        # Build filters
        time_filter = self._build_time_filter(context.get("temporal", "Today's operations"))
        geo_filter = self._build_geographic_filter(context.get("geographic", "All India"))
        
        # Create internal data request
        request = DataRequest(
            sources=list(required_sources),
            filters={},
            time_range=time_filter,
            geographic_filter=geo_filter,
            join_required=len(required_sources) > 1,
            priority=resolved_intent.get("metadata", {}).get("priority", 2)
        )
        
        # Fetch and process data
        data = self._execute_request(request, record_limit)
        
        # Build result WITHOUT dataset names
        return OrchestrationResult(
            data=data,
            record_count=len(data),
            time_range_applied=context.get("temporal", "Today's operations"),
            geographic_scope_applied=context.get("geographic", "All India"),
            processing_notes=self._generate_processing_notes(request, data)
        )
    
    def _determine_sources(
        self,
        signals: List[Dict],
        scope: List[str]
    ) -> set:
        """
        Determine required data sources from signals and scope.
        THIS IS INTERNAL - sources never exposed.
        """
        sources = set()
        
        # Map signals to sources
        for signal in signals:
            signal_id = signal.get("signal_id", "")
            if signal_id in _SIGNAL_TO_SOURCE_MAP:
                sources.update(_SIGNAL_TO_SOURCE_MAP[signal_id])
        
        # Map scope to sources
        for scope_item in scope:
            if scope_item in _SCOPE_TO_SOURCE_MAP:
                sources.update(_SCOPE_TO_SOURCE_MAP[scope_item])
        
        # Default to enrollment if nothing determined
        if not sources:
            sources.add(_DataSource.ENROLMENT)
        
        logger.debug(f"Determined {len(sources)} data sources (internal)")
        return sources
    
    def _build_time_filter(self, temporal_context: str) -> Tuple[datetime, datetime]:
        """Build time range filter from context."""
        now = datetime.now()
        
        if "today" in temporal_context.lower():
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif "7 days" in temporal_context.lower():
            start = now - timedelta(days=7)
            end = now
        elif "month" in temporal_context.lower():
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        else:
            # Default to last 30 days
            start = now - timedelta(days=30)
            end = now
        
        return (start, end)
    
    def _build_geographic_filter(self, geo_context: str) -> Optional[Dict[str, str]]:
        """Build geographic filter from context."""
        if geo_context == "All India" or not geo_context:
            return None
        
        # Parse geographic context
        parts = [p.strip() for p in geo_context.split(",")]
        
        filter_dict = {}
        if len(parts) >= 2:
            filter_dict["district"] = parts[0]
            filter_dict["state"] = parts[1]
        elif len(parts) == 1:
            filter_dict["state"] = parts[0]
        
        return filter_dict if filter_dict else None
    
    def _execute_request(
        self,
        request: DataRequest,
        limit: int
    ) -> pd.DataFrame:
        """
        Execute data request against LIVE API.
        SOURCE NAMES NEVER RETURNED.
        ALL DATA FROM LIVE API - NO SYNTHETIC DATA.
        """
        dataframes = []
        
        for source in request.sources:
            try:
                # Fetch from live API (source name hidden)
                df = self._fetch_from_api(source, limit // max(len(request.sources), 1))
                
                if df.empty:
                    logger.warning(f"No data returned from API for source")
                    continue
                
                # Apply time filter
                df = self._apply_time_filter(df, request.time_range)
                
                # Apply geographic filter
                if request.geographic_filter:
                    df = self._apply_geographic_filter(df, request.geographic_filter)
                
                if not df.empty:
                    dataframes.append(df)
                
            except Exception as e:
                logger.error(f"Error fetching from API: {e}")
                continue
        
        if not dataframes:
            logger.error("No data retrieved from API - returning empty DataFrame")
            return pd.DataFrame()
        
        # Join if multiple sources
        if request.join_required and len(dataframes) > 1:
            result = self._join_dataframes(dataframes)
        else:
            result = pd.concat(dataframes, ignore_index=True) if len(dataframes) > 1 else dataframes[0]
        
        logger.info(f"Retrieved {len(result)} records from LIVE API")
        return result.head(limit)
    
    def _fetch_from_api(
        self,
        source: _DataSource,
        limit: int
    ) -> pd.DataFrame:
        """
        Fetch data from live data.gov.in API.
        INTERNAL METHOD - source names never exposed.
        """
        resource_id = _RESOURCE_IDS.get(source)
        if not resource_id:
            # Fallback to enrolment for unknown sources
            resource_id = _RESOURCE_IDS[_DataSource.ENROLMENT]
        
        url = f"{self._API_BASE_URL}/{resource_id}"
        params = {
            "api-key": self._API_KEY,
            "format": "json",
            "limit": str(min(limit, 5000))
        }
        
        try:
            # Synchronous request for compatibility
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                records = data.get("records", [])
                if not records:
                    logger.warning("API returned empty records")
                    return pd.DataFrame()
                
                logger.info(f"Fetched {len(records)} records from live API")
                return pd.DataFrame(records)
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching from API: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching from API: {e}")
            return pd.DataFrame()
    
    async def _fetch_from_api_async(
        self,
        source: _DataSource,
        limit: int
    ) -> pd.DataFrame:
        """
        Async version of API fetch.
        INTERNAL METHOD - source names never exposed.
        """
        resource_id = _RESOURCE_IDS.get(source)
        if not resource_id:
            resource_id = _RESOURCE_IDS[_DataSource.ENROLMENT]
        
        url = f"{self._API_BASE_URL}/{resource_id}"
        params = {
            "api-key": self._API_KEY,
            "format": "json",
            "limit": str(min(limit, 5000))
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                records = data.get("records", [])
                if not records:
                    return pd.DataFrame()
                
                logger.info(f"Async fetched {len(records)} records from live API")
                return pd.DataFrame(records)
                
        except Exception as e:
            logger.error(f"Async API error: {e}")
            return pd.DataFrame()
    
    def _apply_time_filter(
        self,
        df: pd.DataFrame,
        time_range: Tuple[datetime, datetime]
    ) -> pd.DataFrame:
        """Apply time filter to dataframe."""
        if df.empty:
            return df
        
        # Try common date columns
        date_cols = ['date', 'Date', 'timestamp', 'created_at', 'month', 'year']
        
        for col in date_cols:
            if col in df.columns:
                try:
                    if col in ['month', 'year']:
                        # Filter by month/year
                        start_month = time_range[0].month
                        end_month = time_range[1].month
                        if 'month' in df.columns:
                            df = df[(df['month'] >= start_month) & (df['month'] <= end_month)]
                    else:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        df = df[(df[col] >= time_range[0]) & (df[col] <= time_range[1])]
                    break
                except Exception:
                    continue
        
        return df
    
    def _apply_geographic_filter(
        self,
        df: pd.DataFrame,
        geo_filter: Dict[str, str]
    ) -> pd.DataFrame:
        """Apply geographic filter to dataframe."""
        if df.empty:
            return df
        
        for geo_type, value in geo_filter.items():
            # Try different column name variations
            col_variations = [
                geo_type,
                geo_type.title(),
                geo_type.upper(),
                f"{geo_type}_name",
                f"{geo_type.title()}_Name"
            ]
            
            for col in col_variations:
                if col in df.columns:
                    df = df[df[col].str.contains(value, case=False, na=False)]
                    break
        
        return df
    
    def _join_dataframes(self, dataframes: List[pd.DataFrame]) -> pd.DataFrame:
        """Join multiple dataframes on common keys."""
        if len(dataframes) < 2:
            return dataframes[0] if dataframes else pd.DataFrame()
        
        # Find common columns for joining
        common_cols = set(dataframes[0].columns)
        for df in dataframes[1:]:
            common_cols &= set(df.columns)
        
        # Prefer joining on geographic columns
        join_cols = []
        for col in ['state', 'State', 'district', 'District', 'month', 'year']:
            if col in common_cols:
                join_cols.append(col)
        
        if join_cols:
            # Merge on common columns
            result = dataframes[0]
            for df in dataframes[1:]:
                result = pd.merge(
                    result, df,
                    on=join_cols,
                    how='outer',
                    suffixes=('', '_dup')
                )
                # Remove duplicate columns
                result = result.loc[:, ~result.columns.str.endswith('_dup')]
        else:
            # No common columns - concatenate
            result = pd.concat(dataframes, ignore_index=True)
        
        return result
    
    def _generate_synthetic_data(
        self,
        request: DataRequest,
        limit: int
    ) -> pd.DataFrame:
        """Generate synthetic data for testing/demo."""
        np.random.seed(42)
        
        states = ['Maharashtra', 'Karnataka', 'Tamil Nadu', 'Gujarat', 'Delhi']
        
        data = {
            'state': np.random.choice(states, limit),
            'month': np.random.randint(1, 13, limit),
            'year': np.random.choice([2024, 2025, 2026], limit),
            'total_records': np.random.poisson(100, limit),
            'processed': np.random.poisson(95, limit),
            'flagged': np.random.poisson(5, limit)
        }
        
        return pd.DataFrame(data)
    
    def _generate_processing_notes(
        self,
        request: DataRequest,
        data: pd.DataFrame
    ) -> List[str]:
        """Generate processing notes WITHOUT exposing internals."""
        notes = []
        
        notes.append(f"Retrieved {len(data)} records for analysis")
        
        if request.geographic_filter:
            notes.append(f"Geographic filter applied: {request.geographic_filter.get('state', 'Region')}")
        else:
            notes.append("National scope - all regions included")
        
        start, end = request.time_range
        notes.append(f"Time period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        
        if request.join_required:
            notes.append("Multi-source correlation analysis performed")
        
        # NOTE: No dataset names in notes!
        return notes


class OrchestrationFacade:
    """
    Simple facade for data orchestration.
    
    Provides clean interface without exposing internals.
    """
    
    def __init__(self):
        self._orchestrator = DatasetOrchestrationLayer()
        self._intent_resolver = None
    
    def _get_resolver(self):
        """Lazy load intent resolver."""
        if self._intent_resolver is None:
            try:
                from policy.intent_resolver import IntentResolutionEngine
                self._intent_resolver = IntentResolutionEngine()
            except ImportError:
                self._intent_resolver = None
        return self._intent_resolver
    
    def analyze(
        self,
        intent_id: str,
        state: Optional[str] = None,
        vigilance: str = "standard",
        record_limit: int = 1000
    ) -> Dict[str, Any]:
        """
        High-level analysis function.
        
        Goes from intent to data without exposing datasets.
        
        Args:
            intent_id: User's monitoring intent
            state: Optional state filter
            vigilance: Vigilance level
            record_limit: Max records
        
        Returns:
            Analysis-ready data and metadata.
            NO dataset names in output.
        """
        resolver = self._get_resolver()
        
        if resolver:
            from policy.intent_resolver import UserContext, VigilanceLevel
            
            context = UserContext(
                state=state,
                vigilance=VigilanceLevel(vigilance) if vigilance in ['routine', 'standard', 'enhanced', 'maximum'] else VigilanceLevel.STANDARD
            )
            
            resolved = resolver.resolve(intent_id, context)
            resolved_dict = resolver.to_dict(resolved)
        else:
            # Fallback
            resolved_dict = {
                "intent": {"id": intent_id},
                "signals": [{"signal_id": "volume_patterns"}],
                "processing": {"scope": ["new_registrations"]},
                "context": {
                    "geographic": state or "All India",
                    "temporal": "Today's operations"
                },
                "metadata": {"priority": 1}
            }
        
        # Orchestrate data retrieval
        result = self._orchestrator.orchestrate(resolved_dict, record_limit)
        
        # Return WITHOUT dataset names
        return {
            "data": result.data,
            "record_count": result.record_count,
            "scope": {
                "geographic": result.geographic_scope_applied,
                "temporal": result.time_range_applied
            },
            "notes": result.processing_notes
            # EXPLICITLY NO: dataset_names, source_ids
        }


# Convenience function
def get_analysis_data(
    intent_id: str,
    state: Optional[str] = None,
    vigilance: str = "standard",
    limit: int = 1000
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Convenience function to get analysis-ready data.
    
    Returns:
        Tuple of (DataFrame, metadata_dict)
        NO dataset names in output.
    """
    facade = OrchestrationFacade()
    result = facade.analyze(intent_id, state, vigilance, limit)
    
    return result["data"], {
        "record_count": result["record_count"],
        "scope": result["scope"],
        "notes": result["notes"]
    }


# Example usage
if __name__ == "__main__":
    print("=" * 60)
    print("DATASET ORCHESTRATION LAYER - DEMO")
    print("=" * 60)
    
    # Use facade for simplified access
    facade = OrchestrationFacade()
    
    result = facade.analyze(
        intent_id="check_enrollments",
        state="Maharashtra",
        vigilance="enhanced",
        record_limit=500
    )
    
    print(f"\nRecords Retrieved: {result['record_count']}")
    print(f"Geographic Scope: {result['scope']['geographic']}")
    print(f"Temporal Scope: {result['scope']['temporal']}")
    print("\nProcessing Notes:")
    for note in result['notes']:
        print(f"  • {note}")
    
    print("\n" + "=" * 60)
    print("NOTE: No dataset names in output!")
    print("=" * 60)
