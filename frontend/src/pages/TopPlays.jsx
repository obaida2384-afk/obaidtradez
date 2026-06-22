import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { TOP_PLAYS, COMPANY_UNIVERSE } from "@/lib/mockData";
import { fetchShortTermGrowth, fetchCoverage } from "@/lib/companyUniverse";
import { TrendingUp, AlertTriangle, ArrowUpRight, ArrowDownRight, ChevronDown, ChevronUp, Info } from "lucide-react";

const fmt = (n, d = 1) => Number(n).toFixed(d);
const fmtM = (n) => {
  if (!n) return "N/A";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}T`;
  if (n >= 1000) return `$${(n / 1000).toFixed(1)}B`;
  return `$${n}M`;
};
const pctOf = (target, price) =>
  target != null && price ? (((target - price) / price) * 100).toFixed(1) : null;
const isPositiveRating = (r) => r && (String(r).includes("Buy") || r === "Overweight");

// Demo fallback used only when the live ranking is empty.
const DEMO_PLAYS = TOP_PLAYS.map((p) => {
  const c = COMPANY_UNIVERSE.find((co) => co.ticker === p.ticker) || {};
  return { ...c, ...p };
});

function PlayCard({ play, rank }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  const bullPct = pctOf(play.bullCase?.price, play.price);
  const basePct = pctOf(play.baseCase?.price, play.price);
  const bearPct = pctOf(play.bearCase?.price, play.price);

  const scoreClass = play.opportunityScore >= 80 ? "score-high" : play.opportunityScore >= 65 ? "score-mid" : "score-low";
  const whyText = play.whyMarketMayBeWrong || play.whyNow;

  return (
    <div className="glass-card overflow-hidden transition-all">
      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Rank */}
          <div className="w-8 h-8 rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-xs font-bold text-slate-500 shrink-0">
            {rank}
          </div>

          {/* Score + info */}
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className={`score-ring ${scoreClass} shrink-0`}>{play.opportunityScore}</div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono font-bold text-blue-400">{play.ticker}</span>
                <span className="text-[10px] text-slate-500">·</span>
                <span className="text-xs text-slate-400">{play.sector}</span>
                {play.shariah === "Compliant" && (
                  <span className="text-[9px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-1.5 py-0.5">Halal</span>
                )}
              </div>
              <p className="text-base font-bold text-white mt-0.5">{play.name}</p>
              <p className="text-sm text-slate-500 mt-0.5">Current: <span className="font-mono text-white">${play.price}</span> · Mkt Cap: {fmtM(play.marketCap)}</p>
            </div>
            <div className="text-right shrink-0">
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                isPositiveRating(play.analystRating)
                  ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                  : "text-slate-400 bg-slate-500/10 border-slate-500/20"
              }`}>
                {play.analystRating || "Not rated"}
              </span>
              <p className="text-xs text-slate-500 mt-1">PT: {play.avgPt ? `$${play.avgPt}` : "—"}</p>
            </div>
          </div>
        </div>

        {/* Why the market may be wrong */}
        <div className="mt-4 p-3 bg-white/[0.03] rounded-lg border border-white/[0.04]">
          <p className="text-[11px] font-semibold text-violet-400 uppercase tracking-wider mb-1">Why The Market May Be Wrong</p>
          <p className="text-sm text-slate-400 leading-relaxed">{whyText}</p>
        </div>

        {/* Scenarios row */}
        <div className="grid grid-cols-3 gap-2 mt-3">
          <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/15 text-center">
            <p className="text-[10px] text-emerald-500 font-semibold uppercase mb-1">Bull</p>
            <p className="font-mono font-bold text-emerald-400 text-base">{play.bullCase?.price != null ? `$${play.bullCase.price}` : "—"}</p>
            <p className="text-[11px] text-emerald-400/70">{bullPct != null ? `+${bullPct}%` : ""}</p>
          </div>
          <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/15 text-center">
            <p className="text-[10px] text-blue-400 font-semibold uppercase mb-1">Base</p>
            <p className="font-mono font-bold text-blue-400 text-base">{play.baseCase?.price != null ? `$${play.baseCase.price}` : "—"}</p>
            <p className="text-[11px] text-blue-400/70">{basePct != null ? `${basePct > 0 ? "+" : ""}${basePct}%` : ""}</p>
          </div>
          <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/15 text-center">
            <p className="text-[10px] text-red-400 font-semibold uppercase mb-1">Bear</p>
            <p className="font-mono font-bold text-red-400 text-base">{play.bearCase?.price != null ? `$${play.bearCase.price}` : "—"}</p>
            <p className="text-[11px] text-red-400/70">{bearPct != null ? `${bearPct}%` : ""}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-4">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {expanded ? "Less detail" : "Full thesis"}
          </button>
          <button
            onClick={() => navigate(`/research?ticker=${play.ticker}`)}
            className="ml-auto flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            Full research <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Expanded */}
      {expanded && (
        <div className="border-t border-white/[0.04] p-5 bg-white/[0.01] space-y-4 animate-fade-in">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { label: "Bull Case Thesis", text: play.bullCase.thesis, color: "text-emerald-400" },
              { label: "Base Case Thesis", text: play.baseCase.thesis, color: "text-blue-400" },
              { label: "Bear Case Thesis", text: play.bearCase.thesis, color: "text-red-400" },
            ].map((s) => (
              <div key={s.label}>
                <p className={`text-[10px] font-semibold uppercase tracking-wider mb-2 ${s.color}`}>{s.label}</p>
                <p className="text-xs text-slate-400 leading-relaxed">{s.text}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider mb-2">Key Catalysts</p>
              {play.keyCatalysts?.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {play.keyCatalysts.map((cat) => (
                    <span key={cat} className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/15 rounded-full px-2 py-0.5">{cat}</span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 leading-relaxed">{play.upside}</p>
              )}
            </div>
            <div>
              <p className="text-[10px] font-semibold text-red-400 uppercase tracking-wider mb-2">Key Risks</p>
              {play.keyRisks?.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {play.keyRisks.map((r) => (
                    <span key={r} className="text-[10px] bg-red-500/10 text-red-400 border border-red-500/15 rounded-full px-2 py-0.5">{r}</span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 leading-relaxed">{play.downside}</p>
              )}
            </div>
          </div>
          {play.whatInvalidates && (
            <div>
              <p className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider mb-2">What Could Invalidate The Thesis</p>
              <p className="text-xs text-slate-400 leading-relaxed">{play.whatInvalidates}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TopPlays() {
  const [plays, setPlays] = useState([]);
  const [isLive, setIsLive] = useState(false);
  const [coverage, setCoverage] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [cov, res] = await Promise.all([
          fetchCoverage().catch(() => null),
          fetchShortTermGrowth({ limit: 25, maxMegacap: 5 }),
        ]);
        setCoverage(cov);
        if (res.companies && res.companies.length > 0) {
          setPlays(res.companies);
          setIsLive(true);
        } else {
          setPlays(DEMO_PLAYS);
          setIsLive(false);
        }
      } catch (e) {
        setPlays(DEMO_PLAYS);
        setIsLive(false);
      }
    })();
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <h1 className="text-2xl font-bold text-white">Top Plays This Month</h1>
          </div>
          <p className="text-sm text-slate-500">
            {new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" })} · Updated weekly
          </p>
        </div>
        <div className="text-xs text-slate-500 bg-slate-800/60 border border-white/[0.06] rounded-lg px-3 py-2 max-w-sm">
          <span className="text-amber-400 font-semibold">Important:</span> This list identifies companies with asymmetric upside potential.
          It does not guarantee returns or promise price performance. All investing involves risk.
        </div>
      </div>

      {/* Disclaimer */}
      <div className="glass-card p-4 border-amber-500/20 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-amber-400">Educational Research Only</p>
          <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
            AlphaVault does not guarantee that any company on this list will increase in value.
            This analysis is for research and education purposes. Markets are uncertain and can move against any thesis.
            The AI identifies probability-weighted opportunities, not certainties. Always conduct your own due diligence.
          </p>
        </div>
      </div>

      {/* Methodology */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <Info className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-semibold text-white">How Plays Are Selected</h3>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            "Revenue acceleration vs. prior quarter",
            "Positive analyst estimate revisions",
            "Institutional buying patterns",
            "Valuation dislocation vs. peers",
            "Positive news catalysts (last 30d)",
            "Improving margin trajectory",
            "Macro environment alignment",
            "Technical momentum confirmation",
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-slate-500">
              <span className="text-emerald-400 shrink-0 mt-0.5">✓</span>
              {item}
            </div>
          ))}
        </div>
      </div>

      {/* Play cards */}
      <div className="space-y-4" data-testid="top-plays-list">
        {plays.map((play, i) => (
          <PlayCard key={play.ticker} play={play} rank={i + 1} />
        ))}
      </div>

      <p className="text-xs text-slate-700 pb-4" data-testid="top-plays-data-note">
        {isLive
          ? `Live ranking via Financial Modeling Prep${coverage?.count ? ` across ${coverage.count.toLocaleString()} companies` : ""}, emphasising asymmetric upside in mid/small caps. Educational research only — not a trading system and no trades are executed.`
          : "Top Plays uses simulated data in demo mode. Connect Financial Modeling Prep, Polygon.io, and an AI API for live screening and reasoning. This platform is not a trading system and does not execute trades."}
      </p>
    </div>
  );
}
