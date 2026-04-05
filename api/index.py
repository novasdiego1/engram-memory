"""Vercel ASGI entrypoint — landing page with workspace memory graph search."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route


def _render_landing() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Engram — Shared memory for your team's agents</title>
  <meta name="description" content="Shared memory for your team's agents. Works with any MCP-compatible IDE. Zero setup. Your data is private.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.29.2/cytoscape.min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      line-height: 1.6;
      color: #0f172a;
      background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 50%, #dcfce7 100%);
      min-height: 100vh;
    }

    .container { max-width: 800px; margin: 0 auto; padding: 0 24px; }

    /* Header */
    header {
      padding: 24px 0;
      background: rgba(255,255,255,0.8);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid rgba(5,150,105,0.1);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header-content { display: flex; justify-content: space-between; align-items: center; }
    .logo { font-size: 28px; font-weight: 700; color: #059669; text-decoration: none; letter-spacing: -0.02em; }
    .nav-links a { color: #059669; text-decoration: none; font-size: 15px; font-weight: 500; transition: opacity 0.2s; }
    .nav-links a:hover { opacity: 0.7; }

    /* Hero */
    .hero { padding: 80px 0 60px; text-align: center; }
    h1 { font-size: 48px; font-weight: 700; line-height: 1.2; margin-bottom: 20px; color: #064e3b; letter-spacing: -0.03em; }
    .subtitle { font-size: 18px; color: #047857; max-width: 600px; margin: 0 auto 40px; line-height: 1.6; }

    /* Cards */
    .card {
      background: white;
      border-radius: 16px;
      padding: 40px;
      margin-bottom: 32px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
      border: 1px solid rgba(5,150,105,0.1);
    }
    .section-title { font-size: 28px; font-weight: 700; margin-bottom: 24px; color: #064e3b; text-align: center; }

    /* Code blocks */
    .code-block {
      background: #064e3b; color: #d1fae5;
      padding: 20px; border-radius: 12px;
      font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
      font-size: 15px; margin-bottom: 16px;
      position: relative; border: 2px solid #059669;
    }
    .copy-btn {
      position: absolute; top: 12px; right: 12px;
      background: #059669; color: white; border: none;
      padding: 6px 14px; border-radius: 6px;
      cursor: pointer; font-size: 12px; font-weight: 600;
      transition: background 0.2s, transform 0.15s;
    }
    .copy-btn:hover { background: #047857; }
    .copy-btn:active { transform: scale(0.95); }
    .step { font-size: 15px; color: #047857; margin-bottom: 12px; font-weight: 500; }
    .note { font-size: 14px; color: #047857; line-height: 1.6; text-align: center; margin-top: 20px; }

    /* What happens */
    .card p { font-size: 16px; color: #1e293b; line-height: 1.7; margin-bottom: 16px; }
    .card p:last-child { margin-bottom: 0; }
    .card strong { color: #059669; font-weight: 600; }

    /* Tools grid */
    .tools-grid { display: grid; gap: 12px; margin-top: 24px; }
    .tool-item { padding: 16px; background: #f0fdf4; border-radius: 10px; border-left: 4px solid #059669; }
    .tool-item code { font-family: 'SF Mono', monospace; font-size: 14px; color: #059669; font-weight: 600; }
    .tool-item p { font-size: 14px; color: #1e293b; line-height: 1.5; margin-top: 6px; margin-bottom: 0; }

    /* Memory graph search */
    .search-form { display: flex; flex-direction: column; gap: 16px; }
    .search-row { display: flex; gap: 12px; }
    .search-input {
      flex: 1; padding: 12px 16px;
      border: 2px solid rgba(5,150,105,0.2); border-radius: 10px;
      font-size: 15px; font-family: inherit;
      background: #f0fdf4; color: #064e3b;
      transition: border-color 0.2s;
    }
    .search-input:focus { outline: none; border-color: #059669; background: white; }
    .search-input::placeholder { color: #6ee7b7; }
    .search-btn {
      padding: 12px 28px; background: #059669; color: white;
      border: none; border-radius: 10px; font-size: 15px; font-weight: 600;
      cursor: pointer; white-space: nowrap; transition: background 0.2s;
    }
    .search-btn:hover { background: #047857; }
    .search-btn:disabled { background: #a7f3d0; cursor: not-allowed; }

    /* Graph container */
    #graph-section { display: none; }
    #graph-error { display: none; color: #dc2626; font-size: 14px; font-weight: 500; text-align: center; padding: 12px; }
    #graph-loading { display: none; text-align: center; padding: 20px; color: #047857; font-weight: 500; }

    #cy {
      width: 100%; height: 520px;
      border-radius: 12px; border: 2px solid rgba(5,150,105,0.15);
      background: #f8fffe;
    }

    .graph-stats {
      display: flex; gap: 24px; justify-content: center;
      margin-top: 16px; flex-wrap: wrap;
    }
    .stat { text-align: center; }
    .stat-num { font-size: 28px; font-weight: 700; color: #059669; }
    .stat-label { font-size: 13px; color: #047857; font-weight: 500; }

    .graph-legend {
      display: flex; gap: 20px; justify-content: center;
      margin-top: 16px; flex-wrap: wrap;
    }
    .legend-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #1e293b; }
    .legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }

    .fact-detail {
      display: none; margin-top: 16px; padding: 16px;
      background: #f0fdf4; border-radius: 10px;
      border-left: 4px solid #059669;
    }
    .fact-detail h4 { font-size: 14px; font-weight: 600; color: #064e3b; margin-bottom: 8px; }
    .fact-detail p { font-size: 14px; color: #1e293b; margin: 0; line-height: 1.5; }
    .fact-meta { font-size: 12px; color: #047857; margin-top: 8px; }

    /* Search within graph */
    .graph-search-row { display: flex; gap: 8px; margin-top: 16px; }
    .graph-search-input {
      flex: 1; padding: 8px 12px;
      border: 1px solid rgba(5,150,105,0.3); border-radius: 8px;
      font-size: 14px; font-family: inherit; background: white;
    }
    .graph-search-input:focus { outline: none; border-color: #059669; }

    /* Footer */
    footer { padding: 40px 0; text-align: center; }
    .footer-links { display: flex; gap: 24px; justify-content: center; margin-bottom: 12px; }
    .footer-links a { color: #059669; text-decoration: none; font-size: 14px; font-weight: 500; }
    .footer-links a:hover { opacity: 0.7; }
    .footer-tagline { font-size: 13px; color: #047857; font-style: italic; }

    /* Toast */
    .copy-toast {
      position: fixed; bottom: 32px; left: 50%;
      transform: translateX(-50%) translateY(20px);
      background: #064e3b; color: #d1fae5;
      padding: 12px 24px; border-radius: 10px;
      font-size: 14px; font-weight: 500;
      display: flex; align-items: center; gap: 8px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.2);
      opacity: 0; pointer-events: none;
      transition: opacity 0.3s ease, transform 0.3s ease;
      z-index: 1000;
    }
    .copy-toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

    @media (max-width: 768px) {
      h1 { font-size: 32px; }
      .subtitle { font-size: 16px; }
      .hero { padding: 60px 0 40px; }
      .card { padding: 28px 20px; }
      .section-title { font-size: 22px; }
      .search-row { flex-direction: column; }
      #cy { height: 380px; }
    }
  </style>
</head>
<body>

<header>
  <div class="container">
    <div class="header-content">
      <a href="/" class="logo">engram</a>
      <nav class="nav-links">
        <a href="https://github.com/Agentscreator/Engram" target="_blank">GitHub →</a>
      </nav>
    </div>
  </div>
</header>

<section class="hero">
  <div class="container">
    <h1>Shared memory for your team's agents</h1>
    <p class="subtitle">
      Works with any MCP-compatible IDE. Zero setup — one command and you're in.
      Your data is private and never used.
    </p>
  </div>
</section>

<div class="container">

  <!-- Install -->
  <div class="card">
    <h2 class="section-title">Get Started</h2>
    <div class="step">1. Run the installer</div>
    <div class="code-block">
      <button class="copy-btn" onclick="copyCode('install-cmd')">Copy</button>
      <div id="install-cmd">curl -fsSL https://engram.app/install | sh</div>
    </div>
    <div class="step">2. Restart your IDE</div>
    <div class="step">3. Ask your agent</div>
    <div class="code-block">
      <button class="copy-btn" onclick="copyCode('setup-prompt')">Copy</button>
      <div id="setup-prompt">"Set up Engram for my team"</div>
    </div>
    <p class="note">
      Supports Claude Code, Claude Desktop, Cursor, Windsurf, VS Code, and any MCP-compatible IDE
    </p>
  </div>

  <!-- Memory graph search -->
  <div class="card">
    <h2 class="section-title">View Your Memory Graph</h2>
    <p style="text-align:center; color:#047857; margin-bottom:24px; font-size:15px;">
      Search your workspace to see what your agents know — facts, conflicts, and lineage chains.
    </p>
    <div class="search-form">
      <div class="search-row">
        <input
          class="search-input" id="engram-id-input"
          placeholder="Workspace ID  (ENG-XXXX-XXXX)"
          autocomplete="off" spellcheck="false"
        />
      </div>
      <div class="search-row">
        <input
          class="search-input" id="invite-key-input"
          placeholder="Invite key  (ek_live_...)"
          autocomplete="off" spellcheck="false" type="password"
        />
        <button class="search-btn" id="search-btn" onclick="loadGraph()">View Graph</button>
      </div>
    </div>
    <div id="graph-error"></div>
    <div id="graph-loading">Loading your memory graph…</div>

    <div id="graph-section">
      <div class="graph-stats" id="graph-stats"></div>
      <div class="graph-legend" id="graph-legend">
        <span class="legend-item"><span class="legend-dot" style="background:#059669"></span>Active fact</span>
        <span class="legend-item"><span class="legend-dot" style="background:#94a3b8"></span>Retired fact</span>
        <span class="legend-item"><span class="legend-dot" style="background:#f59e0b"></span>Conflict</span>
      </div>
      <div class="graph-search-row">
        <input class="graph-search-input" id="fact-search" placeholder="Filter facts…" oninput="filterGraph(this.value)" />
      </div>
      <div id="cy" style="margin-top:12px;"></div>
      <div class="fact-detail" id="fact-detail">
        <h4 id="detail-scope"></h4>
        <p id="detail-content"></p>
        <div class="fact-meta" id="detail-meta"></div>
      </div>
    </div>
  </div>

  <!-- What it does -->
  <div class="card">
    <h2 class="section-title">What It Does</h2>
    <p>
      When one agent discovers something important — a hidden side effect, a failed approach,
      an undocumented constraint — it commits that fact. Every other agent on your team
      queries it instantly before starting work.
    </p>
    <p>
      When two agents develop incompatible beliefs, Engram detects the contradiction
      and surfaces it for review.
    </p>
    <p>
      <strong>Your data is private.</strong> Facts live in our database, isolated by workspace.
      We don't read, analyze, or redistribute your team's memory. Ever.
    </p>
  </div>

  <!-- Tools -->
  <div class="card">
    <h2 class="section-title">MCP Tools</h2>
    <div class="tools-grid">
      <div class="tool-item"><code>engram_commit</code><p>Persist a verified discovery to shared memory</p></div>
      <div class="tool-item"><code>engram_query</code><p>Pull what your team's agents already know</p></div>
      <div class="tool-item"><code>engram_conflicts</code><p>Surface contradictions between agents' beliefs</p></div>
      <div class="tool-item"><code>engram_resolve</code><p>Settle a disagreement with a decision or merge</p></div>
    </div>
  </div>

</div>

<footer>
  <div class="container">
    <div class="footer-links">
      <span style="font-weight:600;color:#064e3b;">engram</span>
      <a href="https://github.com/Agentscreator/Engram" target="_blank">GitHub</a>
      <a href="https://github.com/Agentscreator/Engram/blob/main/LICENSE" target="_blank">Apache 2.0</a>
    </div>
    <p class="footer-tagline">An engram is the physical trace a memory leaves in the brain</p>
  </div>
</footer>

<div class="copy-toast" id="copy-toast">
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <circle cx="8" cy="8" r="7.5" stroke="#34d399" stroke-width="1"/>
    <path d="M5 8.5L7 10.5L11 6" stroke="#34d399" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
  <span>Copied to clipboard</span>
</div>

<script>
// ── Copy helper ────────────────────────────────────────────────────
let toastTimeout;
function copyCode(id) {
  const text = document.getElementById(id).textContent.trim();
  navigator.clipboard.writeText(text).then(() => {
    const btn = event.target;
    btn.textContent = '✓ Copied';
    setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
    const toast = document.getElementById('copy-toast');
    clearTimeout(toastTimeout);
    toast.classList.add('show');
    toastTimeout = setTimeout(() => toast.classList.remove('show'), 2200);
  });
}

// ── Graph state ────────────────────────────────────────────────────
let cy = null;
let allElements = null;

// ── Load graph data ────────────────────────────────────────────────
async function loadGraph() {
  const engramId  = document.getElementById('engram-id-input').value.trim();
  const inviteKey = document.getElementById('invite-key-input').value.trim();
  const errEl  = document.getElementById('graph-error');
  const loadEl = document.getElementById('graph-loading');
  const secEl  = document.getElementById('graph-section');
  const btn    = document.getElementById('search-btn');

  errEl.style.display  = 'none';
  secEl.style.display  = 'none';
  loadEl.style.display = 'block';
  btn.disabled = true;

  try {
    const resp = await fetch('/workspace/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ engram_id: engramId, invite_key: inviteKey }),
    });
    const data = await resp.json();

    if (!resp.ok) {
      errEl.textContent = data.error || 'Authentication failed. Check your workspace ID and invite key.';
      errEl.style.display = 'block';
      return;
    }

    renderGraph(data);
    secEl.style.display = 'block';
  } catch (e) {
    errEl.textContent = 'Connection error. Please try again.';
    errEl.style.display = 'block';
  } finally {
    loadEl.style.display = 'none';
    btn.disabled = false;
  }
}

// ── Build Cytoscape elements ───────────────────────────────────────
function renderGraph(data) {
  const { facts, conflicts, agents } = data;

  // Stats
  const active = facts.filter(f => !f.valid_until).length;
  const retired = facts.filter(f => f.valid_until).length;
  const open = conflicts.filter(c => c.status === 'open').length;
  document.getElementById('graph-stats').innerHTML = `
    <div class="stat"><div class="stat-num">${active}</div><div class="stat-label">Active facts</div></div>
    <div class="stat"><div class="stat-num">${retired}</div><div class="stat-label">Retired facts</div></div>
    <div class="stat"><div class="stat-num">${open}</div><div class="stat-label">Open conflicts</div></div>
    <div class="stat"><div class="stat-num">${(agents||[]).length}</div><div class="stat-label">Agents</div></div>
  `;

  const elements = [];

  // Group by scope for label
  const scopeColors = {};
  const PALETTE = ['#059669','#0891b2','#7c3aed','#db2777','#d97706','#16a34a','#2563eb'];
  let palIdx = 0;
  const scopeColor = (scope) => {
    if (!scopeColors[scope]) scopeColors[scope] = PALETTE[palIdx++ % PALETTE.length];
    return scopeColors[scope];
  };

  // Fact nodes
  facts.forEach(f => {
    const retired = !!f.valid_until;
    elements.push({ data: {
      id: f.id, label: f.scope || 'general',
      content: f.content, scope: f.scope,
      fact_type: f.fact_type, committed_at: f.committed_at,
      durability: f.durability, retired,
      color: retired ? '#94a3b8' : scopeColor(f.scope || 'general'),
      size: retired ? 20 : (f.confidence || 0.9) * 36 + 12,
    }});
  });

  // Lineage edges (supersedes)
  facts.filter(f => f.supersedes_fact_id).forEach(f => {
    elements.push({ data: {
      id: `lin-${f.id}`, source: f.supersedes_fact_id, target: f.id,
      kind: 'lineage', label: 'supersedes',
    }});
  });

  // Conflict edges
  conflicts.forEach(c => {
    if (c.status === 'open') {
      elements.push({ data: {
        id: `con-${c.id}`, source: c.fact_a_id, target: c.fact_b_id,
        kind: 'conflict', label: 'conflict',
        explanation: c.explanation, severity: c.severity,
      }});
    }
  });

  allElements = elements;

  if (cy) cy.destroy();
  cy = cytoscape({
    container: document.getElementById('cy'),
    elements,
    style: [
      {
        selector: 'node',
        style: {
          'background-color': 'data(color)',
          'label': 'data(label)',
          'font-size': '11px',
          'color': '#1e293b',
          'text-valign': 'bottom',
          'text-margin-y': '4px',
          'width': 'data(size)',
          'height': 'data(size)',
          'border-width': 2,
          'border-color': '#fff',
          'box-shadow': '0 2px 8px rgba(0,0,0,0.15)',
        },
      },
      {
        selector: 'node[retired = true]',
        style: {
          'opacity': 0.45,
          'border-style': 'dashed',
          'border-color': '#94a3b8',
        },
      },
      {
        selector: 'edge[kind = "lineage"]',
        style: {
          'line-color': '#059669',
          'target-arrow-color': '#059669',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'width': 1.5,
          'opacity': 0.5,
        },
      },
      {
        selector: 'edge[kind = "conflict"]',
        style: {
          'line-color': '#ef4444',
          'line-style': 'dashed',
          'width': 2.5,
          'opacity': 0.8,
          'curve-style': 'bezier',
          'label': '⚡',
          'font-size': '14px',
          'text-rotation': 'autorotate',
        },
      },
      {
        selector: ':selected',
        style: {
          'border-color': '#064e3b',
          'border-width': 3,
        },
      },
    ],
    layout: {
      name: facts.length < 30 ? 'cose' : 'random',
      animate: facts.length < 80,
      randomize: false,
      nodeRepulsion: 8000,
      idealEdgeLength: 120,
      padding: 24,
    },
  });

  // Node click → show detail
  cy.on('tap', 'node', evt => {
    const d = evt.target.data();
    const detail = document.getElementById('fact-detail');
    document.getElementById('detail-scope').textContent = `${d.scope || 'general'}  ·  ${d.fact_type || 'observation'}`;
    document.getElementById('detail-content').textContent = d.content || '';
    const ts = d.committed_at ? new Date(d.committed_at).toLocaleString() : '';
    document.getElementById('detail-meta').textContent =
      `${d.retired ? 'Retired' : 'Active'}  ·  ${d.durability || 'durable'}  ·  ${ts}`;
    detail.style.display = 'block';
  });

  cy.on('tap', evt => {
    if (evt.target === cy) {
      document.getElementById('fact-detail').style.display = 'none';
    }
  });
}

// ── Filter graph ───────────────────────────────────────────────────
function filterGraph(query) {
  if (!cy || !allElements) return;
  const q = query.toLowerCase();
  if (!q) {
    cy.elements().style('opacity', 1);
    return;
  }
  cy.nodes().forEach(n => {
    const matches =
      (n.data('content') || '').toLowerCase().includes(q) ||
      (n.data('scope') || '').toLowerCase().includes(q);
    n.style('opacity', matches ? 1 : 0.1);
  });
  cy.edges().style('opacity', 0.05);
}

// Allow pressing Enter in the inputs
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('invite-key-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') loadGraph();
  });
  document.getElementById('engram-id-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') loadGraph();
  });
});
</script>
</body>
</html>"""


async def landing(request: Request) -> HTMLResponse:
    return HTMLResponse(_render_landing())


app = Starlette(routes=[Route("/{path:path}", landing, methods=["GET"])])
