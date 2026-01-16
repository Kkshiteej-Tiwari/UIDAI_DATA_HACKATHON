"""
New API endpoint schemas for XAI explanations.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ExplainRequest(BaseModel):
    """Request for explaining specific records."""
    record_indices: List[int] = Field(..., description="Indices of records to explain")
    include_deviations: bool = Field(default=True, description="Include deviation analysis")
    include_temporal: bool = Field(default=True, description="Include temporal flags")
    include_geographic: bool = Field(default=True, description="Include geographic flags")


class ExplainResponse(BaseModel):
    """Response with fraud explanations."""
    job_id: str
    explanations: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None
    generated_at: datetime


class FraudPatternsResponse(BaseModel):
    """Response with common fraud patterns."""
    job_id: str
    total_records: int
    total_anomalies: int
    fraud_patterns: List[Dict[str, Any]]
    top_features: List[Dict[str, Any]]
    severity_distribution: Dict[str, int]
    generated_at: datetime
