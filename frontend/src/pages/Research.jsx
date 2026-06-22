import { useState } from "react";
import { useQuotes } from "@/hooks/useQuotes";
import { useSearchParams, useNavigate } from "react-router-dom";
import { COMPANY_UNIVERSE } from "@/lib/mockData";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell,
} from "recharts";
import {
  Search, TrendingUp, TrendingDown, AlertTriangle, CheckCircle,
  FileText, BarChart3, Users, DollarSign, Shield, Brain,
  ArrowUpRight, ArrowDownRight, Star,
} from "lucide-react";

const fmt = (n, d = 1) => (n == null ? "N/A" : Number(n).toFixed(d));
const fmtM = (n) => {
  if (n == null) return "N/A";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(2)}T`;
  if (n >= 1000) return `$${(n / 1000).toFixed(1)}B`;
  return `$${n}M`;
};

const RATINGS = {
  "Strongly Attractive": { color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/30" },
  "Attractive": { color: "text-emerald-300", bg: "bg-emerald-500/8 border-emerald-500/20" },
  "Fairly Valued": { color: "text-slate-300", bg: "bg-slate-500/10 border-slate-500/20" },
  "Expensive": { color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
  "Avoid": { color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
};

function getImpliedRating(company) {
  const ratio = company.impliedPrice / company.price;
  if (ratio > 1.2) return "Strongly Attractive";
  if (ratio > 1.05) return "Attractive";
  if (ratio >= 0.95) return "Fairly Valued";
  if (ratio >= 0.8) return "Expensive";
  return "Avoid";
}

function CompanySearch({ onSelect }) {
  const [q, setQ] = useState("");
  const results = q.length > 0
    ? COMPANY_UNIVERSE.filter((c) =>
        c.ticker.includes(q.toUpperCase()) ||
        c.name.toLowerCase().includes(q.toLowerCase())
      ).slice(0, 6)
    : [];

  return (
    <div className="relative max-w-2xl mx-auto">
      <div className="flex items-center gap-3 glass-card px-5 py-4 border-white/[0.1]">
        <Search className="w-5 h-5 text-slate-400 shrink-0" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search any company — e.g. AAPL, Microsoft, NVDA..."
          className="bg-transparent text-white text-lg placeholder:text-slate-600 outline-none flex-1"
          autoFocus
        />
      </div>
      {results.length > 0 && (
        <div className="absolute top-full mt-2 w-full glass-card border border-white/[0.08] rounded-xl overflow-hidden z-20 shadow-2xl shadow-black/50">
          {results.map((c) => (
            <button
              key={c.ticker}
              onClick={() => { onSelect(c); setQ(""); }}
              className="w-full flex items-center gap-4 px-5 py-3 hover:bg-white/[0.05] transition-colors text-left"
            >
              <span className="font-mono font-bold text-blue-400 w-14 shrink-0">{c.ticker}</span>
              <span className="text-slate-200 flex-1">{c.name}</span>
              <span className="text-xs text-slate-500">{c.sector}</span>
              <span className="text-xs text-slate-500 font-mono">{fmtM(c.marketCap)}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, sub, up }) {
  return (
    <div className="metric-card">
      <p className="text-[11px] text-slate-500">{label}</p>
      <p className={`text-xl font-bold mt-1 font-mono ${up === true ? "text-emerald-400" : up === false ? "text-red-400" : "text-white"}`}>
        {value}
      </p>
      {sub && <p className="text-[11px] text-slate-600 mt-0.5">{sub}</p>}
    </div>
  );
}

function FinancialChart({ company }) {
  const revenueData = company.years.map((y, i) => ({
    year: y,
    revenue: company.revenueHistory[i] ? Math.round(company.revenueHistory[i] / 1000) : 0,
    ebitda: company.ebitdaHistory[i] ? Math.round(company.ebitdaHistory[i] / 1000) : 0,
  }));
  const forecastData = [2025, 2026, 2027, 2028, 2029].map((y, i) => ({
    year: y,
    revenue: company.revenueForcast[i] ? Math.round(company.revenueForcast[i] / 1000) : 0,
    forecast: true,
  }));
  const allData = [...revenueData, ...forecastData];

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={allData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
        <XAxis dataKey="year" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}B`} />
        <Tooltip
          contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }}
          formatter={(v, n) => [`$${v}B`, n === "revenue" ? "Revenue" : "EBITDA"]}
        />
        <Bar dataKey="revenue" radius={[3, 3, 0, 0]}>
          {allData.map((d, i) => (
            <Cell key={i} fill={d.forecast ? "rgba(59,130,246,0.4)" : "#3b82f6"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function ScenarioCard({ label, price, current, color, bgColor, thesis }) {
  const pct = (((price - current) / current) * 100).toFixed(1);
  const isUp = price >= current;
  return (
    <div className={`glass-card p-4 border ${bgColor}`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-semibold uppercase tracking-wider ${color}`}>{label}</span>
        <div className={`flex items-center gap-1 font-mono font-bold text-lg ${color}`}>
          ${price}
          {isUp ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
        </div>
      </div>
      <p className={`text-xs font-semibold ${isUp ? "text-emerald-400" : "text-red-400"} mb-2`}>
        {isUp ? "+" : ""}{pct}% vs current
      </p>
      {thesis && <p className="text-xs text-slate-500 leading-relaxed">{thesis}</p>}
    </div>
  );
}

export default function Research() {
  const [searchParams] = useSearchParams();
  const [company, setCompany] = useState(() => {
    const ticker = searchParams.get("ticker");
    return ticker ? COMPANY_UNIVERSE.find((c) => c.ticker === ticker) || null : null;
  });
  const [tab, setTab] = useState("overview");

  const featured = COMPANY_UNIVERSE.slice(0, 8);
  const { prices: quotes, asOf: quotesAsOf } = useQuotes([...featured.map((x) => x.ticker), ...(company ? [company.ticker] : [])]);

  const rating = company ? getImpliedRating(company) : null;
  const ratingStyle = rating ? RATINGS[rating] : null;

  if (!company) {
    return (
      <div className="animate-fade-in space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Company Research</h1>
          <p className="text-sm text-slate-500 mt-1">Search any company for an institutional-quality research report</p>
        </div>
        <CompanySearch onSelect={setCompany} />

        {/* Featured companies */}
        <div>
          <p className="section-title mb-4">Featured Companies</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {featured.map((c) => {
              const lq = quotes[c.ticker];
              const liveP = lq?.price ?? c.price;
              const livePct = lq?.changePct ?? c.pct;
              const up = (livePct ?? 0) >= 0;
              const r = getImpliedRating(c);
              const rs = RATINGS[r];
              return (
                <button
                  key={c.ticker}
                  onClick={() => setCompany(c)}
                  className="glass-card p-4 text-left hover:border-white/[0.1] transition-all group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <span className="font-mono font-bold text-blue-400 text-sm">{c.ticker}</span>
                      <p className="text-xs text-slate-400 mt-0.5 truncate max-w-[130px]">{c.name}</p>
                    </div>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${rs.bg} ${rs.color}`}>{r}</span>
                  </div>
                  <p className="text-lg font-bold font-mono text-white">${liveP}</p>
                  <p className={`text-xs font-mono ${up ? "text-emerald-400" : "text-red-400"}`}>
                    {up ? "+" : ""}{fmt(livePct)}% today
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[10px] text-slate-600">{c.sector}</span>
                    <span className="text-[10px] text-slate-700">·</span>
                    <span className="text-[10px] text-slate-600">{fmtM(c.marketCap)}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  const liveQ = quotes[company.ticker];
  const c = liveQ
    ? { ...company, price: liveQ.price ?? company.price, change: liveQ.change ?? company.change, pct: liveQ.changePct ?? company.pct }
    : company;
  const up = (c.pct ?? 0) >= 0;

  const TABS = ["overview", "financials", "valuation", "thesis"];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back + search */}
      <div className="flex items-center gap-4">
        <button onClick={() => setCompany(null)} className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1">
          ← Back to search
        </button>
        <div className="flex-1 max-w-md">
          <CompanySearch onSelect={setCompany} />
        </div>
      </div>

      {/* Company header */}
      <div className="glass-card p-6">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="font-mono font-bold text-2xl text-blue-400">{company.ticker}</span>
              <span className={`text-sm font-semibold px-3 py-1 rounded-full border ${ratingStyle.bg} ${ratingStyle.color}`}>
                {rating}
              </span>
              {company.shariah === "Compliant" && (
                <span className="text-[11px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5">
                  Shariah Compliant
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-white">{company.name}</h1>
            <p className="text-sm text-slate-500 mt-1">{company.sector} · {company.industry}</p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold font-mono text-white">${c.price}</p>
            <p className={`text-sm font-mono font-semibold ${up ? "text-emerald-400" : "text-red-400"}`}>
              {up ? "+" : ""}{fmt(c.change)} ({up ? "+" : ""}{fmt(c.pct)}%)
            </p>
            <p className="text-xs text-slate-500 mt-1">Market Cap: {fmtM(company.marketCap)}</p>
            {quotesAsOf && quotes[company.ticker] && (
              <p className="text-[10px] text-emerald-400/80 mt-1 flex items-center justify-end gap-1" data-testid="research-price-asof">
                <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
                Live · as of {new Date(quotesAsOf).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-slate-400 leading-relaxed mt-4 border-t border-white/[0.04] pt-4">
          {company.description}
        </p>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <MetricCard label="P/E Ratio" value={company.pe ? `${company.pe}x` : "N/A"} />
        <MetricCard label="EV/EBITDA" value={company.evEbitda ? `${company.evEbitda}x` : "N/A"} />
        <MetricCard label="Revenue Growth" value={`${fmt(company.revenueGrowth)}%`} up={company.revenueGrowth > 5} />
        <MetricCard label="Gross Margin" value={company.grossMargin ? `${company.grossMargin}%` : "N/A"} />
        <MetricCard label="FCF Margin" value={company.fcfMargin ? `${company.fcfMargin}%` : "N/A"} />
        <MetricCard label="ROE" value={company.roe ? `${company.roe}%` : "N/A"} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/[0.03] border border-white/[0.05] p-1 rounded-xl w-fit">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all capitalize ${
              tab === t ? "bg-white/[0.08] text-white" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t === "thesis" ? "AI Thesis" : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 glass-card p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Revenue & Forecast</h3>
            <FinancialChart company={company} />
            <p className="text-[11px] text-slate-600 mt-2">Historical (solid) · Forecast 2025–2029 (lighter). All values in billions USD.</p>
          </div>
          <div className="space-y-4">
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-3">Competitive Moat</h3>
              {company.moat ? (
                <p className="text-sm text-slate-400 leading-relaxed">{company.moat}</p>
              ) : <p className="text-sm text-slate-600">No moat data available</p>}
            </div>
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" /> Key Risks
              </h3>
              <ul className="space-y-2">
                {(company.risks || []).map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                    <span className="text-red-400 mt-0.5 shrink-0">•</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
            <div className="glass-card p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-white">Analyst Rating</h3>
              </div>
              <p className="text-xl font-bold text-emerald-400">{company.analystRating}</p>
              <p className="text-sm text-slate-400 mt-1">Avg PT: <span className="text-white font-mono font-bold">${company.avgPt}</span></p>
              <p className={`text-xs mt-1 ${(company.avgPt - c.price) > 0 ? "text-emerald-400" : "text-red-400"}`}>
                {(((company.avgPt - c.price) / c.price) * 100).toFixed(1)}% to consensus target
              </p>
            </div>
          </div>
        </div>
      )}

      {tab === "financials" && (
        <div className="glass-card p-5 overflow-x-auto">
          <h3 className="text-sm font-semibold text-white mb-4">Historical Financial Statements ($M)</h3>
          <table className="data-table min-w-[600px]">
            <thead>
              <tr>
                <th>Metric</th>
                {company.years.map((y) => <th key={y}>{y}</th>)}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="text-slate-300 font-medium">Revenue</td>
                {company.revenueHistory.map((v, i) => <td key={i} className="font-mono">${v ? v.toLocaleString() : "—"}</td>)}
              </tr>
              <tr>
                <td className="text-slate-300 font-medium">Revenue Growth</td>
                {company.revenueHistory.map((v, i) => {
                  if (i === 0) return <td key={i} className="text-slate-600">—</td>;
                  const prev = company.revenueHistory[i - 1];
                  const g = prev ? (((v - prev) / prev) * 100).toFixed(1) : null;
                  return <td key={i} className={`font-mono ${g > 0 ? "text-emerald-400" : "text-red-400"}`}>{g ? `${g}%` : "—"}</td>;
                })}
              </tr>
              <tr>
                <td className="text-slate-300 font-medium">EBITDA</td>
                {company.ebitdaHistory.map((v, i) => <td key={i} className="font-mono">{v ? `$${v.toLocaleString()}` : "—"}</td>)}
              </tr>
              <tr>
                <td className="text-slate-300 font-medium">EBITDA Margin</td>
                {company.revenueHistory.map((r, i) => {
                  const e = company.ebitdaHistory[i];
                  return <td key={i} className="font-mono text-slate-400">{e ? `${((e / r) * 100).toFixed(1)}%` : "—"}</td>;
                })}
              </tr>
              <tr>
                <td className="text-slate-300 font-medium">Free Cash Flow</td>
                {company.fcfHistory.map((v, i) => <td key={i} className={`font-mono ${v > 0 ? "text-emerald-400" : "text-red-400"}`}>{v ? `$${v.toLocaleString()}` : "—"}</td>)}
              </tr>
              <tr>
                <td className="text-slate-300 font-medium">FCF Margin</td>
                {company.revenueHistory.map((r, i) => {
                  const f = company.fcfHistory[i];
                  return <td key={i} className="font-mono text-slate-400">{f ? `${((f / r) * 100).toFixed(1)}%` : "—"}</td>;
                })}
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {tab === "valuation" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-4">DCF Valuation Summary</h3>
              <div className="space-y-3">
                {[
                  { l: "WACC", v: `${company.wacc}%` },
                  { l: "Terminal Growth Rate", v: `${company.tgr}%` },
                  { l: "Exit Multiple", v: company.exitMultiple ? `${company.exitMultiple}x EV/EBITDA` : "N/A" },
                  { l: "DCF Implied Price", v: `$${company.impliedPrice}`, highlight: true },
                  { l: "DCF Upside / Downside", v: `${fmt(company.dcfUpside)}%`, up: company.dcfUpside > 0 },
                  { l: "Consensus PT", v: `$${company.avgPt}` },
                ].map((row) => (
                  <div key={row.l} className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
                    <span className="text-sm text-slate-400">{row.l}</span>
                    <span className={`font-mono font-bold text-sm ${row.highlight ? "text-white text-lg" : row.up === true ? "text-emerald-400" : row.up === false ? "text-red-400" : "text-slate-200"}`}>
                      {row.v}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Revenue Forecast ($M)</h3>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Year</th>
                      <th>Revenue</th>
                      <th>Growth</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[2025, 2026, 2027, 2028, 2029].map((y, i) => {
                      const r = company.revenueForcast?.[i];
                      const prev = i === 0 ? company.revenueHistory?.at(-1) : company.revenueForcast?.[i - 1];
                      const g = r && prev ? (((r - prev) / prev) * 100).toFixed(1) : null;
                      return (
                        <tr key={y}>
                          <td className="font-mono text-slate-400">{y}E</td>
                          <td className="font-mono text-white">{r ? `$${r.toLocaleString()}` : "—"}</td>
                          <td className={`font-mono ${g > 0 ? "text-emerald-400" : "text-red-400"}`}>{g ? `+${g}%` : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Scenarios */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Bull / Base / Bear Scenarios</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <ScenarioCard
                label="Bull Case"
                price={company.bullPrice}
                current={c.price}
                color="text-emerald-400"
                bgColor="border-emerald-500/20"
                thesis={company.bullCase?.thesis}
              />
              <ScenarioCard
                label="Base Case"
                price={company.baseprice}
                current={c.price}
                color="text-blue-400"
                bgColor="border-blue-500/20"
                thesis={company.baseCase?.thesis}
              />
              <ScenarioCard
                label="Bear Case"
                price={company.bearPrice}
                current={c.price}
                color="text-red-400"
                bgColor="border-red-500/20"
                thesis={company.bearCase?.thesis}
              />
            </div>
          </div>
        </div>
      )}

      {tab === "thesis" && (
        <div className="space-y-5">
          <div className="glass-card p-6">
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border mb-5 ${ratingStyle.bg}`}>
              <Brain className="w-4 h-4" />
              <span className={`font-bold text-sm ${ratingStyle.color}`}>AI Rating: {rating}</span>
            </div>

            <h3 className="text-base font-semibold text-white mb-3">Investment Thesis</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              {company.name} represents a {rating === "Strongly Attractive" || rating === "Attractive" ? "compelling" : "cautious"} investment case in the current environment.
              {company.moat ? ` The company's competitive advantages — ${company.moat} — create meaningful barriers to entry and support durable above-market returns on invested capital.` : ""}
              {" "}With revenue growing at {fmt(company.revenueGrowth)}% year-over-year and{company.fcfMargin ? ` FCF margins of ${company.fcfMargin}%` : " strong cash generation"},
              the business demonstrates the characteristics of a high-quality compounder.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5">
              <div>
                <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5" /> Bull Case Arguments
                </h4>
                <ul className="space-y-2">
                  {[
                    `Revenue acceleration driven by ${company.sector === "Technology" ? "AI adoption" : "market expansion"}`,
                    `Margin expansion toward ${fmt((company.ebitdaMargin || 20) + 3)}%+ EBITDA margin`,
                    `Analyst consensus PT implies ${(((company.avgPt - c.price) / c.price) * 100).toFixed(1)}% upside`,
                    company.moat?.split(",")[0] ? `${company.moat.split(",")[0]} drives pricing power` : "Strong competitive positioning",
                  ].map((b, i) => (
                    <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                      <span className="text-emerald-400 shrink-0 mt-0.5">+</span> {b}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> Bear Case Arguments
                </h4>
                <ul className="space-y-2">
                  {(company.risks || []).slice(0, 4).map((r, i) => (
                    <li key={i} className="text-sm text-slate-400 flex items-start gap-2">
                      <span className="text-red-400 shrink-0 mt-0.5">−</span> {r}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="mt-5 p-4 bg-white/[0.03] rounded-xl border border-white/[0.05]">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Final Assessment</p>
              <p className="text-sm text-slate-300 leading-relaxed">
                At ${c.price} per share, {company.ticker} trades at {company.pe}x earnings and {company.evEbitda || "N/A"}x EV/EBITDA.
                Our DCF model implies a fair value of <strong className="text-white">${company.impliedPrice}</strong>, representing
                <span className={company.dcfUpside > 0 ? " text-emerald-400" : " text-red-400"}> {company.dcfUpside > 0 ? "+" : ""}{fmt(company.dcfUpside)}% upside</span>.
                Combined with analyst consensus of ${company.avgPt}, the risk/reward appears
                {rating === "Strongly Attractive" || rating === "Attractive" ? " favorable for long-term investors." : rating === "Fairly Valued" ? " balanced at current levels." : " stretched at current valuations."}
              </p>
            </div>

            <p className="text-[10px] text-slate-700 mt-4">
              AlphaVault AI generates research for educational purposes only. This does not constitute investment advice.
              All assumptions should be independently verified. Ratings: Strongly Attractive / Attractive / Fairly Valued / Expensive / Avoid.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
