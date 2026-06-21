import { useNavigate } from "react-router-dom";
import {
  MARKET_INDICES, SECTOR_PERFORMANCE, MACRO_INDICATORS,
  EARNINGS_CALENDAR, ANALYST_ACTIONS, NEWS_FEED, DISCOVERY_RESULTS,
} from "@/lib/mockData";
import {
  TrendingUp, TrendingDown, Calendar, Sparkles,
  Telescope, Newspaper, AlertCircle, ChevronRight, Globe,
} from "lucide-react";

const fmt = (n, d = 2) => Number(n).toFixed(d);

function IndexTicker({ idx }) {
  const up = idx.change >= 0;
  return (
    <div className="glass-card px-4 py-3 flex items-center justify-between gap-4">
      <div>
        <p className="text-[11px] text-slate-500 font-medium">{idx.name}</p>
        <p className="text-white font-bold font-mono text-base mt-0.5">
          {idx.ticker === "TNX" ? `${fmt(idx.value)}%` : idx.value.toLocaleString()}
        </p>
      </div>
      <div className={`text-right ${up ? "text-emerald-400" : "text-red-400"}`}>
        <p className="text-xs font-mono">{up ? "+" : ""}{fmt(idx.change)}</p>
        <p className="text-xs font-semibold">{up ? "+" : ""}{fmt(idx.pct)}%</p>
      </div>
    </div>
  );
}

function SectorBar({ s }) {
  const up = s.pct >= 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-400 w-28 shrink-0 truncate">{s.name}</span>
      <div className="flex-1 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${Math.min(Math.abs(s.pct) * 15, 100)}%`, background: up ? "#10b981" : "#ef4444" }}
        />
      </div>
      <span className={`text-xs font-mono w-12 text-right shrink-0 ${up ? "text-emerald-400" : "text-red-400"}`}>
        {up ? "+" : ""}{fmt(s.pct)}%
      </span>
    </div>
  );
}

function MacroCard({ m }) {
  const TrendIcon = m.trend === "up" ? TrendingUp : m.trend === "down" ? TrendingDown : null;
  const trendColor = m.trend === "up" ? "text-emerald-400" : "text-red-400";
  return (
    <div className="metric-card flex items-start justify-between gap-2">
      <div className="min-w-0">
        <p className="text-[10px] text-slate-500 font-medium">{m.label}</p>
        <p className="text-white font-bold text-base mt-0.5 font-mono">{m.value}</p>
        <p className="text-[10px] text-slate-600 mt-1 leading-relaxed">{m.note}</p>
      </div>
      {TrendIcon && <TrendIcon className={`w-4 h-4 shrink-0 mt-1 ${trendColor}`} />}
    </div>
  );
}

function NewsItem({ n, onClick }) {
  const sentimentClass = {
    positive: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    negative: "text-red-400 bg-red-500/10 border-red-500/20",
  }[n.sentiment] || "text-slate-400 bg-slate-500/10 border-slate-500/20";

  return (
    <div onClick={onClick} className="p-4 border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] cursor-pointer transition-colors">
      <div className="flex items-start gap-3">
        <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full border shrink-0 mt-0.5 ${sentimentClass}`}>
          {n.catalystType}
        </span>
        <div className="min-w-0">
          <p className="text-sm text-slate-200 font-medium leading-snug line-clamp-2">{n.title}</p>
          <div className="flex items-center gap-2 mt-1.5">
            {n.ticker !== "MACRO" && <span className="text-xs font-mono text-blue-400">{n.ticker}</span>}
            <span className="text-xs text-slate-600">{n.source} · {n.time}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function DiscoveryCard({ d, onClick }) {
  const scoreClass = d.opportunityScore >= 80 ? "score-high" : d.opportunityScore >= 65 ? "score-mid" : "score-low";
  const up = d.dcfUpside >= 0;
  return (
    <div onClick={onClick} className="glass-card p-4 hover:border-white/[0.1] cursor-pointer transition-all">
      <div className="flex items-start gap-3 mb-3">
        <div className={`score-ring ${scoreClass} shrink-0`}>{d.opportunityScore}</div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-mono text-blue-400">{d.ticker}</p>
          <p className="text-sm font-semibold text-slate-200 truncate">{d.name}</p>
          <p className="text-[11px] text-slate-500">{d.sector}</p>
        </div>
        <span className={`text-sm font-bold font-mono ${up ? "text-emerald-400" : "text-red-400"}`}>
          {up ? "+" : ""}{fmt(d.dcfUpside)}%
        </span>
      </div>
      <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">{d.thesis}</p>
      <div className="flex flex-wrap gap-1 mt-3">
        {d.catalysts.slice(0, 2).map((c) => (
          <span key={c} className="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/15 rounded-full px-2 py-0.5">{c}</span>
        ))}
      </div>
    </div>
  );
}

const AI_COMMENTARY = [
  "Markets are digesting a complex macro backdrop: the Fed's higher-for-longer stance continues to weigh on rate-sensitive sectors, while AI infrastructure spending is creating a powerful growth tailwind for select technology names. The divergence between AI beneficiaries (NVDA, MSFT, AVGO) and rate-sensitive plays has reached historical extremes.",
  "The most compelling opportunities today appear in: (1) AI infrastructure with durable pricing power, (2) quality compounders trading at below-average multiples, and (3) healthcare names with pipeline optionality. Rotation from momentum to quality may be approaching as earnings season begins.",
  "Key risk to monitor: Treasury yields above 4.5% would likely trigger a valuation reset across high-multiple growth stocks. Conversely, any signal of an earlier Fed pivot would be a significant positive catalyst across the board.",
];

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white">Market Command Center</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-full px-3 py-1.5">
          <AlertCircle className="w-3.5 h-3.5" />
          Demo Mode — connect API keys for live data
        </div>
      </div>

      {/* Market indices */}
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
        {MARKET_INDICES.map((idx) => <IndexTicker key={idx.ticker} idx={idx} />)}
      </div>

      {/* AI commentary + Sector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white">AI Market Commentary</h2>
            <span className="ml-auto text-[10px] text-slate-600 bg-slate-800/60 rounded-full px-2 py-0.5">Simulated · connect OpenAI for live</span>
          </div>
          <div className="space-y-3">
            {AI_COMMENTARY.map((p, i) => <p key={i} className="text-sm text-slate-400 leading-relaxed">{p}</p>)}
          </div>
        </div>

        <div className="glass-card p-5">
          <h2 className="text-sm font-semibold text-white mb-4">Sector Performance</h2>
          <div className="space-y-3">
            {SECTOR_PERFORMANCE.map((s) => <SectorBar key={s.name} s={s} />)}
          </div>
        </div>
      </div>

      {/* Macro + Earnings + Analyst */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-4 h-4 text-violet-400" />
            <h2 className="text-sm font-semibold text-white">Macro Indicators</h2>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {MACRO_INDICATORS.slice(0, 6).map((m) => <MacroCard key={m.label} m={m} />)}
          </div>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-white">Earnings Calendar</h2>
          </div>
          <div className="space-y-0.5">
            {EARNINGS_CALENDAR.slice(0, 8).map((e) => (
              <div
                key={e.ticker + e.date}
                onClick={() => navigate(`/research?ticker=${e.ticker}`)}
                className="flex items-center gap-3 py-2 px-2 rounded-lg hover:bg-white/[0.04] cursor-pointer transition-colors"
              >
                <span className="text-[11px] text-slate-600 w-12 shrink-0">{e.date}</span>
                <span className="text-xs font-mono font-bold text-blue-400 w-12 shrink-0">{e.ticker}</span>
                <span className="text-xs text-slate-400 flex-1 truncate">{e.name}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${e.type === "before" ? "bg-blue-500/10 text-blue-400" : "bg-violet-500/10 text-violet-400"}`}>
                  {e.type === "before" ? "BMO" : "AMC"}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white">Analyst Actions</h2>
          </div>
          <div className="space-y-0.5">
            {ANALYST_ACTIONS.map((a, i) => (
              <div
                key={i}
                onClick={() => navigate(`/research?ticker=${a.ticker}`)}
                className="flex items-center gap-3 py-2 px-2 rounded-lg hover:bg-white/[0.04] cursor-pointer transition-colors"
              >
                <span className="text-sm font-mono font-bold text-blue-400 w-12 shrink-0">{a.ticker}</span>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border shrink-0 ${
                  a.action === "Upgrade" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : a.action === "Downgrade" ? "bg-red-500/10 text-red-400 border-red-500/20"
                  : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                }`}>
                  {a.action}
                </span>
                <div className="min-w-0">
                  <p className="text-xs text-slate-400 truncate">{a.analyst}</p>
                  <p className="text-[11px] text-slate-600">PT ${a.pt} · {a.to}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* News + Discovery */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card overflow-hidden">
          <div className="flex items-center justify-between p-5 border-b border-white/[0.04]">
            <div className="flex items-center gap-2">
              <Newspaper className="w-4 h-4 text-slate-400" />
              <h2 className="text-sm font-semibold text-white">News & Catalysts</h2>
            </div>
            <button onClick={() => navigate("/news")} className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300">
              View all <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          {NEWS_FEED.slice(0, 4).map((n) => (
            <NewsItem
              key={n.id}
              n={n}
              onClick={() => n.ticker !== "MACRO" && navigate(`/research?ticker=${n.ticker}`)}
            />
          ))}
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Telescope className="w-4 h-4 text-violet-400" />
              <h2 className="text-sm font-semibold text-white">AI Discovery — Top Opportunities</h2>
            </div>
            <button onClick={() => navigate("/discovery")} className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300">
              View all <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {DISCOVERY_RESULTS.slice(0, 4).map((d) => (
              <DiscoveryCard key={d.ticker} d={d} onClick={() => navigate(`/research?ticker=${d.ticker}`)} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
