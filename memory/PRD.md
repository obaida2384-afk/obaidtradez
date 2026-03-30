# ObaidTradez — Product Requirements Document

## Original Problem Statement
Build "ObaidTradez", a secure, dark-themed AI trading and investing platform protected by access code (`Bullishalmarkhan7.7`). The platform features dual modes: "Trading" (short-term) and "Investments" (long-term). Core focus is on high performance, filtering noise, scaling to 1,000+ companies, and enforcing strict risk controls.

**Latest Priority (March 2026):** Transform the system from a news-first engine (which produced 0 day trades) into a **technical-analysis-first, professional-grade day trading engine** using Polygon OHLCV data for internal indicator computation.

## Core Architecture
```
/app/
├── backend/
│   ├── ai_trading_system.py (Orchestrator, TA-first DayTradingEngine, Risk Manager)
│   ├── auto_trade_scheduler.py (Periodic execution, safety locks)
│   ├── news_sentiment_engine.py (Multi-source aggregation, boost only)
│   ├── technical_analysis_engine.py (EMA, RSI, MACD, VWAP, Market Structure, FVG)
│   ├── enhanced_investment_engine.py (Fundamental scoring)
│   └── server.py (FastAPI routes)
├── frontend/
│   ├── src/pages/
│   │   ├── AutoTrade.jsx (Pipeline Funnel, TA Status, Diagnostics)
│   │   ├── News.jsx, Investments.jsx, Trading.jsx, etc.
```

## What's Been Implemented

### Completed (March 2026)
- [x] Access code gate with JWT auth
- [x] Trading Signals engine with FMP data
- [x] Investment scoring engine (1,097+ companies via batch processing)
- [x] News Sentiment Engine (500+ articles, FMP + Finnhub + Benzinga)
- [x] Auto-Trade Scheduler with safety controls (daily loss caps, market hours)
- [x] Risky stock blocking (83+ meme/leveraged stocks)
- [x] Persistent watchlist
- [x] **P0: Technical Analysis Engine** (EMA 9/20/50, RSI 14, MACD 12/26/9, VWAP, RelVol, AvgRange, Spread, Market Structure HH/HL/LH/LL, Support/Resistance, FVG, Fake Breakout, Overextension Filter)
- [x] **P0: TA-First Day Trading Pipeline** (Catalyst gate REMOVED, news=boost only, confidence threshold lowered to 65)
- [x] **P0: Pipeline Funnel** (universe_scanned → prefilter_passed → ta_analyzed → setup_found → filters_passed → confidence_passed → risk_approved → executed)
- [x] **P0: Exact Rejection Reasons** for every rejected DT candidate
- [x] **P0: Background TA Refresh** with Polygon rate-limit management (13s delay per stock)
- [x] **P0: TACache** (in-memory 5-min TTL + MongoDB persistence)
- [x] CSV Export (Portfolio, AutoTrade, Investments)
- [x] Custom Screener Presets (Investments)
- [x] Decision Clarity UI (Investments)

### Key Technical Details
- **DT Threshold**: 65 (base), regime adjustments: bearish +5, neutral_bearish +0, bullish -5
- **Filters**: RelVol >= 1.3, Spread <= 0.5%, no overextension
- **Polygon API**: Free tier (5 calls/min), using sequential 13s-delay batch processing
- **Data flow**: Polygon OHLCV → Internal math → Setups/Structure/Indicators → Confidence scoring → Risk check
- **No external API for indicators** - all computed internally from bar data

## Prioritized Backlog

### P1 - Upcoming
- Multi-Timeframe Confirmation (1m entry, 5m structure, 15m trend) for full analysis mode
- Momentum Mode bypass (RelVol > 2 + strong structure)
- Deeper rejection logging in pipeline

### P2 - Future
- Compare stocks side-by-side
- Mobile-responsive sidebar
- Sector filters for Investment Ideas

### P3 - Backlog
- Scheduler Performance Tracker (win rate, Sharpe ratio)
- server.py refactoring (4,700+ lines)

## 3rd Party Integrations
- OpenAI GPT-5.2 (Emergent LLM Key)
- Financial Modeling Prep (FMP) — User API Key
- Polygon.io — User API Key (OHLCV bars for TA)
- Benzinga — User API Key (news)
- Finnhub — User API Key (news)
- Alpaca — User API Key (paper trading)
- Alpha Vantage — User API Key
