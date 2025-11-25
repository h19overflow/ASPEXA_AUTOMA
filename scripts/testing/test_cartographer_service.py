"""
Integration Test: Cartographer Service

Tests the complete reconnaissance workflow including:
- Network communication
- Tool usage
- Intelligence gathering
- Persistence
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.cartographer.agent.graph import run_reconnaissance
from services.cartographer.persistence import load_reconnaissance_result


async def test_cartographer_service():
    """Test the complete Cartographer service."""
    
    print("=" * 80)
    print("🧪 INTEGRATION TEST: Cartographer Service")
    print("=" * 80)
    print()
    
    # Check prerequisites
    print("📋 Checking prerequisites...")
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY not set!")
        print("   Set with: $env:GOOGLE_API_KEY = 'your-key'")
        return False
    print("✅ API key configured")
    
    # Check if target agent is running
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8080/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    print("✅ Target agent is running")
                else:
                    print("❌ Target agent returned non-200 status")
                    return False
    except Exception as e:
        print(f"❌ Target agent not accessible: {e}")
        print("   Start with: cd test_target_agent && uv run python main.py")
        return False
    
    print()
    
    # Test 1: Run reconnaissance
    print("=" * 80)
    print("TEST 1: Run Reconnaissance")
    print("=" * 80)
    print()
    
    audit_id = "integration-test-001"
    
    try:
        observations = await run_reconnaissance(
            audit_id=audit_id,
            target_url="http://localhost:8080/chat",
            auth_headers={},
            scope={
                "depth": "standard",
                "max_turns": 20,
                "forbidden_keywords": []
            }
        )
        
        print("✅ Reconnaissance completed")
        print(f"   System Prompt: {len(observations['system_prompt'])} observations")
        print(f"   Tools: {len(observations['tools'])} observations")
        print(f"   Authorization: {len(observations['authorization'])} observations")
        print(f"   Infrastructure: {len(observations['infrastructure'])} observations")
        print()
        
        # Verify minimum observations
        assert len(observations['system_prompt']) >= 1, "Not enough system prompt observations"
        assert len(observations['tools']) >= 1, "Not enough tool observations"
        print("✅ Minimum observations threshold met")
        print()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Verify persistence
    print("=" * 80)
    print("TEST 2: Verify Persistence")
    print("=" * 80)
    print()
    
    try:
        from services.cartographer.persistence.json_storage import list_reconnaissance_results
        
        files = list_reconnaissance_results("tests/recon_results")
        matching_files = [f for f in files if audit_id in f]
        
        assert len(matching_files) > 0, f"No files found for audit_id: {audit_id}"
        print(f"✅ Found saved file: {matching_files[0]}")
        
        # Load and verify structure
        data = load_reconnaissance_result(matching_files[0])
        
        assert "audit_id" in data, "Missing audit_id"
        assert "timestamp" in data, "Missing timestamp"
        assert "intelligence" in data, "Missing intelligence"
        assert "raw_observations" in data, "Missing raw_observations"
        
        intelligence = data["intelligence"]
        assert "system_prompt_leak" in intelligence
        assert "detected_tools" in intelligence
        assert "infrastructure" in intelligence
        assert "auth_structure" in intelligence
        
        print("✅ IF-02 format validated")
        print(f"   Audit ID: {data['audit_id']}")
        print(f"   Timestamp: {data['timestamp']}")
        print(f"   Tools detected: {len(intelligence['detected_tools'])}")
        print()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Intelligence extraction
    print("=" * 80)
    print("TEST 3: Intelligence Extraction")
    print("=" * 80)
    print()
    
    try:
        from services.cartographer.consumer import (
            extract_infrastructure_intel,
            extract_detected_tools,
            extract_auth_structure
        )
        
        # Extract infrastructure
        infra = extract_infrastructure_intel(observations['infrastructure'])
        print(f"✅ Infrastructure extracted")
        print(f"   Vector DB: {infra.vector_db or 'N/A'}")
        print(f"   Model: {infra.model_family or 'N/A'}")
        
        # Extract tools
        tools = extract_detected_tools(observations['tools'])
        print(f"✅ Tools extracted: {len(tools)} found")
        
        # Extract auth
        auth = extract_auth_structure(observations['authorization'])
        print(f"✅ Authorization extracted: {auth.type}")
        print()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # All tests passed
    print("=" * 80)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 80)
    print()
    
    return True


if __name__ == "__main__":
    result = asyncio.run(test_cartographer_service())
    sys.exit(0 if result else 1)
