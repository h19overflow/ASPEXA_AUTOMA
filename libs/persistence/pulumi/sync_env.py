"""Sync Pulumi outputs to root .env file.

Usage:
    python -m libs.persistence.pulumi.sync_env

Or after pulumi up:
    cd libs/persistence/pulumi
    python sync_env.py
"""
import json
import subprocess
import sys
from pathlib import Path


def get_pulumi_outputs() -> dict:
    """Get outputs from current Pulumi stack."""
    result = subprocess.run(
        ["pulumi", "stack", "output", "--json"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )
    if result.returncode != 0:
        print(f"Error getting Pulumi outputs: {result.stderr}")
        sys.exit(1)
    return json.loads(result.stdout)


def update_env_file(outputs: dict, env_path: Path) -> None:
    """Update .env file with Pulumi outputs."""
    # Read existing .env content
    existing_lines = []
    if env_path.exists():
        existing_lines = env_path.read_text().splitlines()

    # Keys we manage
    managed_keys = {"S3_BUCKET_NAME", "AWS_REGION"}

    # Filter out managed keys from existing content
    filtered_lines = [
        line for line in existing_lines
        if not any(line.startswith(f"{key}=") for key in managed_keys)
    ]

    # Remove trailing empty lines
    while filtered_lines and not filtered_lines[-1].strip():
        filtered_lines.pop()

    # Add S3 section
    new_lines = filtered_lines.copy()
    if new_lines and new_lines[-1].strip():
        new_lines.append("")  # blank line before section

    new_lines.append("# S3 Persistence (managed by Pulumi)")
    new_lines.append(f"S3_BUCKET_NAME={outputs.get('s3_bucket_name', '')}")
    new_lines.append(f"AWS_REGION={outputs.get('aws_region', 'ap-southeast-2')}")
    new_lines.append("")  # trailing newline

    # Write back
    env_path.write_text("\n".join(new_lines))
    print(f"Updated {env_path}")


def main():
    # Find root .env
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent.parent.parent  # libs/persistence/pulumi -> root
    env_path = root_dir / ".env"

    print(f"Syncing Pulumi outputs to {env_path}")
    outputs = get_pulumi_outputs()
    print(f"Outputs: {json.dumps(outputs, indent=2)}")
    update_env_file(outputs, env_path)
    print("Done!")


if __name__ == "__main__":
    main()
