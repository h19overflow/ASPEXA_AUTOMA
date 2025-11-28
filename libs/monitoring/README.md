# Monitoring Library

Langfuse integration for AI agent observability in Aspexa Automa.

## Features

1. **CallbackHandler** - LangChain callback handler for automatic LLM tracing
2. **observe** - Python decorator for function-level input/output tracking

## Configuration

Add to your `.env` file:

```bash
# Required
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Optional
LANGFUSE_HOST=https://cloud.langfuse.com  # default
LANGFUSE_ENABLED=true  # default: false
```

## Usage

### Pattern 1: CallbackHandler for LangChain

Use with any LangChain LLM or agent:

```python
from libs.monitoring import CallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI

# Initialize handler (auto-reads env vars)
handler = CallbackHandler()

# Create LLM
llm = ChatGoogleGenerativeAI(model="gemini-pro")

# Pass handler in config
response = llm.invoke(
    "Tell me about AI security",
    config={"callbacks": [handler]}
)
```

**With helper utility:**

```python
from libs.monitoring import get_callbacks_config

# Get config with handler automatically
config = get_callbacks_config(
    session_id="exploit-campaign-001",
    trace_name="pattern-analysis"
)

response = llm.invoke(prompt, config=config)
```

### Pattern 2: observe Decorator

Track any Python function's inputs and outputs:

```python
from libs.monitoring import observe

@observe()
def analyze_vulnerability(target_url: str, probe_type: str):
    """This function will be traced automatically."""
    # Do analysis
    result = perform_analysis(target_url, probe_type)
    return result

# Nested functions create child spans
@observe()
def perform_analysis(url: str, probe: str):
    # Inner logic is tracked as child span
    return {"status": "vulnerable", "severity": "high"}

# Just call normally - Langfuse works in background
result = analyze_vulnerability("http://target.com", "xss")
```

## Integration Points

### Snipers Service (Exploit Agent)

```python
# In services/snipers/agent/core.py
from libs.monitoring import get_callbacks_config, observe

class ExploitAgent:
    def execute(self, state):
        # Get callbacks for the workflow
        config = get_callbacks_config(
            session_id=state.get("campaign_id"),
            trace_name="exploit-workflow"
        )

        # Pass to workflow.invoke
        result = self.workflow.invoke(state, config=config)
        return result

# Decorate node functions
@observe()
def analyze_pattern_node(state: ExploitAgentState):
    # Node execution tracked automatically
    return updated_state
```

### Cartographer Service (Recon Agent)

```python
# In services/cartographer/agent/graph.py
from libs.monitoring import get_callbacks_config, observe

@observe()
async def run_reconnaissance_streaming(target_url: str):
    config = get_callbacks_config(
        trace_name="reconnaissance",
        user_id=target_url
    )

    # Pass to agent invocation
    result = await agent_graph.ainvoke(
        {"messages": messages},
        config=config
    )
    return result
```

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | Yes* | - | Public API key from Langfuse dashboard |
| `LANGFUSE_SECRET_KEY` | Yes* | - | Secret API key from Langfuse dashboard |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Langfuse server URL (for self-hosted) |
| `LANGFUSE_ENABLED` | No | `false` | Master switch to enable/disable monitoring |

*Required only if `LANGFUSE_ENABLED=true`

## Architecture

```
libs/monitoring/
├── __init__.py          # Public exports
├── utils.py             # Helper functions for initialization
└── README.md            # This file
```

## Dependencies

- `langfuse>=3.10.1` - Core Langfuse SDK
- `libs.config` - Settings management

## Notes

- CallbackHandler automatically reads `LANGFUSE_*` environment variables
- When `LANGFUSE_ENABLED=false`, all monitoring is no-op (zero performance impact)
- Traces are sent asynchronously and won't block agent execution
- Session IDs enable grouping related traces (e.g., entire exploit campaign)
