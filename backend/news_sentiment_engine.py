"""
ObaidTradez Enhanced News & Sentiment Engine v2
High-signal catalyst engine: Large-scale ingestion → Multi-layer filtering → 
Catalyst scoring → Trade-oriented categories → Direct trading integration.
Sources: FMP, Finnhub, Alpha Vantage, Marketaux + GPT-5.2 NLP analysis
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

# Source credibility weights (0-1)
SOURCE_CREDIBILITY = {
    "reuters": 0.95, "bloomberg": 0.95, "wsj": 0.90, "cnbc": 0.88,
    "financial times": 0.90, "barrons": 0.88, "yahoo finance": 0.75,
    "seeking alpha": 0.70, "benzinga": 0.72, "motley fool": 0.65,
    "investorplace": 0.60, "marketwatch": 0.80, "zacks": 0.72,
    "thefly": 0.70, "default": 0.55,
}

# Catalyst type weights
CATALYST_WEIGHTS = {
    "earnings_surprise": 90,
    "guidance_change": 85,
    "merger_acquisition": 92,
    "partnership": 75,
    "product_launch": 80,
    "analyst_upgrade": 78,
    "analyst_downgrade": 78,
    "regulatory_news": 85,
    "insider_activity": 70,
    "viral_momentum": 65,
    "dividend_buyback": 60,
    "none": 0,
}


class NewsFetcher:
    """Fetch large volumes of news from multiple financial data sources"""

    @staticmethod
    async def _get(url: str, params: dict, headers: dict = None, timeout: int = 12) -> Optional[any]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, headers=headers or {}, timeout=timeout)
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning(f"News fetch error ({url}): {e}")
        return None

    @staticmethod
    async def fetch_fmp(symbol: str, limit: int = 50) -> List[Dict]:
        """Fetch up to 50 articles from FMP"""
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
                "text": a.get("text", "")[:600],
                "url": a.get("url", ""),
                "source": a.get("site", "FMP"),
                "published": a.get("publishedDate", ""),
                "image": a.get("image", ""),
                "origin": "fmp"
            })
        return articles

    @staticmethod
    async def fetch_fmp_general(limit: int = 80) -> List[Dict]:
        """Fetch general market news from FMP for broad coverage"""
        if not FMP_KEY:
            return []
        data = await NewsFetcher._get(
            "https://financialmodelingprep.com/stable/news/stock",
            {"limit": limit, "apikey": FMP_KEY}
        )
        if not data or not isinstance(data, list):
            return []
        articles = []
        for a in data:
            articles.append({
                "title": a.get("title", ""),
                "text": a.get("text", "")[:600],
                "url": a.get("url", ""),
                "source": a.get("site", "FMP"),
                "published": a.get("publishedDate", ""),
                "symbol": a.get("symbol", ""),
                "image": a.get("image", ""),
                "origin": "fmp_general"
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
        for a in data[:30]:
            pub = a.get("datetime", 0)
            if isinstance(pub, (int, float)) and pub > 0:
                pub = datetime.fromtimestamp(pub, tz=timezone.utc).isoformat()
            articles.append({
                "title": a.get("headline", ""),
                "text": a.get("summary", "")[:600],
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
            {"function": "NEWS_SENTIMENT", "tickers": symbol, "limit": 30, "apikey": ALPHA_VANTAGE_KEY},
            timeout=15
        )
        if not data or "feed" not in data:
            return []
        articles = []
        for a in data.get("feed", [])[:30]:
            ticker_sent = None
            for ts in a.get("ticker_sentiment", []):
                if ts.get("ticker") == symbol:
                    ticker_sent = ts
                    break
            articles.append({
                "title": a.get("title", ""),
                "text": a.get("summary", "")[:600],
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
             "limit": 20, "api_token": MARKETAUX_KEY}
        )
        if not data or "data" not in data:
            return []
        articles = []
        for a in data.get("data", [])[:20]:
            articles.append({
                "title": a.get("title", ""),
                "text": a.get("description", "")[:600],
                "url": a.get("url", ""),
                "source": a.get("source", "Marketaux"),
                "published": a.get("published_at", ""),
                "image": a.get("image_url", ""),
                "origin": "marketaux"
            })
        return articles


# ===================== MULTI-LAYER FILTERING =====================

class NewsFilterPipeline:
    """Multi-layer filtering: Relevance → Dedup → Source Quality → Signal Extraction"""

    @staticmethod
    def filter_relevance(articles: List[Dict], symbol: str) -> List[Dict]:
        """Stage 1: Match articles to specific ticker, remove weak mentions"""
        if not symbol:
            return articles
        relevant = []
        sym_lower = symbol.lower()
        for a in articles:
            title = a.get("title", "").lower()
            text = a.get("text", "").lower()
            # Direct symbol mention or strong relevance
            if (sym_lower in title or
                f"${sym_lower}" in title or
                sym_lower in text[:200] or
                a.get("av_relevance", 0) > 0.3):
                a["relevance_score"] = 1.0
                relevant.append(a)
            elif sym_lower in text:
                a["relevance_score"] = 0.5
                relevant.append(a)
        return relevant

    @staticmethod
    def deduplicate(articles: List[Dict]) -> List[Dict]:
        """Stage 2: Remove duplicate or near-identical articles, group similar headlines"""
        seen_hashes = set()
        unique = []
        for a in articles:
            title = a.get("title", "").lower()
            words = sorted(set(re.sub(r'[^a-z0-9\s]', '', title).split()))[:8]
            fingerprint = hashlib.md5(" ".join(words).encode()).hexdigest()[:12]
            if fingerprint not in seen_hashes:
                seen_hashes.add(fingerprint)
                unique.append(a)
        return unique

    @staticmethod
    def rank_source_quality(articles: List[Dict]) -> List[Dict]:
        """Stage 3: Rank and weight by source credibility"""
        for a in articles:
            source = a.get("source", "").lower()
            cred = SOURCE_CREDIBILITY.get("default", 0.55)
            for key, val in SOURCE_CREDIBILITY.items():
                if key in source:
                    cred = val
                    break
            a["source_credibility"] = cred
        # Sort by credibility (highest first)
        articles.sort(key=lambda x: x.get("source_credibility", 0.5), reverse=True)
        return articles

    @staticmethod
    def extract_signals(articles: List[Dict]) -> List[Dict]:
        """Stage 4: Extract only meaningful events, filter out filler content"""
        filler_patterns = [
            r"what.*should.*know", r"top.*stocks.*to.*watch",
            r"why.*investors.*should", r"can.*stock.*reach",
            r"should.*you.*buy", r"is.*good.*investment",
            r"morning.*briefing", r"market.*wrap",
        ]
        signal_articles = []
        for a in articles:
            title_lower = a.get("title", "").lower()
            is_filler = any(re.search(p, title_lower) for p in filler_patterns)
            if is_filler:
                a["is_filler"] = True
                # Still include but mark as low-signal
                a["signal_quality"] = 0.3
            else:
                a["is_filler"] = False
                a["signal_quality"] = a.get("source_credibility", 0.55)
            signal_articles.append(a)
        return signal_articles

    @staticmethod
    def run_pipeline(articles: List[Dict], symbol: str) -> Dict:
        """Run full filtering pipeline, return results with stats"""
        raw_count = len(articles)
        relevant = NewsFilterPipeline.filter_relevance(articles, symbol)
        deduped = NewsFilterPipeline.deduplicate(relevant)
        ranked = NewsFilterPipeline.rank_source_quality(deduped)
        filtered = NewsFilterPipeline.extract_signals(ranked)

        # Separate high-signal from filler
        high_signal = [a for a in filtered if not a.get("is_filler", False)]

        return {
            "all_filtered": filtered,
            "high_signal": high_signal,
            "stats": {
                "raw_ingested": raw_count,
                "after_relevance": len(relevant),
                "after_dedup": len(deduped),
                "high_signal_count": len(high_signal),
                "filler_removed": len(filtered) - len(high_signal),
            }
        }


# ===================== NEWS VELOCITY DETECTOR =====================

class NewsVelocityDetector:
    """Detect acceleration in news coverage (article rate, multi-source convergence)"""

    @staticmethod
    def compute(articles: List[Dict]) -> Dict:
        total = len(articles)
        if total == 0:
            return {"velocity": "none", "velocity_score": 0, "articles_24h": 0, "sources": 0, "trend": "flat"}

        now = datetime.now(timezone.utc)
        articles_24h = 0
        articles_4h = 0
        sources_set = set()

        for a in articles:
            pub = a.get("published", "")
            sources_set.add(a.get("source", "").lower()[:20])
            try:
                if pub:
                    ts = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                    age_h = (now - ts).total_seconds() / 3600
                    if age_h <= 24:
                        articles_24h += 1
                    if age_h <= 4:
                        articles_4h += 1
            except (ValueError, TypeError):
                pass

        num_sources = len(sources_set)
        # Velocity scoring
        velocity_score = 0
        velocity_score += min(40, articles_24h * 4)  # Up to 40 for volume
        velocity_score += min(30, articles_4h * 10)   # Up to 30 for recency
        velocity_score += min(30, num_sources * 8)     # Up to 30 for source diversity

        if velocity_score >= 70:
            velocity = "high"
        elif velocity_score >= 40:
            velocity = "medium"
        else:
            velocity = "low"

        # Trend: are articles accelerating?
        trend = "flat"
        if articles_4h >= 3:
            trend = "accelerating"
        elif articles_24h >= 5 and articles_4h >= 1:
            trend = "steady"
        elif articles_24h <= 1:
            trend = "decelerating"

        return {
            "velocity": velocity,
            "velocity_score": min(100, velocity_score),
            "articles_24h": articles_24h,
            "articles_4h": articles_4h,
            "sources": num_sources,
            "trend": trend,
        }


# ===================== CATALYST SCORER =====================

class CatalystScorer:
    """Compute catalyst strength score (0-100) and trade-oriented category"""

    @staticmethod
    def score(ai_analysis: Dict, velocity: Dict, article_count: int) -> Dict:
        """Combine sentiment + catalyst + velocity + credibility into final score"""
        sentiment_score = ai_analysis.get("sentiment_score", 0)
        catalyst_strength = ai_analysis.get("catalyst_strength", 0)
        catalyst_type = ai_analysis.get("catalyst_type", "none")
        velocity_score = velocity.get("velocity_score", 0)

        # Base: catalyst type weight
        type_weight = CATALYST_WEIGHTS.get(catalyst_type, 0)

        # Final catalyst score (weighted combination)
        final = 0
        final += min(35, catalyst_strength * 0.35)   # AI catalyst up to 35
        final += min(25, type_weight * 0.25)           # Type weight up to 25
        final += min(20, abs(sentiment_score) * 0.2)   # Sentiment magnitude up to 20
        final += min(20, velocity_score * 0.2)          # Velocity up to 20

        final = min(100, int(final))

        # Determine catalyst label
        abs_sent = abs(sentiment_score)
        is_bullish = sentiment_score > 0
        if final >= 80:
            label = "STRONG_BULLISH" if is_bullish else "STRONG_BEARISH"
        elif final >= 60:
            label = "MODERATE_BULLISH" if is_bullish else "MODERATE_BEARISH"
        else:
            label = "WEAK_NOISE"

        # Trade-oriented category
        if final >= 85 and velocity.get("velocity", "low") != "low":
            category = "HOT"
        elif final >= 70:
            category = "BULLISH" if is_bullish else "BEARISH"
        elif final >= 50:
            category = "WATCHLIST"
        else:
            category = "IGNORE"

        # Trade impact
        if category == "HOT":
            trade_impact = "HIGH"
        elif category in ("BULLISH", "BEARISH"):
            trade_impact = "MEDIUM"
        else:
            trade_impact = "LOW"

        # Actionable description (replace vague language)
        if category == "HOT":
            description = f"HOT: Strong {'bullish' if is_bullish else 'bearish'} catalyst — trade candidate"
        elif category in ("BULLISH", "BEARISH"):
            description = f"{category}: moderate signal — monitor for confirmation"
        elif category == "WATCHLIST":
            description = "WATCHLIST: moderate signal — NOT tradeable"
        else:
            description = "IGNORE: low signal"

        return {
            "catalyst_score": final,
            "catalyst_label": label,
            "catalyst_type": catalyst_type,
            "category": category,
            "trade_impact": trade_impact,
            "description": description,
            "is_tradeable": category == "HOT",
            "components": {
                "catalyst_strength": catalyst_strength,
                "type_weight": type_weight,
                "sentiment_magnitude": abs_sent,
                "velocity_contribution": velocity_score,
            }
        }


# ===================== AI NEWS ANALYZER =====================

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
                "You are a professional financial trading analyst. Analyze news articles for actionable trading signals. "
                "Be direct and decisive. DO NOT use vague language like 'modestly bullish'. "
                "Use clear labels: STRONG BULLISH, MODERATE BEARISH, NOT TRADEABLE, etc. "
                "Return ONLY valid JSON with no markdown formatting."
            )
        )
        chat.with_model("openai", "gpt-5.2")
        return chat

    async def analyze_batch(self, symbol: str, articles: List[Dict]) -> Dict:
        """Analyze articles using GPT-5.2 for actionable trading signals"""
        if not EMERGENT_KEY or not articles:
            return self._fallback_analysis(articles)

        try:
            from emergentintegrations.llm.chat import UserMessage

            # Use top articles (by credibility and signal quality)
            top_articles = sorted(articles, key=lambda x: x.get("signal_quality", 0.5), reverse=True)[:12]

            article_text = ""
            for i, a in enumerate(top_articles):
                title = a.get("title", "No title")
                text = a.get("text", "")[:250]
                source = a.get("source", "Unknown")
                cred = a.get("source_credibility", 0.5)
                article_text += f"\n{i+1}. [{source}] (cred:{cred:.1f}) {title}\n   {text}\n"

            prompt = f"""Analyze these {len(top_articles)} news articles for {symbol}. Focus on ACTIONABLE trading signals.

{article_text}

Return this exact JSON structure:
{{
  "sentiment_score": <number -100 to +100>,
  "sentiment_label": "<Strong Bullish|Bullish|Neutral|Bearish|Strong Bearish>",
  "catalyst_detected": <true|false>,
  "catalyst_type": "<earnings_surprise|merger_acquisition|guidance_change|partnership|product_launch|analyst_upgrade|analyst_downgrade|regulatory_news|insider_activity|viral_momentum|dividend_buyback|none>",
  "catalyst_strength": <0-100>,
  "news_momentum": "<accelerating|stable|decelerating>",
  "risk_flag": <true|false>,
  "risk_reason": "<string or null>",
  "is_tradeable": <true|false>,
  "trade_reasoning": "<one line: why this IS or IS NOT a tradeable signal>",
  "top_articles": [
    {{
      "index": <1-based>,
      "relevance": <0-100>,
      "sentiment": "<strong_positive|positive|neutral|negative|strong_negative>",
      "why_it_matters": "<one actionable line>",
      "catalyst_contribution": "<string>"
    }}
  ],
  "one_line_summary": "<direct, actionable assessment - no vague language>"
}}

RULES:
- Do NOT use words like "modestly", "somewhat", "slightly"
- Use clear labels: "Strong bullish catalyst - trade candidate" or "Weak signal - NOT tradeable"
- catalyst_strength should reflect actual impact potential (0=noise, 100=major event)
- is_tradeable = true ONLY if catalyst_strength >= 70 AND clear directional signal"""

            chat = self._get_chat(f"news_{symbol}_{datetime.now().strftime('%H%M')}")
            msg = UserMessage(text=prompt)
            response = await chat.send_message(msg)

            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
                json_str = re.sub(r'\s*```$', '', json_str)

            import json
            result = json.loads(json_str)

            # Enrich top_articles with actual article data
            for ta in result.get("top_articles", []):
                idx = ta.get("index", 1) - 1
                if 0 <= idx < len(top_articles):
                    ta["title"] = top_articles[idx].get("title", "")
                    ta["url"] = top_articles[idx].get("url", "")
                    ta["source"] = top_articles[idx].get("source", "")
                    ta["published"] = top_articles[idx].get("published", "")
                    ta["source_credibility"] = top_articles[idx].get("source_credibility", 0.5)

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
                "is_tradeable": False,
                "trade_reasoning": "No news available",
                "top_articles": [], "one_line_summary": "No news available",
                "article_count": 0, "ai_powered": False,
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }

        positive_words = {"surge", "beat", "upgrade", "growth", "profit", "rally", "strong",
                          "record", "bullish", "outperform", "buy", "raise", "positive",
                          "breakthrough", "soar", "jumps", "rocket"}
        negative_words = {"fall", "drop", "miss", "downgrade", "loss", "decline", "weak",
                          "bearish", "sell", "cut", "negative", "warning", "layoff", "crash",
                          "plunge", "sink", "tumble"}
        catalyst_words = {"earnings", "merger", "acquisition", "guidance", "fda", "approval",
                          "launch", "dividend", "buyback", "split", "ipo", "insider",
                          "partnership", "deal", "upgrade", "downgrade"}

        pos_count = 0
        neg_count = 0
        catalyst_found = False
        catalyst_type = "none"

        for a in articles:
            text = (a.get("title", "") + " " + a.get("text", "")).lower()
            weight = a.get("source_credibility", 0.55)
            pos_count += sum(weight for w in positive_words if w in text)
            neg_count += sum(weight for w in negative_words if w in text)
            for w in catalyst_words:
                if w in text:
                    catalyst_found = True
                    if w in ("earnings",):
                        catalyst_type = "earnings_surprise"
                    elif w in ("merger", "acquisition", "deal"):
                        catalyst_type = "merger_acquisition"
                    elif w in ("guidance",):
                        catalyst_type = "guidance_change"
                    elif w in ("fda", "approval", "launch"):
                        catalyst_type = "product_launch"
                    elif w in ("upgrade",):
                        catalyst_type = "analyst_upgrade"
                    elif w in ("downgrade",):
                        catalyst_type = "analyst_downgrade"
                    elif w in ("partnership",):
                        catalyst_type = "partnership"

            av_sent = a.get("av_sentiment")
            if av_sent is not None:
                if av_sent > 0.15:
                    pos_count += 2
                elif av_sent < -0.15:
                    neg_count += 2

        total = pos_count + neg_count
        sentiment_score = int(((pos_count - neg_count) / total) * 100) if total > 0 else 0

        if sentiment_score > 40:
            sentiment_label = "Strong Bullish"
        elif sentiment_score > 15:
            sentiment_label = "Bullish"
        elif sentiment_score < -40:
            sentiment_label = "Strong Bearish"
        elif sentiment_score < -15:
            sentiment_label = "Bearish"
        else:
            sentiment_label = "Neutral"

        catalyst_strength = (CATALYST_WEIGHTS.get(catalyst_type, 0) * 0.8) if catalyst_found else 0

        top_articles = []
        for i, a in enumerate(articles[:5]):
            top_articles.append({
                "index": i + 1,
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("source", ""),
                "published": a.get("published", ""),
                "source_credibility": a.get("source_credibility", 0.5),
                "relevance": 80 - i * 10,
                "sentiment": "positive" if sentiment_score > 10 else "negative" if sentiment_score < -10 else "neutral",
                "why_it_matters": a.get("title", "")[:80]
            })

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "catalyst_detected": catalyst_found,
            "catalyst_type": catalyst_type,
            "catalyst_strength": int(catalyst_strength),
            "news_momentum": "accelerating" if len(articles) > 8 else "stable",
            "risk_flag": sentiment_score < -40,
            "risk_reason": "Strong negative sentiment" if sentiment_score < -40 else None,
            "is_tradeable": catalyst_found and catalyst_strength >= 70 and abs(sentiment_score) >= 30,
            "trade_reasoning": f"Catalyst: {catalyst_type}, Sentiment: {sentiment_label}" if catalyst_found else "No catalyst detected - NOT tradeable",
            "top_articles": top_articles,
            "one_line_summary": f"{len(articles)} articles analyzed - {sentiment_label}" + (f" - {catalyst_type}" if catalyst_found else ""),
            "article_count": len(articles),
            "ai_powered": False,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }


# ===================== MAIN ENGINE =====================

class EnhancedNewsSentimentEngine:
    """Orchestrates large-scale news ingestion, filtering, and AI analysis"""

    def __init__(self, db):
        self.db = db
        self.analyzer = AINewsAnalyzer()

    async def analyze_stock(self, symbol: str, use_cache: bool = True) -> Dict:
        """Full pipeline: Fetch → Filter → Analyze → Score → Categorize → Cache"""
        # Check cache (15 min TTL)
        if use_cache:
            cached = await self.db.news_analysis.find_one({"symbol": symbol}, {"_id": 0})
            if cached:
                analyzed_at = cached.get("analyzed_at", "")
                if analyzed_at:
                    try:
                        ts = datetime.fromisoformat(analyzed_at.replace("Z", "+00:00"))
                        if (datetime.now(timezone.utc) - ts).total_seconds() < 900:
                            return cached
                    except Exception:
                        pass

        # Stage 1: Large-scale ingestion from all sources
        results = await asyncio.gather(
            NewsFetcher.fetch_fmp(symbol, limit=50),
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

        all_articles.sort(key=lambda x: x.get("published", ""), reverse=True)

        # Stage 2: Multi-layer filtering pipeline
        pipeline_result = NewsFilterPipeline.run_pipeline(all_articles, symbol)
        filtered_articles = pipeline_result["high_signal"]
        filter_stats = pipeline_result["stats"]

        # Stage 3: News velocity detection
        velocity = NewsVelocityDetector.compute(filtered_articles)

        # Stage 4: AI analysis
        analysis = await self.analyzer.analyze_batch(symbol, filtered_articles)

        # Stage 5: Catalyst scoring + trade categorization
        catalyst_data = CatalystScorer.score(analysis, velocity, len(filtered_articles))

        # Merge into final result
        result = {
            **analysis,
            "symbol": symbol,
            "total_raw_articles": len(all_articles),
            "unique_articles": filter_stats.get("after_dedup", 0),
            "high_signal_articles": filter_stats.get("high_signal_count", 0),
            "sources": source_counts,
            "filter_stats": filter_stats,
            "news_velocity": velocity.get("velocity", "low"),
            "news_velocity_score": velocity.get("velocity_score", 0),
            "velocity_details": velocity,
            "catalyst_score": catalyst_data["catalyst_score"],
            "catalyst_label": catalyst_data["catalyst_label"],
            "category": catalyst_data["category"],
            "trade_impact": catalyst_data["trade_impact"],
            "trade_description": catalyst_data["description"],
            "is_tradeable": catalyst_data["is_tradeable"],
            "catalyst_components": catalyst_data["components"],
            # For direct integration with DayTradingEngine:
            "composite_score": (analysis.get("sentiment_score", 0) + 100) / 200,  # normalize to 0-1
        }

        # Cache result
        await self.db.news_analysis.update_one(
            {"symbol": symbol}, {"$set": result}, upsert=True
        )

        return result

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
        """Get recent high-impact news across all analyzed stocks (HOT and BULLISH categories)"""
        cursor = self.db.news_analysis.find(
            {"catalyst_score": {"$gte": 50}},
            {"_id": 0, "symbol": 1, "one_line_summary": 1, "catalyst_type": 1,
             "catalyst_score": 1, "catalyst_label": 1, "category": 1,
             "trade_impact": 1, "trade_description": 1,
             "sentiment_score": 1, "sentiment_label": 1,
             "news_velocity": 1, "news_velocity_score": 1,
             "is_tradeable": 1,
             "top_articles": {"$slice": 3}, "analyzed_at": 1}
        ).sort("catalyst_score", -1).limit(30)
        return await cursor.to_list(30)

    async def get_sentiment_overview(self) -> Dict:
        """Get sentiment distribution + category breakdown across all analyzed stocks"""
        sentiment_pipeline = [
            {"$group": {
                "_id": "$sentiment_label",
                "count": {"$sum": 1},
                "avg_score": {"$avg": "$sentiment_score"}
            }}
        ]
        category_pipeline = [
            {"$group": {
                "_id": "$category",
                "count": {"$sum": 1},
                "avg_catalyst": {"$avg": "$catalyst_score"}
            }}
        ]
        sent_dist = await self.db.news_analysis.aggregate(sentiment_pipeline).to_list(10)
        cat_dist = await self.db.news_analysis.aggregate(category_pipeline).to_list(10)

        total = await self.db.news_analysis.count_documents({})
        tradeable = await self.db.news_analysis.count_documents({"is_tradeable": True})
        hot = await self.db.news_analysis.count_documents({"category": "HOT"})

        return {
            "total_analyzed": total,
            "tradeable_signals": tradeable,
            "hot_stocks": hot,
            "sentiment_distribution": {
                d["_id"]: {"count": d["count"], "avg_score": round(d["avg_score"], 1)}
                for d in sent_dist if d["_id"]
            },
            "category_distribution": {
                d["_id"]: {"count": d["count"], "avg_catalyst": round(d.get("avg_catalyst", 0), 1)}
                for d in cat_dist if d["_id"]
            },
        }
