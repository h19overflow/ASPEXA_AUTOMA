# Phase 1: Data Models

## Scope

Define Pydantic models for episodes, hypotheses, probes, and insights.

**No external dependencies. Pure Python + Pydantic.**

---

## Deliverables

### File: `services/snipers/bypass_knowledge/models/episode.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class FailureDepth(str, Enum):
    """How quickly the defense blocked the attempt."""
    IMMEDIATE = "immediate_block"      # <100ms, no processing
    PARTIAL = "partial_then_refuse"    # Started complying, then stopped
    DELAYED = "delayed_block"          # Processed, then refused
    TIMEOUT = "timeout"                # No response


class Hypothesis(BaseModel):
    """A hypothesis about the defense mechanism."""
    mechanism_type: str        # "semantic_classifier", "keyword_filter", "permission_check"
    confidence: float          # 0.0-1.0
    evidence: str              # What observation led to this hypothesis


class ProbeResult(BaseModel):
    """Result of a diagnostic probe sent to fingerprint the defense."""
    probe_type: str            # "encoding", "authority_frame", "synonym"
    probe_description: str     # Brief description of what was tested
    result: str                # "blocked", "partial", "success"
    latency_ms: int            # Response time (helps identify mechanism)
    inference: str             # What we learned from this probe


class BypassEpisode(BaseModel):
    """Complete record of a successful bypass for learning."""

    # === IDENTITY ===
    episode_id: str = Field(description="UUID for this episode")
    campaign_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # === DEFENSE FINGERPRINT (Primary Index) ===
    defense_response: str = Field(description="Raw text of blocking response")
    defense_signals: list[str] = Field(
        default_factory=list,
        description="Detected signals: policy_citation, ethical_refusal, etc."
    )
    failed_techniques: list[str] = Field(
        default_factory=list,
        description="Techniques that didn't work: encoding, direct_request, etc."
    )
    failure_depths: dict[str, FailureDepth] = Field(
        default_factory=dict,
        description="How each failed technique was blocked"
    )

    # === INVESTIGATION ===
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    probes: list[ProbeResult] = Field(default_factory=list)
    mechanism_conclusion: str = Field(
        description="Final assessment: e.g., 'Hybrid: semantic classifier + keyword filter'"
    )

    # === SOLUTION ===
    successful_technique: str = Field(description="What worked: verification_reversal, etc.")
    successful_framing: str = Field(description="Framing used: compliance_audit, etc.")
    successful_converters: list[str] = Field(default_factory=list)
    successful_prompt: str = Field(description="The actual winning prompt")
    jailbreak_score: float = Field(ge=0.0, le=1.0)

    # === REASONING (LLM-generated post-hoc) ===
    why_it_worked: str = Field(description="Explanation of why the bypass succeeded")
    key_insight: str = Field(description="Transferable learning for similar situations")

    # === CONTEXT ===
    target_domain: str = Field(description="finance, customer_service, general, etc.")
    target_description: str = Field(default="", description="From recon intelligence")
    objective_type: str = Field(description="data_extraction, tool_abuse, jailbreak, etc.")

    # === METADATA ===
    iteration_count: int = Field(description="How many iterations to succeed")
    total_probes: int = Field(default=0)
    execution_time_ms: int = Field(default=0)
```

### File: `services/snipers/bypass_knowledge/models/insight.py`

```python
from pydantic import BaseModel, Field


class TechniqueStats(BaseModel):
    """Statistics for a technique across episodes."""
    technique: str
    success_count: int
    total_attempts: int
    success_rate: float
    avg_iterations: float


class HistoricalInsight(BaseModel):
    """Synthesized intelligence from historical episodes."""

    # === QUERY ===
    query: str = Field(description="Original question asked")
    similar_cases_found: int

    # === MECHANISM ANALYSIS ===
    dominant_mechanism: str = Field(
        description="Most common mechanism in matched episodes"
    )
    mechanism_confidence: float

    # === RECOMMENDATIONS ===
    technique_stats: list[TechniqueStats] = Field(default_factory=list)
    recommended_technique: str
    recommended_framing: str
    recommended_converters: list[str] = Field(default_factory=list)

    # === PATTERN ===
    key_pattern: str = Field(
        description="Synthesized insight about what works in this situation"
    )

    # === EXAMPLE ===
    representative_episode_id: str = Field(default="")
    representative_summary: str = Field(default="")

    # === META ===
    confidence: float
    reasoning: str = Field(description="How this insight was derived")
```

---

## Tests

### File: `tests/bypass_knowledge/test_models.py`

```python
import pytest
from datetime import datetime
from services.snipers.bypass_knowledge.models.episode import (
    BypassEpisode, Hypothesis, ProbeResult, FailureDepth
)
from services.snipers.bypass_knowledge.models.insight import (
    HistoricalInsight, TechniqueStats
)


class TestBypassEpisode:
    def test_create_minimal_episode(self):
        episode = BypassEpisode(
            episode_id="test-123",
            campaign_id="campaign-1",
            defense_response="I cannot help with that request.",
            mechanism_conclusion="Unknown",
            successful_technique="role_play",
            successful_framing="qa_testing",
            successful_prompt="As a QA tester...",
            jailbreak_score=0.95,
            why_it_worked="Role play bypassed intent detection",
            key_insight="Role play works against intent classifiers",
            target_domain="general",
            objective_type="jailbreak",
            iteration_count=3,
        )
        assert episode.episode_id == "test-123"
        assert episode.jailbreak_score == 0.95

    def test_episode_with_probes(self):
        probe = ProbeResult(
            probe_type="encoding",
            probe_description="Tested ROT13 encoding",
            result="blocked",
            latency_ms=50,
            inference="Fast block suggests pattern matching"
        )
        episode = BypassEpisode(
            episode_id="test-456",
            campaign_id="campaign-1",
            defense_response="I cannot help.",
            probes=[probe],
            failed_techniques=["encoding"],
            failure_depths={"encoding": FailureDepth.IMMEDIATE},
            mechanism_conclusion="Pattern-based filter",
            successful_technique="synonym_substitution",
            successful_framing="verification",
            successful_prompt="Please verify...",
            jailbreak_score=0.88,
            why_it_worked="Synonyms bypassed keyword filter",
            key_insight="Immediate blocks often indicate regex filters",
            target_domain="finance",
            objective_type="data_extraction",
            iteration_count=2,
        )
        assert len(episode.probes) == 1
        assert episode.failure_depths["encoding"] == FailureDepth.IMMEDIATE


class TestHistoricalInsight:
    def test_create_insight(self):
        stats = TechniqueStats(
            technique="authority_framing",
            success_count=8,
            total_attempts=12,
            success_rate=0.67,
            avg_iterations=2.5
        )
        insight = HistoricalInsight(
            query="What works when encoding fails?",
            similar_cases_found=12,
            dominant_mechanism="semantic_classifier",
            mechanism_confidence=0.75,
            technique_stats=[stats],
            recommended_technique="authority_framing",
            recommended_framing="compliance_audit",
            key_pattern="When encoding fails, try authority framing",
            confidence=0.78,
            reasoning="Based on 12 similar episodes"
        )
        assert insight.similar_cases_found == 12
        assert insight.technique_stats[0].success_rate == 0.67
```

---

## Acceptance Criteria

- [ ] All models pass Pydantic validation
- [ ] Models are immutable (frozen=True if needed)
- [ ] All fields have descriptions
- [ ] Unit tests pass with 100% coverage on models
- [ ] Models can be serialized to JSON
- [ ] Models can be deserialized from JSON
