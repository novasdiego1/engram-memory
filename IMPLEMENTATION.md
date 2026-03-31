# Engram Implementation Plan

This plan is grounded in the four papers in [`./papers/`](./papers/) — particularly Yu et al. (2026), which frames multi-agent memory consistency as a computer architecture problem, and the survey by Hu et al. (2026), which identifies shared memory governance as the field's open frontier. See [`LITERATURE.md`](./LITERATURE.md) for full citations.

---

## Architecture overview

Engram maps directly onto the three-layer hierarchy from Yu et al.:

```
┌─────────────────────────────────────┐
│           I/O Layer (MCP)           │  ← agents connect here
│   engram_query / engram_commit /    │
│         engram_conflicts            │
├─────────────────────────────────────┤
│           Cache Layer               │  ← hot embeddings, recent facts
│   in-memory vector index,           │
│   LRU fact cache, conflict cache    │
├─────────────────────────────────────┤
│           Memory Layer              │  ← durable store
│   SQLite (facts + conflicts),       │
│   embedding store, agent registry   │
└─────────────────────────────────────┘
```

The consistency model sits across all three layers: it governs what writes become visible and when, and surfaces semantic contradictions as structured artifacts rather than errors.

---

## Phase 1 — Foundation: data model and storage

**Goal:** Define the core schema that everything else builds on. Get this right before writing any server code.

### Fact schema

Informed by A-Mem's note structure and Yu et al.'s consistency model requirements:

```sql
CREATE TABLE facts (
    id          TEXT PRIMARY KEY,       -- uuid
    content     TEXT NOT NULL,          -- the raw fact as committed by the agent
    scope       TEXT NOT NULL,          -- e.g. "auth", "payments/webhooks", "infra"
    confidence  REAL NOT NULL,          -- 0.0–1.0, agent-reported
    agent_id    TEXT NOT NULL,          -- which agent committed this
    engineer    TEXT,                   -- human owner of the agent session
    keywords    TEXT,                   -- JSON array, LLM-generated
    tags        TEXT,                   -- JSON array, LLM-generated
    summary     TEXT,                   -- one-sentence LLM-generated description
    embedding   BLOB,                   -- float32 vector, serialized
    committed_at TEXT NOT NULL,         -- ISO8601 timestamp
    version     INTEGER NOT NULL DEFAULT 1,
    superseded_by TEXT                  -- id of newer fact, null if current
);
```

**Design decisions grounded in the literature:**
- `agent_id` + `engineer` implement the "agent memory access protocol" Yu et al. identify as missing — every write is traceable to its source
- `scope` is the unit of access granularity (document, chunk, key-value record) that Yu et al. flag as under-specified
- `keywords`, `tags`, `summary` follow A-Mem's note enrichment approach — facts carry their own semantic metadata, not just raw content
- `superseded_by` enables the versioning Yu et al. require for read-time conflict handling under iterative revisions
- `confidence` is already in the public API; it feeds conflict resolution priority

### Conflict schema

```sql
CREATE TABLE conflicts (
    id           TEXT PRIMARY KEY,
    fact_a_id    TEXT NOT NULL REFERENCES facts(id),
    fact_b_id    TEXT NOT NULL REFERENCES facts(id),
    detected_at  TEXT NOT NULL,
    explanation  TEXT,                  -- LLM-generated description of the contradiction
    severity     TEXT,                  -- "high" | "medium" | "low"
    status       TEXT NOT NULL DEFAULT 'open',  -- "open" | "resolved" | "dismissed"
    resolved_by  TEXT,                  -- agent_id that resolved
    resolved_at  TEXT,
    resolution   TEXT                   -- how it was resolved
);
```

### Agent registry

Implements the "permissions, scope, and access granularity" protocol Yu et al. identify as missing:

```sql
CREATE TABLE agents (
    agent_id     TEXT PRIMARY KEY,
    engineer     TEXT NOT NULL,
    label        TEXT,                  -- human-readable name, e.g. "alice-claude-code"
    registered_at TEXT NOT NULL,
    last_seen    TEXT
);
```

---

## Phase 2 — Core MCP server

**Goal:** A working MCP server exposing the three public tools. No conflict detection yet — just commit, store, and query.

### Stack

- **Python 3.11+** with `fastmcp` (or `mcp` SDK directly)
- **SQLite** via `aiosqlite` for async I/O
- **`sentence-transformers`** for local embeddings (default: `all-MiniLM-L6-v2`, ~80MB, no API key required)
- **`numpy`** for cosine similarity

### `engram_commit(fact, scope, confidence, agent_id?)`

1. Validate inputs
2. Generate embedding for `content`
3. Use LLM (or lightweight local model) to generate `keywords`, `tags`, `summary` — following A-Mem's note construction step
4. Write to `facts` table (append-only: never update or delete rows)
5. Trigger async conflict scan against existing facts in the same scope (Phase 3)
6. Return `{fact_id, committed_at}`

**Append-only is non-negotiable.** Yu et al. require that versioning and traceability be explicit. Every fact that has ever been committed must remain readable. Supersession is expressed via `superseded_by`, not deletion.

### `engram_query(topic, scope?, limit?)`

1. Generate embedding for `topic`
2. Retrieve all current (non-superseded) facts, optionally filtered by `scope`
3. Score each fact: `score = α * cosine_similarity + (1-α) * recency_decay`
   - `α = 0.7` (relevance-weighted, tunable)
   - Recency decay: `exp(-λ * days_since_commit)`, `λ = 0.05`
4. Return top-`limit` facts (default 10), ordered by score
5. Include `agent_id`, `confidence`, `committed_at` in each result — agents need provenance
6. **CRITICAL:** Join with `conflicts` table to flag `has_open_conflict: true` if the fact is currently disputed. (Mitigates the "Blind Read" failure mode where agents unknowingly act on contested information).

The relevance + recency hybrid is drawn from MIRIX's Active Retrieval insight: pure semantic similarity misses temporally important recent facts, but pure recency ignores relevance. The hybrid balances both.

### `engram_conflicts(scope?)`

Initially: return all rows from `conflicts` table with `status = 'open'`, optionally filtered by scope. Conflict detection itself is Phase 3.

### Server entrypoint

```
engram serve [--host HOST] [--port PORT] [--db PATH] [--embedding-model MODEL]
```

- Default: `localhost:7474`, `~/.engram/knowledge.db`
- MCP endpoint: `http://HOST:PORT/mcp`
- Health check: `http://HOST:PORT/health`

---

## Phase 3 — Conflict detection

**Goal:** Implement the core consistency mechanism. This is what no existing system does.

The literature distinguishes two types of consistency violation (Yu et al.):
1. **Read-time conflict** — a stale fact remains visible alongside a newer contradicting fact (versioning problem)
2. **Update-time conflict** — two agents write contradictory facts concurrently or sequentially (semantic contradiction problem)

Both are handled here.

### Detection pipeline

Triggered after every `engram_commit` (async, non-blocking to the committing agent):

**Step 1 — Candidate retrieval**

For the newly committed fact `f_new`:
- Retrieve the top-20 most embedding-similar facts
- Primary filter: exact `scope` match.
- Secondary fallback: if no matches in exact scope, retrieve globally with a higher similarity threshold (`> 0.85`) to catch scope fragmentation (e.g., "auth" vs "authentication").
- Filter to `cosine_similarity > 0.65` (below this threshold, facts are unlikely to be about the same subject)

**Step 2 — LLM contradiction check**

For each candidate pair `(f_new, f_candidate)`:

```
System: You are checking whether two facts about a codebase contradict each other.
        A contradiction means they cannot both be true at the same time.
        Respond with JSON: {"contradicts": true/false, "explanation": "...", "severity": "high/medium/low"}

Fact A (committed by {agent_a}, scope: {scope}, confidence: {conf_a}):
{content_a}

Fact B (committed by {agent_b}, scope: {scope}, confidence: {conf_b}):
{content_b}
```

Use a fast, cheap model (e.g., `claude-haiku-4-5`) — this runs on every commit.

**Step 3 — Write conflict record**

If `contradicts: true`, insert into `conflicts` table. Do not deduplicate against existing open conflicts (facts evolve; the same logical conflict may be reported by different commit pairs).

**Step 4 — Stale supersession check**

If `f_new` and `f_candidate` are from the same agent, same scope, and high similarity (> 0.85): mark `f_candidate.superseded_by = f_new.id`. This handles the read-time conflict case: an agent refining its own prior belief.
*Implementation Note:* To prevent race conditions from concurrent identical commits, this step must use an atomic SQLite `UPDATE ... WHERE superseded_by IS NULL` transaction.

### Conflict severity heuristic

| Condition | Severity |
|---|---|
| Contradicting facts from different engineers, both high-confidence (> 0.8) | high |
| One or both facts low-confidence (< 0.5) | low |
| Same engineer, different sessions | medium |
| Different scopes (detected despite filtering) | low |

---

## Phase 4 — Conflict resolution workflow

**Goal:** Make conflicts actionable, not just detectable. The survey (Hu et al., Section 7.5) calls for "learning-driven conflict resolution" and "agent-aware shared memory where R/W are conditioned on agent roles." This phase implements the deterministic baseline before any learning.

### New MCP tool: `engram_resolve(conflict_id, resolution, winning_fact_id?)`

```python
engram_resolve(
    conflict_id: str,
    resolution: str,          # human-readable explanation
    winning_fact_id: str | None  # if one fact wins, mark the other superseded
)
```

Behavior:
- Sets `conflicts.status = 'resolved'`, records `resolved_by`, `resolved_at`, `resolution`
- If `winning_fact_id` is provided: sets the losing fact's `superseded_by = winning_fact_id`
- If no winner: marks both facts with `confidence *= 0.5` (both remain, both downweighted)

### New MCP tool: `engram_dismiss(conflict_id, reason)`

For conflicts that are not actual contradictions (false positives from the LLM check):
- Sets `conflicts.status = 'dismissed'`
- Feeds into a false-positive training log for future prompt refinement

### Resolution strategies (informed by Yu et al.'s consistency model)

Three strategies agents or engineers can apply:

1. **Last-writer-wins** — the more recent fact supersedes the older. Appropriate when the newer fact is a correction (agent re-investigated and updated its belief).

2. **Higher-confidence-wins** — the fact with higher reported confidence supersedes. Appropriate when one agent had better information at commit time.

3. **Explicit merge** — a new fact is committed that synthesizes both, and both originals are marked superseded. Appropriate for complementary (not truly contradictory) facts that were incorrectly flagged.

---

## Phase 5 — Agent identity and access control

**Goal:** Implement the "agent memory access protocol" Yu et al. identify as missing — permissions, scope, and granularity.

### Agent registration

On first connection, an agent registers with:
```json
{
  "agent_id": "alice-claude-code-session-abc123",
  "engineer": "alice@company.com",
  "label": "Claude Code / alice"
}
```

`agent_id` is included in every `engram_commit` call. If omitted, the server generates one per session (unauthenticated mode).

### Scope-based access control

Scopes are hierarchical: `payments/webhooks` is a child of `payments`, which is a child of the root.

```sql
CREATE TABLE scope_permissions (
    agent_id   TEXT NOT NULL,
    scope      TEXT NOT NULL,           -- e.g. "payments" or "*"
    can_read   BOOLEAN NOT NULL DEFAULT TRUE,
    can_write  BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (agent_id, scope)
);
```

- Unauthenticated mode (default local): all agents can read/write all scopes
- Team mode: admins assign scope permissions per engineer or agent
- Read-only agents: useful for review workflows where an agent audits the knowledge base without writing

### Token auth

Simple bearer token per engineer. Tokens stored hashed in the DB. Passed in MCP connection headers.

```
engram serve --auth  # enables token verification
engram token create --engineer alice@company.com
```

---

## Phase 6 — Cross-team federation

**Goal:** Allow multiple Engram instances to share facts without centralizing everything. Yu et al. flag this as an open protocol gap (the "agent memory access protocol" problem at the inter-server level).

### Federation model

Each Engram instance is a **node**. Nodes can be configured as peers:

```yaml
# ~/.engram/config.yaml
federation:
  peers:
    - url: https://engram.teamb.internal
      token: <bearer>
      scopes: ["shared/*"]   # only sync facts in shared/ scope
      sync_interval: 60      # seconds
```

### Sync protocol

Pull-based (simpler than push, easier to reason about consistency):

1. Node A periodically fetches `/facts/since?timestamp=T&scope=shared/*` from Node B
2. Facts from remote nodes are written locally with their original `agent_id` and `committed_at`; `origin_node` field added
3. Conflicts are detected across nodes using the same pipeline as Phase 3
4. Resolution is local: each node tracks its own conflict table

This is a **eventually consistent** model — exactly the "eventual consistency paradigm" the survey (Hu et al.) describes as the practical direction for multi-agent memory.

---

## Phase 7 — Dashboard

**Goal:** Make the knowledge base inspectable by humans, not just agents.

### Views

- **Knowledge base** — all current (non-superseded) facts, filterable by scope, agent, engineer, date range
- **Conflict queue** — open conflicts grouped by scope, sortable by severity. Each conflict shows both facts side by side with the LLM-generated explanation.
- **Timeline** — fact commits over time, colored by agent/engineer. Makes it visible when different agents were active in the same scope.
- **Agent activity** — per-engineer breakdown of commits, conflict rate, resolution rate

### Stack

- **Backend:** FastAPI, same process as the MCP server (separate router)
- **Frontend:** minimal — server-rendered HTML with HTMX or a single-page Vue/React app
- **Endpoint:** `http://HOST:PORT/dashboard`

---

## Delivery sequence

| Phase | Deliverable | Unlocks |
|---|---|---|
| 1 | Schema + migrations | All subsequent phases |
| 2 | MCP server: commit + query | Usable by agents today |
| 3 | Conflict detection | Core differentiator |
| 4 | Resolution workflow | Conflicts become actionable |
| 5 | Auth + access control | Team deployment |
| 6 | Federation | Multi-team / org-wide |
| 7 | Dashboard | Human oversight |

Phases 1–3 are the minimum viable Engram. Everything after that extends the consistency model further along the axes the literature identifies: governance, access control, federation, human review.

---

## Key design constraints from the literature

**1. Append-only writes**
Yu et al. require explicit versioning for read-time conflict handling. Deletions would break the audit trail. Facts are superseded, not deleted.

**2. Semantic conflicts are structured artifacts, not errors**
The survey (Hu et al., §7.5) and Yu et al. both frame conflicts as something to detect, surface, and resolve — not prevent. `engram_conflicts()` returns a structured list, not an exception. This is intentional.

**3. Embeddings are first-class**
A-Mem demonstrates that embedding-based retrieval without semantic enrichment (keywords, tags, contextual description) misses connections. Every committed fact should carry LLM-generated metadata, not just raw content + vector.

**4. Agent identity is mandatory for consistency**
Yu et al.'s consistency model requires knowing *which agent* wrote what and *when*. The survey (§7.7) warns that memory systems without attribution enable privacy leaks and untraceable hallucinations. `agent_id` is required on every write path.

**5. Scope is the unit of isolation**
MIRIX's six memory types and A-Mem's box structure both point to the same principle: organizing memory by *topic domain* makes retrieval and conflict detection tractable. In Engram, `scope` plays this role. It should be hierarchical (path-like) and queryable at any level.

**6. Conflict detection must be async and non-blocking**
Committing a fact should return immediately. Detection runs in the background. Blocking commits on LLM inference would make the write path unusable in practice.

---

## Failure Modes & Architectural Mitigations

Based on an analysis of current multi-agent memory constraints, several critical failure modes have been explicitly addressed in this design:

**1. The "Blind Read" (Stale Facts / Knowledge Decay)**
- *Failure Mode:* Vector databases natively treat all stored records as equally valid. An agent might query a fact that is currently disputed by another agent, and unknowingly use it as ground truth.
- *Mitigation:* `engram_query` guarantees it surfaces `has_open_conflict` for every returned fact, forcing the reading agent to acknowledge the dispute, wait for resolution, or explicitly choose a side via `engram_resolve`.

**2. Async Race Conditions (Lost Updates)**
- *Failure Mode:* If two agents highly concurrently commit contradictory facts, the async conflict pipeline might interleave, causing incomplete supersession or dropping the conflict entirely. 
- *Mitigation:* SQLite's explicit atomic transactions are used during the `superseded_by` update step. The `conflicts` table acts as a dead-letter queue for contradictory facts that bypass initial synchronous checks.

**3. Scope Fragmentation (Context drift)**
- *Failure Mode:* An agent commits a fact to `payment/webhook`, and another to `payments/webhooks`. Exact string matching filters out the conflict, creating two bifurcated realties.
- *Mitigation:* Candidate retrieval (Phase 3, Step 1) supplements precise scope filtering with a global high-similarity fallback to explicitly catch overlapping semantic domains.

---

## What Engram is not building

The literature covers a large space. Several things are intentionally out of scope:

- **Parametric memory** (fine-tuning, LoRA adapters) — out of scope; Engram is a token-level system
- **Latent/KV-cache sharing** — the "cache sharing protocol" Yu et al. identify as missing; too deep in model internals
- **Episodic/procedural memory** (MIRIX's six types) — Engram stores *factual* memory about a shared codebase, not personal user history
- **RL-driven memory management** (Hu et al., §7.3) — the right long-term direction but requires evaluation infrastructure first
- **Multimodal memory** — text facts only in initial implementation; images and diagrams are a later extension
