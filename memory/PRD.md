# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading platform. Aggressive momentum strategy designed to scale a $1,000 account toward $1,000/month through disciplined momentum trading during regular market hours. Dual-mode: Short-Term Trading (momentum) and Long-Term Investing (ETF core + quality growth + value).

## Architecture
```
/app/backend/
├── ai_trading_system.py          (Orchestrator, Momentum Engine, P0 Relaxed Signals)
├── long_term_engine.py           (NEW: LT Portfolio Engine - 3 buckets, staged buying, rebalancing)
├── enhanced_investment_engine.py  (Scoring with overvaluation penalty)
├── auto_trade_scheduler.py       (Background loop, power hours priority, auto-recovery)
├── live_price_engine.py          (Alpaca WS + REST fallback)
├── live_reeval_engine.py         (Dynamic re-eval on price changes)
├── price_integrity.py            (Single source of truth, dead ticker detection)
├── reeval_verifier.py            (Market-open automated verification)
├── top_movers_scanner.py         (Top gainers/losers scanner with DB fallback)
├── performance_tracker.py        (Session analytics, trade quality, pipeline efficiency)
└── server.py                     (FastAPI routes)
/app/frontend/src/pages/
├── LongTermInvest.jsx            (NEW: LT Portfolio UI - buckets, recs, universe, staged buying)
├── AutoTrade.jsx                 (Analytics, Scheduler, Top Movers UI)
├── Trading.jsx                   (News Sentiment UI)
├── Investments.jsx               (Short-term investment screener)
```

## Active Strategy: Aggressive Momentum (Day Trading)
- Price range: $5-$50
- Min RelVol: 1.5x, Min ATR: 2.0%, Min Volume: 500K
- Dynamic confidence thresholds: 58 (bullish) / 60 (neutral) / 62 (bearish)
- P0 Relaxed Signals: 2 strong confirmations sufficient, top mover override at 58+ conf, near-threshold momentum at 58-61 with 2x+ volume
- Position sizing: 60-70 conf → 10% | 70-80 → 15% | 80+ → 20%
- Exit: Partial profit at 1.5% (50% scale-out), full TP at 3%, SL at 1.5%
- Risk: 3% daily max loss, 3 total losses hard stop, 30min cooldown
- Max 8 trades/day, paper mode deployment

## Long-Term Investment Engine (NEW)
- **Core Bucket (40-60%)**: ETF-heavy (VOO, VTI, QQQ, SCHD, VEA, VWO, BND, GLD, VNQ). Max 35% per ETF. Quarterly rebalance.
- **Quality Growth (25-40%)**: 25 proven compounders (AAPL, MSFT, GOOGL, NVDA, etc.). Max 10% per stock. Monthly rebalance.
- **Opportunistic Value (10-25%)**: 20 deep value plays (JPM, XOM, INTC, etc.). Max 5% per stock. Monthly rebalance.
- **Staged Buying**: 4 stages of 25% each. Stage 2 after 7 days, stage 3 after 14 days, stage 4 after 21 days.
- **Diversification Score**: 0-100 based on position count, bucket balance, concentration, asset type mix.
- **Recommendations**: Auto-generated Buy/Add/Trim/Rebalance based on portfolio state + market signals.
- **Thesis Health**: Per-position health check combining P&L + fundamentals + time held.

## Key API Endpoints
### Day Trading
- `/api/trading/scan` — Full trading scan
- `/api/auto-trade/scan` — Auto trade scan
- `/api/analytics/full-report` — Complete performance report
- `/api/top-movers/scan` — Top movers scanner

### Long-Term Investing (NEW)
- `/api/lt-invest/portfolio` — Full LT portfolio with live prices
- `/api/lt-invest/universe` — Investment universe by bucket
- `/api/lt-invest/recommendations` — Buy/Add/Trim recommendations
- `/api/lt-invest/stage-buy` — Execute staged buy (POST)
- `/api/lt-invest/trim` — Trim position (POST)
- `/api/lt-invest/close` — Close position (POST)
- `/api/lt-invest/thesis/{symbol}` — Thesis health check
- `/api/lt-invest/rebalance-check` — Rebalance status

## Completed (April 6, 2026)
- [x] P0: Relaxed Trading Tab T1 signal requirements
  - 2 strong confirmations → TRADE (was 70 threshold, now 62)
  - Top mover override: 2 signals + top mover at 58+ conf
  - Near-threshold momentum: 2 signals + 2x+ volume at 58-61 conf
  - Top mover 1-signal override at 62+ conf
  - All risk limits unchanged
- [x] P1: Long-Term Investing Backend Engine (long_term_engine.py)
  - 3-bucket system (Core/Quality Growth/Opportunistic Value)
  - Staged buying (4x 25% increments)
  - Diversification scoring (0-100)
  - Rebalance detection (drift + timing)
  - Recommendation generation (Buy/Add/Trim/Sell/Hold)
  - Full CRUD: stage-buy, trim, close, thesis health
- [x] P2: Long-Term Investing Frontend (LongTermInvest.jsx)
  - Summary strip with diversification ring
  - 3 bucket allocation bars with status indicators
  - Portfolio tab with position rows + thesis click
  - Recommendations tab with action cards
  - Universe tab with searchable stock/ETF grid
  - Stage Buy modal and Thesis Health modal

## Previously Completed
- [x] Aggressive Momentum Strategy engine overhaul
- [x] Top Movers Scanner with DB fallback
- [x] Performance Evaluation Framework + Analytics dashboard
- [x] 7 analytics API endpoints

## Upcoming
- [ ] Tune scanner parameters based on real performance data
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py (>5200 lines) and AutoTrade.jsx (>2300 lines) (P3)

## Access: `Bullishalmarkhan7.7`
