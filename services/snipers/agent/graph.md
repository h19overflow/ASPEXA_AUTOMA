# Exploit Agent Workflow Graph

This diagram shows the complete LangGraph workflow for the exploit agent with Human-in-the-Loop (HITL) interrupts.

```mermaid
graph TD
    %% Entry Point
    START([START]) --> A[analyze_pattern<br/>Pattern Analysis Agent<br/>COT + Step-Back]

    %% Sequential Analysis Steps
    A --> B[select_converters<br/>Converter Selection Agent<br/>Structured Output]
    B --> C[generate_payloads<br/>Payload Generation Agent<br/>Uses Human Feedback]
    C --> D[create_attack_plan<br/>Plan Assembly<br/>Risk Assessment]

    %% Human Review Interrupt #1 - CRITICAL GATE
    D --> E{human_review_plan<br/>👤 HITL INTERRUPT<br/>Attack Plan Review}
    
    %% Conditional Edges after Plan Review
    E -->|"approved<br/>Command(resume=True)"| F[execute_attack<br/>PyRIT Execution<br/>Requires Approval]
    E -->|"rejected<br/>Command(resume=False)"| END1([END])
    E -->|"modify<br/>Command(resume=modifications)"| C

    %% Sequential Steps after Execution
    F --> G[score_result<br/>Scoring Agent<br/>Structured Output]
    G --> H{human_review_result<br/>👤 HITL INTERRUPT<br/>Result Review}

    %% Conditional Edges after Result Review
    H -->|"complete<br/>Success/Failure"| END2([END])
    H -->|"retry<br/>With Modifications"| I[handle_retry<br/>Retry Logic<br/>Check Limits]

    %% Conditional Edges after Retry Handling
    I -->|"retry<br/>New Attempt"| C
    I -->|"give_up<br/>Max Retries"| END3([END])

    %% Styling
    style A fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000000
    style B fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000000
    style C fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000000
    style D fill:#fff9c4,stroke:#f57f17,stroke-width:2px,color:#000000
    style E fill:#ffeb3b,stroke:#f57f17,stroke-width:3px,color:#000000
    style F fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:#000000
    style G fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#000000
    style H fill:#ffeb3b,stroke:#f57f17,stroke-width:3px,color:#000000
    style I fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000000
    style START fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000000
    style END1 fill:#ffcdd2,stroke:#d32f2f,stroke-width:2px,color:#000000
    style END2 fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:#000000
    style END3 fill:#ffcdd2,stroke:#d32f2f,stroke-width:2px,color:#000000
```

## Node Descriptions

### Analysis Nodes (Agent-Based)
- **analyze_pattern**: Uses `create_agent` with PatternAnalysis Pydantic output. Analyzes 3 example findings using COT and Step-Back prompting.
- **select_converters**: Uses `create_agent` with ConverterSelection Pydantic output. Selects PyRIT converters based on pattern analysis.
- **generate_payloads**: Uses `create_agent` with PayloadGeneration Pydantic output. Generates attack payloads, incorporates human feedback if provided.

### Planning Node
- **create_attack_plan**: Assembles complete AttackPlan (Pydantic model) with pattern analysis, converter selection, payload generation, reasoning summary, and risk assessment.

### Human Review Nodes (INTERRUPTS)
- **human_review_plan**: **CRITICAL GATE** - Uses `interrupt()` to pause execution. Human reviews complete attack plan. Returns decision: approve, reject, or modify.
- **human_review_result**: Uses `interrupt()` to pause execution. Human reviews attack results. Returns decision: complete or retry.

### Execution Node
- **execute_attack**: Executes approved payloads using PyRIT. Requires `human_approved=True`. Sends payloads to target endpoint.

### Scoring Node
- **score_result**: Uses `create_agent` with ScoringResult Pydantic output. Evaluates attack success by analyzing target response.

### Retry Node
- **handle_retry**: Manages retry logic. Checks retry limits, tracks failed payloads, resets approval state for new attempt.

## Interrupt Points

### Interrupt #1: Attack Plan Review
- **Location**: After `create_attack_plan`
- **Interrupt Payload**: Complete `AttackPlan` model (JSON-serializable)
- **Human Options**:
  - `Command(resume=True)` → **approved** → `execute_attack`
  - `Command(resume=False)` → **rejected** → `END`
  - `Command(resume={"modifications": {...}})` → **modify** → `generate_payloads` (with feedback)

### Interrupt #2: Attack Result Review
- **Location**: After `score_result`
- **Interrupt Payload**: `AttackResult` model with scoring details
- **Human Options**:
  - `Command(resume={"decision": "complete"})` → **complete** → `END`
  - `Command(resume={"decision": "retry", "modifications": {...}})` → **retry** → `handle_retry`

## Routing Logic

Routing decisions are handled by functions in `routing.py`:
- `route_after_human_review()`: Routes based on `next_action` from human review
- `route_after_result_review()`: Routes based on `next_action` from result review
- `route_after_retry()`: Routes based on retry limits and `next_action`

## State Management

- **Checkpointer**: In-memory `MemorySaver` (state persists only during execution session)
- **Thread ID**: Set via `config={"configurable": {"thread_id": ...}}`
- **State Updates**: Each node returns dict that updates `ExploitAgentState`

## Key Features

1. **Structured Output**: All agent nodes use Pydantic models for validation
2. **Human-in-the-Loop**: Two interrupt points for human oversight
3. **Approval Gate**: Attack execution requires explicit human approval
4. **Feedback Loop**: Human modifications feed back into payload generation
5. **Retry Logic**: Failed attacks can be retried with modifications (up to max_retries)
