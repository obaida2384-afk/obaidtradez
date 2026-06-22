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


## Backlog (await user approval per phase)
- P1 Phase 2: Company Universe — scalable API-driven schema for 1k–5k companies (no hardcoded permanent fake numbers).
- P1 Phase 3: Short-Term Growth ranking (de-emphasize mega caps; asymmetric upside framing).
- P1 Phase 4: Future Giants (TAM/CAGR/margin/thesis/risks).
- P1 Phase 5: DCF Modeling engine (IB/equity-research grade sections, sourced assumptions).
- P1 Phase 6: Excel export (multi-sheet, formula-driven, formatting/charts) + fast accurate live prices.

## Notes
- Live data requires API keys (FMP/Polygon/Finnhub/etc.) — currently unset, app runs in Demo Mode.
- Auth is client-side demo (localStorage, any credentials accepted) — see test_credentials.md.
