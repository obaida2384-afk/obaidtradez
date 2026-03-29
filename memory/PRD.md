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
- [x] Trading page with signal categories (Hot, Breakout, Momentum, High Volume, Avoid)
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

## API Endpoints

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
- [ ] Portfolio performance charts
- [ ] Live Alpaca paper execution

### P2 (Medium Priority)
- [ ] Real-time price streaming for Investment cards
- [ ] Custom screener presets
- [ ] Email notifications
- [ ] Compare stocks side-by-side

### P3 (Nice to Have)
- [ ] Export portfolio/trades to CSV
- [ ] Mobile-responsive sidebar collapse
- [ ] Dark/light theme toggle
- [ ] Multi-language support

## Test Status
- Backend: 100% (All endpoints working - iteration_6)
- Frontend: 100% (All features working, tested Dec 2025)
- Investment Explainability UI: 100% (21/21 tests passed - iteration_4)
- Risk Management: 100% (Position Size, Risk/Reward calculators working)
- Backtesting: 100% (Real FMP historical data, 5 strategies)
- Alerts: 100% (CRUD, Check Now, History, Reset - MongoDB persistence)
- Watchlist: 100% (18/18 tests passed - iteration_6)
- Investment Universe: 271 stocks cached from 350+ stock universe
- Access Code: `Bullishalmarkhan7.7`

## Notes
- Category tabs working correctly: Hot (15), Bullish (15), Undervalued (15), Watch (15), Bearish (20)
- FMP API rate limits may cause some stocks to have incomplete data (<80% completeness)
- Investment signals are cached in MongoDB and refreshed on demand
- Background refresh processes stocks in batches of 10 with 0.5s delays
- Conditional sections (Bear Case, Key Risks, Score Detractors) only appear when data is available
- Alpaca API returns 401 (invalid keys) - gracefully handled with "Connect Alpaca" message
- Risk settings, backtest history, and alerts persist to MongoDB
