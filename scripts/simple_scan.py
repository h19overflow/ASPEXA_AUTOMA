"""
Simple Swarm Scanner - Linear, no-nonsense version.

Usage: python -m scripts.simple_scan
"""
import asyncio
import json
from pathlib import Path

# Add project root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.swarm.agents.trinity import run_jailbreak_agent
from services.swarm.core.schema import ScanInput, ScanConfig

# =============================================================================
# CONFIGURATION - Change these 3 things
# =============================================================================
TARGET_URL = "http://localhost:8080/chat"
RECON_FILE = Path("recon_results/integration-test-001_20251124_042930.json")
MODE = "standard"  # quick=1 probe, standard=3 probes, thorough=10 probes

# Mode settings
MODES = {
    "quick":    {"probes": 1, "gens": 1},
    "standard": {"probes": 3, "gens": 2},
    "thorough": {"probes": 10, "gens": 5},
}

# =============================================================================
# MAIN SCRIPT - Linear execution
# =============================================================================
async def main():
    print("=" * 60)
    print("SIMPLE SWARM SCANNER")
    print("=" * 60)

    # 1. Load intelligence
    print(f"\n[1] Loading intelligence from: {RECON_FILE}")
    with open(RECON_FILE) as f:
        data = json.load(f)
    intel = data.get("intelligence", {})
    print(f"    Found: {len(intel.get('detected_tools', []))} tools, "
          f"{len(intel.get('system_prompt_leak', []))} leaks")

    # 2. Build scan input
    print(f"\n[2] Building scan config: {MODE} mode")
    settings = MODES[MODE]

    scan_input = ScanInput(
        audit_id=f"simple-scan-001",
        agent_type="agent_jailbreak",
        target_url=TARGET_URL,
        infrastructure=intel.get("infrastructure", {}),
        detected_tools=intel.get("detected_tools", []),
        config=ScanConfig(
            approach=MODE,
            max_probes=settings["probes"],
            max_generations=settings["gens"],
        ),
    )
    print(f"    Target: {TARGET_URL}")
    print(f"    Probes: {settings['probes']}, Generations: {settings['gens']}")

    # 3. Run the scan
    print(f"\n[3] Running jailbreak agent...")
    print("    (This may take a minute...)")

    result = await run_jailbreak_agent(scan_input)

    # 4. Show results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if result is None:
        print("ERROR: Agent returned None")
        return

    if result.get("success"):
        vulns = result.get("vulnerabilities", [])
        probes = result.get("probes_executed", [])
        metadata = result.get("metadata", {})
        report = result.get("report_path", "")

        print(f"\nStatus: SUCCESS")
        print(f"Probes executed: {probes}")
        print(f"Vulnerabilities found: {len(vulns)}")

        # Stats
        print(f"\nScan Statistics:")
        print(f"  - Total results: {metadata.get('total_results', 0)}")
        print(f"  - Passed: {metadata.get('pass_count', 0)}")
        print(f"  - Failed: {metadata.get('fail_count', 0)}")
        print(f"  - Errors: {metadata.get('error_count', 0)}")

        # Vulnerabilities
        if vulns:
            print(f"\nVulnerabilities:")
            for v in vulns:
                cat = v.get("category", "unknown")
                sev = v.get("severity", "unknown")
                print(f"  - [{sev.upper()}] {cat}")
        else:
            print("\nNo vulnerabilities detected.")

        print(f"\nReport: {report}")
    else:
        print(f"\nStatus: FAILED")
        print(f"Error: {result.get('error', 'Unknown')}")

    print("\n" + "=" * 60)


# Run it
if __name__ == "__main__":
    asyncio.run(main())
