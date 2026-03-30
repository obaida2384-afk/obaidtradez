# ObaidTradez - Product Requirements Document

## Original Problem Statement
ObaidTradez is a secure, dark-themed AI trading and investing platform protected by access code (`Bullishalmarkhan7.7`). The platform features a technical-analysis-first, professional-grade day trading engine. Core requirements: high performance, quality-only setups, ~80+ liquid stock scanning, strict risk controls.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB
- **Data Source**: Polygon.io (OHLCV bars), FMP (fundamentals), Finnhub/Benzinga/Marketaux (news)
- **Execution**: Alpaca Paper Trading API
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key

## Core Technical Design
- **Tiered TA Pipeline**: Tier 1 (fast composite) → Tier 2 (deep multi-timeframe)
- **Internal TA Math**: EMA, RSI, MACD, VWAP, Structure, FVG from Polygon OHLCV (no external APIs)
- **MTF Classification Engine**: BULLISH_ALIGNED, BEARISH_ALIGNED, MOMENTUM_CANDIDATE, NEAR_MISS, MIXED, CONFLICT
- **Aggressive Caching**: Bar-level + TA-level (prevents rate limits)
- **Direction Consistency**: LONG→BUY, SHORT→SELL everywhere

## Strict Trade Quality Filters (Current)
1. **15m Trend**: ranging = heavy penalty, reject unless RelVol>2 + breakout
2. **Strict MTF**: Aligned = 15m+5m BOTH directional (ranging doesn't count)
3. **Volume**: <1.0 = hard reject, 1.0-1.3 = penalize, >=1.5 = preferred
4. **Entry Timing**: Only execute when 1m=entry_ready. Early/weak = watchlist only
5. **Spread**: >0.5% = reject, >0.3% = penalize
6. **Pre-Market**: Hard disable execution before 9:30 AM ET
7. **Momentum Mode**: RelVol>2.5, strong candle, clear structure, VWAP<2%, no bypass of MTF/risk

## Completed Features
- [x] Internal TA engine + Tiered Pipeline + Caching
- [x] MTF Confirmation + MTF Classification + MTF Heatmap (frontend + backend decision engine)
- [x] Direction bug fix (LONG→BUY, SHORT→SELL)
- [x] Confidence normalization (base=35, wider distribution)
- [x] Strict Momentum Mode (RelVol>2.5)
- [x] Pre-market safety gate
- [x] Trade logging system (MongoDB trade_log)
- [x] Strict quality filters (15m trend, volume, timing, spread, alignment)
- [x] Frontend: Heatmap grid, confidence distribution, pipeline funnel, trade log tab

## Upcoming Tasks
- [ ] P2: Compare stocks side-by-side
- [ ] P3: Scheduler Performance Tracker (win rate, Sharpe ratio)
- [ ] Refactor: server.py modularization (~4,800 lines)

## Key Files
- `/app/backend/technical_analysis_engine.py` - TA math, MTF Confirmer, MTFClassifier, confidence scoring
- `/app/backend/ai_trading_system.py` - Trade evaluation, quality filters, heatmap builder, trade logging
- `/app/backend/server.py` - FastAPI routes
- `/app/frontend/src/pages/AutoTrade.jsx` - AutoTrade dashboard with all diagnostics

## Key API Endpoints
- `GET /api/auto-trade/scan` - Full pipeline scan
- `GET /api/auto-trade/mtf-heatmap` - Dedicated MTF heatmap
- `GET /api/auto-trade/trade-log` - Trade lifecycle log
- `POST /api/auth/access` - Verify access code

## Access
- Access Code: `Bullishalmarkhan7.7`
