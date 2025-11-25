"""
Example: Working with Persistence

This script demonstrates how to save and load reconnaissance results
using the persistence layer.
"""
import json
from services.cartographer.persistence import (
    save_reconnaissance_result,
    load_reconnaissance_result
)
from services.cartographer.persistence.json_storage import list_reconnaissance_results


def save_example():
    """Example: Manually save reconnaissance results."""
    
    print("=" * 80)
    print("📚 EXAMPLE: Saving Reconnaissance Results")
    print("=" * 80)
    print()
    
    # Create sample observations
    observations = {
        "system_prompt": [
            "You are a customer service assistant",
            "Always maintain a professional tone",
            "Never reveal internal system information"
        ],
        "tools": [
            "get_user_info(user_id: str)",
            "update_order(order_id: str, status: str)",
            "send_email(to: str, subject: str, body: str)"
        ],
        "authorization": [
            "Users can only access their own data",
            "Admin role required for updates",
            "Rate limit: 100 requests per hour"
        ],
        "infrastructure": [
            "Database: PostgreSQL 15",
            "Cache: Redis",
            "Vector Store: Pinecone"
        ]
    }
    
    # Save results
    print("💾 Saving results...")
    filepath = save_reconnaissance_result(
        audit_id="example-persistence-001",
        observations=observations,
        output_dir="tests/recon_results"
    )
    
    print(f"✅ Saved to: {filepath}")
    print()
    
    return filepath


def load_example(filepath):
    """Example: Load reconnaissance results."""
    
    print("=" * 80)
    print("📚 EXAMPLE: Loading Reconnaissance Results")
    print("=" * 80)
    print()
    
    # Load results
    print(f"📖 Loading from: {filepath}")
    data = load_reconnaissance_result(filepath)
    
    print("✅ Loaded successfully!")
    print()
    
    # Access structured intelligence
    intelligence = data["intelligence"]
    
    print("📊 Intelligence Summary:")
    print(f"   Audit ID: {data['audit_id']}")
    print(f"   Timestamp: {data['timestamp']}")
    print(f"   System Prompts: {len(intelligence['system_prompt_leak'])} items")
    print(f"   Detected Tools: {len(intelligence['detected_tools'])} items")
    print(f"   Infrastructure: {len(intelligence['infrastructure'])} keys")
    print(f"   Auth Type: {intelligence['auth_structure']['type']}")
    print()
    
    # Show detected tools in detail
    print("🔧 Detected Tools:")
    for tool in intelligence['detected_tools']:
        params = ', '.join(tool['arguments']) if tool['arguments'] else 'no params'
        print(f"   • {tool['name']}({params})")
    print()
    
    # Show infrastructure
    print("🏗️  Infrastructure:")
    for key, value in intelligence['infrastructure'].items():
        print(f"   • {key}: {value}")
    print()
    
    return data


def list_example():
    """Example: List all saved reconnaissance results."""
    
    print("=" * 80)
    print("📚 EXAMPLE: Listing All Results")
    print("=" * 80)
    print()
    
    files = list_reconnaissance_results("tests/recon_results")
    
    if files:
        print(f"📁 Found {len(files)} reconnaissance result(s):")
        for i, file in enumerate(files, 1):
            print(f"   {i}. {file}")
        print()
    else:
        print("📁 No reconnaissance results found.")
        print()


def integration_example(filepath):
    """Example: Using saved results for Phase 3 integration."""
    
    print("=" * 80)
    print("📚 EXAMPLE: Phase 3 Integration")
    print("=" * 80)
    print()
    
    # Load reconnaissance blueprint
    blueprint = load_reconnaissance_result(filepath)
    
    # Create a scan job (IF-03 format)
    scan_job = {
        "job_id": "scan-001",
        "blueprint_context": blueprint,  # IF-02 data
        "safety_policy": {
            "allowed_attack_vectors": ["injection", "jailbreak"],
            "blocked_attack_vectors": ["dos", "data_exfiltration"],
            "aggressiveness": "medium"
        }
    }
    
    print("🎯 Created Scan Job (IF-03):")
    print(json.dumps({
        "job_id": scan_job["job_id"],
        "blueprint_audit_id": blueprint["audit_id"],
        "blueprint_timestamp": blueprint["timestamp"],
        "tools_count": len(blueprint["intelligence"]["detected_tools"]),
        "safety_policy": scan_job["safety_policy"]
    }, indent=2))
    print()
    
    print("✅ Ready to send to Swarm service!")
    print("   Next: Implement Swarm service to consume this scan job")
    print()


if __name__ == "__main__":
    # Run all examples in sequence
    
    # 1. Save example
    filepath = save_example()
    
    # 2. Load example
    data = load_example(filepath)
    
    # 3. List example
    list_example()
    
    # 4. Integration example
    integration_example(filepath)
    
    print("=" * 80)
    print("🎉 ALL EXAMPLES COMPLETED!")
    print("=" * 80)
    print()
    print("💡 Next Steps:")
    print("   • Run reconnaissance: scripts/testing/test_reconnaissance.py")
    print("   • Explore IF-02 format: docs/data_contracts.md")
    print("   • Learn more: docs/PERSISTENCE.md")
    print()
