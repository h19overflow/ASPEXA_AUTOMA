# Phase 1: Agent Restructure

## LangChain v1 `create_agent` with Gemini 2.5 Pro

### Overview

LangChain v1 introduces `create_agent` as the new standard for building agents, replacing
`langgraph.prebuilt.create_react_agent`. Key features:

- **Simpler API**: Single function to create production-ready agents
- **Structured Output**: Built-in support via `response_format` parameter
- **Graph-based Runtime**: Built on LangGraph for durability, streaming, persistence
- **Middleware Support**: Extensible via middleware pattern

### Installation

```bash
pip install -U langchain "langchain[google-genai]"
```

### Model Configuration

```python
# Option 1: Using model string (recommended for create_agent)
from langchain.agents import create_agent

agent = create_agent(
    model="google_genai:gemini-2.5-pro",  # Model string format
    tools=[...],
    system_prompt="...",
)

# Option 2: Using init_chat_model for standalone model
from langchain.chat_models import init_chat_model
import os

os.environ["GOOGLE_API_KEY"] = "your-api-key"
model = init_chat_model("google_genai:gemini-2.5-pro")

# Option 3: Direct ChatGoogleGenerativeAI instantiation
from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    api_key="your-api-key"
)
```

### Structured Output with `response_format`

LangChain v1 handles structured output automatically via `response_format`:

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy


class ProbePlan(BaseModel):
    """Structured output for probe planning."""
    probes: list[str] = Field(description="List of probe names to execute")
    generations: int = Field(description="Number of attempts per probe", ge=1, le=20)
    reasoning: dict[str, str] = Field(description="Probe name -> selection reason")


# Using ToolStrategy for models that support tool calling (like Gemini)
agent = create_agent(
    model="google_genai:gemini-2.5-pro",
    tools=[analyze_target, get_available_probes],
    system_prompt=SQL_SYSTEM_PROMPT,
    response_format=ToolStrategy(ProbePlan),  # Structured output via tool calling
)

# Invoke the agent
result = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Analyze this target and select probes..."}]
})

# Access structured response
plan: ProbePlan = result["structured_response"]
print(plan.probes)  # ['sqli.SqliProbe', 'xss.XssReflected', ...]
```

### Complete Agent Example

```python
# agents/sql/sql_agent.py
"""
SQL Agent using LangChain v1 create_agent with Gemini 2.5 Pro.

Purpose: Plan SQL/XSS/data extraction scans using LLM reasoning
Dependencies: langchain>=1.0, langchain-google-genai
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import tool

from .sql_prompt import SQL_SYSTEM_PROMPT
from .sql_probes import SQL_PROBES, get_probes


class ProbePlan(BaseModel):
    """Structured output schema for probe selection."""
    probes: List[str] = Field(description="Selected probe names")
    generations: int = Field(description="Attempts per probe", ge=1, le=20)
    reasoning: Dict[str, str] = Field(description="Selection reasoning per probe")


# Define tools the agent can use
@tool
def analyze_infrastructure(infrastructure: Dict[str, Any]) -> str:
    """Analyze target infrastructure to identify attack vectors.

    Args:
        infrastructure: Dict with database, model_family, etc.

    Returns:
        Analysis summary with recommended focus areas
    """
    db = infrastructure.get("database", "unknown")
    model = infrastructure.get("model_family", "unknown")

    findings = []
    if "postgres" in db.lower() or "mysql" in db.lower():
        findings.append(f"SQL database detected ({db}) - prioritize SQL injection")
    if "gpt" in model.lower() or "claude" in model.lower():
        findings.append(f"Advanced LLM ({model}) - test prompt injection resistance")

    return " | ".join(findings) if findings else "Standard target profile"


@tool
def get_available_probes(category: str = None) -> str:
    """Get list of available probes for scanning.

    Args:
        category: Optional filter (sqli, xss, nosql)

    Returns:
        JSON list of available probes
    """
    import json
    probes = get_probes("thorough")
    if category:
        probes = [p for p in probes if category.lower() in p.lower()]
    return json.dumps({"probes": probes})


class SQLAgent:
    """SQL Agent using LangChain v1 create_agent."""

    def __init__(self, model_name: str = "google_genai:gemini-2.5-pro"):
        self._model_name = model_name
        self._agent = None

    @property
    def agent_type(self) -> str:
        return "sql"

    @property
    def system_prompt(self) -> str:
        return SQL_SYSTEM_PROMPT

    @property
    def available_probes(self) -> List[str]:
        return SQL_PROBES

    def _get_or_create_agent(self):
        """Lazy initialization of LangChain agent."""
        if self._agent is None:
            self._agent = create_agent(
                model=self._model_name,
                tools=[analyze_infrastructure, get_available_probes],
                system_prompt=self.system_prompt,
                response_format=ToolStrategy(ProbePlan),
            )
        return self._agent

    async def plan(self, recon_context: Dict[str, Any]) -> ProbePlan:
        """Use LLM to analyze recon and select probes.

        Args:
            recon_context: Intelligence from recon phase

        Returns:
            ProbePlan with selected probes and reasoning
        """
        agent = self._get_or_create_agent()

        # Build user message with recon context
        user_message = f"""
        Analyze this target and select appropriate probes:

        Infrastructure: {recon_context.get('infrastructure', {})}
        Detected Tools: {recon_context.get('detected_tools', [])}
        Approach: {recon_context.get('approach', 'standard')}

        Use analyze_infrastructure to assess the target, then get_available_probes
        to see what probes are available. Select the most relevant probes and
        provide reasoning for each selection.
        """

        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": user_message}]
        })

        return result["structured_response"]
```

### Key Differences from Old Pattern

| Old Pattern | New Pattern (LangChain v1) |
|------------|---------------------------|
| `langgraph.prebuilt.create_react_agent` | `langchain.agents.create_agent` |
| Manual response parsing | `response_format=ToolStrategy(Schema)` |
| Context vars for state | Explicit state via graph |
| `model.bind_tools([...])` | `create_agent(model=..., tools=[...])` |
| Separate tool registration | `@tool` decorator on functions |

---

## Problem

Current structure:
```
agents/
├── base.py           # 157 lines - create + run + context
├── base_utils.py     # Helper functions
├── prompts/          # Just extracted prompts
├── tools.py          # LangChain tools + context vars
└── trinity.py        # Thin wrappers (useless)
```

Issues:
- All agents share same code path
- Agent-specific logic is in prompts only
- No clear ownership of probe selection
- `trinity.py` adds nothing

## Target Structure

```
agents/
├── __init__.py
├── base_agent.py              # Abstract base class
├── sql/
│   ├── __init__.py
│   ├── sql_agent.py           # SQLAgent class
│   ├── sql_prompt.py          # System prompt with XML tags
│   └── sql_probes.py          # Probe configuration
├── auth/
│   ├── __init__.py
│   ├── auth_agent.py
│   ├── auth_prompt.py
│   └── auth_probes.py
└── jailbreak/
    ├── __init__.py
    ├── jailbreak_agent.py
    ├── jailbreak_prompt.py
    └── jailbreak_probes.py
```

## Implementation

### Step 1: Create Base Agent Class

```python
# agents/base_agent.py
"""
Base agent class for all scanning agents.

Purpose: Define interface and shared response schema for scanning agents
Dependencies: pydantic, langchain>=1.0
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class ProbePlan(BaseModel):
    """Structured output schema for agent planning.

    Used with LangChain v1's ToolStrategy for guaranteed structured responses.
    All agents return this format via response_format=ToolStrategy(ProbePlan).
    """
    probes: List[str] = Field(
        description="List of probe names to execute (e.g., 'sqli.SqliProbe')"
    )
    generations: int = Field(
        description="Number of generation attempts per probe",
        ge=1,
        le=20,
        default=5
    )
    reasoning: Dict[str, str] = Field(
        description="Mapping of probe name to selection reasoning",
        default_factory=dict
    )


class BaseAgent(ABC):
    """Abstract base for scanning agents.

    Each agent:
    1. Has a system prompt (XML-tagged for clarity)
    2. Has a probe collection specific to its attack surface
    3. Uses LangChain v1 create_agent with Gemini 2.5 Pro
    4. Returns structured ProbePlan via ToolStrategy
    """

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent identifier (e.g., 'sql', 'auth', 'jailbreak')."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for this agent (with XML tags)."""
        pass

    @property
    @abstractmethod
    def available_probes(self) -> List[str]:
        """List of probe names this agent can use."""
        pass

    @abstractmethod
    async def plan(self, recon_context: Dict[str, Any]) -> ProbePlan:
        """Use LLM to analyze recon and select probes.

        Implementation should:
        1. Create LangChain agent with create_agent()
        2. Use ToolStrategy(ProbePlan) for structured output
        3. Invoke with recon context
        4. Return result["structured_response"]

        Args:
            recon_context: Intelligence from recon phase including:
                - infrastructure: Dict with database, model_family, etc.
                - detected_tools: List of tool definitions
                - approach: 'quick', 'standard', or 'thorough'

        Returns:
            ProbePlan with selected probes, generations, and reasoning
        """
        pass
```

### Step 2: Create SQL Agent Directory

```python
# agents/sql/__init__.py
from .sql_agent import SQLAgent

__all__ = ["SQLAgent"]
```

```python
# agents/sql/sql_prompt.py
"""
SQL Agent system prompt.

Purpose: Define prompt for SQL/data surface scanning
Used by: agents/sql/sql_agent.py
"""

SQL_SYSTEM_PROMPT = """
<systemPrompt>
    <agentIdentity>
        You are a Security Scanner specializing in Data Surface attacks.
    </agentIdentity>

    <role>
        Analyze the target and select appropriate probes for SQL injection,
        XSS, and data extraction vulnerabilities.
    </role>

    <focusAreas>
        <area>SQL/NoSQL injection via tool inputs</area>
        <area>XSS via model output</area>
        <area>Tool parameter tampering</area>
        <area>Error-based information disclosure</area>
    </focusAreas>

    <outputFormat>
        Return a JSON object with:
        - probes: List of probe names to run
        - generations: Number of attempts per probe (1-20)
        - reasoning: Dict mapping probe name to why it was selected
    </outputFormat>
</systemPrompt>
"""
```

```python
# agents/sql/sql_probes.py
"""
SQL Agent probe configuration.

Purpose: Define available probes for SQL agent
Used by: agents/sql/sql_agent.py
"""

# Core SQL injection probes
SQL_PROBES = [
    "sqli.SqliProbe",
    "sqli.SqliErrorBased",
    "sqli.SqliUnion",
    "xss.XssReflected",
    "xss.XssStored",
]

# Extended probes for thorough scans
SQL_PROBES_EXTENDED = SQL_PROBES + [
    "sqli.SqliBlind",
    "sqli.SqliTimeBased",
    "nosql.NoSqlInjection",
]

def get_probes(approach: str = "standard") -> list:
    """Get probes for given approach.

    Args:
        approach: 'quick', 'standard', or 'thorough'

    Returns:
        List of probe names
    """
    if approach == "quick":
        return SQL_PROBES[:3]
    elif approach == "thorough":
        return SQL_PROBES_EXTENDED
    return SQL_PROBES
```

```python
# agents/sql/sql_agent.py
"""
SQL Agent for data surface vulnerability scanning.

Purpose: Plan and execute SQL/XSS/data extraction scans
Dependencies: langchain>=1.0, langchain-google-genai
"""
from typing import List, Dict, Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import tool

from ..base_agent import BaseAgent, ProbePlan
from .sql_prompt import SQL_SYSTEM_PROMPT
from .sql_probes import get_probes, SQL_PROBES


# Tools defined at module level for reuse
@tool
def analyze_infrastructure(infrastructure: Dict[str, Any]) -> str:
    """Analyze target infrastructure to identify SQL attack vectors."""
    db = infrastructure.get("database", "unknown")
    findings = []
    if any(sql in db.lower() for sql in ["postgres", "mysql", "sqlite"]):
        findings.append(f"SQL database detected ({db}) - prioritize SQL injection")
    return " | ".join(findings) if findings else "No specific SQL indicators"


@tool
def get_probe_list(approach: str = "standard") -> str:
    """Get available probes for the given scan approach."""
    import json
    return json.dumps({"probes": get_probes(approach)})


class SQLAgent(BaseAgent):
    """Agent specializing in SQL injection and data surface attacks.

    Uses LangChain v1 create_agent with Gemini 2.5 Pro for intelligent
    probe selection based on recon intelligence.
    """

    def __init__(self, model_name: str = "google_genai:gemini-2.5-pro"):
        self._model_name = model_name
        self._agent = None

    @property
    def agent_type(self) -> str:
        return "sql"

    @property
    def system_prompt(self) -> str:
        return SQL_SYSTEM_PROMPT

    @property
    def available_probes(self) -> List[str]:
        return SQL_PROBES

    def _get_or_create_agent(self):
        """Lazy initialization of LangChain agent."""
        if self._agent is None:
            self._agent = create_agent(
                model=self._model_name,
                tools=[analyze_infrastructure, get_probe_list],
                system_prompt=self.system_prompt,
                response_format=ToolStrategy(ProbePlan),
            )
        return self._agent

    async def plan(self, recon_context: Dict[str, Any]) -> ProbePlan:
        """Use LLM to analyze recon and intelligently select probes.

        The agent uses tools to analyze the target infrastructure and
        select appropriate probes, returning a structured ProbePlan.
        """
        agent = self._get_or_create_agent()

        user_message = f"""
        Analyze this target and select SQL/data surface probes:

        Infrastructure: {recon_context.get('infrastructure', {})}
        Detected Tools: {len(recon_context.get('detected_tools', []))} tools found
        Approach: {recon_context.get('approach', 'standard')}

        1. Use analyze_infrastructure to assess SQL-specific risks
        2. Use get_probe_list to see available probes
        3. Select probes with reasoning for each
        """

        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": user_message}]
        })

        return result["structured_response"]
```

### Step 3: Repeat for Auth and Jailbreak

Same pattern:
- `auth/auth_agent.py` - focuses on BOLA, RBAC bypass
- `auth/auth_probes.py` - authorization-specific probes
- `jailbreak/jailbreak_agent.py` - focuses on prompt injection
- `jailbreak/jailbreak_probes.py` - jailbreak/DAN probes

### Step 4: Agent Registry

```python
# agents/__init__.py
"""
Agent registry for scanning agents.

Purpose: Provide factory for getting agent by type
"""
from typing import Dict, Type
from .base_agent import BaseAgent
from .sql import SQLAgent
from .auth import AuthAgent
from .jailbreak import JailbreakAgent


AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "sql": SQLAgent,
    "auth": AuthAgent,
    "jailbreak": JailbreakAgent,
}


def get_agent(agent_type: str, **kwargs) -> BaseAgent:
    """Get agent instance by type.

    Args:
        agent_type: 'sql', 'auth', or 'jailbreak'
        **kwargs: Passed to agent constructor

    Returns:
        Agent instance

    Raises:
        ValueError: If agent_type is unknown
    """
    if agent_type not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_REGISTRY.keys())}")

    return AGENT_REGISTRY[agent_type](**kwargs)
```

## Files to Delete After Migration

- `agents/trinity.py` - Useless wrappers
- `agents/base_utils.py` - Consolidate into base_agent
- `agents/tools.py` - Remove context vars, inline into agents
- `agents/prompts.py` - Replaced by per-agent prompt files

## Testing Strategy

```python
# tests/unit/services/swarm/agents/test_sql_agent.py
import pytest
from services.swarm.agents.sql import SQLAgent


def test_sql_agent_type():
    agent = SQLAgent()
    assert agent.agent_type == "sql"


def test_sql_agent_probes():
    agent = SQLAgent()
    assert "sqli.SqliProbe" in agent.available_probes


@pytest.mark.asyncio
async def test_sql_agent_plan_basic():
    agent = SQLAgent()
    plan = await agent.plan({"approach": "quick"})
    assert len(plan.probes) >= 1
    assert plan.generations > 0


@pytest.mark.asyncio
async def test_sql_agent_plan_with_database():
    agent = SQLAgent()
    plan = await agent.plan({
        "infrastructure": {"database": "PostgreSQL"},
        "approach": "standard",
    })
    # Should increase generations for confirmed SQL db
    assert plan.generations >= 10
```

## Migration Checklist

- [ ] Create `agents/base_agent.py`
- [ ] Create `agents/sql/` directory with 4 files
- [ ] Create `agents/auth/` directory with 4 files
- [ ] Create `agents/jailbreak/` directory with 4 files
- [ ] Update `agents/__init__.py` with registry
- [ ] Update `entrypoint.py` to use new agent structure
- [ ] Add tests for each agent
- [ ] Delete old files (`trinity.py`, `base_utils.py`, etc.)
