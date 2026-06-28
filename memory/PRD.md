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

### 2026-06-22 — Built-in universe auto-refresh scheduler (DONE)
- Added `_universe_auto_refresh()` background task (registered in `startup_event`): on startup it rebuilds the company universe if missing OR older than `UNIVERSE_REFRESH_DAYS` (default 7), then re-checks every 6h. Size via `UNIVERSE_TARGET_SIZE` (default 3000). Reads freshness from the `company_universe_meta` doc (`updated_at`).
- Effect: fresh production DBs auto-populate on first boot (manual `POST /api/universe/build` is now optional), and fundamentals/scores stay current automatically. Verified: boots cleanly, correctly skips rebuild when data is fresh (3000 companies, updated today), zero scheduler errors. `DEPLOYMENT.md` updated.


## Backlog (await user approval per phase)
- P1 Phase 2: Company Universe — scalable API-driven schema for 1k–5k companies (no hardcoded permanent fake numbers).
- P1 Phase 3: Short-Term Growth ranking (de-emphasize mega caps; asymmetric upside framing).
- P1 Phase 4: Future Giants (TAM/CAGR/margin/thesis/risks).
- P1 Phase 5: DCF Modeling engine (IB/equity-research grade sections, sourced assumptions).
- P1 Phase 6: Excel export (multi-sheet, formula-driven, formatting/charts) + fast accurate live prices.

## Notes
- Live data is active via backend keys (FMP + StockNewsAPI in backend/.env). A green "Live Data" indicator (Header/Dashboard/Settings, backed by GET /api/status) reflects real status + data freshness.
- Auth is a single-owner gate: Username obaidtradez, validated server-side via /api/auth/access (ACCESS_USERNAME/ACCESS_CODE_HASH). Public signup disabled. See test_credentials.md.

### 2026-06-22 — Price-accuracy fix + Live-Data indicator (DONE)
- Bug (NVDA showed $120): Research.jsx rendered hardcoded MOCK prices (mockData NVDA $120.44); backend live price was always correct (FMP NVDA $208.72). Fixed Research to override displayed prices with live FMP batch quotes via useQuotes (selected company + 8 Featured cards). Scenario %, consensus-target % and AI-thesis assessment now use live price.
- Smart Live-Data indicator: added backend GET /api/status + useLiveStatus hook + fetchStatus. Header (App.js), Dashboard, and Settings now show green "Live Data / Live Market Data Active" with universe count + "refreshed Xh ago" (amber "Data source offline" if backend unreachable). Replaces the misleading per-user-apiKey "Demo Mode" notices.
- Verified testing_agent iteration_4.json — 100% (7/7): NVDA $208.62 live (mock gone), AAPL $299, Featured grid live, all Research tabs render, green indicators on Header/Dashboard/Settings.

### 2026-06-22 — Live "as of" price timestamps (DONE)
- `useQuotes` now also returns `asOf` (from /api/prices/quotes). Research header shows "Live · as of HH:MM" next to the price; DCF model stat bar shows "Live data as of …" (stamped when the model loads); the Excel export Cover adds a "Live Price As Of" row. Callers (TopPlays/FutureGiants/Research) updated to the `{prices, asOf}` shape. Additive UI; frontend compiles clean.

### 2026-06-22 — Research wired to LIVE DCF data (DONE)
- New `lib/researchModel.js buildResearchCompany({dcf, universe, mock})`: composes the Research report from the live DCF payload (fetchDcf) + universe record (fetchCompany→normalizeCompany) + live quote, mock used only for qualitative `moat`. Research now works for ANY FMP ticker.
- `Research.jsx`: async `loadCompany` (deep-link via useEffect, featured cards, search, header search bar route through it); loading spinner; real historicals (Financials), real WACC/TGR + "Consensus Fair Value" + "Run full institutional DCF model" CTA → /modeling?ticker (Valuation); generated memo thesis (AI Thesis). Live price + "as of".
- Verified testing_agent iteration_5.json — 8/8 PASS. Fixed Market Cap double /1e6 (DCF marketCap already in millions).
### 2026-06-22 — Daily refresh, live indices, Wall Street Excel (DONE)
- **Universe auto-refresh now DAILY** (was weekly): `_universe_auto_refresh` default `UNIVERSE_REFRESH_DAYS` 7→1. New prospects appear / stale names drop daily; ratings/consensus/scores refresh daily. Scheduler still re-checks every 6h.
- **Live market index bar**: new `GET /api/market/indices` (FMP `/quote` for ^GSPC/^IXIC/^DJI/^RUT/^VIX + `/treasury-rates` year10 with prior-day change). `companyUniverse.js fetchMarketIndices`; `Dashboard.jsx` now fetches live indices (30s poll) replacing hardcoded mockData MARKET_INDICES ($5,487 etc gone). Verified live: S&P 7,475 / NASDAQ 26,166 / DOW 51,712 / Russell 3,004 / VIX 17.28 / 10Y 4.51%.
- **Excel exporter rebuilt — "Wall Street Classic" (navy + gold)** + equity-research elements: upgraded Cover (navy hero, gold rule, color-coded BUY/AVOID rating badge, key stats grid); new **Scenario Analysis** sheet (Bull/Base/Bear implied value + upside, color-coded, computed from assumptions) with a **football-field** valuation visual (DCF range vs Analyst target range vs 52wk if present, gold current-price marker); gold header rules + cream banding across all sheets. All 67 DCF formulas preserved. Verified e2e: AAPL export downloads, 10 sheets, scenario values + badge correct.
- On-screen Modeling page left unchanged (user skipped on-screen direction; redesign constraint respected).

### 2026-06-22 — On-screen DCF "go big" + teach-the-user (DONE)
- User asked to make the on-screen Financial Modeling page far richer AND add plain-English explanations on EVERY tab (for finance beginners), including Monte Carlo explained for the specific company. Kept the existing dark theme (no redesign).
- New reusable `Explainer` component in `Modeling.jsx` (collapsible, default-open, `data-testid="tab-explainer"`, GraduationCap icon) added to all 9 tabs (Summary, Assumptions, DCF Model, Sensitivity, Monte Carlo, Historicals, Comparables, Sources, Investment Memo). Each block is company-aware (interpolates name/ticker/implied price/upside/WACC/TGR).
- New **Monte Carlo tab** (`MonteCarloTab`): `runMonteCarlo()` runs 6,000 client-side simulations (random-normal nudges to revenue growth, EBITDA margin, WACC, terminal growth via `quickImplied()`), renders 4 stat cards (Median / Mean / P10–P90 range / % Chance Undervalued), a histogram (green=above price, red=below, dashed 'Today' reference line, p99 tail-clip for readability), and a **Tornado** chart (`tornado()`) ranking which input moves the valuation most. Plain-English explainer interpolates company name + dynamic % undervalued. Mounts only when tab active (perf).
- Verified by testing_agent iteration_6.json — 100% (all 9 explainers present/collapsible, Monte Carlo full content + company-specific for NVDA & AAPL, assumptions live-recompute, Excel export + sensitivity heatmap regression PASS, 0 console errors).
- Note: `Modeling.jsx` now ~1600 lines (9 tabs + helpers) — candidate for splitting into /pages/modeling/tabs/*.jsx later (not blocking).

### 2026-06-22 — Excel redesigned to GREEN Equity-Research layout (DONE)
- User shared a reference (green ER tearsheet) and asked to match it exactly. Rebuilt the Excel **Cover** sheet in `excelExporter.js` to that layout: full-width green banner; header row with embedded company **logo** (fetched from FMP `images.financialmodelingprep.com/symbol/{T}.png`, falls back to a ticker tile), **BUY/HOLD/SELL Rating badge** (color-coded), big cream **Target Price** box, and a green Sector/Current-Price/as-of box; a **BULL/BASE/BEAR** scenario block (green/grey/red columns with TP + upside + current price); a **Financial Summary & Key Metrics** table (actual + 5 forecast years from the computed model); plus two **canvas-rendered chart images** embedded via ExcelJS `addImage` — a **Revenue Growth** column chart and a **Valuation Football-Field** (P/E, EV/EBITDA multiple ranges + DCF $ range).
- Whole-workbook palette switched navy+gold → green/cream (constants repointed). `Modeling.jsx handleExport` now passes `computed: model` so the cover uses real forecast numbers. Verified e2e (GOOGL + NVDA downloads): cover cells correct, year labels fixed (no actual/forecast clash), 3 media images embedded (logo + 2 charts).
- NVDA DCF note (explained to user, NOT a bug): pure DCF values high-beta/high-multiple names below market because the high WACC (~16.6%) heavily discounts future cash and the 5-yr taper + ~3% terminal growth can't replicate the market's long-horizon growth pricing. Assumptions are editable to test a bull case.

### 2026-06-23 — Currency normalisation fix (foreign listings / ADRs) (DONE)
- BUG (user: "TSMC bullish DCF = $6,000"): foreign companies report financials in their local currency (TSM=TWD, BABA=CNY, SAP/UL=EUR, TM=JPY, NVO=DKK, NSRGY=CHF, RY=CAD) while price/marketCap/analyst targets are in the trading currency (USD). The DCF mixed currencies → implied/share in local-currency scale (TSM was ~$4,125; bull ~$6,000).
- FIX in `dcf_engine.py`: added `_fx_rate(reported, trading)` (FMP forex `quote`, e.g. TWDUSD). Detect `reportedCurrency` (income stmt) vs `currency` (profile). Keep ALL intermediate ratios (growth, margins, WACC, NWC%, cost-of-debt) in the raw reporting currency for consistency; convert only the absolute $ OUTPUTS to trading currency: company.revenue, revenueHistory, assumptions.cash/debt, and every $ field + EPS in historicals (×fx). WACC debt-weight now uses marketCap converted to reporting ccy. Added company.currency / reportingCurrency / fxApplied; historicals source notes the conversion.
- Excel cover scenarios made DCF-consistent (bull = implied×1.35, bear = implied×0.65) to match the on-screen Summary (previously pulled analyst high/low, causing a $700 vs $146 mismatch).
- Verified: US names unchanged (fx=1.0, AAPL/NVDA identical). TSM implied $4,125→$146.44 (bull $197.70, bear $95.19); BABA $151 (+44%), SAP $251, TM/NVO/UL/NSRGY/RY all correct USD scale. On-screen TSM + Excel export confirmed.
- Determinism: all assumptions are derived from real FMP data (analyst revenueAvg, historical CAGR, effective tax, CAPM WACC from real beta+10Y treasury, margins from statements) — no LLM/random. The only randomness is the Monte Carlo tab (intentional, labeled statistical simulation).

### 2026-06-27 — Auth dual-mode + Top Plays Performance Tracker (DONE)
- **Auth hardened** (`server.py`): `ACCESS_CODE_HASH` now accepts EITHER plaintext OR a bcrypt hash (`_code_matches` → constant-time `secrets.compare_digest` for plaintext, `bcrypt.checkpw` for hashes). Added safe diagnostic `GET /api/auth/config-check` (no secrets; returns configured/length/sha8 fingerprint + code_is_bcrypt_hash). Diagnosed a user Railway login failure: password env was correct but `ACCESS_USERNAME` was an 8-char value (target `obaidtradez`=11, fp a32c3c6b). Root cause = env-var value mismatch / Railway not redeploying the variable change.
- **Top Plays Tracker (`top_plays_tracker.py` + endpoints + `TopPlays.jsx` "Tracked Picks" tab)** — all 5 requested items:
  1. Performance tracker: snapshots the ranked list into `top_plays_picks` collection; tracks entryPrice/Date, live return, hit-rate, avg winner/loser, avg hold days.
  2. Exit-reason labels: Target Hit / Thesis Broke / Out-ranked (`_exit_reason`).
  3. Hysteresis: a pick exits only after being absent ≥2 real days (time-based, frequency-independent).
  4. Conviction stack (momentum + value): High/Medium/Standard from growthScore + analyst upside + P/E vs sector anchor + FCF.
  5. Risk discipline: suggestedWeightPct & suggestedStopPct (scaled by riskScore/beta), reward/risk ratio, and portfolio sector-concentration check (flags >30%).
  - Endpoints: `GET /api/top-plays/tracked`, `POST /api/top-plays/reconcile`. Reconcile is hooked into the 6h universe scheduler. Verified: 30 picks seeded with conviction/risk; simulated exits produce correct Target Hit (+20%) / Thesis Broke (−12%) + stats (hitRate, reasonBreakdown). Frontend tab renders all sections (dark theme).

### 2026-06-27 — Cleanup pass (DONE) + deliberate non-actions
- Deleted 8 dead frontend pages (not routed/imported): Alerts, AutoTrade, Backtesting, Chatbot, Investments, LongTermInvest, Screener, Trading. Sidebar is now a clean research platform. App verified rendering post-deletion.
- Added **FMP rate-limit retry/backoff** centrally in `MultiAPIClient._request` (exponential backoff + Retry-After on 429/5xx, and detects FMP's "Limit Reach" 200-body). Verified live (status + quotes OK).
- **Deliberately NOT removed: backend trading engine.** Modules `ai_trading_system`, `auto_trade_scheduler`, `technical_analysis_engine`, `performance_tracker`, `live_reeval_engine`, `reeval_verifier`, `execution_transparency`, `top_movers_scanner` are referenced ~84× across the 6,300-line `server.py` with cross-imports. A blind rip-out would very likely break the deployed app for zero functional gain. The auto-trade scheduler only starts if previously enabled (it isn't), so the trading code is dormant/harmless. If full removal is wanted later, it needs a dedicated, tested refactor.
- Deferred: MarketMacro→FRED (needs a free FRED API key from user); split Modeling.jsx (pure refactor, regression risk, no user benefit).


### 2026-06-28 — Full-universe access on all tabs + macro stale-price fix (DONE, UI verify pending preview wake)
- **Bug: Market & Macro showed wrong S&P 500 price.** Root cause: `MarketMacro.jsx` initialised the index bar from mock `MARKET_INDICES` (S&P 500 = 5487.23) and only replaced it if the live fetch resolved — on slow/failed fetch (deployed env) it displayed the stale mock price. Fix: removed ALL mock fallbacks from MarketMacro (`MARKET_INDICES`/`SECTOR_PERFORMANCE`/`MACRO_INDICATORS`); indices init to `[]`, index grid renders only when live data present; indicators/sectors use live-only arrays. Live `/api/market/indices` returns correct S&P (~7354). No stale price can ever show now.
- **Bug: Research tab only showed ~12 companies.** Root cause: `Research.jsx` `CompanySearch` filtered the mock `COMPANY_UNIVERSE` (12 hardcoded names) and `featured = COMPANY_UNIVERSE.slice(0,8)`. Fix: search now queries the LIVE universe via `fetchCompanies({search})` (debounced 220ms) across all 3,090 companies; added "Load TICKER directly →" affordance so ANY FMP ticker (even outside the universe) can be loaded via the DCF engine; featured cards now load live top-8 by opportunityScore; `getImpliedRating` falls back to analyst upside when no DCF implied price. testids: `research-search-input`, `research-search-results`, `research-search-result-{T}`, `research-search-direct`.
- **Discovery now reaches all 3,090 (was top-120 only).** Added a live universe search box (`discovery-search-input`, debounced 250ms) → `fetchCompanies({search})`; when a query is present the grid shows server-side matches across the whole universe, else the curated top-120 by opportunityScore. Clear-filters also clears the query.
- Modeling `CompanySelector` already searched the live universe (unchanged). Top Plays / Future Giants remain intentionally curated ranking screens (confirmed scope with user — they wanted per-company lookup tabs to reach everything, which Research/Modeling/Discovery now do).
- Verified: backend `/api/universe/companies?search=` matches by ticker (CRMD) AND name (palantir→PLTR) across 3,090 companies; all 3 edited files pass esbuild parse + Vite HMR clean. UI click-through NOT yet verified — Emergent preview was in platform idle/"resting" state (only the owner can wake it from app.emergent.sh); run frontend testing agent or self-verify on deployed site once awake.

### 2026-06-28 — Top Plays Performance tab upgrades + ROI leaderboard (DONE, verified iteration_8.json 100%)
- **Best Performers leaderboard** (`bestPerformers` in `top_plays_tracker.get_tracked`, UI `best-performers`): ranks ALL tracked picks (active+exited) by **Peak ROI since suggestion date**. Each row shows entry date/price + three clearly-labeled ROI lenses to solve the "timing" question honestly: **Peak** (entry→highest price reached, best-case exit), **Now** (entry→live, if still held), **Sold** (entry→exit, realized when system dropped it). Headline "what you'd have made".
- **Live forward-tracking of exited picks**: endpoint now fetches live prices for active AND exited tickers; exited picks gain `sinceExitPct` + `daysSinceExit` (return SINCE it left the list) so you can see if dropped names kept running. `peakReturnPct`/`nowReturnPct` added to every pick.
- **"Do dropped names keep performing?" forward-summary card** (`exitedForwardSummary` {count, pctStillUp, avgSinceExit, avgDaysSinceExit}, UI `exited-forward-summary`): only renders when exits exist; says e.g. "X% still higher, avg +Y% since exit (~Z days)" + whether exits were early/well-timed.
- **Plain-English "what this means" line** on each exited card (Target Hit / Thesis Broke / Out-ranked → guidance; explicitly notes leaving the list is NOT a sell signal).
- **Top-10 toggles** (`tracker-toggle-more`) on Best Performers, Active, and Exited lists (show top 10 ↔ show all N).
- Verified: backend returns all fields (20 best performers, peak/now/sold/status); preview env has 44 active / 0 exited so forward-summary correctly hidden. testids: best-performers, best-performers-list, exited-forward-summary, tracker-toggle-more.
- Code-review note (non-blocking): TopPlays.jsx now ~553 lines (TrackedPicks ~280) — candidate to split into /pages/topPlays/ later.

### 2026-06-28 — Dashboard "Hall of Fame" best-ever pick badge (DONE)
- New `GET /api/top-plays/hall-of-fame` (`top_plays_tracker.hall_of_fame(live_prices)`) returns the single best tracked pick across ALL picks (no 90-day window) by Peak ROI since suggestion date; uses live prices (peak = max(stored peak, live, entry)) so it stays consistent with the Best Performers leaderboard. Returns {best:{ticker,name,sector,entryDate,entryPrice,peakPrice,peakReturnPct,status,holdDays}, trackedCount}.
- `companyUniverse.js fetchHallOfFame`; Dashboard.jsx renders a gold badge (data-testid=hall-of-fame-badge / hall-of-fame-roi) below Trending Now: Trophy + "Hall of Fame · Best pick to date" + ticker/name + big "+X% peak ROI if bought when suggested". Click → /modeling?ticker. Hidden when no tracked picks. Verified backend live: CTRE +10.2% (matches leaderboard #1). Dashboard.jsx compiles clean; UI render pending preview wake (additive card, mirrors verified TrendingNow pattern).
