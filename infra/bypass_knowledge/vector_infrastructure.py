"""
S3 Vectors infrastructure for Bypass Knowledge VDB.

Creates vector bucket and indexes for episode storage and similarity search.
Uses AWS S3 Vectors - a dedicated vector storage service with:
- 2B vectors per index
- Sub-100ms query latency
- 90% cost savings vs traditional vector DBs
"""

import json

import pulumi
import pulumi_aws_native as aws_native
from pulumi import Config, Output


config = Config()
environment = config.get("environment") or "dev"
region = config.get("region") or "ap-southeast-2"


# === VECTOR BUCKET ===
vector_bucket = aws_native.s3vectors.VectorBucket(
    "bypass-knowledge-vectors",
    vector_bucket_name=f"aspexa-bypass-knowledge-{environment}",
    encryption=aws_native.s3vectors.VectorBucketEncryptionArgs(
        sse_type="AES256",  # SSE-S3 (default, no extra cost)
    ),
    tags=[
        aws_native.TagArgs(key="Project", value="Aspexa"),
        aws_native.TagArgs(key="Component", value="BypassKnowledge"),
        aws_native.TagArgs(key="Environment", value=environment),
    ],
)


# === EPISODE VECTOR INDEX ===
# Primary index for defense fingerprinting
episode_index = aws_native.s3vectors.Index(
    "bypass-episode-index",
    vector_bucket_name=vector_bucket.vector_bucket_name,
    index_name="episodes",
    dimension=3072,  # Gemini gemini-embedding-001 dimension
    distance_metric="COSINE",  # Cosine similarity for semantic search
    metadata_configuration=aws_native.s3vectors.IndexMetadataConfigurationArgs(
        # Non-filterable = stored but not indexed for filtering
        non_filterable_metadata_keys=["successful_prompt", "why_it_worked"],
    ),
    tags=[
        aws_native.TagArgs(key="IndexType", value="EpisodeFingerprint"),
    ],
)


# === IAM POLICY FOR APPLICATION ACCESS ===
vector_access_policy_document = Output.all(
    vector_bucket.arn,
    episode_index.arn
).apply(lambda args: json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VectorBucketAccess",
            "Effect": "Allow",
            "Action": [
                "s3vectors:GetVectorBucket",
                "s3vectors:ListIndexes",
            ],
            "Resource": args[0],
        },
        {
            "Sid": "VectorIndexOperations",
            "Effect": "Allow",
            "Action": [
                "s3vectors:GetIndex",
                "s3vectors:PutVectors",
                "s3vectors:GetVectors",
                "s3vectors:DeleteVectors",
                "s3vectors:QueryVectors",
                "s3vectors:ListVectors",
            ],
            "Resource": args[1],
        },
    ],
}))

vector_access_policy = aws_native.iam.ManagedPolicy(
    "bypass-knowledge-vector-access",
    managed_policy_name=f"bypass-knowledge-vector-access-{environment}",
    policy_document=vector_access_policy_document,
    description="Access policy for Bypass Knowledge VDB operations",
)


# === EXPORTS ===
pulumi.export("vector_bucket_name", vector_bucket.vector_bucket_name)
pulumi.export("vector_bucket_arn", vector_bucket.arn)
pulumi.export("episode_index_name", episode_index.index_name)
pulumi.export("episode_index_arn", episode_index.arn)
pulumi.export("vector_access_policy_arn", vector_access_policy.policy_arn)
