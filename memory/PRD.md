# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Build "ObaidTradez" - a secure, dark-themed AI trading and investing platform with access code gate, dual-mode Trading/Investments, 1,400+ stock universe, autonomous dual-engine auto-trading (Day Trade + Long-Term), and AI-powered news catalyst engine.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + Python
- **Database**: MongoDB
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Data**: FMP, Finnhub, Alpha Vantage, Marketaux
- **Trading**: Alpaca Paper Trading API

## Implemented Features

### Core Platform
- [x] Secure access gate (Bullishalmarkhan7.7)
- [x] Dashboard, Trading, Investments, Chatbot, Screener, News, Backtesting, Portfolio, Alerts, Auto Trade, Settings
- [x] Mobile-responsive hamburger sidebar

### Investment Engine
- [x] 1,400+ stock universe with background batching
- [x] 30-year historical performance (CAGR, Max Drawdown)
- [x] Decision Clarity UI, Screener Presets, CSV Export

### AI Auto-Trade System (Phase 1 Upgrade - Mar 30, 2026)
- [x] **Dynamic Confidence Thresholds**: Regime-adaptive (DT default 80, LT default 75)
  - Bearish/Neutral Bearish: +8 DT, +6 LT
  - High Volatility: +5 DT, +3 LT
  - Bullish: -5 DT, -4 LT (floors: DT=70, LT=65)
  - Post-cooldown boost: +5
  - Soft lock at 80% daily loss: +5
- [x] **Enhanced PositionSizer**: Regime scaling (-50% bearish, -40% high vol), confidence-near-threshold reduction (60% size if margin ≤5), caps (DT max 5%, LT max 20%)
- [x] **DayTradingEngine Catalyst Gate**: Requires strong catalyst OR (technical breakout + volume + sentiment), blocks weak/conflicting sentiment
- [x] **LongTermEngine Quality Filters**: Rejects weak revenue, poor FCF, excessive debt (D/E>2), value traps, cyclical sectors in bearish regime
- [x] **Trade Pipeline Funnel**: Universe → Liquidity → Technical → Catalyst → Confidence → Risk → Executed (with bottleneck detection)
- [x] **Zero-Trade Diagnostics**: Reasons, near-miss candidates (confidence within 12 of threshold), opportunity quality indicator (HIGH/MEDIUM/LOW)
- [x] **TradeFrequencyController**: Max 3 DT/hour, 1 LT/hour, reduced in weak regime, paused after 3 consecutive losses
- [x] **DynamicThresholdManager**: Risk modes (NORMAL/CAUTIOUS/DEFENSIVE), max positions reduction in bearish

### News & Catalyst Engine (Phase 3 Upgrade - Mar 30, 2026)
- [x] **Large-scale ingestion**: 80+ articles per stock from FMP, Finnhub, Alpha Vantage, Marketaux
- [x] **Multi-layer filtering**: Relevance → Dedup → Source Quality → Signal Extraction
- [x] **Catalyst Strength Scoring (0-100)**: Weighted combination of AI strength, type weight, sentiment, velocity
- [x] **Trade-oriented categories**: HOT (trade candidate), BULLISH, BEARISH, WATCHLIST, IGNORE
- [x] **News Velocity Detection**: 24h/4h article counts, source diversity, trend (accelerating/steady/decelerating)
- [x] **Source credibility weighting**: Reuters/Bloomberg 0.95, CNBC 0.88, Yahoo Finance 0.75, etc.
- [x] **Catalyst types**: earnings_surprise, guidance_change, merger_acquisition, partnership, product_launch, analyst_upgrade/downgrade, regulatory_news, viral_momentum
- [x] **Actionable language**: Replaces "modestly bullish" with "WATCHLIST: moderate signal — NOT tradeable"
- [x] **Trade integration rules**: Only HOT category (catalyst ≥80) or strong technical + volume + sentiment qualifies for DT

### Scheduler Safety (Phase 2 Upgrade - Mar 30, 2026)
- [x] **2 consecutive loss cooldown** (changed from 3)
- [x] **Post-cooldown threshold boost**: +5 after cooldown ends
- [x] **Soft lock at 80% daily loss**: Auto-reduces position sizes by 50%
- [x] **Pre-market/After-hours**: Execution OFF by default
- [x] **Zero-trade handling**: Full-day alerts, diagnostics
- [x] **Deployment stages**: Paper → Shadow → Limited Live → Full Live
- [x] **Emergency stop always visible**

### Frontend Dashboard (Phase 4 - Mar 30, 2026)
- [x] Risk Mode indicator (NORMAL/CAUTIOUS/DEFENSIVE badge)
- [x] Market Condition Adjustment Active banner
- [x] Dynamic Thresholds display (DT/LT values)
- [x] Pipeline Funnel visualization with bottleneck detection
- [x] No-Trade Reason panel with near-miss candidates
- [x] Opportunity Quality indicator
- [x] News: catalyst scores, trade categories, velocity indicators, trade impact tags
- [x] News: filter pipeline stats, velocity details, catalyst explainability

## Pending / Future Tasks
- [ ] Event-driven triggers (breaking news triggers immediate re-evaluation) - P2
- [ ] Compare stocks side-by-side - P2
- [ ] server.py refactoring (4,600+ lines) - P3

## Key Files
- `/app/backend/ai_trading_system.py` - Dual-engine + dynamic thresholds + pipeline funnel
- `/app/backend/auto_trade_scheduler.py` - Scheduler with safety controls
- `/app/backend/news_sentiment_engine.py` - Multi-source news + GPT-5.2 catalyst engine
- `/app/backend/enhanced_investment_engine.py` - Investment scoring
- `/app/backend/server.py` - Main API routes
- `/app/frontend/src/pages/AutoTrade.jsx` - Scheduler + diagnostics dashboard
- `/app/frontend/src/pages/News.jsx` - Catalyst engine UI
