<div align="center">

# Engram

**Shared memory for your team's agents**

Persistent memory that survives across sessions and detects when agents contradict each other.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=flat-square)](./LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-8b5cf6?style=flat-square)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square)](https://python.org)

</div>

---



## What It Does

When one agent discovers something important — a hidden side effect, a failed approach, an undocumented constraint — it commits that fact. Every other agent on your team can query it instantly.

When two agents develop incompatible beliefs, Engram detects the contradiction and surfaces it for review.

**You own your data.** Engram connects to your PostgreSQL database. Your facts live in your database, not ours.

---

## Quick Start

```bash
pip install engram-team
engram install
```

Restart your editor, then ask your agent:
```
"Set up Engram for my team"
```

Your agent handles the rest. Works with Claude Code, Claude Desktop, Cursor, Windsurf, VS Code, and any MCP-compatible IDE.

**Security note:** Set your database URL in a `.env` file or environment variable — never paste it in chat.

---

## Setup Flow

### Creating a Workspace

> 🤖 **Agent**
>
> Do you have an Invite Key to join an existing workspace, or are you setting up a new one?

> 👤 **You**
>
> New

> 🤖 **Agent**
>
> Do you already have a PostgreSQL database for this project?
>
> - **Yes** → Great, Engram will create a separate `engram` schema inside your existing database. Your app tables are untouched.
> - **No** → No problem. You can get a free one in under a minute:
>   - [Neon](https://neon.tech) — Serverless Postgres
>   - [Supabase](https://supabase.com) — Open source Firebase alternative
>   - [Railway](https://railway.app) — Deploy in minutes
> - **Just testing locally?** → Skip the database entirely. Engram runs on SQLite by default — no setup needed.

> 👤 **You**
>
> I have one already

> 🤖 **Agent**
>
> Add your connection string to a `.env` file in your project root:
>
> ```
> ENGRAM_DB_URL='postgres://user:pass@host:5432/mydb'
> ```
>
> ⚠️ Don't paste your database URL in this chat — keep it in `.env` or an environment variable.
>
> Engram creates all its tables in a separate `engram` schema, so there's zero conflict with your existing tables. Once set, restart this chat and I'll detect it automatically.

*You set `ENGRAM_DB_URL` in `.env` and restart*

> 🤖 **Agent**
>
> Your team workspace is ready.
>
> Engram tables are in the `engram` schema — fully isolated from your app.
>
> Share this Invite Key with teammates:
> ```
> ek_live_abc123...
> ```
>
> That's all they need — the database connection is encrypted inside it.
>
> Should commits show who made them, or stay anonymous?

---

### Joining a Workspace

> 🤖 **Agent**
>
> Do you have an Invite Key to join an existing workspace, or are you setting up a new one?

> 👤 **You**
>
> Join — here's my key: `ek_live_abc123...`

> 🤖 **Agent**
>
> You're in. I'll query team memory before starting work on anything.

**That's it.** Teammates only need the Invite Key. No database URL, no Team ID, no configuration. Everything is encrypted inside the key.

---

## Do I Need My Own Database?

| Situation | What to do |
|---|---|
| **I have a PostgreSQL database for this project** | Point `ENGRAM_DB_URL` at it. Engram creates a separate `engram` schema — your app tables are untouched. |
| **I don't have a database yet** | Grab a free one from [Neon](https://neon.tech), [Supabase](https://supabase.com), or [Railway](https://railway.app). Takes under a minute. |
| **I'm just trying it out locally** | Do nothing. Engram defaults to SQLite (`~/.engram/knowledge.db`) — no database needed. |
| **A teammate invited me** | Just paste the Invite Key. The database connection is encrypted inside it — you don't need to set up anything. |

---

## How It Works

```
┌──────────────────────────────────────────┐
│            MCP Tools                     │
│  engram_commit  — Write a fact           │
│  engram_query   — Read team knowledge    │
│  engram_conflicts — See disagreements    │
│  engram_resolve — Settle conflicts       │
├──────────────────────────────────────────┤
│        Conflict Detection                │
│  Tier 0: Entity exact-match              │
│  Tier 1: NLI cross-encoder (local)       │
│  Tier 2: Numeric/temporal rules          │
│  Tier 3: LLM escalation (rare)           │
├──────────────────────────────────────────┤
│          Storage                         │
│  Your PostgreSQL database                │
│  (or SQLite for local mode)              │
└──────────────────────────────────────────┘
```

Team sharing works through the shared database — no HTTP server, no port forwarding, no firewall rules.

---

## Privacy & Security

**You own your data:**
- Connect to your own PostgreSQL database
- Use your existing app database with schema isolation
- Self-host if you want zero third-party involvement
- Database URL stored securely (mode 600) or in environment variables
- Invite keys encrypt credentials — teammates never see them

**Privacy settings** (asked once during setup):
- **Anonymous mode** — Strip engineer names from all commits
- **Anonymous agents** — Randomize agent IDs each session

---

## Tools

| Tool | Purpose |
|---|---|
| `engram_commit` | Persist a verified discovery |
| `engram_query` | Pull what your team's agents know |
| `engram_conflicts` | Surface contradictions |
| `engram_resolve` | Settle disagreements |
| `engram_promote` | Graduate ephemeral memory to durable |

---

## Conflict Detection

Runs asynchronously in the background:

| Tier | Method | Catches |
|---|---|---|
| 0 | Entity matching | "rate limit is 1000" vs "rate limit is 2000" |
| 1 | NLI cross-encoder | Semantic contradictions |
| 2 | Numeric rules | Different values for same entity |
| 3 | LLM escalation | Ambiguous cases (rare, optional) |

Commits return instantly. Detection completes in the background (~2-10s on CPU).

---

## Memory That Forgets on Purpose

Engram doesn't just accumulate — it actively forgets what doesn't earn its place.

> Persistent memory helps until it starts introducing assumptions you never explicitly designed.

- **Ephemeral memory** — Scratchpad facts auto-expire in 24h unless queried twice ("proved useful more than once")
- **Importance decay** — Unverified inferences expire after 30 days. Unverified observations expire after 90 days.
- **Protected facts** — Decisions, verified facts, and corroborated claims are never auto-retired.
- **Steeper recency curve** — A 90-day-old fact scores 0.001 in retrieval. Old context stops crowding out what matters now.

Grounded in the [FiFA/MaRS research](https://arxiv.org/abs/2512.12856) on forgetting-by-design for cognitive agents.

---

## Research Foundation

Engram is grounded in peer-reviewed research on multi-agent memory systems:

- **[Yu et al. (2026)](https://arxiv.org/abs/2603.10062)** — Multi-agent memory as a computer architecture problem
- **[Xu et al. (2025)](https://arxiv.org/abs/2502.12110)** — A-Mem's Zettelkasten structure for fact enrichment
- **[Rasmussen et al. (2025)](https://arxiv.org/abs/2501.13956)** — Graphiti's bitemporal modeling for temporal validity
- **[Hu et al. (2026)](https://arxiv.org/abs/2512.13564)** — Survey confirming shared memory as an open frontier
- **[Alqithami (2025)](https://arxiv.org/abs/2512.12856)** — FiFA: forgetting-by-design improves agent coherence

Full literature review: [`LITERATURE.md`](./LITERATURE.md)  
Implementation details: [`docs/IMPLEMENTATION.md`](./docs/IMPLEMENTATION.md)

---

## Contributing

PRs welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md).

---

## License

[Apache 2.0](./LICENSE)

---

<div align="center">
<sub>An engram is the physical trace a memory leaves in the brain — the actual unit of stored knowledge.</sub>
</div>
