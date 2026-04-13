# Engram Pricing

## Model: Commit-Volume Tiers

Engram charges on commit volume — the unit that directly drives compute cost. No per-seat pricing (agents aren't humans), no per-conflict pricing (that penalizes users when things go wrong).

| Tier | Price | Commits/mo | Conflict Detection | LLM Suggestions | History |
|---|---|---|---|---|---|
| Free | $0 | 500 | ✅ | ❌ | 30 days |
| Builder | $12/mo | 5,000 | ✅ | ✅ | 90 days |
| Team | $39/mo | 25,000 | ✅ | ✅ | 1 year |
| Scale | $99/mo | 100,000 | ✅ | ✅ | Unlimited |

Overage: $0.015/commit above the tier limit. Prevents churn on spikes without forcing a mid-month upgrade.

## Why This Model

- Free tier includes conflict detection — that's the hook. Don't gate the differentiator, gate the scale and intelligence.
- LLM suggestions are gated on paid tiers — near-zero implementation cost to toggle, but feels like a meaningful upgrade.
- Commit volume maps directly to compute cost. Each commit triggers LLM-based conflict detection against the full fact corpus.
- No "per seat" — the right unit is agent activity (commits), not human seats. Teams might have 50 agents and 3 humans.
- History gating on free costs nothing to enforce but creates real pull toward paid.

## What We Don't Do

- Per-conflict pricing — punishes users when we catch something (perverse incentive)
- Storage-based pricing — facts are tiny, users feel nickel-and-dimed for nothing
- Per-agent pricing — trivially gamed by sharing one agent identity

## Checking Usage

```bash
engram stats --json
engram config show
```

## Implementation Notes

- Usage tracked per workspace via `commit_count_month` column
- Limits enforced at the API level in `_tool_commit`
- Overage commits succeed but are billed at $0.015/commit
- Hard limit returns 429 with upgrade URL when no payment method is on file
- Plan upgrades via Stripe Checkout on the dashboard
