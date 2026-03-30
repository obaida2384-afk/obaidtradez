"""
ObaidTradez Enhanced News & Sentiment Engine
Multi-source aggregation, AI-powered sentiment analysis, catalyst detection
Sources: FMP, Finnhub, Alpha Vantage, Marketaux + GPT-5.2 analysis
"""

import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FMP_KEY = os.environ.get("FMP_API_KEY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
MARKETAUX_KEY = os.environ.get("MARKETAUX_API_KEY", "")
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


class NewsFetcher:
    """Fetch news from multiple financial data sources"""

    @staticmethod
    async def _get(url: str, params: dict, headers: dict = None, timeout: int = 10) -> Optional[any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=headers or {}, timeout=timeout)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"News fetch error ({url}): {e}")
        return None

    @staticmethod
    async def fetch_fmp(symbol: str, limit: int = 15) -> List[Dict]:
        if not FMP_KEY:
            return []
        data = await NewsFetcher._get(
            "https://financialmodelingprep.com/stable/news/stock",
            {"symbol": symbol, "limit": limit, "apikey": FMP_KEY}
        )
        if not data or not isinstance(data, list):
            return []
        articles = []
        for a in data:
            articles.append({
                "title": a.get("title", ""),
                "text": a.get("text", "")[:500],
                "url": a.get("url", ""),
                "source": a.get("site", "FMP"),
                "published": a.get("publishedDate", ""),
                "image": a.get("image", ""),
                "origin": "fmp"
            })
        return articles

    @staticmethod
    async def fetch_finnhub(symbol: str) -> List[Dict]:
        if not FINNHUB_KEY:
            return []
        now = datetime.now(timezone.utc)
        from_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")
        data = await NewsFetcher._get(
            "https://finnhub.io/api/v1/company-news",
            {"symbol": symbol, "from": from_date, "to": to_date, "token": FINNHUB_KEY}
        )
        if not data or not isinstance(data, list):
            return []
        articles = []
        for a in data[:15]:
            pub = a.get("datetime", 0)
            if isinstance(pub, (int, float)) and pub > 0:
                pub = datetime.fromtimestamp(pub, tz=timezone.utc).isoformat()
            articles.append({
                "title": a.get("headline", ""),
                "text": a.get("summary", "")[:500],
                "url": a.get("url", ""),
                "source": a.get("source", "Finnhub"),
                "published": str(pub),
                "image": a.get("image", ""),
                "origin": "finnhub"
            })
        return articles

    @staticmethod
    async def fetch_alpha_vantage(symbol: str) -> List[Dict]:
        if not ALPHA_VANTAGE_KEY:
            return []
        data = await NewsFetcher._get(
            "https://www.alphavantage.co/query",
            {"function": "NEWS_SENTIMENT", "tickers": symbol, "limit": 10, "apikey": ALPHA_VANTAGE_KEY},
            timeout=15
        )
        if not data or "feed" not in data:
            return []
        articles = []
        for a in data.get("feed", [])[:10]:
            # Extract ticker-specific sentiment
            ticker_sent = None
            for ts in a.get("ticker_sentiment", []):
                if ts.get("ticker") == symbol:
                    ticker_sent = ts
                    break
            articles.append({
                "title": a.get("title", ""),
                "text": a.get("summary", "")[:500],
                "url": a.get("url", ""),
                "source": a.get("source", "AlphaVantage"),
                "published": a.get("time_published", ""),
                "image": a.get("banner_image", ""),
                "origin": "alphavantage",
                "av_sentiment": float(ticker_sent.get("ticker_sentiment_score", 0)) if ticker_sent else None,
                "av_relevance": float(ticker_sent.get("relevance_score", 0)) if ticker_sent else None
            })
        return articles

    @staticmethod
    async def fetch_marketaux(symbol: str) -> List[Dict]:
        if not MARKETAUX_KEY:
            return []
        data = await NewsFetcher._get(
            "https://api.marketaux.com/v1/news/all",
            {"symbols": symbol, "filter_entities": "true", "language": "en",
             "limit": 10, "api_token": MARKETAUX_KEY}
        )
        if not data or "data" not in data:
            return []
        articles = []
        for a in data.get("data", [])[:10]:
            articles.append({
                "title": a.get("title", ""),
                "text": a.get("description", "")[:500],
                "url": a.get("url", ""),
                "source": a.get("source", "Marketaux"),
                "published": a.get("published_at", ""),
                "image": a.get("image_url", ""),
                "origin": "marketaux"
            })
        return articles


class ArticleDeduplicator:
    """Deduplicate similar articles across sources"""

    @staticmethod
    def deduplicate(articles: List[Dict]) -> List[Dict]:
        seen_hashes = set()
        unique = []
        for a in articles:
            # Create fingerprint from title words
            title = a.get("title", "").lower()
            words = sorted(set(re.sub(r'[^a-z0-9\s]', '', title).split()))[:8]
            fingerprint = hashlib.md5(" ".join(words).encode()).hexdigest()[:12]

            if fingerprint not in seen_hashes:
                seen_hashes.add(fingerprint)
                unique.append(a)
        return unique


class AINewsAnalyzer:
    """GPT-5.2 powered news sentiment analysis and catalyst detection"""

    def __init__(self):
        self._chat = None

    def _get_chat(self, session_id: str):
        from emergentintegrations.llm.chat import LlmChat
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=session_id,
            system_message=(
                "You are a professional financial analyst. Analyze news articles for a given stock. "
                "Return ONLY valid JSON with no markdown formatting. Be concise."
            )
        )
        chat.with_model("openai", "gpt-5.2")
        return chat

    async def analyze_batch(self, symbol: str, articles: List[Dict]) -> Dict:
        """Analyze a batch of articles for a stock using GPT-5.2"""
        if not EMERGENT_KEY or not articles:
            return self._fallback_analysis(articles)

        try:
            from emergentintegrations.llm.chat import UserMessage

            # Prepare article summaries for the LLM
            article_text = ""
            for i, a in enumerate(articles[:8]):
                title = a.get("title", "No title")
                text = a.get("text", "")[:200]
                source = a.get("source", "Unknown")
                article_text += f"\n{i+1}. [{source}] {title}\n   {text}\n"

            prompt = f"""Analyze these news articles for {symbol}. Return ONLY valid JSON:

{article_text}

Return this exact JSON structure:
{{
  "sentiment_score": <number -100 to +100>,
  "sentiment_label": "<Bullish|Neutral|Bearish>",
  "catalyst_detected": <true|false>,
  "catalyst_type": "<earnings_surprise|merger_acquisition|guidance_change|regulatory|product_launch|analyst_rating|insider_activity|none>",
  "catalyst_strength": <0-100>,
  "news_momentum": "<accelerating|stable|decelerating>",
  "risk_flag": <true|false>,
  "risk_reason": "<string or null>",
  "top_articles": [
    {{
      "index": <1-based>,
      "relevance": <0-100>,
      "sentiment": "<positive|neutral|negative>",
      "why_it_matters": "<one line>"
    }}
  ],
  "one_line_summary": "<one line overall assessment>"
}}"""

            chat = self._get_chat(f"news_{symbol}_{datetime.now().strftime('%H%M')}")
            msg = UserMessage(text=prompt)
            response = await chat.send_message(msg)

            # Parse JSON from response
            json_str = response.strip()
            # Remove markdown code fences if present
            if json_str.startswith("```"):
                json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
                json_str = re.sub(r'\s*```$', '', json_str)

            import json
            result = json.loads(json_str)

            # Enrich top_articles with actual article data
            for ta in result.get("top_articles", []):
                idx = ta.get("index", 1) - 1
                if 0 <= idx < len(articles):
                    ta["title"] = articles[idx].get("title", "")
                    ta["url"] = articles[idx].get("url", "")
                    ta["source"] = articles[idx].get("source", "")
                    ta["published"] = articles[idx].get("published", "")

            result["analyzed_at"] = datetime.now(timezone.utc).isoformat()
            result["article_count"] = len(articles)
            result["ai_powered"] = True
            return result

        except Exception as e:
            logger.error(f"AI news analysis error for {symbol}: {e}")
            return self._fallback_analysis(articles)

    def _fallback_analysis(self, articles: List[Dict]) -> Dict:
        """Rule-based fallback when AI is unavailable"""
        if not articles:
            return {
                "sentiment_score": 0, "sentiment_label": "Neutral",
                "catalyst_detected": False, "catalyst_type": "none",
                "catalyst_strength": 0, "news_momentum": "stable",
                "risk_flag": False, "risk_reason": None,
                "top_articles": [], "one_line_summary": "No news available",
                "article_count": 0, "ai_powered": False,
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }

        # Simple keyword-based sentiment
        positive_words = {"surge", "beat", "upgrade", "growth", "profit", "rally", "strong", "record", "bullish", "outperform", "buy", "raise", "positive", "breakthrough"}
        negative_words = {"fall", "drop", "miss", "downgrade", "loss", "decline", "weak", "bearish", "sell", "cut", "negative", "warning", "layoff", "crash"}
        catalyst_words = {"earnings", "merger", "acquisition", "guidance", "fda", "approval", "launch", "dividend", "buyback", "split", "ipo", "insider"}

        pos_count = 0
        neg_count = 0
        catalyst_found = False
        catalyst_type = "none"

        for a in articles:
            text = (a.get("title", "") + " " + a.get("text", "")).lower()
            pos_count += sum(1 for w in positive_words if w in text)
            neg_count += sum(1 for w in negative_words if w in text)
            for w in catalyst_words:
                if w in text:
                    catalyst_found = True
                    if w in ("earnings",):
                        catalyst_type = "earnings_surprise"
                    elif w in ("merger", "acquisition"):
                        catalyst_type = "merger_acquisition"
                    elif w in ("guidance",):
                        catalyst_type = "guidance_change"
                    elif w in ("fda", "approval", "launch"):
                        catalyst_type = "product_launch"

            # Use Alpha Vantage sentiment if available
            av_sent = a.get("av_sentiment")
            if av_sent is not None:
                if av_sent > 0.15:
                    pos_count += 2
                elif av_sent < -0.15:
                    neg_count += 2

        total = pos_count + neg_count
        if total > 0:
            sentiment_score = int(((pos_count - neg_count) / total) * 100)
        else:
            sentiment_score = 0

        sentiment_label = "Bullish" if sentiment_score > 20 else "Bearish" if sentiment_score < -20 else "Neutral"

        top_articles = []
        for i, a in enumerate(articles[:5]):
            top_articles.append({
                "index": i + 1,
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("source", ""),
                "published": a.get("published", ""),
                "relevance": 80 - i * 10,
                "sentiment": "positive" if sentiment_score > 10 else "negative" if sentiment_score < -10 else "neutral",
                "why_it_matters": a.get("title", "")[:80]
            })

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "catalyst_detected": catalyst_found,
            "catalyst_type": catalyst_type,
            "catalyst_strength": 60 if catalyst_found else 0,
            "news_momentum": "accelerating" if len(articles) > 8 else "stable",
            "risk_flag": sentiment_score < -40,
            "risk_reason": "Strong negative sentiment" if sentiment_score < -40 else None,
            "top_articles": top_articles,
            "one_line_summary": f"{len(articles)} articles, sentiment: {sentiment_label}",
            "article_count": len(articles),
            "ai_powered": False,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }


class EnhancedNewsSentimentEngine:
    """Orchestrates multi-source news aggregation and AI analysis"""

    def __init__(self, db):
        self.db = db
        self.analyzer = AINewsAnalyzer()

    async def analyze_stock(self, symbol: str, use_cache: bool = True) -> Dict:
        """Full news analysis for a stock: fetch → dedupe → AI analyze → cache"""
        # Check cache (15 min TTL)
        if use_cache:
            cached = await self.db.news_analysis.find_one(
                {"symbol": symbol}, {"_id": 0}
            )
            if cached:
                analyzed_at = cached.get("analyzed_at", "")
                if analyzed_at:
                    try:
                        ts = datetime.fromisoformat(analyzed_at.replace("Z", "+00:00"))
                        if (datetime.now(timezone.utc) - ts).total_seconds() < 900:
                            return cached
                    except:
                        pass

        # Fetch from all sources in parallel
        results = await asyncio.gather(
            NewsFetcher.fetch_fmp(symbol),
            NewsFetcher.fetch_finnhub(symbol),
            NewsFetcher.fetch_alpha_vantage(symbol),
            NewsFetcher.fetch_marketaux(symbol),
            return_exceptions=True
        )

        all_articles = []
        source_counts = {}
        for r in results:
            if isinstance(r, list):
                for a in r:
                    all_articles.append(a)
                    origin = a.get("origin", "unknown")
                    source_counts[origin] = source_counts.get(origin, 0) + 1

        # Sort by recency (newest first)
        all_articles.sort(key=lambda x: x.get("published", ""), reverse=True)

        # Deduplicate
        unique_articles = ArticleDeduplicator.deduplicate(all_articles)

        # AI analysis
        analysis = await self.analyzer.analyze_batch(symbol, unique_articles)
        analysis["symbol"] = symbol
        analysis["total_raw_articles"] = len(all_articles)
        analysis["unique_articles"] = len(unique_articles)
        analysis["sources"] = source_counts

        # Cache result
        await self.db.news_analysis.update_one(
            {"symbol": symbol}, {"$set": analysis}, upsert=True
        )

        return analysis

    async def batch_analyze(self, symbols: List[str], batch_size: int = 3) -> int:
        """Analyze news for multiple stocks in batches"""
        count = 0
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            results = await asyncio.gather(
                *[self.analyze_stock(s, use_cache=False) for s in batch],
                return_exceptions=True
            )
            for r in results:
                if not isinstance(r, Exception) and r:
                    count += 1
            if i + batch_size < len(symbols):
                await asyncio.sleep(2)
            if (i // batch_size) % 5 == 0:
                logger.info(f"News batch {i // batch_size + 1}: {count} analyzed")
        logger.info(f"News batch analysis complete: {count} stocks")
        return count

    async def get_breaking_news(self) -> List[Dict]:
        """Get recent high-impact news across all analyzed stocks"""
        cursor = self.db.news_analysis.find(
            {"catalyst_detected": True, "catalyst_strength": {"$gte": 50}},
            {"_id": 0, "symbol": 1, "one_line_summary": 1, "catalyst_type": 1,
             "catalyst_strength": 1, "sentiment_score": 1, "sentiment_label": 1,
             "top_articles": {"$slice": 2}, "analyzed_at": 1}
        ).sort("analyzed_at", -1).limit(20)
        return await cursor.to_list(20)

    async def get_sentiment_overview(self) -> Dict:
        """Get sentiment distribution across all analyzed stocks"""
        pipeline = [
            {"$group": {
                "_id": "$sentiment_label",
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$sentiment_score"}
            }}
        ]
        dist = await self.db.news_analysis.aggregate(pipeline).to_list(10)

        total = await self.db.news_analysis.count_documents({})
        catalysts = await self.db.news_analysis.count_documents({"catalyst_detected": True})

        return {
            "total_analyzed": total,
            "with_catalysts": catalysts,
            "distribution": {d["_id"]: {"count": d["count"], "avg_score": round(d["avg_score"], 1)} for d in dist}
        }
