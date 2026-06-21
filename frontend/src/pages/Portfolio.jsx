import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { COMPANY_UNIVERSE } from "@/lib/mockData";
import { toast } from "sonner";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
} from "recharts";
import {
  Wallet, Plus, Trash2, TrendingUp, TrendingDown, AlertTriangle, Brain,
  ArrowUpRight, X,
} from "lucide-react";

const fmt = (n, d = 2) => (n == null ? "—" : Number(n).toFixed(d));
const fmtM = (n) => {
  if (!n) return "N/A";
  if (n >= 1000000000) return `$${(n / 1000000000).toFixed(1)}B`;
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `$${(n / 1000).toFixed(1)}K`;
  return `$${n.toFixed(0)}`;
};

const COLORS = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444", "#06b6d4", "#ec4899", "#14b8a6"];

const DEFAULT_HOLDINGS = [
  { ticker: "NVDA", shares: 50, avgCost: 85 },
  { ticker: "MSFT", shares: 30, avgCost: 380 },
  { ticker: "AAPL", shares: 100, avgCost: 175 },
  { ticker: "META", shares: 25, avgCost: 380 },
  { ticker: "LLY", shares: 10, avgCost: 650 },
];

function AddHoldingModal({ onAdd, onClose }) {
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("");
  const [avgCost, setAvgCost] = useState("");
  const results = ticker.length > 0
    ? COMPANY_UNIVERSE.filter((c) => c.ticker.startsWith(ticker.toUpperCase())).slice(0, 5)
    : [];

  const handleAdd = () => {
    if (!ticker || !shares || !avgCost) return toast.error("Fill all fields");
    onAdd({ ticker: ticker.toUpperCase(), shares: Number(shares), avgCost: Number(avgCost) });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-card p-6 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-sm font-semibold text-white">Add Holding</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Ticker</label>
            <input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL" className="input-dark" autoFocus />
            {results.length > 0 && (
              <div className="mt-1 rounded-lg border border-white/[0.08] overflow-hidden">
                {results.map((c) => (
                  <button key={c.ticker} onClick={() => setTicker(c.ticker)}
                    className="w-full flex items-center gap-3 px-3 py-2 hover:bg-white/[0.05] text-left text-sm">
                    <span className="font-mono font-bold text-blue-400 w-12">{c.ticker}</span>
                    <span className="text-slate-300">{c.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Shares</label>
            <input type="number" value={shares} onChange={(e) => setShares(e.target.value)}
              placeholder="Number of shares" className="input-dark" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Average Cost ($)</label>
            <input type="number" value={avgCost} onChange={(e) => setAvgCost(e.target.value)}
              placeholder="Your average purchase price" className="input-dark" />
          </div>
          <button onClick={handleAdd}
            className="w-full bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-sm py-2.5 rounded-lg transition-colors">
            Add to Portfolio
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Portfolio() {
  const navigate = useNavigate();
  const [holdings, setHoldings] = useState(DEFAULT_HOLDINGS);
  const [showAdd, setShowAdd] = useState(false);

  const enriched = holdings.map((h) => {
    const c = COMPANY_UNIVERSE.find((co) => co.ticker === h.ticker);
    if (!c) return { ...h, currentPrice: h.avgCost, name: h.ticker, sector: "Unknown", pnl: 0, pnlPct: 0, value: h.shares * h.avgCost };
    const value = h.shares * c.price;
    const cost = h.shares * h.avgCost;
    return {
      ...h,
      currentPrice: c.price,
      name: c.name,
      sector: c.sector,
      value,
      cost,
      pnl: value - cost,
      pnlPct: ((value - cost) / cost) * 100,
      opportunityScore: c.opportunityScore,
      analystRating: c.analystRating,
      dcfUpside: c.dcfUpside,
    };
  });

  const totalValue = enriched.reduce((s, h) => s + h.value, 0);
  const totalCost = enriched.reduce((s, h) => s + (h.cost || h.value), 0);
  const totalPnl = totalValue - totalCost;
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

  const sectorMap = {};
  enriched.forEach((h) => {
    sectorMap[h.sector] = (sectorMap[h.sector] || 0) + h.value;
  });
  const sectorData = Object.entries(sectorMap).map(([name, value]) => ({
    name,
    value: Math.round((value / totalValue) * 100),
  })).sort((a, b) => b.value - a.value);

  const removeHolding = (ticker) => {
    setHoldings((prev) => prev.filter((h) => h.ticker !== ticker));
  };

  const addHolding = (h) => {
    if (holdings.find((x) => x.ticker === h.ticker)) {
      toast.info(`${h.ticker} already in portfolio — edit shares instead`);
      return;
    }
    setHoldings((prev) => [...prev, h]);
    toast.success(`${h.ticker} added to portfolio`);
  };

  const aiInsights = [
    `Your portfolio is concentrated in Technology (${sectorData.find((s) => s.name === "Technology")?.value || 0}%). Consider diversifying into Healthcare or Financials to reduce sector risk.`,
    totalPnlPct > 0
      ? `Portfolio is up ${fmt(totalPnlPct)}% from cost basis — consider trimming positions with >50% gains to manage concentration risk.`
      : `Portfolio is down ${fmt(Math.abs(totalPnlPct))}% from cost basis. Review each position's fundamental thesis before deciding to add or exit.`,
    `${enriched.filter((h) => h.dcfUpside > 10).length} of your holdings have significant DCF upside remaining per our models. ${enriched.filter((h) => h.dcfUpside < -10).length} appear richly valued.`,
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      {showAdd && <AddHoldingModal onAdd={addHolding} onClose={() => setShowAdd(false)} />}

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white">Portfolio Intelligence</h1>
          <p className="text-sm text-slate-500 mt-0.5">AI-powered analysis of your holdings and risk profile</p>
        </div>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 text-sm bg-emerald-500/10 hover:bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 rounded-lg px-3 py-2 transition-colors">
          <Plus className="w-4 h-4" /> Add Holding
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Portfolio Value", value: fmtM(totalValue), sub: "Current market value" },
          { label: "Total Cost", value: fmtM(totalCost), sub: "Total invested" },
          { label: "Total P&L", value: `${totalPnl >= 0 ? "+" : ""}${fmtM(totalPnl)}`, sub: "Unrealized gain/loss", up: totalPnl >= 0 },
          { label: "Return", value: `${totalPnlPct >= 0 ? "+" : ""}${fmt(totalPnlPct)}%`, sub: "vs cost basis", up: totalPnlPct >= 0 },
        ].map((m) => (
          <div key={m.label} className="metric-card">
            <p className="text-[11px] text-slate-500">{m.label}</p>
            <p className={`text-xl font-bold font-mono mt-1 ${m.up === true ? "text-emerald-400" : m.up === false ? "text-red-400" : "text-white"}`}>
              {m.value}
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">{m.sub}</p>
          </div>
        ))}
      </div>

      {/* Chart + AI Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Sector Allocation</h3>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={180} height={180}>
              <PieChart>
                <Pie data={sectorData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} dataKey="value" paddingAngle={2}>
                  {sectorData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, fontSize: 12 }} formatter={(v) => `${v}%`} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2 flex-1">
              {sectorData.map((s, i) => (
                <div key={s.name} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                  <span className="text-xs text-slate-400 flex-1 truncate">{s.name}</span>
                  <span className="text-xs font-mono text-slate-300">{s.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="glass-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="w-4 h-4 text-violet-400" />
            <h3 className="text-sm font-semibold text-white">AI Portfolio Analysis</h3>
          </div>
          <div className="space-y-3">
            {aiInsights.map((insight, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <div className="w-5 h-5 rounded-full bg-violet-500/15 border border-violet-500/25 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-[10px] font-bold text-violet-400">{i + 1}</span>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed">{insight}</p>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-slate-700 mt-4">
            AI analysis uses demo data. This is not investment advice — conduct your own due diligence.
          </p>
        </div>
      </div>

      {/* Holdings table */}
      <div className="glass-card overflow-x-auto">
        <div className="p-5 border-b border-white/[0.04] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Holdings ({holdings.length})</h3>
          <span className="text-xs text-slate-600">Click any row to view research</span>
        </div>
        <table className="data-table min-w-[900px]">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Company</th>
              <th>Shares</th>
              <th>Avg Cost</th>
              <th>Current</th>
              <th>Value</th>
              <th>P&L</th>
              <th>Return</th>
              <th>DCF Upside</th>
              <th>Rating</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {enriched.map((h) => {
              const pnlUp = h.pnl >= 0;
              const dcfUp = (h.dcfUpside || 0) >= 0;
              return (
                <tr key={h.ticker} className="cursor-pointer" onClick={() => navigate(`/research?ticker=${h.ticker}`)}>
                  <td className="font-mono font-bold text-blue-400">{h.ticker}</td>
                  <td className="text-slate-200">{h.name}</td>
                  <td className="font-mono text-slate-300">{h.shares}</td>
                  <td className="font-mono text-slate-400">${fmt(h.avgCost)}</td>
                  <td className="font-mono text-white font-semibold">${fmt(h.currentPrice)}</td>
                  <td className="font-mono text-slate-300">{fmtM(h.value)}</td>
                  <td className={`font-mono font-semibold ${pnlUp ? "text-emerald-400" : "text-red-400"}`}>
                    {pnlUp ? "+" : ""}{fmtM(h.pnl)}
                  </td>
                  <td className={`font-mono font-semibold ${pnlUp ? "text-emerald-400" : "text-red-400"}`}>
                    {pnlUp ? "+" : ""}{fmt(h.pnlPct)}%
                  </td>
                  <td className={`font-mono ${dcfUp ? "text-emerald-400" : "text-red-400"}`}>
                    {dcfUp ? "+" : ""}{fmt(h.dcfUpside || 0)}%
                  </td>
                  <td>
                    <span className={`text-xs font-medium ${h.analystRating === "Overweight" ? "text-emerald-400" : h.analystRating === "Underweight" ? "text-red-400" : "text-slate-400"}`}>
                      {h.analystRating || "—"}
                    </span>
                  </td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <button onClick={() => removeHolding(h.ticker)} className="text-slate-700 hover:text-red-400 p-1 transition-colors">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-700">
        Portfolio data is stored locally in your browser. AlphaVault never executes trades or connects to broker accounts.
      </p>
    </div>
  );
}
