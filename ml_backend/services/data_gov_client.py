"""
data.gov.in API Client

PRIVACY NOTICE:
- Fetches ONLY aggregated, anonymized data
- No individual Aadhaar numbers or PII accessed
- All data is publicly available government statistics
"""

import requests
import pandas as pd
from typing import Optional, Dict, List, Any
from config import DATA_GOV_API_KEY, DATA_GOV_BASE_URL, DATASETS


class DataGovClient:
    """Client for fetching Aadhaar data from data.gov.in APIs"""
    
    def __init__(self):
        self.api_key = DATA_GOV_API_KEY
        self.base_url = DATA_GOV_BASE_URL
        self.datasets = DATASETS
        
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Return list of available datasets with metadata"""
        return [
            {
                "key": key,
                "id": info["id"],
                "name": info["name"],
                "description": info["description"],
                "fields": info["fields"]
            }
            for key, info in self.datasets.items()
        ]
    
    def fetch_data(
        self,
        dataset_key: str,
        limit: int = 1000,
        offset: int = 0,
        filters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch data from a specific dataset
        
        Args:
            dataset_key: One of 'enrolment', 'demographic', 'biometric'
            limit: Number of records to fetch (max 10000)
            offset: Pagination offset
            filters: Optional filters like {'state': 'Maharashtra'}
        
        Returns:
            Dict with 'success', 'total', 'records' keys
        """
        if dataset_key not in self.datasets:
            return {"success": False, "error": f"Unknown dataset: {dataset_key}", "records": []}
        
        resource_id = self.datasets[dataset_key]["id"]
        
        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": str(limit),
            "offset": str(offset)
        }
        
        # Add filters if provided
        if filters:
            for key, value in filters.items():
                params[f"filters[{key}]"] = value
        
        url = f"{self.base_url}/{resource_id}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": True,
                "total": data.get("total", 0),
                "count": data.get("count", 0),
                "records": data.get("records", [])
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "records": []
            }
    
    def fetch_all_data(
        self,
        dataset_key: str,
        max_records: int = 10000,
        filters: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """
        Fetch all data from a dataset (with pagination)
        
        Args:
            dataset_key: Dataset to fetch
            max_records: Maximum records to fetch
            filters: Optional filters
            
        Returns:
            DataFrame with all records
        """
        all_records = []
        offset = 0
        batch_size = 1000
        
        while len(all_records) < max_records:
            result = self.fetch_data(dataset_key, limit=batch_size, offset=offset, filters=filters)
            
            if not result["success"] or not result["records"]:
                break
                
            all_records.extend(result["records"])
            offset += batch_size
            
            # Check if we've fetched all available records
            if len(result["records"]) < batch_size:
                break
        
        return pd.DataFrame(all_records[:max_records])
    
    def fetch_multiple_datasets(
        self,
        dataset_keys: List[str],
        limit_per_dataset: int = 5000
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data from multiple datasets
        
        Args:
            dataset_keys: List of dataset keys to fetch
            limit_per_dataset: Max records per dataset
            
        Returns:
            Dict mapping dataset_key to DataFrame
        """
        results = {}
        for key in dataset_keys:
            if key in self.datasets:
                results[key] = self.fetch_all_data(key, max_records=limit_per_dataset)
        return results
    
    def get_schema(self, dataset_key: str) -> Dict[str, Any]:
        """Get schema information for a dataset"""
        if dataset_key not in self.datasets:
            return {"error": f"Unknown dataset: {dataset_key}"}
        
        # Fetch a small sample to infer schema
        result = self.fetch_data(dataset_key, limit=10)
        
        if not result["success"] or not result["records"]:
            return {"error": "Could not fetch sample data"}
        
        sample = pd.DataFrame(result["records"])
        
        return {
            "dataset": dataset_key,
            "name": self.datasets[dataset_key]["name"],
            "total_records": result.get("total", 0),
            "columns": list(sample.columns),
            "dtypes": {col: str(dtype) for col, dtype in sample.dtypes.items()},
            "sample": result["records"][:3]
        }


# Singleton instance
data_client = DataGovClient()
