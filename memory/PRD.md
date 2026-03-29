# ObaidTradez - AI Trading & Investing Platform

## Original Problem Statement
Build "ObaidTradez" - a secure, dark-themed AI trading and investing platform with:
1. **Mandatory access code gate**: `Bullishalmarkhan7.7` (No public access, backend validation)
2. **Two-mode platform**: Trading (short-term, momentum, technicals) and Investments (long-term, fundamentals, DCF)
3. **Left sidebar tabs**: Dashboard, Trading, Investments, Chatbot, Screener, News & Sentiment, Backtesting, Portfolio, Alerts, Auto Trade, Settings
4. **Multiple external APIs**: Alpaca (paper trading), Polygon, Finnhub, FMP, Alpha Vantage, NewsAPI
5. **Strict Risk Management layer** and **AI chatbot with GPT-5.2**
6. **Broad market coverage**: Investment universe of 350+ stocks across all sectors

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + Python
- **Database**: MongoDB (for chat history, access logs, investment signals cache)
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Data**: Multi-provider (FMP, Polygon, Finnhub, Alpha Vantage, NewsAPI)
- **Trading**: Alpaca Paper Trading API

## User Personas
1. **Short-term Trader**: Momentum, breakouts, volume-based signals
2. **Long-term Investor**: Value investing, fundamental analysis, DCF
3. **Mixed**: Uses both approaches based on market conditions

## What's Been Implemented ✓

### Phase 1 - Core Platform (Dec 2025)
- [x] Secure access gate with code validation
- [x] Dashboard with dual-mode signals overview
- [x] **Trading page ENHANCED (Quality Engine)**:
  - Selective signal generation (max 15/day, quality over quantity)
  - Strict confluence requirements (momentum + volume + structure)
  - Quality filters: Min volume 500K, Min ATR 1.5%, Min R:R 2.0:1
  - Clear trade setup: Entry zone, Stop-loss, Take-profit, R:R ratio
  - **Top Trades Today** section with top 3-5 ranked setups
  - **Diagnostics Panel** showing exclusions and filters applied
- [x] AI Chatbot with 3 modes: Trading, Investing, General (GPT-5.2)
- [x] News & Sentiment page with filtering
- [x] Stock Screener with trading/investing mode toggle
- [x] Backtesting page (simulated results)
- [x] Portfolio page with Alpaca integration
- [x] Alerts page (local state)
- [x] Auto Trade/Invest configuration page
- [x] Settings page with risk management
- [x] 11 sidebar navigation tabs

### Phase 2 - Broad Universe Coverage (Dec 2025)
- [x] **350+ stock universe** covering all major sectors
- [x] **Investment signals caching** in MongoDB (271 stocks analyzed)
- [x] **Browse All tab** with pagination (10 pages, 30 stocks/page)
- [x] **Advanced filtering**: Market cap, Sector, Signal type, Score thresholds
- [x] **Category tabs**: Hot, Bullish, Undervalued, Watch, Bearish
- [x] **Background refresh** for universe scanning
- [x] **Data completeness indicators** for stocks with incomplete data
- [x] **Sector coverage**: Technology, Healthcare, Financials, Consumer, Energy, Industrials, Materials, Utilities, Real Estate, Communications

### Phase 2.5 - Investment Explainability UI (Dec 2025)
- [x] **Score Breakdown Section**: 5 visual bars (Valuation, Quality, Growth, Strength, Risk)
- [x] **Valuation Summary**: P/E Ratio, EV/EBITDA, Fair Value, Classification
- [x] **Business Quality**: ROE, Net Margin, Gross Margin, Quality Rating
- [x] **Growth Profile**: Revenue Growth, EPS Growth, Trend, Rating
- [x] **Score Drivers**: Boosters, Detractors, Biggest Weakness
- [x] **Bull Case**: Bullet points showing investment strengths
- [x] **Bear Case**: Bullet points showing investment concerns (conditional)
- [x] **Key Risks**: Badges showing risk factors (conditional)
- [x] **AI Analysis**: GPT-generated summary text
- [x] **Percentile Rank**: Top X% ranking indicator
- [x] **Dynamic thresholding**: Percentile-based category assignment

### Phase 3 - Risk Management, Backtesting & Alerts (Dec 2025)
- [x] **Risk Management Engine**:
  - Position Size Calculator (shares, position value, risk amount based on stop-loss)
  - Risk/Reward Calculator (ratio display, quality rating: Excellent/Good/Fair/Poor)
  - Risk Settings (max position, max daily/weekly loss, max drawdown, stop-loss/take-profit defaults)
  - Daily Risk Status (account value, daily P&L, can_trade flag - gracefully handles Alpaca 401)
- [x] **Backtesting Tab**:
  - 5 strategies: Momentum, Mean Reversion, Breakout, MA Crossover, Value
  - Time periods: 3m, 6m, 1y, 2y, 5y
  - Real historical data from FMP API
  - Results: Total Return, Final Value, Max Drawdown, Sharpe Ratio, Win Rate
  - Equity Curve visualization
  - Trade Log (last 10 trades with entry/exit and P&L)
  - Backtest History persistence
- [x] **Alerts Tab**:
  - 4 alert types: Price Above, Price Below, % Change, Volume Spike
  - MongoDB persistence
  - Real-time price checking via FMP API
  - Trigger detection with timestamp and message
  - Alert History log
  - Reset functionality for triggered alerts

### Phase 4 - Watchlist (Dec 2025)
- [x] **Watchlist Page**:
  - New sidebar tab with Star icon
  - Stats cards: Total Stocks, Bullish, Bearish, Avg Score
  - Quick add symbol input
  - Filter/search watchlist
  - Refresh All and Clear All bulk actions
- [x] **Watchlist Cards**:
  - Symbol, Name, Price, Change %, Signal, Category, Score
  - Upside, Confidence, Sector
  - Added date and source badge (manual/trading/investments)
  - Inline note editing
  - Individual remove button
- [x] **Star Icon Integration**:
  - Star button on Investment cards
  - Star button on Trading cards
  - Click to add/remove from watchlist
  - Toast notifications
  - MongoDB persistence across sessions

### Phase 5 - Portfolio Performance Charts (Dec 2025)
- [x] **Portfolio Analytics Page**:
  - Header with period selector (1D, 1W, 1M, 3M, 1Y, ALL)
  - Account Summary cards (Equity, Day P&L, Cash, Buying Power)
  - Win Rate summary row
- [x] **Charts**:
  - Equity Chart (AreaChart with gradient)
  - Drawdown Chart (AreaChart, red theme)
  - Win Rate Trend (LineChart with 50% baseline)
  - Strategy Performance (BarChart from backtests)
  - Sector Allocation (PieChart with legend)
- [x] **P&L Breakdown**:
  - Realized vs Unrealized P&L
  - Total P&L
  - Avg Trade Return
  - Best/Worst Trade display
- [x] **Data Sources**:
  - Alpaca positions and trade history
  - MongoDB backtest history
  - Graceful handling of Alpaca 401

### Phase 6 - Paper Execution (Dec 2025)
- [x] **Paper Trading Only**:
  - Uses Alpaca Paper account only
  - Live trading disabled
  - "Paper Trading Only" badge in UI
- [x] **Safety Controls (Defaults)**:
  - Kill Switch: OFF
  - Manual Approval Required: ON
  - Auto Execution: OFF
  - Block Extended Hours: ON (regular market hours only by default)
  - Max Position Size: 5%
  - Cash Buffer: 10%
  - Min Confidence: 60%
  - Max Daily Loss: 2%
- [x] **Market Hours Controls**:
  - Real-time market status display (Open, Pre-Market, After-Hours, Closed)
  - Clear warning banner when outside regular hours
  - "Allow Extended Hours Trading" toggle for pre-market (4AM-9:30AM ET) and after-hours (4PM-8PM ET)
  - Descriptive error messages when trades blocked by market hours
  - Regular market hours (9:30 AM - 4:00 PM ET) enforced by default
- [x] **Order Workflow**:
  - Queue trades for review
  - Approve / Reject / Cancel actions
  - Status tracking: pending → approved → executed/rejected/failed
  - Execute only approved trades
- [x] **Trade Logs & Audit Trail**:
  - Symbol, side, qty, reason, strategy, confidence
  - Entry, stop-loss, take-profit prices
  - Alpaca order ID when executed
  - Status history with timestamps
  - Full audit log of all actions
- [x] **Risk Controls Before Execution**:
  - Kill switch check
  - Position size limit
  - Cash buffer enforcement
  - Confidence threshold check
  - Extended hours block
  - Daily loss limit check
- [x] **UI**:
  - Account stats (Buying Power, Cash, counts)
  - Safety Controls section with toggles/sliders
  - Queue New Trade form
  - Tabs: Queue, Executed, Positions, Audit Log
  - Trade cards with action buttons

### Phase 7 - Real-time Price Streaming (Dec 2025)
- [x] **Backend Price Service**:
  - LivePriceService class with 5s cache TTL
  - Batch quote fetching via FMP stable API
  - Parallel requests for multiple symbols (10 at a time)
  - Rate limiting (0.1s delay between batches)
- [x] **Price Endpoints**:
  - POST /api/prices/batch - Get prices for up to 100 symbols
  - GET /api/prices/{symbol} - Get single symbol price
  - GET /api/prices/watchlist - Get prices for watchlist symbols
  - GET /api/prices/positions - Get prices for position symbols
- [x] **Frontend Hooks**:
  - useLivePrices(symbols, interval, enabled) - Custom hook for any symbol list
  - useWatchlistPrices(interval, enabled) - Hook for watchlist prices
  - usePositionsPrices(interval, enabled) - Hook for position prices
  - LiveIndicator component (green animated dot)
- [x] **Page Integrations**:
  - Trading: 12s updates, memoized TradingCard
  - Investments: 20s updates, 30 symbols max, memoized InvestmentCard
  - Watchlist: 15s updates
  - Portfolio: 15s updates for positions
  - AutoTrade: 12s for queue, 15s for positions
- [x] **Performance Optimizations**:
  - React.memo on all card components
  - useMemo for visible symbols calculation
  - Flash effects on price changes (green/red highlight)
  - Throttled updates prevent API overload

## API Endpoints

### Live Prices (NEW)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/prices/batch` | POST | Get live prices for multiple symbols (max 100) |
| `/api/prices/{symbol}` | GET | Get live price for single symbol |
| `/api/prices/watchlist` | GET | Get live prices for watchlist symbols |
| `/api/prices/positions` | GET | Get live prices for position symbols |

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/access` | POST | Verify access code, return token |
| `/api/auth/verify` | GET | Verify token validity |

### Investments (Enhanced)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/investments/browse` | GET | Paginated browse with filters |
| `/api/investments/filters` | GET | Available filter options |
| `/api/investments/refresh` | POST | Trigger background scan |
| `/api/investments/scan` | GET | Categorized signals overview |
| `/api/investments/analyze/{symbol}` | GET | Deep analysis for single stock |

### Trading
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trading/scan` | GET | Scan trading opportunities |
| `/api/trading/analyze/{symbol}` | GET | Analyze for trading |

### Other
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | AI chatbot |
| `/api/news/market` | GET | Market news |
| `/api/news/{symbol}` | GET | Symbol-specific news |
| `/api/account` | GET | Alpaca account |
| `/api/positions` | GET | Current positions |
| `/api/universe/stats` | GET | Universe statistics |

### Risk Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/risk/position-size` | POST | Calculate optimal position size |
| `/api/risk/risk-reward` | POST | Calculate risk/reward ratio |
| `/api/risk/settings` | GET/POST | Get/save risk settings |
| `/api/risk/daily-status` | GET | Daily risk status with P&L |

### Backtesting
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/backtest/run` | POST | Run a backtest simulation |
| `/api/backtest/history` | GET | Get backtest history |
| `/api/backtest/strategies` | GET | List available strategies |

### Alerts
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts` | GET/POST | List/create alerts |
| `/api/alerts/{id}` | PUT/DELETE | Update/delete alert |
| `/api/alerts/check` | GET | Check all alerts vs real prices |
| `/api/alerts/history` | GET | Get triggered alert history |
| `/api/alerts/{id}/reset` | POST | Reset a triggered alert |
| `/api/alerts/types` | GET | List available alert types |

### Watchlist
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/watchlist` | GET | List all watchlist items with enriched data |
| `/api/watchlist` | POST | Add stock to watchlist |
| `/api/watchlist/{symbol}` | DELETE | Remove stock from watchlist |
| `/api/watchlist/check/{symbol}` | GET | Check if symbol is in watchlist |
| `/api/watchlist/refresh` | POST | Refresh all watchlist prices |
| `/api/watchlist/all` | DELETE | Clear entire watchlist |
| `/api/watchlist/{symbol}/note` | PUT | Update note for a stock |

### Portfolio Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/portfolio/analytics` | GET | Comprehensive analytics (all data) |
| `/api/portfolio/history` | GET | Portfolio equity history |
| `/api/portfolio/drawdown` | GET | Drawdown analysis |
| `/api/portfolio/win-rate` | GET | Win rate trends |
| `/api/portfolio/sector-allocation` | GET | Sector allocation |
| `/api/portfolio/pnl-breakdown` | GET | P&L breakdown |
| `/api/portfolio/strategy-performance` | GET | Strategy performance from backtests |

### Paper Execution
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/paper/settings` | GET/POST | Get/update execution settings |
| `/api/paper/kill-switch` | GET/POST | Get/toggle kill switch |
| `/api/paper/market-status` | GET | Get current market status and trading availability |
| `/api/paper/queue` | GET/POST | Get trade queue / queue new trade |
| `/api/paper/trade/{id}` | GET | Get specific trade |
| `/api/paper/trade/{id}/approve` | POST | Approve pending trade |
| `/api/paper/trade/{id}/reject` | POST | Reject pending trade |
| `/api/paper/trade/{id}/cancel` | POST | Cancel trade |
| `/api/paper/trade/{id}/execute` | POST | Execute approved trade |
| `/api/paper/risk-check` | POST | Check risk controls for trade |
| `/api/paper/audit` | GET | Get audit log |
| `/api/paper/stats` | GET | Get execution statistics |

## Prioritized Backlog

### P0 (Critical) - COMPLETE ✓
- All 11 sidebar tabs implemented
- Access gate working
- Dual-mode trading/investing signals
- AI chatbot functional
- Broad market coverage (271 stocks)

### P1 (High Priority)
- [x] Real backtesting with historical data ✓
- [x] Persistent alerts with MongoDB storage ✓
- [x] Risk Management engine ✓
- [x] Watchlist with saved stocks ✓
- [x] Portfolio performance charts ✓
- [x] Alpaca paper execution (with manual approval, kill switch) ✓
- [x] Real-time price streaming for all views ✓

### Phase 8 - Performance Optimization (Mar 2026)
- [x] **Stock Universe Expansion**:
  - ~1,400 unique stock symbols across all sectors
  - 60+ high-volatility day trading stocks (GME, AMC, MARA, RIOT, etc.)
  - 30+ leveraged ETFs (TQQQ, SQQQ, SOXL, SOXS, LABU, LABD, etc.)
  - Meme stocks, biotech runners, SPACs, crypto-related stocks
  - **1,097 stocks currently analyzed and cached**
- [x] **News Sentiment Integration**:
  - FMP News API integration (primary source)
  - Finnhub and Polygon news fallback
  - Sentiment scoring with positive/negative word analysis
  - Sentiment impact score (-10 to +10) adjusts confidence
  - Trading signals include news_sentiment, news_impact, news_headlines
  - UI displays "News: Bullish/Bearish/Slightly Positive/Negative (+/-X)" badges
  - Recent headlines section under each trading signal
- [x] **Auto Trade Safety Controls**:
  - **83 risky stocks blocked** from auto-trading
  - Categories: Meme stocks, leveraged ETFs, SPACs, crypto-related, EV SPACs, biotech runners
  - New endpoints: `/api/paper/risky-stocks`, `/api/paper/check-symbol/{symbol}`
  - UI shows warning when entering risky stock in Quick Trade form
  - Button changes to "Queue (Will Block)" for risky stocks

### P2 (Medium Priority)
- [ ] Custom screener presets
- [ ] Email notifications
- [ ] Compare stocks side-by-side

### P3 (Nice to Have)
- [ ] Export portfolio/trades to CSV
- [ ] Mobile-responsive sidebar collapse
- [ ] Dark/light theme toggle
- [ ] Multi-language support

## Test Status
- Backend: 100% (All endpoints working - iteration_13)
- Frontend: 100% (All features working, tested Mar 2026)
- Trading Signals (Quality Engine): 100% - selective signals with R:R > 2.0
- Trading News Sentiment: 100% - news_sentiment, news_impact, news_headlines fields verified
- Investment Engine: 100% - **1,097 stocks** analyzed across all categories:
  - Hot: 165 stocks
  - Bullish: 286 stocks
  - Undervalued: 53 stocks
  - Watch: 481 stocks
  - Bearish: 112 stocks (combined with Overpriced)
- Investment Explainability UI: 100%
- Risk Management: 100%
- Backtesting: 100%
- Alerts: 100%
- Watchlist: 100%
- Portfolio Analytics: 100%
- Paper Execution: 100% - **83 risky stocks blocked** (meme, leveraged ETFs, SPACs)
- Auto Trade Recommended Tab: 100% - Shows only safe, high-quality stocks
  - New endpoints: `/api/paper/safe-stocks`, `/api/paper/recommended-trades`
- Real-time Price Streaming: 100%
- News Sentiment: 100%
- Stock Universe: **1,097 stocks** across all tabs
- Risky Stocks Filter: **83 high-risk stocks blocked**
- Access Code: `Bullishalmarkhan7.7`

## Notes
- Category tabs working correctly: Hot (15), Bullish (15), Undervalued (15), Watch (15), Bearish (20)
- FMP API rate limits may cause some stocks to have incomplete data (<80% completeness)
- Investment signals are cached in MongoDB and refreshed on demand
- Background refresh processes stocks in batches of 10 with 0.5s delays
- Conditional sections (Bear Case, Key Risks, Score Detractors) only appear when data is available
- Alpaca API returns 401 (invalid keys) - gracefully handled with "Connect Alpaca" message
- Risk settings, backtest history, and alerts persist to MongoDB
