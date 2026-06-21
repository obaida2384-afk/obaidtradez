import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { NEWS_FEED } from "@/lib/mockData";
import { Newspaper, Filter, TrendingUp, TrendingDown, Minus, ArrowUpRight } from "lucide-react";

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

const CATALYST_TYPES = ["All", "Analyst Upgrade", "Earnings Beat", "Product Catalyst", "Macro Event", "Regulatory Risk"];
const SENTIMENTS = ["All", "positive", "negative", "neutral"];

// Extend the news feed for a fuller page
const EXTENDED_NEWS = [
  ...NEWS_FEED,
  {
    id: 7,
    title: "Microsoft Azure AI Revenue Growing at 60%+ Annually — CFO Confirms at Investor Day",
    summary: "Microsoft CFO Amy Hood confirmed Azure AI services are growing at over 60% annually, now representing a meaningful portion of Azure's total revenue. The company also reiterated its partnership with OpenAI is expected to generate $1B+ in revenue in FY2025.",
    source: "Microsoft Investor Day",
    time: "3d ago",
    ticker: "MSFT",
    sentiment: "positive",
    catalystType: "Product Catalyst",
    catalystStrength: "High",
    financialImpact: "Azure AI revenue recognition accelerates estimate revisions upward for FY2025 and FY2026.",
  },
  {
    id: 8,
    title: "Broadcom VMware Integration Ahead of Schedule, Raising FY2024 Synergy Guidance to $8.5B",
    summary: "Broadcom management raised its VMware cost synergy guidance to $8.5B within 3 years, up from $8.2B. Enterprise software renewal rates exceeded expectations. CEO Hock Tan stated most major VMware customer transitions are complete.",
    source: "Broadcom Earnings Call",
    time: "4d ago",
    ticker: "AVGO",
    sentiment: "positive",
    catalystType: "Earnings Beat",
    catalystStrength: "High",
    financialImpact: "Better-than-expected integration drives significant EBITDA margin expansion ahead of schedule.",
  },
  {
    id: 9,
    title: "Tesla Cuts Prices Again in China as Competition from BYD Intensifies",
    summary: "Tesla reduced prices for the Model 3 and Model Y in China by 5–8%, the third price cut this year. BYD continues to gain market share with competitively priced EVs. Tesla's China deliveries fell 6% YoY in Q1.",
    source: "Reuters",
    time: "5d ago",
    ticker: "TSLA",
    sentiment: "negative",
    catalystType: "Regulatory Risk",
    catalystStrength: "Medium",
    financialImpact: "Margin pressure intensifies. China segment gross margins may decline below 15% — a concern for overall profitability.",
  },
];

function NewsCard({ n, onClick }) {
  const s = SENTIMENT_STYLE[n.sentiment] || SENTIMENT_STYLE.neutral;
  const SentIcon = n.sentiment === "positive" ? TrendingUp : n.sentiment === "negative" ? TrendingDown : Minus;

  return (
    <div onClick={onClick} className="glass-card p-5 hover:border-white/[0.1] cursor-pointer transition-all group">
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

      <p className="text-xs text-slate-500 leading-relaxed mb-3 line-clamp-2">{n.summary}</p>

      {n.financialImpact && (
        <div className="p-2.5 bg-white/[0.03] border border-white/[0.04] rounded-lg mb-3">
          <p className="text-[10px] font-semibold text-violet-400 uppercase tracking-wider mb-0.5">Financial Impact</p>
          <p className="text-xs text-slate-400 leading-relaxed">{n.financialImpact}</p>
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-[11px] text-slate-600">{n.source} · {n.time}</span>
        {n.ticker !== "MACRO" && (
          <span className="flex items-center gap-1 text-[11px] text-emerald-400 group-hover:gap-1.5 transition-all">
            Research <ArrowUpRight className="w-3 h-3" />
          </span>
        )}
      </div>
    </div>
  );
}

export default function News() {
  const navigate = useNavigate();
  const [catalystFilter, setCatalystFilter] = useState("All");
  const [sentimentFilter, setSentimentFilter] = useState("All");
  const [tickerFilter, setTickerFilter] = useState("");

  const filtered = EXTENDED_NEWS.filter((n) => {
    const matchCatalyst = catalystFilter === "All" || n.catalystType === catalystFilter;
    const matchSentiment = sentimentFilter === "All" || n.sentiment === sentimentFilter;
    const matchTicker = !tickerFilter || n.ticker.includes(tickerFilter.toUpperCase()) || n.name?.toLowerCase().includes(tickerFilter.toLowerCase());
    return matchCatalyst && matchSentiment && matchTicker;
  });

  const positiveCount = EXTENDED_NEWS.filter((n) => n.sentiment === "positive").length;
  const negativeCount = EXTENDED_NEWS.filter((n) => n.sentiment === "negative").length;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Newspaper className="w-5 h-5 text-slate-400" />
            <h1 className="text-2xl font-bold text-white">News & Catalysts</h1>
          </div>
          <p className="text-sm text-slate-500">
            {EXTENDED_NEWS.length} items · {positiveCount} positive · {negativeCount} negative catalysts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1.5 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            AI sentiment classification active
          </span>
        </div>
      </div>

      {/* Sentiment overview */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Positive Catalysts", count: positiveCount, color: "text-emerald-400", bg: "bg-emerald-500/5 border-emerald-500/15" },
          { label: "Negative Catalysts", count: negativeCount, color: "text-red-400", bg: "bg-red-500/5 border-red-500/15" },
          { label: "High Impact Events", count: EXTENDED_NEWS.filter((n) => n.catalystStrength === "High").length, color: "text-violet-400", bg: "bg-violet-500/5 border-violet-500/15" },
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
          className="glass-card px-3 py-2 text-sm text-slate-300 outline-none placeholder:text-slate-600 w-36"
        />
        <select value={catalystFilter} onChange={(e) => setCatalystFilter(e.target.value)}
          className="glass-card px-3 py-2 text-sm text-slate-300 outline-none">
          {CATALYST_TYPES.map((t) => <option key={t} value={t} className="bg-slate-900">{t}</option>)}
        </select>
        <select value={sentimentFilter} onChange={(e) => setSentimentFilter(e.target.value)}
          className="glass-card px-3 py-2 text-sm text-slate-300 outline-none capitalize">
          {SENTIMENTS.map((s) => <option key={s} value={s} className="bg-slate-900 capitalize">{s === "All" ? "All sentiments" : s}</option>)}
        </select>
        <span className="text-xs text-slate-600">{filtered.length} items</span>
      </div>

      {/* News grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filtered.map((n) => (
          <NewsCard
            key={n.id}
            n={n}
            onClick={() => n.ticker !== "MACRO" && navigate(`/research?ticker=${n.ticker}`)}
          />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-20 text-slate-600">
          <Newspaper className="w-8 h-8 mx-auto mb-3 opacity-40" />
          <p>No news matches your filters</p>
        </div>
      )}

      <p className="text-xs text-slate-700 pb-4">
        Demo news data. Connect Benzinga, Polygon, or SEC EDGAR APIs in Settings for live news and filings.
      </p>
    </div>
  );
}
