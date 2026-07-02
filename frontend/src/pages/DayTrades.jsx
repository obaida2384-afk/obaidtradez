import { useState, useEffect, useCallback } from "react";
import { fetchDayTrades, fetchDayTradesScoreboard } from "@/lib/companyUniverse";
import {
  Zap, RefreshCw, TrendingUp, Newspaper, Target, ShieldAlert, ChevronDown,
  ChevronUp, Activity, Clock, Trophy, AlertTriangle, BookOpen, ExternalLink,
} from "lucide-react";

const fmt = (n, d = 2) => (n == null ? "—" : Number(n).toFixed(d));
const fmtVol = (n) => {
  if (n == null) return "—";
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return String(n);
};

const OUTCOME_LABELS = {
  target1_hit: { label: "Target 1 hit (+2%)", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
  target2_hit: { label: "Target 2 hit (+3%)", cls: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
  stopped: { label: "Stopped out", cls: "text-red-400 bg-red-500/10 border-red-500/20" },
  ambiguous_stopped: { label: "Stopped (both touched)", cls: "text-red-400 bg-red-500/10 border-red-500/20" },
  closed_flat: { label: "Closed flat", cls: "text-slate-400 bg-slate-500/10 border-slate-500/20" },
};

function MorningRoutine() {
  const [open, setOpen] = useState(false);
  return (
    <div className="glass-card p-5" data-testid="day-trades-morning-routine">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between" data-testid="morning-routine-toggle">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-bold text-white">How to trade this tab — the daily routine</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
      </button>
      {open && (
        <div className="mt-4 space-y-3 text-sm text-slate-400 leading-relaxed">
          <div>
            <p className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider mb-1">1 · Pre-market (before 9:30 ET)</p>
            <p>Open this tab, hit Refresh. Read every catalyst headline. Pick your top 2–3 names — the ones with a fresh news catalyst, relative volume above 2x, and price above VWAP. Write down the entry, stop, and both targets for each before the bell.</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider mb-1">2 · The open (9:30–9:45 ET)</p>
            <p>Do nothing for the first 15 minutes. Let the opening range form. The biggest amateur mistake is buying the open — spreads are widest and reversals are most violent here.</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider mb-1">3 · Execution (9:45–11:30 ET)</p>
            <p>Enter only on your two triggers: a VWAP-hold pullback or an opening-range breakout on volume. Place the stop immediately. Risk a fixed amount per trade (e.g., 1% of account) — position size = risk ÷ (entry − stop).</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider mb-1">4 · Management until sell</p>
            <p>+2% → sell 50–75%, stop to breakeven. +3% → sell the rest or trail the 9-EMA on the 5-min chart. Stop hit → out, no exceptions, no averaging down. 15:45 ET → everything closes. The 2–3% daily goal comes from taking the base hit, not swinging for home runs.</p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider mb-1">5 · Midday (11:30–14:00 ET)</p>
            <p>Volume dries up and ranges chop. Manage what you hold; avoid fresh entries unless a name reclaims VWAP on a volume surge.</p>
          </div>
        </div>
      )}
    </div>
  );
}

function TradeCard({ c, rank }) {
  const [expanded, setExpanded] = useState(rank === 1);
  const t = c.technicals || {};
  const p = c.plan || {};
  const a = c.analyst || {};
  const cat = c.catalyst || {};
  const chgUp = (c.changePct || 0) >= 0;

  return (
    <div className="glass-card overflow-hidden" data-testid={`day-trade-card-${c.ticker}`}>
      <div className="p-5">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-xs font-bold text-slate-500 shrink-0">
            {rank}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono font-bold text-blue-400">{c.ticker}</span>
              <span className={`text-xs font-mono font-semibold ${chgUp ? "text-emerald-400" : "text-red-400"}`}>
                {chgUp ? "+" : ""}{fmt(c.changePct, 1)}%
              </span>
              <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${
                c.sourceList === "gainer"
                  ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                  : "text-cyan-400 bg-cyan-500/10 border-cyan-500/20"
              }`}>
                {c.sourceList === "gainer" ? "Top Gainer" : "Most Active"}
              </span>
            </div>
            <p className="text-sm font-bold text-white mt-0.5 truncate">{c.name}</p>
            <p className="text-xs text-slate-500 mt-0.5">
              ${fmt(c.price)} · Day range <span className="font-mono">${fmt(c.dayLow)}–${fmt(c.dayHigh)}</span> · Vol {fmtVol(c.volume)} ({t.relVolume != null ? `${t.relVolume}x avg` : "—"})
            </p>
          </div>
          <div className="text-right shrink-0">
            <div className={`score-ring ${c.score >= 70 ? "score-high" : c.score >= 50 ? "score-mid" : "score-low"}`}>{Math.round(c.score)}</div>
            <p className="text-[10px] text-slate-500 mt-1">setup score</p>
          </div>
        </div>

        {cat.headline && (
          <div className="mt-3 p-3 bg-white/[0.03] rounded-lg border border-white/[0.04]" data-testid={`catalyst-${c.ticker}`}>
            <div className="flex items-center gap-2 mb-1">
              <Newspaper className="w-3 h-3 text-violet-400" />
              <span className="text-[11px] font-semibold text-violet-400 uppercase tracking-wider">Catalyst {cat.isToday ? "· Today" : ""}</span>
              {cat.sentiment && (
                <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${
                  cat.sentiment === "Positive" ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
                  : cat.sentiment === "Negative" ? "text-red-400 bg-red-500/10 border-red-500/20"
                  : "text-slate-400 bg-slate-500/10 border-slate-500/20"
                }`}>{cat.sentiment}</span>
              )}
            </div>
            <a href={cat.url} target="_blank" rel="noreferrer" className="text-sm text-slate-300 hover:text-white leading-snug inline-flex items-start gap-1">
              {cat.headline}
              <ExternalLink className="w-3 h-3 mt-0.5 shrink-0 text-slate-600" />
            </a>
            <p className="text-[10px] text-slate-600 mt-1">{cat.source} · {cat.date}</p>
          </div>
        )}

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
          <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.04] text-center">
            <p className="text-[10px] text-slate-500 uppercase">VWAP</p>
            <p className={`font-mono text-sm font-bold ${t.aboveVwap ? "text-emerald-400" : t.aboveVwap === false ? "text-red-400" : "text-white"}`}>
              {t.vwap != null ? `$${fmt(t.vwap)}` : "—"}
            </p>
            <p className="text-[10px] text-slate-600">{t.distFromVwapPct != null ? `${t.distFromVwapPct > 0 ? "+" : ""}${t.distFromVwapPct}% vs px` : ""}</p>
          </div>
          <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.04] text-center">
            <p className="text-[10px] text-slate-500 uppercase">RSI (5m)</p>
            <p className={`font-mono text-sm font-bold ${t.rsi14 > 80 ? "text-amber-400" : "text-white"}`}>{t.rsi14 ?? "—"}</p>
            <p className="text-[10px] text-slate-600">{t.rsi14 > 80 ? "overheated" : t.rsi14 >= 50 ? "momentum" : ""}</p>
          </div>
          <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.04] text-center">
            <p className="text-[10px] text-slate-500 uppercase">OR High</p>
            <p className="font-mono text-sm font-bold text-white">{t.openingRangeHigh != null ? `$${fmt(t.openingRangeHigh)}` : "—"}</p>
            <p className="text-[10px] text-slate-600">breakout trigger</p>
          </div>
          <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.04] text-center">
            <p className="text-[10px] text-slate-500 uppercase">9-EMA (5m)</p>
            <p className="font-mono text-sm font-bold text-white">{t.ema9 != null ? `$${fmt(t.ema9)}` : "—"}</p>
            <p className="text-[10px] text-slate-600">trail guide</p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2 mt-3" data-testid={`trade-plan-${c.ticker}`}>
          <div className="p-3 rounded-lg bg-blue-500/5 border border-blue-500/15 text-center">
            <p className="text-[10px] text-blue-400 font-semibold uppercase mb-1">Entry Zone</p>
            <p className="font-mono font-bold text-blue-400 text-sm">${fmt(p.entryZoneLow)}–${fmt(p.entryRef)}</p>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/15 text-center">
            <p className="text-[10px] text-emerald-500 font-semibold uppercase mb-1">Target 1 (+2%)</p>
            <p className="font-mono font-bold text-emerald-400 text-sm">${fmt(p.target1)}</p>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/15 text-center">
            <p className="text-[10px] text-emerald-500 font-semibold uppercase mb-1">Target 2 (+3%)</p>
            <p className="font-mono font-bold text-emerald-400 text-sm">${fmt(p.target2)}</p>
          </div>
          <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/15 text-center">
            <p className="text-[10px] text-red-400 font-semibold uppercase mb-1">Stop ({fmt(p.stopPct, 1)}%)</p>
            <p className="font-mono font-bold text-red-400 text-sm">${fmt(p.stop)}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 mt-3 flex-wrap">
          {p.rewardRisk != null && (
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Target className="w-3 h-3 text-blue-400" /> R/R {p.rewardRisk}:1 to T1
            </span>
          )}
          {a.consensus && (
            <span className="text-[11px] text-slate-400">Analysts: <span className="text-white font-semibold">{a.consensus}</span>{a.priceTarget ? ` · PT $${fmt(a.priceTarget)}` : ""}{a.upsidePct != null ? ` (${a.upsidePct > 0 ? "+" : ""}${a.upsidePct}%)` : ""}</span>
          )}
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 w-full flex items-center justify-center gap-1 text-xs text-slate-400 hover:text-white py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.05] transition-colors"
          data-testid={`expand-playbook-${c.ticker}`}
        >
          {expanded ? "Hide" : "Show"} full trade playbook
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>

        {expanded && (
          <div className="mt-3 space-y-3" data-testid={`playbook-${c.ticker}`}>
            <div className="p-3 bg-white/[0.03] rounded-lg border border-white/[0.04]">
              <p className="text-[11px] font-semibold text-blue-400 uppercase tracking-wider mb-2">How to trade it — until sell</p>
              <ol className="space-y-2">
                {(p.steps || []).map((s, i) => (
                  <li key={i} className="text-sm text-slate-400 leading-relaxed flex gap-2">
                    <span className="text-blue-400 font-mono font-bold shrink-0">{i + 1}.</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ol>
            </div>
            {(c.signals || []).length > 0 && (
              <div className="p-3 bg-emerald-500/5 rounded-lg border border-emerald-500/10">
                <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider mb-1.5">Why it qualifies</p>
                {c.signals.map((s, i) => (
                  <p key={i} className="text-sm text-slate-400 flex items-start gap-1.5"><TrendingUp className="w-3 h-3 text-emerald-500 mt-1 shrink-0" />{s}</p>
                ))}
              </div>
            )}
            {(c.risks || []).length > 0 && (
              <div className="p-3 bg-amber-500/5 rounded-lg border border-amber-500/10">
                <p className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider mb-1.5">Risk flags</p>
                {c.risks.map((r, i) => (
                  <p key={i} className="text-sm text-slate-400 flex items-start gap-1.5"><ShieldAlert className="w-3 h-3 text-amber-500 mt-1 shrink-0" />{r}</p>
                ))}
              </div>
            )}
            {(a.recentActions || []).length > 0 && (
              <div className="p-3 bg-white/[0.03] rounded-lg border border-white/[0.04]">
                <p className="text-[11px] font-semibold text-violet-400 uppercase tracking-wider mb-1.5">Analyst actions this week</p>
                {a.recentActions.map((r, i) => (
                  <p key={i} className="text-sm text-slate-400">
                    <span className="text-slate-500 font-mono text-xs">{r.date}</span> · <span className="text-white">{r.firm}</span> — {r.action}{r.grade ? `: ${r.grade}` : ""}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Scoreboard({ data }) {
  if (!data) return null;
  return (
    <div className="glass-card p-5" data-testid="day-trades-scoreboard">
      <div className="flex items-center gap-2 mb-4">
        <Trophy className="w-4 h-4 text-amber-400" />
        <h2 className="text-base font-bold text-white">Pick Scoreboard</h2>
        <span className="text-xs text-slate-500">— did the +2% targets actually hit?</span>
      </div>
      {data.evaluated === 0 ? (
        <p className="text-sm text-slate-500">No evaluated picks yet. Today's picks get scored against real intraday highs/lows after the session closes.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
            <div className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.04] text-center">
              <p className="text-2xl font-mono font-bold text-white">{data.winRatePct != null ? `${data.winRatePct}%` : "—"}</p>
              <p className="text-[10px] text-slate-500 uppercase mt-1">Win rate</p>
            </div>
            <div className="p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/15 text-center">
              <p className="text-2xl font-mono font-bold text-emerald-400">{data.targetHits}</p>
              <p className="text-[10px] text-slate-500 uppercase mt-1">Target hits</p>
            </div>
            <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/15 text-center">
              <p className="text-2xl font-mono font-bold text-red-400">{data.stops}</p>
              <p className="text-[10px] text-slate-500 uppercase mt-1">Stopped</p>
            </div>
            <div className="p-3 rounded-lg bg-white/[0.03] border border-white/[0.04] text-center">
              <p className="text-2xl font-mono font-bold text-white">{data.avgRealizedPct != null ? `${data.avgRealizedPct > 0 ? "+" : ""}${data.avgRealizedPct}%` : "—"}</p>
              <p className="text-[10px] text-slate-500 uppercase mt-1">Avg realized</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[10px] text-slate-500 uppercase tracking-wider border-b border-white/[0.05]">
                  <th className="py-2 pr-3">Date</th>
                  <th className="py-2 pr-3">Ticker</th>
                  <th className="py-2 pr-3">Entry</th>
                  <th className="py-2 pr-3">Outcome</th>
                  <th className="py-2 pr-3 text-right">Realized</th>
                </tr>
              </thead>
              <tbody>
                {data.history.map((h, i) => {
                  const o = OUTCOME_LABELS[h.outcome] || { label: h.outcome, cls: "text-slate-400 bg-slate-500/10 border-slate-500/20" };
                  return (
                    <tr key={i} className="border-b border-white/[0.03]">
                      <td className="py-2 pr-3 font-mono text-xs text-slate-500">{h.date}</td>
                      <td className="py-2 pr-3 font-mono font-bold text-blue-400">{h.ticker}</td>
                      <td className="py-2 pr-3 font-mono text-slate-400">${fmt(h.entryRef)}</td>
                      <td className="py-2 pr-3"><span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${o.cls}`}>{o.label}</span></td>
                      <td className={`py-2 pr-3 text-right font-mono font-semibold ${(h.realizedPct || 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {h.realizedPct != null ? `${h.realizedPct > 0 ? "+" : ""}${h.realizedPct}%` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default function DayTrades() {
  const [data, setData] = useState(null);
  const [scoreboard, setScoreboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (refresh = false) => {
    try {
      refresh ? setRefreshing(true) : setLoading(true);
      setError(null);
      const d = await fetchDayTrades(refresh);
      setData(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    fetchDayTradesScoreboard().then(setScoreboard).catch(() => {});
  }, [load]);

  const session = data?.session;

  return (
    <div className="space-y-5" data-testid="day-trades-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" />
            <h1 className="text-2xl font-bold text-white">Day Trades</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Intraday candidates targeting +2–3% — news catalysts, live technicals, analyst flow, and a step-by-step plan until sell.
          </p>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-semibold hover:bg-blue-500/20 transition-colors disabled:opacity-50"
          data-testid="day-trades-refresh-btn"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? "Scanning..." : "Refresh scan"}
        </button>
      </div>

      {session && (
        <div className="glass-card p-4 flex items-center gap-3" data-testid="session-banner">
          <Clock className="w-4 h-4 text-blue-400 shrink-0" />
          <div>
            <span className="text-xs font-bold text-white">{session.phase}</span>
            <span className="text-xs text-slate-500"> · {session.etTime}</span>
            <p className="text-sm text-slate-400 mt-0.5">{session.note}</p>
          </div>
        </div>
      )}

      <MorningRoutine />

      <div className="glass-card p-3 flex items-start gap-2 border-amber-500/10">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-slate-500 leading-relaxed">
          Day trading is high risk. These are technical setups, not guarantees — expect stops to hit regularly. Risk a fixed fraction per trade (1% rule) and never trade without the stop in place.
        </p>
      </div>

      {loading ? (
        <div className="glass-card p-10 text-center">
          <Activity className="w-6 h-6 text-blue-400 mx-auto animate-pulse" />
          <p className="text-sm text-slate-500 mt-3">Scanning gainers, volume leaders, news and analyst flow...</p>
        </div>
      ) : error ? (
        <div className="glass-card p-6 text-center" data-testid="day-trades-error">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      ) : (data?.candidates || []).length === 0 ? (
        <div className="glass-card p-10 text-center">
          <p className="text-sm text-slate-500">No qualifying setups right now. Re-scan closer to the market open.</p>
        </div>
      ) : (
        <div className="space-y-4" data-testid="day-trades-list">
          {data.candidates.map((c, i) => (
            <TradeCard key={c.ticker} c={c} rank={i + 1} />
          ))}
        </div>
      )}

      <Scoreboard data={scoreboard} />
    </div>
  );
}
