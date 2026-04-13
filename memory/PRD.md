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
3. **Auto Trade Scheduler** — Autonomous execution loop with 8-gate pipeline (including re-entry cooldown), session awareness, risk controls
4. **Execution Transparency** — Logs every candidate's journey through execution gates with rejection reasons
5. **Position Protection** — Manual Alpaca positions tagged separately, never touched by bot

## Key Endpoints
- `/api/execution/diagnostics` — Real-time score breakdowns, component utilization, pipeline health
- `/api/execution/rejection-report` — Post-session candidate rejection analysis
- `/api/positions` — Positions enriched with ownership/strategy labels
- `/api/auto-trade/trade-log` — Trade log with entry reasons, exit plans, confidence breakdown
- `/api/trading/scan` — Full TA pipeline scan
- `/api/lt-invest/market-overview` — 1250+ company master list
- `/api/scheduler/status` — Scheduler state

## What's Implemented
- Trading signals engine with FMP/Finnhub news sentiment
- Investment engine scanning 1097+ companies via background batching
- Auto Trade scheduler with 8-gate execution pipeline (including re-entry cooldown)
- Strict ownership tagging (bot vs manual) for position protection
- Execution transparency logger
- Long-Term Investing tab with Market Overview (auto-refreshing P&L)
- Watchlist, Portfolio, Alerts, Chatbot, Screener, News, Backtesting pages
- Risk controls: RISKY_STOCKS blocklist (83+), daily loss limits, cooldowns, drawdown protection

## Recent Work (April 2026)

### P0: Day Trading Execution Bottleneck — RESOLVED
- **Root Cause**: ConfidenceScoringEngine used non-existent field names (confluence_factors vs confluence_score, missing rr_ratio, news_sentiment format mismatch)
- **Fix**: Recalibrated 7-component scorer. Result: 103/168 signals now pass 61 threshold (was 0)
- Scheduler refactored to use scan_opportunities() for TA-enriched data

### P1: Verifier Watcher Bug — RESOLVED
- Fixed MarketSessionManager._now_et() → _now_et()

### P2: Execution Diagnostics — IMPLEMENTED
- `/api/execution/diagnostics` with component utilization and score breakdowns

### 5 UI Improvements — IMPLEMENTED & TESTED (iteration 40: 100%)
1. **"Why Didn't It Trade?"** — Rejection report with gate breakdown, blocking reason per candidate
2. **Pipeline Gate Breakdown** — Component utilization bars (tech, volume, sentiment, risk-reward, trend, volatility, regime)
3. **Position Labels** — Day Trade (Bot) amber, Long-Term (Bot) blue, Manual/Protected emerald badges
4. **Trade Quality Details** — Entry reasons, exit plan (SL/TP/Partial), confidence breakdown per trade
5. **Re-entry Cooldown** — 30min default, configurable slider, prevents immediate re-buy after sell

### LT Portfolio Auto-Refresh — FIXED
- P&L now auto-refreshes every 60 seconds during market hours

## Backlog
- Compare stocks side-by-side (P3)
- Modularize server.py (>6000 lines) and AutoTrade.jsx (>2700 lines) (P3)
- Auto-rebalance alerts for Long-Term portfolio drift (P3)
- Optimize execution quality and scale performance
