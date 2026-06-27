import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { TOP_PLAYS, COMPANY_UNIVERSE } from "@/lib/mockData";
import { fetchShortTermGrowth, fetchCoverage, fetchTrackedPlays } from "@/lib/companyUniverse";
import { useQuotes } from "@/hooks/useQuotes";
import { TrendingUp, AlertTriangle, ArrowUpRight, ArrowDownRight, ChevronDown, ChevronUp, Info, Activity, Target, ShieldAlert } from "lucide-react";

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
          {(play.insiderActivity || play.institutionalOwnershipTrend) && (
            <div className="flex flex-wrap items-center gap-2" data-testid="top-play-ownership">
              <p className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider w-full mb-0.5">Ownership & Insider Activity</p>
              {play.insiderActivity && (
                <span className={`text-[10px] rounded-full border px-2 py-0.5 ${
                  /buy/i.test(play.insiderActivity) ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/15"
                  : /sell/i.test(play.insiderActivity) ? "text-red-400 bg-red-500/10 border-red-500/15"
                  : "text-slate-400 bg-slate-500/10 border-slate-500/15"}`}>
                  Insider: {play.insiderActivity}
                </span>
              )}
              {play.institutionalOwnershipTrend && (
                <span className="text-[10px] text-slate-400 bg-white/[0.03] border border-white/[0.06] rounded-full px-2 py-0.5">
                  Institutional: {play.institutionalOwnershipTrend}
                </span>
              )}
            </div>
          )}
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

const convBadge = (c) =>
  c === "High" ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
  : c === "Medium" ? "text-blue-400 bg-blue-500/10 border-blue-500/20"
  : "text-slate-400 bg-slate-500/10 border-slate-500/20";
const reasonBadge = (r) =>
  r === "Target Hit" ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
  : r === "Thesis Broke" ? "text-red-400 bg-red-500/10 border-red-500/20"
  : "text-amber-400 bg-amber-500/10 border-amber-500/20";
const retClass = (v) => (v == null ? "text-slate-400" : v >= 0 ? "text-emerald-400" : "text-red-400");

function StatCard({ label, value, sub, tone }) {
  return (
    <div className="glass-card p-4" data-testid={`tracker-stat-${label.toLowerCase().replace(/[^a-z]/g, "-")}`}>
      <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-xl font-bold font-mono ${tone || "text-white"}`}>{value}</p>
      {sub && <p className="text-[10px] text-slate-600 mt-0.5">{sub}</p>}
    </div>
  );
}

function TrackedPicks() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchTrackedPlays()
      .then((d) => alive && setData(d))
      .catch(() => alive && setErr(true));
    return () => { alive = false; };
  }, []);

  if (err) return <div className="glass-card p-6 text-sm text-slate-400">Tracker not available yet — it populates on the daily refresh.</div>;
  if (!data) return <div className="glass-card p-6 text-sm text-slate-500 animate-pulse">Loading tracked picks…</div>;

  const { active = [], exited = [], stats = {}, sectorConcentration = [] } = data;
  const fmtRet = (v) => (v == null ? "—" : `${v >= 0 ? "+" : ""}${v}%`);
  const fmtPx = (v) => (v == null ? "—" : `$${Number(v).toFixed(2)}`);

  return (
    <div className="space-y-6">
      {/* Explainer */}
      <div className="glass-card p-4 border-blue-500/20 flex items-start gap-3">
        <Activity className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-blue-200">How tracking works</p>
          <p className="text-xs text-slate-400 mt-1 leading-relaxed">
            Every refresh we snapshot the Top Plays list. New names are tracked from their entry price; when a name
            leaves (after a 2-day buffer to avoid noise) we record why — <span className="text-emerald-400">Target Hit</span> (ran to its goal),
            <span className="text-red-400"> Thesis Broke</span> (fundamentals/price deteriorated), or <span className="text-amber-400">Out-ranked</span> (still fine, just beaten by better setups).
            Forward returns below tell you whether the picks actually worked.
          </p>
        </div>
      </div>

      {/* Performance stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <StatCard label="Closed Picks" value={stats.closedCount ?? 0} sub="exited & measured" />
        <StatCard label="Hit Rate" value={stats.hitRate != null ? `${stats.hitRate}%` : "—"} sub="% that gained" tone={stats.hitRate >= 50 ? "text-emerald-400" : stats.hitRate != null ? "text-amber-400" : "text-white"} />
        <StatCard label="Avg Return" value={fmtRet(stats.avgReturn)} sub="per closed pick" tone={retClass(stats.avgReturn)} />
        <StatCard label="Avg Winner" value={fmtRet(stats.avgWinner)} sub="winning picks" tone="text-emerald-400" />
        <StatCard label="Avg Loser" value={fmtRet(stats.avgLoser)} sub="losing picks" tone="text-red-400" />
      </div>

      {/* Sector concentration */}
      {sectorConcentration.length > 0 && (
        <div className="glass-card p-4" data-testid="sector-concentration">
          <div className="flex items-center gap-2 mb-3">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <p className="text-sm font-semibold text-white">Diversification check ({active.length} active)</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {sectorConcentration.map((s) => (
              <span key={s.sector} className={`text-[11px] rounded-full border px-2.5 py-1 ${s.concentrated ? "text-amber-400 bg-amber-500/10 border-amber-500/25" : "text-slate-400 bg-white/[0.03] border-white/[0.06]"}`}>
                {s.sector}: {s.count} ({s.pct}%){s.concentrated ? " ⚠ heavy" : ""}
              </span>
            ))}
          </div>
          <p className="text-[10px] text-slate-600 mt-2">A sector above 30% of your active picks is flagged — spread risk across sectors so one bad theme can't sink the book.</p>
        </div>
      )}

      {/* Active picks */}
      <div>
        <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Active Picks ({active.length})</p>
        <div className="space-y-2" data-testid="tracked-active-list">
          {active.length === 0 && <p className="text-sm text-slate-500">No active picks yet.</p>}
          {active.map((p) => (
            <div key={p.ticker} className="glass-card p-4 hover:bg-white/[0.02] transition-colors cursor-pointer" onClick={() => navigate(`/modeling?ticker=${p.ticker}`)}>
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-[10px] text-slate-600 w-6">#{p.entryRank}</span>
                <span className="font-mono font-bold text-blue-400 w-16">{p.ticker}</span>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${convBadge(p.conviction)}`}>{p.conviction} conviction</span>
                <span className="text-xs text-slate-500 hidden sm:inline">{p.sector}</span>
                <div className="ml-auto flex items-center gap-4 text-right">
                  <div>
                    <p className="text-[9px] text-slate-600 uppercase">Entry → Now</p>
                    <p className="text-xs font-mono text-slate-300">{fmtPx(p.entryPrice)} → {fmtPx(p.currentPrice)}</p>
                  </div>
                  <div className="w-16">
                    <p className="text-[9px] text-slate-600 uppercase">Return</p>
                    <p className={`text-sm font-bold font-mono ${retClass(p.returnPct)}`}>{fmtRet(p.returnPct)}</p>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 pl-6 text-[10px] text-slate-500">
                <span>Held {p.holdDays}d</span>
                <span>·</span>
                <span title="Suggested position size, scaled down for higher risk">Size <span className="text-slate-300">{p.suggestedWeightPct}%</span></span>
                <span title="Suggested stop-loss, wider for higher volatility">Stop <span className="text-red-300">-{p.suggestedStopPct}%</span></span>
                {p.rewardRiskRatio != null && <span title="Reward (to analyst target) ÷ stop-loss risk">R/R <span className={p.rewardRiskRatio >= 2 ? "text-emerald-400" : "text-slate-300"}>{p.rewardRiskRatio}:1</span></span>}
                {p.analystTarget && <span>PT ${p.analystTarget}</span>}
                {p.convictionReasons?.length > 0 && <span className="hidden md:inline text-slate-600">· {p.convictionReasons.join(" · ")}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Exited picks */}
      <div>
        <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">Recently Exited ({exited.length})</p>
        <div className="space-y-2" data-testid="tracked-exited-list">
          {exited.length === 0 && <p className="text-sm text-slate-500">No exits yet — names appear here once they leave the list.</p>}
          {exited.map((p) => (
            <div key={`${p.ticker}-${p.exitDate}`} className="glass-card p-3 flex items-center gap-3 flex-wrap opacity-90">
              <span className="font-mono font-bold text-slate-300 w-16">{p.ticker}</span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${reasonBadge(p.exitReason)}`}>{p.exitReason}</span>
              <span className="text-xs font-mono text-slate-500">{fmtPx(p.entryPrice)} → {fmtPx(p.exitPrice)}</span>
              <span className="text-[10px] text-slate-600">held {p.holdDays}d</span>
              <span className={`ml-auto text-sm font-bold font-mono ${retClass(p.exitReturnPct)}`}>{fmtRet(p.exitReturnPct)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function TopPlays() {
  const [tab, setTab] = useState("current");
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

  const { prices: quotes } = useQuotes(plays.map((p) => p.ticker));

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <h1 className="text-2xl font-bold text-white">Top Plays This Month</h1>
          </div>
          <p className="text-sm text-slate-500">
            {new Date().toLocaleDateString("en-US", { month: "long", year: "numeric" })} · Refreshed daily
          </p>
        </div>
        <div className="text-xs text-slate-500 bg-slate-800/60 border border-white/[0.06] rounded-lg px-3 py-2 max-w-sm">
          <span className="text-amber-400 font-semibold">Important:</span> This list identifies companies with asymmetric upside potential.
          It does not guarantee returns or promise price performance. All investing involves risk.
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-white/[0.06]">
        {[
          { id: "current", label: "Current Picks", Icon: TrendingUp },
          { id: "tracked", label: "Tracked Picks & Performance", Icon: Target },
        ].map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            data-testid={`top-plays-tab-${id}`}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === id ? "border-emerald-400 text-white" : "border-transparent text-slate-500 hover:text-slate-300"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "tracked" ? <TrackedPicks /> : (
      <>
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
        {plays.map((play, i) => {
          const lp = quotes[play.ticker]?.price;
          return <PlayCard key={play.ticker} play={lp != null ? { ...play, price: lp } : play} rank={i + 1} />;
        })}
      </div>

      <p className="text-xs text-slate-700 pb-4" data-testid="top-plays-data-note">
        {isLive
          ? `Live ranking via Financial Modeling Prep${coverage?.count ? ` across ${coverage.count.toLocaleString()} companies` : ""}, emphasising asymmetric upside in mid/small caps. Educational research only — not a trading system and no trades are executed.`
          : "Top Plays uses simulated data in demo mode. Connect Financial Modeling Prep, Polygon.io, and an AI API for live screening and reasoning. This platform is not a trading system and does not execute trades."}
      </p>
      </>
      )}
    </div>
  );
}
