import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { DISCOVERY_RESULTS, COMPANY_UNIVERSE } from "@/lib/mockData";
import { fetchCompanies, fetchCoverage } from "@/lib/companyUniverse";
import { Sparkles, TrendingUp, Filter, ArrowUpRight, Brain, Zap } from "lucide-react";

const fmt = (n, d = 1) => (n == null ? "—" : Number(n).toFixed(d));
const fmtM = (n) => {
  if (!n) return "N/A";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}T`;
  if (n >= 1000) return `$${(n / 1000).toFixed(1)}B`;
  return `$${n}M`;
};

// Demo fallback used only when the live universe is empty (no API key / not yet built).
const DEMO_OPPORTUNITIES = [
  ...DISCOVERY_RESULTS,
  ...COMPANY_UNIVERSE.filter((c) => c.opportunityScore >= 70 && !DISCOVERY_RESULTS.find((d) => d.ticker === c.ticker))
    .map((c) => ({
      ticker: c.ticker,
      name: c.name,
      sector: c.sector,
      opportunityScore: c.opportunityScore,
      marketCap: c.marketCap,
      price: c.price,
      revenueGrowth: c.revenueGrowth,
      grossMargin: c.grossMargin,
      analystRating: c.analystRating,
      avgPt: c.avgPt,
      dcfUpside: c.dcfUpside,
      thesis: c.description,
      catalysts: c.risks ? [] : [],
      shariah: c.shariah,
    })),
].sort((a, b) => b.opportunityScore - a.opportunityScore);

const SHARIAH_OPTIONS = ["All", "Compliant", "Non-Compliant", "Questionable"];

function OpportunityCard({ d, onClick }) {
  const scoreClass = d.opportunityScore >= 80 ? "score-high" : d.opportunityScore >= 65 ? "score-mid" : "score-low";
  const up = d.dcfUpside >= 0;
  const revUp = d.revenueGrowth >= 15;

  return (
    <div
      onClick={onClick}
      className="glass-card p-5 hover:border-white/[0.1] cursor-pointer transition-all group animate-fade-in"
    >
      <div className="flex items-start gap-3 mb-3">
        <div className={`score-ring ${scoreClass} shrink-0 text-base font-bold`}>{d.opportunityScore}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono font-bold text-blue-400 text-sm">{d.ticker}</span>
            {d.shariah === "Compliant" && (
              <span className="text-[9px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-1.5 py-0.5">Halal</span>
            )}
          </div>
          <p className="text-sm font-semibold text-slate-200 truncate">{d.name}</p>
          <p className="text-[11px] text-slate-500">{d.sector}</p>
        </div>
        <div className="text-right shrink-0">
          <p className={`text-sm font-bold font-mono ${up ? "text-emerald-400" : "text-red-400"}`}>
            {up ? "+" : ""}{fmt(d.dcfUpside)}%
          </p>
          <p className="text-[10px] text-slate-600">DCF upside</p>
        </div>
      </div>

      <p className="text-xs text-slate-500 leading-relaxed line-clamp-3 mb-3">{d.thesis}</p>

      <div className="flex items-center gap-3 text-xs mb-3">
        <span className={`font-mono ${revUp ? "text-emerald-400" : "text-slate-400"}`}>
          Rev +{fmt(d.revenueGrowth)}%
        </span>
        {d.grossMargin && <span className="text-slate-500">GM {fmt(d.grossMargin)}%</span>}
        <span className={`${d.analystRating === "Overweight" ? "text-emerald-400" : "text-slate-400"}`}>
          {d.analystRating}
        </span>
        {d.avgPt && <span className="text-slate-500">PT ${d.avgPt}</span>}
      </div>

      {d.catalysts?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {d.catalysts.slice(0, 3).map((c) => (
            <span key={c} className="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/15 rounded-full px-2 py-0.5">{c}</span>
          ))}
        </div>
      )}

      {(d.insiderActivity || d.institutionalOwnershipTrend) && (
        <div className="flex flex-wrap items-center gap-2 mt-3 text-[10px]" data-testid="discovery-ownership">
          {d.insiderActivity && (
            <span className={`flex items-center gap-1 rounded-full border px-2 py-0.5 ${
              /buy/i.test(d.insiderActivity) ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/15"
              : /sell/i.test(d.insiderActivity) ? "text-red-400 bg-red-500/10 border-red-500/15"
              : "text-slate-400 bg-slate-500/10 border-slate-500/15"}`}>
              Insider: {d.insiderActivity}
            </span>
          )}
          {d.institutionalOwnershipTrend && (
            <span className="text-slate-400 bg-white/[0.03] border border-white/[0.06] rounded-full px-2 py-0.5">
              Inst: {d.institutionalOwnershipTrend}
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/[0.04]">
        <span className="text-[11px] text-slate-600">{fmtM(d.marketCap)}</span>
        <span className="flex items-center gap-1 text-[11px] text-emerald-400 group-hover:gap-2 transition-all">
          Research <ArrowUpRight className="w-3 h-3" />
        </span>
      </div>
    </div>
  );
}

export default function Discovery() {
  const navigate = useNavigate();
  const [sector, setSector] = useState("All");
  const [shariah, setShariah] = useState("All");
  const [minScore, setMinScore] = useState(0);
  const [scanning, setScanning] = useState(false);
  const [opportunities, setOpportunities] = useState([]);
  const [isLive, setIsLive] = useState(false);
  const [coverage, setCoverage] = useState(null);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);

  const load = useCallback(async () => {
    setScanning(true);
    try {
      const [cov, res] = await Promise.all([
        fetchCoverage().catch(() => null),
        fetchCompanies({ limit: 120, sortBy: "opportunityScore", order: -1 }),
      ]);
      setCoverage(cov);
      if (res.companies && res.companies.length > 0) {
        setOpportunities(res.companies);
        setIsLive(true);
      } else {
        setOpportunities(DEMO_OPPORTUNITIES);
        setIsLive(false);
      }
    } catch (e) {
      setOpportunities(DEMO_OPPORTUNITIES);
      setIsLive(false);
    } finally {
      setScanning(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 1) { setSearchResults(null); return; }
    let alive = true;
    const t = setTimeout(async () => {
      try {
        const res = await fetchCompanies({ search: term, limit: 60, sortBy: "opportunityScore", order: -1 });
        if (alive) setSearchResults(res.companies || []);
      } catch { if (alive) setSearchResults([]); }
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [query]);

  const SECTORS = ["All", ...Array.from(new Set(opportunities.map((c) => c.sector).filter(Boolean)))];

  const baseList = query.trim() && searchResults != null ? searchResults : opportunities;

  const filtered = baseList.filter((d) => {
    const matchSector = sector === "All" || d.sector === sector;
    const matchShariah = shariah === "All" || d.shariah === shariah;
    const matchScore = (d.opportunityScore || 0) >= minScore;
    return matchSector && matchShariah && matchScore;
  });

  const handleRescan = () => load();

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-5 h-5 text-violet-400" />
            <h1 className="text-2xl font-bold text-white">AI Discovery Engine</h1>
          </div>
          <p className="text-sm text-slate-500">
            Continuously scanning for companies with strong fundamentals, improving momentum, and attractive valuations — before the market notices.
          </p>
        </div>
        <button
          onClick={handleRescan}
          disabled={scanning}
          data-testid="discovery-rescan-button"
          className="flex items-center gap-2 bg-violet-500/10 hover:bg-violet-500/15 text-violet-400 border border-violet-500/20 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
        >
          {scanning ? (
            <><span className="w-3.5 h-3.5 border-2 border-violet-400/30 border-t-violet-400 rounded-full animate-spin" /> Scanning universe…</>
          ) : (
            <><Zap className="w-4 h-4" /> Re-scan Universe</>
          )}
        </button>
      </div>

      {/* Scoring methodology */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="w-4 h-4 text-violet-400" />
          <h3 className="text-sm font-semibold text-white">Opportunity Score Methodology (0–100)</h3>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          {[
            { label: "Fundamental Strength", weight: "20%" },
            { label: "Revenue Growth", weight: "15%" },
            { label: "Profitability", weight: "15%" },
            { label: "FCF Quality", weight: "10%" },
            { label: "Valuation", weight: "15%" },
            { label: "Analyst Sentiment", weight: "10%" },
            { label: "Macro Support", weight: "5%" },
            { label: "Catalyst Strength", weight: "10%" },
          ].map((item) => (
            <div key={item.label} className="text-center p-2 bg-white/[0.03] rounded-lg">
              <p className="text-sm font-bold text-violet-400">{item.weight}</p>
              <p className="text-[10px] text-slate-500 mt-0.5 leading-tight">{item.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Score legend */}
      <div className="flex items-center gap-4 flex-wrap">
        <span className="text-xs text-slate-600">Score legend:</span>
        <span className="flex items-center gap-1.5 text-xs"><span className="score-ring score-high w-6 h-6 text-[10px]">80+</span> <span className="text-emerald-400">High conviction</span></span>
        <span className="flex items-center gap-1.5 text-xs"><span className="score-ring score-mid w-6 h-6 text-[10px]">65+</span> <span className="text-blue-400">Moderate opportunity</span></span>
        <span className="flex items-center gap-1.5 text-xs"><span className="score-ring score-low w-6 h-6 text-[10px]">&lt;65</span> <span className="text-amber-400">Watch list</span></span>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <span className="text-xs text-slate-500">Filter:</span>
        </div>
        <div className="flex items-center gap-2 glass-card px-3 py-2 flex-1 min-w-[200px] max-w-sm">
          <Sparkles className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search all companies — ticker or name…"
            data-testid="discovery-search-input"
            className="bg-transparent text-sm text-slate-300 placeholder:text-slate-600 outline-none flex-1"
          />
        </div>
        <select value={sector} onChange={(e) => setSector(e.target.value)} data-testid="discovery-sector-filter" className="glass-card px-3 py-2 text-sm text-slate-300 outline-none">
          {SECTORS.map((s) => <option key={s} value={s} className="bg-slate-900">{s}</option>)}
        </select>
        <select value={shariah} onChange={(e) => setShariah(e.target.value)} className="glass-card px-3 py-2 text-sm text-slate-300 outline-none">
          {SHARIAH_OPTIONS.map((s) => <option key={s} value={s} className="bg-slate-900">{s}</option>)}
        </select>
        <div className="flex items-center gap-2 glass-card px-3 py-2">
          <span className="text-xs text-slate-500">Min score:</span>
          <select value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} className="bg-transparent text-sm text-slate-300 outline-none">
            <option value={0} className="bg-slate-900">Any</option>
            <option value={65} className="bg-slate-900">65+</option>
            <option value={75} className="bg-slate-900">75+</option>
            <option value={80} className="bg-slate-900">80+</option>
          </select>
        </div>
        <span className="text-xs text-slate-600">{filtered.length} opportunities</span>
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="discovery-opportunities-grid">
        {filtered.map((d) => (
          <OpportunityCard
            key={d.ticker}
            d={d}
            onClick={() => navigate(`/research?ticker=${d.ticker}`)}
          />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-20 text-slate-600">
          <Sparkles className="w-8 h-8 mx-auto mb-3 opacity-40" />
          <p>No opportunities match your filters</p>
          <button onClick={() => { setSector("All"); setShariah("All"); setMinScore(0); setQuery(""); }} className="text-sm text-emerald-400 mt-2 hover:text-emerald-300">
            Clear filters
          </button>
        </div>
      )}

      <p className="text-xs text-slate-700" data-testid="discovery-data-source-note">
        {isLive
          ? `Live data via Financial Modeling Prep${coverage?.count ? ` — screening ${coverage.count.toLocaleString()} companies` : ""}${coverage?.updated_at ? `, updated ${new Date(coverage.updated_at).toLocaleString()}` : ""}.`
          : "AI Discovery uses simulated data in demo mode. Connect Financial Modeling Prep and Polygon.io APIs for real-time screening across 5,000+ stocks."}
      </p>
    </div>
  );
}
