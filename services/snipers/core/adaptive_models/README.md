# Adaptive Attack Models

**Path:** `services/snipers/core/adaptive_models`

The **Adaptive Models** module contains the strongly-typed Pydantic schemas that facilitate structured LLM reasoning. When the AI agents analyze a failure or decide how to adapt an ongoing attack, they output their decisions mapped perfectly to these models.

---

## 🏗️ Model Relationships

```mermaid
classDiagram
    class FailureAnalysisDecision {
        +bool needs_adaptation
        +str reasoning
        +List~DefenseSignal~ defense_signals
        +str recommended_strategy
    }

    class DefenseAnalysis {
        +List~str~ detected_guardrails
        +str filtering_mechanism
        +str vulnerability_gap
    }

    class AdaptationDecision {
        +Optional~CustomFraming~ new_framing
        +Optional~ChainDiscoveryDecision~ new_chain_strategy
        +str strategic_shift_explanation
    }

    class ChainDiscoveryDecision {
        +List~ConverterChainCandidate~ proposed_chains
        +str chaining_rationale
    }

    FailureAnalysisDecision "1" *-- "*" DefenseSignal
    AdaptationDecision "1" *-- "1" CustomFraming
    AdaptationDecision "1" *-- "1" ChainDiscoveryDecision
```

## 🧠 Why We Use This

By enforcing strict Output Schemas (like `AdaptationDecision` and `FailureAnalysisDecision`), we ensure that when the `FailureAnalyzerAgent` or `ChainDiscoveryAgent` communicates their findings, that data can be programmatically parsed and executed by the Python orchestration loop, bridging the gap between non-deterministic AI text and deterministic code pathways.

---

## 📁 Core Models

- `adaptation_decision.py`: Defines how the agent decides to pivot (e.g. `CustomFraming`, `AdaptationDecision`).
- `chain_discovery.py`: Defines how the agent structures proposed obfuscation layers (e.g. `ChainDiscoveryDecision`, `ConverterChainCandidate`).
- `failure_analysis.py`: Defines how the agent classifies why an attack was blocked (e.g. `FailureAnalysisDecision`, `DefenseSignal`).
- `defense_analysis.py`: Models what guardrails the agent thinks the target is using (`DefenseAnalysis`).
