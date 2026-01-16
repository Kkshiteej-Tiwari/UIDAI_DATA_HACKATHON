"""
Policy Package - Government-Ready Abstraction Layer

Provides policy-level controls for UIDAI fraud detection
with all ML/DL details completely hidden.

Modules:
- policy_engine: Core policy management
- intent_resolver: User intent to signal mapping
- dataset_orchestrator: Data retrieval (internal)
- strategy_selector: Analysis strategy selection
- analysis_output: Risk assessment & auditor explanations
"""
from policy.policy_engine import (
    PolicyEngine,
    RiskTolerance,
    RecordDisposition,
    ComplianceLevel,
    PolicyPreset,
    PolicyResult,
    AuditRecord
)

from policy.intent_resolver import (
    IntentResolutionEngine,
    UserContext,
    VigilanceLevel,
    TimePeriod,
    resolve_intent
)

from policy.dataset_orchestrator import (
    DatasetOrchestrationLayer,
    OrchestrationFacade,
    OrchestrationResult,
    get_analysis_data
)

from policy.strategy_selector import (
    AnalysisStrategySelector,
    AnalysisStrategy,
    select_strategies
)

from policy.analysis_output import (
    UnifiedRiskEngine,
    GovernmentExplanationLayer,
    RiskLevel,
    ConfidenceLevel,
    RiskAssessment,
    AuditorExplanation,
    StrategyOutput,
    calculate_unified_risk,
    generate_auditor_explanation
)

__all__ = [
    # Policy Engine
    'PolicyEngine', 'RiskTolerance', 'RecordDisposition',
    'ComplianceLevel', 'PolicyPreset', 'PolicyResult', 'AuditRecord',
    
    # Intent Resolver
    'IntentResolutionEngine', 'UserContext', 'VigilanceLevel',
    'TimePeriod', 'resolve_intent',
    
    # Dataset Orchestrator
    'DatasetOrchestrationLayer', 'OrchestrationFacade',
    'OrchestrationResult', 'get_analysis_data',
    
    # Strategy Selector
    'AnalysisStrategySelector', 'AnalysisStrategy', 'select_strategies',
    
    # Analysis Output (Risk + Explanation)
    'UnifiedRiskEngine', 'GovernmentExplanationLayer',
    'RiskLevel', 'ConfidenceLevel', 'RiskAssessment',
    'AuditorExplanation', 'StrategyOutput',
    'calculate_unified_risk', 'generate_auditor_explanation'
]
