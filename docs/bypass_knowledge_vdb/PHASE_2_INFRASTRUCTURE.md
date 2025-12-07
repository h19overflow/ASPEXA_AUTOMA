# Phase 2: Infrastructure

## Scope

Deploy AWS S3 Vectors infrastructure using Pulumi for vector storage and similarity search.

**Dependencies**: None (can run in parallel with Phase 1)

---

## S3 Vectors Overview

Amazon S3 Vectors is a dedicated AWS service for vector storage:

| Feature | Specification |
|---------|---------------|
| Max vectors per index | 2 billion |
| Max indexes per bucket | 10,000 |
| Warm query latency | ~100ms |
| Cold query latency | <1 second |
| Cost savings | 90% vs traditional vector DBs |

**Key Concepts:**
- **Vector Bucket**: New bucket type purpose-built for vectors
- **Vector Index**: Logical grouping within a bucket (defines dimension, distance metric)
- **Vectors**: Key-value pairs with embeddings + optional metadata

---

## Deliverables

### File: `infra/bypass_knowledge/vector_infrastructure.py`

```python
"""
S3 Vectors infrastructure for Bypass Knowledge VDB.

Creates vector bucket and indexes for episode storage and similarity search.
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
```

### File: `infra/bypass_knowledge/__init__.py`

```python
"""Bypass Knowledge VDB infrastructure module."""

from .vector_infrastructure import (
    vector_bucket,
    episode_index,
    vector_access_policy,
)

__all__ = [
    "vector_bucket",
    "episode_index",
    "vector_access_policy",
]
```

### File: `infra/bypass_knowledge/Pulumi.yaml`

```yaml
name: bypass-knowledge-infra
runtime:
  name: python
  options:
    virtualenv: ../../.venv
description: S3 Vectors infrastructure for Bypass Knowledge VDB
```

### File: `infra/bypass_knowledge/Pulumi.dev.yaml`

```yaml
config:
  aws:region: ap-southeast-2
  bypass-knowledge-infra:environment: dev
```

---

## S3 Vectors API Reference

### Boto3 Client

```python
import boto3

s3vectors = boto3.client('s3vectors', region_name='ap-southeast-2')
```

### Key Operations

| Operation | Description | Max Items |
|-----------|-------------|-----------|
| `create_vector_bucket` | Create vector bucket | - |
| `create_index` | Create index with dimension/metric | - |
| `put_vectors` | Insert vectors | 500/call |
| `query_vectors` | Similarity search | topK up to 10,000 |
| `get_vectors` | Retrieve by key | 500/call |
| `delete_vectors` | Remove vectors | 500/call |
| `list_vectors` | Paginated listing | - |

### Distance Metrics

| Metric | Use Case |
|--------|----------|
| `COSINE` | Semantic similarity (recommended) |
| `EUCLIDEAN` | Spatial distance |
| `DOT_PRODUCT` | When vectors are normalized |

---

## Regional Availability

S3 Vectors is available in 14 AWS Regions including **ap-southeast-2 (Sydney)**:
- US: East (Ohio, N. Virginia), West (Oregon)
- Europe: Frankfurt, Ireland, London, Paris, Stockholm
- Asia Pacific: Mumbai, Seoul, Singapore, **Sydney**, Tokyo
- Canada: Central

---

## Cost Model

| Component | Pricing |
|-----------|---------|
| Storage | Per GB-month |
| Writes | Per 1M put operations |
| Queries | Per 1M query operations |
| Data Transfer | Standard AWS rates |

**Estimate for 10K episodes**: <$50/month (90% cheaper than alternatives)

---

## Acceptance Criteria

- [ ] Vector bucket created successfully
- [ ] Episode index created with 3072 dimensions (Gemini embedding)
- [ ] COSINE distance metric configured
- [ ] IAM policy grants required s3vectors:* permissions
- [ ] Pulumi stack exports bucket/index ARNs
- [ ] Infrastructure deploys in <2 minutes

---

## Deployment

```bash
cd infra/bypass_knowledge
pulumi up --stack dev
```

---

## Sources

- [Amazon S3 Vectors Features](https://aws.amazon.com/s3/features/vectors/)
- [S3 Vectors GA Announcement](https://aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/)
- [Pulumi AWS Native S3 Vectors](https://www.pulumi.com/registry/packages/aws-native/api-docs/s3vectors/vectorbucket/)
- [Boto3 S3Vectors Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3vectors.html)
