# Client-Side Encryption Architecture

## Overview

This document describes the architectural design for implementing client-side encryption in Engram, where facts are encrypted before leaving the user's machine. This enables a true zero-knowledge backend where the server stores only ciphertext.

## Current Security Model

Today, Engram provides:
- **In transit:** TLS encryption
- **At rest:** PostgreSQL encryption (server-side)

**Limitation:** The server can read fact content in plaintext.

## Goal: Zero-Knowledge Backend

With client-side encryption:
- Only ciphertext is stored on the server
- The server handles metadata operations (search, conflict detection)
- The client decrypts facts locally
- Even server admins cannot read fact content

## Architecture

### Key Hierarchy

```
┌─────────────────────────────────────────────────────┐
│  Workspace Secret (user-provided or generated)       │
│  ├── Stored in: ~/.engram/workspace_secret          │
│  └── Never transmitted to server                     │
└─────────────────────────────────────────────────────┘
                         │
                         ▼ HKDF (HMAC-based Key Derivation)
┌─────────────────────────────────────────────────────┐
│  Derived Encryption Key (DEK)                       │
│  └── Used to encrypt/decrypt fact content           │
└─────────────────────────────────────────────────────┘
                         │
                         ▼ Each fact gets unique IV
┌─────────────────────────────────────────────────────┐
│  Encrypted Fact Content                             │
│  ├── Algorithm: AES-256-GCM                        │
│  ├── Format: base64(IV || ciphertext || auth_tag)  │
│  └── Stored in: server as ciphertext               │
└─────────────────────────────────────────────────────┘
```

### Key Derivation

```python
import hashlib
import hmac
import os

def derive_key(workspace_secret: bytes, salt: bytes) -> bytes:
    """Derive encryption key using HKDF-SHA256."""
    # HKDF (RFC 5869) with SHA-256
    prk = hmac.new(salt, workspace_secret, hashlib.sha256).digest()
    info = b"engram-fact-encryption"
    t = b""
    okm = b""
    n = (32 + 31) // 32  # 32 bytes of output
    for i in range(1, n + 1):
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        okm += t
    return okm[:32]
```

### Encrypted Fact Format

```python
@dataclass
class EncryptedFact:
    fact_id: str
    ciphertext: str  # base64(IV || ciphertext || auth_tag)
    iv: str  # base64(12 bytes)
    workspace_id: str  # for key lookup
    metadata: dict[str, Any]  # NOT encrypted:
                              # - agent_id (optional)
                              # - scope
                              # - confidence
                              # - provenance
                              # - timestamps
                              # - embeddings (for search)
```

### Search with Encrypted Content

Challenge: Search requires the server to match queries against encrypted content.

**Solution: Searchable Encryption**

1. Client generates a search token from the query
2. Search token is encrypted deterministically (same query → same token)
3. Server stores encrypted search tokens alongside ciphertext
4. Server can match queries without decrypting content

```python
def generate_search_token(query: str, workspace_secret: bytes) -> str:
    """Generate deterministic search token for encrypted search."""
    # Normalize query
    normalized = " ".join(query.lower().split())
    # Hash with workspace secret for determinism
    token = hashlib.sha256(workspace_secret + normalized.encode()).digest()
    return base64.b64encode(token).decode()
```

### Conflict Detection

Conflicts can be detected in two ways:
1. **Semantic:** Compare embeddings (already works - embeddings are not encrypted)
2. **Exact:** Compare encrypted content hashes

```python
def detect_conflicts(encrypted_facts: list[EncryptedFact]) -> list[Conflict]:
    """Detect conflicting facts from encrypted content."""
    content_hashes: dict[str, list[str]] = {}
    
    for fact in encrypted_facts:
        # Decrypt to get content hash
        content = decrypt_fact(fact, dek)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        if content_hash in content_hashes:
            # Potential conflict detected
            conflicts.append(Conflict(
                fact_ids=[content_hashes[content_hash], fact.fact_id],
                type="exact_contradiction"
            ))
        else:
            content_hashes[content_hash] = fact.fact_id
    
    return conflicts
```

## API Changes

### New MCP Tool: commit_encrypted

```python
@mcp.tool()
async def commit_encrypted(
    content: str,
    scope: str,
    confidence: float = 1.0,
    agent_id: str | None = None,
    provenance: str | None = None,
) -> dict[str, Any]:
    """Commit a fact with client-side encryption.
    
    The fact content is encrypted before being sent to the server.
    Only the workspace owner can decrypt fact content.
    
    Parameters:
    - content: The fact to store (will be encrypted client-side)
    - scope: Namespace for the fact (e.g., "auth", "payments")
    - confidence: How confident you are (0.0-1.0)
    - agent_id: Which agent is committing this fact
    - provenance: Where this fact came from (file:line, URL, etc.)
    
    Returns: {status, fact_id, encrypted_content}
    """
    # Encrypt locally
    ciphertext, iv = encrypt_fact(content, derived_key)
    
    # Generate deterministic search token
    search_token = generate_search_tokens(content, derived_key)
    
    # Send to server
    await storage.insert_fact(
        fact_id=generate_fact_id(),
        encrypted_content=ciphertext,
        iv=iv,
        search_token=search_token,
        metadata={scope, confidence, agent_id, provenance, timestamps}
    )
```

### New MCP Tool: query_encrypted

```python
@mcp.tool()
async def query_encrypted(
    topic: str,
    scope: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Query encrypted facts.
    
    Search tokens are generated from the query and matched
    against encrypted facts. Content is decrypted client-side.
    
    Returns: [{fact_id, content, scope, confidence, ...}]
    """
    # Generate search token
    search_token = generate_search_token(topic, derived_key)
    
    # Server returns matching encrypted facts
    encrypted_facts = await storage.search_facts(
        search_token=search_token,
        scope=scope,
        limit=limit
    )
    
    # Decrypt client-side
    return [decrypt_fact(f, derived_key) for f in encrypted_facts]
```

## Performance Considerations

### Embedding Computation

Embeddings are computed on the **query** (client), not stored per-fact:
- Pro: Smaller storage, no embedding leakage
- Con: More compute on client per query

### Batch Operations

```python
async def commit_batch_encrypted(
    facts: list[dict[str, Any]],
    batch_size: int = 50,
) -> list[dict[str, Any]]:
    """Commit multiple facts efficiently."""
    results = []
    for i in range(0, len(facts), batch_size):
        batch = facts[i:i + batch_size]
        # Parallel encryption
        encrypted_batch = await asyncio.gather(*[
            encrypt_fact(f["content"], derived_key)
            for f in batch
        ])
        # Parallel storage
        batch_results = await storage.insert_facts_batch([
            {**f, **enc} for f, enc in zip(batch, encrypted_batch)
        ])
        results.extend(batch_results)
    return results
```

## Key Management

### Workspace Secret Generation

```python
def generate_workspace_secret() -> str:
    """Generate a new workspace secret."""
    return secrets.token_urlsafe(32)  # 256 bits
```

### Secret Backup

Critical: Users must back up their workspace secret.

```python
# When creating a new workspace with encryption:
1. Generate workspace_secret
2. Display secret to user with backup instructions
3. User downloads/stores secret securely
4. Secret stored locally at ~/.engram/workspace_secret (mode 600)

# If secret is lost:
- No recovery possible (server cannot decrypt)
- Must create new workspace
- This is expected for zero-knowledge architecture
```

## Migration Path

### Phase 1: Documentation (This Document)
- Define architecture and API
- Get feedback from security team

### Phase 2: Prototype
- Implement encryption/decryption utilities
- Add commit_encrypted and query_encrypted tools
- Test with local storage

### Phase 3: Server Integration
- Add encrypted storage support
- Implement searchable encryption
- Add migration tools for existing workspaces

### Phase 4: Gradual Rollout
- New workspaces opt-in to encryption
- Existing workspaces can migrate
- Encryption status visible in workspace settings

## Security Considerations

### What IS Encrypted
- Fact content (the main body text)
- Search queries (in transit)

### What is NOT Encrypted (Metadata)
- Scope names
- Timestamps
- Confidence scores
- Agent IDs (if not anonymous)
- File paths in provenance
- Embeddings (for search)

**Note:** This means an adversary with server access can see:
- That user X committed facts in scope Y
- When facts were committed
- How many facts exist
- Search patterns (but not content)

### Threat Model

| Threat | Protected? |
|--------|------------|
| Server admin reading facts | ✅ Yes |
| Database breach | ✅ Yes |
| Network sniffing (TLS) | ✅ Yes |
| Metadata analysis | ❌ No |
| Traffic analysis | ❌ Partial |

## Related Issues

- #83: Zero-knowledge architecture transparency document
- #84: Client-side encryption: facts encrypted before leaving the machine (this document)
