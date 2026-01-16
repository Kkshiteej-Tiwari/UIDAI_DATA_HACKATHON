"""
Analysis Strategy Selector

Selects analytical strategies based on monitoring needs.
Internally maps strategies to ML/DL techniques - NEVER exposed externally.

DESIGN PRINCIPLES:
- Strategy names are government-friendly
- Algorithm names are NEVER exposed
- Strategy selection is automatic or user-guided
- All ML/DL mapping is internal only
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# STRATEGY DEFINITIONS (PUBLIC)
# =============================================================================

class AnalysisStrategy(str, Enum):
    """
    Available analysis strategies.
    These are the ONLY options exposed to users.
    """
    BEHAVIORAL_BASELINE = "behavioral_baseline"
    REGIONAL_DEVIATION = "regional_deviation"
    PATTERN_CONSISTENCY = "pattern_consistency"
    TEMPORAL_TREND = "temporal_trend"
    OPERATOR_PROFILING = "operator_profiling"
    CROSS_REFERENCE = "cross_reference"
    VOLUME_SURGE = "volume_surge"
    QUALITY_ASSESSMENT = "quality_assessment"


@dataclass
class StrategyInfo:
    """Public information about a strategy."""
    strategy_id: str
    name: str
    description: str
    use_case: str
    typical_findings: List[str]
    recommended_for: List[str]
    processing_time: str  # "Fast", "Standard", "Comprehensive"


# =============================================================================
# INTERNAL ML MAPPING - NEVER EXPOSED
# =============================================================================

class _MLTechnique(str, Enum):
    """Internal ML technique identifiers. NEVER exposed."""
    ISOLATION_FOREST = "isolation_forest"
    HDBSCAN = "hdbscan"
    AUTOENCODER = "autoencoder"
    ONE_CLASS_SVM = "one_class_svm"
    LOCAL_OUTLIER_FACTOR = "lof"
    DBSCAN = "dbscan"
    STATISTICAL_ZSCORE = "zscore"
    IQR_DETECTION = "iqr"
    MOVING_AVERAGE = "moving_avg"
    EXPONENTIAL_SMOOTHING = "exp_smooth"
    PROPHET = "prophet"
    LSTM = "lstm"


@dataclass
class _InternalStrategyConfig:
    """Internal configuration for a strategy. NEVER exposed."""
    primary_techniques: List[_MLTechnique]
    fallback_techniques: List[_MLTechnique]
    ensemble_method: str  # "voting", "averaging", "stacking"
    min_confidence: float
    hyperparameters: Dict[str, Any]


# Strategy to ML technique mapping - COMPLETELY INTERNAL
_STRATEGY_TO_ML_MAP: Dict[AnalysisStrategy, _InternalStrategyConfig] = {
    
    AnalysisStrategy.BEHAVIORAL_BASELINE: _InternalStrategyConfig(
        primary_techniques=[_MLTechnique.ISOLATION_FOREST, _MLTechnique.AUTOENCODER],
        fallback_techniques=[_MLTechnique.STATISTICAL_ZSCORE],
        ensemble_method="averaging",
        min_confidence=0.7,
        hyperparameters={
            "contamination": 0.1,
            "n_estimators": 100,
            "encoding_dim": 8
        }
    ),
    
    AnalysisStrategy.REGIONAL_DEVIATION: _InternalStrategyConfig(
        primary_techniques=[_MLTechnique.HDBSCAN, _MLTechnique.LOCAL_OUTLIER_FACTOR],
        fallback_techniques=[_MLTechnique.DBSCAN, _MLTechnique.IQR_DETECTION],
        ensemble_method="voting",
        min_confidence=0.65,
        hyperparameters={
            "min_cluster_size": 5,
            "n_neighbors": 20,
            "eps": 0.5
        }
    ),
    
    AnalysisStrategy.PATTERN_CONSISTENCY: _InternalStrategyConfig(
        primary_techniques=[_MLTechnique.AUTOENCODER, _MLTechnique.ISOLATION_FOREST],
        fallback_techniques=[_MLTechnique.ONE_CLASS_SVM],
        ensemble_method="stacking",
        min_confidence=0.75,
        hyperparameters={
            "encoding_layers": [64, 32, 16],
            "reconstruction_threshold": 0.05
        }
    ),
    
    AnalysisStrategy.TEMPORAL_TREND: _InternalStrategyConfig(
        primary_techniques=[_MLTechnique.MOVING_AVERAGE, _MLTechnique.EXPONENTIAL_SMOOTHING],
        fallback_techniques=[_MLTechnique.STATISTICAL_ZSCORE],
        ensemble_method="averaging",
        min_confidence=0.6,
        hyperparameters={
            "window_size": 7,
            "alpha": 0.3,
            "seasonality": "monthly"
        }
    ),
    
    AnalysisStrategy.OPERATOR_PROFILING: _InternalStrategyConfig(
        primary_techniques=[_MLTechnique.ISOLATION_FOREST, _MLTechnique.LOCAL_OUTLIER_FACTOR],
        fallback_techniques=[_MLTechnique.IQR_DETECTION],
        ensemble_method="voting",
        min_confidence=0.8,
        hyperparameters={
            "contamination": 0.05,
            "n_neighbors": 10,
            "profile_features": ["volume", "speed", "error_rate"]
        }
    ),
    
    AnalysisStrategy.CROSS_REFERENCE: _InternalStrategyConfig(
        primary_techniques=[_MLTechnique.HDBSCAN, _MLTechnique.AUTOENCODER],
        fallback_techniques=[_MLTechnique.ISOLATION_FOREST],
        ensemble_method="stacking",
        min_confidence=0.7,
        hyperparameters={
            "correlation_threshold": 0.7,
            "min_samples": 10
        }
    ),
    
    AnalysisStrategy.VOLUME_SURGE: _InternalStrategyConfig(
        primary_techniques=[_MLTechnique.STATISTICAL_ZSCORE, _MLTechnique.IQR_DETECTION],
        fallback_techniques=[_MLTechnique.MOVING_AVERAGE],
        ensemble_method="voting",
        min_confidence=0.6,
        hyperparameters={
            "zscore_threshold": 3.0,
            "iqr_multiplier": 1.5
        }
    ),
    
    AnalysisStrategy.QUALITY_ASSESSMENT: _InternalStrategyConfig(
        primary_techniques=[_MLTechnique.AUTOENCODER, _MLTechnique.ONE_CLASS_SVM],
        fallback_techniques=[_MLTechnique.STATISTICAL_ZSCORE],
        ensemble_method="averaging",
        min_confidence=0.65,
        hyperparameters={
            "quality_features": ["completeness", "accuracy", "timeliness"],
            "threshold": 0.8
        }
    )
}


# =============================================================================
# PUBLIC STRATEGY INFORMATION
# =============================================================================

STRATEGY_CATALOG: Dict[AnalysisStrategy, StrategyInfo] = {
    
    AnalysisStrategy.BEHAVIORAL_BASELINE: StrategyInfo(
        strategy_id="behavioral_baseline",
        name="Behavioral Baseline Analysis",
        description="Establishes normal operational patterns and identifies deviations from expected behavior",
        use_case="Detecting unusual activity that deviates from established norms",
        typical_findings=[
            "Centers operating outside normal hours",
            "Unusual processing speeds",
            "Atypical workload distribution"
        ],
        recommended_for=["Routine monitoring", "New center evaluation", "Operator assessment"],
        processing_time="Standard"
    ),
    
    AnalysisStrategy.REGIONAL_DEVIATION: StrategyInfo(
        strategy_id="regional_deviation",
        name="Regional Deviation Detection",
        description="Compares regional metrics to identify areas with unusual patterns",
        use_case="Finding geographic clusters of suspicious activity",
        typical_findings=[
            "Districts with abnormal enrollment rates",
            "Regional concentration of issues",
            "Cross-border activity patterns"
        ],
        recommended_for=["State-level audits", "Regional reviews", "Hotspot identification"],
        processing_time="Standard"
    ),
    
    AnalysisStrategy.PATTERN_CONSISTENCY: StrategyInfo(
        strategy_id="pattern_consistency",
        name="Pattern Consistency Evaluation",
        description="Evaluates consistency of operational patterns across time and entities",
        use_case="Identifying anomalies in how operations are conducted",
        typical_findings=[
            "Inconsistent data entry patterns",
            "Unusual sequence of operations",
            "Deviation from standard procedures"
        ],
        recommended_for=["Quality audits", "Process compliance", "Training gap identification"],
        processing_time="Comprehensive"
    ),
    
    AnalysisStrategy.TEMPORAL_TREND: StrategyInfo(
        strategy_id="temporal_trend",
        name="Temporal Trend Analysis",
        description="Analyzes patterns over time to identify trends and anomalies",
        use_case="Detecting time-based irregularities and emerging patterns",
        typical_findings=[
            "End-of-month spikes",
            "Holiday period anomalies",
            "Gradual drift from baseline"
        ],
        recommended_for=["Trend monitoring", "Seasonal analysis", "Long-term assessment"],
        processing_time="Standard"
    ),
    
    AnalysisStrategy.OPERATOR_PROFILING: StrategyInfo(
        strategy_id="operator_profiling",
        name="Operator Performance Profiling",
        description="Profiles individual operator behavior to identify outliers",
        use_case="Detecting operators with unusual performance patterns",
        typical_findings=[
            "Unusually high throughput",
            "Abnormal error patterns",
            "Suspicious timing patterns"
        ],
        recommended_for=["Operator audits", "Performance review", "Fraud investigation"],
        processing_time="Comprehensive"
    ),
    
    AnalysisStrategy.CROSS_REFERENCE: StrategyInfo(
        strategy_id="cross_reference",
        name="Cross-Reference Validation",
        description="Cross-validates data across multiple operational dimensions",
        use_case="Finding inconsistencies across related data points",
        typical_findings=[
            "Mismatched records across systems",
            "Correlated anomalies",
            "Linked suspicious activities"
        ],
        recommended_for=["Deep investigations", "Fraud rings", "System integrity"],
        processing_time="Comprehensive"
    ),
    
    AnalysisStrategy.VOLUME_SURGE: StrategyInfo(
        strategy_id="volume_surge",
        name="Volume Surge Detection",
        description="Identifies sudden spikes or drops in operational volumes",
        use_case="Detecting unusual volume changes that may indicate issues",
        typical_findings=[
            "Sudden enrollment spikes",
            "Unusual processing volumes",
            "Capacity threshold breaches"
        ],
        recommended_for=["Real-time monitoring", "Capacity planning", "Quick scans"],
        processing_time="Fast"
    ),
    
    AnalysisStrategy.QUALITY_ASSESSMENT: StrategyInfo(
        strategy_id="quality_assessment",
        name="Data Quality Assessment",
        description="Evaluates the quality and integrity of submitted data",
        use_case="Identifying records with quality issues that may indicate fraud",
        typical_findings=[
            "Incomplete submissions",
            "Low quality biometrics",
            "Inconsistent field values"
        ],
        recommended_for=["Quality control", "Data governance", "Compliance checks"],
        processing_time="Standard"
    )
}


# =============================================================================
# STRATEGY SELECTOR
# =============================================================================

@dataclass
class SelectedStrategy:
    """Result of strategy selection. NO algorithm details exposed."""
    strategy: AnalysisStrategy
    info: StrategyInfo
    confidence_level: str  # "High", "Standard"
    estimated_time: str
    applies_to: List[str]  # What this strategy will analyze


@dataclass
class StrategyExecutionPlan:
    """Execution plan for selected strategies. NO ML details exposed."""
    plan_id: str
    strategies: List[SelectedStrategy]
    execution_order: List[str]
    total_estimated_time: str
    coverage: str  # What aspects are covered
    # EXPLICITLY NO: algorithm names, hyperparameters, model configs


class AnalysisStrategySelector:
    """
    Selects appropriate analysis strategies based on monitoring needs.
    
    This selector:
    - Maps signals to strategies
    - Recommends strategies based on context
    - Provides execution plans
    - NEVER exposes underlying ML algorithms
    
    Example:
        selector = AnalysisStrategySelector()
        
        # Get strategy recommendations
        strategies = selector.recommend_strategies(
            signals=["volume_patterns", "operator_activity"],
            vigilance="enhanced"
        )
        
        # Get execution plan
        plan = selector.create_execution_plan(strategies)
    """
    
    # Signal to strategy mapping - determines which strategies apply
    _SIGNAL_STRATEGY_MAP = {
        "volume_patterns": [AnalysisStrategy.VOLUME_SURGE, AnalysisStrategy.BEHAVIORAL_BASELINE],
        "geographic_distribution": [AnalysisStrategy.REGIONAL_DEVIATION],
        "temporal_patterns": [AnalysisStrategy.TEMPORAL_TREND, AnalysisStrategy.BEHAVIORAL_BASELINE],
        "operator_activity": [AnalysisStrategy.OPERATOR_PROFILING, AnalysisStrategy.BEHAVIORAL_BASELINE],
        "update_frequency": [AnalysisStrategy.PATTERN_CONSISTENCY, AnalysisStrategy.TEMPORAL_TREND],
        "demographic_changes": [AnalysisStrategy.PATTERN_CONSISTENCY, AnalysisStrategy.CROSS_REFERENCE],
        "biometric_update_frequency": [AnalysisStrategy.QUALITY_ASSESSMENT, AnalysisStrategy.OPERATOR_PROFILING],
        "cross_operation_correlation": [AnalysisStrategy.CROSS_REFERENCE]
    }
    
    def __init__(self):
        """Initialize the strategy selector."""
        self.catalog = STRATEGY_CATALOG
        logger.info("Analysis Strategy Selector initialized")
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """
        Get all available strategies for display.
        
        Returns user-friendly strategy information.
        NO algorithm details included.
        """
        return [
            {
                "strategy_id": info.strategy_id,
                "name": info.name,
                "description": info.description,
                "use_case": info.use_case,
                "processing_time": info.processing_time,
                "recommended_for": info.recommended_for
            }
            for strategy, info in self.catalog.items()
        ]
    
    def recommend_strategies(
        self,
        signals: List[str],
        vigilance: str = "standard",
        max_strategies: int = 3
    ) -> List[SelectedStrategy]:
        """
        Recommend strategies based on analytical signals.
        
        Args:
            signals: List of signal IDs from resolved intent
            vigilance: Vigilance level ("routine", "standard", "enhanced", "maximum")
            max_strategies: Maximum strategies to recommend
        
        Returns:
            List of SelectedStrategy objects.
            NO algorithm details in output.
        """
        strategy_scores: Dict[AnalysisStrategy, float] = {}
        
        # Score strategies based on signal coverage
        for signal in signals:
            if signal in self._SIGNAL_STRATEGY_MAP:
                for strategy in self._SIGNAL_STRATEGY_MAP[signal]:
                    strategy_scores[strategy] = strategy_scores.get(strategy, 0) + 1
        
        # Apply vigilance modifier
        if vigilance in ["enhanced", "maximum"]:
            # Add comprehensive strategies for higher vigilance
            strategy_scores[AnalysisStrategy.PATTERN_CONSISTENCY] = \
                strategy_scores.get(AnalysisStrategy.PATTERN_CONSISTENCY, 0) + 0.5
            strategy_scores[AnalysisStrategy.CROSS_REFERENCE] = \
                strategy_scores.get(AnalysisStrategy.CROSS_REFERENCE, 0) + 0.5
        
        # Sort by score
        sorted_strategies = sorted(
            strategy_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:max_strategies]
        
        # Build selected strategies
        selected = []
        for strategy, score in sorted_strategies:
            info = self.catalog[strategy]
            
            selected.append(SelectedStrategy(
                strategy=strategy,
                info=info,
                confidence_level="High" if score >= 2 else "Standard",
                estimated_time=info.processing_time,
                applies_to=self._get_applies_to(strategy, signals)
            ))
        
        # Ensure at least one strategy
        if not selected:
            default_strategy = AnalysisStrategy.BEHAVIORAL_BASELINE
            selected.append(SelectedStrategy(
                strategy=default_strategy,
                info=self.catalog[default_strategy],
                confidence_level="Standard",
                estimated_time="Standard",
                applies_to=["General monitoring"]
            ))
        
        logger.info(f"Recommended {len(selected)} strategies")
        return selected
    
    def _get_applies_to(
        self,
        strategy: AnalysisStrategy,
        signals: List[str]
    ) -> List[str]:
        """Determine what aspects this strategy applies to."""
        # Map signals to user-friendly descriptions
        signal_descriptions = {
            "volume_patterns": "Enrollment volumes",
            "geographic_distribution": "Regional patterns",
            "temporal_patterns": "Time-based activity",
            "operator_activity": "Operator behavior",
            "update_frequency": "Update patterns",
            "demographic_changes": "Demographic modifications",
            "biometric_update_frequency": "Biometric submissions"
        }
        
        applies_to = []
        for signal, strategies in self._SIGNAL_STRATEGY_MAP.items():
            if strategy in strategies and signal in signals:
                if signal in signal_descriptions:
                    applies_to.append(signal_descriptions[signal])
        
        return applies_to if applies_to else ["General operations"]
    
    def create_execution_plan(
        self,
        strategies: List[SelectedStrategy]
    ) -> StrategyExecutionPlan:
        """
        Create an execution plan for selected strategies.
        
        Returns a plan with NO algorithm details.
        """
        import uuid
        
        # Determine execution order (fast strategies first)
        time_order = {"Fast": 0, "Standard": 1, "Comprehensive": 2}
        ordered = sorted(
            strategies,
            key=lambda s: time_order.get(s.estimated_time, 1)
        )
        
        # Calculate total time
        time_map = {"Fast": 1, "Standard": 3, "Comprehensive": 5}
        total_minutes = sum(
            time_map.get(s.estimated_time, 3)
            for s in strategies
        )
        
        if total_minutes <= 3:
            total_time = "Under 5 minutes"
        elif total_minutes <= 10:
            total_time = "5-10 minutes"
        else:
            total_time = "10-15 minutes"
        
        # Determine coverage
        all_applies_to = set()
        for s in strategies:
            all_applies_to.update(s.applies_to)
        
        if len(all_applies_to) >= 4:
            coverage = "Comprehensive"
        elif len(all_applies_to) >= 2:
            coverage = "Broad"
        else:
            coverage = "Focused"
        
        return StrategyExecutionPlan(
            plan_id=str(uuid.uuid4())[:8],
            strategies=strategies,
            execution_order=[s.strategy.value for s in ordered],
            total_estimated_time=total_time,
            coverage=f"{coverage} - Covering: {', '.join(list(all_applies_to)[:4])}"
        )
    
    def get_internal_config(
        self,
        strategy: AnalysisStrategy
    ) -> Optional[_InternalStrategyConfig]:
        """
        Get internal ML configuration for a strategy.
        
        THIS IS FOR INTERNAL USE ONLY.
        NEVER expose this to external APIs.
        """
        return _STRATEGY_TO_ML_MAP.get(strategy)
    
    def execute_strategy(
        self,
        strategy: AnalysisStrategy,
        data: pd.DataFrame,
        feature_columns: List[str]
    ) -> Dict[str, Any]:
        """
        Execute a strategy on data.
        
        Returns results WITHOUT algorithm details.
        """
        config = self.get_internal_config(strategy)
        if config is None:
            return {"error": "Strategy not configured"}
        
        X = data[feature_columns].fillna(0).values
        
        # Execute using internal techniques
        scores = self._execute_techniques(X, config)
        
        # Generate results WITHOUT exposing algorithms
        flagged_count = int((scores >= 0.5).sum())
        
        return {
            "strategy_applied": STRATEGY_CATALOG[strategy].name,
            "records_analyzed": len(data),
            "findings": {
                "flagged": flagged_count,
                "review_recommended": int((scores >= 0.3).sum()) - flagged_count,
                "cleared": len(data) - int((scores >= 0.3).sum())
            },
            "confidence": "High" if config.min_confidence >= 0.7 else "Standard",
            # NO: algorithm_used, model_name, hyperparameters
        }
    
    def _execute_techniques(
        self,
        X: np.ndarray,
        config: _InternalStrategyConfig
    ) -> np.ndarray:
        """
        Execute ML techniques internally.
        
        THIS METHOD IS COMPLETELY INTERNAL.
        No external visibility.
        """
        scores_list = []
        
        for technique in config.primary_techniques:
            try:
                score = self._run_technique(X, technique, config.hyperparameters)
                scores_list.append(score)
            except Exception as e:
                logger.warning(f"Primary technique failed, trying fallback: {e}")
        
        # Fallback if primary failed
        if not scores_list:
            for technique in config.fallback_techniques:
                try:
                    score = self._run_technique(X, technique, config.hyperparameters)
                    scores_list.append(score)
                    break
                except Exception:
                    continue
        
        if not scores_list:
            # Ultimate fallback: statistical
            return self._statistical_baseline(X)
        
        # Ensemble based on method
        if config.ensemble_method == "voting":
            predictions = np.array([s >= 0.5 for s in scores_list])
            return predictions.mean(axis=0)
        elif config.ensemble_method == "stacking":
            return np.max(scores_list, axis=0)
        else:  # averaging
            return np.mean(scores_list, axis=0)
    
    def _run_technique(
        self,
        X: np.ndarray,
        technique: _MLTechnique,
        params: Dict
    ) -> np.ndarray:
        """Run a specific ML technique. INTERNAL ONLY."""
        
        if technique == _MLTechnique.ISOLATION_FOREST:
            from sklearn.ensemble import IsolationForest
            model = IsolationForest(
                contamination=params.get("contamination", 0.1),
                n_estimators=params.get("n_estimators", 100),
                random_state=42
            )
            model.fit(X)
            scores = -model.decision_function(X)
            return (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)
        
        elif technique == _MLTechnique.LOCAL_OUTLIER_FACTOR:
            from sklearn.neighbors import LocalOutlierFactor
            model = LocalOutlierFactor(
                n_neighbors=params.get("n_neighbors", 20),
                contamination=params.get("contamination", 0.1)
            )
            scores = -model.fit_predict(X)
            return (scores + 1) / 2  # Convert -1/1 to 0/1
        
        elif technique in [_MLTechnique.STATISTICAL_ZSCORE, _MLTechnique.IQR_DETECTION]:
            return self._statistical_baseline(X)
        
        else:
            return self._statistical_baseline(X)
    
    def _statistical_baseline(self, X: np.ndarray) -> np.ndarray:
        """Statistical baseline scoring. INTERNAL."""
        from scipy import stats
        
        # Z-score based
        zscores = np.abs(stats.zscore(X, axis=0, nan_policy='omit'))
        combined = np.mean(zscores, axis=1)
        
        # Normalize to 0-1
        return (combined - combined.min()) / (combined.max() - combined.min() + 1e-10)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def select_strategies(
    signals: List[str],
    vigilance: str = "standard"
) -> Dict[str, Any]:
    """
    Convenience function to select strategies.
    
    Returns strategy recommendations WITHOUT algorithm details.
    """
    selector = AnalysisStrategySelector()
    strategies = selector.recommend_strategies(signals, vigilance)
    plan = selector.create_execution_plan(strategies)
    
    return {
        "strategies": [
            {
                "name": s.info.name,
                "description": s.info.description,
                "confidence": s.confidence_level,
                "applies_to": s.applies_to,
                "processing_time": s.estimated_time
            }
            for s in strategies
        ],
        "execution_plan": {
            "plan_id": plan.plan_id,
            "order": plan.execution_order,
            "estimated_time": plan.total_estimated_time,
            "coverage": plan.coverage
        }
        # NO: algorithms, models, hyperparameters
    }


# Example
if __name__ == "__main__":
    print("=" * 60)
    print("ANALYSIS STRATEGY SELECTOR - DEMO")
    print("=" * 60)
    
    selector = AnalysisStrategySelector()
    
    print("\nAvailable Strategies:")
    for info in selector.get_available_strategies():
        print(f"\n  • {info['name']}")
        print(f"    {info['description']}")
    
    print("\n" + "=" * 60)
    print("Selecting strategies for signals: volume_patterns, operator_activity")
    print("=" * 60)
    
    result = select_strategies(
        signals=["volume_patterns", "operator_activity"],
        vigilance="enhanced"
    )
    
    print("\nRecommended Strategies:")
    for s in result["strategies"]:
        print(f"\n  • {s['name']}")
        print(f"    Applies to: {', '.join(s['applies_to'])}")
        print(f"    Confidence: {s['confidence']}")
    
    print(f"\nExecution Plan:")
    print(f"  Total Time: {result['execution_plan']['estimated_time']}")
    print(f"  Coverage: {result['execution_plan']['coverage']}")
    
    print("\n" + "=" * 60)
    print("NOTE: No algorithm names exposed!")
    print("=" * 60)
