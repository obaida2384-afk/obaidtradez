import { MACRO_INDICATORS, SECTOR_PERFORMANCE, MARKET_INDICES } from "@/lib/mockData";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell,
} from "recharts";
import { Globe, TrendingUp, TrendingDown, Brain, AlertTriangle } from "lucide-react";

const fmt = (n, d = 2) => Number(n).toFixed(d);

const RATE_HISTORY = [
  { date: "Jan 23", rate: 4.25 }, { date: "Mar 23", rate: 4.75 }, { date: "May 23", rate: 5.0 },
  { date: "Jul 23", rate: 5.25 }, { date: "Sep 23", rate: 5.50 }, { date: "Nov 23", rate: 5.50 },
  { date: "Jan 24", rate: 5.50 }, { date: "Mar 24", rate: 5.50 }, { date: "May 24", rate: 5.50 },
  { date: "Jun 24", rate: 5.50 },
];

const YIELD_CURVE = [
  { maturity: "1M", yield: 5.32 }, { maturity: "3M", yield: 5.28 }, { maturity: "6M", yield: 5.15 },
  { maturity: "1Y", yield: 5.02 }, { maturity: "2Y", yield: 4.70 }, { maturity: "5Y", yield: 4.44 },
  { maturity: "10Y", yield: 4.28 }, { maturity: "20Y", yield: 4.52 }, { maturity: "30Y", yield: 4.42 },
];

const AI_MACRO_COMMENTARY = [
  {
    title: "Interest Rate Environment",
    text: "The Federal Reserve has maintained the fed funds rate at 5.25–5.50% since July 2023, the highest since 2001. The market has consistently over-anticipated rate cuts, and the Fed has repeatedly pushed back. We remain in a 'higher for longer' environment. This is meaningful for equity valuations — discount rates matter, and a 5.5% risk-free rate competes directly with equity earnings yields.",
  },
  {
    title: "Inflation & Growth Balance",
    text: "Core PCE at 2.8% remains above the 2% target, though the trend is downward. GDP growth at 2.1% in Q1 2024 is resilient — the 'soft landing' narrative is gaining credibility. Consumer spending remains strong driven by wage growth and excess pandemic savings, though signs of fatigue are emerging among lower-income cohorts.",
  },
  {
    title: "AI & Technology Cycle",
    text: "AI infrastructure spending is the dominant investment theme. Hyperscaler capex is accelerating, with Microsoft, Google, Meta, and Amazon collectively spending $200B+ on AI infrastructure in 2024–2025. This is creating a powerful earnings cycle for semiconductors (NVDA, AVGO, AMD), networking (Arista), and cloud infrastructure. The question is whether AI ROI will materialize in time to sustain the capex cycle.",
  },
  {
    title: "Investment Implications",
    text: "In this environment: (1) Quality over growth — companies with strong FCF generation outperform when rates are high. (2) AI infrastructure beneficiaries have a durable multi-year tailwind regardless of broader market volatility. (3) Rate-sensitive sectors (Utilities, REITs, Consumer Staples) remain challenged until the Fed pivots. (4) International diversification (Europe, Japan) may offer better risk/reward as valuations are lower.",
  },
];

function MacroRow({ m }) {
  const TrendIcon = m.trend === "up" ? TrendingUp : m.trend === "down" ? TrendingDown : null;
  const trendColor = m.trend === "up" ? "text-emerald-400" : m.trend === "down" ? "text-red-400" : "text-slate-400";
  return (
    <div className="flex items-center gap-4 py-3 border-b border-white/[0.04] last:border-0">
      <div className="w-44 shrink-0">
        <p className="text-xs text-slate-400">{m.label}</p>
      </div>
      <div className="flex items-center gap-2 flex-1">
        <span className="font-mono font-bold text-white text-sm">{m.value}</span>
        {TrendIcon && <TrendIcon className={`w-4 h-4 ${trendColor}`} />}
      </div>
      <p className="text-xs text-slate-500 text-right max-w-xs">{m.note}</p>
    </div>
  );
}

export default function MarketMacro() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Globe className="w-5 h-5 text-blue-400" />
          <h1 className="text-2xl font-bold text-white">Market & Macro</h1>
        </div>
        <p className="text-sm text-slate-500">Understanding the macro environment and its impact on investment opportunities</p>
      </div>

      {/* Index overview */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {MARKET_INDICES.map((idx) => {
          const up = idx.change >= 0;
          return (
            <div key={idx.ticker} className="metric-card">
              <p className="text-[10px] text-slate-500">{idx.name}</p>
              <p className="font-mono font-bold text-white text-base mt-1">
                {idx.ticker === "TNX" ? `${fmt(idx.value)}%` : idx.value.toLocaleString()}
              </p>
              <p className={`text-xs font-mono ${up ? "text-emerald-400" : "text-red-400"}`}>
                {up ? "+" : ""}{fmt(idx.pct)}%
              </p>
            </div>
          );
        })}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Fed Funds Rate History</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={RATE_HISTORY} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis domain={[3.5, 6]} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
              <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }} formatter={(v) => `${v}%`} />
              <Line type="stepAfter" dataKey="rate" stroke="#3b82f6" strokeWidth={2} dot={{ fill: "#3b82f6", r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Yield Curve (US Treasuries)</h3>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-full px-2 py-0.5">
              ⚠ Inverted — 2Y–10Y spread: -0.42%
            </span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={YIELD_CURVE} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <XAxis dataKey="maturity" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis domain={[4.0, 5.5]} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
              <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }} formatter={(v) => `${v}%`} />
              <Line dataKey="yield" stroke="#10b981" strokeWidth={2} dot={{ fill: "#10b981", r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Macro indicators table */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Key Macro Indicators</h3>
        {MACRO_INDICATORS.map((m) => <MacroRow key={m.label} m={m} />)}
      </div>

      {/* Sector performance */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Sector Performance (Today)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={SECTOR_PERFORMANCE} margin={{ top: 5, right: 10, left: 0, bottom: 40 }}>
            <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} angle={-35} textAnchor="end" />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
            <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }} formatter={(v) => `${Number(v).toFixed(2)}%`} />
            <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
              {SECTOR_PERFORMANCE.map((s, i) => <Cell key={i} fill={s.pct >= 0 ? "#10b981" : "#ef4444"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* AI Macro Commentary */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-violet-400" />
          <h3 className="text-sm font-semibold text-white">AI Macro Analysis & Investment Implications</h3>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {AI_MACRO_COMMENTARY.map((item) => (
            <div key={item.title} className="glass-card p-5">
              <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">{item.title}</h4>
              <p className="text-sm text-slate-400 leading-relaxed">{item.text}</p>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-slate-700 pb-4">
        Macro data is simulated in demo mode. Connect Polygon.io or FRED API for live economic data.
      </p>
    </div>
  );
}
