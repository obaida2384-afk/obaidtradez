# ObaidTradez - AI Trading & Investing Platform

## Problem Statement
Secure, dark-themed AI trading and investing platform protected by access code (`Bullishalmarkhan7.7`). Features dual modes: Day Trading (short-term momentum) and Long-Term Investments. Core requirements: high performance, strict risk controls, 1000+ company universe, ownership-tagged positions (manual vs bot), execution transparency.

## Access
- Access Code: `Bullishalmarkhan7.7`

## Architecture
- **Backend**: FastAPI (Python) on port 8001
- **Frontend**: React on port 3000
- **Database**: MongoDB
- **APIs**: FMP, Finnhub, Alpaca (Paper), Polygon, OpenAI GPT-5.2

## Core Systems
1. **Day Trading Engine** — Momentum-driven TA pipeline: prefilter → Tier1 fast scan → Tier2 deep analysis → DayTradingEngine.evaluate_buy() → confidence scoring → execution
2. **Long-Term Engine** — Fundamental scoring, 1250+ company Market Overview with fair value, ratings
3. **Auto Trade Scheduler** — Autonomous execution loop with 7-gate pipeline, session awareness, risk controls
4. **Execution Transparency** — Logs every candidate's journey through execution gates with rejection reasons
5. **Position Protection** — Manual Alpaca positions tagged separately, never touched by bot

## Key Endpoints
- `/api/execution/diagnostics` — Real-time score breakdowns, component utilization, pipeline health
- `/api/execution/rejection-report` — Post-session candidate rejection analysis
- `/api/trading/scan` — Full TA pipeline scan
- `/api/lt-invest/market-overview` — 1250+ company master list
- `/api/scheduler/status` — Scheduler state

## What's Implemented
- Trading signals engine with FMP/Finnhub news sentiment
- Investment engine scanning 1097+ companies via background batching
- Auto Trade scheduler with 7-gate execution pipeline
- Strict ownership tagging (bot vs manual) for position protection
- Execution transparency logger
- Long-Term Investing tab with Market Overview
- Watchlist, Portfolio, Alerts, Chatbot, Screener, News, Backtesting pages
- Risk controls: RISKY_STOCKS blocklist (83+), daily loss limits, cooldowns, drawdown protection

## Recent Fixes (April 2026)
### P0: Day Trading Execution Bottleneck — RESOLVED
- **Root Cause**: `ConfidenceScoringEngine.score_day_trade()` was scoring against fields that didn't exist in stored signals:
  - `confluence_factors` → signals store `confluence_score` (field name mismatch)
  - `rr_ratio` → missing from indicators (now calculated from stop_loss/take_profit/price)
  - `news_sentiment` → stored as string, scorer expected dict
- **Fix**: Recalibrated scorer with 7 components (technical_setup 25%, volume 18%, sentiment 12%, risk_reward 12%, trend_alignment 13%, volatility 10%, market_regime 10%)
- **Result**: 102 of 168 signals now pass 61 threshold (was 0 before)
- **Additional Fix**: Scheduler refactored to use `scan_opportunities()` for TA-enriched data instead of stale DB reads

### P1: Verifier Watcher Bug — RESOLVED
- `MarketSessionManager._now_et()` → `_now_et()` (module-level function)

### P2: Execution Diagnostics Endpoint — IMPLEMENTED
- `/api/execution/diagnostics` with component utilization, top signal breakdowns, pipeline health

## Backlog
- Compare stocks side-by-side (P3)
- Modularize server.py (>5800 lines) and AutoTrade.jsx (>2500 lines) (P3)
- Auto-rebalance alerts for Long-Term portfolio drift (P3)
