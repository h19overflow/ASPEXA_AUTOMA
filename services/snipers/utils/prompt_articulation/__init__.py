"""Prompt Articulation System.

Provides LLM-powered payload crafting with contextual framing,
effectiveness tracking, and learning capabilities.

Main Entry Point:
    ArticulationPhase - Single source of truth for payload generation
"""

from services.snipers.utils.prompt_articulation.articulation_phase import (
    ArticulationPhase,
)
from services.snipers.utils.prompt_articulation.components import (
    ArticulatedPayload,
    EffectivenessProvider,
    EffectivenessTracker,
    FormatControl,
    FormatControlType,
    FramingLibrary,
    PayloadGenerator,
    PersistenceProvider,
)
from services.snipers.utils.prompt_articulation.config import (
    DEFAULT_FORMAT_CONTROL,
    DEFAULT_STRATEGIES,
    DOMAIN_STRATEGY_BOOST,
    EFFECTIVENESS_SAVE_INTERVAL,
)
from services.snipers.utils.prompt_articulation.loaders import (
    CampaignLoader,
    CampaignIntelligence,
)
from services.snipers.utils.prompt_articulation.models import (
    AttackHistory,
    EffectivenessRecord,
    EffectivenessSummary,
    FramingStrategy,
    FramingType,
    PayloadContext,
    TargetInfo,
)

__all__ = [
    # Main Entry Point
    "ArticulationPhase",
    # Loaders
    "CampaignLoader",
    "CampaignIntelligence",
    # Models
    "PayloadContext",
    "TargetInfo",
    "AttackHistory",
    "FramingType",
    "FramingStrategy",
    "EffectivenessRecord",
    "EffectivenessSummary",
    # Components
    "PayloadGenerator",
    "ArticulatedPayload",
    "FramingLibrary",
    "EffectivenessProvider",
    "FormatControl",
    "FormatControlType",
    "EffectivenessTracker",
    "PersistenceProvider",
    # Config
    "DEFAULT_STRATEGIES",
    "DOMAIN_STRATEGY_BOOST",
    "DEFAULT_FORMAT_CONTROL",
    "EFFECTIVENESS_SAVE_INTERVAL",
]
