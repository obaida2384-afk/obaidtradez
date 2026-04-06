# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading platform. Aggressive momentum strategy designed to scale a $1,000 account toward $1,000/month through disciplined momentum trading during regular market hours. Dual-mode: Short-Term Trading (momentum) and Long-Term Investing (ETF core + quality growth + value).

## Architecture
```
/app/backend/
├── ai_trading_system.py          (Orchestrator, Momentum Engine, P0 Relaxed Signals, Regime-aware prefilter)
├── long_term_engine.py           (LT Portfolio Engine - 3 buckets, staged buying, rebalancing)
├── enhanced_investment_engine.py  (Scoring with overvaluation penalty)
├── auto_trade_scheduler.py       (Background loop, power hours priority, auto-recovery)
├── live_price_engine.py          (Alpaca WS + REST fallback)
├── live_reeval_engine.py         (Dynamic re-eval on price changes)
├── price_integrity.py            (Single source of truth, dead ticker detection)
├── reeval_verifier.py            (Market-open automated verification)
├── top_movers_scanner.py         (Top gainers/losers scanner with DB fallback)
├── performance_tracker.py        (Session analytics, trade quality, pipeline efficiency)
└── server.py                     (FastAPI routes, ~5400 lines)
/app/frontend/src/pages/
├── LongTermInvest.jsx            (LT Portfolio: Market (1250 companies), Portfolio, Recs, Universe tabs)
├── AutoTrade.jsx                 (Analytics, Scheduler, Top Movers UI)
├── Trading.jsx                   (News Sentiment UI)
├── Investments.jsx               (Short-term investment screener)
```

## Active Strategy: Aggressive Momentum (Day Trading)
- Price range: $5-$100 (expanded from $50)
- Min RelVol: 1.5x (1.2x in bearish regime), Min ATR: 2.0% (1.5% in bearish), Min Volume: 500K
- Dynamic confidence thresholds: 58 (bullish) / 60 (neutral) / 62 (bearish)
- P0 Relaxed Signals: 2 strong confirmations at 62+ conf, top mover override at 58+ conf, near-threshold momentum at 58-61 with 2x+ volume, top mover 1-signal at 62+
- Position sizing: 60-70 conf → 10% | 70-80 → 15% | 80+ → 20%
- Exit: Partial profit at 1.5% (50% scale-out), full TP at 3%, SL at 1.5%
- Risk: 3% daily max loss, 3 total losses hard stop, 30min cooldown
- Max 8 trades/day, paper mode deployment

## Long-Term Investment Engine
- **Core Bucket (40-60%)**: ETF-heavy (VOO, VTI, QQQ, SCHD, VEA, VWO, BND, GLD, VNQ). Max 35% per ETF. Quarterly rebalance.
- **Quality Growth (25-40%)**: 25 proven compounders. Max 10% per stock. Monthly rebalance.
- **Opportunistic Value (10-25%)**: 20 deep value plays. Max 5% per stock. Monthly rebalance.
- **Staged Buying**: 4 stages of 25% each. Stage 2 after 7d, stage 3 after 14d, stage 4 after 21d.
- **Diversification Score**: 0-100 based on position count, bucket balance, concentration, asset type mix.
- **Market Overview**: 1,250 companies merged from trading signals + investment signals with live prices, entry/stop/target, quality/growth/valuation/historical ratings, bull/bear cases.

## Key API Endpoints
### Day Trading
- `/api/trading/scan` — Full trading scan
- `/api/auto-trade/scan` — Auto trade scan
- `/api/analytics/full-report` — Complete performance report
- `/api/top-movers/scan` — Top movers scanner

### Long-Term Investing
- `/api/lt-invest/market-overview` — 1,250 companies with full analysis + live prices + ratings
- `/api/lt-invest/portfolio` — Full LT portfolio with live prices
- `/api/lt-invest/universe` — Investment universe by bucket (9 ETFs + 25 Growth + 20 Value)
- `/api/lt-invest/recommendations` — Buy/Add/Trim recommendations
- `/api/lt-invest/stage-buy` — Execute staged buy (POST)
- `/api/lt-invest/trim` — Trim position (POST)
- `/api/lt-invest/close` — Close position (POST)
- `/api/lt-invest/thesis/{symbol}` — Thesis health check
- `/api/lt-invest/rebalance-check` — Rebalance status

## Completed (April 6, 2026)
- [x] P0: Relaxed Trading Tab T1 signal requirements (6 unit tests passed)
- [x] Scanner tuning: price cap $50→$100, regime-aware prefilter relaxation (bearish: RelVol→1.2, ATR→1.5%)
- [x] P1: Long-Term Investing Backend Engine (long_term_engine.py)
- [x] P2: Long-Term Investing Frontend (LongTermInvest.jsx) with Market tab showing 1,250 companies
- [x] Market Overview endpoint merging trading signals + investment signals + live prices + performance ratings
- [x] Full analysis per company: entry zone, stop loss, take profit, R:R, quality/growth/valuation ratings, bull/bear cases

## Previously Completed
- [x] Aggressive Momentum Strategy engine overhaul
- [x] Top Movers Scanner with DB fallback
- [x] Performance Evaluation Framework + Analytics dashboard
- [x] FMP/Finnhub News Sentiment integration
- [x] 1,097+ stock universe with background batching

## Upcoming
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py (>5400 lines) and AutoTrade.jsx (>2300 lines) (P3)
- [ ] Tune scanner parameters based on real live market performance data
- [ ] Add auto-rebalance alerts for LT portfolio drift

## Access: `Bullishalmarkhan7.7`
