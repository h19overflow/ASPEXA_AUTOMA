# PyRIT Bridge Infrastructure

**Path:** `services/snipers/infrastructure/pyrit`

The **PyRIT Bridge** module wraps and initializes [Microsoft's PyRIT (Python Risk Identification Tool for generative AI)](https://github.com/Azure/PyRIT) framework. Instead of using PyRIT's full orchestration (which is built for static targets), this module extracts specific utility components—like converters and scorers—and maps them to our dynamic, adaptive orchestration.

---

## 🏗️ Integration Flow

```mermaid
graph LR
    subgraph Our Pipeline
        Phase2[Phase 2: Conversion]
        Phase4[Phase 4: Evaluation]
    end

    subgraph PyRIT Bridge Layer
        Init[pyrit_init.py]
        Bridge[pyrit_bridge.py]
    end

    subgraph Microsoft PyRIT Framework
        PyConv[PyRIT BaseConverter]
        PyScore[PyRIT BaseScorer]
        PyMem[PyRIT Memory]
    end

    Phase2 --> Bridge
    Phase4 --> Bridge

    Bridge -.-> |Wraps| PyConv
    Bridge -.-> |Wraps| PyScore

    Init -.-> |Bootstraps| PyMem

    style PyRIT Bridge Layer fill:#f9f,stroke:#333
```

### Core Responsibilities

1. **`pyrit_init.py`**: PyRIT requires an internal SQLite memory store to function securely. This script ensures that whenever the Sniper API spins up, PyRIT's underlying memory and environment variables are properly initialized before any conversions occur.
2. **`pyrit_bridge.py`**: A unified facade. Our custom Converters and Scorers (in `core/converters` and `core/scoring`) often inherit from or utilize internal PyRIT logic. The bridge simplifies this connection so our core pipeline doesn't have to manage complex PyRIT dependencies directly.
