"""Phase 7 — Dashboard: server-rendered HTML with HTMX.

Co-located with the MCP server on the same process. Endpoint: /dashboard.
Landing page at / for new visitors deploying via Vercel.
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
            facts_count=facts_count,
            total_facts=total_facts,
            open_conflicts=open_conflicts,
            resolved_conflicts=resolved_conflicts,
            agents=agents,
            expiring_count=len(expiring),
        ))

    async def knowledge_base(request: Request) -> HTMLResponse:
        scope = request.query_params.get("scope")
        fact_type = request.query_params.get("fact_type")
        as_of = request.query_params.get("as_of")
        facts = await storage.get_current_facts_in_scope(
            scope=scope, fact_type=fact_type, as_of=as_of, limit=100
        )
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


# ── Landing page ─────────────────────────────────────────────────────

def _render_landing() -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Engram — Multi-agent memory consistency</title>
  <meta name="description" content="Give your AI agents shared, persistent memory that detects contradictions. Works with Claude Code, Cursor, Windsurf, Kiro, and any MCP client.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  {_LANDING_STYLE}
</head>
<body>
  <div class="grain"></div>

  <!-- Nav -->
  <nav class="topnav">
    <div class="topnav-inner">
      <a href="/" class="logo" aria-label="Engram home">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <circle cx="14" cy="14" r="12" stroke="url(#glow)" stroke-width="2" opacity="0.5"/>
          <circle cx="14" cy="14" r="6" fill="url(#glow)"/>
          <circle cx="14" cy="14" r="3" fill="#0a0a0b"/>
          <defs>
            <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
              <stop offset="0%" stop-color="#a78bfa"/>
              <stop offset="100%" stop-color="#6d28d9"/>
            </radialGradient>
          </defs>
        </svg>
        <span>engram</span>
      </a>
      <div class="topnav-links">
        <a href="https://github.com/Agentscreator/Engram" target="_blank" rel="noopener">GitHub</a>
        <a href="#get-started">Get Started</a>
        <a href="/dashboard" class="nav-btn">Dashboard</a>
      </div>
    </div>
  </nav>

  <!-- Hero -->
  <section class="hero">
    <div class="hero-glow" aria-hidden="true"></div>
    <div class="hero-content">
      <div class="hero-badge">Open source &middot; Apache 2.0</div>
      <h1>Shared memory for<br>your AI agents</h1>
      <p class="hero-sub">
        Engram gives every agent on your team a persistent knowledge base that
        detects contradictions. One install. Four MCP tools. Zero config.
      </p>
      <div class="hero-install" id="get-started">
        <div class="install-box">
          <div class="install-label">Install &amp; run</div>
          <div class="code-line">
            <code id="install-cmd">pip install engram-mcp &amp;&amp; engram serve --http</code>
            <button class="copy-btn" onclick="copyText('install-cmd')" aria-label="Copy install command">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 11V3a1 1 0 011-1h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              <span class="copy-label">Copy</span>
            </button>
          </div>
        </div>
        <div class="install-or">or use uvx (no install needed)</div>
        <div class="install-box">
          <div class="install-label">One-liner with uvx</div>
          <div class="code-line">
            <code id="uvx-cmd">uvx engram-mcp@latest serve --http</code>
            <button class="copy-btn" onclick="copyText('uvx-cmd')" aria-label="Copy uvx command">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 11V3a1 1 0 011-1h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
              <span class="copy-label">Copy</span>
            </button>
          </div>
        </div>
      </div>
      <p class="hero-note">Requires Python 3.11+. Runs on localhost:7474. No API keys needed.</p>
    </div>
  </section>

  <!-- How it works -->
  <section class="section">
    <div class="section-inner">
      <h2>Four tools. That's the entire API.</h2>
      <p class="section-sub">Engram exposes four MCP tools. Your agents call them automatically.</p>
      <div class="tools-grid">
        <div class="tool-card">
          <div class="tool-icon" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/><path d="M16 16l4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </div>
          <h3>engram_query</h3>
          <p>Pull what your team's agents collectively know about a topic. Structured facts, ranked by relevance.</p>
        </div>
        <div class="tool-card">
          <div class="tool-icon" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          </div>
          <h3>engram_commit</h3>
          <p>Persist a verified discovery. Append-only, timestamped, traceable. Every commit is immediately available to every agent.</p>
        </div>
        <div class="tool-card">
          <div class="tool-icon" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 9v4M12 17h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <h3>engram_conflicts</h3>
          <p>Surface pairs of facts that semantically contradict each other. Reviewable, resolvable, auditable.</p>
        </div>
        <div class="tool-card">
          <div class="tool-icon" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M9 12l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <h3>engram_resolve</h3>
          <p>Settle a disagreement. Pick a winner, merge both sides, or dismiss a false positive.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Connect -->
  <section class="section section-dark" id="connect">
    <div class="section-inner">
      <h2>Connect your MCP client</h2>
      <p class="section-sub">Works with any MCP-compatible client. Pick your setup.</p>

      <div class="tabs" role="tablist">
        <button class="tab active" role="tab" aria-selected="true" onclick="switchTab(event, 'tab-http')">Streamable HTTP</button>
        <button class="tab" role="tab" aria-selected="false" onclick="switchTab(event, 'tab-stdio')">stdio (local)</button>
      </div>

      <div class="tab-panels">
        <div class="tab-panel active" id="tab-http">
          <div class="config-context">Add this to your MCP client config (Claude Code, Cursor, Windsurf, Kiro, VS Code):</div>
          <div class="code-block">
            <div class="code-block-header">
              <span>mcp.json</span>
              <button class="copy-btn" onclick="copyBlock('config-http')" aria-label="Copy HTTP config">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 11V3a1 1 0 011-1h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                <span class="copy-label">Copy</span>
              </button>
            </div>
            <pre id="config-http"><code>{{
  "mcpServers": {{
    "engram": {{
      "url": "http://localhost:7474/mcp"
    }}
  }}
}}</code></pre>
          </div>
        </div>
        <div class="tab-panel" id="tab-stdio">
          <div class="config-context">For local-only mode without running a server. Add to your MCP client config:</div>
          <div class="code-block">
            <div class="code-block-header">
              <span>mcp.json</span>
              <button class="copy-btn" onclick="copyBlock('config-stdio')" aria-label="Copy stdio config">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M3 11V3a1 1 0 011-1h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                <span class="copy-label">Copy</span>
              </button>
            </div>
            <pre id="config-stdio"><code>{{
  "mcpServers": {{
    "engram": {{
      "command": "uvx",
      "args": ["engram-mcp@latest"]
    }}
  }}
}}</code></pre>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Architecture -->
  <section class="section">
    <div class="section-inner">
      <h2>How it works under the hood</h2>
      <p class="section-sub">Three layers. Writes return in ~1ms. Conflict detection runs async.</p>
      <div class="arch-diagram" role="img" aria-label="Architecture diagram showing three layers: I/O Layer with MCP tools, Detection Layer with tiered pipeline, and Storage Layer with SQLite">
        <div class="arch-layer arch-layer-top">
          <div class="arch-label">I/O Layer (MCP)</div>
          <div class="arch-items">
            <span class="arch-chip">engram_commit</span>
            <span class="arch-chip">engram_query</span>
            <span class="arch-chip">engram_conflicts</span>
            <span class="arch-chip">engram_resolve</span>
          </div>
          <div class="arch-note">Agents connect here</div>
        </div>
        <div class="arch-arrow" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M7 14l5 5 5-5" stroke="#6d28d9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="arch-layer arch-layer-mid">
          <div class="arch-label">Detection Layer</div>
          <div class="arch-items">
            <span class="arch-chip">Hash dedup</span>
            <span class="arch-chip">Entity match</span>
            <span class="arch-chip">NLI cross-encoder</span>
            <span class="arch-chip">LLM escalation</span>
          </div>
          <div class="arch-note">Runs asynchronously in background</div>
        </div>
        <div class="arch-arrow" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 5v14M7 14l5 5 5-5" stroke="#6d28d9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="arch-layer arch-layer-bottom">
          <div class="arch-label">Storage Layer (SQLite)</div>
          <div class="arch-items">
            <span class="arch-chip">Append-only</span>
            <span class="arch-chip">Bitemporal</span>
            <span class="arch-chip">Zero config</span>
          </div>
          <div class="arch-note">~/.engram/knowledge.db</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Clients -->
  <section class="section section-dark">
    <div class="section-inner">
      <h2>Works with your tools</h2>
      <p class="section-sub">Any MCP-compatible client. No vendor lock-in.</p>
      <div class="clients-row">
        <div class="client-badge">Claude Code</div>
        <div class="client-badge">Cursor</div>
        <div class="client-badge">Windsurf</div>
        <div class="client-badge">Kiro</div>
        <div class="client-badge">VS Code</div>
        <div class="client-badge">Any MCP Client</div>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <div class="footer-inner">
      <div class="footer-left">
        <span class="footer-logo">engram</span>
        <span class="footer-tagline">The physical trace a memory leaves in the brain.</span>
      </div>
      <div class="footer-links">
        <a href="https://github.com/Agentscreator/Engram" target="_blank" rel="noopener">GitHub</a>
        <a href="https://github.com/Agentscreator/Engram/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener">Contributing</a>
        <a href="https://github.com/Agentscreator/Engram/blob/main/LICENSE" target="_blank" rel="noopener">Apache 2.0</a>
      </div>
    </div>
  </footer>

  <script>
  function copyText(id) {{
    const el = document.getElementById(id);
    const text = el.textContent.replace(/&amp;/g, '&');
    navigator.clipboard.writeText(text).then(() => {{
      const btn = el.closest('.code-line').querySelector('.copy-label');
      btn.textContent = 'Copied';
      setTimeout(() => btn.textContent = 'Copy', 2000);
    }});
  }}
  function copyBlock(id) {{
    const el = document.getElementById(id);
    navigator.clipboard.writeText(el.textContent).then(() => {{
      const btn = el.closest('.code-block').querySelector('.copy-label');
      btn.textContent = 'Copied';
      setTimeout(() => btn.textContent = 'Copy', 2000);
    }});
  }}
  function switchTab(e, panelId) {{
    document.querySelectorAll('.tab').forEach(t => {{
      t.classList.remove('active');
      t.setAttribute('aria-selected', 'false');
    }});
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    e.currentTarget.classList.add('active');
    e.currentTarget.setAttribute('aria-selected', 'true');
    document.getElementById(panelId).classList.add('active');
  }}
  </script>
</body>
</html>"""


_LANDING_STYLE = """
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0a0a0b; color: #e4e4e7; line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  .grain {
    position: fixed; inset: 0; z-index: 9999; pointer-events: none; opacity: 0.03;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  }

  /* Nav */
  .topnav { position: sticky; top: 0; z-index: 100; background: rgba(10,10,11,0.8);
            backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255,255,255,0.06); }
  .topnav-inner { max-width: 1100px; margin: 0 auto; padding: 0.75rem 1.5rem;
                   display: flex; align-items: center; justify-content: space-between; }
  .logo { display: flex; align-items: center; gap: 0.5rem; text-decoration: none;
          color: #e4e4e7; font-weight: 600; font-size: 1.05rem; }
  .topnav-links { display: flex; align-items: center; gap: 1.25rem; }
  .topnav-links a { color: #a1a1aa; text-decoration: none; font-size: 0.875rem;
                     transition: color 0.15s; }
  .topnav-links a:hover { color: #e4e4e7; }
  .nav-btn { background: rgba(109,40,217,0.15); border: 1px solid rgba(109,40,217,0.3);
             border-radius: 8px; padding: 0.4rem 1rem; color: #c4b5fd !important;
             transition: all 0.15s; }
  .nav-btn:hover { background: rgba(109,40,217,0.25); border-color: rgba(109,40,217,0.5); }

  /* Hero */
  .hero { position: relative; padding: 6rem 1.5rem 4rem; text-align: center;
          overflow: hidden; }
  .hero-glow { position: absolute; top: -200px; left: 50%; transform: translateX(-50%);
               width: 800px; height: 600px; border-radius: 50%;
               background: radial-gradient(ellipse, rgba(109,40,217,0.15) 0%, transparent 70%);
               pointer-events: none; }
  .hero-content { position: relative; max-width: 720px; margin: 0 auto; }
  .hero-badge { display: inline-block; padding: 0.3rem 0.9rem; border-radius: 100px;
                background: rgba(109,40,217,0.1); border: 1px solid rgba(109,40,217,0.25);
                color: #c4b5fd; font-size: 0.8rem; font-weight: 500; margin-bottom: 1.5rem; }
  .hero h1 { font-size: clamp(2.2rem, 5vw, 3.5rem); font-weight: 700; line-height: 1.15;
             letter-spacing: -0.03em; color: #fafafa;
             background: linear-gradient(to bottom right, #fafafa, #a1a1aa);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent;
             background-clip: text; }
  .hero-sub { margin-top: 1.25rem; font-size: 1.1rem; color: #a1a1aa; max-width: 560px;
              margin-left: auto; margin-right: auto; line-height: 1.7; }
  .hero-install { margin-top: 2.5rem; display: flex; flex-direction: column;
                  align-items: center; gap: 0.75rem; }
  .install-box { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
                 border-radius: 12px; padding: 1rem 1.25rem; width: 100%; max-width: 520px; }
  .install-label { font-size: 0.75rem; color: #71717a; text-transform: uppercase;
                   letter-spacing: 0.05em; margin-bottom: 0.5rem; font-weight: 500; }
  .code-line { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
  .code-line code { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem;
                    color: #c4b5fd; white-space: nowrap; overflow-x: auto; }
  .copy-btn { display: flex; align-items: center; gap: 0.35rem; background: none;
              border: 1px solid rgba(255,255,255,0.1); border-radius: 6px;
              padding: 0.3rem 0.6rem; color: #71717a; cursor: pointer;
              font-size: 0.75rem; transition: all 0.15s; flex-shrink: 0;
              font-family: 'Inter', sans-serif; }
  .copy-btn:hover { color: #e4e4e7; border-color: rgba(255,255,255,0.2); }
  .install-or { color: #52525b; font-size: 0.8rem; }
  .hero-note { margin-top: 1rem; font-size: 0.8rem; color: #52525b; }

  /* Sections */
  .section { padding: 5rem 1.5rem; }
  .section-dark { background: rgba(255,255,255,0.02); }
  .section-inner { max-width: 1000px; margin: 0 auto; }
  .section h2 { font-size: 1.75rem; font-weight: 700; color: #fafafa; text-align: center;
                letter-spacing: -0.02em; }
  .section-sub { text-align: center; color: #a1a1aa; margin-top: 0.75rem;
                 margin-bottom: 2.5rem; font-size: 1rem; }

  /* Tool cards */
  .tools-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 1rem; }
  .tool-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
               border-radius: 12px; padding: 1.5rem; transition: border-color 0.2s; }
  .tool-card:hover { border-color: rgba(109,40,217,0.3); }
  .tool-icon { color: #8b5cf6; margin-bottom: 0.75rem; }
  .tool-card h3 { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem;
                  color: #c4b5fd; margin-bottom: 0.5rem; font-weight: 500; }
  .tool-card p { font-size: 0.85rem; color: #a1a1aa; line-height: 1.6; }

  /* Tabs */
  .tabs { display: flex; gap: 0.25rem; justify-content: center; margin-bottom: 1.5rem;
          background: rgba(255,255,255,0.03); border-radius: 10px; padding: 0.25rem;
          width: fit-content; margin-left: auto; margin-right: auto; }
  .tab { background: none; border: none; color: #71717a; padding: 0.5rem 1.25rem;
         border-radius: 8px; cursor: pointer; font-size: 0.875rem; font-weight: 500;
         transition: all 0.15s; font-family: 'Inter', sans-serif; }
  .tab.active { background: rgba(109,40,217,0.15); color: #c4b5fd; }
  .tab:hover:not(.active) { color: #a1a1aa; }
  .tab-panels { max-width: 560px; margin: 0 auto; }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .config-context { font-size: 0.85rem; color: #a1a1aa; margin-bottom: 1rem; text-align: center; }

  /* Code blocks */
  .code-block { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px; overflow: hidden; }
  .code-block-header { display: flex; justify-content: space-between; align-items: center;
                       padding: 0.6rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.06);
                       font-size: 0.75rem; color: #52525b; }
  .code-block pre { padding: 1rem 1.25rem; overflow-x: auto; margin: 0; }
  .code-block code { font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
                     color: #c4b5fd; line-height: 1.7; }

  /* Architecture */
  .arch-diagram { display: flex; flex-direction: column; align-items: center; gap: 0.5rem;
                  max-width: 600px; margin: 0 auto; }
  .arch-layer { width: 100%; padding: 1.25rem 1.5rem; border-radius: 12px; text-align: center; }
  .arch-layer-top { background: rgba(109,40,217,0.08); border: 1px solid rgba(109,40,217,0.2); }
  .arch-layer-mid { background: rgba(59,130,246,0.06); border: 1px solid rgba(59,130,246,0.15); }
  .arch-layer-bottom { background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.15); }
  .arch-label { font-weight: 600; font-size: 0.9rem; color: #e4e4e7; margin-bottom: 0.5rem; }
  .arch-items { display: flex; flex-wrap: wrap; gap: 0.4rem; justify-content: center;
                margin-bottom: 0.4rem; }
  .arch-chip { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
               padding: 0.2rem 0.6rem; border-radius: 6px;
               background: rgba(255,255,255,0.05); color: #a1a1aa; }
  .arch-note { font-size: 0.75rem; color: #52525b; }
  .arch-arrow { color: #6d28d9; }

  /* Clients */
  .clients-row { display: flex; flex-wrap: wrap; gap: 0.75rem; justify-content: center; }
  .client-badge { padding: 0.6rem 1.25rem; border-radius: 10px;
                  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
                  font-size: 0.875rem; color: #a1a1aa; font-weight: 500; }

  /* Footer */
  .footer { border-top: 1px solid rgba(255,255,255,0.06); padding: 2rem 1.5rem; }
  .footer-inner { max-width: 1100px; margin: 0 auto; display: flex;
                  justify-content: space-between; align-items: center; flex-wrap: wrap;
                  gap: 1rem; }
  .footer-left { display: flex; align-items: center; gap: 1rem; }
  .footer-logo { font-weight: 600; color: #71717a; }
  .footer-tagline { font-size: 0.8rem; color: #3f3f46; font-style: italic; }
  .footer-links { display: flex; gap: 1.25rem; }
  .footer-links a { color: #52525b; text-decoration: none; font-size: 0.8rem;
                    transition: color 0.15s; }
  .footer-links a:hover { color: #a1a1aa; }

  /* Responsive */
  @media (max-width: 640px) {
    .hero { padding: 4rem 1rem 3rem; }
    .hero h1 { font-size: 2rem; }
    .hero-sub { font-size: 1rem; }
    .tools-grid { grid-template-columns: 1fr; }
    .topnav-links { gap: 0.75rem; }
    .footer-inner { flex-direction: column; text-align: center; }
    .footer-left { flex-direction: column; }
    .code-line code { font-size: 0.8rem; }
  }
</style>
"""


# ── Dashboard HTML rendering ─────────────────────────────────────────

_HTMX_SCRIPT = '<script src="https://unpkg.com/htmx.org@2.0.4"></script>'

_DASH_STYLE = """
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0a0a0b; color: #e4e4e7; line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }
  .container { max-width: 1200px; margin: 0 auto; padding: 1.5rem; }

  /* Header */
  .dash-header { display: flex; align-items: center; justify-content: space-between;
                 margin-bottom: 1.5rem; flex-wrap: wrap; gap: 0.75rem; }
  .dash-title { display: flex; align-items: center; gap: 0.5rem; }
  .dash-title h1 { font-size: 1.25rem; font-weight: 600; color: #fafafa; }
  .dash-title .dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e;
                     box-shadow: 0 0 8px rgba(34,197,94,0.4); }
  .back-link { color: #71717a; text-decoration: none; font-size: 0.8rem;
               transition: color 0.15s; }
  .back-link:hover { color: #a1a1aa; }

  /* Nav */
  nav { display: flex; gap: 0.25rem; margin-bottom: 1.5rem; background: rgba(255,255,255,0.03);
        border-radius: 10px; padding: 0.25rem; width: fit-content; flex-wrap: wrap; }
  nav a { color: #71717a; text-decoration: none; padding: 0.45rem 0.9rem; border-radius: 8px;
          font-size: 0.8rem; font-weight: 500; transition: all 0.15s; }
  nav a:hover { color: #a1a1aa; background: rgba(255,255,255,0.03); }
  nav a.active { background: rgba(109,40,217,0.15); color: #c4b5fd; }

  /* Stats */
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
           gap: 0.75rem; margin-bottom: 1.5rem; }
  .stat { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06);
          border-radius: 12px; padding: 1.25rem; }
  .stat-value { font-size: 2rem; font-weight: 700; color: #fafafa;
                letter-spacing: -0.02em; }
  .stat-label { font-size: 0.8rem; color: #71717a; margin-top: 0.15rem; }
  .stat-accent .stat-value { color: #8b5cf6; }
  .stat-warn .stat-value { color: #f59e0b; }
  .stat-ok .stat-value { color: #22c55e; }

  /* Tables */
  h2 { font-size: 1rem; font-weight: 600; color: #e4e4e7; margin-bottom: 0.75rem; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 0.6rem 0.75rem; font-size: 0.7rem; font-weight: 500;
       color: #52525b; text-transform: uppercase; letter-spacing: 0.05em;
       border-bottom: 1px solid rgba(255,255,255,0.06); }
  td { padding: 0.6rem 0.75rem; font-size: 0.8rem; color: #a1a1aa;
       border-bottom: 1px solid rgba(255,255,255,0.04); }
  tr:hover td { background: rgba(255,255,255,0.02); }
  .content-cell { max-width: 360px; overflow: hidden; text-overflow: ellipsis;
                  white-space: nowrap; }

  /* Badges */
  .badge { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 100px;
           font-size: 0.7rem; font-weight: 500; }
  .badge-high { background: rgba(239,68,68,0.12); color: #f87171; }
  .badge-medium { background: rgba(245,158,11,0.12); color: #fbbf24; }
  .badge-low { background: rgba(34,197,94,0.12); color: #4ade80; }
  .badge-open { background: rgba(239,68,68,0.12); color: #f87171; }
  .badge-resolved { background: rgba(34,197,94,0.12); color: #4ade80; }
  .badge-dismissed { background: rgba(113,113,122,0.12); color: #a1a1aa; }
  .badge-verified { background: rgba(34,197,94,0.12); color: #4ade80; }
  .badge-unverified { background: rgba(245,158,11,0.12); color: #fbbf24; }

  /* Timeline bar */
  .timeline-bar { height: 6px; border-radius: 3px; background: #8b5cf6; min-width: 4px; }
  .timeline-bar.superseded { background: #3f3f46; }

  /* Filter bar */
  .filter-bar { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem;
                flex-wrap: wrap; }
  input, select { background: rgba(255,255,255,0.03); color: #e4e4e7;
                  border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;
                  padding: 0.45rem 0.75rem; font-size: 0.8rem; font-family: 'Inter', sans-serif;
                  transition: border-color 0.15s; }
  input:focus, select:focus { outline: none; border-color: rgba(109,40,217,0.4); }
  input::placeholder { color: #3f3f46; }
  button[type="submit"] { background: rgba(109,40,217,0.15); color: #c4b5fd;
                          border: 1px solid rgba(109,40,217,0.3); border-radius: 8px;
                          padding: 0.45rem 1rem; font-size: 0.8rem; cursor: pointer;
                          font-family: 'Inter', sans-serif; font-weight: 500;
                          transition: all 0.15s; }
  button[type="submit"]:hover { background: rgba(109,40,217,0.25); }

  .table-wrap { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px; overflow: hidden; }
  .table-wrap table { margin: 0; }
  .count-note { color: #3f3f46; font-size: 0.75rem; margin-top: 0.75rem; }

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
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
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
    facts_count: int,
    total_facts: int,
    open_conflicts: int,
    resolved_conflicts: int,
    agents: list[dict],
    expiring_count: int,
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
    </div>
    """
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
            f"<td>{_esc(f['scope'])}</td>"
            f"<td>{f['confidence']:.2f}</td>"
            f"<td>{_esc(f['fact_type'])}</td>"
            f"<td>{_esc(f['agent_id'])}</td>"
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
    <p class="count-note">{len(facts)} fact(s)</p>
    """
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
            f"<td>{sev_badge}</td>"
            f"<td>{status_badge}</td>"
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
    <p class="count-note">{len(conflicts)} conflict(s)</p>
    """
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
            f"<td>{_esc(f['scope'])}</td>"
            f"<td>{_esc(f['agent_id'])}</td>"
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
    </div>
    """
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
            f"<td>{total}</td>"
            f"<td>{flagged}</td>"
            f"<td>{reliability}</td>"
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
    </div>
    """
    return _dash_layout("Agents", body, active="agents")


def _render_expiring(facts: list[dict], days: int) -> str:
    rows = []
    for f in facts:
        rows.append(
            f"<tr><td class='content-cell'>{_esc(f['content'])}</td>"
            f"<td>{_esc(f['scope'])}</td>"
            f"<td>{f.get('ttl_days', '')}</td>"
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
    <p class="count-note">{len(facts)} fact(s) expiring within {days} day(s)</p>
    """
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
