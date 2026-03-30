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
- [x] Auto Trade dashboard with timing diagnostics

### P1 (Quality & Momentum) - Completed Mar 30, 2026
- [x] **Multi-Timeframe Confirmation (MTF)**
  - 1-min = entry timing only, 5-min = structure gate, 15-min = trend gate
  - Hard reject if 5m/15m oppose trade direction
  - 1m conflict = soft downgrade, not hard reject
  - Explicit logging for every MTF rejection
- [x] **Momentum Mode Bypass**
  - Requirements: RelVol>2.5, breakout/breakdown setup, strong candle (body>=60% range), clear HH/HL or LH/LL, VWAP aligned, spread<=0.5%, within 2% of VWAP, NOT overextended, NOT fake breakout
  - Bypasses soft conservative filters only
  - Does NOT bypass: risk rules, fake breakout, overextension, spread/liquidity, MTF conflicts

### Critical Fixes - Completed Mar 30, 2026
- [x] **Direction Bug Fix**: LONG→BUY, SHORT→SELL consistently across backend logic, API responses, UI display, and execution layer
- [x] **Confidence Score Normalization**: Base lowered from 45→35, wider distribution (85-95 elite, 75-85 strong, 65-75 acceptable, <65 reject), added penalties for weak structure, borderline RelVol, structure opposition
- [x] **Momentum Mode Control**: Tightened to RelVol>2.5 (from 2.0), strong breakout candle check, <2% VWAP distance requirement
- [x] **Pre-Market Safety**: Hard disable auto-execution before 9:30 AM ET, scan-only mode in pre-market, signals logged as informational only
- [x] **MTF Conflict Detection**: Verified working (5+ conflicts per scan), explicit logging for every rejection with reasons
- [x] **Trade Logging System**: MongoDB `trade_log` collection storing full lifecycle (ticker, direction, entry/SL/TP, exit price, P&L $+%, setup type, confidence, entry/exit reasons, MTF status, momentum mode)
- [x] **Frontend Diagnostics**: Confidence distribution card (elite/strong/acceptable/below), momentum %, market session badge with pre-market warning, Trade Log tab with full trade details

### Infrastructure
- [x] 1,000+ stock universe with background batch scanning
- [x] 83+ risky/meme stock blocklist for AutoTrade
- [x] Screener presets, CSV exports, Decision Clarity UI

## Upcoming Tasks
- [ ] P2: Compare stocks side-by-side
- [ ] P3: Scheduler Performance Tracker (win rate, Sharpe ratio)
- [ ] Refactor: server.py modularization into routes/ directory (~4,800 lines)

## Key Files
- `/app/backend/technical_analysis_engine.py` - Core TA math, MTF Confirmer, confidence scoring (base=35)
- `/app/backend/ai_trading_system.py` - Trade evaluation (LONG→BUY, SHORT→SELL), MTF gates, Momentum bypass (RelVol>2.5), pre-market safety, trade logging
- `/app/backend/auto_trade_scheduler.py` - Market session management, scheduler loop
- `/app/backend/server.py` - FastAPI routes, background tasks
- `/app/frontend/src/pages/AutoTrade.jsx` - AutoTrade dashboard with all diagnostics

## Key API Endpoints
- `GET /api/auto-trade/scan` - Tiered pipeline scan with confidence_distribution, momentum_pct, market_session
- `GET /api/auto-trade/trade-log` - Full trade lifecycle log
- `POST /api/auto-trade/refresh-ta` - Background TA data refresh
- `GET /api/auto-trade/settings` - Current threshold settings
- `POST /api/auth/access` - Verify access code

## Key DB Collections
- `trade_log` - Comprehensive trade lifecycle (entry/exit/P&L/setup/confidence/reasons/MTF/momentum)
- `auto_trade_log` - Order execution log
- `trading_signals`, `investment_signals` - Signal data
- `settings` - Dynamic thresholds
- `scheduler_state`, `scheduler_notifications`, `scheduler_execution_log` - Scheduler data

## Access
- Access Code: `Bullishalmarkhan7.7`
