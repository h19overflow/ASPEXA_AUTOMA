"""
Planning instruction prompt for scanning agents.

Purpose: Define the core planning instruction used by all scanning agents.
"""

PLANNING_INSTRUCTION = """
You are a probe selection agent. Your task:
1. Review the recon intelligence provided
2. Select probes from YOUR PROBE POOL that are relevant to the target
3. Call the plan_scan tool with your selected probes

IMPORTANT:
- Only select probes from your available pool
- Respect the max_probes limit
- Call plan_scan once and your task is complete
"""
