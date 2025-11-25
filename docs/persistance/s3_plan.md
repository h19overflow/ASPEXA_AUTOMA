S3 Persistence Layer: The Audit Lake

1. Overview

The S3 Persistence Layer acts as the "Audit Lake" for Aspexa. Unlike the transactional database (PostgreSQL), this layer stores heavy, immutable artifacts:

Recon Blueprints (IF-02)

Garak Raw Logs (IF-04 source)

Attack Plans (IF-05)

Kill Chain Evidence (IF-07)

Structure: s3://{bucket_name}/campaigns/{audit_id}/{phase}/{filename}
Region: ap-southeast-2

2. Infrastructure (Pulumi)

We use Pulumi (Python) to define the infrastructure. This ensures the bucket is reproducible, secure, and integrated with our environment configuration.

A. Directory Setup

Located in: infrastructure/pulumi/

B. The Pulumi Program (__main__.py)

This script creates the private S3 bucket and exports the bucket name.

C. Deployment & .env Integration

Step 1: Initialize Stack

cd infrastructure/pulumi
pulumi stack init dev
pulumi config set aws:region ap-southeast-2


Step 2: Deploy

pulumi up


Review the plan and select 'yes'.

Step 3: Sync to .env
We use a command-line trick to append the Pulumi output directly to your root .env file.

# Run from root directory
echo "\n# S3 Persistence" >> .env
echo "S3_BUCKET_NAME=$(pulumi stack output s3_bucket_name -C infrastructure/pulumi)" >> .env
echo "AWS_REGION=ap-southeast-2" >> .env


3. The Shared Kernel Layer (libs/persistence/)

We have added a specialized adapter at libs/persistence/s3.py.

Configuration

Ensure your libs/config/settings.py or .env includes:

AWS_ACCESS_KEY_ID

AWS_SECRET_ACCESS_KEY

S3_BUCKET_NAME

AWS_REGION

Async by Design

Since boto3 is synchronous (blocking), the adapter wraps all I/O calls in asyncio.to_thread. This prevents S3 uploads from blocking your FastAPI or FastStream event loops.

4. Precise Entry Points

Import from libs.persistence.

save_artifact

Saves a dictionary as a JSON file in the structured path.

await save_artifact(
    audit_id="audit-123",
    phase="reconnaissance",  # or "scanning", "planning", "execution"
    filename="blueprint_v1.json",
    data={...} # Your Pydantic model .model_dump() or dict
)


load_artifact

Retrieves a JSON file.

data = await load_artifact(
    audit_id="audit-123",
    phase="reconnaissance",
    filename="blueprint_v1.json"
)


list_audit_files

Lists all files for a specific audit to populate the dashboard.

files = await list_audit_files(audit_id="audit-123")
# Returns: ["reconnaissance/blueprint_v1.json", "scanning/garak_log.jsonl"]


5. Phase Mapping Guidelines

Phase

Phase Directory Name

Artifact

Phase 1

01_recon

blueprint.json (IF-02)

Phase 2

02_scanning

scan_dispatch.json (IF-03), garak_raw.jsonl

Phase 3

03_planning

sniper_plan.json (IF-05)

Phase 4

04_execution

warrant.json (IF-06), kill_chain.json (IF-07)