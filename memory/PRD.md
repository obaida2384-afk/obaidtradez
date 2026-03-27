# AlphaLens - AI-Powered Investment Research Platform

## Original Problem Statement
Build a production-style web app and chatbot for stock investing and trading idea generation. An AI-powered investment research assistant that helps discover publicly traded companies that may be attractive to invest in or trade. Combines historical price data, technical indicators, company fundamentals, valuation multiples, news sentiment, and strategy-based filters.

## Architecture
- **Frontend**: React + Tailwind CSS + Recharts
- **Backend**: FastAPI + Python
- **Database**: MongoDB
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key
- **Data**: Financial Modeling Prep (FMP) API

## User Personas
1. **Retail Investor**: Wants screened stock ideas with clear reasoning
2. **Student/Learner**: Needs educational explanations of financial concepts
3. **Active Trader**: Seeks momentum and swing trade candidates

## Core Requirements (Static)
- Multi-factor stock scoring (0-100)
- Strategy-based rankings (Value, Growth, Momentum, Swing)
- Bull/Bear case analysis for each stock
- Real-time stock data from FMP
- AI chatbot with grounded financial reasoning
- Professional dark mode dashboard UI

## What's Been Implemented ✓
- [x] Dashboard with top recommendations (Jan 2026)
- [x] Stock analysis with 7-factor scoring (Jan 2026)
- [x] Strategy rankings (Value, Growth, Momentum, Quality) (Jan 2026)
- [x] Stock screener with filters (Jan 2026)
- [x] AI Chat with investment research assistant (Jan 2026)
- [x] Stock detail page with charts, valuation, financials, technicals (Jan 2026)
- [x] Real FMP data integration (Jan 2026)
- [x] Search functionality (Jan 2026)

## Prioritized Backlog

### P0 (Critical)
- All core features implemented ✓

### P1 (High Priority)
- [ ] Watchlist with saved stocks
- [ ] Alerts for price/score changes
- [ ] Compare stocks side-by-side
- [ ] News sentiment integration

### P2 (Medium Priority)
- [ ] Backtesting for strategies
- [ ] Portfolio idea mode
- [ ] Earnings calendar
- [ ] Sector heatmap

### P3 (Nice to Have)
- [ ] Export to CSV/PDF
- [ ] Research notes per stock
- [ ] Economic calendar
- [ ] Market regime detection

## Next Action Items
1. Watchlist feature with saved stocks
2. Alerts for score thresholds
3. Compare page for side-by-side analysis
4. Enhanced news sentiment from FMP
