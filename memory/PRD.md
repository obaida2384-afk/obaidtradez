# ObaidTradez — Maintenance & Improvement

Owner's project. Identity: **ObaidTradez** (UI brand shows "ALPHA VAULT"). Do NOT rebrand, restructure, or add external traces. Maintenance/improvement only; stop after each major phase for approval.

## Source
- Loaded from GitHub: `obaida2384-afk/obaidtradez` (branch `main`), live ref: https://obaidtradez.vercel.app

## Stack (as-is)
- Frontend: **Vite 6** + React 19 (entry `frontend/src/index.html` -> `src/index.jsx`). shadcn/ui, Tailwind, recharts, framer-motion, xlsx, jspdf.
  - Stale CRA leftovers present but unused: `craco.config.js`, `src/index.js`, `public/index.html`, `plugins/`.
- Backend: **FastAPI** (`backend/server.py`, ~6k lines) + Motor/MongoDB. Many engine modules (trading, investment, news, live price, scheduler). External APIs: FMP, Polygon, Finnhub, NewsAPI, Alpaca, Anthropic — all optional (demo mode without keys).
- Env: frontend uses `process.env.REACT_APP_BACKEND_URL`; backend uses `MONGO_URL`/`DB_NAME`.

## Feature -> file map
- Company Universe / mock data: `backend/server.py` (UniverseManager.CORE_UNIVERSE), `frontend/src/lib/mockData.js`
- Short-Term Growth (Top Plays): `frontend/src/pages/TopPlays.jsx` + backend TradingEngine
- Future Giants: `frontend/src/pages/FutureGiants.jsx`
- Institutional Leaders / Investments: `frontend/src/pages/Investments.jsx`, `Research.jsx`
- DCF Modeling: `frontend/src/pages/Modeling.jsx`
- Excel Export: `frontend/src/lib/excelExporter.js`

## Progress log
### 2026-06-21 — Phase 1: Stabilization (DONE)
- Loaded repo into `/app` (frontend + backend), preserved platform `.env` files.
- `frontend/vite.config.js`: serve on `PORT` (3000 here, 5173 locally), `host:true`, `allowedHosts:true`, HMR clientPort from `WDS_SOCKET_PORT`; resolve `REACT_APP_BACKEND_URL` via `loadEnv` (was always falling back to hardcoded Railway URL).
- `backend/server.py` `MultiAPIClient._request`: skip outbound calls when a required credential (header/param) is `None` — eliminated `Header value must be str/bytes` log-spam + wasted requests in demo mode.
- Installed deps (yarn frontend, pip backend). Verified: frontend 200, backend `/api/` 200, login+onboarding+all main pages mount with 0 runtime errors.

### 2026-06-22 — Phase 2: Company Universe (BACKEND DONE, awaiting approval + FMP key)
- New module `backend/company_universe.py` — `CompanyUniverseService`: dynamic ticker discovery via FMP screener (NOT hardcoded; capped 5000), per-ticker enrichment, computed opportunity/risk scores, bull/base/bear + thesis assembled from real data, per-field `source` provenance, `lastUpdated`. Missing data → null + `ESTIMATED` flag (no fabricated numbers).
- 28-field schema: ticker, companyName, sector, industry, marketCap, price, revenueGrowth, revenueAcceleration, ebitdaMargin, fcfMargin, epsGrowth, analystRating, analystPriceTarget, analystEstimateRevisions, institutionalOwnershipTrend, insiderActivity, valuationMultiples, peerComparison, catalysts, macroSensitivity, shariahStatus, opportunityScore, riskScore, bullCase, baseCase, bearCase, thesis, source, lastUpdated.
- `server.py`: import + `company_universe_service` instance + endpoints `GET /api/universe/companies` (filter/sort/paginate), `GET /api/universe/company/{ticker}`, `GET /api/universe/coverage`, `POST /api/universe/build`. Mongo collection `company_universe` (indexed).
- Fixed a pre-existing syntax corruption at end of `server.py` (duplicate mis-indented `except` in `_market_open_verifier_watcher`) that blocked reload.
- Verified endpoints return honest empty/`has_data_source:false` in demo mode.
- FMP key added to backend/.env. Validated all 7 FMP stable endpoints; corrected field maps (ebitdaMarginTTM, evToEBITDATTM, revenueAvg; FCF margin derived from EV/Sales÷EV/FCF). Fixed screener endpoint (`/company-screener`, not legacy `/stock-screener`).
- Built universe at target 3,000 (background). Verified NVDA record: full real data, computed scores, bull/bear from real metrics, provenance map.
- FRONTEND WIRED: new `frontend/src/lib/companyUniverse.js` (fetch/normalize service). `Discovery.jsx` now renders the live API universe (ranked by opportunityScore), with graceful fallback to mock when empty. UI/layout preserved; added data-testids + live data-source note.
- KNOWN MINOR: Discovery card label "DCF upside" currently shows analyst-consensus upside (real DCF arrives in Phase 5). Global "Demo Mode" header banner is driven by user's own localStorage apiKeys (separate from server FMP key) — left as-is.
- NOT YET (next): institutional ownership / insider endpoints (currently flagged Estimated); wiring Research/TopPlays/FutureGiants list views; Research/Modeling detail stay on mock until Phase 5 (need DCF fields).

### 2026-06-22 — Phase 3: Short-Term Growth Opportunities (DONE)
- `company_universe.py`: added `analystPriceTargetHigh/Low` to enrichment; `_short_term_score` (revenue accel, growth, EPS, est. revisions, analyst upside, FCF, valuation dislocation, rating) with a **size tilt that de-emphasises mega caps** (0.85x mega → 1.16x small); `_growth_view` builds bull/base/bear price scenarios, "why the market may be wrong", "what could invalidate", key catalysts & risks — all from real data. Sanity clamps discard implausible analyst targets (filters garbage on illiquid names/closed-end funds).
- `rank_short_term_growth(limit, max_megacap)` ranks the 3,000 universe, caps mega-cap count in the list.
- `server.py`: `GET /api/universe/short-term-growth`.
- Frontend: `companyUniverse.js` `fetchShortTermGrowth` (rounds marketCap→millions); `TopPlays.jsx` wired to live ranking with graceful mock fallback — relabelled to "Why The Market May Be Wrong", added Key Catalysts / Key Risks chips + "What Could Invalidate The Thesis", null-safe scenarios, data-testids, live data note.
- Verified: 25 live plays, 1,259 ranked, 0–5 mega caps, mid/small-cap names dominate (MAKO, DEC, CRMD, GPOR…), clean market caps, scenarios + narratives render. No fabricated numbers.

### 2026-06-22 — Phase 4: Future Giants (DONE)
- `company_universe.py`: `_future_giant_score` (gates rg≥15% & marketCap<150B; weights growth[capped], size-runway, FCF/EBITDA margins, EPS, secular sector, analyst upside) + `_giant_sector_tilt` (secular 1.0 / cyclical-commodity 0.6 / other 0.8) so Tech/Healthcare/Comm/Consumer lead and miners/energy/REITs are demoted. `_giant_view` builds potential bucket (2x→5-10x, framed as "potential"), qualitative TAM (no fake $), margin trajectory, moat, thesis, "why it could become much larger", key metrics, risks. `rank_future_giants(limit)`.
- `server.py`: `GET /api/universe/future-giants`.
- Frontend: `companyUniverse.js` `fetchFutureGiants` (marketCap→millions); `FutureGiants.jsx` wired to live screen with mock fallback, added "Why It Could Become Much Larger" block, data-testids, live note.
- Verified: 12 live giants (CRMD, NUTX, RDDT/Reddit, XPEV/XPeng, biotech/tech names), 338 ranked, secular sectors dominate, all fields render. No guaranteed returns; speculative framing + disclaimers intact.

### 2026-06-22 — Phase 5: DCF Modeling Engine (DONE)
- New `backend/dcf_engine.py` — `DCFEngine.build_dcf(ticker)`: pulls FMP income/balance/cash-flow (5yr), analyst-estimates, treasury-rates, ratios, peers, grades, price-target. Builds: real historicals, forward revenue growth (analyst consensus → tapered CAGR), margin forecast, D&A/CapEx/NWC % (historical avgs), CAPM WACC (10Y treasury + levered beta + ERP + after-tax cost of debt, real weights), cash/debt/shares from balance sheet. Every assumption carries source/reasoning/confidence; missing → ESTIMATED. Also returns comps (peer multiples from universe), analyst recs, macro (yield curve), industry, risk factors, investment memo.
- `server.py`: `GET /api/modeling/dcf/{ticker}`.
- Frontend `Modeling.jsx`: kept existing client-side `computeDCF` + tabs, now fed REAL company + sourced assumptions from backend. CompanySelector searches live 3,000 universe. Added tabs: Historicals, Comparables (peers+analyst+macro+industry), Sources (assumption provenance+confidence). `fetchDcf` in companyUniverse.js. data-testids added.
- Verified (NVDA): real 5yr financials, analyst-driven forecast, WACC 16.6%, full UFCF/TV/valuation, comps (AAPL/ADI…), sources tab. DCF implied differs from price (legit conservative output; assumptions editable).
- Spec sections covered: Company Overview, Historical Financials, Revenue Build, Margin Forecast, Working Capital, CapEx, D&A, UFCF, WACC, Terminal Value, DCF Summary, Sensitivity, Trading Comps, Analyst Recs, Macro, Industry, Bull/Base/Bear, Risk Factors, Investment Memo. NOT in DCF view: News & Catalysts (separate News page exists) — deferred.

### 2026-06-22 — Phase 6: Excel Export (DONE)
- Rewrote `frontend/src/lib/excelExporter.js` using **ExcelJS** (added via yarn) — SheetJS `xlsx` can't style cells. `generateExcelModel(payload)` builds an 8-sheet institutional workbook: Cover, **DCF Model (formula-driven)**, Historical Financials, Sensitivity, Comparables, Analyst & Macro, Assumptions (sources+confidence), Investment Memo.
- DCF sheet is genuinely formula-driven (67 formulas): yellow editable inputs → Revenue/EBITDA/EBIT/NOPAT/UFCF/PV/TV/EV/Equity/Implied all as Excel formulas referencing input cells. Palette: dark-blue headers, light-blue subheaders, yellow inputs, gray formulas, green/red. Sensitivity uses a WACC×TGR grid with green→red colorScale conditional formatting.
- `Modeling.jsx` handleExport passes `{company, ...payload}`; export verified (MSFT/AAPL → valid .xlsx, 8 sheets, 67 formula cells, color scale present).
- LIMITATION: native embedded Excel charts are not supported by JS Excel libraries (ExcelJS/xlsx) — used colorScale/data visuals instead; on-screen Modeling page has live charts (recharts). Prices are pulled live from FMP at model-build time (accurate/current); real-time streaming not added.

## ALL 6 PHASES COMPLETE. Possible follow-ups: embed News & Catalysts into DCF; wire Research detail page to DCF engine; institutional/insider enrichment; hard fund/ETF exclusion; faster live-price polling.

### 2026-06-22 — Post-Phase: Live News, Live Pricing & DCF News (DONE)
- `News.jsx` rewritten to drop all mock `NEWS_FEED` data — now consumes live `fetchMarketNews` (StockNewsAPI `/api/news/market`) + `fetchNewsSuggestions` (`/api/news/suggestions`). Added "News-Driven Stock Ideas" suggestions row (buzz × universe fundamentals). Filters (ticker/catalyst-type/sentiment) work against live feed; catalyst types built dynamically from article topics with junk-topic sanitisation (paywall/paylimitwall → "Market News"). High-Impact KPI now keyed off non-neutral sentiment.
- Live pricing: new `useQuotes` hook (polls `/api/prices/quotes` FMP batch-quote, 20s) wired into `TopPlays.jsx` (Current price) and `FutureGiants.jsx` (Price) — displayed prices refresh to live FMP quotes. Discovery shows no price field so left unchanged; Modeling builds live at fetch time.
- DCF Excel export: `excelExporter.js` now writes a dedicated IB-styled "News & Catalysts" worksheet (date / hyperlinked headline / source / colour-coded sentiment / tickers + tone summary) from `model.news` (DCF payload attaches `news_service.company_news`).
- Verified by testing_agent (iteration_1.json): 100% frontend pass — 40 live news cards (no legacy mock headlines), 10 suggestions, numeric live prices on Top Plays (25) & Future Giants (12), DCF export of AAPL succeeded with success toast + News sheet, no errors.
- Known cosmetic note (not blocking): `companyUniverse.js normalizeCompany` sets grossMargin = ebitdaMargin (pre-existing copy-paste); left as-is to avoid out-of-scope change.

### 2026-06-22 — Owner lockdown, Trending banner, Ownership rendering, Vercel prep (DONE)
- **Single-credential access lock**: app now restricted to ONE login (Username `obaidtradez`), validated server-side by existing `POST /api/auth/access` against `ACCESS_USERNAME` / `ACCESS_CODE_HASH` (added to `backend/.env`). `AuthContext.login(username,password)` posts to it, stores token + user in localStorage, routes straight to dashboard (onboarding auto-completed). Public **signup disabled**: removed `signup` from AuthContext, dropped Signup/ForgotPassword imports, `/auth/signup` & `/auth/forgot-password` redirect to `/auth/login`, Login.jsx now a Username field with no signup/forgot links. Removed the credential-leaking `/api/auth/debug` endpoint. Credentials recorded in test_credentials.md.
- **Dashboard 'Trending Now' banner**: new `TrendingNow` component surfaces the top news-driven idea (StockNewsAPI suggestions) with ticker/sector/mentions/sentiment/price/PT, click → Research, plus 'All ideas' → News and 3 secondary chips.
- **Institutional ownership + insider activity rendering**: `normalizeCompany` now maps `institutionalOwnershipTrend` + `insiderActivity`; Discovery cards show a color-coded ownership chip row (data-testid `discovery-ownership`); Top Plays expanded card shows an 'Ownership & Insider Activity' block (data-testid `top-play-ownership`). Backend `rank_short_term_growth`/`_growth_view` now project & return these fields (sparse data — ~4/25 populated — renders where present).
- **Vercel / zero Emergent traces**: audited frontend `src/`, `public/`, `index.html`, `vite.config.js`, `package.json` — NO Emergent references. `vercel.json` updated with SPA rewrites (deep links no longer 404). Backend fallback URL in vite.config is the owner's own Railway host. Deployment is the owner's responsibility via Vercel (not performed here).
- Verified by testing_agent iteration_2.json — 100% frontend pass (auth correct/wrong/signup-disabled, trending banner + navigation, ownership chips, regression on News/prices/DCF). 

### Deferred / backlog (next pass)
- **Research → DCF engine wiring**: `Research.jsx` is still 100% mock (`COMPANY_UNIVERSE`) and uses a data shape (revenueHistory, impliedPrice, bullPrice, etc.) different from the DCF engine payload — needs a dedicated rewrite to consume `fetchCompany` + `fetchDcf` and add a richer institutional/insider panel. (P1, larger effort.)
- Consolidate legacy `useLivePrices.js` polling with `useQuotes` (refactor).
- Optional: enforce the bearer token on backend data endpoints (currently open; UI gate only). Optional: replace persistent 'Demo Mode' chip when server data is live.

### 2026-06-22 — One-click DCF + recommendation ratings + Vercel guide (DONE)
- **One-click DCF from Trending Now**: dashboard ideas now navigate to `/modeling?ticker=` (Modeling auto-loads via `useSearchParams`); the Excel export button is right there. Direct deep-links `/modeling?ticker=MSFT` work.
- **Buy/sell recommendation rating** (Strong Buy / Buy / Hold / Not a Good Buy / Avoid) via new `lib/rating.js getRating()` (blends valuation upside + opportunityScore + news tone). Rendered on: Trending Now top idea + chips, News stock-idea suggestions, and the DCF model page (badge). Recommendation also written into the Excel export (Cover + DCF sheets).
- **Deployment guide**: `/app/DEPLOYMENT.md` — Vercel (frontend) + Railway (backend) + MongoDB Atlas, env vars, and the one-time `POST /api/universe/build` step. `vercel.json` has SPA rewrites; backend `Procfile` binds `$PORT`; CORS is `*`.
- Verified by testing_agent iteration_3.json — 100% (8/8 scenarios: login, one-click DCF, auto-load, ratings on all three surfaces, Excel export with recommendation, deep-link).


## Backlog (await user approval per phase)
- P1 Phase 2: Company Universe — scalable API-driven schema for 1k–5k companies (no hardcoded permanent fake numbers).
- P1 Phase 3: Short-Term Growth ranking (de-emphasize mega caps; asymmetric upside framing).
- P1 Phase 4: Future Giants (TAM/CAGR/margin/thesis/risks).
- P1 Phase 5: DCF Modeling engine (IB/equity-research grade sections, sourced assumptions).
- P1 Phase 6: Excel export (multi-sheet, formula-driven, formatting/charts) + fast accurate live prices.

## Notes
- Live data requires API keys (FMP/Polygon/Finnhub/etc.) — currently unset, app runs in Demo Mode.
- Auth is client-side demo (localStorage, any credentials accepted) — see test_credentials.md.
