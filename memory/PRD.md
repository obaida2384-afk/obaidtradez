# ObaidTradez - Product Requirements Document

## Original Problem Statement
ObaidTradez is a secure, dark-themed AI trading and investing platform protected by access code (`Bullishalmarkhan7.7`). The platform features a technical-analysis-first, professional-grade day trading engine. Core requirements demand high performance, filtering out noise to surface quality setups, scanning ~80+ liquid stocks rapidly, and enforcing strict risk controls.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB
- **Data Source**: Polygon.io (OHLCV bars, primary), FMP (fundamentals), Finnhub/Benzinga/Marketaux (news)
- **Execution**: Alpaca Paper Trading API
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key

## Core Technical Design
- **Tiered TA Pipeline**: Tier 1 (fast composite score on ~80 stocks) → Tier 2 (deep multi-timeframe analysis on top 20)
- **Internal TA Math**: EMA, RSI, MACD, VWAP, Market Structure, FVG calculated internally from Polygon OHLCV bars (NO external indicator APIs)
- **MTF Classification Engine**: Classifies every stock into BULLISH_ALIGNED, BEARISH_ALIGNED, MOMENTUM_CANDIDATE, NEAR_MISS, MIXED, CONFLICT — shared between decision engine and heatmap UI
- **Aggressive Caching**: Bar-level + TA-level caching to prevent Polygon rate limits
- **News = Confidence Boost Only**: Never a hard gate for trades
- **Direction Consistency**: LONG→BUY, SHORT→SELL across backend, API, UI, and execution layer

## Completed Features

### P0 (Core Engine)
- [x] Internal Technical Analysis engine (EMA, RSI, MACD, VWAP, FVG, Market Structure)
- [x] Tiered Pipeline: Tier 1 fast composite → Tier 2 deep analysis
- [x] Aggressive bar-level caching (~4s scan time)
- [x] News as confidence boost only (not a gate)
- [x] Dynamic threshold configuration (DT: 65, LT: 72)

### P1 (Quality & Momentum) - Completed Mar 30, 2026
- [x] Multi-Timeframe Confirmation (MTF) — 1m=timing, 5m=structure gate, 15m=trend gate
- [x] Momentum Mode Bypass — RelVol>2.5, strong candle, clear structure, VWAP aligned, <2% distance
- [x] Direction Bug Fix — LONG→BUY, SHORT→SELL consistently
- [x] Confidence Score Normalization — base=35, wider distribution (85-95 elite, 75-85 strong, 65-75 acceptable)
- [x] Momentum Mode Control — tightened to RelVol>2.5, strong breakout candle, <2% VWAP
- [x] Pre-Market Safety — hard disable execution before 9:30 AM ET
- [x] MTF Conflict Detection — explicit logging for every rejection
- [x] Trade Logging System — MongoDB `trade_log` collection with full lifecycle

### MTF Heatmap - Completed Mar 30, 2026
- [x] **Backend MTF Classification Engine** — Classifies stocks into 6 categories: BULLISH_ALIGNED, BEARISH_ALIGNED, MOMENTUM_CANDIDATE, NEAR_MISS, MIXED, CONFLICT
- [x] **Auto-Trading Integration** — MTF classification drives trade selection, ranking, confidence scoring. Aligned avg confidence ~60 vs Conflict avg ~24
- [x] **Frontend Heatmap UI** — Color-coded grid with 15m trend, 5m structure, 1m timing, MTF status, confidence, RelVol, VWAP, setup type, rejection reasons
- [x] **Distribution Summary** — Clickable category cards showing counts and percentages
- [x] **Sorting & Filtering** — Sort by confidence/rel_vol/mtf_score/category, filter by direction (LONG/SHORT) and category
- [x] **Performance** — Zero extra cost, reuses cached TA data
- [x] **Consistency** — Backend classification matches UI display exactly
- [x] Dedicated `/api/auto-trade/mtf-heatmap` endpoint
- [x] Confidence distribution card, momentum %, market session badge, Trade Log tab

### Infrastructure
- [x] 1,000+ stock universe with background batch scanning
- [x] 83+ risky/meme stock blocklist for AutoTrade
- [x] Screener presets, CSV exports, Decision Clarity UI

## Upcoming Tasks
- [ ] P2: Compare stocks side-by-side
- [ ] P3: Scheduler Performance Tracker (win rate, Sharpe ratio)
- [ ] Refactor: server.py modularization into routes/ directory (~4,800 lines)

## Key Files
- `/app/backend/technical_analysis_engine.py` - Core TA math, MTF Confirmer, MTFClassifier, confidence scoring
- `/app/backend/ai_trading_system.py` - Trade evaluation, MTF gates, Momentum bypass, heatmap builder, trade logging
- `/app/backend/auto_trade_scheduler.py` - Market session management
- `/app/backend/server.py` - FastAPI routes
- `/app/frontend/src/pages/AutoTrade.jsx` - AutoTrade dashboard with MTF Heatmap, diagnostics, trade log

## Key API Endpoints
- `GET /api/auto-trade/scan` - Tiered pipeline scan with mtf_heatmap, confidence_distribution, momentum_pct
- `GET /api/auto-trade/mtf-heatmap` - Dedicated MTF heatmap endpoint
- `GET /api/auto-trade/trade-log` - Full trade lifecycle log
- `POST /api/auto-trade/refresh-ta` - Background TA data refresh
- `POST /api/auth/access` - Verify access code

## Key DB Collections
- `trade_log` - Comprehensive trade lifecycle
- `auto_trade_log` - Order execution log
- `trading_signals`, `investment_signals`, `settings`, `scheduler_state`

## Access
- Access Code: `Bullishalmarkhan7.7`
