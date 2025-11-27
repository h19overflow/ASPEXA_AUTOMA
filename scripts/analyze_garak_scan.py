"""
Analyze Garak scan structure from S3.
Usage: python -m scripts.analyze_garak_scan <scan_id>
Example: python -m scripts.analyze_garak_scan garak-soultanBreach-agent_jailbreak
"""
import asyncio
import json
import sys
from typing import Any, Dict

from libs.persistence import load_scan, ScanType


def print_structure(data: Any, indent: int = 0, max_depth: int = 4, path: str = "root") -> None:
    """Print nested structure with types and sample values."""
    prefix = "  " * indent

    if indent >= max_depth:
        print(f"{prefix}... (max depth reached)")
        return

    if isinstance(data, dict):
        print(f"{prefix}{path}: dict ({len(data)} keys)")
        for key, value in data.items():
            print_structure(value, indent + 1, max_depth, f"{path}.{key}")
    elif isinstance(data, list):
        print(f"{prefix}{path}: list ({len(data)} items)")
        if data:
            # Show first item structure
            print_structure(data[0], indent + 1, max_depth, f"{path}[0]")
            if len(data) > 1:
                print(f"{prefix}  ... and {len(data) - 1} more items")
    elif isinstance(data, str):
        sample = data[:100] + "..." if len(data) > 100 else data
        print(f"{prefix}{path}: str = \"{sample}\"")
    elif isinstance(data, (int, float)):
        print(f"{prefix}{path}: {type(data).__name__} = {data}")
    elif isinstance(data, bool):
        print(f"{prefix}{path}: bool = {data}")
    elif data is None:
        print(f"{prefix}{path}: null")
    else:
        print(f"{prefix}{path}: {type(data).__name__}")


async def analyze_scan(scan_id: str) -> None:
    """Load and analyze a Garak scan."""
    print(f"\n{'='*60}")
    print(f"Analyzing Garak Scan: {scan_id}")
    print(f"{'='*60}\n")

    try:
        # Load raw data (no validation)
        data = await load_scan(ScanType.GARAK, scan_id, validate=False)

        print("TOP-LEVEL KEYS:")
        print("-" * 40)
        for key in data.keys():
            value = data[key]
            type_info = type(value).__name__
            if isinstance(value, list):
                type_info = f"list[{len(value)}]"
            elif isinstance(value, dict):
                type_info = f"dict[{len(value)} keys]"
            elif isinstance(value, str) and len(value) > 50:
                type_info = f"str[{len(value)} chars]"
            print(f"  - {key}: {type_info}")

        print("\n\nFULL STRUCTURE (depth=4):")
        print("-" * 40)
        print_structure(data, max_depth=4)

        # Output full JSON for inspection
        print("\n\nFULL JSON OUTPUT:")
        print("-" * 40)
        print(json.dumps(data, indent=2, default=str))

    except Exception as e:
        print(f"ERROR: {e}")
        raise


async def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.analyze_garak_scan <scan_id>")
        print("Example: python -m scripts.analyze_garak_scan garak-soultanBreach-agent_jailbreak")
        sys.exit(1)

    scan_id = sys.argv[1]
    await analyze_scan(scan_id)


if __name__ == "__main__":
    asyncio.run(main())
