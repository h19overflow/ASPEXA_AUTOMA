# Attack Agents Module

**Path:** `services/snipers/core/agents`

The **Agents** module serves as the "brain" behind the Sniper's adaptive lifecycle. When a standard payload fails or faces heavy resistance from target guardrails, these specialized, LLM-powered agents step in to analyze the failure and pivot the attack strategy in real-time.

---

## 🏗️ Agent Interaction Flow

```mermaid
sequenceDiagram
    participant Pipe as Pipeline Orchestrator
    participant FA as FailureAnalyzerAgent
    participant CD as ChainDiscoveryAgent
    participant SG as StrategyGenerator
    participant LLM as Base Generation Model

    Pipe->>FA: Analyze failed attack results
    activate FA
    FA-->>Pipe: FailureAnalysisDecision (e.g., "Semantic filter detected")
    deactivate FA

    alt If Obfuscation Needed
        Pipe->>CD: Suggest new obfuscation chain
        activate CD
        CD-->>Side: Query AVAILABLE_CONVERTERS
        CD-->>Pipe: ChainDiscoveryDecision (e.g., "Base64 + HTML Entity")
        deactivate CD
    end

    alt If Persona Adaptation Needed
        Pipe->>SG: Suggest new phrasing/persona
        activate SG
        SG-->>Pipe: New CustomFraming (e.g., "Use System Admin Persona")
        deactivate SG
    end
```

### Components

- **`FailureAnalyzerAgent`**: The detective. Looks at the target's rejection reasons (e.g., "I cannot fulfill this request") and determines _why_ it was blocked (e.g., keyword detection vs semantic intent blocking).
- **`ChainDiscoveryAgent`**: The cryptographer. Looks at available converters (Base64, Leetspeak, Unicode) and determines the best sequential combination (a 'chain') to bypass regex and pattern-matching guardrails.
- **`StrategyGenerator`**: The social engineer. Modifies the angle, phrasing, and underlying persona (Context Framing) to try and slip past semantic analysis guardrails.

---

## 📁 Files

- `chain_discovery_agent.py`: Agent for chaining logic.
- `failure_analyzer_agent.py`: Agent for root cause analysis of failures.
- `strategy_generator.py`: Agent for generating new payload phrasing.
- `prompts/`: Contains the specific prompt templates that guide the Agents' behaviors.
