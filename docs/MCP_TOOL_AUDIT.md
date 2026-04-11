# MCP Tool Description Quality Audit

This document reviews MCP tool descriptions in [`src/engram/server.py`](../src/engram/server.py). It supports [issue #109](https://github.com/Agentscreator/Engram/issues/109) (tool description quality) and contributor onboarding.

**How to use this file:** Prefer jumping to the `async def engram_*` handler in `server.py` over relying on line numbers; lines drift as the file changes. The table below was last expanded in April 2026.

---

## Audit summary (all registered tools)

| Tool | Approx. line | Quality | Notes |
|------|----------------|---------|--------|
| `engram_status` | 102 | Excellent | Preconditions, when/not, common mistakes, examples |
| `engram_init` | 178 | Excellent | Same structural pattern; `awaiting_db` next_prompt lists free Postgres hosts |
| `engram_join` | 316 | Excellent | Single-key join model is clear |
| `engram_rename` | 413 | Good | Clear params; could add when/not guardrails like other tools |
| `engram_reset_invite_key` | 475 | Excellent | Security and teammate impact spelled out |
| `engram_commit` | 614 | Excellent | BAD/GOOD examples, secrets and rate limits |
| `engram_query` | 771 | Excellent | Conflict and verification warnings, query budget |
| `engram_conflicts` | 900 | Excellent | When to call, what not to do, sample return shape |
| `engram_resolve` | 958 | Excellent | Preconditions, workflows, mistake patterns |
| `engram_batch_commit` | 1019 | Excellent | Parity with single commit, per-fact outcomes, limits |
| `engram_promote` | 1093 | Excellent | fact_id via `include_ephemeral`, IMPORTANT + numbered workflow |
| `engram_feedback` | 1135 | Good | Clear enum-style feedback; could note relation to `engram_resolve` |
| `engram_timeline` | 1162 | Good | Scope/limit documented |
| `engram_agents` | 1188 | Good | Purpose clear; short |
| `engram_lineage` | ~1208 | Good | See source for parameters/returns |
| `engram_expiring` | ~1231 | Good | See source for parameters/returns |
| `engram_bulk_dismiss` | ~1260 | Good | See source for parameters/returns |
| `engram_export` | ~1293 | Good | See source for parameters/returns |
| `engram_create_webhook` | ~1346 | Good | See source for parameters/returns |
| `engram_create_rule` | ~1377 | Good | See source for parameters/returns |

---

## What changed since the original audit

Earlier versions of this file quoted shorter docstrings and marked `engram_promote`, `engram_conflicts`, and `engram_resolve` as needing work. The live `server.py` descriptions now largely follow a consistent pattern:

- **Precondition / when to call / what not to do / common mistake** blocks (where it helps)
- **IMPORTANT** callouts for safety and budgets
- **Explicit return shapes** or examples where agents parse JSON

The `awaiting_db` response for `engram_init` already points users at Neon, Supabase, and Railway; that complements the docstring without duplicating host names in every path.

---

## Follow-up ideas (non-blocking)

1. **Cross-links:** Optional "See also" lines (e.g. `engram_commit` ↔ `engram_query`, `engram_feedback` after `engram_conflicts` / `engram_resolve`).
2. **Secondary tools:** `engram_lineage` through `engram_create_rule` are fine but could get the same **when to call** treatment as core memory tools if usage grows.
3. **`engram_rename`:** Align with the richer guardrail style used on `engram_reset_invite_key` if product feedback says agents misuse it.

---

## General patterns (still accurate)

**Strengths across tools:**

- IMPORTANT guidelines are easy to scan
- Parameter docs often include examples or allowed values
- Return JSON is described or exemplified for agent consumers

**Ongoing discipline:**

- When you add or change an MCP tool, update this table (and any quoted snippets if you still use them elsewhere).
- Keep docstrings the source of truth; this file should summarize, not fork prose.

---

## Historical note

The first iteration of this audit (early 2026) included full docstring quotations and line-specific suggestions. Those went stale quickly as `server.py` grew. This revision tracks **all** `engram_*` tools and focuses on maintainability.
