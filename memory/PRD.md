# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Secure, dark-themed AI day trading platform. Aggressive momentum strategy designed to scale a $1,000 account toward $1,000/month through disciplined momentum trading during regular market hours.

## Architecture
```
/app/backend/
├── ai_trading_system.py        (Orchestrator, Momentum Engine, PositionSizer, RiskManager)
├── enhanced_investment_engine.py (Scoring with overvaluation penalty)
├── auto_trade_scheduler.py     (Background loop, power hours priority, MongoDB auto-recovery)
├── live_price_engine.py        (Alpaca WS + REST fallback)
├── live_reeval_engine.py       (Dynamic re-eval on price changes)
├── price_integrity.py          (Single source of truth, dead ticker detection)
├── reeval_verifier.py          (Market-open automated verification)
├── top_movers_scanner.py       (NEW: Top gainers/losers scanner with FMP + DB fallback)
└── server.py                   (FastAPI routes)
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
- Fetches top gainers/losers from FMP API (falls back to DB signals if 403)
- Quality filters: $5-$50 price, ≥500K volume, ≥2% change, ≥$100M market cap
- Excludes halted/low-float/risky tickers
- Caps: 30 gainers + 30 losers + 20 actives
- Auto-refresh every 20min during regular market hours
- Pre-populates trading universe with top movers (relaxed prefilter for movers)
- Source tagging: top_gainer / top_loser / most_active on each symbol

## Completed (March 31, 2026)
- [x] Live Prices: WS + REST fallback, SSE stream, mode indicator UI
- [x] Dynamic Re-Evaluation: VWAP/S-R/breakout triggers, 30s throttle
- [x] Price Integrity: 167 dead tickers flagged, 14 ticker renames
- [x] Overvaluation penalty: stocks with upside < -25% blocked from "Buy"
- [x] Entry status: TRADE_NOW/WATCHLIST/MISSED/STALE_SETUP/BLOWN_STOP
- [x] Market-open auto-verifier: 30min capture, health checks, persists to MongoDB
- [x] Bug Fix: ExplanationCard livePrices prop — Day/Long tabs fixed

## Completed (April 1, 2026)
- [x] Aggressive Momentum Strategy: full engine overhaul
- [x] Momentum prefilter: $5-$50 price, RelVol >= 1.5x, ATR > 2%, volume >= 500K
- [x] Dynamic thresholds: base 60, bullish 58, bearish 62
- [x] Confidence-tiered position sizing: 60-70→10%, 70-80→15%, 80+→20%
- [x] 3-signal alignment entry requirement (momentum + volume + setup/VWAP/catalyst)
- [x] Partial profit at 1.5% (50% scale-out), full TP at 3%, SL at 1.5%
- [x] Hard stop: 3 total losses/day, 30min cooldown after consecutive losses
- [x] Relaxed quality filters for DT: removed ranging structure hard reject, softened MTF gate
- [x] Enhanced catalyst boosting: +4 to +8 confidence from news
- [x] Power hours scanning (2x speed in 9:30-11:30 and 14:00-16:00 ET)
- [x] Strategy Overview panel in AutoTrade UI
- [x] Top Movers Scanner: FMP + DB fallback, quality filters, auto-refresh, source tagging
- [x] Top Movers panel in UI: Injected/Prefilter/Candidates/Watchlist + Active Movers chips
- [x] Pipeline Summary with top movers step
- [x] Source badges on candidate cards (TOP GAINER / TOP LOSER / MOST ACTIVE)

## Key API Endpoints
- `/api/top-movers/scan` — Fetch/compute top movers
- `/api/top-movers/status` — Scanner state and config
- `/api/top-movers/performance` — Daily scan analytics
- `/api/auto-trade/scan` — Full trading scan with top_movers block
- `/api/auto-trade/settings` — Strategy settings CRUD

## Upcoming
- [ ] Evaluate paper trading during next live regular session
- [ ] Review candidate count, prefilter pass rate, setup conversions
- [ ] Tune scanner parameters based on live performance
- [ ] Compare stocks side-by-side (P3)
- [ ] Modularize server.py (>5000 lines) and AutoTrade.jsx (>2000 lines) (P3)

## Access: `Bullishalmarkhan7.7`
