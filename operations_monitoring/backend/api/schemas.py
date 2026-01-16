"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AnalysisStatus(str, Enum):
    """Status of an analysis job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============== Dataset Schemas ==============

class DatasetInfo(BaseModel):
    """Information about an available dataset."""
    id: str
    name: str
    description: str
    fields: List[str]
    record_count: Optional[int] = None


class DatasetListResponse(BaseModel):
    """Response containing list of available datasets."""
    datasets: List[DatasetInfo]
    total: int


# ============== Analysis Schemas ==============

class AnalysisRequest(BaseModel):
    """Request to start an analysis job."""
    limit: int = Field(default=1000, ge=1, le=10000, description="Number of records to analyze")
    models: Optional[List[str]] = Field(default=None, description="Specific models to use (default: auto-select)")


class AnalysisJobResponse(BaseModel):
    """Response when an analysis job is created."""
    job_id: str
    dataset_id: str
    status: AnalysisStatus
    created_at: datetime
    message: str


class AnomalyRecord(BaseModel):
    """A single anomaly detection result."""
    record_id: str
    anomaly_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: List[str]
    features: Dict[str, Any]


class ModelResult(BaseModel):
    """Results from a single ML model."""
    model_name: str
    anomaly_scores: List[float]
    threshold: float
    anomaly_count: int
    execution_time_ms: float


class AnalysisResults(BaseModel):
    """Complete analysis results."""
    job_id: str
    dataset_id: str
    status: AnalysisStatus
    total_records: int
    anomaly_count: int
    anomaly_percentage: float
    models_used: List[str]
    model_results: List[ModelResult]
    anomalies: List[AnomalyRecord]
    execution_time_ms: float
    created_at: datetime
    completed_at: Optional[datetime] = None


class AnalysisStatusResponse(BaseModel):
    """Response for analysis status check."""
    job_id: str
    status: AnalysisStatus
    progress: float = Field(ge=0.0, le=100.0)
    message: str
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None


# ============== Auditor Summary Schemas ==============

class FraudPattern(BaseModel):
    """A detected fraud pattern."""
    pattern_type: str
    description: str
    affected_records: int
    severity: RiskLevel
    examples: List[str]


class HighRiskEntity(BaseModel):
    """A high-risk entity (center/operator/region)."""
    entity_type: str
    entity_id: str
    entity_name: str
    anomaly_count: int
    risk_score: float


class TemporalTrend(BaseModel):
    """Temporal trend analysis."""
    period: str
    normal_avg: float
    anomaly_avg: float
    spike_detected: bool
    spike_magnitude: Optional[float] = None


class AuditorSummary(BaseModel):
    """Summary report for auditors."""
    job_id: str
    generated_at: datetime
    total_records_analyzed: int
    total_anomalies: int
    anomaly_percentage: float
    risk_distribution: Dict[str, int]  # {"Low": 10, "Medium": 5, "High": 2}
    top_fraud_patterns: List[FraudPattern]
    high_risk_entities: List[HighRiskEntity]
    temporal_trends: List[TemporalTrend]
    recommendations: List[str]


# ============== Visualization Schemas ==============

class ChartData(BaseModel):
    """Generic chart data structure."""
    chart_type: str
    title: str
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    data: Dict[str, Any]


class VisualizationResponse(BaseModel):
    """Response containing visualization data."""
    job_id: str
    charts: List[ChartData]
    generated_at: datetime
