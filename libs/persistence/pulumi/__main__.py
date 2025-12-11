"""Pulumi IaC for Aspexa Persistence Layer.

Creates:
- S3 bucket for storing audit artifacts (heavy data)
- RDS PostgreSQL for campaign tracking (lightweight index)

Structure:
- S3: s3://{bucket}/campaigns/{audit_id}/{phase}/{filename}
- RDS: campaigns table with stage flags and S3 mappings

Usage:
    cd libs/persistence/pulumi
    pulumi stack init dev
    pulumi config set aws:region ap-southeast-2
    pulumi up
"""
import pulumi
import pulumi_aws as aws

from rds import create_rds_infrastructure, export_rds_outputs

# Configuration
config = pulumi.Config()
environment = pulumi.get_stack()  # dev, staging, prod

# S3 Bucket for Audit Lake
audit_bucket = aws.s3.BucketV2(
    "aspexa-audit-lake",
    bucket_prefix=f"aspexa-audit-{environment}-",
    tags={
        "Environment": environment,
        "Project": "Aspexa",
        "Purpose": "Audit Lake - Heavy artifact storage",
        "ManagedBy": "Pulumi",
    },
)

# Block all public access
public_access_block = aws.s3.BucketPublicAccessBlock(
    "audit-lake-public-access-block",
    bucket=audit_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True,
)

# Enable versioning for audit trail
versioning = aws.s3.BucketVersioningV2(
    "audit-lake-versioning",
    bucket=audit_bucket.id,
    versioning_configuration=aws.s3.BucketVersioningV2VersioningConfigurationArgs(
        status="Enabled",
    ),
)

# Server-side encryption
encryption = aws.s3.BucketServerSideEncryptionConfigurationV2(
    "audit-lake-encryption",
    bucket=audit_bucket.id,
    rules=[
        aws.s3.BucketServerSideEncryptionConfigurationV2RuleArgs(
            apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationV2RuleApplyServerSideEncryptionByDefaultArgs(
                sse_algorithm="AES256",
            ),
            bucket_key_enabled=True,
        )
    ],
)

# Lifecycle rules for cost optimization
lifecycle = aws.s3.BucketLifecycleConfigurationV2(
    "audit-lake-lifecycle",
    bucket=audit_bucket.id,
    rules=[
        aws.s3.BucketLifecycleConfigurationV2RuleArgs(
            id="archive-old-audits",
            status="Enabled",
            filter=aws.s3.BucketLifecycleConfigurationV2RuleFilterArgs(
                prefix="campaigns/",
            ),
            transitions=[
                # Move to Infrequent Access after 30 days
                aws.s3.BucketLifecycleConfigurationV2RuleTransitionArgs(
                    days=30,
                    storage_class="STANDARD_IA",
                ),
                # Move to Glacier after 90 days
                aws.s3.BucketLifecycleConfigurationV2RuleTransitionArgs(
                    days=90,
                    storage_class="GLACIER",
                ),
            ],
        ),
        aws.s3.BucketLifecycleConfigurationV2RuleArgs(
            id="delete-incomplete-uploads",
            status="Enabled",
            abort_incomplete_multipart_upload=aws.s3.BucketLifecycleConfigurationV2RuleAbortIncompleteMultipartUploadArgs(
                days_after_initiation=7,
            ),
        ),
    ],
)

# ============================================================
# RDS PostgreSQL for Campaign Tracking
# ============================================================
# Small instance for campaign metadata (stage flags, S3 mappings)
# Heavy scan data stays in S3, RDS is just the lightweight index

rds_enabled = config.get_bool("rds_enabled") or True

if rds_enabled:
    rds_resources = create_rds_infrastructure()
    export_rds_outputs(rds_resources)

# ============================================================
# Export S3 outputs
# ============================================================
pulumi.export("s3_bucket_name", audit_bucket.bucket)
pulumi.export("s3_bucket_arn", audit_bucket.arn)
pulumi.export("aws_region", aws.get_region().name)
