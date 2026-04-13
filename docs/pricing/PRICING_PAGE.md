# Pricing Page — engram-memory.com/pricing

## Tiers

| Tier | Price | Commits/mo | Conflict Detection | LLM Suggestions | History |
|---|---|---|---|---|---|
| Free | $0 | 500 | ✅ | ❌ | 30 days |
| Builder | $12/mo | 5,000 | ✅ | ✅ | 90 days |
| Team | $39/mo | 25,000 | ✅ | ✅ | 1 year |
| Scale | $99/mo | 100,000 | ✅ | ✅ | Unlimited |

Overage: $0.015/commit above the tier limit.

## Stripe Integration

Products to create in Stripe:
- `engram_builder` — $12/mo recurring
- `engram_team` — $39/mo recurring
- `engram_scale` — $99/mo recurring
- Metered component for overage at $0.015/commit

Payment flow uses Stripe Checkout via the dashboard. Webhook updates the workspace `plan` column on successful payment.
