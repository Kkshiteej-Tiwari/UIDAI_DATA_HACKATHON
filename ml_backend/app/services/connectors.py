"""
Gender Inclusion Tracker - Data Connectors
Handles fetching data from external APIs (data.gov.in).
"""

import httpx
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DatasetInfo:
    """Information about a dataset."""
    id: str
    name: str
    source: str
    description: str
    fields: List[str]
    record_count: int
    suitability_score: float


class DataGovConnector:
    """Connector for data.gov.in API."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def fetch_dataset(
        self,
        resource_id: str,
        limit: int = 1000,
        offset: int = 0,
        filters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch data from a data.gov.in resource.
        
        Args:
            resource_id: The resource ID to fetch
            limit: Number of records to fetch
            offset: Pagination offset
            filters: Optional filters
        
        Returns:
            Dict containing success status, total, count, and records
        """
        params = {
            'api-key': self.api_key,
            'format': 'json',
            'limit': str(limit),
            'offset': str(offset)
        }
        
        if filters:
            params.update(filters)
        
        url = f"{self.base_url}/{resource_id}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'total': data.get('total', 0),
                'count': data.get('count', 0),
                'records': data.get('records', []),
                'fields': list(data.get('records', [{}])[0].keys()) if data.get('records') else []
            }
        except httpx.HTTPError as e:
            logger.error(f"API fetch error for {resource_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'records': [],
                'fields': []
            }
    
    async def get_dataset_info(self, resource_id: str, name: str) -> DatasetInfo:
        """Get dataset information including schema and suitability score."""
        # Fetch sample data to understand schema
        result = await self.fetch_dataset(resource_id, limit=10)
        
        fields = result.get('fields', [])
        suitability = self._calculate_suitability(fields)
        
        return DatasetInfo(
            id=resource_id,
            name=name,
            source="data.gov.in",
            description=f"UIDAI {name} dataset",
            fields=fields,
            record_count=result.get('total', 0),
            suitability_score=suitability
        )
    
    def _calculate_suitability(self, fields: List[str]) -> float:
        """
        Calculate suitability score (0-1) based on presence of required fields.
        
        Essential fields for gender analysis:
        - Gender-related: male, female, gender
        - Geographic: state, district
        - Demographic: age groups, population
        """
        score = 0.0
        fields_lower = [f.lower() for f in fields]
        
        # Check for gender-related fields (highest weight)
        gender_keywords = ['male', 'female', 'gender', 'm_', 'f_', 'men', 'women']
        for keyword in gender_keywords:
            if any(keyword in f for f in fields_lower):
                score += 0.3
                break
        
        # Check for geographic fields
        geo_keywords = ['state', 'district', 'pincode', 'location']
        for keyword in geo_keywords:
            if any(keyword in f for f in fields_lower):
                score += 0.25
                break
        
        # Check for date/time fields
        date_keywords = ['date', 'year', 'month', 'period']
        for keyword in date_keywords:
            if any(keyword in f for f in fields_lower):
                score += 0.15
                break
        
        # Check for count/enrollment fields
        count_keywords = ['count', 'total', 'enrolled', 'population', 'age']
        for keyword in count_keywords:
            if any(keyword in f for f in fields_lower):
                score += 0.15
                break
        
        # Check for demographic indicators
        demo_keywords = ['literacy', 'education', 'income', 'bank', 'mobile']
        for keyword in demo_keywords:
            if any(keyword in f for f in fields_lower):
                score += 0.15
                break
        
        return min(score, 1.0)


class MultiAPIConnector:
    """Manages connections to multiple data APIs."""
    
    def __init__(self):
        self.connectors = {
            'api1': DataGovConnector(settings.api1_base, settings.data_gov_api_key),
            'api2': DataGovConnector(settings.api2_base, settings.data_gov_api_key),
            'api3': DataGovConnector(settings.api3_base, settings.data_gov_api_key),
        }
        
        self.known_datasets = {
            'enrolment': {
                'resource_id': settings.enrolment_resource_id,
                'name': 'Aadhaar Monthly Enrolment Data',
                'description': 'Contains enrollment counts by state, district, pincode, and age groups'
            },
            'demographic': {
                'resource_id': settings.demographic_resource_id,
                'name': 'Aadhaar Demographic Update Data',
                'description': 'Contains demographic update data by age groups'
            },
            'biometric': {
                'resource_id': settings.biometric_resource_id,
                'name': 'Aadhaar Biometric Update Data',
                'description': 'Contains biometric update data'
            }
        }
    
    async def close(self):
        """Close all connectors."""
        for connector in self.connectors.values():
            await connector.close()
    
    async def list_all_datasets(self) -> List[Dict[str, Any]]:
        """List all available datasets with suitability scores."""
        datasets = []
        
        for dataset_key, info in self.known_datasets.items():
            try:
                connector = self.connectors['api1']  # Use primary API
                dataset_info = await connector.get_dataset_info(
                    info['resource_id'],
                    info['name']
                )
                
                datasets.append({
                    'id': dataset_info.id,
                    'key': dataset_key,
                    'name': dataset_info.name,
                    'source': 'api1',
                    'description': info['description'],
                    'fields': dataset_info.fields,
                    'record_count': dataset_info.record_count,
                    'suitability_score': dataset_info.suitability_score
                })
            except Exception as e:
                logger.error(f"Failed to get dataset info for {dataset_key}: {str(e)}")
        
        # Sort by suitability
        datasets.sort(key=lambda x: x['suitability_score'], reverse=True)
        return datasets
    
    async def fetch_dataset(
        self,
        source: str,
        resource_id: str,
        limit: int = 1000,
        **kwargs
    ) -> pd.DataFrame:
        """
        Fetch a specific dataset and return as DataFrame.
        
        Args:
            source: API source key ('api1', 'api2', 'api3')
            resource_id: Dataset resource ID
            limit: Number of records
        
        Returns:
            pandas DataFrame with the data
        """
        connector = self.connectors.get(source)
        if not connector:
            raise ValueError(f"Unknown source: {source}")
        
        result = await connector.fetch_dataset(resource_id, limit=limit, **kwargs)
        
        if not result['success']:
            raise Exception(f"Failed to fetch data: {result.get('error')}")
        
        return pd.DataFrame(result['records'])
    
    async def auto_select_best_dataset(self) -> Dict[str, Any]:
        """
        Automatically select the most suitable dataset for gender analysis.
        
        Returns:
            Dict with selected dataset info and reasoning
        """
        datasets = await self.list_all_datasets()
        
        if not datasets:
            return {
                'success': False,
                'error': 'No datasets available',
                'selected': None
            }
        
        # Select the dataset with highest suitability score
        best = datasets[0]
        
        return {
            'success': True,
            'selected': best,
            'alternatives': datasets[1:3] if len(datasets) > 1 else [],
            'reasoning': f"Selected '{best['name']}' with suitability score {best['suitability_score']:.2f}"
        }


# Singleton instance
_connector: Optional[MultiAPIConnector] = None


def get_connector() -> MultiAPIConnector:
    """Get or create the multi-API connector singleton."""
    global _connector
    if _connector is None:
        _connector = MultiAPIConnector()
    return _connector
