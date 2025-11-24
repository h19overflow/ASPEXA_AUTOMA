"""
Example: Scan Target Agent with Swarm Service

Demonstrates the complete workflow:
1. Load reconnaissance results
2. Create scan job dispatch
3. Run Trinity agents against target
4. Aggregate and report findings

Usage:
    python scan_target_with_swarm.py [--recon-file FILE] [--target-url URL]

Environment:
    GOOGLE_API_KEY: Required for LangChain/Gemini
    (Optional) GARAK_HOME: Directory for Garak output
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
import argparse
from dotenv import load_dotenv
from libs.contracts.recon import ReconBlueprint
from services.swarm.agent.worker import run_scanning_agent
from services.swarm.schema import ScanInput
from services.swarm.policies.mapping import get_probe_config
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))



async def scan_with_swarm(
    blueprint: ReconBlueprint,
    target_url: str,
    agents: Optional[list] = None,
    dry_run: bool = False,
) -> dict:
    """
    Scan a target using the Swarm service Trinity agents.

    Args:
        blueprint: Reconnaissance blueprint (IF-02)
        target_url: Target LLM endpoint URL
        agents: List of agents to run (default: all)
        dry_run: If True, only show what would be done (no actual scans)

    Returns:
        Dictionary with results from each agent
    """
    agents = agents or ["agent_sql", "agent_auth", "agent_jailbreak"]

    print("\n" + "=" * 80)
    print("SCANNING WITH SWARM SERVICE")
    print("=" * 80)
    print()
    print(f"Target URL: {target_url}")
    print(f"Audit ID: {blueprint.audit_id}")
    print(f"Agents: {', '.join(agents)}")
    if dry_run:
        print("⚠️  DRY RUN MODE - No actual scans will be executed")
    print()

    # Extract infrastructure details
    infrastructure = {}
    if blueprint.intelligence and blueprint.intelligence.infrastructure:
        infra = blueprint.intelligence.infrastructure
        infrastructure = {
            "vector_db": infra.vector_db,
            "model_family": infra.model_family,
            "rate_limits": infra.rate_limits,
        }

    # Extract detected tools
    detected_tools = []
    if blueprint.intelligence and blueprint.intelligence.detected_tools:
        detected_tools = [
            t.model_dump() for t in blueprint.intelligence.detected_tools
        ]

    results = {}

    for agent_type in agents:
        print(f"📍 Running {agent_type}...")

        # Show probe configuration
        try:
            probe_config = get_probe_config(agent_type, infrastructure)
            print(f"   Probes: {', '.join(probe_config['probes'][:2])}...")
        except Exception as e:
            print(f"   ⚠️  Failed to get probe config: {e}")

        if dry_run:
            print(f"   [DRY RUN] Would execute scan")
            results[agent_type] = {
                "status": "dry_run",
                "message": "Scan not executed (dry run mode)",
            }
            continue

        # Create scan input
        scan_input = ScanInput(
            audit_id=blueprint.audit_id,
            agent_type=agent_type,
            target_url=target_url,
            infrastructure=infrastructure,
            detected_tools=detected_tools,
        )

        # Run agent
        try:
            result = await run_scanning_agent(agent_type, scan_input)
            results[agent_type] = result

            if result["success"]:
                print(f"   ✅ Scan completed successfully")
            else:
                print(f"   ❌ Scan failed: {result.get('error')}")

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results[agent_type] = {"status": "error", "error": str(e)}

        print()

    return results


def load_recon_blueprint(file_path: Path) -> Optional[ReconBlueprint]:
    """Load reconnaissance blueprint from JSON file."""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            blueprint = ReconBlueprint(**data)
            return blueprint
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to load blueprint: {e}")
        return None


def print_summary(results: dict) -> None:
    """Print summary of scan results."""
    print("\n" + "=" * 80)
    print("SCAN RESULTS SUMMARY")
    print("=" * 80)
    print()

    success_count = 0
    failed_count = 0
    error_count = 0

    for agent_type, result in results.items():
        status = result.get("status", "unknown")

        if status == "success":
            print(f"✅ {agent_type}: SUCCESS")
            success_count += 1
        elif status == "dry_run":
            print(f"⚠️  {agent_type}: DRY RUN")
        elif status == "failed":
            print(f"❌ {agent_type}: FAILED - {result.get('error')}")
            failed_count += 1
        else:
            print(f"⚠️  {agent_type}: ERROR - {result.get('error')}")
            error_count += 1

    print()
    print(f"Summary: {success_count} succeeded, {failed_count} failed, {error_count} errors")
    print()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scan target agent using Swarm scanning service"
    )
    parser.add_argument(
        "--recon-file",
        type=Path,
        help="Path to reconnaissance JSON file",
    )
    parser.add_argument(
        "--target-url",
        type=str,
        default="http://localhost:8080/chat",
        help="Target LLM endpoint URL",
    )
    parser.add_argument(
        "--agents",
        type=str,
        default="agent_sql,agent_auth,agent_jailbreak",
        help="Comma-separated list of agents to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--list-recon",
        action="store_true",
        help="List available reconnaissance files",
    )

    args = parser.parse_args()

    # Handle --list-recon
    if args.list_recon:
        recon_dir = Path(__file__).parent.parent.parent / "recon_results"
        print("\n📂 Available reconnaissance files:")
        for file_path in sorted(recon_dir.glob("*.json")):
            print(f"   {file_path.name}")
        return

    # Determine recon file
    if not args.recon_file:
        # Auto-detect latest recon file
        recon_dir = Path(__file__).parent.parent.parent / "recon_results"
        recon_files = sorted(recon_dir.glob("*.json"))
        if not recon_files:
            print("❌ No reconnaissance files found")
            print("   Run: python -m scripts.testing.test_reconnaissance")
            return
        args.recon_file = recon_files[-1]
        print(f"📂 Using latest recon file: {args.recon_file.name}\n")

    # Load blueprint
    print(f"📂 Loading: {args.recon_file}")
    blueprint = load_recon_blueprint(args.recon_file)
    if not blueprint:
        return

    print(f"✅ Loaded blueprint: {blueprint.audit_id}\n")

    # Parse agents
    agents = [a.strip() for a in args.agents.split(",")]

    # Run scan
    results = await scan_with_swarm(
        blueprint=blueprint,
        target_url=args.target_url,
        agents=agents,
        dry_run=args.dry_run,
    )

    # Print summary
    print_summary(results)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⛔ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
