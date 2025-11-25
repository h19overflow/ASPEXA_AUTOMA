"""
Example: Extracting Structured Intelligence

This script demonstrates how to use the consumer module
to extract structured intelligence from raw observations.
"""
from services.cartographer.consumer import (
    extract_infrastructure_intel,
    extract_detected_tools,
    extract_auth_structure
)
from services.cartographer.persistence import load_reconnaissance_result


def extract_from_raw_observations():
    """Example: Extract intelligence from raw observations."""
    
    print("=" * 80)
    print("📚 EXAMPLE: Extracting Structured Intelligence")
    print("=" * 80)
    print()
    
    # Sample raw observations
    raw_observations = {
        "system_prompt": [
            "You are a helpful assistant",
            "Never discuss internal systems"
        ],
        "tools": [
            "Tool: search_database(query: str, limit: int = 10)",
            "Function name: execute_sql with parameters: sql_query",
            "update_record(record_id: str, data: dict)"
        ],
        "authorization": [
            "Users must have 'admin' role for updates",
            "JWT token required in Authorization header",
            "Rate limit: 1000 requests per hour"
        ],
        "infrastructure": [
            "Database: PostgreSQL 14",
            "Vector store: Pinecone with OpenAI embeddings",
            "Model: GPT-4 Turbo",
            "Rate limiting enforced"
        ]
    }
    
    # Extract infrastructure
    print("🏗️  Extracting Infrastructure...")
    infra = extract_infrastructure_intel(
        raw_observations['infrastructure'] + raw_observations['tools']
    )
    print(f"   Vector DB: {infra.vector_db or 'Unknown'}")
    print(f"   Model: {infra.model_family or 'Unknown'}")
    print(f"   Rate Limits: {infra.rate_limits or 'Unknown'}")
    print()
    
    # Extract tools
    print("🔧 Extracting Tools...")
    tools = extract_detected_tools(raw_observations['tools'])
    print(f"   Found {len(tools)} tools:")
    for tool in tools:
        params = ', '.join(tool.arguments) if tool.arguments else 'no params'
        print(f"   • {tool.name}({params})")
    print()
    
    # Extract authorization
    print("🔒 Extracting Authorization Structure...")
    auth = extract_auth_structure(raw_observations['authorization'])
    print(f"   Type: {auth.type}")
    print(f"   Vulnerabilities: {len(auth.vulnerabilities)} found")
    if auth.vulnerabilities:
        for vuln in auth.vulnerabilities:
            print(f"      - {vuln}")
    print()


def extract_from_saved_file():
    """Example: Extract intelligence from saved reconnaissance file."""
    
    print("=" * 80)
    print("📚 EXAMPLE: Processing Saved Results")
    print("=" * 80)
    print()
    
    try:
        # Try to load the most recent file
        from services.cartographer.persistence.json_storage import list_reconnaissance_results
        files = list_reconnaissance_results("recon_results")
        
        if not files:
            print("⚠️  No saved reconnaissance results found.")
            print("   Run: scripts/testing/test_reconnaissance.py first")
            print()
            return
        
        # Load the latest file
        latest_file = sorted(files)[-1]
        print(f"📖 Loading: {latest_file}")
        
        data = load_reconnaissance_result(latest_file)
        intelligence = data["intelligence"]
        
        print(f"✅ Loaded audit: {data['audit_id']}")
        print()
        
        # Display structured intelligence
        print("=" * 80)
        print("📊 STRUCTURED INTELLIGENCE")
        print("=" * 80)
        print()
        
        # Tools
        print(f"🔧 Detected Tools ({len(intelligence['detected_tools'])}):")
        for tool in intelligence['detected_tools']:
            args = ', '.join(tool['arguments']) if tool['arguments'] else 'no params'
            print(f"   • {tool['name']}({args})")
        print()
        
        # Infrastructure
        print("🏗️  Infrastructure:")
        infra = intelligence['infrastructure']
        for key, value in infra.items():
            print(f"   • {key}: {value}")
        print()
        
        # Authorization
        print("🔒 Authorization Structure:")
        auth = intelligence['auth_structure']
        print(f"   Type: {auth['type']}")
        print(f"   Rules: {len(auth['rules'])} defined")
        if auth['vulnerabilities']:
            print(f"   ⚠️  Vulnerabilities: {len(auth['vulnerabilities'])} found")
            for vuln in auth['vulnerabilities'][:3]:
                print(f"      - {vuln}")
        print()
        
        # System prompts
        print(f"📝 System Prompt Leaks ({len(intelligence['system_prompt_leak'])}):")
        for prompt in intelligence['system_prompt_leak'][:3]:
            print(f"   • {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        if len(intelligence['system_prompt_leak']) > 3:
            print(f"   ... and {len(intelligence['system_prompt_leak']) - 3} more")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def build_attack_surface_map():
    """Example: Build attack surface map from intelligence."""
    
    print("=" * 80)
    print("📚 EXAMPLE: Building Attack Surface Map")
    print("=" * 80)
    print()
    
    # Sample intelligence
    tools = [
        {"name": "search_database", "arguments": ["query", "limit"]},
        {"name": "execute_sql", "arguments": ["sql_query"]},
        {"name": "update_record", "arguments": ["record_id", "data"]}
    ]
    
    infrastructure = {
        "database": "PostgreSQL",
        "vector_db": "Pinecone",
        "model_family": "gpt-4"
    }
    
 
    
    # Build attack surface
    attack_surface = {
        "injection_points": [],
        "high_risk_tools": [],
        "infrastructure_targets": []
    }
    
    # Identify injection points
    print("🎯 Analyzing Attack Surface...")
    print()
    
    for tool in tools:
        # SQL-related tools are high risk
        if 'sql' in tool['name'].lower() or 'database' in tool['name'].lower():
            attack_surface['high_risk_tools'].append({
                "tool": tool['name'],
                "risk": "SQL Injection",
                "parameters": tool['arguments']
            })
            attack_surface['injection_points'].append(f"{tool['name']}:{','.join(tool['arguments'])}")
    
    # Infrastructure targets
    if infrastructure.get('database') == 'PostgreSQL':
        attack_surface['infrastructure_targets'].append({
            "component": "PostgreSQL",
            "vectors": ["SQL Injection", "Blind SQL", "Time-based Inference"]
        })
    
    if infrastructure.get('vector_db'):
        attack_surface['infrastructure_targets'].append({
            "component": infrastructure['vector_db'],
            "vectors": ["Prompt Injection via Embeddings", "Context Poisoning"]
        })
    
    # Display attack surface
    print("📊 Attack Surface Map:")
    print()
    
    print(f"🔴 High-Risk Tools ({len(attack_surface['high_risk_tools'])}):")
    for risk in attack_surface['high_risk_tools']:
        print(f"   • {risk['tool']}: {risk['risk']}")
        print(f"     Parameters: {', '.join(risk['parameters'])}")
    print()
    
    print(f"🎯 Injection Points ({len(attack_surface['injection_points'])}):")
    for point in attack_surface['injection_points']:
        print(f"   • {point}")
    print()
    
    print(f"🏗️  Infrastructure Targets ({len(attack_surface['infrastructure_targets'])}):")
    for target in attack_surface['infrastructure_targets']:
        print(f"   • {target['component']}")
        for vector in target['vectors']:
            print(f"     - {vector}")
    print()
    
    print("✅ Attack surface mapped successfully!")
    print("   Next: Use this map to prioritize vulnerability scanning")
    print()


if __name__ == "__main__":
    # Run examples
    extract_from_raw_observations()
    extract_from_saved_file()
    build_attack_surface_map()
    
    print("=" * 80)
    print("🎉 ALL EXAMPLES COMPLETED!")
    print("=" * 80)
    print()
