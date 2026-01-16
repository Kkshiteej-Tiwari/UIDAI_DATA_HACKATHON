"""
Analysis Output Module

Unified module for:
1. Risk Assessment (Unified Risk Engine)
2. Auditor Explanations (Government Explanation Layer)

DESIGN PRINCIPLES:
- Consistent output across all intents
- All thresholds internal only
- Plain language for auditors
- No ML/algorithm terminology exposed
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS - PUBLIC
# =============================================================================

class RiskLevel(str, Enum):
    """Risk level classification - government-friendly terminology."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class ConfidenceLevel(str, Enum):
    """Confidence level in risk assessment."""
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    VERY_HIGH = "Very High"


class ExplanationType(str, Enum):
    """Types of explanations."""
    OBSERVATION = "observation"
    CONCERN = "concern"
    RECOMMENDATION = "recommend"
    CONTEXT = "context"


# =============================================================================
# INTERNAL CONFIGURATION - NEVER EXPOSED
# =============================================================================

class _InternalConfig:
    """All internal thresholds and mappings. NEVER exposed."""
    
    # Risk thresholds
    RISK_LOW_UPPER = 30
    RISK_MEDIUM_UPPER = 60
    RISK_HIGH_UPPER = 85
    
    # Confidence thresholds
    CONFIDENCE_LOW = 0.4
    CONFIDENCE_MODERATE = 0.6
    CONFIDENCE_HIGH = 0.8
    
    # Strategy weights
    STRATEGY_WEIGHTS = {
        "behavioral_baseline": 0.25,
        "regional_deviation": 0.20,
        "pattern_consistency": 0.20,
        "temporal_trend": 0.10,
        "operator_profiling": 0.25,
        "cross_reference": 0.15,
        "volume_surge": 0.15,
        "quality_assessment": 0.10
    }
    
    # Vigilance modifiers
    VIGILANCE_MODIFIERS = {
        "routine": 0.85,
        "standard": 1.0,
        "enhanced": 1.15,
        "maximum": 1.3
    }
    
    # Term translations (ML → Government)
    TERM_TRANSLATIONS = {
        "anomaly": "irregularity",
        "anomaly score": "concern level",
        "outlier": "exception",
        "cluster": "pattern group",
        "prediction": "assessment",
        "feature": "indicator",
        "threshold": "standard",
        "model": "system",
        "algorithm": "process",
        "dataset": "records",
        "z-score": "deviation level",
        "mean": "average",
        "variance": "spread",
        "correlation": "relationship"
    }


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StrategyOutput:
    """Output from a single analysis strategy."""
    strategy_id: str
    strategy_name: str
    raw_score: float
    records_analyzed: int
    flagged_count: int
    confidence: float


@dataclass
class RiskAssessment:
    """Unified risk assessment output."""
    risk_index: int
    risk_level: RiskLevel
    confidence_score: float
    confidence_level: ConfidenceLevel
    assessment_summary: str
    key_findings: List[str]
    recommended_actions: List[str]
    assessment_id: str
    timestamp: str
    records_analyzed: int
    strategies_applied: int


@dataclass
class Observation:
    """A single human-readable observation."""
    observation_type: ExplanationType
    title: str
    description: str
    severity: str
    location: Optional[str]
    time_context: Optional[str]


@dataclass
class AuditorExplanation:
    """Complete explanation package for auditors."""
    summary: str
    observations: List[Observation]
    context: str
    next_steps: List[str]
    glossary: Dict[str, str]
    generated_at: str


# =============================================================================
# UNIFIED RISK ENGINE
# =============================================================================

class UnifiedRiskEngine:
    """
    Aggregates outputs from multiple analysis strategies
    into consistent, unified risk metrics.
    
    OUTPUT:
    - Risk Index: 0-100
    - Risk Level: Low/Medium/High/Critical
    - Confidence Score: 0.0-1.0
    """
    
    def __init__(self, vigilance: str = "standard"):
        self.vigilance = vigilance
        self._modifier = _InternalConfig.VIGILANCE_MODIFIERS.get(vigilance, 1.0)
    
    def aggregate(
        self,
        strategy_outputs: List[StrategyOutput],
        context: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """Aggregate strategy outputs into unified risk assessment."""
        if not strategy_outputs:
            return self._empty_assessment()
        
        # Calculate weighted score
        weighted_score = self._calculate_weighted_score(strategy_outputs)
        adjusted_score = min(1.0, weighted_score * self._modifier)
        
        # Convert to metrics
        risk_index = int(round(adjusted_score * 100))
        risk_level = self._to_risk_level(risk_index)
        confidence_score = self._calculate_confidence(strategy_outputs)
        confidence_level = self._to_confidence_level(confidence_score)
        
        # Generate outputs
        summary = self._generate_summary(risk_level, strategy_outputs)
        findings = self._extract_findings(strategy_outputs)
        actions = self._generate_actions(risk_level)
        
        import uuid
        return RiskAssessment(
            risk_index=risk_index,
            risk_level=risk_level,
            confidence_score=round(confidence_score, 2),
            confidence_level=confidence_level,
            assessment_summary=summary,
            key_findings=findings,
            recommended_actions=actions,
            assessment_id=str(uuid.uuid4())[:12],
            timestamp=datetime.now().isoformat(),
            records_analyzed=sum(s.records_analyzed for s in strategy_outputs),
            strategies_applied=len(strategy_outputs)
        )
    
    def _calculate_weighted_score(self, outputs: List[StrategyOutput]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0
        for output in outputs:
            weight = _InternalConfig.STRATEGY_WEIGHTS.get(output.strategy_id, 0.15)
            weighted_sum += output.raw_score * weight
            total_weight += weight
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _to_risk_level(self, risk_index: int) -> RiskLevel:
        if risk_index <= _InternalConfig.RISK_LOW_UPPER:
            return RiskLevel.LOW
        elif risk_index <= _InternalConfig.RISK_MEDIUM_UPPER:
            return RiskLevel.MEDIUM
        elif risk_index <= _InternalConfig.RISK_HIGH_UPPER:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL
    
    def _calculate_confidence(self, outputs: List[StrategyOutput]) -> float:
        if not outputs:
            return 0.0
        base = np.mean([o.confidence for o in outputs])
        bonus = min(0.15, len(outputs) * 0.03)
        total_records = sum(o.records_analyzed for o in outputs)
        penalty = 0.1 if total_records < 100 else (0.05 if total_records < 500 else 0)
        return min(1.0, max(0.0, base + bonus - penalty))
    
    def _to_confidence_level(self, score: float) -> ConfidenceLevel:
        if score < _InternalConfig.CONFIDENCE_LOW:
            return ConfidenceLevel.LOW
        elif score < _InternalConfig.CONFIDENCE_MODERATE:
            return ConfidenceLevel.MODERATE
        elif score < _InternalConfig.CONFIDENCE_HIGH:
            return ConfidenceLevel.HIGH
        return ConfidenceLevel.VERY_HIGH
    
    def _generate_summary(self, level: RiskLevel, outputs: List[StrategyOutput]) -> str:
        total = sum(o.records_analyzed for o in outputs)
        flagged = sum(o.flagged_count for o in outputs)
        summaries = {
            RiskLevel.LOW: f"Analysis of {total:,} records shows normal patterns. {flagged} flagged for routine review.",
            RiskLevel.MEDIUM: f"Analysis of {total:,} records found moderate deviations. {flagged} require attention.",
            RiskLevel.HIGH: f"Analysis of {total:,} records revealed significant anomalies. {flagged} need investigation.",
            RiskLevel.CRITICAL: f"CRITICAL: Analysis of {total:,} records detected severe irregularities. {flagged} require immediate action."
        }
        return summaries.get(level, summaries[RiskLevel.LOW])
    
    def _extract_findings(self, outputs: List[StrategyOutput]) -> List[str]:
        findings = []
        for output in sorted(outputs, key=lambda x: x.raw_score, reverse=True)[:3]:
            if output.raw_score >= 0.7:
                findings.append(f"High concern: {output.strategy_name} detected {output.flagged_count} anomalies")
            elif output.raw_score >= 0.4:
                findings.append(f"Moderate concern: {output.strategy_name} identified {output.flagged_count} items for review")
        return findings if findings else ["No significant anomalies detected"]
    
    def _generate_actions(self, level: RiskLevel) -> List[str]:
        actions = {
            RiskLevel.LOW: ["Continue routine monitoring", "Archive for compliance"],
            RiskLevel.MEDIUM: ["Review flagged records within 48 hours", "Notify team lead"],
            RiskLevel.HIGH: ["Immediate review required", "Notify senior management", "Initiate investigation"],
            RiskLevel.CRITICAL: ["URGENT: Escalate to Director", "Suspend affected operations", "Full investigation required"]
        }
        return actions.get(level, actions[RiskLevel.LOW])
    
    def _empty_assessment(self) -> RiskAssessment:
        import uuid
        return RiskAssessment(
            risk_index=0, risk_level=RiskLevel.LOW,
            confidence_score=0.0, confidence_level=ConfidenceLevel.LOW,
            assessment_summary="No data available",
            key_findings=["Insufficient data"], recommended_actions=["Ensure data availability"],
            assessment_id=str(uuid.uuid4())[:12], timestamp=datetime.now().isoformat(),
            records_analyzed=0, strategies_applied=0
        )
    
    def to_dict(self, assessment: RiskAssessment) -> Dict[str, Any]:
        return {
            "risk_metrics": {
                "risk_index": assessment.risk_index,
                "risk_level": assessment.risk_level.value,
                "confidence_score": assessment.confidence_score,
                "confidence_level": assessment.confidence_level.value
            },
            "summary": assessment.assessment_summary,
            "key_findings": assessment.key_findings,
            "recommended_actions": assessment.recommended_actions,
            "metadata": {
                "assessment_id": assessment.assessment_id,
                "timestamp": assessment.timestamp,
                "records_analyzed": assessment.records_analyzed,
                "strategies_applied": assessment.strategies_applied
            }
        }


# =============================================================================
# GOVERNMENT EXPLANATION LAYER
# =============================================================================

class GovernmentExplanationLayer:
    """
    Converts analytical findings into human-readable observations.
    NO ML terminology. Suitable for UIDAI auditors.
    """
    
    def __init__(self):
        self._translations = _InternalConfig.TERM_TRANSLATIONS
    
    def explain(
        self,
        risk_assessment: Dict[str, Any],
        findings: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> AuditorExplanation:
        """Generate auditor-friendly explanation."""
        risk_level = risk_assessment.get("risk_metrics", {}).get("risk_level", "Low")
        risk_index = risk_assessment.get("risk_metrics", {}).get("risk_index", 0)
        
        summary = self._generate_summary(risk_level, context)
        observations = self._findings_to_observations(findings, risk_level)
        context_text = self._generate_context(context)
        next_steps = self._generate_next_steps(risk_level)
        
        return AuditorExplanation(
            summary=summary,
            observations=observations,
            context=context_text,
            next_steps=next_steps,
            glossary={"Flagged": "Marked for review", "Deviation": "Difference from expected pattern"},
            generated_at=datetime.now().strftime("%d %B %Y at %H:%M")
        )
    
    def _generate_summary(self, risk_level: str, context: Optional[Dict]) -> str:
        geo = context.get("geographic", "All India") if context else "All India"
        temporal = context.get("temporal", "recent period") if context else "recent period"
        
        summaries = {
            "Low": f"Assessment of operations in {geo} during {temporal} shows results within expected ranges. No immediate concerns.",
            "Medium": f"Assessment of operations in {geo} during {temporal} identified some variations. Several items marked for review.",
            "High": f"Assessment of operations in {geo} during {temporal} revealed notable deviations requiring prompt attention.",
            "Critical": f"URGENT: Assessment of operations in {geo} during {temporal} uncovered serious irregularities requiring immediate action."
        }
        return summaries.get(risk_level, summaries["Low"])
    
    def _findings_to_observations(self, findings: List[Dict], risk_level: str) -> List[Observation]:
        observations = []
        for finding in findings:
            obs = self._convert_finding(finding)
            if obs:
                observations.append(obs)
        
        if not observations:
            observations.append(Observation(
                observation_type=ExplanationType.OBSERVATION,
                title="Assessment Complete",
                description="No issues requiring immediate attention.",
                severity="Minor", location=None, time_context=None
            ))
        return observations
    
    def _convert_finding(self, finding: Dict) -> Optional[Observation]:
        finding_type = finding.get("type", "general")
        score = finding.get("score", 0)
        location = finding.get("location", finding.get("region", "the affected area"))
        
        severity = "Significant" if score > 0.7 else ("Moderate" if score > 0.4 else "Minor")
        
        if finding_type in ["volume_spike", "volume_surge", "volume"]:
            return Observation(
                observation_type=ExplanationType.OBSERVATION,
                title="Unusual Activity Level",
                description=f"Operations in {location} showed higher than expected activity levels.",
                severity=severity, location=location, time_context=finding.get("time_period")
            )
        elif finding_type in ["operator", "operator_activity"]:
            return Observation(
                observation_type=ExplanationType.CONCERN,
                title="Operator Performance Noted",
                description="Operator work patterns showed deviations from expected norms.",
                severity=severity, location=location, time_context=None
            )
        elif finding_type in ["regional", "geographic"]:
            return Observation(
                observation_type=ExplanationType.OBSERVATION,
                title=f"Regional Variation - {location}",
                description=f"Operations in {location} differ from other regions.",
                severity=severity, location=location, time_context=None
            )
        else:
            return Observation(
                observation_type=ExplanationType.OBSERVATION,
                title=finding.get("title", "Finding"),
                description=self._translate(finding.get("description", "Item identified for review.")),
                severity=severity, location=location, time_context=finding.get("time_period")
            )
    
    def _translate(self, text: str) -> str:
        for tech, gov in self._translations.items():
            text = text.replace(tech, gov).replace(tech.title(), gov.title())
        return text
    
    def _generate_context(self, context: Optional[Dict]) -> str:
        if not context:
            return "This assessment covers routine monitoring."
        geo = context.get("geographic", "All India")
        temporal = context.get("temporal", "recent period")
        return f"This assessment covered operations in {geo} during {temporal}."
    
    def _generate_next_steps(self, risk_level: str) -> List[str]:
        steps = {
            "Low": ["File for compliance", "Continue routine monitoring"],
            "Medium": ["Review flagged items", "Brief team leads", "Schedule follow-up"],
            "High": ["Prompt review required", "Notify senior officers", "Field verification"],
            "Critical": ["Escalate immediately", "Suspend affected operations", "Full investigation"]
        }
        return steps.get(risk_level, steps["Low"])
    
    def to_dict(self, explanation: AuditorExplanation) -> Dict[str, Any]:
        return {
            "summary": explanation.summary,
            "context": explanation.context,
            "observations": [
                {"type": o.observation_type.value, "title": o.title, "description": o.description,
                 "severity": o.severity, "location": o.location, "time_context": o.time_context}
                for o in explanation.observations
            ],
            "next_steps": explanation.next_steps,
            "glossary": explanation.glossary,
            "generated_at": explanation.generated_at
        }
    
    def to_text(self, explanation: AuditorExplanation) -> str:
        lines = [
            "=" * 60, "UIDAI OPERATIONS ASSESSMENT REPORT",
            f"Generated: {explanation.generated_at}", "=" * 60,
            "\nSUMMARY", "-" * 40, explanation.summary,
            "\nCONTEXT", "-" * 40, explanation.context,
            "\nOBSERVATIONS", "-" * 40
        ]
        for i, o in enumerate(explanation.observations, 1):
            lines.append(f"{i}. {o.title} [{o.severity}]\n   {o.description}")
        lines.extend(["\nNEXT STEPS", "-" * 40] + [f"• {s}" for s in explanation.next_steps])
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_unified_risk(
    strategy_results: List[Dict[str, Any]],
    vigilance: str = "standard"
) -> Dict[str, Any]:
    """Calculate unified risk from strategy results."""
    outputs = [
        StrategyOutput(
            strategy_id=r.get("strategy_id", "unknown"),
            strategy_name=r.get("strategy_name", "Unknown"),
            raw_score=r.get("score", r.get("raw_score", 0.0)),
            records_analyzed=r.get("records_analyzed", 0),
            flagged_count=r.get("flagged_count", r.get("flagged", 0)),
            confidence=r.get("confidence", 0.7)
        ) for r in strategy_results
    ]
    engine = UnifiedRiskEngine(vigilance)
    return engine.to_dict(engine.aggregate(outputs))


def generate_auditor_explanation(
    risk_assessment: Dict[str, Any],
    findings: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None,
    output_format: str = "dict"
) -> Any:
    """Generate auditor-friendly explanation."""
    layer = GovernmentExplanationLayer()
    explanation = layer.explain(risk_assessment, findings, context)
    return layer.to_text(explanation) if output_format == "text" else layer.to_dict(explanation)


# Example
if __name__ == "__main__":
    print("=" * 60)
    print("ANALYSIS OUTPUT MODULE - DEMO")
    print("=" * 60)
    
    # Test risk engine
    outputs = [
        StrategyOutput("behavioral_baseline", "Behavioral Analysis", 0.45, 500, 23, 0.82),
        StrategyOutput("operator_profiling", "Operator Profiling", 0.62, 500, 31, 0.75)
    ]
    
    engine = UnifiedRiskEngine("enhanced")
    assessment = engine.aggregate(outputs)
    print(f"\nRisk Index: {assessment.risk_index}/100")
    print(f"Risk Level: {assessment.risk_level.value}")
    print(f"Confidence: {assessment.confidence_score}")
    
    # Test explanation
    risk_dict = engine.to_dict(assessment)
    findings = [{"type": "volume_surge", "location": "Pune", "score": 0.65}]
    explanation = generate_auditor_explanation(risk_dict, findings, {"geographic": "Maharashtra"}, "text")
    print("\n" + explanation)
