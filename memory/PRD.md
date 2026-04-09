# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading platform. Aggressive momentum strategy designed to scale a $1,000 account toward $1,000/month. Dual-mode: Day Trading (momentum) + Long-Term Investing (ETF core + quality growth + value). Strict separation between engines. Full execution transparency.

## Architecture
```
/app/backend/
├── ai_trading_system.py          (Orchestrator, Momentum Engine, Ownership-tagged orders, Manual protection)
├── execution_transparency.py     (NEW: Candidate-to-execution rejection tracking)
├── long_term_engine.py           (LT Portfolio Engine - 3 buckets, staged buying, rebalancing)
├── auto_trade_scheduler.py       (Full transparency logging, ownership gates, 7-gate execution pipeline)
├── enhanced_investment_engine.py  (Scoring with overvaluation penalty)
├── live_price_engine.py          (Alpaca WS + REST fallback)
├── price_integrity.py            (Single source of truth)
├── top_movers_scanner.py         (DB-backed gainer/loser scanner)
├── performance_tracker.py        (Session analytics)
└── server.py                     (FastAPI routes, ~5800 lines)
/app/frontend/src/pages/
├── LongTermInvest.jsx            (Market tab: 1250 companies with ratings, Portfolio, Recs, Universe)
├── AutoTrade.jsx                 (Analytics, Scheduler, Top Movers)
├── Trading.jsx                   (News Sentiment)
├── Investments.jsx               (Short-term screener)
```

## Execution Transparency (NEW)
Every qualified candidate is tracked through a 7-gate pipeline:
1. **Max trades reached** — cycle limit
2. **Cooldown active** — post-loss cooldown
3. **Duplicate position** — already holding symbol
4. **Soft lock** — near daily loss limit
5. **Risk manager** — violations (drawdown, concentration, etc.)
6. **Position sizing** — 0 shares after calculation
7. **Order submission** — Alpaca rejection

Each non-executed candidate is logged with exact rejection category from 18 defined categories.

## Ownership & Strategy Separation (NEW)
- Every bot order tagged: `ownership=bot`, `strategy_type=day_trade|long_term`
- `client_order_id` prefix: `OT_bot_day_trade_xxxx` or `OT_bot_long_term_xxxx`
- Manual positions identified by absence of bot ownership record
- Day trade engine NEVER touches long-term or manual positions
- Long-term engine NEVER interferes with day trades

## Separated Analytics (NEW)
- **Day Trading**: Round trips from Alpaca fills, win rate, avg win/loss, best/worst, P&L
- **Long-Term**: Active/closed positions, portfolio value, bucket allocation
- **Manual/External**: Listed separately, marked as PROTECTED

## Current Day Trading Performance
- 3 round trips, 66.7% win rate, +$498.35 P&L
- TSM: +$262.40 (7.74%), CRUS: +$301.05 (4.53%), CF: -$65.10 (-1.58%)
- Account: $100,495.84 equity on $100K base

## Key API Endpoints
### Execution Transparency
- `/api/execution/rejection-report` — Why setups weren't traded (18 categories)
- `/api/execution/pipeline-stages` — Candidate counts per pipeline stage

### Separated Analytics
- `/api/analytics/by-strategy` — DT/LT/Manual separated with full metrics

### Day Trading
- `/api/trading/scan` — Full trading scan
- `/api/auto-trade/scan` — Auto trade scan

### Long-Term Investing
- `/api/lt-invest/market-overview` — 1,250 companies with full analysis
- `/api/lt-invest/portfolio` — LT portfolio with live prices
- `/api/lt-invest/stage-buy` — Staged buy (POST)

## Completed (April 9, 2026)
- [x] Execution transparency engine (18 rejection categories, 7-gate pipeline logging)
- [x] Ownership + strategy tagging on all bot orders
- [x] Manual position protection (bot never touches unowned positions)
- [x] Separated analytics (DT/LT/Manual with actual P&L from Alpaca fills)
- [x] Backfilled existing trades with ownership=bot, strategy_type=day_trade

## Previously Completed (April 6, 2026)
- [x] P0: Relaxed T1 signals (2 confirmations, top mover override, near-threshold momentum)
- [x] Scanner tuning (price cap $100, regime-aware prefilter)
- [x] P1/P2: Long-Term Investing Engine + Frontend (3 buckets, staged buying, Market tab with 1,250 companies)

## Upcoming
- [ ] Evaluate paper trading during live market session
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py (>5800 lines) and AutoTrade.jsx (>2300 lines) (P3)

## Access: `Bullishalmarkhan7.7`
