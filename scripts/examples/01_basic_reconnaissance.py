"""
Example: Basic Reconnaissance Usage

This script demonstrates how to use the Cartographer service
to perform reconnaissance on a target agent.
"""
import asyncio
import os
from dotenv import load_dotenv
from services.cartographer.agent.graph import run_reconnaissance

load_dotenv()



async def basic_reconnaissance_example():
    """Run a basic reconnaissance mission."""
    
    print("=" * 80)
    print("📚 EXAMPLE: Basic Reconnaissance")
    print("=" * 80)
    print()
    
    print("This example shows how to:")
    print("  1. Configure reconnaissance parameters")
    print("  2. Run reconnaissance against a target")
    print("  3. Access the collected intelligence")
    print("  4. Results are automatically saved to tests/recon_results/")
    print()
    
    # Configure reconnaissance parameters
    audit_id = "example-basic-001"
    target_url = "http://localhost:8080/chat"
    auth_headers = {}  # Add Authorization headers if needed
    scope = {
        "depth": "standard",        # shallow, standard, aggressive
        "max_turns": 5,             # Number of reconnaissance turns
        "forbidden_keywords": []     # Keywords to avoid in questions
    }
    
    print(f"🎯 Target: {target_url}")
    print(f"📊 Scope: {scope['depth']} depth, max {scope['max_turns']} turns")
    print()
    
    try:
        # Run reconnaissance
        print("🔍 Starting reconnaissance...")
        observations = await run_reconnaissance(
            audit_id=audit_id,
            target_url=target_url,
            auth_headers=auth_headers,
            scope=scope
        )
        
        # Display results
        print()
        print("=" * 80)
        print("📊 RESULTS")
        print("=" * 80)
        print()
        
        print(f"System Prompt: {len(observations['system_prompt'])} observations")
        print(f"Tools: {len(observations['tools'])} observations")
        print(f"Authorization: {len(observations['authorization'])} observations")
        print(f"Infrastructure: {len(observations['infrastructure'])} observations")
        print()
        
        # Show some examples
        if observations['tools']:
            print("🔧 Sample Tools Discovered:")
            for tool in observations['tools'][:3]:
                print(f"   • {tool}")
            print()
        
        if observations['infrastructure']:
            print("🏗️  Sample Infrastructure:")
            for infra in observations['infrastructure'][:3]:
                print(f"   • {infra}")
            print()
        
        print(f"💾 Results saved to: tests/ recon_results/{audit_id}_*.json")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  ERROR: GOOGLE_API_KEY not set!")
        print("   Set it with: $env:GOOGLE_API_KEY = 'your-key'")
        exit(1)
    
    asyncio.run(basic_reconnaissance_example())
