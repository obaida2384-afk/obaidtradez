import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FUTURE_GIANTS } from "@/lib/mockData";
import { fetchFutureGiants, fetchCoverage } from "@/lib/companyUniverse";
import { Telescope, TrendingUp, AlertTriangle, ArrowUpRight, ChevronDown, ChevronUp } from "lucide-react";

const fmtM = (n) => {
  if (!n) return "N/A";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}T`;
  if (n >= 1000) return `$${(n / 1000).toFixed(1)}B`;
  return `$${n}M`;
};

function GiantCard({ g }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  const scoreClass = g.opportunityScore >= 80 ? "score-high" : g.opportunityScore >= 65 ? "score-mid" : "score-low";

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-6">
        <div className="flex items-start gap-4">
          <div className={`score-ring ${scoreClass} shrink-0 text-base font-bold`}>{g.opportunityScore}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono font-bold text-blue-400">{g.ticker}</span>
                  <span className="text-[11px] text-slate-500">{g.sector}</span>
                  {g.shariah === "Compliant" && (
                    <span className="text-[9px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-1.5 py-0.5">Halal</span>
                  )}
                </div>
                <h3 className="text-xl font-bold text-white">{g.name}</h3>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-emerald-400">{g.upside}</div>
                <p className="text-xs text-slate-500 mt-0.5">potential over {g.timeframe}</p>
              </div>
            </div>

            <div className="flex items-center gap-4 mt-2 flex-wrap text-xs text-slate-500">
              <span>Rev Growth: <span className="text-emerald-400 font-mono">+{g.revenueGrowth}%</span></span>
              <span>Mkt Cap: <span className="text-slate-300">{fmtM(g.marketCap)}</span></span>
              <span>Price: <span className="text-slate-300 font-mono">${g.price}</span></span>
            </div>
          </div>
        </div>

        {/* TAM */}
        <div className="mt-4 flex items-center gap-2">
          <span className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider">TAM:</span>
          <span className="text-sm text-slate-300">{g.tam}</span>
        </div>

        {/* Thesis */}
        <p className="text-sm text-slate-400 leading-relaxed mt-3">{g.thesis}</p>

        {/* Why it could become much larger */}
        {g.whyLarger && (
          <div className="mt-3 p-3 bg-violet-500/[0.06] rounded-lg border border-violet-500/15">
            <p className="text-[10px] font-semibold text-violet-400 uppercase tracking-wider mb-1">Why It Could Become Much Larger</p>
            <p className="text-xs text-slate-400 leading-relaxed">{g.whyLarger}</p>
          </div>
        )}

        {/* Moat */}
        <div className="mt-3 p-3 bg-white/[0.03] rounded-lg border border-white/[0.04]">
          <p className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider mb-1">Competitive Moat</p>
          <p className="text-xs text-slate-400 leading-relaxed">{g.moat}</p>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-3 gap-2 mt-3">
          {Object.entries(g.keyMetrics).map(([k, v]) => (
            <div key={k} className="text-center p-2 bg-white/[0.03] rounded-lg">
              <p className="text-xs font-bold text-white font-mono">{v}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">{k}</p>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3 mt-4">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {expanded ? "Hide risks" : "View risks"}
          </button>
          <button
            onClick={() => navigate(`/research?ticker=${g.ticker}`)}
            className="ml-auto flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300"
          >
            Full research <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-white/[0.04] p-5 bg-white/[0.01] animate-fade-in">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <p className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Risks That Could Prevent This Outcome</p>
          </div>
          <ul className="space-y-2">
            {g.risks.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                <span className="text-red-400 shrink-0 mt-0.5">•</span> {r}
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-slate-700 mt-4">
            Multi-year return projections are speculative and based on fundamental analysis. Actual results may differ materially.
            This is not investment advice.
          </p>
        </div>
      )}
    </div>
  );
}

export default function FutureGiants() {
  const [giants, setGiants] = useState([]);
  const [isLive, setIsLive] = useState(false);
  const [coverage, setCoverage] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [cov, res] = await Promise.all([
          fetchCoverage().catch(() => null),
          fetchFutureGiants({ limit: 12 }),
        ]);
        setCoverage(cov);
        if (res.companies && res.companies.length > 0) {
          setGiants(res.companies);
          setIsLive(true);
        } else {
          setGiants(FUTURE_GIANTS);
          setIsLive(false);
        }
      } catch (e) {
        setGiants(FUTURE_GIANTS);
        setIsLive(false);
      }
    })();
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Telescope className="w-5 h-5 text-violet-400" />
          <h1 className="text-2xl font-bold text-white">Future Giants</h1>
        </div>
        <p className="text-sm text-slate-500">
          Companies with the potential to become 2x, 5x, or 10x investments over the next several years.
          AI identifies disruptive businesses with expanding TAM, strong balance sheets, and scalable economics.
        </p>
      </div>

      {/* Disclaimer */}
      <div className="glass-card p-4 border-amber-500/20 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-xs text-slate-500 leading-relaxed">
          <span className="text-amber-400 font-semibold">Long-term research only.</span>{" "}
          Multi-year projections are inherently speculative. A company that appears to be a "future giant" today
          may face disruption, execution failure, or macro headwinds. These companies require conviction, patience,
          and a long investment horizon. Never invest money you cannot afford to leave invested for 5+ years.
          AlphaVault does not guarantee returns.
        </p>
      </div>

      {/* Selection criteria */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-violet-400" /> Selection Criteria
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[
            "Large and expanding total addressable market",
            "Durable competitive moat (data, network effects, switching costs)",
            "Management with proven execution track record",
            "Scalable economics — improving unit economics at scale",
            "Strong balance sheet with adequate runway",
            "Revenue growth 20%+ with path to profitability",
          ].map((c, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-slate-500">
              <span className="text-violet-400 shrink-0 mt-0.5">✓</span> {c}
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-6" data-testid="future-giants-list">
        {giants.map((g) => <GiantCard key={g.ticker} g={g} />)}
      </div>

      <p className="text-xs text-slate-700 pb-4" data-testid="future-giants-data-note">
        {isLive
          ? `Live screen via Financial Modeling Prep${coverage?.count ? ` across ${coverage.count.toLocaleString()} companies` : ""} — secular-growth companies with runway to compound. Multi-year projections are speculative; not investment advice and returns are not guaranteed.`
          : "Future Giants uses simulated/demo data. Connect AI APIs for real-time fundamental screening and AI-generated thesis across thousands of companies."}
      </p>
    </div>
  );
}
