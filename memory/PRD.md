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

## Backlog (await user approval per phase)
- P1 Phase 2: Company Universe — scalable API-driven schema for 1k–5k companies (no hardcoded permanent fake numbers).
- P1 Phase 3: Short-Term Growth ranking (de-emphasize mega caps; asymmetric upside framing).
- P1 Phase 4: Future Giants (TAM/CAGR/margin/thesis/risks).
- P1 Phase 5: DCF Modeling engine (IB/equity-research grade sections, sourced assumptions).
- P1 Phase 6: Excel export (multi-sheet, formula-driven, formatting/charts) + fast accurate live prices.

## Notes
- Live data requires API keys (FMP/Polygon/Finnhub/etc.) — currently unset, app runs in Demo Mode.
- Auth is client-side demo (localStorage, any credentials accepted) — see test_credentials.md.
