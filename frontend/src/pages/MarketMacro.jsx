import { useState, useEffect } from "react";
import { MACRO_INDICATORS, SECTOR_PERFORMANCE, MARKET_INDICES } from "@/lib/mockData";
import { fetchMacro, fetchMarketIndices } from "@/lib/companyUniverse";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell,
} from "recharts";
import { Globe, TrendingUp, TrendingDown, Brain } from "lucide-react";

const fmt = (n, d = 2) => Number(n).toFixed(d);
const num = (s) => parseFloat(String(s).replace(/[^0-9.\-]/g, ""));

function buildCommentary(indicators, spread, inverted) {
  const get = (label) => num((indicators.find((i) => i.label.startsWith(label)) || {}).value);
  const ff = get("Fed Funds"), cpi = get("CPI"), pce = get("Core PCE"),
    unemp = get("Unemployment"), gdp = get("Real GDP"), y10 = get("10Y");
  const cards = [];
  if (!isNaN(ff)) {
    const stance = ff >= 4.5 ? "restrictive ('higher for longer')" : ff >= 3 ? "moderately restrictive" : "accommodative";
    cards.push({
      title: "Interest Rate Environment",
      text: `The Fed funds rate sits at ${ff.toFixed(2)}%, a ${stance} setting. With the 10-year Treasury at ${isNaN(y10) ? "—" : y10.toFixed(2)}%, the risk-free rate competes directly with equity earnings yields — higher rates compress valuations, so quality and cash flow matter more here. The 2Y–10Y curve is ${inverted ? "inverted" : "normal/upward"} (${spread != null ? `${spread > 0 ? "+" : ""}${spread}%` : "—"})${inverted ? ", historically a late-cycle / recession-watch signal." : ", consistent with a non-recessionary backdrop."}`,
    });
  }
  if (!isNaN(cpi) || !isNaN(pce)) {
    const above = (pce || cpi) > 2;
    cards.push({
      title: "Inflation & Growth Balance",
      text: `Headline CPI is running ${isNaN(cpi) ? "—" : cpi.toFixed(1)}% YoY and Core PCE (the Fed's preferred gauge) ${isNaN(pce) ? "—" : pce.toFixed(1)}% — ${above ? "still above the 2% target, which keeps the Fed cautious about cutting." : "at/below target, giving the Fed room to ease."} Real GDP growth of ${isNaN(gdp) ? "—" : gdp.toFixed(1)}% with unemployment at ${isNaN(unemp) ? "—" : unemp.toFixed(1)}% ${gdp > 0 && unemp < 5 ? "supports the 'soft landing' narrative." : "warrants monitoring for slowdown."}`,
    });
  }
  cards.push({
    title: "Investment Implications",
    text: `${ff >= 4.5 ? "With rates restrictive, favour quality compounders with strong free cash flow over speculative growth; rate-sensitive sectors (Utilities, REITs) stay pressured until the Fed pivots. " : "As policy eases, longer-duration growth and rate-sensitive sectors tend to re-rate higher. "}${inverted ? "An inverted curve argues for caution on cyclical risk. " : "A positively-sloped curve is supportive of risk assets. "}Use the DCF tab to stress each idea against today's ${isNaN(y10) ? "" : `${y10.toFixed(2)}% `}risk-free rate.`,
  });
  return cards;
}

function MacroRow({ m }) {
  const TrendIcon = m.trend === "up" ? TrendingUp : m.trend === "down" ? TrendingDown : null;
  const trendColor = m.trend === "up" ? "text-emerald-400" : m.trend === "down" ? "text-red-400" : "text-slate-400";
  return (
    <div className="flex items-center gap-4 py-3 border-b border-white/[0.04] last:border-0" data-testid={`macro-row-${m.label.split(" ")[0].toLowerCase()}`}>
      <div className="w-44 shrink-0"><p className="text-xs text-slate-400">{m.label}</p></div>
      <div className="flex items-center gap-2 flex-1">
        <span className="font-mono font-bold text-white text-sm">{m.value}</span>
        {TrendIcon && <TrendIcon className={`w-4 h-4 ${trendColor}`} />}
      </div>
      <p className="text-xs text-slate-500 text-right max-w-xs">{m.note}</p>
    </div>
  );
}

export default function MarketMacro() {
  const [macro, setMacro] = useState(null);
  const [indices, setIndices] = useState(MARKET_INDICES);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchMacro().then((d) => { if (alive && d?.available) { setMacro(d); setLive(true); } }).catch(() => {});
    fetchMarketIndices().then((d) => { if (alive && d?.indices?.length) setIndices(d.indices); }).catch(() => {});
    return () => { alive = false; };
  }, []);

  const rateHistory = macro?.fedFundsHistory?.length ? macro.fedFundsHistory : [];
  const yieldCurve = macro?.yieldCurve?.length ? macro.yieldCurve : [];
  const indicators = macro?.indicators?.length ? macro.indicators : MACRO_INDICATORS;
  const sectors = macro?.sectorPerformance?.length ? macro.sectorPerformance : SECTOR_PERFORMANCE;
  const spread = macro?.spread2y10y;
  const inverted = macro?.inverted;
  const commentary = live ? buildCommentary(indicators, spread, inverted) : [];

  const rateDomain = rateHistory.length
    ? [Math.floor(Math.min(...rateHistory.map((r) => r.rate)) - 0.5), Math.ceil(Math.max(...rateHistory.map((r) => r.rate)) + 0.5)]
    : [3.5, 6];
  const curveDomain = yieldCurve.length
    ? [Math.floor(Math.min(...yieldCurve.map((y) => y.yield)) * 10) / 10 - 0.2, Math.ceil(Math.max(...yieldCurve.map((y) => y.yield)) * 10) / 10 + 0.2]
    : [4, 5.5];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Globe className="w-5 h-5 text-blue-400" />
          <h1 className="text-2xl font-bold text-white">Market & Macro</h1>
          {live && <span className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5" data-testid="macro-live-badge">LIVE · FRED</span>}
        </div>
        <p className="text-sm text-slate-500">Understanding the macro environment and its impact on investment opportunities</p>
      </div>

      {/* Index overview */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="macro-indices">
        {indices.map((idx) => {
          const up = (idx.change ?? 0) >= 0;
          return (
            <div key={idx.ticker} className="metric-card">
              <p className="text-[10px] text-slate-500">{idx.name}</p>
              <p className="font-mono font-bold text-white text-base mt-1">
                {idx.ticker === "TNX" ? `${fmt(idx.value)}%` : Number(idx.value).toLocaleString()}
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
            <LineChart data={rateHistory} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <XAxis dataKey="date" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} minTickGap={20} />
              <YAxis domain={rateDomain} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
              <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }} formatter={(v) => `${v}%`} />
              <Line type="stepAfter" dataKey="rate" stroke="#3b82f6" strokeWidth={2} dot={{ fill: "#3b82f6", r: 2 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Yield Curve (US Treasuries)</h3>
          <div className="flex items-center gap-2 mb-3">
            <span className={`text-[11px] rounded-full px-2 py-0.5 border ${inverted ? "text-amber-400 bg-amber-500/10 border-amber-500/20" : "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"}`}>
              {inverted ? "⚠ Inverted" : "Normal"} — 2Y–10Y spread: {spread != null ? `${spread > 0 ? "+" : ""}${spread}%` : "—"}
            </span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={yieldCurve} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <XAxis dataKey="maturity" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis domain={curveDomain} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
              <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }} formatter={(v) => `${v}%`} />
              <Line dataKey="yield" stroke="#10b981" strokeWidth={2} dot={{ fill: "#10b981", r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Macro indicators table */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Key Macro Indicators</h3>
        {indicators.map((m) => <MacroRow key={m.label} m={m} />)}
      </div>

      {/* Sector performance */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Sector Performance (Today)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={sectors} margin={{ top: 5, right: 10, left: 0, bottom: 40 }}>
            <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} angle={-35} textAnchor="end" />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
            <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }} formatter={(v) => `${Number(v).toFixed(2)}%`} />
            <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
              {sectors.map((s, i) => <Cell key={i} fill={s.pct >= 0 ? "#10b981" : "#ef4444"} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Macro commentary (derived from live data) */}
      {commentary.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-violet-400" />
            <h3 className="text-sm font-semibold text-white">Macro Analysis & Investment Implications</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {commentary.map((item) => (
              <div key={item.title} className="glass-card p-5">
                <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">{item.title}</h4>
                <p className="text-sm text-slate-400 leading-relaxed">{item.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-slate-700 pb-4">
        {live
          ? `Live macro from FRED (Federal Reserve) + live sector performance from FMP. ${macro?.asOf ? `As of ${new Date(macro.asOf).toLocaleString()}.` : ""}`
          : "Macro data is loading… connect the FRED API for live economic data."}
      </p>
    </div>
  );
}
