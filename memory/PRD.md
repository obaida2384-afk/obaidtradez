# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Build "ObaidTradez" - a secure, dark-themed AI trading and investing platform with:
1. **Mandatory access code gate**: `Bullishalmarkhan7.7`
2. **Two-mode platform**: Trading (short-term) and Investments (long-term)
3. **Left sidebar tabs**: Dashboard, Trading, Investments, Chatbot, Screener, News & Sentiment, Backtesting, Portfolio, Alerts, Auto Trade, Settings
4. **Multiple external APIs**: Alpaca (paper trading), Polygon, Finnhub, FMP, Alpha Vantage, NewsAPI, Marketaux
5. **Strict Risk Management** and **AI chatbot with GPT-5.2**
6. **1,400+ stock universe** with dual-engine autonomous trading

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + Python
- **Database**: MongoDB
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Data**: Multi-provider (FMP, Polygon, Finnhub, Alpha Vantage, Marketaux)
- **Trading**: Alpaca Paper Trading API

## What's Been Implemented

### Core Platform
- [x] Secure access gate with code validation
- [x] Dashboard with dual-mode signals overview
- [x] Trading page with quality engine (selective signals, confluence requirements)
- [x] AI Chatbot with 3 modes (GPT-5.2)
- [x] Stock Screener with mode toggle
- [x] Portfolio page with Alpaca integration
- [x] Alerts page
- [x] Settings page with risk management
- [x] Mobile-responsive hamburger menu sidebar

### Investment Engine
- [x] 1,400+ stock universe across all sectors
- [x] Investment signals caching in MongoDB
- [x] Category tabs: Hot, Bullish, Undervalued, Watch, Bearish
- [x] Background refresh with FMP rate limit handling
- [x] 30-year historical performance metrics (CAGR, Max Drawdown)
- [x] Decision Clarity UI, Screener Presets, CSV Export

### Backtesting
- [x] 10yr/20yr/30yr backtesting options
- [x] S&P 500 (SPY) baseline comparison
- [x] Strategy vs benchmark visualization

### AI News & Sentiment Engine (Mar 2026)
- [x] Multi-source aggregation: FMP, Finnhub, Alpha Vantage, Marketaux
- [x] GPT-5.2 powered NLP analysis with catalyst detection
- [x] "Why it matters" AI summaries for each article
- [x] Breaking news / catalyst alerts
- [x] Sentiment overview dashboard
- [x] Article deduplication across sources

### AI Auto-Trade System (Mar 2026)
- [x] Dual-engine: Day Trading + Long-Term Investment classification
- [x] Market Regime Detection (SPY-based)
- [x] Confidence Scoring Engine (weighted multi-factor)
- [x] Risk Manager (daily loss, drawdown, sector concentration, cooldown)
- [x] Position Sizer (confidence-based, stop-distance aware)
- [x] AI Explainability (entry/exit reasons, key indicators)
- [x] 83+ risky/meme stocks blocklist

### Auto-Trade Scheduler (Mar 30, 2026)
- [x] Background scheduler with dual-engine scan intervals
- [x] Day Trading: configurable interval (default 5 min)
- [x] Long-Term: configurable interval (default 30 min)
- [x] Market Session Detection (pre-market, regular, closing, after-hours, closed)
- [x] Session-specific risk multipliers (closing: 50%, pre/after: 30%)
- [x] Deployment Stages: Paper -> Shadow -> Limited Live -> Full Live
- [x] Safety Controls:
  - Max daily loss cutoff
  - Max portfolio drawdown cutoff
  - Consecutive loss cooldown
  - API failure auto-pause
  - Live mode confidence boost
  - Live mode position size reduction
- [x] Emergency Stop (always visible and working)
- [x] Notification System (trade opened/closed, SL/TP hit, paused, emergency)
- [x] Execution Logging
- [x] Pre-market/After-hours execution toggles
- [x] Dashboard: countdown timers, status badges, risk limits, last execution summary

## Pending / Future Tasks
- [ ] Event-driven triggers (breaking news, volume spikes, earnings releases) - P2
- [ ] Compare stocks side-by-side - P2
- [ ] server.py refactoring (4,600+ lines) - P3

## Key Files
- `/app/backend/server.py` - Main API routes
- `/app/backend/ai_trading_system.py` - Dual-engine trading logic
- `/app/backend/auto_trade_scheduler.py` - Scheduler system
- `/app/backend/news_sentiment_engine.py` - Multi-source news + GPT-5.2
- `/app/backend/enhanced_investment_engine.py` - Investment scoring
- `/app/frontend/src/pages/AutoTrade.jsx` - Scheduler dashboard UI
- `/app/frontend/src/pages/News.jsx` - AI news page
