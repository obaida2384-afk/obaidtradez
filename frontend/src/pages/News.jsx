import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { fetchMarketNews, fetchNewsSuggestions } from "@/lib/companyUniverse";
import { getRating } from "@/lib/rating";
import { Newspaper, Filter, TrendingUp, TrendingDown, Minus, ArrowUpRight, Sparkles } from "lucide-react";

const SENTIMENT_STYLE = {
  positive: { label: "Positive", color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  negative: { label: "Negative", color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
  neutral: { label: "Neutral", color: "text-slate-400", bg: "bg-slate-500/10 border-slate-500/20" },
};

const STRENGTH_STYLE = {
  High: "text-violet-400 bg-violet-500/10 border-violet-500/20",
  Medium: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  Low: "text-slate-400 bg-slate-500/10 border-slate-500/20",
};

const SENTIMENTS = ["All", "positive", "negative", "neutral"];

const titleCase = (s) =>
  String(s || "").replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()).trim();

function relTime(dateStr) {
  const t = Date.parse(dateStr);
  if (Number.isNaN(t)) return "";
  const diff = Date.now() - t;
  const m = Math.round(diff / 60000);
  if (m < 60) return `${Math.max(m, 1)}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}

// Topic noise from the news provider that should not surface as a catalyst type.
const JUNK_TOPICS = new Set(["paywall", "paylimitwall", "prnews", "pr", "general"]);

// Map a StockNewsAPI article into the card shape the page renders.
function mapArticle(a, idx) {
  const sentiment = String(a.sentiment || "neutral").toLowerCase();
  const tickers = a.tickers || [];
  const topic = (a.topics || []).find((t) => t && !JUNK_TOPICS.has(String(t).toLowerCase()));
  const strength = sentiment !== "neutral" ? "High" : tickers.length > 0 ? "Medium" : "Low";
  return {
    id: a.url || idx,
    title: a.title,
    summary: a.text,
    source: a.source || "Newswire",
    time: relTime(a.date),
    url: a.url,
    ticker: tickers[0] || "MACRO",
    allTickers: tickers,
    sentiment: ["positive", "negative", "neutral"].includes(sentiment) ? sentiment : "neutral",
    catalystType: topic ? titleCase(topic) : "Market News",
    catalystStrength: strength,
  };
}

function NewsCard({ n, onClick }) {
  const s = SENTIMENT_STYLE[n.sentiment] || SENTIMENT_STYLE.neutral;
  const SentIcon = n.sentiment === "positive" ? TrendingUp : n.sentiment === "negative" ? TrendingDown : Minus;

  return (
    <div onClick={onClick} data-testid="news-card" className="glass-card p-5 hover:border-white/[0.1] cursor-pointer transition-all group">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex flex-wrap gap-1.5">
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border flex items-center gap-1 ${s.bg} ${s.color}`}>
            <SentIcon className="w-2.5 h-2.5" />
            {s.label}
          </span>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${STRENGTH_STYLE[n.catalystStrength] || STRENGTH_STYLE.Low}`}>
            {n.catalystStrength} impact
          </span>
          <span className="text-[10px] text-slate-500 border border-white/[0.06] bg-white/[0.03] rounded-full px-2 py-0.5">
            {n.catalystType}
          </span>
        </div>
        {n.ticker !== "MACRO" && (
          <span className="font-mono font-bold text-blue-400 text-xs shrink-0">{n.ticker}</span>
        )}
      </div>

      <h3 className="text-sm font-semibold text-slate-100 leading-snug mb-2 group-hover:text-white transition-colors">
        {n.title}
      </h3>

      {n.summary && <p className="text-xs text-slate-500 leading-relaxed mb-3 line-clamp-2">{n.summary}</p>}

      <div className="flex items-center justify-between">
        <span className="text-[11px] text-slate-600">{n.source}{n.time ? ` · ${n.time}` : ""}</span>
        {n.ticker !== "MACRO" && (
          <span className="flex items-center gap-1 text-[11px] text-emerald-400 group-hover:gap-1.5 transition-all">
            Research <ArrowUpRight className="w-3 h-3" />
          </span>
        )}
      </div>
    </div>
  );
}

function SuggestionCard({ s, onClick }) {
  const sent = SENTIMENT_STYLE[String(s.newsSentiment || "neutral").toLowerCase()] || SENTIMENT_STYLE.neutral;
  const up = s.analystUpsidePct;
  const rec = getRating({ upsidePct: s.analystUpsidePct, opportunityScore: s.opportunityScore, newsSentiment: s.newsSentiment });
  return (
    <div onClick={onClick} data-testid="news-suggestion-card" className="glass-card p-4 hover:border-white/[0.1] cursor-pointer transition-all group min-w-[220px]">
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="font-mono font-bold text-blue-400 text-sm">{s.ticker}</span>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${sent.bg} ${sent.color}`}>{sent.label}</span>
      </div>
      <p className="text-xs font-semibold text-slate-200 truncate">{s.name}</p>
      <p className="text-[11px] text-slate-500 mb-2">{s.sector}</p>
      <div className="mb-2">
        <span data-testid="news-suggestion-rating" className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${rec.className}`}>{rec.label}</span>
      </div>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-slate-400">{s.price != null ? `$${s.price}` : "—"}</span>
        {up != null && (
          <span className={`font-mono font-semibold ${up >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {up >= 0 ? "+" : ""}{Number(up).toFixed(1)}% PT
          </span>
        )}
      </div>
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/[0.04] text-[10px] text-slate-600">
        <span>{s.newsMentions} mentions (30d)</span>
        <span className="flex items-center gap-1 text-emerald-400 group-hover:gap-1.5 transition-all">Research <ArrowUpRight className="w-3 h-3" /></span>
      </div>
    </div>
  );
}

export default function News() {
  const navigate = useNavigate();
  const [catalystFilter, setCatalystFilter] = useState("All");
  const [sentimentFilter, setSentimentFilter] = useState("All");
  const [tickerFilter, setTickerFilter] = useState("");
  const [articles, setArticles] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [news, sugg] = await Promise.all([
          fetchMarketNews(40).catch(() => ({ articles: [] })),
          fetchNewsSuggestions(10).catch(() => ({ suggestions: [] })),
        ]);
        setArticles((news.articles || []).filter((a) => a.title).map(mapArticle));
        setSuggestions(sugg.suggestions || []);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const CATALYST_TYPES = useMemo(
    () => ["All", ...Array.from(new Set(articles.map((n) => n.catalystType).filter(Boolean)))],
    [articles]
  );

  const filtered = articles.filter((n) => {
    const matchCatalyst = catalystFilter === "All" || n.catalystType === catalystFilter;
    const matchSentiment = sentimentFilter === "All" || n.sentiment === sentimentFilter;
    const matchTicker = !tickerFilter || (n.allTickers || []).some((t) => t.includes(tickerFilter.toUpperCase()));
    return matchCatalyst && matchSentiment && matchTicker;
  });

  const positiveCount = articles.filter((n) => n.sentiment === "positive").length;
  const negativeCount = articles.filter((n) => n.sentiment === "negative").length;
  const highImpactCount = articles.filter((n) => n.catalystStrength === "High").length;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Newspaper className="w-5 h-5 text-slate-400" />
            <h1 className="text-2xl font-bold text-white">News & Catalysts</h1>
          </div>
          <p className="text-sm text-slate-500">
            {articles.length} items · {positiveCount} positive · {negativeCount} negative catalysts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1.5 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Live sentiment classification active
          </span>
        </div>
      </div>

      {/* News-driven stock ideas */}
      {suggestions.length > 0 && (
        <div className="space-y-3" data-testid="news-suggestions">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-violet-400" />
            <h3 className="text-sm font-semibold text-white">News-Driven Stock Ideas</h3>
            <span className="text-[11px] text-slate-600">Most-mentioned names this month, backed by fundamentals</span>
          </div>
          <div className="flex gap-3 overflow-x-auto pb-2">
            {suggestions.map((s) => (
              <SuggestionCard key={s.ticker} s={s} onClick={() => navigate(`/research?ticker=${s.ticker}`)} />
            ))}
          </div>
        </div>
      )}

      {/* Sentiment overview */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Positive Catalysts", count: positiveCount, color: "text-emerald-400", bg: "bg-emerald-500/5 border-emerald-500/15" },
          { label: "Negative Catalysts", count: negativeCount, color: "text-red-400", bg: "bg-red-500/5 border-red-500/15" },
          { label: "High Impact Events", count: highImpactCount, color: "text-violet-400", bg: "bg-violet-500/5 border-violet-500/15" },
        ].map((item) => (
          <div key={item.label} className={`glass-card p-4 border ${item.bg} text-center`}>
            <p className={`text-2xl font-bold font-mono ${item.color}`}>{item.count}</p>
            <p className="text-xs text-slate-500 mt-1">{item.label}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Filter className="w-4 h-4 text-slate-500 shrink-0" />
        <input
          value={tickerFilter}
          onChange={(e) => setTickerFilter(e.target.value)}
          placeholder="Filter by ticker..."
          data-testid="news-ticker-filter"
          className="glass-card px-3 py-2 text-sm text-slate-300 outline-none placeholder:text-slate-600 w-36"
        />
        <select value={catalystFilter} onChange={(e) => setCatalystFilter(e.target.value)} data-testid="news-catalyst-filter"
          className="glass-card px-3 py-2 text-sm text-slate-300 outline-none">
          {CATALYST_TYPES.map((t) => <option key={t} value={t} className="bg-slate-900">{t}</option>)}
        </select>
        <select value={sentimentFilter} onChange={(e) => setSentimentFilter(e.target.value)} data-testid="news-sentiment-filter"
          className="glass-card px-3 py-2 text-sm text-slate-300 outline-none capitalize">
          {SENTIMENTS.map((s) => <option key={s} value={s} className="bg-slate-900 capitalize">{s === "All" ? "All sentiments" : s}</option>)}
        </select>
        <span className="text-xs text-slate-600">{filtered.length} items</span>
      </div>

      {/* News grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="news-grid">
        {filtered.map((n) => (
          <NewsCard
            key={n.id}
            n={n}
            onClick={() => n.ticker !== "MACRO" && navigate(`/research?ticker=${n.ticker}`)}
          />
        ))}
      </div>

      {loading && (
        <div className="text-center py-20 text-slate-600">
          <span className="w-5 h-5 border-2 border-slate-600/40 border-t-slate-400 rounded-full animate-spin inline-block mb-3" />
          <p>Loading live market news…</p>
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="text-center py-20 text-slate-600">
          <Newspaper className="w-8 h-8 mx-auto mb-3 opacity-40" />
          <p>No news matches your filters</p>
        </div>
      )}

      <p className="text-xs text-slate-700 pb-4" data-testid="news-data-note">
        Live market news and sentiment via StockNewsAPI. Stock ideas cross-reference news buzz with the enriched company universe. Educational research only — not investment advice.
      </p>
    </div>
  );
}
