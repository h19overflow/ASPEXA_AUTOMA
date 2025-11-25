"""
Simple Swarm Scanner - Linear, no-nonsense version.

Usage: python -m scripts.simple_scan

Supports:
- HTTP and WebSocket endpoints (auto-detected from URL)
- Parallel execution (optional)
- Rate limiting (optional)
- All production features
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
# CONFIGURATION - Change these settings
# =============================================================================
TARGET_URL = "http://localhost:8080/chat"  # Supports: http://, https://, ws://, wss://
RECON_FILE = Path("tests" / "recon_results" / "integration-test-001_20251124_042930.json")
MODE = "standard"  # quick=1 probe, standard=3 probes, thorough=10 probes

# Production features (optional)
ENABLE_PARALLEL = False  # Set to True to enable parallel execution
ENABLE_RATE_LIMITING = False  # Set to True to enable rate limiting
RATE_LIMIT_RPS = 10.0  # Requests per second (if rate limiting enabled)

# Mode settings
MODES = {
    "quick":    {"probes": 1, "gens": 1, "concurrent_probes": 1, "concurrent_gens": 1},
    "standard": {"probes": 8, "gens": 1, "concurrent_probes": 4, "concurrent_gens": 2},
    "thorough": {"probes": 10, "gens": 5, "concurrent_probes": 3, "concurrent_gens": 2},
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

    # Auto-detect connection type from URL
    connection_type = None
    if TARGET_URL.startswith(("ws://", "wss://")):
        connection_type = "websocket"
    elif TARGET_URL.startswith(("http://", "https://")):
        connection_type = "http"

    scan_config = ScanConfig(
        approach=MODE,
        max_probes=settings["probes"],
        max_generations=settings["gens"],
        # Production features
        enable_parallel_execution=ENABLE_PARALLEL,
        max_concurrent_probes=settings.get("concurrent_probes", 1),
        max_concurrent_generations=settings.get("concurrent_gens", 1),
        max_concurrent_connections=10,
        requests_per_second=RATE_LIMIT_RPS if ENABLE_RATE_LIMITING else None,
        connection_type=connection_type,
        request_timeout=30,
        max_retries=3,
        retry_backoff=1.0,
    )

    scan_input = ScanInput(
        audit_id="simple-scan-001",
        agent_type="agent_jailbreak",
        target_url=TARGET_URL,
        infrastructure=intel.get("infrastructure", {}),
        detected_tools=intel.get("detected_tools", []),
        config=scan_config,
    )
    print(f"    Target: {TARGET_URL}")
    print(f"    Connection: {connection_type or 'auto-detect'}")
    print(f"    Probes: {settings['probes']}, Generations: {settings['gens']}")
    if ENABLE_PARALLEL:
        print(f"    Parallel: {settings.get('concurrent_probes', 1)} probes, {settings.get('concurrent_gens', 1)} gens")
    if ENABLE_RATE_LIMITING:
        print(f"    Rate Limit: {RATE_LIMIT_RPS} RPS")

    # 3. Run the scan
    print("\n[3] Running jailbreak agent...")
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

        if vulns:
            print("\nVulnerabilities:")
            for v in vulns:
                cat = v.get("category", "unknown")
                sev = v.get("severity", "unknown")
                print(f"  - [{sev.upper()}] {cat}")
        else:
            print("\nNo vulnerabilities detected.")

    else:
        print("\nStatus: FAILED")
        print(f"Error: {result.get('error', 'Unknown')}")

    print("\n" + "=" * 60)


# Run it
if __name__ == "__main__":
    asyncio.run(main())
