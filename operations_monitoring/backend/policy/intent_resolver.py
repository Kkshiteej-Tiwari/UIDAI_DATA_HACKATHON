"""
Intent Resolution Engine

Resolves user monitoring intents to analytical signals.
Config-driven, extensible, and completely abstracted from datasets.

DESIGN PRINCIPLES:
- NO dataset references in output
- User intents map to signals, not data sources
- Extensible via YAML configuration
- Context-aware signal selection
"""
import os
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class VigilanceLevel(str, Enum):
    """User-selectable vigilance levels."""
    ROUTINE = "routine"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    MAXIMUM = "maximum"


class TimePeriod(str, Enum):
    """Time period options."""
    TODAY = "today"
    LAST_7_DAYS = "last_7_days"
    THIS_MONTH = "this_month"
    CUSTOM = "custom_range"


@dataclass
class UserContext:
    """User-provided context for analysis."""
    location: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    time_period: TimePeriod = TimePeriod.TODAY
    vigilance: VigilanceLevel = VigilanceLevel.STANDARD
    custom_date_start: Optional[str] = None
    custom_date_end: Optional[str] = None


@dataclass
class Signal:
    """An analytical signal derived from intent."""
    signal_id: str
    description: str
    indicators: List[str]
    severity_weight: float
    active: bool = True


@dataclass
class ResolvedIntent:
    """
    Resolved intent ready for analysis.
    
    Contains NO dataset references - only signals and processing directives.
    """
    resolution_id: str
    intent_id: str
    intent_display: str
    category: str
    
    # Analytical signals to compute
    signals: List[Signal]
    
    # Processing directives
    analysis_scope: List[str]
    sensitivity: str
    processing_depth: str
    
    # Context applied
    geographic_scope: str
    temporal_scope: str
    vigilance_applied: str
    
    # Metadata
    resolved_at: str
    priority: int
    
    # DO NOT INCLUDE: dataset_id, model_name, threshold, hyperparameters


class IntentResolutionEngine:
    """
    Resolves user monitoring intents to analytical signals.
    
    This engine:
    - Loads intent mappings from YAML configuration
    - Maps user intents to required signals
    - Applies context modifiers
    - Returns analysis-ready directives WITHOUT dataset references
    
    Example:
        engine = IntentResolutionEngine()
        
        resolved = engine.resolve(
            intent_id="check_enrollments",
            context=UserContext(
                location="Maharashtra",
                vigilance=VigilanceLevel.ENHANCED
            )
        )
        
        # resolved.signals contains analytical signals
        # NO dataset references in output
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize engine with configuration."""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "intent_mapping.yaml"
        
        self.config = self._load_config(config_path)
        self.intents = self.config.get("intents", {})
        self.signals = self.config.get("signals", {})
        self.vigilance_levels = self.config.get("vigilance_levels", {})
        self.context_modifiers = self.config.get("context_modifiers", {})
        
        logger.info(f"Intent Resolution Engine initialized with {len(self.intents)} intents")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config not found at {config_path}, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration if YAML not found."""
        return {
            "intents": {
                "check_enrollments": {
                    "display_name": "Check enrollment operations",
                    "category": "enrollment_monitoring",
                    "signals_required": ["volume_patterns", "operator_activity"],
                    "analysis_scope": ["new_registrations"],
                    "default_vigilance": "standard",
                    "priority": 1
                },
                "comprehensive_check": {
                    "display_name": "Comprehensive integrity check",
                    "category": "full_audit",
                    "signals_required": ["volume_patterns", "geographic_distribution", "temporal_patterns"],
                    "analysis_scope": ["all_operations"],
                    "default_vigilance": "enhanced",
                    "priority": 1
                }
            },
            "signals": {
                "volume_patterns": {
                    "description": "Volume anomaly detection",
                    "indicators": ["daily_volume", "hourly_peaks"],
                    "severity_weight": 0.8
                },
                "operator_activity": {
                    "description": "Operator behavior analysis",
                    "indicators": ["operator_volume", "speed_patterns"],
                    "severity_weight": 0.9
                },
                "geographic_distribution": {
                    "description": "Geographic pattern analysis",
                    "indicators": ["regional_concentration"],
                    "severity_weight": 0.7
                },
                "temporal_patterns": {
                    "description": "Time-based pattern analysis",
                    "indicators": ["after_hours", "weekend_activity"],
                    "severity_weight": 0.6
                }
            },
            "vigilance_levels": {
                "routine": {"sensitivity": "low", "processing_depth": "shallow"},
                "standard": {"sensitivity": "medium", "processing_depth": "normal"},
                "enhanced": {"sensitivity": "high", "processing_depth": "deep"},
                "maximum": {"sensitivity": "maximum", "processing_depth": "exhaustive"}
            }
        }
    
    def get_available_intents(self) -> List[Dict[str, str]]:
        """
        Get list of available monitoring intents for UI display.
        
        Returns user-friendly intent options.
        """
        return [
            {
                "intent_id": intent_id,
                "display_name": intent_data.get("display_name", intent_id),
                "description": intent_data.get("description", ""),
                "category": intent_data.get("category", "general")
            }
            for intent_id, intent_data in self.intents.items()
        ]
    
    def resolve(
        self,
        intent_id: str,
        context: Optional[UserContext] = None
    ) -> ResolvedIntent:
        """
        Resolve a user intent to analytical signals.
        
        Args:
            intent_id: The selected monitoring intent
            context: Optional user context (location, time, vigilance)
        
        Returns:
            ResolvedIntent with signals and processing directives.
            NO dataset references included.
        """
        if context is None:
            context = UserContext()
        
        # Validate intent
        if intent_id not in self.intents:
            # Fallback to comprehensive check
            logger.warning(f"Unknown intent '{intent_id}', falling back to comprehensive_check")
            intent_id = "comprehensive_check"
        
        intent_config = self.intents[intent_id]
        
        # Resolve signals
        signals = self._resolve_signals(
            intent_config.get("signals_required", []),
            context
        )
        
        # Apply vigilance level
        vigilance_key = context.vigilance.value
        vigilance_config = self.vigilance_levels.get(
            vigilance_key,
            self.vigilance_levels.get("standard", {})
        )
        
        # Build geographic scope description
        geographic_scope = self._build_geographic_scope(context)
        
        # Build temporal scope description
        temporal_scope = self._build_temporal_scope(context)
        
        # Create resolution
        import uuid
        resolved = ResolvedIntent(
            resolution_id=str(uuid.uuid4()),
            intent_id=intent_id,
            intent_display=intent_config.get("display_name", intent_id),
            category=intent_config.get("category", "general"),
            signals=signals,
            analysis_scope=intent_config.get("analysis_scope", []),
            sensitivity=vigilance_config.get("sensitivity", "medium"),
            processing_depth=vigilance_config.get("processing_depth", "normal"),
            geographic_scope=geographic_scope,
            temporal_scope=temporal_scope,
            vigilance_applied=vigilance_key,
            resolved_at=datetime.now().isoformat(),
            priority=intent_config.get("priority", 2)
        )
        
        logger.info(f"Resolved intent '{intent_id}' with {len(signals)} signals")
        return resolved
    
    def _resolve_signals(
        self,
        signal_ids: List[str],
        context: UserContext
    ) -> List[Signal]:
        """Resolve signal IDs to Signal objects."""
        signals = []
        
        for signal_id in signal_ids:
            if signal_id in self.signals:
                signal_config = self.signals[signal_id]
                signal = Signal(
                    signal_id=signal_id,
                    description=signal_config.get("description", ""),
                    indicators=signal_config.get("indicators", []),
                    severity_weight=signal_config.get("severity_weight", 0.5),
                    active=True
                )
                signals.append(signal)
            else:
                logger.warning(f"Unknown signal '{signal_id}' requested")
        
        # Apply context modifiers to boost certain signals
        signals = self._apply_context_modifiers(signals, context)
        
        return signals
    
    def _apply_context_modifiers(
        self,
        signals: List[Signal],
        context: UserContext
    ) -> List[Signal]:
        """Apply context-based modifications to signals."""
        # Boost relevant signals based on context
        for signal in signals:
            # Location-specific boost
            if context.location and signal.signal_id == "geographic_distribution":
                signal.severity_weight = min(1.0, signal.severity_weight * 1.2)
            
            # Time-specific boost
            if context.time_period == TimePeriod.TODAY and signal.signal_id == "temporal_patterns":
                signal.severity_weight = min(1.0, signal.severity_weight * 1.1)
            
            # Vigilance-based boost
            if context.vigilance == VigilanceLevel.MAXIMUM:
                signal.severity_weight = min(1.0, signal.severity_weight * 1.15)
        
        return signals
    
    def _build_geographic_scope(self, context: UserContext) -> str:
        """Build human-readable geographic scope."""
        if context.district:
            return f"{context.district}, {context.state or 'India'}"
        elif context.state:
            return context.state
        elif context.location:
            return context.location
        else:
            return "All India"
    
    def _build_temporal_scope(self, context: UserContext) -> str:
        """Build human-readable temporal scope."""
        scope_map = {
            TimePeriod.TODAY: "Today's operations",
            TimePeriod.LAST_7_DAYS: "Last 7 days",
            TimePeriod.THIS_MONTH: "This month",
            TimePeriod.CUSTOM: f"{context.custom_date_start} to {context.custom_date_end}"
        }
        return scope_map.get(context.time_period, "Today's operations")
    
    def to_dict(self, resolved: ResolvedIntent) -> Dict[str, Any]:
        """Convert ResolvedIntent to dictionary for JSON serialization."""
        result = {
            "resolution_id": resolved.resolution_id,
            "intent": {
                "id": resolved.intent_id,
                "display": resolved.intent_display,
                "category": resolved.category
            },
            "signals": [
                {
                    "signal_id": s.signal_id,
                    "description": s.description,
                    "indicators": s.indicators,
                    "weight": s.severity_weight
                }
                for s in resolved.signals
            ],
            "processing": {
                "scope": resolved.analysis_scope,
                "sensitivity": resolved.sensitivity,
                "depth": resolved.processing_depth
            },
            "context": {
                "geographic": resolved.geographic_scope,
                "temporal": resolved.temporal_scope,
                "vigilance": resolved.vigilance_applied
            },
            "metadata": {
                "resolved_at": resolved.resolved_at,
                "priority": resolved.priority
            }
        }
        
        # EXPLICITLY NO: dataset_id, model_name, threshold, hyperparameters
        return result


# Convenience function
def resolve_intent(
    intent_id: str,
    location: Optional[str] = None,
    state: Optional[str] = None,
    time_period: str = "today",
    vigilance: str = "standard"
) -> Dict[str, Any]:
    """
    Quick function to resolve intent.
    
    Example:
        result = resolve_intent(
            "check_enrollments",
            state="Maharashtra",
            vigilance="enhanced"
        )
    """
    engine = IntentResolutionEngine()
    
    context = UserContext(
        location=location,
        state=state,
        time_period=TimePeriod(time_period) if time_period in [e.value for e in TimePeriod] else TimePeriod.TODAY,
        vigilance=VigilanceLevel(vigilance) if vigilance in [e.value for e in VigilanceLevel] else VigilanceLevel.STANDARD
    )
    
    resolved = engine.resolve(intent_id, context)
    return engine.to_dict(resolved)


# Example usage
if __name__ == "__main__":
    # Initialize engine
    engine = IntentResolutionEngine()
    
    # Show available intents
    print("Available Monitoring Intents:")
    print("-" * 50)
    for intent in engine.get_available_intents():
        print(f"  • {intent['display_name']}")
    
    print("\n" + "=" * 50)
    print("EXAMPLE: Resolving 'check_enrollments' intent")
    print("=" * 50 + "\n")
    
    # Resolve an intent with context
    context = UserContext(
        state="Maharashtra",
        time_period=TimePeriod.TODAY,
        vigilance=VigilanceLevel.ENHANCED
    )
    
    resolved = engine.resolve("check_enrollments", context)
    
    # Convert to dict for display
    import json
    result = engine.to_dict(resolved)
    print(json.dumps(result, indent=2))
    
    print("\n" + "=" * 50)
    print("NOTE: No dataset references in output!")
    print("=" * 50)
