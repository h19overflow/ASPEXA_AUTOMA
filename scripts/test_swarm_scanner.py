#!/usr/bin/env python3
"""
Swarm Scanner Test Script
========================

Purpose: Test the Swarm scanning system with REAL intelligence data
         from reconnaissance and demonstrate actual vulnerability detection.
         Default configuration is simple (quick mode) for basic verification.

Configuration Entry Points:
---------------------------
1. TARGET_URL: The endpoint to attack (default: http://localhost:8080/chat)
2. RECON_FILE: Path to reconnaissance intelligence JSON
3. SCAN_MODE: 'quick' (default) | 'standard' | 'thorough'
4. AGENT_TYPE: 'jailbreak' (default) | 'sql' | 'auth' | 'all'

Understanding Scan Parameters:
------------------------------
- max_probes: Maximum number of DIFFERENT probe types to run
  * Each probe is a different attack type (e.g., "dan", "promptinj", "encoding")
  * Example: max_probes=2 means run up to 2 different probe types
  * Each probe has multiple prompts (attack variations)
  
- max_generations: Maximum number of ATTEMPTS per probe
  * How many times to generate outputs for each prompt in a probe
  * Example: max_generations=2 means try each prompt 2 times
  * Higher = more reliable detection but slower
  
Total Attack Count = (probes × prompts_per_probe × generations)
Example: 2 probes × 5 prompts × 2 generations = 20 total attacks

Intelligence Loading:
--------------------
Loads actual recon data from: recon_results/integration-test-001_20251124_042930.json
This includes:
- System prompt leaks (refund approval rules)
- Tool signatures (process_refund, check_balance, etc.)
- Authorization structure ($1000 threshold)
- Infrastructure details (FAISS, OpenAI embeddings)

What This Tests:
---------------
✓ Agent decision-making based on real intelligence
✓ Scanner probe selection and execution
✓ Detector evaluation (pass/fail determination)
✓ Report generation with vulnerability clusters
✓ End-to-end Swarm pipeline

Expected Vulnerabilities:
------------------------
1. Authorization Bypass: Exploiting $1000 refund threshold
2. Tool Parameter Manipulation: Crafting malicious transaction IDs
3. Prompt Injection: Bypassing system constraints
4. Information Disclosure: Extracting more system details
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.swarm.agents.trinity import (
    run_jailbreak_agent,
    run_sql_agent,
    run_auth_agent,
)
from services.swarm.core.schema import ScanInput, ScanConfig
from services.swarm.core.config import AgentType

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'swarm_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION ENTRY POINTS
# ============================================================================

class TestConfig:
    """Centralized test configuration"""
    
    # Target Configuration
    TARGET_URL = "http://localhost:8080/chat"  # 👈 CHANGE THIS to your target
    
    # Intelligence File
    RECON_FILE = project_root / "recon_results" / "integration-test-001_20251124_042930.json"
    
    # Scan Configuration
    SCAN_MODE = "quick"  # quick | standard | thorough | aggressive (default: quick for simple testing)
    AGENT_TYPE = "jailbreak"  # jailbreak | sql | auth | all (default: jailbreak for simple testing)
    
    # Scan Intensity Settings
    # max_probes = number of different attack types (probes) to run
    # max_generations = number of attempts per probe prompt
    SCAN_CONFIG = {
        "quick": {
            "max_probes": 1,        # Run just 1 probe type for fastest testing
            "max_generations": 1,    # Try each prompt 1 time
            "approach": "quick"      # Use quick approach defaults
        },
        "standard": {
            "max_probes": 3,
            "max_generations": 2,
            "approach": "standard"
        },
        "thorough": {
            "max_probes": 10,
            "max_generations": 5,
            "approach": "thorough"
        },
    }
    
    # Output Configuration
    OUTPUT_DIR = project_root / "garak_runs"
    RESULTS_DIR = project_root / "test_results"


# ============================================================================
# INTELLIGENCE LOADER
# ============================================================================

def load_recon_intelligence(recon_file: Path) -> Dict[str, Any]:
    """
    Load and parse reconnaissance intelligence.
    
    Returns structured intelligence including:
    - infrastructure: Database, model info
    - detected_tools: Tool signatures and parameters
    - auth_structure: Authorization rules
    - system_prompt_leak: Extracted system constraints
    """
    logger.info(f"📖 Loading intelligence from: {recon_file}")
    
    if not recon_file.exists():
        logger.error(f"❌ Intelligence file not found: {recon_file}")
        raise FileNotFoundError(f"Recon file missing: {recon_file}")
    
    with open(recon_file, 'r') as f:
        data = json.load(f)
    
    intelligence = data.get('intelligence', {})
    
    # Extract key intelligence
    result = {
        "infrastructure": intelligence.get('infrastructure', {}),
        "detected_tools": intelligence.get('detected_tools', []),
        "auth_structure": intelligence.get('auth_structure', {}),
        "system_prompt_leaks": intelligence.get('system_prompt_leak', []),
    }
    
    # Log what we found
    logger.info(f"✓ Infrastructure: {result['infrastructure']}")
    logger.info(f"✓ Tools detected: {len(result['detected_tools'])}")
    logger.info(f"✓ Auth rules: {len(result['auth_structure'].get('rules', []))}")
    logger.info(f"✓ System leaks: {len(result['system_prompt_leaks'])}")
    
    return result


# ============================================================================
# INTELLIGENCE ANALYSIS
# ============================================================================

def analyze_intelligence(intel: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze intelligence to determine attack strategy.
    
    This mimics what the AI agent would think about.
    """
    logger.info("🧠 Analyzing intelligence for attack vectors...")
    
    analysis = {
        "risk_level": "medium",
        "attack_surfaces": [],
        "recommended_agents": [],
        "key_findings": [],
    }
    
    # Check for authorization vulnerabilities
    auth_rules = intel.get('auth_structure', {}).get('rules', [])
    if any('$1000' in rule for rule in auth_rules):
        analysis["attack_surfaces"].append("authorization")
        analysis["recommended_agents"].append("auth")
        analysis["key_findings"].append("🎯 $1000 refund threshold - potential bypass opportunity")
        analysis["risk_level"] = "high"
    
    # Check for tool exploitation vectors
    tools = intel.get('detected_tools', [])
    if len(tools) > 5:
        analysis["attack_surfaces"].append("tools")
        analysis["recommended_agents"].append("sql")
        analysis["key_findings"].append(f"🎯 {len(tools)} tools detected - high attack surface")
    
    # Check for prompt injection vectors
    leaks = intel.get('system_prompt_leaks', [])
    if leaks:
        analysis["attack_surfaces"].append("prompt")
        analysis["recommended_agents"].append("jailbreak")
        analysis["key_findings"].append(f"🎯 {len(leaks)} system prompt leaks - jailbreak opportunity")
        analysis["risk_level"] = "critical"
    
    # Check infrastructure
    infra = intel.get('infrastructure', {})
    if 'vector_db' in infra or 'embeddings' in infra:
        analysis["key_findings"].append(f"🎯 Vector DB detected: {infra.get('vector_db')} - injection target")
    
    logger.info(f"📊 Risk Level: {analysis['risk_level'].upper()}")
    for finding in analysis['key_findings']:
        logger.info(f"   {finding}")
    
    return analysis


# ============================================================================
# SCAN EXECUTION
# ============================================================================

async def run_aggressive_scan(
    target_url: str,
    intel: Dict[str, Any],
    config: TestConfig,
    agent_type: str = "jailbreak"
) -> Dict[str, Any]:
    """
    Execute security scan with real intelligence.
    
    Args:
        target_url: Target endpoint URL
        intel: Parsed intelligence from recon
        config: Test configuration
        agent_type: Which agents to run (jailbreak|sql|auth|all)
    
    Returns:
        Dictionary with results from all executed agents
    """
    logger.info("🚀 Starting security scan...")
    logger.info(f"   Target: {target_url}")
    logger.info(f"   Mode: {config.SCAN_MODE}")
    logger.info(f"   Agent: {agent_type}")
    
    # Get scan settings
    settings = config.SCAN_CONFIG[config.SCAN_MODE]
    
    # Build scan input
    audit_id = f"swarm-test-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    scan_config = ScanConfig(
        approach=settings["approach"],
        max_probes=settings["max_probes"],
        max_generations=settings["max_generations"],
        allow_agent_override=True,  # Let agent optimize based on intelligence
        custom_probes=None,  # Let agent decide
    )
    
    scan_input = ScanInput(
        audit_id=audit_id,
        agent_type=agent_type,  # Will be overridden per agent
        target_url=target_url,
        infrastructure=intel.get('infrastructure', {}),
        detected_tools=intel.get('detected_tools', []),
        config=scan_config,
    )
    
    results = {}
    
    # Run selected agents
    agents_to_run = []
    if agent_type == "all":
        agents_to_run = ["jailbreak", "auth", "sql"]
    else:
        agents_to_run = [agent_type]
    
    logger.info(f"🎯 Will execute: {', '.join(agents_to_run)} agents")
    
    for agent in agents_to_run:
        logger.info(f"\n{'='*80}")
        logger.info(f"🤖 Running {agent.upper()} Agent")
        logger.info(f"{'='*80}")

        # Update agent type in scan input (use proper enum values)
        if agent == "jailbreak":
            scan_input.agent_type = AgentType.JAILBREAK.value
        elif agent == "sql":
            scan_input.agent_type = AgentType.SQL.value
        elif agent == "auth":
            scan_input.agent_type = AgentType.AUTH.value

        try:
            if agent == "jailbreak":
                result = await run_jailbreak_agent(scan_input)
            elif agent == "sql":
                result = await run_sql_agent(scan_input)
            elif agent == "auth":
                result = await run_auth_agent(scan_input)

            # Handle None result (shouldn't happen but defensive)
            if result is None:
                logger.error(f"❌ {agent.upper()} Agent returned None - check agent implementation")
                results[agent] = {
                    "success": False,
                    "error": "Agent returned None result",
                    "agent_type": f"agent_{agent}",
                }
                continue

            results[agent] = result

            # Log summary
            if result.get("success"):
                logger.info(f"✅ {agent.upper()} Agent completed successfully")

                # Log structured results
                vulnerabilities = result.get("vulnerabilities", [])
                probes_executed = result.get("probes_executed", [])
                generations_used = result.get("generations_used", 0)
                report_path = result.get("report_path")
                metadata = result.get("metadata", {})

                logger.info(f"   📊 Vulnerabilities found: {len(vulnerabilities)}")
                logger.info(f"   🔍 Probes executed: {len(probes_executed)}")
                if probes_executed:
                    logger.info(f"      Probes: {', '.join(probes_executed)}")
                logger.info(f"   🔄 Generations used: {generations_used}")

                # Show scan statistics from metadata
                if metadata:
                    pass_count = metadata.get("pass_count", 0)
                    fail_count = metadata.get("fail_count", 0)
                    error_count = metadata.get("error_count", 0)
                    total = metadata.get("total_results", pass_count + fail_count + error_count)

                    logger.info(f"   📈 Scan Statistics:")
                    logger.info(f"      Total Results: {total}")
                    logger.info(f"      Passed: {pass_count}")
                    logger.info(f"      Failed: {fail_count}")
                    logger.info(f"      Errors: {error_count}")

                    # HTTP stats
                    http_stats = metadata.get("http_stats", {})
                    if http_stats:
                        success_rate = http_stats.get("success_rate", 0) * 100
                        logger.info(f"      HTTP Success Rate: {success_rate:.1f}%")

                if report_path:
                    logger.info(f"   📄 Report: {report_path}")

                # Show vulnerability details
                if vulnerabilities:
                    logger.info("   🚨 Vulnerability Details:")
                    for vuln in vulnerabilities[:5]:  # Show first 5
                        if isinstance(vuln, dict):
                            category = vuln.get("category", "Unknown")
                            severity = vuln.get("severity", "unknown")
                            cluster_id = vuln.get("cluster_id", "")
                            logger.info(f"      • [{severity.upper()}] {category} ({cluster_id})")
                            # Show evidence if available
                            evidence = vuln.get("evidence", {})
                            if evidence:
                                payload = evidence.get("input_payload", "")[:80]
                                if payload:
                                    logger.info(f"        Payload: {payload}...")
                        else:
                            logger.info(f"      • {vuln}")
                    if len(vulnerabilities) > 5:
                        logger.info(f"      ... and {len(vulnerabilities) - 5} more vulnerabilities")
                else:
                    logger.info("   ✓ No vulnerabilities detected in this scan")
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ {agent.upper()} Agent failed: {error}")
                # Show any partial metadata
                metadata = result.get("metadata", {})
                if metadata:
                    logger.info(f"   Partial metadata: {metadata}")

        except Exception as e:
            logger.error(f"💥 {agent.upper()} Agent crashed: {e}", exc_info=True)
            results[agent] = {
                "success": False,
                "error": str(e),
                "agent_type": f"agent_{agent}",
            }

    return results


# ============================================================================
# RESULTS ANALYSIS
# ============================================================================

def analyze_results(results: Dict[str, Any], config: TestConfig) -> Dict[str, Any]:
    """
    Analyze scan results and generate comprehensive summary.
    """
    logger.info("\n" + "="*80)
    logger.info("📊 RESULTS ANALYSIS")
    logger.info("="*80)

    summary = {
        "agents_run": len(results),
        "agents_succeeded": 0,
        "agents_failed": 0,
        "total_vulnerabilities": 0,
        "total_probes_passed": 0,
        "total_probes_failed": 0,
        "total_probes_errored": 0,
        "critical_findings": [],
        "report_paths": [],
        "vulnerabilities_by_agent": {},
    }

    for agent_name, result in results.items():
        if result is None:
            summary["agents_failed"] += 1
            continue

        if result.get("success"):
            summary["agents_succeeded"] += 1

            # Extract vulnerabilities
            vulnerabilities = result.get("vulnerabilities", [])
            vuln_count = len(vulnerabilities)
            summary["total_vulnerabilities"] += vuln_count
            summary["vulnerabilities_by_agent"][agent_name] = vuln_count

            if vuln_count > 0:
                summary["critical_findings"].append(f"{agent_name}: {vuln_count} vulnerabilities found")

            # Extract scan statistics from metadata
            metadata = result.get("metadata", {})
            summary["total_probes_passed"] += metadata.get("pass_count", 0)
            summary["total_probes_failed"] += metadata.get("fail_count", 0)
            summary["total_probes_errored"] += metadata.get("error_count", 0)

            # Collect report paths
            report_path = result.get("report_path")
            if report_path:
                summary["report_paths"].append(report_path)
        else:
            summary["agents_failed"] += 1
            error = result.get("error", "Unknown error")
            summary["critical_findings"].append(f"{agent_name}: FAILED - {error[:50]}")

    # Log summary
    logger.info(f"✅ Successful: {summary['agents_succeeded']}/{summary['agents_run']}")
    logger.info(f"❌ Failed: {summary['agents_failed']}/{summary['agents_run']}")

    # Aggregate statistics
    total_probes = (summary["total_probes_passed"] +
                   summary["total_probes_failed"] +
                   summary["total_probes_errored"])

    if total_probes > 0:
        logger.info(f"\n📈 AGGREGATE STATISTICS:")
        logger.info(f"   Total Probe Results: {total_probes}")
        logger.info(f"   Passed: {summary['total_probes_passed']}")
        logger.info(f"   Failed: {summary['total_probes_failed']}")
        logger.info(f"   Errors: {summary['total_probes_errored']}")

    logger.info(f"\n🚨 VULNERABILITIES: {summary['total_vulnerabilities']} total")
    for agent, count in summary["vulnerabilities_by_agent"].items():
        if count > 0:
            logger.info(f"   • {agent}: {count}")

    if summary["critical_findings"]:
        logger.info("\n⚠️  FINDINGS:")
        for finding in summary["critical_findings"]:
            logger.info(f"   • {finding}")

    # Check for generated reports
    if config.OUTPUT_DIR.exists():
        # Look for reports matching the audit_id pattern
        reports = list(config.OUTPUT_DIR.glob("swarm-test-*.jsonl"))
        if not reports:
            # Also check for any recent jsonl files
            reports = sorted(config.OUTPUT_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]

        # Add any we found from results
        all_report_paths = set(summary["report_paths"])
        all_report_paths.update(str(r) for r in reports)
        summary["report_paths"] = list(all_report_paths)

        logger.info(f"\n📋 Reports generated: {len(summary['report_paths'])}")
        for report in summary["report_paths"]:
            logger.info(f"   • {report}")

    return summary


# ============================================================================
# MAIN TEST FUNCTION
# ============================================================================

async def main():
    """
    Main test execution flow.
    
    Steps:
    1. Load recon intelligence
    2. Analyze intelligence for attack vectors
    3. Configure aggressive scan parameters
    4. Execute selected agents
    5. Analyze and report results
    """
    config = TestConfig()
    
    logger.info("="*80)
    logger.info("🐝 SWARM SCANNER TEST")
    logger.info("="*80)
    logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Target: {config.TARGET_URL}")
    logger.info(f"Mode: {config.SCAN_MODE}")
    logger.info(f"Agent: {config.AGENT_TYPE}")
    logger.info("="*80 + "\n")
    
    try:
        # Step 1: Load intelligence
        logger.info("📖 STEP 1: Loading reconnaissance intelligence")
        intel = load_recon_intelligence(config.RECON_FILE)
        
        # Step 2: Analyze intelligence
        logger.info("\n🧠 STEP 2: Analyzing intelligence")
        analyze_intelligence(intel)  # Logs analysis results
        
        # Step 3: Execute scan
        logger.info("\n🚀 STEP 3: Executing security scan")
        results = await run_aggressive_scan(
            config.TARGET_URL,
            intel,
            config,
            config.AGENT_TYPE
        )
        
        # Step 4: Analyze results
        logger.info("\n📊 STEP 4: Analyzing results")
        summary = analyze_results(results, config)
        
        # Final summary
        logger.info("\n" + "="*80)
        logger.info("✅ TEST COMPLETED")
        logger.info("="*80)
        logger.info(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Agents executed: {summary['agents_run']}")
        logger.info(f"Success rate: {summary['agents_succeeded']}/{summary['agents_run']}")
        logger.info(f"Total vulnerabilities: {summary['total_vulnerabilities']}")

        # Show probe statistics
        total_probes = (summary.get('total_probes_passed', 0) +
                       summary.get('total_probes_failed', 0) +
                       summary.get('total_probes_errored', 0))
        if total_probes > 0:
            logger.info(f"Probe results: {total_probes} total "
                       f"({summary.get('total_probes_passed', 0)} pass, "
                       f"{summary.get('total_probes_failed', 0)} fail, "
                       f"{summary.get('total_probes_errored', 0)} error)")

        if summary["report_paths"]:
            logger.info("\n📋 Check reports at:")
            for path in summary["report_paths"]:
                logger.info(f"   {path}")

        # Return code based on results
        if summary['agents_failed'] > 0:
            logger.warning("Some agents failed - check logs for details")
            return 1
        return 0
    
    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        return 1
    except Exception as e:
        logger.error(f"💥 Test failed with exception: {e}", exc_info=True)
        return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Usage:
    ------
    
    # Default simple scan against localhost (quick mode, jailbreak agent only)
    python scripts/test_swarm_scanner.py
    
    # Modify TestConfig class above to customize:
    - TARGET_URL: Your target endpoint
    - SCAN_MODE: quick (default), standard, thorough
    - AGENT_TYPE: jailbreak (default), sql, auth, all
    
    # Understanding the parameters:
    - max_probes: Number of different attack types (probes) to run
    - max_generations: Number of attempts per probe prompt
    - Quick mode: 2 probes × 2 generations = fast test (~1-2 min)
    
    Environment Variables (optional):
    ---------------------------------
    TARGET_URL: Override target URL
    SCAN_MODE: Override scan mode
    AGENT_TYPE: Override agent selection
    
    Examples:
    ---------
    # Quick scan with jailbreak only (fastest - good for testing)
    TARGET_URL=http://myapp.com/chat SCAN_MODE=quick AGENT_TYPE=jailbreak python scripts/test_swarm_scanner.py
    
    # Standard scan with all agents
    SCAN_MODE=standard AGENT_TYPE=all python scripts/test_swarm_scanner.py
    
    # Thorough scan (comprehensive but slower)
    SCAN_MODE=thorough AGENT_TYPE=all python scripts/test_swarm_scanner.py
    """
    
    # Allow environment variable overrides
    import os
    if os.getenv("TARGET_URL"):
        TestConfig.TARGET_URL = os.getenv("TARGET_URL")
    if os.getenv("SCAN_MODE"):
        TestConfig.SCAN_MODE = os.getenv("SCAN_MODE")
    if os.getenv("AGENT_TYPE"):
        TestConfig.AGENT_TYPE = os.getenv("AGENT_TYPE")
    
    # Run test
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
