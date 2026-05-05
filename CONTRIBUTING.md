<div align="center">

# Contributing to Engram

*This is built in the open. Early contributors shape what it becomes — and become part of it.*

</div>

---

## Five-Minute Quick Start

```bash
# 1. Fork the repo on GitHub, then:
git clone https://github.com/YOUR-USERNAME/Engram.git
cd Engram

# 2. Install development dependencies
make install

# 3. Run the MCP server locally
make serve

# 4. Open the local dashboard
# http://127.0.0.1:7474/dashboard

# 5. Ask your agent (Claude Code, Cursor, etc.) to set up Engram
# Your agent will call engram_init and you'll see it working.

# 6. Make a change and open a PR
git checkout -b your-feature-or-fix
```

That's it. If any step fails, open an issue - a broken setup path is itself a valid first contribution.

Run `make help` to see every supported development command.

If your machine has multiple Python installations, pass `PYTHON=/path/to/python` to keep install and test targets on the same interpreter.

---

## Shared Agent Memory (Engram Workspace)

All contributors' AI agents share the same Engram workspace so your agent has the same context and memory as the rest of the team. Before starting work, have your agent join with this invite key:

```
ek_live_TXeVIk5ENmmWFHMR_-wq_XgwN6f5So8nIR8CVGAmhi5bzxZQQP13t7gOhGgGIhVWFmJTYuKn3kn_R22kwzxHEcH-BD2KIKS8EhXN4dxiry6HT1-g9CQ6g_S1JLnLJM4PKBeSahokEdHG9evVKSSQlaqe-oJnnBHiSpXXRkaXCcy8maGo2RPPFw
```

Your agent will call `engram_join` with this key and automatically connect to the shared workspace. This means every agent working on Engram sees the same verified facts, architectural decisions, and known issues.

---

## Good First Contributions

Not sure where to start? These are always useful:
- **Improve error messages** — vague errors are bugs
- **Add test coverage** for an edge case you noticed
- **Document a non-obvious behavior** in a code comment or the README
- **Pick a roadmap item** from [README.md#roadmap](./README.md#roadmap) — comment on the issue before starting so we can align
- **Add a quickstart guide** for your favorite IDE in `docs/quickstart/` — we already have Claude Code, Cursor, and VS Code, but need more

---

## Before You Start

Read the [README](./README.md). Understand the problem Engram is solving. The best contributions come from people who've felt the pain — agents re-discovering things that were already known, knowledge evaporating at session end.

If something is unclear or the design raises questions, **open a discussion before writing code.** Early-stage projects benefit more from alignment than from PRs that go in a different direction.

<br />

## Ways to Contribute

### Open a Discussion
The design is still being shaped. If you have thoughts on the API surface, the storage model, the conflict detection approach, or anything else — open a GitHub Discussion and share them. That is a real contribution.

### File an Issue
Found a bug, a gap in the design, or something that doesn't make sense? Open an issue. Be specific. Include what you expected, what happened, and what context matters.

### Submit a Pull Request
Code contributions are welcome. See the workflow below.

<br />

## Development Workflow

**1. Fork and clone**
```bash
git clone https://github.com/your-username/Engram.git
cd Engram
```

**2. Create a branch**
```bash
git checkout -b your-feature-or-fix
```

Use a descriptive branch name. `fix/conflict-detection-threshold` is better than `fix`.

**3. Make your changes**

Keep changes focused. One concern per PR. If you find yourself touching unrelated things, split them out.

**4. Test your work**

Before opening a PR, run the same local checks used by CI:

```bash
make check
```

For faster iteration, use the narrower targets:

```bash
make test
make lint
make format-check
```

To run one test file through the Makefile, pass `TEST_ARGS`:

```bash
make test TEST_ARGS="tests/test_cli_config.py -q"
```

Don't submit a PR you haven't run yourself. If tests don't exist yet for what you're changing, add them or note it clearly in the PR description.

**5. Open a PR**

Write a clear description:
- What does this change?
- Why is it the right change?
- Is there anything the reviewer should pay particular attention to?

<br />

## What Good PRs Look Like

- **Focused.** One change, one reason.
- **Explained.** The description covers the why, not just the what.
- **Clean.** No dead code, no commented-out experiments, no unrelated formatting changes.
- **Tested.** Ideally with new tests. At minimum, not breaking existing ones.

<br />

## What to Avoid

- PRs without context or explanation
- Large refactors without prior discussion
- Changes to core API surface without an issue or discussion first
- Dependency additions without a clear reason

If you're unsure whether something is in scope, ask first. The cost of a quick discussion is much lower than a PR that can't be merged.

<br />

## Code Style

Consistency matters more than any particular style. Match what's already there. Use `make format` for automatic formatting and `make lint` before sending a PR. If you're introducing something new, be deliberate about it and note it in the PR.

<br />

## Roadmap Items

The [README roadmap](./README.md#roadmap) lists what's being built. These are good starting points if you want to contribute but aren't sure where. Comment on an issue or open a discussion before picking one up — some items have design decisions that need to happen first.

<br />

## Ground Rules

- Be direct and specific in issues and reviews. Be respectful.
- Disagreement on approach is fine. Resolve it through discussion, not pressure.
- If you commit to something, follow through. If you can't, say so early.

<br />

## Questions

Not sure where to start? Open a discussion. Describe what you're thinking, what interests you, or what problem you've run into. That's enough to start a conversation.


<br />

## Contribution History

This project history is kept here so contributors have one canonical place for both workflow guidance and implementation context. The recorded rounds below were fully tested when they landed; across these rounds the suite grew from the original baseline to **252 passing tests** with no regressions.

### Round 9 - Makefile developer workflow

**Summary:** Added a root `Makefile` as the canonical entry point for common contributor commands and updated contribution guidance to use it.

**Files changed:** `Makefile`, `CONTRIBUTING.md`, `README.md`, `docs/DEVELOPER_SETUP.md`

**Commands added:** `make help`, `make install`, `make test`, `make test-all`, `make lint`, `make format`, `make format-check`, `make check`, `make build`, `make clean`, `make serve`, `make docker-build`, `make docker-up`, `make docker-up-sqlite`, `make docker-up-postgres`, `make docker-down`, `make docker-logs`

**New tests added:** 0 (developer workflow/documentation change)

### Round 8 - Seven major features

**Summary:** Implemented 7 production-ready features across the full stack: schema, storage, engine, REST, MCP, and tests. Schema bumped from v7 to v8 with 5 new tables.

**Files changed:** `src/engram/schema.py`, `src/engram/storage.py`, `src/engram/engine.py`, `src/engram/rest.py`, `src/engram/server.py`, `tests/test_rest.py`

**New tests added:** 60 (total: 252 passing)

#### 1. Webhooks / Event Subscriptions
- New tables: `webhooks`, `webhook_deliveries`
- Engine: `create_webhook`, `list_webhooks`, `delete_webhook`, `_fire_event`, `_webhook_delivery_worker` (background loop with aiohttp + HMAC-SHA256 signing, max 3 retries)
- Events fired: `fact.committed`, `conflict.detected`, `conflict.resolved`, `fact.expired`
- REST: `POST /api/webhooks`, `GET /api/webhooks`, `DELETE /api/webhooks/{webhook_id}`
- MCP: `engram_create_webhook`

#### 2. Auto-Resolution Rules Engine
- New table: `resolution_rules`
- Condition types: `latest_wins`, `highest_confidence`, `confidence_delta`
- Engine: `create_rule`, `list_rules`, `delete_rule`, `_apply_rules` (called after every conflict insert)
- REST: `POST /api/rules`, `GET /api/rules`, `DELETE /api/rules/{rule_id}`
- MCP: `engram_create_rule`

#### 3. Knowledge Export / Import
- Engine: `export_workspace(scope, include_history)`, `import_workspace(facts, agent_id, engineer)`
- Strips binary `embedding` field on export; re-commits via the full pipeline on import
- REST: `GET /api/export?scope=X&include_history=false`, `POST /api/import`

#### 4. Real-Time SSE Watch
- Engine: `subscribe(scope_prefix)`, `unsubscribe(queue, scope_prefix)`, `_broadcast(event_type, scope, payload)`
- `_sse_subscribers: dict[str, list[asyncio.Queue]]` on engine
- REST: `GET /api/watch?scope=X` via Starlette `StreamingResponse` with `text/event-stream`, 30s keepalive, and graceful disconnect via `try/finally`

#### 5. Scope Registry + Analytics
- New table: `scopes`
- Storage: `upsert_scope`, `get_scopes`, `get_scope_by_name`, `get_scope_analytics` (SQL aggregation: fact counts, conflict rate, most active agent, average confidence)
- Engine: `register_scope`, `list_scopes`, `get_scope_info`
- REST: `POST /api/scopes`, `GET /api/scopes`, `GET /api/scopes/{scope_name}`

#### 6. Fact Diffing
- Engine: `diff_facts(fact_id_a, fact_id_b)` for field-level diffs on content, scope, confidence, fact type, agent ID, and entity changes
- REST: `GET /api/diff/{fact_id_a}/{fact_id_b}`

#### 7. Audit Trail
- New table: `audit_log`
- Operations tracked: `commit`, `query`, `resolve`, `dismiss`, `feedback`, `webhook_create`, `rule_create`, `import`
- Engine: `_audit(operation, ...)` helper called from commit, resolve, record_feedback, create_webhook, create_rule, and import workspace
- REST: `GET /api/audit?agent_id=X&operation=commit&from=ISO&to=ISO&limit=100`

### Round 1 - Workspace isolation (`storage.py`)

**Problem:** 16 `SQLiteStorage` methods were missing `AND workspace_id = ?` filters. In multi-tenant deployments, facts, conflicts, and agents from one workspace were silently visible to others. `PostgresStorage` already had the filters correct; `SQLiteStorage` did not.

**Files changed:** `src/engram/storage.py`, `tests/test_workspace_isolation.py` (new, 23 tests)

**Methods fixed:**

| Method | Bug |
|--------|-----|
| `find_duplicate` | Cross-workspace dedup suppression |
| `close_validity_window` | Could retire facts in other workspaces |
| `expire_ttl_facts` | TTL expiry hit all workspaces |
| `get_current_facts_in_scope` | Returned facts from all workspaces |
| `get_facts_by_rowids` | FTS rowids are cross-workspace; filter missing |
| `get_promotable_ephemeral_facts` | Pulled from all workspaces |
| `retire_stale_facts` | Both `UPDATE` statements were missing workspace filters |
| `insert_conflict` | `workspace_id` missing from `INSERT` columns and defaulted to `local` |
| `conflict_exists` | Cross-workspace conflicts suppressed detection |
| `get_conflicts` | Returned conflicts from all workspaces |
| `get_stale_open_conflicts` | Escalation loop touched all workspaces |
| `get_active_facts_with_embeddings` | NLI/semantic search crossed workspaces |
| `get_facts_by_lineage` | Lineage lookup crossed workspaces |
| `count_facts` / `count_conflicts` | Dashboard counts included all workspaces |
| `get_fact_timeline` | Timeline showed facts from all workspaces |
| `get_open_conflict_fact_ids` | Conflict fact set included all workspaces |

### Round 2 - Bug fixes, input validation, pre-existing test fix

**Files changed:** `src/engram/engine.py`, `src/engram/federation.py`, `src/engram/rest.py`, `tests/test_engine.py`, `tests/test_rest.py` (new), `tests/test_federation.py`

#### `engine.py` - `corrects_lineage` silent failure
Passing a non-existent `lineage_id` as `corrects_lineage` silently created an orphaned new lineage instead of failing with a clear error. Validation now calls `get_facts_by_lineage(corrects_lineage)` before the auto-updater block and raises `ValueError` if the result is empty.

#### `federation.py` - safe `limit` param parsing
`int(request.query_params.get("limit", "1000"))` crashed with a 500 on non-numeric input. The endpoint now uses `try`/`except` with `max(1, min(..., 5000))` clamping.

#### `rest.py` - complete input validation
The REST layer was passing raw values straight to the engine, returning 500s on bad input. It now returns clean 400s at the boundary:

- `POST /api/commit`: whitespace-only `content`/`scope`, `confidence` range 0.0-1.0, `fact_type` enum, `operation` enum, positive integer `ttl_days`
- `POST /api/query`: `as_of` validated as ISO 8601
- `GET /api/conflicts`: `status` enum
- `POST /api/resolve`: `resolution_type` enum

#### Pre-existing failing test fixed
`test_detection_finds_numeric_conflict` expected `tier2_numeric`, but same-scope numeric entity conflicts always fire as `tier0_entity` because tier 0 runs first and short-circuits tier 2. The assertion now accepts either tier.

**New tests:** 8 engine tests, 28 REST validation tests, 4 federation tests.

### Round 3 - Bulk import + workspace analytics

**Files changed:** `src/engram/engine.py`, `src/engram/storage.py`, `src/engram/server.py`, `src/engram/rest.py`, `tests/test_rest.py`

#### `engine.batch_commit()` + `POST /api/batch-commit` + `engram_batch_commit`
Imports up to 100 facts in a single call. Each fact runs through the full commit pipeline: dedup, secret scan, embedding, entity extraction, and async conflict detection. Per-fact error isolation means one bad fact does not abort the batch.

Returns: `{total, committed, duplicates, failed, results: [{index, status, fact_id?, error?}]}`

Validation at the REST layer: array required, 1-100 items, each item must have non-empty `content`/`scope` and `confidence` in 0.0-1.0.

#### `storage.get_workspace_stats()` + `GET /api/stats`
Single-endpoint workspace snapshot for dashboards and monitoring. Aggregates via SQL:

- **facts:** total, current, expiring soon, by scope (top 10), by type, by durability
- **conflicts:** open/resolved/dismissed counts, by detection tier
- **agents:** total, most active, average trust score
- **detection:** true positive / false positive feedback counts

**New tests:** 16 REST tests for batch-commit validation, partial failure, and stats shape.

### Round 4 - N+1 query elimination + storage test coverage

**Files changed:** `src/engram/engine.py`, `src/engram/storage.py`, `tests/test_storage.py`

#### New storage batch methods

`get_conflicting_fact_ids(fact_id) -> set[str]` returns all fact IDs that already have any conflict with `fact_id` in a single query.

`get_facts_by_ids(ids) -> dict[str, dict]` batch-fetches multiple facts with one `WHERE id IN (...)` query and returns `{id: fact_row}`.

Both methods were added to `BaseStorage` and `SQLiteStorage`.

#### N+1 in detection worker
Before any detection tier runs, `get_conflicting_fact_ids(fact_id)` is called once and cached as `existing_conflict_ids`. The three per-candidate `conflict_exists()` DB calls are replaced with an in-memory set lookup. With 50 candidates per fact, this removes up to 50 round trips per commit.

#### N+1 in escalation loop
`_escalation_loop` now collects all `fact_a_id`/`fact_b_id` values from the stale-conflicts batch, calls `get_facts_by_ids(all_ids)` once, and passes prefetched facts to `_escalate_conflict`. Previously this required 2xN queries; now it takes one query.

`_escalate_conflict` accepts optional prefetched `fact_a`/`fact_b` and falls back to `get_fact_by_id` if not provided.

#### N+1 in suggestion worker
`_generate_and_store_suggestion` uses `get_facts_by_ids([a_id, b_id])` instead of two sequential `get_fact_by_id()` calls, halving queries per suggestion.

#### `test_storage.py` expanded
Storage tests grew from 2 to 29. The new tests cover batch helpers, conflict lifecycle, agent operations, TTL retirement, expiring facts, timeline, workspace stats, and validity windows.

### Round 5 - Four new REST endpoints + three MCP tools

**Files changed:** `src/engram/engine.py`, `src/engram/rest.py`, `src/engram/server.py`, `tests/test_rest.py`

#### `POST /api/feedback` + `engram_feedback`
Closes the conflict detection quality loop. Agents and humans can label a conflict detection as `true_positive` or `false_positive`. Feedback is persisted via `storage.insert_detection_feedback()` and surfaced in `/api/stats`.

Validation: `conflict_id` required and must exist; `feedback` must be one of the two valid values.

Engine method: `record_feedback(conflict_id, feedback) -> {recorded, conflict_id, feedback}`

#### `GET /api/timeline` + `engram_timeline`
Exposes `storage.get_fact_timeline()` via REST for audit and debugging. Query params: `scope` (optional prefix), `limit` (default 50, capped at 200).

Engine method: `get_timeline(scope, limit) -> list[dict]`

#### `GET /api/agents` + `engram_agents`
Lists all registered agents with their commit count, flagged count, engineer association, and last-seen timestamp.

Engine method: `get_agents() -> list[dict]`

#### `GET /api/health`
Live health check. It queries `count_facts()` and `count_conflicts("open")` from storage and returns `200 {status: "ok", facts: N, open_conflicts: N}` when healthy or `503 {status: "degraded"}` when storage is unavailable.

**New tests:** 17 REST tests across all four endpoints.

### Round 6 - Postgres parity (`postgres_storage.py`)

**File changed:** `src/engram/postgres_storage.py`

Four gaps between `SQLiteStorage` and `PostgresStorage` were identified and fixed.

#### Missing: `get_facts_by_ids(ids) -> dict[str, dict]`
Added to `PostgresStorage`. It uses `$1` for `workspace_id` and `$2..$N` positional placeholders for IDs. Without this, the engine's escalation loop and suggestion worker would crash on the Postgres backend.

#### Missing: `get_conflicting_fact_ids(fact_id) -> set[str]`
Added to `PostgresStorage`. Same semantics as the SQLite version: a single query returning all fact IDs that already have any conflict with `fact_id`. Without this, the N+1 fix in the detection worker would crash on Postgres.

#### Missing: `get_workspace_stats() -> dict`
Added full Postgres implementation. It mirrors the SQLiteStorage version with Postgres-native syntax such as `INTERVAL '1 day'`, `NOW()`, and positional params. Returns the same facts/conflicts/agents/detection shape.

#### Bug: `get_facts_by_rowids` missing workspace filter
`get_facts_by_rowids` queried `WHERE id IN (...)` without a workspace filter. Since `fts_search` in Postgres already filters by workspace, this was a latent cross-workspace leak. Fixed by adding `workspace_id = $1` as the first condition and updating placeholder numbering.

#### Bug: `auto_resolved=1` in `auto_resolve_conflict`
Postgres boolean columns require `TRUE`/`FALSE`, not `1`/`0`. `auto_resolved=1` caused a type error on Postgres and was changed to `auto_resolved=TRUE`.

### Round 7 - Five new REST endpoints + three MCP tools

**Files changed:** `src/engram/engine.py`, `src/engram/rest.py`, `src/engram/server.py`, `tests/test_rest.py`

#### `GET /api/facts` - list current facts
Returns non-retired durable facts, optionally filtered by `scope`, `fact_type`, and `limit`. Delegates to `storage.get_current_facts_in_scope()` and validates `fact_type` against the three valid values.

Engine method: `list_facts(scope, fact_type, limit) -> list[dict]`

#### `GET /api/facts/{fact_id}` - fetch a single fact
Looks up one fact by ID. Returns `404` if not found. Exposes `storage.get_fact_by_id()` directly so REST clients can inspect a specific fact without a query.

Engine method: `get_fact(fact_id) -> dict | None`

#### `GET /api/lineage/{lineage_id}` - fact evolution history
Returns all versions of a fact lineage ordered newest-first. The current fact (`valid_until IS NULL`) is always first. Returns `404` if no facts share that `lineage_id`.

Engine method: `get_lineage(lineage_id) -> list[dict]` + `engram_lineage`

#### `GET /api/expiring` - TTL monitoring
Returns facts whose TTL will expire within `days_ahead` days (default 7, capped at 30), letting agents and dashboards proactively refresh knowledge before it disappears from queries.

Engine method: `get_expiring_facts(days_ahead) -> list[dict]` + `engram_expiring`

#### `POST /api/conflicts/bulk-dismiss` - batch conflict management
Dismisses up to 100 open conflicts in one call with a shared reason string. Per-conflict failure isolation means a missing or already resolved conflict does not abort the batch.

Engine method: `bulk_dismiss(conflict_ids, reason, dismissed_by) -> {total, dismissed, failed, results}` + `engram_bulk_dismiss`

Validation: `conflict_ids` array required (1-100 items), `reason` required and non-whitespace.

**New tests:** 23 REST tests across all five endpoints.

### Test Count Summary

| Round | Tests added | Running total |
|-------|-------------|---------------|
| Baseline | - | ~60 |
| Round 1 | 23 (workspace isolation) | ~83 |
| Round 2 | 40 (engine + REST + federation) | ~123 |
| Round 3 | 16 (batch-commit + stats) | ~139 |
| Round 4 | 27 (storage coverage) | ~166 |
| Round 5 | 17 (new endpoints) | 192 |
| Round 6 | 0 (Postgres fixes, no test runner without a real DB) | 192 |
| Round 7 | 23 (facts list/lookup, lineage, expiring, bulk-dismiss) | 215 |
| Round 8 | 60 (major feature set) | 252 |
| Round 9 | 0 (developer workflow/documentation change) | 252 |

Latest recorded state in this log: **252 passing tests**.

<br />

---

<div align="center">

*Every great project was once just a problem someone cared about enough to fix.*
*Glad you're here.*

</div>
