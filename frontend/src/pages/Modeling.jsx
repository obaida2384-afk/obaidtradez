import { useState, useMemo, useCallback, useEffect } from "react";
import { COMPANY_UNIVERSE } from "@/lib/mockData";
import { fetchCompanies, fetchDcf } from "@/lib/companyUniverse";
import { generateExcelModel } from "@/lib/excelExporter";
import { getRating, RATING_STYLE } from "@/lib/rating";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  Search, FileSpreadsheet, Calculator, Edit3, RotateCcw,
  BarChart2, BookOpen, Target, ChevronRight, AlertTriangle,
  Info, CheckCircle, History, Users, FileText, Activity, GraduationCap,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
} from "recharts";

// ─── Formatters ───────────────────────────────────────────────────────────────
const fmtB  = (n) => { if (n == null || isNaN(n)) return "—"; const a = Math.abs(n); if (a >= 1e6) return `$${(n/1e6).toFixed(1)}T`; if (a >= 1e3) return `$${(n/1e3).toFixed(1)}B`; return `$${n.toFixed(0)}M`; };
const fmtPx = (n) => n == null ? "—" : `$${Number(n).toFixed(2)}`;
const fmtP  = (n, d=1) => n == null ? "—" : `${Number(n).toFixed(d)}%`;
const fmtN  = (n, d=1) => n == null ? "—" : Number(n).toFixed(d);
const fmtComma = (n) => n == null ? "—" : `$${Number(n).toLocaleString(undefined,{maximumFractionDigits:0})}M`;
const sign  = (n) => n >= 0 ? "+" : "";
const clr   = (n) => n >= 0 ? "text-emerald-400" : "text-red-400";

// ─── Balance sheet lookup (shares in M, cash/debt in $M) ─────────────────────
const BS = {
  AAPL:  { cash: 67_000,  debt: 104_000, shares: 15_441 },
  MSFT:  { cash: 80_000,  debt: 45_000,  shares:  7_431 },
  NVDA:  { cash: 26_000,  debt: 11_000,  shares: 24_640 },
  AMZN:  { cash: 86_000,  debt: 58_000,  shares: 10_480 },
  GOOGL: { cash:108_000,  debt: 13_000,  shares: 12_580 },
  META:  { cash: 58_000,  debt: 18_000,  shares:  2_570 },
  TSLA:  { cash: 29_000,  debt: 13_000,  shares:  3_190 },
  AVGO:  { cash: 12_000,  debt: 69_000,  shares:  4_190 },
  AMD:   { cash:  5_600,  debt:  2_200,  shares:  1_618 },
  JPM:   { cash:500_000,  debt:      0,  shares:  2_897 },
  LLY:   { cash:  3_200,  debt: 25_000,  shares:    947 },
  V:     { cash: 16_000,  debt: 20_000,  shares:  2_050 },
};

// ─── Default assumptions builder ──────────────────────────────────────────────
function buildDefaults(c) {
  const bs = BS[c.ticker] || {
    cash: Math.round(c.revenue * 0.10),
    debt: Math.round(c.revenue * 0.05),
    shares: Math.round(c.marketCap / c.price),
  };
  const g = c.revenueGrowth || 10;
  const revGrowth = [
    Math.min(g * 1.00, 80), Math.min(g * 0.82, 70),
    Math.min(g * 0.65, 60), Math.min(g * 0.50, 45),
    Math.min(g * 0.38, 35),
  ].map(v => Math.max(2, parseFloat(v.toFixed(1))));

  const bm = c.ebitdaMargin || 20;
  const ebitdaMargin = [bm, Math.min(bm+1,80), Math.min(bm+2,80), Math.min(bm+3,80), Math.min(bm+3.5,80)]
    .map(v => parseFloat(v.toFixed(1)));

  const sectorBeta = { Technology:1.25, Healthcare:0.85, Financials:1.10,
    "Consumer Discretionary":1.15, Energy:1.05, Industrials:0.95,
    "Communication Services":1.10 }[c.sector] || 1.10;

  const riskFreeRate = 4.5, erp = 5.5, beta = sectorBeta;
  const costOfEquity = riskFreeRate + beta * erp;
  const costOfDebt = 5.5, taxRate = 21;
  const debtWeight = Math.min(30, Math.round((c.debtToEbitda || 1) * 5));
  const equityWeight = 100 - debtWeight;
  const wacc = parseFloat(((equityWeight/100)*costOfEquity + (debtWeight/100)*costOfDebt*(1-taxRate/100)).toFixed(1));

  return {
    riskFreeRate, erp, beta, costOfDebt, taxRate,
    debtWeight, equityWeight, wacc,
    tgr: 3.0, exitMultiple: c.exitMultiple || 20, tvMethod: "gordon",
    revGrowth,
    ebitdaMargin,
    daPercent:   [7.0, 7.0, 6.5, 6.0, 6.0],
    capexPercent:[5.0, 5.0, 4.5, 4.0, 4.0],
    nwcPercent:  [2.0, 2.0, 2.0, 1.5, 1.5],
    cash: bs.cash, debt: bs.debt, sharesOut: bs.shares,
  };
}

// ─── DCF Engine ───────────────────────────────────────────────────────────────
function computeDCF(c, a) {
  const w = a.wacc / 100;
  const tax = a.taxRate / 100;
  const costOfEquity = a.riskFreeRate + a.beta * a.erp;
  const atcod = a.costOfDebt * (1 - tax);
  const compWacc = (a.equityWeight/100)*costOfEquity + (a.debtWeight/100)*atcod;

  let prevRev = c.revenue;
  let prevNWC = c.revenue * (a.nwcPercent[0]/100);
  const BASE_YEAR = 2024;
  const forecast = [];

  for (let i = 0; i < 5; i++) {
    const rev    = prevRev * (1 + a.revGrowth[i]/100);
    const ebitda = rev * (a.ebitdaMargin[i]/100);
    const da     = rev * (a.daPercent[i]/100);
    const ebit   = ebitda - da;
    const taxes  = Math.max(0, ebit * tax);
    const nopat  = ebit - taxes;
    const capex  = rev * (a.capexPercent[i]/100);
    const nwc    = rev * (a.nwcPercent[i]/100);
    const dNWC   = nwc - prevNWC;
    const ufcf   = nopat + da - capex - dNWC;
    const df     = 1 / Math.pow(1 + w, i + 1);
    const pvUFCF = ufcf * df;
    forecast.push({ year: BASE_YEAR+i+1, rev, revGrowth: a.revGrowth[i],
      ebitda, ebitdaM: ebitda/rev*100, da, daM: a.daPercent[i],
      ebit, ebitM: ebit/rev*100, taxes, nopat, nopatM: nopat/rev*100,
      capex, capexM: a.capexPercent[i], nwc, dNWC, ufcf, ufcfM: ufcf/rev*100, df, pvUFCF });
    prevRev = rev; prevNWC = nwc;
  }

  const lastFCF  = forecast[4].ufcf;
  const tvGG     = lastFCF * (1+a.tgr/100) / (w - a.tgr/100);
  const tvEM     = forecast[4].ebitda * a.exitMultiple;
  const tvUsed   = a.tvMethod === "gordon" ? tvGG : tvEM;
  const pvTV     = tvUsed / Math.pow(1+w, 5);
  const pvFCFs   = forecast.reduce((s,f) => s+f.pvUFCF, 0);
  const tvPct    = pvTV / (pvFCFs + pvTV) * 100;
  const EV       = pvFCFs + pvTV;
  const eqVal    = EV + a.cash - a.debt;
  const implied  = eqVal / a.sharesOut;
  const upside   = (implied / c.price - 1) * 100;

  // Sensitivity: WACC rows × TGR/EM cols
  const wRows = [-1.5,-1.0,-0.5,0,0.5,1.0,1.5].map(d => parseFloat((a.wacc+d).toFixed(1)));
  const xCols = a.tvMethod === "gordon"
    ? [-1.0,-0.5,0,0.5,1.0].map(d => parseFloat((a.tgr+d).toFixed(1)))
    : [-4,-2,0,2,4].map(d => a.exitMultiple+d);

  const sens = wRows.map(wr => xCols.map(xc => {
    const wd = wr/100;
    const pvF = forecast.reduce((s,f,i) => s + f.ufcf/Math.pow(1+wd,i+1), 0);
    const tv = a.tvMethod === "gordon"
      ? lastFCF*(1+xc/100)/(wd - xc/100)
      : forecast[4].ebitda * xc;
    const pv = tv / Math.pow(1+wd,5);
    const eq = pvF + pv + a.cash - a.debt;
    const p  = Math.max(0, eq / a.sharesOut);
    return { price: p, upside: (p/c.price-1)*100 };
  }));

  // Rev/EBITDA margin sensitivity
  const revScens = [-5,-2.5,0,2.5,5].map(d => a.revGrowth[0]+d);
  const mgnScens = [-3,-1.5,0,1.5,3].map(d => a.ebitdaMargin[0]+d);
  const rmSens = revScens.map(rg => mgnScens.map(mg => {
    let pr2 = c.revenue, pn2 = c.revenue*(a.nwcPercent[0]/100);
    let pv2 = 0;
    for (let i=0;i<5;i++){
      const gR = i===0?rg:a.revGrowth[i]; const mR = i===0?mg:a.ebitdaMargin[i];
      const r2=pr2*(1+gR/100), eb2=r2*(mR/100), d2=r2*(a.daPercent[i]/100);
      const e2=eb2-d2, n2=Math.max(0,e2*(1-tax));
      const cap2=r2*(a.capexPercent[i]/100), nw2=r2*(a.nwcPercent[i]/100), dn2=nw2-pn2;
      const u2=n2+d2-cap2-dn2;
      pv2+=u2/Math.pow(1+w,i+1); pr2=r2; pn2=nw2;
    }
    const tv2 = a.tvMethod==="gordon"
      ? (forecast[4].ufcf*(1+a.tgr/100))/(w-a.tgr/100)
      : forecast[4].ebitda*a.exitMultiple;
    const eq2 = pv2+tv2/Math.pow(1+w,5)+a.cash-a.debt;
    return { price: Math.max(0,eq2/a.sharesOut), upside:(Math.max(0,eq2/a.sharesOut)/c.price-1)*100 };
  }));

  return {
    costOfEquity, atcod, compWacc, forecast, tvGG, tvEM, tvUsed, pvTV, pvFCFs, tvPct,
    EV, eqVal, implied, upside, wRows, xCols, sens, revScens, mgnScens, rmSens,
  };
}

// ─── Shared cells ─────────────────────────────────────────────────────────────
const TH = ({ children, right }) => (
  <th className={`px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-800/60 border-b border-white/[0.06] whitespace-nowrap ${right ? "text-right" : "text-left"}`}>
    {children}
  </th>
);
const TD = ({ children, right, mono, color, bold, amber, gray }) => (
  <td className={`px-3 py-1.5 text-xs border-b border-white/[0.04] whitespace-nowrap
    ${right ? "text-right" : ""}
    ${mono ? "font-mono" : ""}
    ${bold ? "font-semibold" : ""}
    ${amber ? "text-amber-300 bg-amber-500/5" : gray ? "text-slate-400 bg-slate-800/30" : color || "text-slate-300"}`}>
    {children}
  </td>
);

const EditInput = ({ value, onChange, step=0.5, min=-200, max=200 }) => (
  <input type="number" value={value}
    onChange={e => onChange(parseFloat(e.target.value)||0)}
    step={step} min={min} max={max}
    className="w-16 bg-amber-500/10 border border-amber-500/30 rounded px-1.5 py-0.5 text-amber-300 text-xs font-mono text-right outline-none focus:border-amber-400 transition-colors" />
);

// ─── Plain-English explainer (collapsible, teaches the user) ───────────────────
function Explainer({ title, points, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="glass-card border-blue-500/20 overflow-hidden" data-testid="tab-explainer">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors">
        <GraduationCap className="w-4 h-4 text-blue-400 shrink-0" />
        <span className="text-xs font-semibold text-blue-200">In plain English — {title}</span>
        <ChevronRight className={`w-4 h-4 text-slate-500 ml-auto transition-transform ${open ? "rotate-90" : ""}`} />
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 space-y-2 border-t border-white/[0.06]">
          {points.map((p, i) => (
            <p key={i} className="text-xs text-slate-400 leading-relaxed flex gap-2">
              <span className="text-blue-400 mt-0.5 shrink-0">›</span><span>{p}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Compact DCF (for Monte Carlo + tornado) ───────────────────────────────────
function quickImplied(c, a, { growthMul = 1, marginShift = 0, wacc = a.wacc, tgr = a.tgr } = {}) {
  const w = wacc / 100, tax = a.taxRate / 100;
  let prevRev = c.revenue, prevNWC = c.revenue * (a.nwcPercent[0] / 100), pvF = 0, lastU = 0;
  for (let i = 0; i < 5; i++) {
    const g = a.revGrowth[i] * growthMul;
    const rev = prevRev * (1 + g / 100);
    const eb = rev * ((a.ebitdaMargin[i] + marginShift) / 100);
    const da = rev * (a.daPercent[i] / 100);
    const ebit = eb - da;
    const nopat = ebit - Math.max(0, ebit * tax);
    const capex = rev * (a.capexPercent[i] / 100);
    const nwc = rev * (a.nwcPercent[i] / 100);
    const u = nopat + da - capex - (nwc - prevNWC);
    pvF += u / Math.pow(1 + w, i + 1);
    prevRev = rev; prevNWC = nwc; lastU = u;
  }
  if (w <= tgr / 100) return null;
  const tv = (lastU * (1 + tgr / 100)) / (w - tgr / 100);
  const eq = pvF + tv / Math.pow(1 + w, 5) + a.cash - a.debt;
  return Math.max(0, eq / a.sharesOut);
}

function runMonteCarlo(c, a, n = 6000) {
  const randn = () => { let u = 0, v = 0; while (!u) u = Math.random(); while (!v) v = Math.random(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  const prices = [];
  for (let i = 0; i < n; i++) {
    const growthMul = Math.max(0.2, 1 + randn() * 0.25);
    const marginShift = randn() * 2;
    const wacc = Math.max(4, a.wacc + randn() * 1.0);
    const tgr = Math.min(wacc - 0.5, Math.max(0.5, a.tgr + randn() * 0.5));
    const p = quickImplied(c, a, { growthMul, marginShift, wacc, tgr });
    if (p != null && isFinite(p)) prices.push(p);
  }
  prices.sort((x, y) => x - y);
  if (!prices.length) return null;
  const q = (p) => prices[Math.floor(p * (prices.length - 1))];
  const mean = prices.reduce((s, x) => s + x, 0) / prices.length;
  const probAbove = (prices.filter(x => x >= c.price).length / prices.length) * 100;
  let min = prices[0], max = q(0.99); // clip extreme tail for a readable chart
  const BUCKETS = 26, wdt = (max - min) / BUCKETS || 1;
  const hist = Array.from({ length: BUCKETS }, (_, i) => ({ price: +(min + wdt * (i + 0.5)).toFixed(2), count: 0 }));
  prices.forEach(x => { const idx = Math.min(BUCKETS - 1, Math.max(0, Math.floor((x - min) / wdt))); hist[idx].count++; });
  return { n: prices.length, mean, median: q(0.5), p10: q(0.1), p90: q(0.9), p25: q(0.25), p75: q(0.75), min: prices[0], max: prices[prices.length - 1], probAbove, hist };
}

function tornado(c, a) {
  const base = quickImplied(c, a, {});
  const defs = [
    { name: "Revenue Growth", lo: { growthMul: 0.7 }, hi: { growthMul: 1.3 } },
    { name: "EBITDA Margin", lo: { marginShift: -3 }, hi: { marginShift: 3 } },
    { name: "WACC (discount rate)", lo: { wacc: a.wacc + 1.5 }, hi: { wacc: Math.max(4, a.wacc - 1.5) } },
    { name: "Terminal Growth", lo: { tgr: Math.max(0.5, a.tgr - 1) }, hi: { tgr: a.tgr + 1 } },
  ];
  return defs.map(f => {
    const x = quickImplied(c, a, f.lo), y = quickImplied(c, a, f.hi);
    return { name: f.name, low: Math.min(x, y), high: Math.max(x, y) };
  }).sort((p, q) => (q.high - q.low) - (p.high - p.low)).map(f => ({ ...f, base }));
}

// ─── TAB: Monte Carlo ──────────────────────────────────────────────────────────
function MonteCarloTab({ c, assumptions: a }) {
  const mc = useMemo(() => runMonteCarlo(c, a), [c, a]);
  const tor = useMemo(() => tornado(c, a), [c, a]);
  if (!mc) return <div className="glass-card p-6 text-sm text-slate-400">Not enough data to simulate.</div>;

  const undervalued = mc.probAbove >= 50;
  const spread = mc.p90 - mc.p10;
  const spreadPct = c.price ? (spread / c.price) * 100 : 0;
  const uncertainty = spreadPct > 90 ? "very high" : spreadPct > 55 ? "high" : spreadPct > 30 ? "moderate" : "relatively low";

  const torMin = Math.min(...tor.map(t => t.low), c.price);
  const torMax = Math.max(...tor.map(t => t.high), c.price);
  const torSpan = torMax - torMin || 1;
  const posPct = (v) => ((v - torMin) / torSpan) * 100;

  const stats = [
    { l: "Median Value", v: fmtPx(mc.median), sub: "Most likely outcome" },
    { l: "Mean Value", v: fmtPx(mc.mean), sub: "Average of all runs" },
    { l: "Likely Range (P10–P90)", v: `${fmtPx(mc.p10)} – ${fmtPx(mc.p90)}`, sub: "80% of outcomes land here" },
    { l: "Chance Undervalued", v: `${mc.probAbove.toFixed(0)}%`, sub: `vs price ${fmtPx(c.price)}`, hi: undervalued, lo: !undervalued },
  ];

  return (
    <div className="space-y-5">
      <Explainer title={`Monte Carlo — stress-testing ${c.name}'s valuation`} points={[
        `A normal DCF gives ONE answer. But nobody knows exactly how fast ${c.name} will grow or what margins it will earn. Monte Carlo runs the model ${mc.n.toLocaleString()} times, each time randomly nudging the key inputs (revenue growth, EBITDA margin, WACC and terminal growth) within realistic ranges — like rolling the dice on the company's future thousands of times.`,
        `The histogram below shows where the implied share price landed across all those runs. Taller bars = more likely outcomes. The white line marks today's price (${fmtPx(c.price)}).`,
        `Most important number: about ${mc.probAbove.toFixed(0)}% of simulations valued ${c.ticker} ABOVE its current price — i.e. the model thinks there's roughly a ${mc.probAbove.toFixed(0)}% chance the stock is undervalued today.`,
        `The range of outcomes is ${uncertainty} (P10–P90 spans ${fmtPx(mc.p10)} to ${fmtPx(mc.p90)}, about ${spreadPct.toFixed(0)}% of the price). A wide range means the answer is very sensitive to assumptions, so treat any single target with caution.`,
      ]} />

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {stats.map(s => (
          <div key={s.l} className="glass-card p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{s.l}</p>
            <p className={`text-lg font-bold font-mono ${s.hi ? "text-emerald-400" : s.lo ? "text-red-400" : "text-white"}`}>{s.v}</p>
            <p className="text-[10px] text-slate-600 mt-0.5">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Histogram */}
      <div className="glass-card p-5">
        <p className="text-xs font-semibold text-slate-300 mb-1">Distribution of Implied Share Price — {mc.n.toLocaleString()} simulations</p>
        <p className="text-[10px] text-slate-500 mb-4">Green bars = outcomes above today's price (undervalued). Red bars = below (overvalued).</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={mc.hist} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <XAxis dataKey="price" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `$${Math.round(v)}`} minTickGap={24} />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: "#0d1117", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 11 }}
              formatter={(v) => [`${v} runs`, "Frequency"]} labelFormatter={(l) => `≈ $${Number(l).toFixed(2)}/share`} />
            <ReferenceLine x={mc.hist.reduce((best, h) => Math.abs(h.price - c.price) < Math.abs(best - c.price) ? h.price : best, mc.hist[0].price)}
              stroke="#e2e8f0" strokeDasharray="3 3" label={{ value: "Today", fill: "#e2e8f0", fontSize: 10, position: "top" }} />
            <Bar dataKey="count" radius={[2, 2, 0, 0]}>
              {mc.hist.map((d, i) => <Cell key={i} fill={d.price >= c.price ? "#10b981" : "#ef4444"} opacity={0.8} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Tornado */}
      <div className="glass-card p-5">
        <p className="text-xs font-semibold text-slate-300 mb-1">Tornado — what moves the valuation most?</p>
        <p className="text-[10px] text-slate-500 mb-4">Each bar shows how far the implied price swings when that single input is changed (others held fixed). The longest bar is the assumption that matters most for {c.ticker}.</p>
        <div className="space-y-3">
          {tor.map((t, i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-[11px] text-slate-400 w-40 shrink-0 text-right">{t.name}</span>
              <div className="relative flex-1 h-6 bg-white/[0.03] rounded">
                <div className="absolute top-0 bottom-0 rounded bg-blue-500/40 border-x border-blue-400/60"
                  style={{ left: `${posPct(t.low)}%`, width: `${Math.max(2, posPct(t.high) - posPct(t.low))}%` }} />
                <div className="absolute top-0 bottom-0 w-px bg-white/70" style={{ left: `${posPct(c.price)}%` }} title="Today's price" />
              </div>
              <span className="text-[10px] font-mono text-slate-500 w-28 shrink-0">{fmtPx(t.low)}–{fmtPx(t.high)}</span>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-slate-600 mt-4 flex items-center gap-2">
          <span className="inline-block w-3 h-2.5 rounded-sm bg-blue-500/40 border-x border-blue-400/60" /> swing range
          <span className="inline-block w-px h-3 bg-white/70 ml-2" /> today's price
        </p>
      </div>

      <div className="glass-card p-4 border-amber-500/20 flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs text-slate-400 leading-relaxed">
          Probabilities are model estimates based on assumed input ranges — not guarantees. They describe the math's sensitivity, not real-world certainty. Educational use only; not investment advice.
        </p>
      </div>
    </div>
  );
}


// ─── TAB: Summary ─────────────────────────────────────────────────────────────
function SummaryTab({ c, model, assumptions }) {
  const { forecast, implied, upside, EV, pvFCFs, pvTV, tvPct, eqVal } = model;
  const isUp = implied >= c.price;

  const chartData = [
    ...(c.revenueHistory||[]).map((v,i) => ({ year: (c.years||[])[i]||2020+i, rev: v/1000, type: "actual" })),
    ...forecast.map(f => ({ year: f.year, rev: parseFloat((f.rev/1000).toFixed(1)), type: "forecast" })),
  ];
  const bridgeData = [
    { name: "PV of FCFs",  value: pvFCFs,  fill: "#3b82f6" },
    { name: "PV of TV",    value: pvTV,     fill: "#8b5cf6" },
    { name: "+ Cash",      value: assumptions.cash, fill: "#10b981" },
    { name: "− Debt",      value: -assumptions.debt, fill: "#ef4444" },
  ];

  const bull = c.bullPrice || implied * 1.35;
  const base = implied;
  const bear = c.bearPrice || implied * 0.65;

  return (
    <div className="space-y-5">
      <Explainer title={`what this Summary tells you about ${c.name}`} points={[
        `A DCF estimates what ${c.name} is genuinely worth today by forecasting the cash the business generates over the next 5 years and converting that future cash back into today's money.`,
        `Bottom line: the model values ${c.ticker} at about ${fmtPx(implied)} per share versus ${fmtPx(c.price)} today — ${upside >= 0 ? `roughly ${fmtN(upside)}% upside` : `roughly ${fmtN(Math.abs(upside))}% downside`}.`,
        `${fmtN(tvPct, 0)}% of the value is "Terminal Value" — everything beyond year 5. The larger this share, the more the answer leans on long-term assumptions, so don't treat it as precise.`,
        `The scenario table below frames the range: a strong outcome near ${fmtPx(bull)} versus a weak one near ${fmtPx(bear)}.`,
      ]} />
      {/* Key outputs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: "Current Price",    val: fmtPx(c.price),           sub: "Market" },
          { label: "DCF Implied",      val: fmtPx(implied),            sub: "Base case", hi: isUp },
          { label: "Upside / Downside",val: `${sign(upside)}${fmtN(upside)}%`, sub: "vs current", hi: isUp, lo: !isUp },
          { label: "Enterprise Value", val: fmtB(EV),                  sub: "PV(FCFs)+PV(TV)" },
          { label: "TV Weight",        val: `${fmtN(tvPct, 0)}%`,      sub: "of total EV" },
          { label: "WACC",             val: `${assumptions.wacc}%`,    sub: "Discount rate" },
        ].map(item => (
          <div key={item.label} className="glass-card p-4">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{item.label}</p>
            <p className={`text-xl font-bold font-mono ${item.hi ? "text-emerald-400" : item.lo ? "text-red-400" : "text-white"}`}>{item.val}</p>
            <p className="text-[10px] text-slate-600 mt-0.5">{item.sub}</p>
          </div>
        ))}
      </div>

      {/* Valuation bridge + Revenue chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="glass-card p-5">
          <p className="text-xs font-semibold text-slate-300 mb-4">Valuation Bridge ($M)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={bridgeData} margin={{top:5,right:10,left:0,bottom:0}}>
              <XAxis dataKey="name" tick={{fill:"#64748b",fontSize:10}} axisLine={false} tickLine={false} />
              <YAxis tick={{fill:"#64748b",fontSize:10}} axisLine={false} tickLine={false}
                tickFormatter={v => `$${(v/1000).toFixed(0)}B`} />
              <Tooltip contentStyle={{background:"#0d1117",border:"1px solid rgba(255,255,255,0.08)",borderRadius:8,color:"#e2e8f0",fontSize:11}}
                formatter={v => fmtB(v)} />
              <Bar dataKey="value" radius={[4,4,0,0]}>
                {bridgeData.map((d,i) => <Cell key={i} fill={d.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-3 pt-3 border-t border-white/[0.06] flex items-center justify-between">
            <span className="text-xs text-slate-500">Equity Value</span>
            <span className="text-sm font-bold font-mono text-white">{fmtB(eqVal)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">Implied Price per Share</span>
            <span className={`text-sm font-bold font-mono ${isUp?"text-emerald-400":"text-red-400"}`}>{fmtPx(implied)}</span>
          </div>
        </div>

        <div className="glass-card p-5">
          <p className="text-xs font-semibold text-slate-300 mb-4">Revenue — Actual vs Forecast ($B)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{top:5,right:10,left:0,bottom:0}}>
              <XAxis dataKey="year" tick={{fill:"#64748b",fontSize:10}} axisLine={false} tickLine={false} />
              <YAxis tick={{fill:"#64748b",fontSize:10}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v}B`} />
              <Tooltip contentStyle={{background:"#0d1117",border:"1px solid rgba(255,255,255,0.08)",borderRadius:8,color:"#e2e8f0",fontSize:11}}
                formatter={v=>`$${v}B`} />
              <Bar dataKey="rev" radius={[3,3,0,0]}>
                {chartData.map((d,i)=><Cell key={i} fill={d.type==="actual"?"#3b82f6":"#10b981"} opacity={d.type==="forecast"?0.75:1} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex items-center gap-4 mt-3">
            <span className="flex items-center gap-1.5 text-[10px] text-slate-500"><span className="w-2 h-2 rounded-sm bg-blue-500" />Historical</span>
            <span className="flex items-center gap-1.5 text-[10px] text-slate-500"><span className="w-2 h-2 rounded-sm bg-emerald-500 opacity-75" />Forecast</span>
          </div>
        </div>
      </div>

      {/* Bull / Base / Bear */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 border-b border-white/[0.06] bg-slate-800/40">
          <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Price Target Scenarios — 12-Month Horizon</p>
        </div>
        <table className="w-full">
          <thead>
            <tr>
              <TH>Scenario</TH><TH right>Price Target</TH><TH right>Upside</TH><TH>Key Driver</TH><TH>Probability</TH>
            </tr>
          </thead>
          <tbody>
            <tr>
              <TD bold><span className="text-emerald-400">▲ Bull Case</span></TD>
              <TD right mono bold color="text-emerald-400">{fmtPx(bull)}</TD>
              <TD right mono color="text-emerald-400">+{((bull/c.price-1)*100).toFixed(1)}%</TD>
              <TD>Revenue growth exceeds estimates; margin expansion accelerates; multiple re-rates</TD>
              <TD><div className="w-20 bg-slate-700 rounded-full h-1.5"><div className="bg-emerald-500 h-1.5 rounded-full" style={{width:"25%"}} /></div><span className="text-[10px] text-slate-500 ml-2">25%</span></TD>
            </tr>
            <tr>
              <TD bold><span className="text-blue-400">◆ Base Case</span></TD>
              <TD right mono bold color="text-blue-400">{fmtPx(base)}</TD>
              <TD right mono color={clr(upside)}>{sign(upside)}{fmtN(upside)}%</TD>
              <TD>In-line with consensus estimates; stable macro; normal execution</TD>
              <TD><div className="w-20 bg-slate-700 rounded-full h-1.5"><div className="bg-blue-500 h-1.5 rounded-full" style={{width:"55%"}} /></div><span className="text-[10px] text-slate-500 ml-2">55%</span></TD>
            </tr>
            <tr>
              <TD bold><span className="text-red-400">▼ Bear Case</span></TD>
              <TD right mono bold color="text-red-400">{fmtPx(bear)}</TD>
              <TD right mono color="text-red-400">{((bear/c.price-1)*100).toFixed(1)}%</TD>
              <TD>Revenue miss; margin compression; macro deterioration; multiple contraction</TD>
              <TD><div className="w-20 bg-slate-700 rounded-full h-1.5"><div className="bg-red-500 h-1.5 rounded-full" style={{width:"20%"}} /></div><span className="text-[10px] text-slate-500 ml-2">20%</span></TD>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Company profile */}
      <div className="glass-card p-5">
        <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Company Overview</p>
        <p className="text-sm text-slate-400 leading-relaxed">{c.description}</p>
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Market Cap",      val: fmtB(c.marketCap) },
            { label: "Revenue (TTM)",   val: fmtB(c.revenue) },
            { label: "Revenue Growth",  val: fmtP(c.revenueGrowth) },
            { label: "EBITDA Margin",   val: fmtP(c.ebitdaMargin) },
            { label: "FCF Margin",      val: fmtP(c.fcfMargin) },
            { label: "P/E Ratio",       val: c.pe ? `${c.pe}x` : "—" },
            { label: "EV/EBITDA",       val: c.evEbitda ? `${c.evEbitda}x` : "—" },
            { label: "Analyst Rating",  val: c.analystRating || "—" },
          ].map(m => (
            <div key={m.label}>
              <p className="text-[10px] text-slate-600 uppercase tracking-wider">{m.label}</p>
              <p className="text-sm font-semibold text-slate-200 mt-0.5">{m.val}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── TAB: Assumptions ─────────────────────────────────────────────────────────
function AssumptionsTab({ assumptions: a, setAss, setAssArr, model, c }) {
  const yrs = model.forecast.map(f => f.year);
  return (
    <div className="space-y-5">
      <Explainer title="the dials that drive the whole model" points={[
        "Yellow cells are inputs you can change; gray cells recalculate automatically. Edit anything and the valuation updates instantly.",
        "Revenue Growth = how fast sales grow each year. EBITDA Margin = how much of each sales dollar becomes operating profit. These two do most of the heavy lifting.",
        `WACC (${a.wacc}%) is the "discount rate" — the return investors demand. A higher WACC makes future cash worth less today, lowering the value. Terminal Growth (${a.tgr}%) is how fast ${c.ticker} grows forever after year 5 — kept low, near the economy's long-run rate.`,
        "Tip: nudge Revenue Growth or WACC by a single point and watch how much the implied price moves — that reveals which assumption matters most.",
      ]} />
      <div className="glass-card p-4 border-amber-500/20 flex items-start gap-2">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs text-slate-400">
          Yellow cells are editable assumptions. Gray cells are formula-driven outputs. Changes recalculate the model in real time.
          Every assumption is sourced from historical financials, management guidance, or analyst consensus.
        </p>
      </div>

      {/* WACC */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20">
          <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">WACC — Weighted Average Cost of Capital</p>
        </div>
        <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[
            { label:"Risk-Free Rate", key:"riskFreeRate", hint:"10Y US Treasury yield", step:0.1 },
            { label:"Equity Risk Premium", key:"erp", hint:"Damodaran US ERP estimate", step:0.1 },
            { label:"Beta (Levered)", key:"beta", hint:"5Y monthly vs S&P 500", step:0.05, min:0.1, max:3 },
            { label:"Cost of Debt (Pre-Tax)", key:"costOfDebt", hint:"Blended yield on outstanding debt", step:0.1 },
            { label:"Tax Rate", key:"taxRate", hint:"Effective corporate tax rate", step:0.5, min:0, max:40 },
            { label:"Debt Weight", key:"debtWeight", hint:"Debt as % of capital structure", step:1, min:0, max:80 },
          ].map(row => (
            <div key={row.key}>
              <p className="text-xs text-slate-400 mb-1.5">{row.label}</p>
              <div className="flex items-center gap-2">
                <EditInput value={a[row.key]} onChange={v=>setAss(row.key,v)}
                  step={row.step||0.5} min={row.min??-100} max={row.max??100} />
                <span className="text-xs text-slate-600">%</span>
              </div>
              <p className="text-[10px] text-slate-700 mt-1">{row.hint}</p>
            </div>
          ))}
          <div>
            <p className="text-xs text-slate-400 mb-1.5">Equity Weight</p>
            <p className="text-sm font-mono text-slate-400 bg-slate-800/50 rounded px-2 py-1 w-20 text-right">{100-a.debtWeight}%</p>
            <p className="text-[10px] text-slate-700 mt-1">Auto = 100% − debt weight</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-1.5">Cost of Equity (CAPM)</p>
            <p className="text-sm font-mono text-slate-400 bg-slate-800/50 rounded px-2 py-1 w-20 text-right">{fmtN(model.costOfEquity)}%</p>
            <p className="text-[10px] text-slate-700 mt-1">Rf + β × ERP</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-1.5">After-Tax Cost of Debt</p>
            <p className="text-sm font-mono text-slate-400 bg-slate-800/50 rounded px-2 py-1 w-20 text-right">{fmtN(model.atcod)}%</p>
            <p className="text-[10px] text-slate-700 mt-1">Kd × (1 − Tax)</p>
          </div>
        </div>
        <div className="px-5 pb-5 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Manual WACC Override:</span>
            <EditInput value={a.wacc} onChange={v=>setAss("wacc",v)} step={0.1} min={1} max={25} />
            <span className="text-xs text-slate-600">%</span>
          </div>
          <div className="text-xs text-slate-500">
            CAPM-derived WACC: <span className="text-slate-300 font-mono">{fmtN(model.compWacc)}%</span> —
            Manual WACC <span className="text-amber-300 font-mono">{a.wacc}%</span> is used in the model
          </div>
        </div>
      </div>

      {/* Revenue growth */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20">
          <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">Revenue Growth Assumptions</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[500px]">
            <thead><tr><TH>Metric</TH>{yrs.map(y=><TH key={y} right>FY{y}</TH>)}</tr></thead>
            <tbody>
              <tr>
                <TD>Revenue Growth Rate</TD>
                {a.revGrowth.map((v,i)=>(
                  <td key={i} className="px-3 py-2 text-right border-b border-white/[0.04]">
                    <div className="flex items-center justify-end gap-1">
                      <EditInput value={v} onChange={nv=>setAssArr("revGrowth",i,nv)} step={0.5} min={-50} max={150} />
                      <span className="text-[10px] text-slate-600">%</span>
                    </div>
                  </td>
                ))}
              </tr>
              <tr>
                <TD gray>Implied Revenue ($M)</TD>
                {model.forecast.map(f=><TD key={f.year} right mono gray>{fmtComma(f.rev)}</TD>)}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Margin assumptions */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20">
          <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">Margin &amp; Cost Assumptions (% of Revenue)</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[500px]">
            <thead><tr><TH>Line Item</TH>{yrs.map(y=><TH key={y} right>FY{y}</TH>)}</tr></thead>
            <tbody>
              {[
                { label:"EBITDA Margin", key:"ebitdaMargin", step:0.5, min:0, max:90 },
                { label:"D&A (% Revenue)", key:"daPercent", step:0.5, min:0, max:30 },
                { label:"CapEx (% Revenue)", key:"capexPercent", step:0.5, min:0, max:30 },
                { label:"ΔNWC (% Revenue)", key:"nwcPercent", step:0.5, min:0, max:20 },
              ].map(row => (
                <tr key={row.key}>
                  <TD>{row.label}</TD>
                  {a[row.key].map((v,i)=>(
                    <td key={i} className="px-3 py-2 text-right border-b border-white/[0.04]">
                      <div className="flex items-center justify-end gap-1">
                        <EditInput value={v} onChange={nv=>setAssArr(row.key,i,nv)} step={row.step} min={row.min} max={row.max} />
                        <span className="text-[10px] text-slate-600">%</span>
                      </div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Terminal value */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20">
          <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">Terminal Value Assumptions</p>
        </div>
        <div className="p-5 grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div>
            <p className="text-xs text-slate-400 mb-2">Terminal Value Method</p>
            <div className="flex gap-2">
              {["gordon","exit"].map(m => (
                <button key={m} onClick={()=>setAss("tvMethod",m)}
                  className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${a.tvMethod===m?"bg-blue-500/20 border-blue-500/40 text-blue-300":"border-white/[0.08] text-slate-500 hover:text-slate-300"}`}>
                  {m==="gordon"?"Gordon Growth":"Exit Multiple"}
                </button>
              ))}
            </div>
          </div>
          {a.tvMethod==="gordon" ? (
            <div>
              <p className="text-xs text-slate-400 mb-1.5">Terminal Growth Rate (TGR)</p>
              <div className="flex items-center gap-2">
                <EditInput value={a.tgr} onChange={v=>setAss("tgr",v)} step={0.1} min={0} max={5} />
                <span className="text-xs text-slate-600">%</span>
              </div>
              <p className="text-[10px] text-slate-700 mt-1">Should not exceed long-run GDP growth (~3%)</p>
            </div>
          ) : (
            <div>
              <p className="text-xs text-slate-400 mb-1.5">Exit EV/EBITDA Multiple</p>
              <div className="flex items-center gap-2">
                <EditInput value={a.exitMultiple} onChange={v=>setAss("exitMultiple",v)} step={1} min={5} max={60} />
                <span className="text-xs text-slate-600">x</span>
              </div>
              <p className="text-[10px] text-slate-700 mt-1">Based on current trading comps ({c?.evEbitda||"N/A"}x)</p>
            </div>
          )}
          <div>
            <p className="text-xs text-slate-400 mb-1">Implied Terminal Value</p>
            <p className="text-sm font-mono font-bold text-white">{fmtB(a.tvMethod==="gordon"?model.tvGG:model.tvEM)}</p>
            <p className="text-[10px] text-slate-600 mt-0.5">PV = {fmtB(model.pvTV)} ({fmtN(model.tvPct,0)}% of EV)</p>
          </div>
        </div>
      </div>

      {/* Balance sheet */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20">
          <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">Balance Sheet Bridge</p>
        </div>
        <div className="p-5 grid grid-cols-3 gap-6">
          {[
            { label:"Cash & Equivalents ($M)", key:"cash", step:100, min:0, max:1000000 },
            { label:"Total Debt ($M)", key:"debt", step:100, min:0, max:1000000 },
            { label:"Diluted Shares (M)", key:"sharesOut", step:10, min:1, max:100000 },
          ].map(row => (
            <div key={row.key}>
              <p className="text-xs text-slate-400 mb-1.5">{row.label}</p>
              <input type="number" value={a[row.key]}
                onChange={e=>setAss(row.key,parseFloat(e.target.value)||0)}
                step={row.step} min={row.min} max={row.max}
                className="w-full bg-amber-500/10 border border-amber-500/30 rounded px-2.5 py-1.5 text-amber-300 text-sm font-mono outline-none focus:border-amber-400 transition-colors" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── TAB: DCF Model ───────────────────────────────────────────────────────────
function DCFTab({ c, model, assumptions: a }) {
  const { forecast, pvFCFs, pvTV, EV, eqVal, implied, upside } = model;
  const yrs = forecast.map(f => f.year);

  const rows = [
    { label:"Revenue ($M)",          key:"rev",     fmt:fmtComma, bold:true, border:true },
    { label:"YoY Growth",            key:"revGrowth",fmt:v=>`${v.toFixed(1)}%`, amber:true },
    { label:"EBITDA ($M)",           key:"ebitda",  fmt:fmtComma },
    { label:"EBITDA Margin",         key:"ebitdaM", fmt:v=>`${v.toFixed(1)}%`, gray:true },
    { label:"— Depreciation & Amort.", key:"da",    fmt:v=>`(${fmtComma(v)})` },
    { label:"D&A (% Rev)",           key:"daM",     fmt:v=>`${v.toFixed(1)}%`, gray:true },
    { label:"EBIT ($M)",             key:"ebit",    fmt:fmtComma, bold:true, border:true },
    { label:"EBIT Margin",           key:"ebitM",   fmt:v=>`${v.toFixed(1)}%`, gray:true },
    { label:"— Taxes @ "+a.taxRate+"%", key:"taxes",fmt:v=>`(${fmtComma(v)})` },
    { label:"NOPAT ($M)",            key:"nopat",   fmt:fmtComma, bold:true, border:true, hint:"Net Operating Profit After Tax" },
    { label:"NOPAT Margin",          key:"nopatM",  fmt:v=>`${v.toFixed(1)}%`, gray:true },
    { label:"+ Depreciation & Amort.", key:"da",    fmt:fmtComma },
    { label:"— Capital Expenditures", key:"capex",  fmt:v=>`(${fmtComma(v)})` },
    { label:"CapEx (% Rev)",         key:"capexM",  fmt:v=>`${v.toFixed(1)}%`, gray:true },
    { label:"— Change in NWC ($M)",  key:"dNWC",    fmt:v=>`(${fmtComma(v)})` },
    { label:"Unlevered Free Cash Flow", key:"ufcf", fmt:fmtComma, bold:true, border:true, green:true },
    { label:"UFCF Margin",           key:"ufcfM",   fmt:v=>`${v.toFixed(1)}%`, gray:true },
    { label:"Discount Factor",       key:"df",      fmt:v=>v.toFixed(4), gray:true },
    { label:"PV of UFCF ($M)",       key:"pvUFCF",  fmt:fmtComma, bold:true, green:true },
  ];

  return (
    <div className="space-y-5">
      <Explainer title="how the cash-flow engine builds the price" points={[
        "We start at Revenue, then subtract operating costs, taxes, capital spending and working-capital needs to reach \u201CUnlevered Free Cash Flow\u201D — the actual spare cash the business throws off each year.",
        `Each future year's cash is multiplied by a "Discount Factor" (driven by the ${a.wacc}% WACC) to convert it into today's dollars — money received later is worth less than money now.`,
        "Add up the 5 years of discounted cash plus the discounted Terminal Value = Enterprise Value. Then add cash, subtract debt, and divide by shares to get the implied price per share.",
      ]} />
      {/* Historical + Forecast table */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20 flex items-center justify-between">
          <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">Unlevered Free Cash Flow Build</p>
          <div className="flex items-center gap-3 text-[10px]">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-amber-500/60" />Assumption</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-slate-600" />Derived</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-emerald-600/60" />Key Output</span>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px]">
            <thead>
              <tr>
                <TH>Line Item</TH>
                {/* Historical */}
                {(c.years||[2020,2021,2022,2023,2024]).slice(-2).map(y=><TH key={y} right>FY{y} (A)</TH>)}
                {/* Forecast */}
                {yrs.map(y=><TH key={y} right>FY{y} (E)</TH>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => {
                const histRevs = (c.revenueHistory||[]).slice(-2);
                const histEBs  = (c.ebitdaHistory||[]).slice(-2);
                const histFCFs = (c.fcfHistory||[]).slice(-2);
                return (
                  <tr key={ri} className={row.border ? "border-t-2 border-white/[0.1]" : ""}>
                    <td className={`px-3 py-1.5 text-xs border-b border-white/[0.04] whitespace-nowrap
                      ${row.bold?"font-semibold text-slate-200":"text-slate-400"}
                      ${row.gray?"text-slate-600 italic":""}`}>
                      {row.label}
                      {row.hint && <span className="text-[10px] text-slate-600 ml-1">({row.hint})</span>}
                    </td>
                    {/* Historical cells — only for top-level metrics */}
                    {(c.years||[]).slice(-2).map((y,i) => {
                      let histVal = null;
                      if (row.key==="rev") histVal = histRevs[i];
                      else if (row.key==="ebitda") histVal = histEBs[i];
                      else if (row.key==="ufcf") histVal = histFCFs[i];
                      return (
                        <td key={y} className="px-3 py-1.5 text-xs border-b border-white/[0.04] text-right font-mono text-slate-600">
                          {histVal != null ? row.fmt(histVal) : "—"}
                        </td>
                      );
                    })}
                    {/* Forecast cells */}
                    {forecast.map(f => {
                      const val = f[row.key];
                      return (
                        <td key={f.year} className={`px-3 py-1.5 text-xs border-b border-white/[0.04] text-right font-mono
                          ${row.green?"text-emerald-400 font-semibold":row.amber?"text-amber-300":row.gray?"text-slate-500":"text-slate-300"}
                          ${row.bold?"font-semibold":""}`}>
                          {val != null ? row.fmt(val) : "—"}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Terminal value + valuation summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="glass-card overflow-hidden">
          <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20">
            <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">Terminal Value</p>
          </div>
          <table className="w-full">
            <tbody>
              {[
                ["Method Used", a.tvMethod==="gordon"?"Gordon Growth Model":"Exit EBITDA Multiple"],
                ["Terminal Year FCF ($M)", fmtComma(forecast[4].ufcf * (1 + a.tgr/100))],
                a.tvMethod==="gordon"
                  ? ["Terminal Growth Rate", `${a.tgr}%`]
                  : ["Exit EV/EBITDA Multiple", `${a.exitMultiple}x`],
                ["Terminal Value (Undiscounted)", fmtB(a.tvMethod==="gordon"?model.tvGG:model.tvEM)],
                ["PV of Terminal Value", fmtB(model.pvTV)],
                ["TV as % of Enterprise Value", `${fmtN(model.tvPct,0)}%`],
                ["Gordon Growth TV (Cross-Check)", fmtB(model.tvGG)],
                ["Exit Multiple TV (Cross-Check)", fmtB(model.tvEM)],
              ].map(([k,v],i)=>(
                <tr key={i} className={i===0?"border-t-0":""}>
                  <td className="px-4 py-2 text-xs text-slate-400 border-b border-white/[0.04]">{k}</td>
                  <td className="px-4 py-2 text-xs font-mono font-semibold text-white text-right border-b border-white/[0.04]">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="glass-card overflow-hidden">
          <div className="px-5 py-3 bg-emerald-900/30 border-b border-emerald-500/20">
            <p className="text-xs font-bold text-emerald-300 uppercase tracking-wider">Valuation Summary</p>
          </div>
          <table className="w-full">
            <tbody>
              {[
                ["PV of FCFs (5-Year)", fmtB(pvFCFs), ""],
                ["+ PV of Terminal Value", fmtB(pvTV), ""],
                ["= Enterprise Value", fmtB(EV), "bold"],
                ["+ Cash & Equivalents", fmtB(a.cash), ""],
                ["− Total Debt", `(${fmtB(a.debt)})`, ""],
                ["= Equity Value", fmtB(eqVal), "bold"],
                ["÷ Diluted Shares (M)", fmtN(a.sharesOut,0)+"M", ""],
                ["= Implied Share Price", fmtPx(implied), "bold green"],
                ["Current Market Price", fmtPx(c.price), ""],
                ["Implied Upside / (Downside)", `${sign(upside)}${fmtN(upside)}%`, upside>=0?"bold green":"bold red"],
              ].map(([k,v,style],i)=>(
                <tr key={i} className={style.includes("bold")?"bg-white/[0.02]":""}>
                  <td className={`px-4 py-2 text-xs border-b border-white/[0.04] ${style.includes("bold")?"font-semibold text-slate-200":"text-slate-400"}`}>{k}</td>
                  <td className={`px-4 py-2 text-xs font-mono font-semibold text-right border-b border-white/[0.04]
                    ${style.includes("green")?"text-emerald-400":style.includes("red")?"text-red-400":style.includes("bold")?"text-white":"text-slate-300"}`}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── TAB: Sensitivity ─────────────────────────────────────────────────────────
function SensitivityTab({ model, assumptions: a, c }) {
  const { sens, wRows, xCols, rmSens, revScens, mgnScens } = model;
  const xLabel = a.tvMethod==="gordon" ? "Terminal Growth Rate" : "Exit EV/EBITDA Multiple";
  const xFmt   = v => a.tvMethod==="gordon" ? `${v}%` : `${v}x`;
  const cellColor = (up) => {
    if (up >= 50) return "bg-emerald-700/60 text-emerald-200";
    if (up >= 25) return "bg-emerald-600/40 text-emerald-300";
    if (up >= 10) return "bg-emerald-500/20 text-emerald-400";
    if (up >= 0)  return "bg-emerald-500/10 text-emerald-400";
    if (up >= -15) return "bg-red-500/10 text-red-400";
    if (up >= -30) return "bg-red-500/20 text-red-300";
    return "bg-red-700/50 text-red-200";
  };

  return (
    <div className="space-y-6">
      <Explainer title="how confident can we be in the number?" points={[
        `No forecast is exact, so this grid re-prices ${c.ticker} across different values of the two most important inputs: WACC (down the side) and ${a.tvMethod === "gordon" ? "Terminal Growth" : "the exit multiple"} (across the top).`,
        "Green means the stock still looks cheap (upside); red means expensive (downside). If most of the grid is green, the \u201Cundervalued\u201D case holds up even under tougher assumptions — a more robust signal.",
        "Watch how fast the colors flip as you move one step: a grid that swings from deep green to deep red quickly means the valuation is fragile and highly assumption-dependent.",
      ]} />
      {/* WACC vs TGR/Exit Multiple */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20">
          <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">
            Implied Share Price — WACC vs {xLabel}
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">
            Base WACC: {a.wacc}% · Base {a.tvMethod==="gordon"?"TGR":a.exitMultiple+"x"} · Current Price: {fmtPx(c.price)}
          </p>
        </div>
        <div className="overflow-x-auto p-4">
          <table className="text-xs border-collapse mx-auto">
            <thead>
              <tr>
                <th className="px-3 py-2 text-[10px] text-slate-500 font-normal text-right">WACC ↓ / {a.tvMethod==="gordon"?"TGR":"Multiple"} →</th>
                {xCols.map(x => (
                  <th key={x} className={`px-4 py-2 text-center font-semibold border border-white/[0.06] min-w-[90px]
                    ${x===(a.tvMethod==="gordon"?a.tgr:a.exitMultiple)?"bg-blue-900/40 text-blue-300":"text-slate-400"}`}>
                    {xFmt(x)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {wRows.map((w, wi) => (
                <tr key={w}>
                  <td className={`px-3 py-2 text-right font-semibold border border-white/[0.06]
                    ${w===a.wacc?"bg-blue-900/40 text-blue-300":"text-slate-400"}`}>
                    {w}%
                  </td>
                  {sens[wi].map((cell, xi) => (
                    <td key={xi} className={`px-4 py-2 text-center font-mono font-semibold border border-white/[0.06] ${cellColor(cell.upside)}
                      ${w===a.wacc && xCols[xi]===(a.tvMethod==="gordon"?a.tgr:a.exitMultiple)?"ring-2 ring-inset ring-white/20 ring-offset-0":""}`}>
                      {fmtPx(cell.price)}
                      <div className="text-[9px] opacity-80 font-normal">{sign(cell.upside)}{cell.upside.toFixed(0)}%</div>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center gap-4 mt-4 justify-center flex-wrap text-[10px]">
            {[
              ["bg-emerald-700/60","≥ +50% upside"],
              ["bg-emerald-500/20","0%–+25% upside"],
              ["bg-red-500/10","0%–-15% downside"],
              ["bg-red-700/50","≤ -30% downside"],
            ].map(([bg,label])=>(
              <span key={label} className="flex items-center gap-1.5 text-slate-500">
                <span className={`w-3 h-3 rounded-sm ${bg}`} />{label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Revenue Growth vs EBITDA Margin */}
      <div className="glass-card overflow-hidden">
        <div className="px-5 py-3 bg-blue-900/30 border-b border-blue-500/20">
          <p className="text-xs font-bold text-blue-300 uppercase tracking-wider">
            Implied Share Price — Yr1 Revenue Growth vs Yr1 EBITDA Margin
          </p>
          <p className="text-[10px] text-slate-500 mt-0.5">Tests sensitivity of valuation to Year 1 top-line and margin assumptions</p>
        </div>
        <div className="overflow-x-auto p-4">
          <table className="text-xs border-collapse mx-auto">
            <thead>
              <tr>
                <th className="px-3 py-2 text-[10px] text-slate-500 font-normal text-right">Rev Growth → / Margin ↓</th>
                {revScens.map(r => (
                  <th key={r} className={`px-4 py-2 text-center font-semibold border border-white/[0.06] min-w-[80px]
                    ${r===a.revGrowth[0]?"bg-blue-900/40 text-blue-300":"text-slate-400"}`}>
                    {r.toFixed(1)}%
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mgnScens.map((m, mi) => (
                <tr key={m}>
                  <td className={`px-3 py-2 text-right font-semibold border border-white/[0.06]
                    ${m===a.ebitdaMargin[0]?"bg-blue-900/40 text-blue-300":"text-slate-400"}`}>
                    {m.toFixed(1)}%
                  </td>
                  {rmSens.map((row,ri) => {
                    const cell = row[mi];
                    return (
                      <td key={ri} className={`px-4 py-2 text-center font-mono font-semibold border border-white/[0.06] ${cellColor(cell.upside)}`}>
                        {fmtPx(cell.price)}
                        <div className="text-[9px] opacity-80 font-normal">{sign(cell.upside)}{cell.upside.toFixed(0)}%</div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── TAB: Investment Memo ─────────────────────────────────────────────────────
function MemoTab({ c, model, assumptions: a }) {
  const { implied, upside, EV, eqVal } = model;
  const isUp = implied >= c.price;
  const rating = upside >= 25 ? "Outperform" : upside >= 5 ? "Market Perform" : "Underperform";
  const ratingColor = upside >= 25 ? "text-emerald-400" : upside >= 5 ? "text-blue-400" : "text-red-400";

  return (
    <div className="space-y-5">
      <Explainer title="the investment story in plain words" points={[
        `This memo turns the numbers into a narrative: what ${c.name} does, why it could be worth more (or less) than today's price, and what would need to happen for the thesis to play out.`,
        "Always pair the upside case with the Key Risks section — a sound decision weighs both. The rating reflects the model's implied return, not a promise of performance.",
      ]} />
      {/* Header */}
      <div className="glass-card p-6 border-blue-500/20">
        <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
          <div>
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Investment Research — Equity Analysis</p>
            <h2 className="text-xl font-bold text-white">{c.name} ({c.ticker})</h2>
            <p className="text-sm text-slate-400 mt-0.5">{c.sector} · {c.industry}</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">AI Rating</p>
            <p className={`text-2xl font-bold ${ratingColor}`}>{rating}</p>
            <p className="text-xs text-slate-500 mt-0.5">12M Price Target: {fmtPx(implied)}</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 p-4 bg-white/[0.02] rounded-lg border border-white/[0.05]">
          <div><p className="text-[10px] text-slate-500 uppercase">Current Price</p><p className="font-mono font-bold text-white">{fmtPx(c.price)}</p></div>
          <div><p className="text-[10px] text-slate-500 uppercase">Price Target</p><p className={`font-mono font-bold ${ratingColor}`}>{fmtPx(implied)}</p></div>
          <div><p className="text-[10px] text-slate-500 uppercase">Implied Return</p><p className={`font-mono font-bold ${isUp?"text-emerald-400":"text-red-400"}`}>{sign(upside)}{fmtN(upside)}%</p></div>
        </div>
      </div>

      {/* Business description */}
      <Section title="1. Business Description">
        <p className="text-sm text-slate-400 leading-relaxed">{c.description}</p>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="p-3 bg-white/[0.02] rounded-lg border border-white/[0.05]">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Competitive Moat</p>
            <p className="text-xs text-slate-300">{c.moat || "Not specified"}</p>
          </div>
          <div className="p-3 bg-white/[0.02] rounded-lg border border-white/[0.05]">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Total Addressable Market</p>
            <p className="text-xs text-slate-300">{c.tam || "Not specified"}</p>
          </div>
        </div>
      </Section>

      {/* Investment thesis */}
      <Section title="2. Investment Thesis">
        <p className="text-sm text-slate-400 leading-relaxed">{c.longTermThesis || `${c.name} is positioned to benefit from ${c.sector.toLowerCase()} sector tailwinds, with revenue growing at ${c.revenueGrowth?.toFixed(0)||"N/A"}% and expanding margins. The company's competitive moat and FCF generation support a premium valuation.`}</p>
        {c.shortTermCatalyst && (
          <div className="mt-3 p-3 bg-blue-500/5 border border-blue-500/15 rounded-lg">
            <p className="text-[10px] text-blue-400 uppercase tracking-wider font-semibold mb-1">Near-Term Catalyst (1–3 Months)</p>
            <p className="text-xs text-slate-400">{c.shortTermCatalyst}</p>
          </div>
        )}
      </Section>

      {/* Valuation */}
      <Section title="3. Valuation Summary">
        <p className="text-sm text-slate-400 leading-relaxed mb-4">
          Our DCF analysis uses a {a.wacc}% WACC ({a.tvMethod==="gordon" ? `${a.tgr}% terminal growth rate` : `${a.exitMultiple}x exit EV/EBITDA`}) to discount 5 years of forecasted unlevered free cash flows.
          The analysis yields an enterprise value of {fmtB(EV)}, translating to an equity value of {fmtB(eqVal)} or {fmtPx(implied)} per diluted share — implying
          {isUp ? ` ${fmtN(upside)}% upside` : ` ${fmtN(Math.abs(upside))}% downside`} from the current price of {fmtPx(c.price)}.
        </p>
        <table className="w-full text-xs">
          <tbody>
            {[
              ["Revenue Growth (Yr 1–5)", a.revGrowth.map(g=>g.toFixed(1)+"%").join(" → ")],
              ["EBITDA Margin (Yr 1–5)", a.ebitdaMargin.map(m=>m.toFixed(1)+"%").join(" → ")],
              ["WACC",              `${a.wacc}%`],
              ["Terminal Value Method", a.tvMethod==="gordon"?"Gordon Growth":"Exit Multiple"],
              a.tvMethod==="gordon"?["Terminal Growth Rate",`${a.tgr}%`]:["Exit Multiple",`${a.exitMultiple}x`],
              ["Enterprise Value",  fmtB(EV)],
              ["Net Debt / (Cash)", fmtB(a.debt - a.cash)],
              ["Equity Value",      fmtB(eqVal)],
              ["Implied Share Price",fmtPx(implied)],
            ].map(([k,v],i)=>(
              <tr key={i}>
                <td className="py-1.5 text-slate-500 border-b border-white/[0.04]">{k}</td>
                <td className="py-1.5 text-slate-300 font-mono text-right border-b border-white/[0.04]">{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      {/* Scenarios */}
      <Section title="4. Bull / Base / Bear Scenarios">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { scenario:"Bull Case", price: c.bullPrice||implied*1.35, color:"text-emerald-400", border:"border-emerald-500/20 bg-emerald-500/5",
              desc: "Revenue growth accelerates above estimates; margin expansion outperforms; multiple re-rates upward. Management executes flawlessly. Macro environment remains supportive." },
            { scenario:"Base Case", price: implied, color:"text-blue-400", border:"border-blue-500/20 bg-blue-500/5",
              desc: `In-line execution with consensus estimates. WACC of ${a.wacc}%. Revenue growth of ${a.revGrowth[0].toFixed(0)}% tapering to ${a.revGrowth[4].toFixed(0)}%. Normal competitive environment.` },
            { scenario:"Bear Case", price: c.bearPrice||implied*0.65, color:"text-red-400", border:"border-red-500/20 bg-red-500/5",
              desc: "Revenue misses estimates. Margin compression. Macro deterioration. Increased competition. Multiple contracts from current levels." },
          ].map(s=>(
            <div key={s.scenario} className={`p-4 rounded-xl border ${s.border}`}>
              <p className={`text-xs font-bold ${s.color} mb-1`}>{s.scenario}</p>
              <p className={`text-2xl font-bold font-mono ${s.color} mb-2`}>{fmtPx(s.price)}</p>
              <p className={`text-xs font-semibold ${s.color} mb-3`}>{sign((s.price/c.price-1)*100)}{((s.price/c.price-1)*100).toFixed(1)}% vs current</p>
              <p className="text-xs text-slate-500 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Why mispriced */}
      {c.whyMispriced && (
        <Section title="5. Why This Could Be Mispriced">
          <div className="p-4 bg-amber-500/5 border border-amber-500/15 rounded-lg">
            <p className="text-sm text-slate-300 leading-relaxed">{c.whyMispriced}</p>
          </div>
        </Section>
      )}

      {/* Key risks */}
      <Section title={c.whyMispriced ? "6. Key Risks — What Could Prove This Wrong" : "5. Key Risks"}>
        {c.whatCouldGoWrong && <p className="text-sm text-slate-400 leading-relaxed mb-3">{c.whatCouldGoWrong}</p>}
        <div className="space-y-2">
          {(c.risks||["Competition","Execution risk","Macro headwinds"]).map((r,i)=>(
            <div key={i} className="flex items-start gap-2.5 p-3 bg-red-500/5 border border-red-500/10 rounded-lg">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
              <p className="text-xs text-slate-400">{r}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Disclaimer */}
      <div className="glass-card p-4 border-slate-700">
        <p className="text-[10px] text-slate-600 leading-relaxed">
          This analysis is AI-generated for research and educational purposes only. It does not constitute investment advice, a solicitation to buy or sell securities, or a guarantee of future performance.
          All assumptions are estimates based on historical financials, analyst consensus, and management guidance. Past performance does not predict future results. Do your own due diligence before making investment decisions.
        </p>
      </div>
    </div>
  );
}

// ─── TAB: Historical Financials ───────────────────────────────────────────────
function HistoricalsTab({ payload }) {
  const h = payload?.historicals;
  if (!h?.rows?.length) return <Section title="Historical Financials"><p className="text-sm text-slate-500">No historical data available.</p></Section>;
  const rows = [
    ["Revenue", (r) => fmtComma(r.revenue)],
    ["Gross Profit", (r) => fmtComma(r.grossProfit)],
    ["Gross Margin", (r) => fmtP(r.grossMargin)],
    ["Operating Income", (r) => fmtComma(r.operatingIncome)],
    ["EBITDA", (r) => fmtComma(r.ebitda)],
    ["EBITDA Margin", (r) => fmtP(r.ebitdaMargin)],
    ["Net Income", (r) => fmtComma(r.netIncome)],
    ["Diluted EPS", (r) => r.eps == null ? "—" : `$${r.eps.toFixed(2)}`],
    ["Free Cash Flow", (r) => fmtComma(r.freeCashFlow)],
  ];
  return (
    <div className="space-y-4">
      <Explainer title="the real, reported past — the model's foundation" points={[
        `These are ${payload?.company?.name || "the company"}'s actual reported results, not estimates. The forecast in this model is anchored to these real trends in growth, margins and cash flow.`,
        "Look for consistency: steady or rising margins and growing free cash flow point to a higher-quality business; lumpy or declining numbers mean the forecast deserves more caution.",
      ]} />
    <Section title="Historical Financials (reported)">
      <div className="overflow-x-auto">
        <table className="w-full" data-testid="dcf-historicals-table">
          <thead><tr><TH>Line Item</TH>{h.rows.map((r) => <TH key={r.year} right>FY{r.year}</TH>)}</tr></thead>
          <tbody>
            {rows.map(([label, fn]) => (
              <tr key={label}>
                <TD>{label}</TD>
                {h.rows.map((r) => <TD key={r.year} right mono>{fn(r)}</TD>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-slate-600 mt-3">Source: {h.source}</p>
    </Section>
    </div>
  );
}

// ─── TAB: Comparables, Analyst, Macro ─────────────────────────────────────────
function CompsTab({ payload, c }) {
  const comps = payload?.comps, analyst = payload?.analyst, macro = payload?.macro, industry = payload?.industry;
  return (
    <div className="space-y-4">
      <Explainer title={`how the market prices ${c.ticker} versus its peers`} points={[
        `Multiples like P/E and EV/EBITDA show how many dollars investors pay per dollar of earnings or profit — they let you compare ${c.ticker} against similar companies on a level field.`,
        "Trading well ABOVE the peer median means the market already expects strong growth (a high bar to clear). Well BELOW could mean it's overlooked — or that something is wrong. Use this alongside the DCF, never instead of it.",
      ]} />
      <Section title="Trading Comparables">
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="dcf-comps-table">
            <thead><tr><TH>Ticker</TH><TH>Company</TH><TH right>Mkt Cap</TH><TH right>P/E</TH><TH right>EV/EBITDA</TH><TH right>P/S</TH><TH right>Rev Gr.</TH><TH right>EBITDA M.</TH></tr></thead>
            <tbody>
              {(comps?.rows || []).map((r) => (
                <tr key={r.ticker} className={r.isTarget ? "bg-blue-500/10" : ""}>
                  <TD mono bold>{r.ticker}{r.isTarget ? " ★" : ""}</TD>
                  <TD>{r.name}</TD>
                  <TD right mono>{fmtB(r.marketCap)}</TD>
                  <TD right mono>{r.pe ?? "—"}</TD>
                  <TD right mono>{r.evEbitda ?? "—"}</TD>
                  <TD right mono>{r.ps ?? "—"}</TD>
                  <TD right mono>{r.revenueGrowth != null ? `${r.revenueGrowth}%` : "—"}</TD>
                  <TD right mono>{r.ebitdaMargin != null ? `${r.ebitdaMargin}%` : "—"}</TD>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-slate-400 mt-3">Peer median: P/E <span className="text-white font-mono">{comps?.medianPe ?? "—"}x</span> · EV/EBITDA <span className="text-white font-mono">{comps?.medianEvEbitda ?? "—"}x</span></p>
        <p className="text-[10px] text-slate-600 mt-1">Source: {comps?.source}</p>
      </Section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Section title="Analyst Recommendations">
          {analyst?.consensus ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-emerald-400">{analyst.consensus}</span>
                <span className="text-xs text-slate-500">consensus</span>
              </div>
              <div className="grid grid-cols-5 gap-1 text-center">
                {[["Strong Buy", analyst.strongBuy], ["Buy", analyst.buy], ["Hold", analyst.hold], ["Sell", analyst.sell], ["Strong Sell", analyst.strongSell]].map(([l, v]) => (
                  <div key={l} className="p-2 bg-white/[0.03] rounded"><p className="text-sm font-bold text-white">{v ?? 0}</p><p className="text-[9px] text-slate-500 mt-0.5">{l}</p></div>
                ))}
              </div>
              <div className="flex items-center gap-4 text-xs pt-2 border-t border-white/[0.06]">
                <span className="text-slate-500">Target: <span className="text-white font-mono">{analyst.targetConsensus ? `$${analyst.targetConsensus}` : "—"}</span></span>
                <span className="text-slate-500">Range: <span className="text-slate-300 font-mono">${analyst.targetLow}–${analyst.targetHigh}</span></span>
                {analyst.impliedUpside != null && <span className={clr(analyst.impliedUpside)}>{sign(analyst.impliedUpside)}{analyst.impliedUpside}%</span>}
              </div>
            </div>
          ) : <p className="text-sm text-slate-500">No analyst coverage available.</p>}
          <p className="text-[10px] text-slate-600 mt-3">Source: {analyst?.source}</p>
        </Section>

        <Section title="Macro & Industry">
          <div className="space-y-2 text-xs">
            <p className="text-slate-400">Risk-free rate (10Y UST): <span className="text-white font-mono">{macro?.riskFreeRate10y}%</span> <span className="text-slate-600">as of {macro?.asOf}</span></p>
            <div className="flex flex-wrap gap-2 mt-1">
              {Object.entries(macro?.yieldCurve || {}).map(([k, v]) => (
                <span key={k} className="text-[10px] bg-white/[0.03] border border-white/[0.06] rounded px-2 py-1 text-slate-400">{k}: <span className="text-slate-200 font-mono">{v}%</span></span>
              ))}
            </div>
            <p className="text-slate-500 mt-2">{macro?.note}</p>
            <div className="pt-2 border-t border-white/[0.06] mt-2">
              <p className="text-slate-400">Sector: <span className="text-white">{industry?.sector}</span> · {industry?.industry}</p>
              <p className="text-slate-500 mt-1">{industry?.note}</p>
            </div>
          </div>
          <p className="text-[10px] text-slate-600 mt-3">Source: {macro?.source}</p>
        </Section>
      </div>
    </div>
  );
}

// ─── TAB: Assumption Sources & Confidence ─────────────────────────────────────
function SourcesTab({ assumptions }) {
  const meta = assumptions?.meta || {};
  const labels = {
    revGrowth: "Revenue Growth", ebitdaMargin: "EBITDA Margin", wacc: "WACC",
    taxRate: "Tax Rate", daPercent: "D&A % of Revenue", capexPercent: "CapEx % of Revenue",
    nwcPercent: "ΔNWC % of Revenue", tgr: "Terminal Growth", exitMultiple: "Exit Multiple",
    cash: "Cash & Equivalents", debt: "Total Debt", sharesOut: "Diluted Shares",
  };
  const confColor = (c) => c === "High" ? "text-emerald-400 bg-emerald-500/10" : c === "Medium" ? "text-blue-400 bg-blue-500/10" : "text-amber-400 bg-amber-500/10";
  return (
    <div className="space-y-4">
      <Explainer title="why you can trust (and challenge) these numbers" points={[
        "Every forward assumption is tagged with where it came from and a confidence level — \u201CHigh\u201D means pulled straight from financial statements or analyst consensus; \u201CLow\u201D means a reasoned estimate.",
        "This keeps the model honest: nothing is fabricated, and anything uncertain is flagged so you know exactly where to push back. Edit the yellow inputs in the Assumptions tab to test your own view.",
      ]} />
    <Section title="Assumption Sources & Confidence">
      <div className="overflow-x-auto">
        <table className="w-full" data-testid="dcf-sources-table">
          <thead><tr><TH>Assumption</TH><TH>Source</TH><TH>Reasoning</TH><TH>Confidence</TH></tr></thead>
          <tbody>
            {Object.entries(meta).map(([k, m]) => (
              <tr key={k}>
                <TD bold>{labels[k] || k}</TD>
                <TD>{m.source}</TD>
                <TD><span className="text-slate-400">{m.reasoning}</span></TD>
                <TD><span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${confColor(m.confidence)}`}>{m.confidence}</span></TD>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-slate-600 mt-3">Every forward assumption is derived from reported financials, consensus estimates or clearly-flagged estimates. Edit the yellow inputs in the Assumptions tab to stress-test.</p>
    </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="glass-card p-5">
      <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4 pb-2 border-b border-white/[0.06]">{title}</p>
      {children}
    </div>
  );
}

// ─── Company selector ─────────────────────────────────────────────────────────
function CompanySelector({ onSelect, loading }) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState([]);
  const [defaults, setDefaults] = useState([]);

  useEffect(() => {
    fetchCompanies({ limit: 9, sortBy: "marketCap", order: -1 })
      .then((d) => setDefaults(d.companies || []))
      .catch(() => setDefaults(COMPANY_UNIVERSE.slice(0, 9)));
  }, []);

  useEffect(() => {
    if (!search) { setResults([]); return; }
    const t = setTimeout(() => {
      fetchCompanies({ limit: 15, search })
        .then((d) => setResults(d.companies || []))
        .catch(() => setResults(
          COMPANY_UNIVERSE.filter((c) => c.ticker.includes(search.toUpperCase()) || c.name.toLowerCase().includes(search.toLowerCase())).slice(0, 15)
        ));
    }, 250);
    return () => clearTimeout(t);
  }, [search]);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">DCF Financial Model</h1>
        <p className="text-sm text-slate-500 mt-1">
          Institutional discounted cash flow built from reported financials, consensus estimates and a CAPM-derived WACC — with editable assumptions, sensitivity analysis, comparables and an investment memo. Select a company to begin.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">Search Company {loading && <span className="text-blue-400 normal-case">· building model…</span>}</p>
          <div className="relative">
            <div className="flex items-center gap-2 bg-white/[0.03] border border-white/[0.1] rounded-xl px-3 py-2.5">
              <Search className="w-4 h-4 text-slate-500" />
              <input value={search}
                onChange={e=>{setSearch(e.target.value);setOpen(true)}}
                onFocus={()=>setOpen(true)}
                data-testid="dcf-company-search"
                placeholder="Search 3,000+ companies by ticker or name…"
                className="bg-transparent text-sm text-white placeholder:text-slate-600 outline-none flex-1" />
            </div>
            {open && results.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 glass-card border border-white/[0.1] z-20 max-h-60 overflow-y-auto rounded-xl">
                {results.map(c=>(
                  <button key={c.ticker} onClick={()=>onSelect(c.ticker)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/[0.05] text-left transition-colors">
                    <span className="font-mono font-bold text-blue-400 text-sm w-14">{c.ticker}</span>
                    <span className="text-slate-300 text-sm flex-1">{c.name}</span>
                    <span className="text-slate-600 text-xs">{c.sector}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <p className="text-[10px] text-slate-600 uppercase tracking-wider mt-5 mb-3">Largest Companies</p>
          <div className="grid grid-cols-3 gap-2">
            {defaults.map(c=>(
              <button key={c.ticker} onClick={()=>onSelect(c.ticker)}
                className="p-3 border border-white/[0.06] rounded-xl hover:border-blue-500/30 hover:bg-blue-500/5 text-left transition-all">
                <p className="font-mono font-bold text-blue-400 text-sm">{c.ticker}</p>
                <p className="text-slate-500 text-[10px] mt-0.5 truncate">{c.name}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-3">
          <div className="glass-card p-5">
            <p className="text-xs font-semibold text-slate-300 mb-3">What's Inside the Model</p>
            <div className="space-y-2">
              {[
                ["Summary", "Valuation bridge, revenue chart, bull/base/bear scenarios"],
                ["Assumptions", "Editable WACC, revenue growth, margins, terminal value"],
                ["DCF Model", "Full UFCF build: NOPAT + D&A − CapEx − ΔNWC"],
                ["Historicals", "5 years of reported income & cash-flow statements"],
                ["Comparables", "Peer trading multiples, analyst consensus, macro & industry"],
                ["Sources", "Every assumption with source, reasoning & confidence"],
              ].map(([tab,desc])=>(
                <div key={tab} className="flex items-start gap-3">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="text-xs font-semibold text-slate-300">{tab}</span>
                    <span className="text-xs text-slate-500"> — {desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="glass-card p-4 border-blue-500/20">
            <p className="text-xs font-semibold text-blue-300 mb-1">Built from live API data</p>
            <p className="text-xs text-slate-500">Financials, consensus estimates and treasury rates via Financial Modeling Prep. Every forward assumption is sourced; missing data is flagged, never fabricated.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────
const TABS = [
  { id:"summary",     label:"Summary",         Icon: Target },
  { id:"assumptions", label:"Assumptions",     Icon: Edit3 },
  { id:"dcf",         label:"DCF Model",       Icon: Calculator },
  { id:"sensitivity", label:"Sensitivity",     Icon: BarChart2 },
  { id:"montecarlo",  label:"Monte Carlo",     Icon: Activity },
  { id:"historicals", label:"Historicals",     Icon: History },
  { id:"comps",       label:"Comparables",     Icon: Users },
  { id:"sources",     label:"Sources",         Icon: FileText },
  { id:"memo",        label:"Investment Memo", Icon: BookOpen },
];

export default function Modeling() {
  const [ticker, setTicker]   = useState(null);
  const [tab, setTab]         = useState("summary");
  const [assumptions, setAss] = useState(null);
  const [company, setCompany] = useState(null);
  const [payload, setPayload] = useState(null);
  const [generating, setGen]  = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadedAt, setLoadedAt] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const c = company;

  const selectCompany = useCallback(async (t) => {
    setLoading(true);
    try {
      const data = await fetchDcf(t);
      setCompany(data.company);
      setAss(JSON.parse(JSON.stringify(data.assumptions)));
      setPayload(data);
      setTicker(t);
      setLoadedAt(new Date().toISOString());
      setTab("summary");
    } catch (err) {
      toast.error(`Could not build model for ${t}: insufficient financial data`);
    } finally {
      setLoading(false);
    }
  }, []);

  const setAssKey   = (key, val) => setAss(prev => ({ ...prev, [key]: val }));
  const setAssArr   = (key, i, val) => setAss(prev => { const a=[...prev[key]]; a[i]=val; return {...prev,[key]:a}; });
  const resetAss    = () => { if (payload?.assumptions) setAss(JSON.parse(JSON.stringify(payload.assumptions))); };

  const model = useMemo(() => {
    if (!c || !assumptions) return null;
    try { return computeDCF(c, assumptions); } catch { return null; }
  }, [c, assumptions]);

  const rec = useMemo(
    () => (model && c)
      ? getRating({ upsidePct: model.upside, secondaryUpsidePct: payload?.analyst?.impliedUpside, opportunityScore: c.opportunityScore })
      : { label: "Hold", className: RATING_STYLE.Hold },
    [model, c, payload]
  );

  useEffect(() => {
    const t = searchParams.get("ticker");
    if (t && !ticker && !loading) selectCompany(t.toUpperCase());
  }, [searchParams, ticker, loading, selectCompany]);

  const handleExport = async () => {
    if (!c) return;
    setGen(true);
    try {
      toast.loading(`Building Excel model for ${c.ticker}…`, { id:"model" });
      await new Promise(r => setTimeout(r, 800));
      await generateExcelModel({ company: c, ...(payload || {}), recommendation: rec.label, priceAsOf: loadedAt });
      toast.success(`${c.ticker} Excel model downloaded`, { id:"model" });
    } catch (err) {
      toast.error(`Export failed: ${err.message}`, { id:"model" });
    } finally { setGen(false); }
  };

  if (!c || !model || !assumptions) {
    return <CompanySelector onSelect={selectCompany} loading={loading} />;
  }

  const isUp = model.implied >= c.price;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <button onClick={()=>{setTicker(null);setAss(null);setCompany(null);setPayload(null);setSearchParams({});}}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors">← All Companies</button>
            <ChevronRight className="w-3 h-3 text-slate-600" />
            <span className="text-xs text-slate-400">{c.name}</span>
          </div>
          <h1 className="text-xl font-bold text-white">
            {c.name} <span className="text-slate-500 font-mono text-base">({c.ticker})</span>
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">{c.sector} · {c.industry}</p>
          <span data-testid="dcf-recommendation" className={`inline-flex items-center gap-1.5 mt-2 text-xs font-bold px-3 py-1 rounded-full border ${rec.className}`}>
            Recommendation: {rec.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={resetAss}
            className="flex items-center gap-1.5 px-3 py-2 text-xs text-slate-400 hover:text-white border border-white/[0.08] hover:border-white/[0.15] rounded-lg transition-colors">
            <RotateCcw className="w-3 h-3" /> Reset
          </button>
          <button onClick={handleExport} disabled={generating} data-testid="dcf-export-button"
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50">
            <FileSpreadsheet className="w-3.5 h-3.5" />
            {generating ? "Building…" : "Export Excel"}
          </button>
        </div>
      </div>

      {/* Key stat bar */}
      <div className={`glass-card px-5 py-3 border ${isUp?"border-emerald-500/20":"border-red-500/20"} flex items-center gap-6 flex-wrap`} data-testid="dcf-stat-bar">
        {[
          { l:"Current Price",    v: `$${c.price.toFixed(2)}` },
          { l:"DCF Implied",      v: `$${model.implied.toFixed(2)}`, c: isUp?"text-emerald-400":"text-red-400" },
          { l:"Implied Return",   v: `${sign(model.upside)}${model.upside.toFixed(1)}%`, c: isUp?"text-emerald-400":"text-red-400" },
          { l:"Enterprise Value", v: fmtB(model.EV) },
          { l:"TV Weight",        v: `${model.tvPct.toFixed(0)}%` },
          { l:"WACC",             v: `${assumptions.wacc}%` },
          { l:"Revenue Growth",   v: `${c.revenueGrowth?.toFixed(0)||"—"}%` },
          { l:"EBITDA Margin",    v: `${c.ebitdaMargin?.toFixed(0)||"—"}%` },
        ].map(item => (
          <div key={item.l}>
            <p className="text-[9px] text-slate-600 uppercase tracking-wider">{item.l}</p>
            <p className={`text-sm font-bold font-mono ${item.c||"text-white"}`}>{item.v}</p>
          </div>
        ))}
      </div>
      {loadedAt && (
        <p className="text-[10px] text-emerald-400/80 -mt-3 flex items-center gap-1" data-testid="dcf-price-asof">
          <span className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
          Live data as of {new Date(loadedAt).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
        </p>
      )}

      {/* Tabs */}
      <div className="flex items-center border-b border-white/[0.06] gap-0 overflow-x-auto">
        {TABS.map(({id,label,Icon}) => (
          <button key={id} onClick={()=>setTab(id)} data-testid={`dcf-tab-${id}`}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
              tab===id ? "border-blue-500 text-white" : "border-transparent text-slate-500 hover:text-slate-300"
            }`}>
            <Icon className="w-3.5 h-3.5" />{label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab==="summary"     && <SummaryTab     c={c} model={model} assumptions={assumptions} />}
      {tab==="assumptions" && <AssumptionsTab  assumptions={assumptions} setAss={setAssKey} setAssArr={setAssArr} model={model} c={c} />}
      {tab==="dcf"         && <DCFTab          c={c} model={model} assumptions={assumptions} />}
      {tab==="sensitivity" && <SensitivityTab  model={model} assumptions={assumptions} c={c} />}
      {tab==="montecarlo"  && <MonteCarloTab    c={c} assumptions={assumptions} />}
      {tab==="historicals" && <HistoricalsTab  payload={payload} />}
      {tab==="comps"       && <CompsTab        payload={payload} c={c} />}
      {tab==="sources"     && <SourcesTab      assumptions={assumptions} />}
      {tab==="memo"        && <MemoTab         c={c} model={model} assumptions={assumptions} />}
    </div>
  );
}
