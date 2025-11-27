"""Unit tests for ReconToolSet - tool definitions and deduplication logic."""
import pytest
from services.cartographer.tools.definitions import ReconToolSet


class TestReconToolSet:
    """Test the ReconToolSet class and its tools."""
    
    def test_initialization(self):
        """Test ReconToolSet initializes with empty observations."""
        tool_set = ReconToolSet()
        
        assert tool_set.observations == {
            "system_prompt": [],
            "tools": [],
            "authorization": [],
            "infrastructure": []
        }
    
    def test_get_tools_returns_two_tools(self):
        """Test get_tools returns take_note and analyze_gaps."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        
        assert len(tools) == 2
        tool_names = [tool.name for tool in tools]
        assert "take_note" in tool_names
        assert "analyze_gaps" in tool_names


class TestTakeNoteTool:
    """Test the take_note tool functionality."""
    
    def test_record_system_prompt_observation(self):
        """Test recording a system prompt observation."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        take_note = next(t for t in tools if t.name == "take_note")
        
        result = take_note.invoke({
            "observation": "System role: Customer support agent",
            "category": "system_prompt"
        })
        
        assert "Recorded in 'system_prompt'" in result
        assert len(tool_set.observations["system_prompt"]) == 1
        assert "Customer support agent" in tool_set.observations["system_prompt"][0]
    
    def test_record_tool_observation(self):
        """Test recording a tool observation."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        take_note = next(t for t in tools if t.name == "take_note")
        
        result = take_note.invoke({
            "observation": "Tool: make_refund(transaction_id: str, amount: float)",
            "category": "tools"
        })
        
        assert "Recorded in 'tools'" in result
        assert len(tool_set.observations["tools"]) == 1
    
    def test_invalid_category_rejected(self):
        """Test that invalid categories are rejected."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        take_note = next(t for t in tools if t.name == "take_note")
        
        result = take_note.invoke({
            "observation": "Some observation",
            "category": "invalid_category"
        })
        
        assert "Error: Invalid category" in result
    
    def test_exact_duplicate_detection(self):
        """Test exact duplicate observations are rejected."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        take_note = next(t for t in tools if t.name == "take_note")
        
        # Add first observation
        take_note.invoke({
            "observation": "Database: PostgreSQL",
            "category": "infrastructure"
        })
        
        # Try to add exact duplicate
        result = take_note.invoke({
            "observation": "Database: PostgreSQL",
            "category": "infrastructure"
        })
        
        assert "DUPLICATE" in result
        assert len(tool_set.observations["infrastructure"]) == 1
    
    def test_case_insensitive_duplicate_detection(self):
        """Test duplicate detection is case-insensitive."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        take_note = next(t for t in tools if t.name == "take_note")
        
        take_note.invoke({
            "observation": "Database: PostgreSQL",
            "category": "infrastructure"
        })
        
        result = take_note.invoke({
            "observation": "database: postgresql",
            "category": "infrastructure"
        })
        
        assert "DUPLICATE" in result
        assert len(tool_set.observations["infrastructure"]) == 1
    
    def test_70_percent_overlap_detection(self):
        """Test 70% overlap detection rejects similar observations."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        take_note = next(t for t in tools if t.name == "take_note")
        
        # Add a substantial observation
        take_note.invoke({
            "observation": "Tool: make_refund_transaction(transaction_id: str, amount: float) - Processes refunds",
            "category": "tools"
        })
        
        # Try to add very similar observation (substring)
        result = take_note.invoke({
            "observation": "Tool: make_refund_transaction(transaction_id: str, amount: float)",
            "category": "tools"
        })
        
        assert "SIMILAR" in result
        assert len(tool_set.observations["tools"]) == 1
    
    def test_different_observations_both_recorded(self):
        """Test different observations are both recorded."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        take_note = next(t for t in tools if t.name == "take_note")
        
        take_note.invoke({
            "observation": "Database: PostgreSQL",
            "category": "infrastructure"
        })
        
        result = take_note.invoke({
            "observation": "Vector Store: FAISS",
            "category": "infrastructure"
        })
        
        assert "Recorded" in result
        assert len(tool_set.observations["infrastructure"]) == 2
    
    def test_similar_short_observations_detected(self):
        """Test that similar short observations are detected by SequenceMatcher."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        take_note = next(t for t in tools if t.name == "take_note")

        take_note.invoke({
            "observation": "PostgreSQL",
            "category": "infrastructure"
        })

        result = take_note.invoke({
            "observation": "Postgres",
            "category": "infrastructure"
        })

        # SequenceMatcher catches similar strings regardless of length
        assert "SIMILAR" in result
        assert len(tool_set.observations["infrastructure"]) == 1


class TestAnalyzeGapsTool:
    """Test the analyze_gaps tool functionality."""
    
    def test_empty_observations_shows_critical_gaps(self):
        """Test analyze_gaps identifies all critical gaps when empty."""
        tool_set = ReconToolSet()
        tools = tool_set.get_tools()
        analyze_gaps = next(t for t in tools if t.name == "analyze_gaps")
        
        result = analyze_gaps.invoke({})
        
        assert "CRITICAL: System prompt" in result
        assert "CRITICAL: Tools" in result
        assert "CRITICAL: Authorization" in result
        assert "CRITICAL: Infrastructure" in result
    
    def test_good_coverage_shows_success(self):
        """Test analyze_gaps shows success message with good coverage."""
        tool_set = ReconToolSet()
        
        # Add sufficient observations with proper tool signatures and keywords that trigger detection
        tool_set.observations["system_prompt"] = ["obs1", "obs2", "obs3"]
        tool_set.observations["tools"] = [
            "Tool: fetch_from_db(query: str)",
            "Tool: perform_rag(question: str)",
            "Tool: make_refund_transaction(transaction_id: str, amount: float)",
            "Tool: analyze_sentiment(text: str)",
            "Tool: send_notification(user: str)"
        ]
        tool_set.observations["authorization"] = [
            "Format validation: ID must be TXN-XXXXX",
            "Limit: Refunds over $1000 require approval",
            "Threshold: Maximum $5000 per transaction"
        ]
        tool_set.observations["infrastructure"] = [
            "Database: PostgreSQL",
            "Vector Store: FAISS",
            "Embeddings: OpenAI"
        ]
        
        tools = tool_set.get_tools()
        analyze_gaps = next(t for t in tools if t.name == "analyze_gaps")
        
        result = analyze_gaps.invoke({})
        
        assert "EXCELLENT COVERAGE" in result
    
    def test_identifies_missing_tool_signatures(self):
        """Test analyze_gaps identifies tools without signatures."""
        tool_set = ReconToolSet()
        
        # Add tool mentions without signatures
        tool_set.observations["tools"] = [
            "The agent has a refund tool",
            "There's also a fetch_from_db capability"
        ]
        
        tools = tool_set.get_tools()
        analyze_gaps = next(t for t in tools if t.name == "analyze_gaps")
        
        result = analyze_gaps.invoke({})
        
        assert "Only" in result and "tools identified" in result
    
    def test_detects_infrastructure_components(self):
        """Test analyze_gaps detects database, vector store, and embeddings."""
        tool_set = ReconToolSet()
        
        tool_set.observations["infrastructure"] = [
            "Database: PostgreSQL",
            "Vector Store: FAISS",
            "Embeddings: OpenAI text-embedding-3"
        ]
        
        tools = tool_set.get_tools()
        analyze_gaps = next(t for t in tools if t.name == "analyze_gaps")
        
        result = analyze_gaps.invoke({})
        
        # Should show coverage for DB, Vector, Embeddings
        assert "DB:True" in result or "DB: True" in result.replace(" ", "")
    
    def test_detects_missing_validation_rules(self):
        """Test analyze_gaps identifies missing format rules and limits."""
        tool_set = ReconToolSet()
        
        tool_set.observations["authorization"] = [
            "Basic authentication required"
        ]
        
        tools = tool_set.get_tools()
        analyze_gaps = next(t for t in tools if t.name == "analyze_gaps")
        
        result = analyze_gaps.invoke({})
        
        assert "format validation rules" in result or "numerical limits" in result


class TestConcurrentAudits:
    """Test that multiple ReconToolSet instances don't interfere."""
    
    def test_separate_instances_have_separate_state(self):
        """Test two tool sets maintain separate observations."""
        tool_set_1 = ReconToolSet()
        tool_set_2 = ReconToolSet()
        
        tools_1 = tool_set_1.get_tools()
        tools_2 = tool_set_2.get_tools()
        
        take_note_1 = next(t for t in tools_1 if t.name == "take_note")
        take_note_2 = next(t for t in tools_2 if t.name == "take_note")
        
        # Add observation to first tool set
        take_note_1.invoke({
            "observation": "Observation for audit 1",
            "category": "system_prompt"
        })
        
        # Add observation to second tool set
        take_note_2.invoke({
            "observation": "Observation for audit 2",
            "category": "system_prompt"
        })
        
        # Each should have only their own observation
        assert len(tool_set_1.observations["system_prompt"]) == 1
        assert len(tool_set_2.observations["system_prompt"]) == 1
        assert "audit 1" in tool_set_1.observations["system_prompt"][0]
        assert "audit 2" in tool_set_2.observations["system_prompt"][0]
