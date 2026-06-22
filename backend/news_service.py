"""
News service backed by StockNewsAPI — company news (with sentiment), market news,
and news-driven stock suggestions (top-mentioned tickers cross-referenced with the
enriched company universe).
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BASE = "https://stocknewsapi.com/api/v1"


class NewsService:
    def __init__(self, api_client, db, key_getter):
        self.api = api_client
        self.db = db
        self._key = key_getter

    async def _get(self, path: str, params: Dict, timeout: float = 20.0):
        if not self._key():
            return None
        params = {**params, "token": self._key()}
        return await self.api._request(f"{BASE}{path}", params=params, timeout=timeout)

    def _shape(self, items: List[Dict]) -> List[Dict]:
        out = []
        for n in items or []:
            out.append({
                "title": n.get("title"),
                "text": n.get("text"),
                "url": n.get("news_url"),
                "source": n.get("source_name"),
                "date": n.get("date"),
                "image": n.get("image_url"),
                "sentiment": n.get("sentiment"),
                "tickers": n.get("tickers") or [],
                "topics": n.get("topics") or [],
            })
        return out

    async def company_news(self, ticker: str, items: int = 12) -> Dict:
        data = await self._get("", {"tickers": ticker.upper(), "items": min(items, 50)})
        articles = self._shape((data or {}).get("data") or [])
        pos = sum(1 for a in articles if a["sentiment"] == "Positive")
        neg = sum(1 for a in articles if a["sentiment"] == "Negative")
        tone = "Positive" if pos > neg else "Negative" if neg > pos else "Neutral"
        return {"ticker": ticker.upper(), "articles": articles,
                "sentiment": {"positive": pos, "negative": neg, "tone": tone},
                "source": "StockNewsAPI"}

    async def market_news(self, items: int = 24) -> Dict:
        data = await self._get("/category", {"section": "general", "items": min(items, 50)})
        return {"articles": self._shape((data or {}).get("data") or []), "source": "StockNewsAPI"}

    async def suggestions(self, limit: int = 12) -> Dict:
        """News-driven ideas: check news buzz on top-opportunity universe names, rank by buzz + fundamentals."""
        cands = []
        cursor = self.db["company_universe"].find(
            {"opportunityScore": {"$gte": 55}},
            {"_id": 0, "ticker": 1, "companyName": 1, "sector": 1, "price": 1,
             "opportunityScore": 1, "marketCap": 1, "analystRating": 1, "analystUpsidePct": 1},
        ).sort("opportunityScore", -1).limit(60)
        async for d in cursor:
            cands.append(d)
        if not cands:
            return {"suggestions": [], "source": "StockNewsAPI + universe", "generated_at": datetime.now(timezone.utc).isoformat()}

        by = {c["ticker"]: c for c in cands}
        tickers = list(by.keys())
        counts: Dict[str, int] = {}
        sent: Dict[str, int] = {}
        data = await self._get("", {"tickers": ",".join(tickers[:50]), "items": 100})
        for a in (data or {}).get("data") or []:
            s = 1 if a.get("sentiment") == "Positive" else -1 if a.get("sentiment") == "Negative" else 0
            for t in a.get("tickers") or []:
                if t in by:
                    counts[t] = counts.get(t, 0) + 1
                    sent[t] = sent.get(t, 0) + s

        if counts:
            ranked = sorted(counts.keys(), key=lambda t: (counts[t], by[t].get("opportunityScore") or 0), reverse=True)
        else:
            ranked = [c["ticker"] for c in cands]  # fallback: pure opportunity ranking

        suggestions = []
        for t in ranked[:limit]:
            d = by[t]
            sv = sent.get(t, 0)
            suggestions.append({
                "ticker": t,
                "name": d.get("companyName"),
                "sector": d.get("sector"),
                "price": d.get("price"),
                "marketCap": round((d.get("marketCap") or 0) / 1e6),
                "opportunityScore": d.get("opportunityScore"),
                "analystRating": d.get("analystRating"),
                "analystUpsidePct": d.get("analystUpsidePct"),
                "newsMentions": counts.get(t, 0),
                "newsSentiment": "Positive" if sv > 0 else "Negative" if sv < 0 else "Neutral",
            })
        return {"suggestions": suggestions, "generated_at": datetime.now(timezone.utc).isoformat(),
                "source": "StockNewsAPI buzz + enriched company universe"}
