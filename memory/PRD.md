# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading platform. Aggressive momentum strategy designed to scale a $1,000 account toward $1,000/month through disciplined momentum trading during regular market hours.

## Architecture
```
/app/backend/
├── ai_trading_system.py          (Orchestrator, Momentum Engine, PositionSizer, RiskManager)
├── enhanced_investment_engine.py  (Scoring with overvaluation penalty)
├── auto_trade_scheduler.py       (Background loop, power hours priority, auto-recovery)
├── live_price_engine.py          (Alpaca WS + REST fallback)
├── live_reeval_engine.py         (Dynamic re-eval on price changes)
├── price_integrity.py            (Single source of truth, dead ticker detection)
├── reeval_verifier.py            (Market-open automated verification)
├── top_movers_scanner.py         (Top gainers/losers scanner with FMP + DB fallback)
├── performance_tracker.py        (NEW: Session analytics, trade quality, pipeline efficiency)
└── server.py                     (FastAPI routes)
```

## Active Strategy: Aggressive Momentum
- Price range: $5-$50
- Min RelVol: 1.5x, Min ATR: 2.0%, Min Volume: 500K
- Dynamic confidence thresholds: 58 (bullish) / 60 (neutral) / 62 (bearish)
- Position sizing: 60-70 conf → 10% | 70-80 → 15% | 80+ → 20%
- Entry: 3-signal alignment (momentum + volume + trend/breakout/catalyst)
- Exit: Partial profit at 1.5% (50% scale-out), full TP at 3%, SL at 1.5%
- Risk: 3% daily max loss, 3 total losses hard stop, 30min cooldown
- Power hours: 2x faster scanning in first/last 2 hours of session
- Max 8 trades/day, paper mode deployment

## Top Movers Scanner
- Fetches top gainers/losers from FMP API (falls back to DB signals)
- Quality filters: $5-$50, ≥500K vol, ≥2% change, ≥$100M market cap
- Caps: 30 gainers + 30 losers + 20 actives
- Auto-refresh every 20min during regular hours
- Source tagging: top_gainer / top_loser / most_active

## Performance Evaluation Framework
- **Per-trade logging**: entry signals, confidence, regime, time window, source
- **Session summary**: total trades, win rate, avg win/loss, net P&L, max drawdown, P&L by time window
- **Pipeline efficiency**: movers→setups conversion, setups→executed %, top 3 rejection reasons
- **Trade quality**: signal-to-outcome analysis, confidence vs outcome, entry quality (early/on_time/late/chasing)
- **Risk compliance**: stop-loss execution consistency, trailing stop effectiveness, position sizing audit
- **Market regime tagging**: performance by regime (trending/choppy/bearish/high-vol)
- **Best/worst trades**: top 3 best + worst with full reasoning
- Auto-logged via scheduler hooks (no manual intervention needed)

## Completed (April 1, 2026)
- [x] Aggressive Momentum Strategy: full engine overhaul
- [x] Momentum prefilter: $5-$50 price, RelVol >= 1.5x, ATR > 2%, volume >= 500K
- [x] Dynamic thresholds: base 60, bullish 58, bearish 62
- [x] Confidence-tiered position sizing: 60-70→10%, 70-80→15%, 80+→20%
- [x] 3-signal alignment entry requirement
- [x] Partial profit at 1.5% (50% scale-out), full TP at 3%, SL at 1.5%
- [x] Hard stop: 3 total losses/day, 30min cooldown
- [x] Power hours scanning (2x speed 9:30-11:30, 14:00-16:00 ET)
- [x] Top Movers Scanner: FMP + DB fallback, quality filters, auto-refresh
- [x] Performance Evaluation Framework: full tracking + analytics dashboard
- [x] 7 analytics API endpoints (/api/analytics/*)
- [x] Frontend: Strategy Overview, Top Movers, Pipeline Summary, Performance Report

## Key API Endpoints
- `/api/analytics/full-report` — Complete performance report
- `/api/analytics/session-summary` — Session metrics
- `/api/analytics/trade-quality` — Signal quality analysis
- `/api/analytics/pipeline-efficiency` — Conversion rates
- `/api/analytics/best-worst-trades` — Top 3 best/worst
- `/api/analytics/risk-compliance` — Risk rule audit
- `/api/analytics/regime-performance` — Performance by regime
- `/api/top-movers/scan` — Top movers scanner
- `/api/auto-trade/scan` — Full trading scan

## Upcoming
- [ ] Evaluate paper trading during next 1-2 live regular sessions
- [ ] Review performance report and tune based on real data
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py and AutoTrade.jsx (P3)

## Access: `Bullishalmarkhan7.7`
