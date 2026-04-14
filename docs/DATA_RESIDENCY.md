# Data Residency Architecture

This document outlines Engram's multi-region infrastructure for meeting enterprise data residency requirements (GDPR Article 46, Japan APPI, Australia Privacy Act).

## Overview

Enterprise customers in the EU, Japan, and Australia have contractual or regulatory data residency requirements. Engram supports workspace-level data residency settings to ensure facts never leave the designated jurisdiction.

## Supported Regions

| Region Code | Geographic Area | Compliance |
|-------------|-----------------|------------|
| `us` | United States | Default |
| `eu` | European Union (Germany, Ireland) | GDPR Article 46 |
| `apac` | Asia-Pacific (Tokyo, Sydney) | Japan APPI, Australia Privacy Act |

## Implementation

### Workspace Configuration

Each workspace can specify its data residency preference:

```sql
ALTER TABLE workspaces ADD COLUMN data_residency TEXT NOT NULL DEFAULT 'us';
```

### Region Routing

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Determine  │
│  workspace  │
│  region      │
└──────┬──────┘
       │
       ▼
   ┌────┴────┐
   │         │
┌──┴──┐  ┌──┴──┐
│ EU  │  │ APAC│
│Pool │  │Pool │
└─────┘  └─────┘
```

### Database Pools

Each region has its own PostgreSQL pool:

- **US Pool**: `postgresql://us-engram-cluster.eu.rds.amazonaws.com`
- **EU Pool**: `postgresql://eu-engram-cluster.de.rds.amazonaws.com`
- **APAC Pool**: `postgresql://apac-engram-cluster.tokyo.rds.amazonaws.com`

### Invite Keys

Invite keys are region-specific:

```python
# Encode region in invite key
payload = {
    "engram_id": "workspace-123",
    "db_url": encrypt(db_url, workspace_key),
    "region": "eu"  # Must match workspace.data_residency
}
```

### Migration Path

Existing workspaces can migrate regions:

1. Export all facts from current region
2. Create new workspace in target region
3. Import facts to new workspace
4. Update DNS/invite keys to point to new region
5. Archive old workspace (soft delete)

## Privacy Implications

- Facts are encrypted client-side before storage
- Region selection determines which database cluster stores the encrypted data
- Embeddings are generated client-side using workspace key
- Even with encryption, data residency ensures encrypted blobs stay in-region

## Documentation Updates

- Update PRIVACY_ARCHITECTURE.md with region routing
- Update HIRING.md for enterprise sales (regional pricing)
- Update pricing page with "Data Residency" as an enterprise feature
