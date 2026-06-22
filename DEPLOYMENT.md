# Deployment Guide — ObaidTradez / ALPHA VAULT

This app has **two parts** that must BOTH be deployed:

1. **Frontend** (this `frontend/` folder) → **Vercel** (static Vite build)
2. **Backend** (`backend/` folder, FastAPI) + **MongoDB** → a server host (e.g. **Railway**) + **MongoDB Atlas**

Vercel only serves the frontend. The frontend is useless without the backend (it powers login,
the company universe, DCF, news and prices), so deploy the backend first.

---

## STEP 1 — MongoDB (Atlas, free tier is fine)
1. Create a cluster at https://www.mongodb.com/atlas → create a database user → allow network access (0.0.0.0/0 or Railway's IPs).
2. Copy the connection string, e.g. `mongodb+srv://USER:PASS@cluster0.xxxx.mongodb.net`.

## STEP 2 — Backend on Railway
1. https://railway.app → New Project → Deploy from GitHub repo → pick this repo, set **root directory = `backend`**.
   (Railway auto-detects Python + the `Procfile`: `uvicorn server:app --host 0.0.0.0 --port $PORT`.)
2. Add **environment variables** (Railway → Variables):
   ```
   MONGO_URL=mongodb+srv://USER:PASS@cluster0.xxxx.mongodb.net
   DB_NAME=obaidtradez
   FMP_API_KEY=FZQnhpLdjDZosqUNtyN4hTwuvdsBea7J
   STOCKNEWS_API_KEY=zvovwa0lj9e0mkzmc4cwjph6hp6fcyjb6jwg5tdc
   ACCESS_USERNAME=obaidtradez
   ACCESS_CODE_HASH=Odm200429
   ```
   Optional (auto-refresh tuning): `UNIVERSE_REFRESH_DAYS` (default 7), `UNIVERSE_TARGET_SIZE` (default 3000).
3. Deploy. Note the public backend URL, e.g. `https://obaidtradez-backend-production.up.railway.app`.
4. **Company universe** — builds itself automatically: a built-in scheduler runs on startup and rebuilds the
   universe if it is missing or older than `UNIVERSE_REFRESH_DAYS` (default weekly). So on first boot of a fresh DB
   it auto-populates within a few minutes — **no manual step required**.
   (Optional) to force an immediate rebuild any time:
   ```
   curl -X POST "https://YOUR-BACKEND-URL/api/universe/build?target_size=3000"
   ```
   Check progress / freshness:
   ```
   curl "https://YOUR-BACKEND-URL/api/universe/coverage"
   ```

## STEP 3 — Frontend on Vercel
1. https://vercel.com → New Project → import this repo → set **Root Directory = `frontend`**.
   (`frontend/vercel.json` already sets build = `npm run build`, output = `dist`, and SPA rewrites so deep links work.)
2. Add **environment variable** (Vercel → Settings → Environment Variables, for Production):
   ```
   REACT_APP_BACKEND_URL=https://YOUR-BACKEND-URL
   ```
   (No trailing slash. This is the Railway URL from Step 2.)
3. Deploy. Open the Vercel URL and log in with **obaidtradez / Odm200429**.

---

## What you get (all wired & verified)
- Single-credential login gate (server-validated); public signup disabled.
- Live company universe, Discovery, Top Plays (live prices), Future Giants (live prices).
- DCF modeling engine + formula-driven multi-sheet Excel export (with a News & Catalysts sheet
  and a Recommendation line).
- StockNewsAPI: market news, news-driven stock ideas, company news inside DCF.
- Dashboard "Trending Now" banner — one click opens the idea's DCF model.
- Buy/Strong Buy/Hold/Not a Good Buy/Avoid recommendation on Trending Now, News ideas and the DCF model.

## Notes
- CORS is open (`*`) so the Vercel domain can call the backend out of the box.
- Read-only market-data endpoints are public; the credential gate protects the website UI.
- To change the password later, update `ACCESS_CODE_HASH` (and/or `ACCESS_USERNAME`) in Railway and redeploy.
- Custom domain: add it in Vercel (frontend). Keep `REACT_APP_BACKEND_URL` pointing at the backend host.
