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
  - 1-min = entry timing only
  - 5-min = structure (must be supportive for trade direction)
  - 15-min = trend direction (must be supportive/neutral)
  - Hard reject if 5m/15m oppose trade direction
  - 1m conflict = soft downgrade (-5 conf), not hard reject
  - MTF scoring: aligned=+12, partial=+5, tf_conflict=-15, 1m_conflict=-5
  - MTF reflected in confidence scoring, rejection reasons, and execution approval
- [x] **Momentum Mode Bypass**
  - Requirements: RelVol>2, breakout/breakdown setup, clear HH/HL or LH/LL, VWAP aligned, spread<=0.5%, NOT overextended, NOT fake breakout
  - Bypasses: soft conservative filters (RelVol minimum)
  - Does NOT bypass: risk rules, fake breakout detection, overextension, spread/liquidity, MTF conflicts
- [x] **Frontend Diagnostics**
  - MTF Confirmation panel in expanded candidate cards (15m Trend, 5m Structure, 1m Timing, MTF Score)
  - MTF OK / TF CONFLICT / MOMENTUM / BYPASS ACTIVE badges on candidate cards
  - Multi-Timeframe & Momentum Mode stats card in Diagnostics
  - Pipeline Funnel with MTF rejection reasons highlighted in red
  - 9-column stats grid: Scanned, T1, T2, Setups, MTF Conflicts, Momentum, DT, Watchlist, Rejected

### Infrastructure
- [x] 1,000+ stock universe with background batch scanning
- [x] 83+ risky/meme stock blocklist for AutoTrade
- [x] Screener presets, CSV exports, Decision Clarity UI
- [x] Investment scoring engine with category tabs

## Upcoming Tasks
- [ ] P2: Compare stocks side-by-side
- [ ] P3: Scheduler Performance Tracker (win rate, Sharpe ratio)
- [ ] Refactor: server.py modularization into routes/ directory (~4,700 lines)

## Key Files
- `/app/backend/technical_analysis_engine.py` - Core TA math, MTF Confirmer, Tier 1/2 processing
- `/app/backend/ai_trading_system.py` - Trade evaluation, MTF gates, Momentum bypass, scan orchestration
- `/app/backend/server.py` - FastAPI routes, background tasks
- `/app/frontend/src/pages/AutoTrade.jsx` - AutoTrade dashboard with MTF/Momentum diagnostics

## Key API Endpoints
- `GET /api/auto-trade/scan` - Executes Tiered pipeline, returns candidates + diagnostics
- `POST /api/auto-trade/refresh-ta` - Triggers background TA data refresh
- `GET /api/auto-trade/settings` - Current threshold settings
- `POST /api/auth/access` - Verify access code

## Access
- Access Code: `Bullishalmarkhan7.7`
