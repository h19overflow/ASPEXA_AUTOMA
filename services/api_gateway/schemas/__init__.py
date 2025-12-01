"""API Gateway request/response schemas."""
from .recon import ReconStartRequest
from .scan import ScanStartRequest
from .exploit import ExploitStartRequest, ExploitStreamRequest, AttackModeAPI, ProbeCategoryAPI
from .campaigns import CampaignCreateRequest, CampaignUpdateRequest, StageCompleteRequest
from .snipers import (
    # Enums
    FramingType,
    ScorerType,
    # Phase 1
    CustomFraming,
    Phase1Request,
    Phase1Response,
    ConverterChainResponse,
    # Phase 2
    Phase2Request,
    Phase2WithChainRequest,
    Phase2Response,
    ConvertedPayloadResponse,
    AvailableConvertersResponse,
    # Phase 3
    Phase3Request,
    Phase3WithPhase2Request,
    Phase3Response,
    AttackResponseItem,
    ScorerResultItem,
    CompositeScoreResponse,
    # Full Attack
    FullAttackRequest,
    FullAttackResponse,
    # Adaptive Attack
    AdaptiveAttackRequest,
    AdaptiveAttackResponse,
    IterationHistoryItem,
)

__all__ = [
    "ReconStartRequest",
    "ScanStartRequest",
    "ExploitStartRequest",
    "ExploitStreamRequest",
    "AttackModeAPI",
    "ProbeCategoryAPI",
    "CampaignCreateRequest",
    "CampaignUpdateRequest",
    "StageCompleteRequest",
    # Snipers schemas
    "FramingType",
    "ScorerType",
    "CustomFraming",
    "Phase1Request",
    "Phase1Response",
    "ConverterChainResponse",
    "Phase2Request",
    "Phase2WithChainRequest",
    "Phase2Response",
    "ConvertedPayloadResponse",
    "AvailableConvertersResponse",
    "Phase3Request",
    "Phase3WithPhase2Request",
    "Phase3Response",
    "AttackResponseItem",
    "ScorerResultItem",
    "CompositeScoreResponse",
    "FullAttackRequest",
    "FullAttackResponse",
    "AdaptiveAttackRequest",
    "AdaptiveAttackResponse",
    "IterationHistoryItem",
]
