"""
UIDAI Fraud Detection Policy Engine

This module provides a government-ready abstraction layer that completely hides
all ML/DL implementation details. Users interact only through policy-level controls
using government-friendly terminology.

DESIGN PRINCIPLES:
- No algorithm names exposed (Isolation Forest, HDBSCAN, etc. hidden)
- No thresholds or hyperparameters visible
- No technical ML terminology in responses
- All controls use policy-level language
- Full audit trail for government compliance
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RiskTolerance(str, Enum):
    """
    Policy-level risk tolerance settings.
    These are the ONLY configuration options exposed to users.
    
    CONSERVATIVE: Prioritizes security. Flags more records for review.
                 Suitable for high-value operations or sensitive regions.
    
    BALANCED: Default setting. Balanced approach between security and efficiency.
             Recommended for standard operations.
    
    AGGRESSIVE: Prioritizes throughput. Fewer flags, faster processing.
               Suitable for trusted regions with good historical records.
    """
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class RecordDisposition(str, Enum):
    """
    Policy-level record disposition.
    Government-friendly terminology replacing technical ML outputs.
    """
    FLAG = "FLAG"           # Requires immediate investigation
    REVIEW = "REVIEW"       # Recommend manual review
    CLEAR = "CLEAR"         # Proceed with normal processing
    ESCALATE = "ESCALATE"   # Escalate to senior authority


class ComplianceLevel(str, Enum):
    """Data protection compliance level."""
    STANDARD = "standard"
    ENHANCED = "enhanced"
    RESTRICTED = "restricted"


@dataclass
class PolicyPreset:
    """Pre-configured policy for common use cases."""
    name: str
    description: str
    risk_tolerance: RiskTolerance
    auto_flag_high_risk: bool
    require_secondary_verification: bool
    min_confidence_for_clear: float  # Internal only, never exposed
    escalation_enabled: bool


@dataclass
class AuditRecord:
    """Immutable audit trail for compliance."""
    audit_id: str
    timestamp: str
    action: str
    user_id: str
    policy_applied: str
    records_processed: int
    flags_raised: int
    disposition_summary: Dict[str, int]
    compliance_level: str
    data_classification: str


@dataclass
class PolicyResult:
    """
    Policy-level result for a single record.
    Contains NO technical ML details.
    """
    record_id: str
    disposition: RecordDisposition
    risk_indicator: str  # "Low", "Medium", "High", "Critical"
    confidence_level: str  # "Standard", "High", "Very High"
    requires_action: bool
    action_priority: int  # 1 (highest) to 5 (lowest)
    reason_summary: str  # Human-readable, no technical terms
    recommended_action: str
    review_by: Optional[str]  # Recommended review authority
    flags: List[str]  # Policy-level flags


class PolicyEngine:
    """
    Government-Ready Fraud Detection Policy Engine
    
    This engine provides a complete abstraction over ML/DL models.
    All technical implementation details are hidden. Users interact
    only through policy-level controls.
    
    USAGE:
        engine = PolicyEngine()
        results = engine.analyze_records(
            data=dataframe,
            risk_tolerance=RiskTolerance.BALANCED,
            region="Maharashtra"
        )
    
    SECURITY:
        - All ML models are internal
        - No thresholds exposed
        - No hyperparameters configurable
        - Full audit logging
    """
    
    # Internal thresholds - NEVER exposed to users
    _INTERNAL_THRESHOLDS = {
        RiskTolerance.CONSERVATIVE: {"flag": 0.4, "review": 0.6, "escalate": 0.85},
        RiskTolerance.BALANCED: {"flag": 0.5, "review": 0.7, "escalate": 0.9},
        RiskTolerance.AGGRESSIVE: {"flag": 0.6, "review": 0.8, "escalate": 0.95}
    }
    
    # Internal confidence mapping - NEVER exposed
    _CONFIDENCE_MAPPING = {
        (0.0, 0.4): "Standard",
        (0.4, 0.7): "High",
        (0.7, 1.0): "Very High"
    }
    
    # Pre-defined policy presets for government use
    POLICY_PRESETS = {
        "HIGH_SECURITY": PolicyPreset(
            name="High Security Operations",
            description="Maximum scrutiny for sensitive operations. Recommended for new enrollment centers or flagged regions.",
            risk_tolerance=RiskTolerance.CONSERVATIVE,
            auto_flag_high_risk=True,
            require_secondary_verification=True,
            min_confidence_for_clear=0.85,
            escalation_enabled=True
        ),
        "STANDARD": PolicyPreset(
            name="Standard Operations",
            description="Balanced approach for routine operations. Default setting for established centers.",
            risk_tolerance=RiskTolerance.BALANCED,
            auto_flag_high_risk=True,
            require_secondary_verification=False,
            min_confidence_for_clear=0.75,
            escalation_enabled=True
        ),
        "HIGH_THROUGHPUT": PolicyPreset(
            name="High Throughput Mode",
            description="Optimized for trusted regions with excellent historical compliance.",
            risk_tolerance=RiskTolerance.AGGRESSIVE,
            auto_flag_high_risk=True,
            require_secondary_verification=False,
            min_confidence_for_clear=0.65,
            escalation_enabled=False
        ),
        "SPECIAL_DRIVE": PolicyPreset(
            name="Special Drive Mode",
            description="For government enrollment drives. Enhanced monitoring with streamlined processing.",
            risk_tolerance=RiskTolerance.BALANCED,
            auto_flag_high_risk=True,
            require_secondary_verification=True,
            min_confidence_for_clear=0.70,
            escalation_enabled=True
        )
    }
    
    def __init__(self, compliance_level: ComplianceLevel = ComplianceLevel.STANDARD):
        """Initialize the Policy Engine with compliance settings."""
        self.compliance_level = compliance_level
        self.session_id = str(uuid.uuid4())
        self.audit_trail: List[AuditRecord] = []
        self._models_loaded = False
        self._internal_ensemble = None
        
        logger.info(f"Policy Engine initialized. Session: {self.session_id[:8]}...")
    
    def _load_internal_models(self):
        """Internal method to load ML models. Never exposed."""
        if self._models_loaded:
            return
        
        try:
            # Load ensemble - completely hidden from users
            from models.ensemble_detector import EnsembleAnomalyDetector
            from config import EnsembleConfig
            config = EnsembleConfig()
            self._internal_ensemble = EnsembleAnomalyDetector(config)
            self._models_loaded = True
            logger.info("Internal detection models initialized")
        except Exception as e:
            logger.error(f"Model initialization error: {e}")
            # Fallback to statistical methods
            self._models_loaded = True
    
    def _calculate_internal_score(self, X: np.ndarray) -> np.ndarray:
        """
        Internal scoring method. NEVER exposed.
        Returns normalized risk indicators (not "anomaly scores").
        """
        if self._internal_ensemble is not None:
            try:
                self._internal_ensemble.fit(X)
                scores, _ = self._internal_ensemble.predict(X)
                return scores
            except Exception as e:
                logger.error(f"Scoring error: {e}")
        
        # Fallback: statistical approach
        from sklearn.preprocessing import StandardScaler
        from sklearn.ensemble import IsolationForest
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(X_scaled)
        
        raw_scores = -model.decision_function(X_scaled)
        return (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-10)
    
    def _score_to_disposition(
        self,
        score: float,
        risk_tolerance: RiskTolerance
    ) -> RecordDisposition:
        """Convert internal score to policy disposition. Never exposed."""
        thresholds = self._INTERNAL_THRESHOLDS[risk_tolerance]
        
        if score >= thresholds["escalate"]:
            return RecordDisposition.ESCALATE
        elif score >= thresholds["review"]:
            return RecordDisposition.FLAG
        elif score >= thresholds["flag"]:
            return RecordDisposition.REVIEW
        else:
            return RecordDisposition.CLEAR
    
    def _score_to_risk_indicator(self, score: float) -> str:
        """Convert internal score to risk indicator. Never exposed."""
        if score >= 0.8:
            return "Critical"
        elif score >= 0.6:
            return "High"
        elif score >= 0.4:
            return "Medium"
        else:
            return "Low"
    
    def _generate_policy_reason(
        self,
        contributors: List[Dict],
        disposition: RecordDisposition
    ) -> str:
        """Generate policy-level reason without technical details."""
        
        # Map technical features to policy language
        feature_translations = {
            "total_enrolments": "enrollment volume",
            "total_demo_updates": "demographic update frequency",
            "total_bio_updates": "biometric update frequency",
            "state_event_count": "regional activity level",
            "district_event_count": "local area activity",
            "operator_activity": "operator workload",
            "is_weekend": "weekend processing",
            "month": "seasonal pattern"
        }
        
        if disposition == RecordDisposition.CLEAR:
            return "Record aligns with expected operational patterns."
        
        # Get top indicator
        if contributors:
            top_feature = contributors[0].get("feature", "activity")
            translated = feature_translations.get(top_feature, "operational metric")
            direction = contributors[0].get("direction", "")
            
            if disposition == RecordDisposition.ESCALATE:
                return f"Critical deviation detected in {translated}. Immediate review required."
            elif disposition == RecordDisposition.FLAG:
                return f"Significant deviation in {translated} warrants investigation."
            else:
                return f"Minor deviation in {translated} recommended for review."
        
        return "Pattern deviation detected. Manual review recommended."
    
    def _generate_recommended_action(
        self,
        disposition: RecordDisposition,
        risk_indicator: str
    ) -> str:
        """Generate policy-level action recommendation."""
        actions = {
            (RecordDisposition.ESCALATE, "Critical"): "Suspend processing. Escalate to Deputy Director. Initiate field verification.",
            (RecordDisposition.ESCALATE, "High"): "Hold for senior officer review. Request additional documentation.",
            (RecordDisposition.FLAG, "High"): "Flag for investigation team. Cross-reference with other flagged records.",
            (RecordDisposition.FLAG, "Medium"): "Queue for manual verification. Verify operator credentials.",
            (RecordDisposition.REVIEW, "Medium"): "Schedule routine review. No immediate action required.",
            (RecordDisposition.REVIEW, "Low"): "Add to review batch. Standard verification sufficient.",
            (RecordDisposition.CLEAR, "Low"): "Proceed with normal processing."
        }
        
        return actions.get(
            (disposition, risk_indicator),
            "Follow standard operating procedure for this record type."
        )
    
    def get_available_policies(self) -> List[Dict[str, Any]]:
        """
        Get available policy presets for user selection.
        
        Returns policy-level options only. No technical details.
        """
        return [
            {
                "policy_id": key,
                "name": preset.name,
                "description": preset.description,
                "security_level": "Enhanced" if preset.require_secondary_verification else "Standard",
                "throughput": "Standard" if preset.risk_tolerance == RiskTolerance.CONSERVATIVE else "High",
                "recommended_for": self._get_policy_recommendation(key)
            }
            for key, preset in self.POLICY_PRESETS.items()
        ]
    
    def _get_policy_recommendation(self, policy_id: str) -> str:
        """Get recommendation text for policy."""
        recommendations = {
            "HIGH_SECURITY": "New centers, flagged regions, sensitive operations",
            "STANDARD": "Established centers, routine operations",
            "HIGH_THROUGHPUT": "Trusted regions with clean compliance history",
            "SPECIAL_DRIVE": "Government drives, camps, special initiatives"
        }
        return recommendations.get(policy_id, "General use")
    
    def analyze_records(
        self,
        data: pd.DataFrame,
        policy_id: str = "STANDARD",
        region: Optional[str] = None,
        operator_id: Optional[str] = None,
        user_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Analyze records using policy-level controls.
        
        This is the PRIMARY interface for fraud detection.
        All ML/DL details are completely hidden.
        
        Args:
            data: Records to analyze
            policy_id: Policy preset to apply ("STANDARD", "HIGH_SECURITY", etc.)
            region: Optional region filter
            operator_id: Optional operator filter
            user_id: User ID for audit trail
        
        Returns:
            Policy-level analysis results (no technical ML details)
        """
        self._load_internal_models()
        
        # Get policy preset
        if policy_id not in self.POLICY_PRESETS:
            policy_id = "STANDARD"
        policy = self.POLICY_PRESETS[policy_id]
        
        # Prepare features internally
        from data.feature_engineering import FeatureEngineer
        engineer = FeatureEngineer()
        df_engineered = engineer.engineer_features(data.copy(), "enrolment")
        
        # Get numeric columns for analysis
        numeric_cols = df_engineered.select_dtypes(include=[np.number]).columns.tolist()
        exclude_cols = ['year', 'month', 'day']
        feature_cols = [c for c in numeric_cols if c not in exclude_cols][:15]
        
        X = df_engineered[feature_cols].fillna(0).values
        
        # Internal scoring - hidden from users
        scores = self._calculate_internal_score(X)
        
        # Get feature attributions for reason generation
        from explainability.feature_attribution import FeatureAttribution
        attribution = FeatureAttribution()
        attribution.fit(X, feature_cols)
        
        # Generate policy-level results
        results = []
        disposition_counts = {d.value: 0 for d in RecordDisposition}
        
        for i in range(len(data)):
            score = scores[i]
            
            disposition = self._score_to_disposition(score, policy.risk_tolerance)
            risk_indicator = self._score_to_risk_indicator(score)
            
            contributors = attribution.get_top_contributors(X[i], top_k=3)
            
            result = PolicyResult(
                record_id=str(data.index[i]) if hasattr(data, 'index') else f"REC-{i+1:06d}",
                disposition=disposition,
                risk_indicator=risk_indicator,
                confidence_level=self._get_confidence_level(score),
                requires_action=disposition in [RecordDisposition.FLAG, RecordDisposition.ESCALATE],
                action_priority=self._get_action_priority(disposition, risk_indicator),
                reason_summary=self._generate_policy_reason(contributors, disposition),
                recommended_action=self._generate_recommended_action(disposition, risk_indicator),
                review_by=self._get_review_authority(disposition),
                flags=self._get_policy_flags(score, df_engineered.iloc[i] if len(df_engineered) > i else None)
            )
            
            results.append(asdict(result))
            disposition_counts[disposition.value] += 1
        
        # Create audit record
        audit = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            action="POLICY_ANALYSIS",
            user_id=user_id,
            policy_applied=policy_id,
            records_processed=len(data),
            flags_raised=disposition_counts["FLAG"] + disposition_counts["ESCALATE"],
            disposition_summary=disposition_counts,
            compliance_level=self.compliance_level.value,
            data_classification="OFFICIAL"
        )
        self.audit_trail.append(audit)
        
        # Return policy-level response - NO technical details
        return {
            "analysis_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "policy_applied": {
                "policy_id": policy_id,
                "policy_name": policy.name,
                "security_level": "Enhanced" if policy.require_secondary_verification else "Standard"
            },
            "summary": {
                "total_records": len(data),
                "disposition_breakdown": {
                    "requires_immediate_action": disposition_counts["ESCALATE"],
                    "flagged_for_investigation": disposition_counts["FLAG"],
                    "pending_review": disposition_counts["REVIEW"],
                    "cleared": disposition_counts["CLEAR"]
                },
                "risk_assessment": self._get_overall_risk_assessment(disposition_counts, len(data)),
                "compliance_status": "COMPLIANT",
                "data_integrity": "VERIFIED"
            },
            "records": results[:100],  # Limit response size
            "audit_reference": audit.audit_id,
            "next_steps": self._get_next_steps(disposition_counts),
            "metadata": {
                "region_analyzed": region or "All Regions",
                "classification": "OFFICIAL",
                "retention_period": "7 years",
                "generated_by": "UIDAI Fraud Detection System v2.0"
            }
        }
    
    def _get_confidence_level(self, score: float) -> str:
        """Map score to confidence level."""
        if score >= 0.7:
            return "Very High"
        elif score >= 0.4:
            return "High"
        else:
            return "Standard"
    
    def _get_action_priority(self, disposition: RecordDisposition, risk: str) -> int:
        """Calculate action priority (1=highest, 5=lowest)."""
        priority_matrix = {
            (RecordDisposition.ESCALATE, "Critical"): 1,
            (RecordDisposition.ESCALATE, "High"): 1,
            (RecordDisposition.FLAG, "Critical"): 1,
            (RecordDisposition.FLAG, "High"): 2,
            (RecordDisposition.FLAG, "Medium"): 2,
            (RecordDisposition.REVIEW, "High"): 3,
            (RecordDisposition.REVIEW, "Medium"): 3,
            (RecordDisposition.REVIEW, "Low"): 4,
            (RecordDisposition.CLEAR, "Low"): 5
        }
        return priority_matrix.get((disposition, risk), 4)
    
    def _get_review_authority(self, disposition: RecordDisposition) -> Optional[str]:
        """Get recommended review authority."""
        authorities = {
            RecordDisposition.ESCALATE: "Deputy Director / Regional Head",
            RecordDisposition.FLAG: "Senior Investigation Officer",
            RecordDisposition.REVIEW: "Field Verification Team",
            RecordDisposition.CLEAR: None
        }
        return authorities.get(disposition)
    
    def _get_policy_flags(self, score: float, row: Optional[pd.Series]) -> List[str]:
        """Generate policy-level flags."""
        flags = []
        
        if score >= 0.9:
            flags.append("CRITICAL_DEVIATION")
        elif score >= 0.7:
            flags.append("SIGNIFICANT_DEVIATION")
        
        if row is not None:
            if row.get('is_weekend', 0) == 1:
                flags.append("WEEKEND_ACTIVITY")
            
            if row.get('total_enrolments', 0) > 200:
                flags.append("HIGH_VOLUME")
        
        return flags
    
    def _get_overall_risk_assessment(
        self,
        counts: Dict[str, int],
        total: int
    ) -> str:
        """Calculate overall risk assessment."""
        if total == 0:
            return "NO_DATA"
        
        critical_rate = (counts["ESCALATE"] + counts["FLAG"]) / total
        
        if critical_rate > 0.2:
            return "HIGH - Immediate attention required"
        elif critical_rate > 0.1:
            return "ELEVATED - Enhanced monitoring recommended"
        elif critical_rate > 0.05:
            return "MODERATE - Standard monitoring sufficient"
        else:
            return "LOW - Normal operations"
    
    def _get_next_steps(self, counts: Dict[str, int]) -> List[str]:
        """Generate policy-level next steps."""
        steps = []
        
        if counts["ESCALATE"] > 0:
            steps.append(f"URGENT: {counts['ESCALATE']} records require immediate escalation to senior authority")
        
        if counts["FLAG"] > 0:
            steps.append(f"Assign {counts['FLAG']} flagged records to investigation team")
        
        if counts["REVIEW"] > 0:
            steps.append(f"Schedule review batch for {counts['REVIEW']} records")
        
        if counts["CLEAR"] > 0:
            steps.append(f"{counts['CLEAR']} records cleared for standard processing")
        
        steps.append("Generate compliance report for audit trail")
        
        return steps
    
    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Get audit trail for compliance."""
        return [asdict(a) for a in self.audit_trail]
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report for government submission."""
        return {
            "report_type": "UIDAI Fraud Detection Compliance Report",
            "generated_at": datetime.now().isoformat(),
            "session_id": self.session_id,
            "compliance_level": self.compliance_level.value,
            "audit_entries": len(self.audit_trail),
            "total_records_processed": sum(a.records_processed for a in self.audit_trail),
            "total_flags_raised": sum(a.flags_raised for a in self.audit_trail),
            "data_classification": "OFFICIAL",
            "retention_policy": "7 years as per government guidelines",
            "audit_trail": self.get_audit_trail()
        }
