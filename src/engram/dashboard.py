"""Phase 7 — Dashboard: server-rendered HTML with HTMX.

Co-located with the MCP server on the same process. Endpoint: /dashboard.
Landing page at / for new visitors.
Views: knowledge base, conflict queue, timeline, agent activity,
point-in-time, expiring facts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from engram.storage import Storage

logger = logging.getLogger("engram")


def build_dashboard_routes(storage: Storage) -> list[Route]:
    """Build all dashboard routes."""

    async def landing(request: Request) -> HTMLResponse:
        return HTMLResponse(_render_landing())

    async def index(request: Request) -> HTMLResponse:
        facts_count = await storage.count_facts(current_only=True)
        total_facts = await storage.count_facts(current_only=False)
        open_conflicts = await storage.count_conflicts("open")
        resolved_conflicts = await storage.count_conflicts("resolved")
        agents = await storage.get_agents()
        expiring = await storage.get_expiring_facts(days_ahead=7)
        return HTMLResponse(_render_index(
            facts_count=facts_count, total_facts=total_facts,
            open_conflicts=open_conflicts, resolved_conflicts=resolved_conflicts,
            agents=agents, expiring_count=len(expiring),
        ))

    async def knowledge_base(request: Request) -> HTMLResponse:
        scope = request.query_params.get("scope")
        fact_type = request.query_params.get("fact_type")
        as_of = request.query_params.get("as_of")
        facts = await storage.get_current_facts_in_scope(
            scope=scope, fact_type=fact_type, as_of=as_of, limit=100)
        conflict_ids = await storage.get_open_conflict_fact_ids()
        return HTMLResponse(_render_facts_table(facts, conflict_ids))

    async def conflict_queue(request: Request) -> HTMLResponse:
        scope = request.query_params.get("scope")
        status = request.query_params.get("status", "open")
        conflicts = await storage.get_conflicts(scope=scope, status=status)
        return HTMLResponse(_render_conflicts_table(conflicts))

    async def timeline(request: Request) -> HTMLResponse:
        scope = request.query_params.get("scope")
        facts = await storage.get_fact_timeline(scope=scope, limit=100)
        return HTMLResponse(_render_timeline(facts))

    async def agents_view(request: Request) -> HTMLResponse:
        agents = await storage.get_agents()
        feedback = await storage.get_detection_feedback_stats()
        return HTMLResponse(_render_agents(agents, feedback))

    async def expiring_view(request: Request) -> HTMLResponse:
        days = int(request.query_params.get("days", "7"))
        facts = await storage.get_expiring_facts(days_ahead=days)
        return HTMLResponse(_render_expiring(facts, days))

    return [
        Route("/", landing, methods=["GET"]),
        Route("/dashboard", index, methods=["GET"]),
        Route("/dashboard/facts", knowledge_base, methods=["GET"]),
        Route("/dashboard/conflicts", conflict_queue, methods=["GET"]),
        Route("/dashboard/timeline", timeline, methods=["GET"]),
        Route("/dashboard/agents", agents_view, methods=["GET"]),
        Route("/dashboard/expiring", expiring_view, methods=["GET"]),
    ]


# ── Landing page (mirrors api/index.py for local server) ────────────
# Imported by the local server; the Vercel deployment uses api/index.py directly.

def _render_landing() -> str:
    # Import the canonical version from api/index if available,
    # otherwise fall back to a minimal redirect.
    try:
        from api.index import _render_landing as _vercel_landing
        return _vercel_landing()
    except ImportError:
        pass

    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="0;url=/dashboard">
<title>Engram</title></head>
<body style="background:#f0f9f0;color:#2d3b2d;font-family:sans-serif;display:flex;
align-items:center;justify-content:center;min-height:100vh;">
<p>🌿 Redirecting to <a href="/dashboard" style="color:#16a34a;">dashboard</a>...</p>
</body></html>"""


# ── Dashboard HTML rendering ─────────────────────────────────────────

_HTMX_SCRIPT = '<script src="https://unpkg.com/htmx.org@2.0.4"></script>'

_DASH_STYLE = """
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f0f9f0; color: #2d3b2d; line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    position: relative; min-height: 100vh;
  }
  /* Decorative leaves */
  body::before {
    content: '🌿'; position: fixed; top: 1.2rem; right: 1.5rem;
    font-size: 1.6rem; opacity: 0.35; pointer-events: none; z-index: 0;
  }
  body::after {
    content: '🍃 🌱 🍀';
    position: fixed; bottom: 1rem; left: 1.5rem;
    font-size: 1.1rem; opacity: 0.25; pointer-events: none; z-index: 0;
    letter-spacing: 0.4rem;
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 1.5rem; position: relative; z-index: 1; }

  .dash-header { display: flex; align-items: center; justify-content: space-between;
                 margin-bottom: 1.5rem; flex-wrap: wrap; gap: 0.75rem; }
  .dash-title { display: flex; align-items: center; gap: 0.5rem; }
  .dash-title h1 { font-size: 1.25rem; font-weight: 600; color: #1a3a1a; }
  .dash-title h1::before { content: '🌿 '; }
  .dash-title .dot { width: 8px; height: 8px; border-radius: 50%; background: #4ade80;
                     box-shadow: 0 0 8px rgba(74,222,128,0.5); }
  .back-link { color: #5a8a5a; text-decoration: none; font-size: 0.8rem;
               transition: color 0.15s; }
  .back-link:hover { color: #2d6a2d; }

  nav { display: flex; gap: 0.25rem; margin-bottom: 1.5rem;
        background: rgba(74,222,128,0.08); border-radius: 10px;
        padding: 0.25rem; width: fit-content; flex-wrap: wrap; }
  nav a { color: #5a8a5a; text-decoration: none; padding: 0.45rem 0.9rem;
          border-radius: 8px; font-size: 0.8rem; font-weight: 500;
          transition: all 0.15s; }
  nav a:hover { color: #1a5a1a; background: rgba(74,222,128,0.1); }
  nav a.active { background: rgba(74,222,128,0.18); color: #15803d; }

  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
           gap: 0.75rem; margin-bottom: 1.5rem; }
  .stat { background: #fff; border: 1px solid #c6e9c6;
          border-radius: 12px; padding: 1.25rem;
          box-shadow: 0 1px 3px rgba(0,80,0,0.04); }
  .stat-value { font-size: 2rem; font-weight: 700; color: #1a3a1a;
                letter-spacing: -0.02em; }
  .stat-label { font-size: 0.8rem; color: #5a8a5a; margin-top: 0.15rem; }
  .stat-accent .stat-value { color: #16a34a; }
  .stat-warn .stat-value { color: #d97706; }
  .stat-ok .stat-value { color: #22c55e; }

  h2 { font-size: 1rem; font-weight: 600; color: #1a3a1a; margin-bottom: 0.75rem; }
  h2::before { content: '🍃 '; font-size: 0.9rem; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 0.6rem 0.75rem; font-size: 0.7rem; font-weight: 500;
       color: #5a8a5a; text-transform: uppercase; letter-spacing: 0.05em;
       border-bottom: 1px solid #c6e9c6; background: #f7fdf7; }
  td { padding: 0.6rem 0.75rem; font-size: 0.8rem; color: #3d5c3d;
       border-bottom: 1px solid #e2f2e2; }
  tr:hover td { background: #edf7ed; }
  .content-cell { max-width: 360px; overflow: hidden; text-overflow: ellipsis;
                  white-space: nowrap; }

  .badge { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 100px;
           font-size: 0.7rem; font-weight: 500; }
  .badge-high { background: #fee2e2; color: #dc2626; }
  .badge-medium { background: #fef3c7; color: #d97706; }
  .badge-low { background: #dcfce7; color: #16a34a; }
  .badge-open { background: #fee2e2; color: #dc2626; }
  .badge-resolved { background: #dcfce7; color: #16a34a; }
  .badge-dismissed { background: #f0f9f0; color: #5a8a5a; }
  .badge-verified { background: #dcfce7; color: #16a34a; }
  .badge-unverified { background: #fef3c7; color: #d97706; }

  .timeline-bar { height: 6px; border-radius: 3px; background: #4ade80; min-width: 4px; }
  .timeline-bar.superseded { background: #c6e9c6; }

  .filter-bar { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem;
                flex-wrap: wrap; }
  input, select { background: #fff; color: #2d3b2d;
                  border: 1px solid #c6e9c6; border-radius: 8px;
                  padding: 0.45rem 0.75rem; font-size: 0.8rem;
                  font-family: 'DM Sans', sans-serif; transition: border-color 0.15s; }
  input:focus, select:focus { outline: none; border-color: #4ade80;
                              box-shadow: 0 0 0 3px rgba(74,222,128,0.15); }
  input::placeholder { color: #9ab89a; }
  button[type="submit"] { background: #dcfce7; color: #15803d;
                          border: 1px solid #86efac; border-radius: 8px;
                          padding: 0.45rem 1rem; font-size: 0.8rem; cursor: pointer;
                          font-family: 'DM Sans', sans-serif; font-weight: 500;
                          transition: all 0.15s; }
  button[type="submit"]:hover { background: #bbf7d0; }

  .table-wrap { background: #fff; border: 1px solid #c6e9c6;
                border-radius: 12px; overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,80,0,0.04); }
  .table-wrap table { margin: 0; }
  .count-note { color: #5a8a5a; font-size: 0.75rem; margin-top: 0.75rem; }

  @media (max-width: 640px) {
    .stats { grid-template-columns: repeat(2, 1fr); }
    .content-cell { max-width: 180px; }
  }
</style>
"""


def _dash_layout(title: str, body: str, active: str = "") -> str:
    def _nav_cls(name: str) -> str:
        return ' class="active"' if name == active else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Engram Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  {_HTMX_SCRIPT}
  {_DASH_STYLE}
</head>
<body>
  <div class="container">
    <div class="dash-header">
      <div class="dash-title">
        <div class="dot"></div>
        <h1>Engram Dashboard</h1>
      </div>
      <a href="/" class="back-link">&larr; Back to home</a>
    </div>
    <nav>
      <a href="/dashboard"{_nav_cls("overview")}>Overview</a>
      <a href="/dashboard/facts"{_nav_cls("facts")}>Knowledge Base</a>
      <a href="/dashboard/conflicts"{_nav_cls("conflicts")}>Conflicts</a>
      <a href="/dashboard/timeline"{_nav_cls("timeline")}>Timeline</a>
      <a href="/dashboard/agents"{_nav_cls("agents")}>Agents</a>
      <a href="/dashboard/expiring"{_nav_cls("expiring")}>Expiring</a>
    </nav>
    {body}
  </div>
</body>
</html>"""


def _render_index(
    facts_count: int, total_facts: int, open_conflicts: int,
    resolved_conflicts: int, agents: list[dict], expiring_count: int,
) -> str:
    body = f"""
    <div class="stats">
      <div class="stat stat-accent">
        <div class="stat-value">{facts_count}</div>
        <div class="stat-label">Current Facts</div>
      </div>
      <div class="stat">
        <div class="stat-value">{total_facts}</div>
        <div class="stat-label">Total Facts</div>
      </div>
      <div class="stat stat-warn">
        <div class="stat-value">{open_conflicts}</div>
        <div class="stat-label">Open Conflicts</div>
      </div>
      <div class="stat stat-ok">
        <div class="stat-value">{resolved_conflicts}</div>
        <div class="stat-label">Resolved</div>
      </div>
      <div class="stat">
        <div class="stat-value">{len(agents)}</div>
        <div class="stat-label">Agents</div>
      </div>
      <div class="stat">
        <div class="stat-value">{expiring_count}</div>
        <div class="stat-label">Expiring (7d)</div>
      </div>
    </div>
    <h2>Recent Agents</h2>
    <div class="table-wrap">
    <table>
      <tr><th>Agent</th><th>Engineer</th><th>Commits</th><th>Flagged</th><th>Last Seen</th></tr>
      {"".join(_agent_row(a) for a in agents[:10])}
    </table>
    </div>"""
    return _dash_layout("Overview", body, active="overview")


def _agent_row(a: dict) -> str:
    total = a.get("total_commits", 0)
    flagged = a.get("flagged_commits", 0)
    ratio = f"{flagged}/{total}" if total else "0/0"
    return (
        f"<tr><td>{_esc(a['agent_id'])}</td><td>{_esc(a.get('engineer', ''))}</td>"
        f"<td>{total}</td><td>{ratio}</td>"
        f"<td>{_esc(a.get('last_seen', '') or '')}</td></tr>"
    )


def _render_facts_table(facts: list[dict], conflict_ids: set[str]) -> str:
    rows = []
    for f in facts:
        has_conflict = f["id"] in conflict_ids
        verified = f.get("provenance") is not None
        conflict_badge = '<span class="badge badge-open">conflict</span>' if has_conflict else ""
        ver_badge = (
            '<span class="badge badge-verified">verified</span>'
            if verified
            else '<span class="badge badge-unverified">unverified</span>'
        )
        rows.append(
            f"<tr><td class='content-cell'>{_esc(f['content'])}</td>"
            f"<td>{_esc(f['scope'])}</td><td>{f['confidence']:.2f}</td>"
            f"<td>{_esc(f['fact_type'])}</td><td>{_esc(f['agent_id'])}</td>"
            f"<td>{conflict_badge} {ver_badge}</td>"
            f"<td>{_esc(f.get('committed_at', '')[:19])}</td></tr>"
        )
    body = f"""
    <h2>Knowledge Base</h2>
    <div class="filter-bar">
      <form method="get" action="/dashboard/facts" style="display:flex;gap:0.5rem;flex-wrap:wrap;">
        <input name="scope" placeholder="Scope filter" value="">
        <select name="fact_type">
          <option value="">All types</option>
          <option value="observation">observation</option>
          <option value="inference">inference</option>
          <option value="decision">decision</option>
        </select>
        <input name="as_of" placeholder="as_of (ISO 8601)" value="">
        <button type="submit">Filter</button>
      </form>
    </div>
    <div class="table-wrap">
    <table>
      <tr><th>Content</th><th>Scope</th><th>Confidence</th><th>Type</th>
          <th>Agent</th><th>Status</th><th>Committed</th></tr>
      {"".join(rows)}
    </table>
    </div>
    <p class="count-note">{len(facts)} fact(s)</p>"""
    return _dash_layout("Knowledge Base", body, active="facts")


def _render_conflicts_table(conflicts: list[dict]) -> str:
    rows = []
    for c in conflicts:
        sev = c.get("severity", "low")
        status = c.get("status", "open")
        sev_badge = f'<span class="badge badge-{sev}">{sev}</span>'
        status_badge = f'<span class="badge badge-{status}">{status}</span>'
        rows.append(
            f"<tr><td>{_esc(c['id'][:12])}...</td>"
            f"<td class='content-cell'>{_esc(c.get('fact_a_content', ''))}</td>"
            f"<td class='content-cell'>{_esc(c.get('fact_b_content', ''))}</td>"
            f"<td>{_esc(c.get('detection_tier', ''))}</td>"
            f"<td>{sev_badge}</td><td>{status_badge}</td>"
            f"<td>{_esc(c.get('detected_at', '')[:19])}</td></tr>"
        )
    body = f"""
    <h2>Conflict Queue</h2>
    <div class="filter-bar">
      <form method="get" action="/dashboard/conflicts" style="display:flex;gap:0.5rem;">
        <input name="scope" placeholder="Scope filter" value="">
        <select name="status">
          <option value="open">Open</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
          <option value="all">All</option>
        </select>
        <button type="submit">Filter</button>
      </form>
    </div>
    <div class="table-wrap">
    <table>
      <tr><th>ID</th><th>Fact A</th><th>Fact B</th><th>Tier</th>
          <th>Severity</th><th>Status</th><th>Detected</th></tr>
      {"".join(rows)}
    </table>
    </div>
    <p class="count-note">{len(conflicts)} conflict(s)</p>"""
    return _dash_layout("Conflicts", body, active="conflicts")


def _render_timeline(facts: list[dict]) -> str:
    rows = []
    for f in facts:
        is_superseded = f.get("valid_until") is not None
        bar_class = "timeline-bar superseded" if is_superseded else "timeline-bar"
        valid_range = f.get("valid_from", "")[:10]
        if is_superseded:
            valid_range += f" → {f['valid_until'][:10]}"
        else:
            valid_range += " → current"
        rows.append(
            f"<tr><td class='content-cell'>{_esc(f['content'][:80])}</td>"
            f"<td>{_esc(f['scope'])}</td><td>{_esc(f['agent_id'])}</td>"
            f"<td>{valid_range}</td>"
            f"<td><div class='{bar_class}' style='width:60px;'></div></td></tr>"
        )
    body = f"""
    <h2>Timeline</h2>
    <div class="filter-bar">
      <form method="get" action="/dashboard/timeline" style="display:flex;gap:0.5rem;">
        <input name="scope" placeholder="Scope filter" value="">
        <button type="submit">Filter</button>
      </form>
    </div>
    <div class="table-wrap">
    <table>
      <tr><th>Content</th><th>Scope</th><th>Agent</th><th>Validity</th><th>Window</th></tr>
      {"".join(rows)}
    </table>
    </div>"""
    return _dash_layout("Timeline", body, active="timeline")


def _render_agents(agents: list[dict], feedback: dict[str, int]) -> str:
    rows = []
    for a in agents:
        total = a.get("total_commits", 0)
        flagged = a.get("flagged_commits", 0)
        reliability = f"{(1 - flagged / total) * 100:.0f}%" if total > 0 else "N/A"
        rows.append(
            f"<tr><td>{_esc(a['agent_id'])}</td>"
            f"<td>{_esc(a.get('engineer', ''))}</td>"
            f"<td>{total}</td><td>{flagged}</td><td>{reliability}</td>"
            f"<td>{_esc(a.get('registered_at', '')[:19])}</td>"
            f"<td>{_esc(a.get('last_seen', '') or '')[:19]}</td></tr>"
        )
    tp = feedback.get("true_positive", 0)
    fp = feedback.get("false_positive", 0)
    body = f"""
    <h2>Agent Activity</h2>
    <div class="stats">
      <div class="stat">
        <div class="stat-value">{len(agents)}</div>
        <div class="stat-label">Total Agents</div>
      </div>
      <div class="stat stat-ok">
        <div class="stat-value">{tp}</div>
        <div class="stat-label">True Positives</div>
      </div>
      <div class="stat stat-warn">
        <div class="stat-value">{fp}</div>
        <div class="stat-label">False Positives</div>
      </div>
    </div>
    <div class="table-wrap">
    <table>
      <tr><th>Agent</th><th>Engineer</th><th>Commits</th><th>Flagged</th>
          <th>Reliability</th><th>Registered</th><th>Last Seen</th></tr>
      {"".join(rows)}
    </table>
    </div>"""
    return _dash_layout("Agents", body, active="agents")


def _render_expiring(facts: list[dict], days: int) -> str:
    rows = []
    for f in facts:
        rows.append(
            f"<tr><td class='content-cell'>{_esc(f['content'])}</td>"
            f"<td>{_esc(f['scope'])}</td><td>{f.get('ttl_days', '')}</td>"
            f"<td>{_esc(f.get('valid_until', '')[:19])}</td>"
            f"<td>{_esc(f['agent_id'])}</td></tr>"
        )
    body = f"""
    <h2>Expiring Facts (next {days} days)</h2>
    <div class="filter-bar">
      <form method="get" action="/dashboard/expiring" style="display:flex;gap:0.5rem;">
        <input name="days" type="number" value="{days}" min="1" max="90" style="width:80px;">
        <button type="submit">Update</button>
      </form>
    </div>
    <div class="table-wrap">
    <table>
      <tr><th>Content</th><th>Scope</th><th>TTL (days)</th><th>Expires</th><th>Agent</th></tr>
      {"".join(rows)}
    </table>
    </div>
    <p class="count-note">{len(facts)} fact(s) expiring within {days} day(s)</p>"""
    return _dash_layout("Expiring Facts", body, active="expiring")


def _esc(s: Any) -> str:
    """HTML-escape a string."""
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
