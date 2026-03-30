import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import {
  Zap, TrendingUp, Shield, AlertTriangle, Power, Activity,
  Clock, Target, DollarSign, BarChart2, Settings, Timer,
  Play, Pause, Square, RefreshCw, Eye, ChevronDown, ChevronUp,
  ArrowUpRight, ArrowDownRight, Loader2, Brain, Lock, Bell,
  CircleStop, Radio, MonitorCheck, Gauge, ShieldAlert, Filter,
  Search, Layers, TriangleAlert, CheckCircle, Database,
  ArrowUp, ArrowDown, Grid3x3
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

const RegimeBadge = ({ regime }) => {
  const colors = {
    bullish: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    neutral_bullish: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    neutral: "bg-slate-500/20 text-slate-400 border-slate-500/30",
    neutral_bearish: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    bearish: "bg-red-500/20 text-red-400 border-red-500/30",
    high_volatility: "bg-red-500/20 text-orange-400 border-orange-500/30"
  };
  return (
    <Badge variant="outline" className={`text-[10px] ${colors[regime?.regime] || colors.neutral}`}>
      {regime?.regime?.replace("_", " ")?.toUpperCase() || "UNKNOWN"} | Vol: {regime?.volatility_pct || "?"}%
    </Badge>
  );
};

const StatusIndicator = ({ status }) => {
  const cfg = {
    off: { color: "bg-slate-500", pulse: false, text: "OFF", textClass: "text-slate-400" },
    running: { color: "bg-emerald-500", pulse: true, text: "RUNNING", textClass: "text-emerald-400" },
    paused: { color: "bg-amber-500", pulse: true, text: "PAUSED", textClass: "text-amber-400" },
    emergency_stop: { color: "bg-red-500", pulse: true, text: "EMERGENCY STOP", textClass: "text-red-400" },
  };
  const c = cfg[status] || cfg.off;
  return (
    <div className="flex items-center gap-2" data-testid="scheduler-status-indicator">
      <div className={`w-3 h-3 rounded-full ${c.color} ${c.pulse ? 'animate-pulse' : ''}`} />
      <span className={`text-sm font-bold ${c.textClass}`}>{c.text}</span>
    </div>
  );
};

const DeployBadge = ({ mode }) => {
  const cfg = {
    paper: { label: "PAPER", cls: "bg-blue-500/20 border-blue-500/40 text-blue-400" },
    shadow: { label: "SHADOW", cls: "bg-purple-500/20 border-purple-500/40 text-purple-400" },
    limited_live: { label: "LIMITED LIVE", cls: "bg-amber-500/20 border-amber-500/40 text-amber-400" },
    full_live: { label: "FULL LIVE", cls: "bg-red-500/20 border-red-500/40 text-red-400" },
  };
  const c = cfg[mode] || cfg.paper;
  return <Badge variant="outline" className={`text-[10px] font-bold ${c.cls}`} data-testid="deploy-mode-badge">{c.label}</Badge>;
};

const RiskModeBadge = ({ mode }) => {
  const cfg = {
    NORMAL: { cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
    CAUTIOUS: { cls: "bg-amber-500/20 text-amber-400 border-amber-500/30" },
    DEFENSIVE: { cls: "bg-red-500/20 text-red-400 border-red-500/30" },
  };
  const c = cfg[mode] || cfg.NORMAL;
  return <Badge variant="outline" className={`text-[10px] font-bold ${c.cls}`} data-testid="risk-mode-badge">{mode || "NORMAL"}</Badge>;
};

const CountdownTimer = ({ seconds, label }) => {
  if (seconds === null || seconds === undefined) return <span className="text-slate-600">--:--</span>;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return (
    <div className="text-center">
      <p className="text-xl font-mono text-white tabular-nums">{m}:{String(s).padStart(2, '0')}</p>
      <p className="text-[10px] text-slate-500">{label}</p>
    </div>
  );
};

const SessionBadge = ({ session }) => {
  const cfg = {
    pre_market: { label: "Pre-Market", cls: "text-amber-400 border-amber-500/30" },
    regular: { label: "Regular Hours", cls: "text-emerald-400 border-emerald-500/30" },
    closing: { label: "Closing (Risk Tightened)", cls: "text-orange-400 border-orange-500/30" },
    after_hours: { label: "After Hours", cls: "text-purple-400 border-purple-500/30" },
    closed: { label: "Market Closed", cls: "text-slate-400 border-slate-700" },
  };
  const c = cfg[session] || cfg.closed;
  return <Badge variant="outline" className={`text-[10px] ${c.cls}`}>{c.label}</Badge>;
};

const OpportunityBadge = ({ quality }) => {
  const cfg = {
    HIGH_OPPORTUNITY: { cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", label: "HIGH OPP." },
    MEDIUM_OPPORTUNITY: { cls: "bg-amber-500/20 text-amber-400 border-amber-500/30", label: "MEDIUM OPP." },
    LOW_OPPORTUNITY: { cls: "bg-red-500/20 text-red-400 border-red-500/30", label: "LOW OPP." },
  };
  const c = cfg[quality] || cfg.LOW_OPPORTUNITY;
  return <Badge variant="outline" className={`text-[10px] ${c.cls}`}>{c.label}</Badge>;
};

// Pipeline Funnel visualization
const PipelineFunnel = ({ funnel }) => {
  if (!funnel?.funnel) return null;
  const stages = [
    { key: "universe_scanned", label: "Universe", icon: Layers },
    { key: "prefilter_passed", label: "Pre-Filter", icon: Filter },
    { key: "ta_analyzed", label: "TA Analyzed", icon: BarChart2 },
    { key: "setup_found", label: "Setup Found", icon: Zap },
    { key: "filters_passed", label: "Filters OK", icon: CheckCircle },
    { key: "confidence_passed", label: "Confidence", icon: Target },
    { key: "risk_approved", label: "Risk OK", icon: Shield },
    { key: "executed", label: "Executed", icon: Play },
  ];
  const maxVal = Math.max(1, ...Object.values(funnel.funnel));

  // Separate MTF and Momentum rejections for special display
  const mtfRejections = Object.entries(funnel.top_rejections || {}).filter(([k]) => k.toLowerCase().includes('mtf') || k.toLowerCase().includes('timeframe'));
  const momentumRejections = Object.entries(funnel.top_rejections || {}).filter(([k]) => k.toLowerCase().includes('momentum'));
  const otherRejections = Object.entries(funnel.top_rejections || {}).filter(([k]) => !k.toLowerCase().includes('mtf') && !k.toLowerCase().includes('timeframe') && !k.toLowerCase().includes('momentum'));

  return (
    <Card className="terminal-card p-4" data-testid="pipeline-funnel">
      <div className="flex items-center gap-2 mb-3">
        <Filter className="w-4 h-4 text-blue-400" />
        <span className="text-xs text-white font-medium">Trade Pipeline Funnel</span>
        {funnel.bottleneck && (
          <Badge variant="outline" className="text-[10px] border-red-500/30 text-red-400">
            Bottleneck: {funnel.bottleneck.replace("_", " ")}
          </Badge>
        )}
      </div>
      <div className="space-y-1.5">
        {stages.map(({ key, label, icon: Icon }) => {
          const count = funnel.funnel[key] || 0;
          const width = Math.max(2, (count / maxVal) * 100);
          return (
            <div key={key} className="flex items-center gap-2">
              <Icon className="w-3 h-3 text-slate-500 shrink-0" />
              <span className="text-[10px] text-slate-500 w-16 shrink-0">{label}</span>
              <div className="flex-1 h-4 bg-slate-900 rounded overflow-hidden">
                <div className="h-full bg-blue-500/30 rounded transition-all duration-500"
                  style={{ width: `${width}%` }} />
              </div>
              <span className="text-xs text-white font-mono w-10 text-right">{count}</span>
            </div>
          );
        })}
      </div>
      {(mtfRejections.length > 0 || momentumRejections.length > 0 || otherRejections.length > 0) && (
        <div className="mt-3 pt-2 border-t border-slate-800">
          <p className="text-[10px] text-slate-500 mb-1">Top Rejection Reasons</p>
          <div className="flex flex-wrap gap-1">
            {mtfRejections.map(([reason, count]) => (
              <Badge key={reason} variant="outline" className="text-[10px] border-red-500/30 text-red-400">
                {reason.replace(/_/g, " ")}: {count}
              </Badge>
            ))}
            {momentumRejections.map(([reason, count]) => (
              <Badge key={reason} variant="outline" className="text-[10px] border-orange-500/30 text-orange-400">
                {reason.replace(/_/g, " ")}: {count}
              </Badge>
            ))}
            {otherRejections.slice(0, 6).map(([reason, count]) => (
              <Badge key={reason} variant="outline" className="text-[10px] border-slate-700 text-slate-400">
                {reason.replace(/_/g, " ")}: {count}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};

// No-Trade Reason Panel
const NoTradePanel = ({ summary }) => {
  if (!summary || summary.has_trades) return null;
  return (
    <Card className="p-4 border-amber-500/20 bg-amber-500/5" data-testid="no-trade-panel">
      <div className="flex items-center gap-2 mb-2">
        <TriangleAlert className="w-4 h-4 text-amber-400" />
        <span className="text-xs text-amber-400 font-medium">No Trades Generated</span>
        <OpportunityBadge quality={summary.opportunity_quality} />
      </div>
      {summary.top_reasons?.length > 0 && (
        <div className="mb-3">
          <p className="text-[10px] text-slate-500 mb-1">Reasons:</p>
          <ul className="space-y-1">
            {summary.top_reasons.map((r, i) => (
              <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                <span className="text-amber-500">-</span> {r}
              </li>
            ))}
          </ul>
        </div>
      )}
      {summary.near_misses?.length > 0 && (
        <div>
          <p className="text-[10px] text-slate-500 mb-1">Near-Miss Candidates (Almost Qualified):</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {summary.near_misses.slice(0, 8).map((nm, i) => (
              <div key={i} className="p-2 rounded bg-slate-900/50 border border-slate-800">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white font-medium">{nm.symbol}</span>
                  <span className={`text-[10px] font-mono ${nm.confidence >= 75 ? 'text-amber-400' : 'text-slate-500'}`}>
                    {nm.confidence}/100
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 truncate">{nm.reject_reasons?.[0] || nm.label}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};

const ExplanationCard = ({ item, expanded, onToggle }) => {
  const exp = item.explanation || {};
  const isDay = item.classification === "DAY_TRADE";
  const signal = item.signal || {};
  const ki = exp.key_indicators || {};
  return (
    <Card className="terminal-card overflow-hidden" data-testid={`candidate-${item.symbol}`}>
      <div className="p-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isDay ? 'bg-amber-500/20' : 'bg-blue-500/20'}`}>
              {isDay ? <Zap className="w-5 h-5 text-amber-400" /> : <TrendingUp className="w-5 h-5 text-blue-400" />}
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white font-bold">{item.symbol}</span>
                <Badge variant="outline" className={`text-[10px] ${isDay ? 'border-amber-500/30 text-amber-400' : 'border-blue-500/30 text-blue-400'}`}>
                  {isDay ? "DAY TRADE" : "LONG TERM"}
                </Badge>
                <Badge variant="outline" className={`text-[10px] ${
                  item.action === "BUY" ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10' :
                  item.action === "SELL" ? 'border-red-500/30 text-red-400 bg-red-500/10' :
                  item.action === "WATCHLIST" ? 'border-amber-500/30 text-amber-400' :
                  item.action === "NEAR_MISS" ? 'border-purple-500/30 text-purple-400' :
                  'border-red-500/30 text-red-400'
                }`}>{item.action}</Badge>
                {item.momentum_mode && (
                  <Badge variant="outline" className="text-[10px] border-orange-500/40 text-orange-400 bg-orange-500/10 animate-pulse">
                    MOMENTUM
                  </Badge>
                )}
                {item.momentum_bypass_active && (
                  <Badge variant="outline" className="text-[10px] border-orange-500/40 text-orange-300 bg-orange-500/15">
                    BYPASS ACTIVE
                  </Badge>
                )}
                {item.mtf_aligned && (
                  <Badge variant="outline" className="text-[10px] border-cyan-500/30 text-cyan-400">
                    MTF OK
                  </Badge>
                )}
                {item.has_tf_conflict && (
                  <Badge variant="outline" className="text-[10px] border-red-500/40 text-red-400 bg-red-500/10">
                    TF CONFLICT
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-500">{isDay ? `${item.direction || ''} ${item.best_setup ? `- ${item.best_setup}` : ''}`.trim() : (signal.name || signal.company_name || "")}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-white font-mono">${(signal.price || signal.entry || 0).toFixed(2)}</p>
              <p className="text-xs text-slate-500">Conf: <span className={`font-bold ${
                item.confidence >= 80 ? 'text-emerald-400' : item.confidence >= 65 ? 'text-amber-400' : 'text-red-400'
              }`}>{item.confidence}/100</span></p>
            </div>
            {expanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </div>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-800 pt-3">
          {/* MTF Details */}
          {isDay && (ki.mtf_5m || ki.mtf_15m || ki.mtf_1m) && (
            <div className="p-3 rounded bg-cyan-500/5 border border-cyan-500/20">
              <p className="text-[10px] text-cyan-400 mb-1 font-medium">MULTI-TIMEFRAME CONFIRMATION</p>
              <div className="grid grid-cols-4 gap-2 text-xs">
                <div className="text-center p-1.5 rounded bg-slate-800/50">
                  <p className="text-[10px] text-slate-500">15m Trend</p>
                  <p className={`font-mono text-[11px] ${ki.mtf_15m === 'bullish' ? 'text-emerald-400' : ki.mtf_15m === 'bearish' ? 'text-red-400' : 'text-slate-400'}`}>
                    {ki.mtf_15m || '?'}
                  </p>
                </div>
                <div className="text-center p-1.5 rounded bg-slate-800/50">
                  <p className="text-[10px] text-slate-500">5m Structure</p>
                  <p className={`font-mono text-[11px] ${ki.mtf_5m === 'bullish' ? 'text-emerald-400' : ki.mtf_5m === 'bearish' ? 'text-red-400' : 'text-slate-400'}`}>
                    {ki.mtf_5m || '?'}
                  </p>
                </div>
                <div className="text-center p-1.5 rounded bg-slate-800/50">
                  <p className="text-[10px] text-slate-500">1m Timing</p>
                  <p className={`font-mono text-[11px] ${ki.mtf_1m === 'bullish' ? 'text-emerald-400' : ki.mtf_1m === 'bearish' ? 'text-red-400' : 'text-slate-400'}`}>
                    {ki.mtf_1m || '?'}
                  </p>
                </div>
                <div className="text-center p-1.5 rounded bg-slate-800/50">
                  <p className="text-[10px] text-slate-500">MTF Score</p>
                  <p className={`font-mono text-[11px] ${ki.mtf_aligned ? 'text-emerald-400' : ki.has_tf_conflict ? 'text-red-400' : 'text-amber-400'}`}>
                    {ki.mtf_score || '?'}
                  </p>
                </div>
              </div>
              {ki.has_tf_conflict && (
                <p className="text-[10px] text-red-400 mt-1">Timeframe conflict: higher timeframes oppose trade direction</p>
              )}
              {ki.momentum_bypass_active && (
                <p className="text-[10px] text-orange-400 mt-1">Momentum Mode active: bypassing soft conservative filters</p>
              )}
            </div>
          )}
          {exp.entry_reasons?.length > 0 && (
            <div className="p-3 rounded bg-emerald-500/5 border border-emerald-500/20">
              <p className="text-[10px] text-emerald-400 mb-1 font-medium">BUY REASONS</p>
              <ul className="space-y-1">
                {exp.entry_reasons.map((r, i) => (
                  <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                    <ArrowUpRight className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />{r}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {exp.reject_reasons?.length > 0 && (
            <div className="p-3 rounded bg-red-500/5 border border-red-500/20">
              <p className="text-[10px] text-red-400 mb-1 font-medium">RISK FLAGS</p>
              <ul className="space-y-1">
                {exp.reject_reasons.map((r, i) => (
                  <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                    <AlertTriangle className="w-3 h-3 text-red-400 shrink-0 mt-0.5" />{r}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {exp.exit_plan && Object.keys(exp.exit_plan).length > 0 && (
            <div className="p-3 rounded bg-slate-900/50 border border-slate-800">
              <p className="text-[10px] text-slate-400 mb-2 font-medium">EXIT PLAN</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                {exp.exit_plan.entry && <div><p className="text-slate-500">Entry</p><p className="text-white font-mono">${exp.exit_plan.entry}</p></div>}
                {exp.exit_plan.take_profit && <div><p className="text-slate-500">TP</p><p className="text-emerald-400 font-mono">${exp.exit_plan.take_profit}</p></div>}
                {exp.exit_plan.stop_loss && <div><p className="text-slate-500">SL</p><p className="text-red-400 font-mono">${exp.exit_plan.stop_loss}</p></div>}
                {exp.exit_plan.time_exit && <div><p className="text-slate-500">Time</p><p className="text-slate-300">{exp.exit_plan.time_exit}</p></div>}
              </div>
            </div>
          )}
          {exp.key_indicators && (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs">
              {Object.entries(exp.key_indicators).filter(([k, v]) => v !== null && v !== undefined && v !== "" && !["diagnostic_tags", "mtf_5m", "mtf_15m", "mtf_1m", "mtf_score", "mtf_aligned", "has_tf_conflict", "momentum_bypass_active"].includes(k)).map(([k, v]) => (
                <div key={k} className="text-center p-1.5 rounded bg-slate-800/50">
                  <p className="text-[10px] text-slate-500">{k.replace(/_/g, " ")}</p>
                  <p className="text-white font-mono text-[11px]">{typeof v === "number" ? v.toFixed(1) : String(v)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

// ===================== MTF HEATMAP COMPONENT =====================
const CATEGORY_STYLES = {
  BULLISH_ALIGNED: { bg: "bg-emerald-500/10", border: "border-emerald-500/25", text: "text-emerald-400", label: "Bullish Aligned" },
  BEARISH_ALIGNED: { bg: "bg-red-500/10", border: "border-red-500/25", text: "text-red-400", label: "Bearish Aligned" },
  MOMENTUM_CANDIDATE: { bg: "bg-purple-500/10", border: "border-purple-500/25", text: "text-purple-400", label: "Momentum" },
  NEAR_MISS: { bg: "bg-amber-500/10", border: "border-amber-500/25", text: "text-amber-400", label: "Near Miss" },
  MIXED: { bg: "bg-slate-500/10", border: "border-slate-600/25", text: "text-slate-400", label: "Mixed" },
  CONFLICT: { bg: "bg-orange-500/10", border: "border-orange-500/25", text: "text-orange-400", label: "Conflict" },
};

const TF_CELL_COLORS = {
  bullish: "bg-emerald-500/20 text-emerald-400",
  bearish: "bg-red-500/20 text-red-400",
  ranging: "bg-slate-500/15 text-slate-400",
  neutral: "bg-slate-500/10 text-slate-500",
  mixed: "bg-amber-500/15 text-amber-400",
  unknown: "bg-slate-800 text-slate-600",
  entry_ready: "bg-emerald-500/20 text-emerald-400",
  early: "bg-amber-500/15 text-amber-400",
  weak: "bg-red-500/15 text-red-400",
};

const MTFHeatmap = ({ heatmap, distribution }) => {
  const [sortBy, setSortBy] = useState("confidence");
  const [filterCat, setFilterCat] = useState("ALL");
  const [filterDir, setFilterDir] = useState("ALL");
  const [showCount, setShowCount] = useState(30);

  if (!heatmap || heatmap.length === 0) {
    return (
      <Card className="terminal-card p-8 text-center text-slate-500 text-sm">
        No MTF heatmap data. Run a scan first.
      </Card>
    );
  }

  const sortFns = {
    confidence: (a, b) => b.confidence - a.confidence,
    rel_vol: (a, b) => b.rel_vol - a.rel_vol,
    mtf_score: (a, b) => b.mtf_score - a.mtf_score,
    category: (a, b) => a.category.localeCompare(b.category),
  };

  const filtered = heatmap
    .filter(h => filterCat === "ALL" || h.category === filterCat)
    .filter(h => filterDir === "ALL" || h.direction === filterDir)
    .sort(sortFns[sortBy] || sortFns.confidence)
    .slice(0, showCount);

  const total = heatmap.length;

  return (
    <div className="space-y-3" data-testid="mtf-heatmap">
      {/* Distribution Summary */}
      {distribution && (
        <Card className="terminal-card p-4">
          <h3 className="text-xs text-cyan-400 mb-3 flex items-center gap-2"><Grid3x3 className="w-4 h-4" /> MTF Classification Distribution ({total} stocks)</h3>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
            {Object.entries(distribution).map(([cat, count]) => {
              const s = CATEGORY_STYLES[cat] || CATEGORY_STYLES.MIXED;
              const pct = total > 0 ? Math.round((count / total) * 100) : 0;
              return (
                <button key={cat} onClick={() => setFilterCat(filterCat === cat ? "ALL" : cat)}
                  className={`p-2 rounded border text-center transition-all ${s.bg} ${filterCat === cat ? s.border + ' ring-1 ring-offset-1 ring-offset-slate-950 ' + s.border : 'border-slate-800 hover:' + s.border}`}
                  data-testid={`heatmap-filter-${cat}`}>
                  <p className={`text-lg font-mono font-bold ${s.text}`}>{count}</p>
                  <p className="text-[9px] text-slate-500">{s.label}</p>
                  <p className="text-[9px] text-slate-600">{pct}%</p>
                </button>
              );
            })}
          </div>
        </Card>
      )}

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10px] text-slate-500">Sort:</span>
        {["confidence", "rel_vol", "mtf_score", "category"].map(s => (
          <button key={s} onClick={() => setSortBy(s)}
            className={`px-2 py-1 text-[10px] rounded border ${sortBy === s ? 'border-cyan-500/40 text-cyan-400 bg-cyan-500/10' : 'border-slate-700 text-slate-500 hover:text-slate-300'}`}>
            {s.replace("_", " ")}
          </button>
        ))}
        <span className="text-[10px] text-slate-600 mx-1">|</span>
        <span className="text-[10px] text-slate-500">Dir:</span>
        {["ALL", "LONG", "SHORT"].map(d => (
          <button key={d} onClick={() => setFilterDir(d)}
            className={`px-2 py-1 text-[10px] rounded border ${filterDir === d ? 'border-blue-500/40 text-blue-400 bg-blue-500/10' : 'border-slate-700 text-slate-500 hover:text-slate-300'}`}>
            {d}
          </button>
        ))}
        <span className="text-[10px] text-slate-600 mx-1">|</span>
        <button onClick={() => setFilterCat("ALL")} className="px-2 py-1 text-[10px] rounded border border-slate-700 text-slate-500 hover:text-white">
          Clear Filters
        </button>
        <span className="text-[10px] text-slate-500 ml-auto">{filtered.length} shown</span>
      </div>

      {/* Heatmap Table */}
      <Card className="terminal-card overflow-x-auto">
        <table className="w-full text-xs" data-testid="heatmap-table">
          <thead>
            <tr className="border-b border-slate-800 text-[10px] text-slate-500">
              <th className="p-2 text-left">Ticker</th>
              <th className="p-2 text-center">15m Trend</th>
              <th className="p-2 text-center">5m Structure</th>
              <th className="p-2 text-center">1m Timing</th>
              <th className="p-2 text-center">MTF Status</th>
              <th className="p-2 text-center">Conf</th>
              <th className="p-2 text-center">RelVol</th>
              <th className="p-2 text-center">VWAP</th>
              <th className="p-2 text-center">Setup</th>
              <th className="p-2 text-left">Rejection / Notes</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((h, i) => {
              const cs = CATEGORY_STYLES[h.category] || CATEGORY_STYLES.MIXED;
              return (
                <tr key={h.symbol} className={`border-b border-slate-800/50 hover:bg-slate-800/30 ${i % 2 === 0 ? '' : 'bg-slate-900/30'}`}
                  data-testid={`heatmap-row-${h.symbol}`}>
                  <td className="p-2">
                    <div className="flex items-center gap-1.5">
                      <span className="text-white font-mono font-medium">{h.symbol}</span>
                      <span className={`text-[9px] ${h.direction === "LONG" ? "text-emerald-400" : h.direction === "SHORT" ? "text-red-400" : "text-slate-500"}`}>
                        {h.direction === "LONG" ? "L" : h.direction === "SHORT" ? "S" : "?"}
                      </span>
                    </div>
                    <span className="text-[9px] text-slate-600 font-mono">${h.price?.toFixed(2)}</span>
                  </td>
                  <td className="p-2 text-center">
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono ${TF_CELL_COLORS[h.trend_15m] || TF_CELL_COLORS.unknown}`}>
                      {h.trend_15m}
                    </span>
                  </td>
                  <td className="p-2 text-center">
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono ${TF_CELL_COLORS[h.structure_5m] || TF_CELL_COLORS.unknown}`}>
                      {h.structure_5m}
                    </span>
                  </td>
                  <td className="p-2 text-center">
                    <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono ${TF_CELL_COLORS[h.timing_status] || TF_CELL_COLORS.unknown}`}>
                      {h.timing_status}
                    </span>
                  </td>
                  <td className="p-2 text-center">
                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium border ${cs.bg} ${cs.border} ${cs.text}`}>
                      {cs.label}
                    </span>
                  </td>
                  <td className="p-2 text-center">
                    <span className={`font-mono font-bold ${h.confidence >= 75 ? "text-emerald-400" : h.confidence >= 65 ? "text-amber-400" : h.confidence >= 50 ? "text-orange-400" : "text-red-400"}`}>
                      {h.confidence}
                    </span>
                  </td>
                  <td className="p-2 text-center">
                    <span className={`font-mono ${h.rel_vol >= 2.5 ? "text-purple-400 font-bold" : h.rel_vol >= 1.5 ? "text-blue-400" : h.rel_vol >= 1.0 ? "text-slate-300" : "text-slate-600"}`}>
                      {h.rel_vol}x
                    </span>
                  </td>
                  <td className="p-2 text-center">
                    <div className="flex flex-col items-center">
                      <span className={`text-[10px] font-mono ${h.above_vwap ? "text-emerald-400" : h.above_vwap === false ? "text-red-400" : "text-slate-500"}`}>
                        {h.above_vwap ? "Above" : h.above_vwap === false ? "Below" : "—"}
                      </span>
                      <span className="text-[9px] text-slate-600">{h.vwap_distance_pct}%</span>
                    </div>
                  </td>
                  <td className="p-2 text-center">
                    <span className="text-[10px] text-slate-400 font-mono">{h.setup_type !== "none" ? h.setup_type.replace(/_/g, " ") : "—"}</span>
                  </td>
                  <td className="p-2">
                    {h.reject_reasons?.length > 0 ? (
                      <div className="max-w-[200px]">
                        {h.reject_reasons.slice(0, 2).map((r, j) => (
                          <p key={j} className="text-[9px] text-red-400/80 truncate">{r}</p>
                        ))}
                      </div>
                    ) : h.action === "BUY" || h.action === "SELL" ? (
                      <Badge variant="outline" className={`text-[9px] ${h.action === "BUY" ? "border-emerald-500/30 text-emerald-400" : "border-red-500/30 text-red-400"}`}>
                        {h.action}
                      </Badge>
                    ) : (
                      <span className="text-[9px] text-slate-600">{h.action}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      {/* Show More */}
      {filtered.length >= showCount && (
        <div className="text-center">
          <button onClick={() => setShowCount(prev => prev + 20)} className="text-[10px] text-cyan-400 hover:underline">
            Show more...
          </button>
        </div>
      )}
    </div>
  );
};

const AutoTrade = () => {
  const [status, setStatus] = useState(null);
  const [scheduler, setScheduler] = useState(null);
  const [opportunities, setOpportunities] = useState(null);
  const [history, setHistory] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [tradeLog, setTradeLog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [expandedCard, setExpandedCard] = useState(null);
  const [activeTab, setActiveTab] = useState("scheduler");
  const [dtCountdown, setDtCountdown] = useState(null);
  const [ltCountdown, setLtCountdown] = useState(null);
  const { token } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const timerRef = useRef(null);

  const fetchStatus = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/auto-trade/status`, { headers });
      if (resp.ok) setStatus(await resp.json());
    } catch (e) { console.error(e); }
  }, [token]);

  const fetchScheduler = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/scheduler/status`, { headers });
      if (resp.ok) {
        const data = await resp.json();
        setScheduler(data);
        setDtCountdown(data.next_dt_scan_seconds);
        setLtCountdown(data.next_lt_scan_seconds);
      }
    } catch (e) { console.error(e); }
  }, [token]);

  const fetchOpportunities = useCallback(async () => {
    setScanning(true);
    try {
      const resp = await fetch(`${API}/auto-trade/scan`, { headers });
      if (resp.ok) setOpportunities(await resp.json());
    } catch (e) { console.error(e); }
    setScanning(false);
  }, [token]);

  const fetchHistory = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/auto-trade/history?limit=30`, { headers });
      if (resp.ok) setHistory(await resp.json());
    } catch (e) { console.error(e); }
  }, [token]);

  const fetchNotifications = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/scheduler/notifications?limit=30`, { headers });
      if (resp.ok) setNotifications(await resp.json());
    } catch (e) { console.error(e); }
  }, [token]);

  const fetchTradeLog = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/auto-trade/trade-log?limit=50`, { headers });
      if (resp.ok) setTradeLog(await resp.json());
    } catch (e) { console.error(e); }
  }, [token]);

  useEffect(() => {
    Promise.all([fetchStatus(), fetchScheduler(), fetchOpportunities(), fetchHistory()]).finally(() => setLoading(false));
    const interval = setInterval(() => { fetchScheduler(); fetchStatus(); }, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchScheduler, fetchOpportunities, fetchHistory]);

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setDtCountdown(prev => prev !== null && prev > 0 ? prev - 1 : prev);
      setLtCountdown(prev => prev !== null && prev > 0 ? prev - 1 : prev);
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  const startScheduler = async () => {
    try {
      const resp = await fetch(`${API}/scheduler/start`, { method: "POST", headers });
      if (resp.ok) { const d = await resp.json(); toast.success(`Scheduler started (${d.deployment_mode} mode)`); fetchScheduler(); }
      else { const d = await resp.json(); toast.error(d.message || "Failed to start"); }
    } catch (e) { toast.error("Start failed"); }
  };
  const stopScheduler = async () => {
    try { const resp = await fetch(`${API}/scheduler/stop`, { method: "POST", headers }); if (resp.ok) { toast.success("Stopped"); fetchScheduler(); } } catch (e) { toast.error("Stop failed"); }
  };
  const emergencyStop = async () => {
    try { const resp = await fetch(`${API}/scheduler/emergency-stop`, { method: "POST", headers }); if (resp.ok) { toast.error("EMERGENCY STOP"); fetchScheduler(); fetchStatus(); } } catch (e) { toast.error("Failed"); }
  };
  const clearEmergency = async () => {
    try { const resp = await fetch(`${API}/scheduler/clear-emergency`, { method: "POST", headers }); if (resp.ok) { toast.success("Cleared"); fetchScheduler(); } } catch (e) { toast.error("Failed"); }
  };
  const setDeployMode = async (mode) => {
    try {
      const resp = await fetch(`${API}/scheduler/deploy-mode?mode=${mode}`, { method: "POST", headers });
      const d = await resp.json();
      if (d.error) { toast.error(d.error); } else { toast.success(`Mode: ${d.deployment_mode}`); fetchScheduler(); }
    } catch (e) { toast.error("Failed"); }
  };
  const executeCycle = async () => {
    setExecuting(true);
    try { await fetch(`${API}/auto-trade/execute-cycle`, { method: "POST", headers }); toast.success("Cycle executing..."); setTimeout(() => { fetchStatus(); fetchHistory(); }, 5000); } catch (e) { toast.error("Failed"); }
    setExecuting(false);
  };
  const [refreshingTA, setRefreshingTA] = useState(false);
  const refreshTA = async () => {
    setRefreshingTA(true);
    try {
      const resp = await fetch(`${API}/auto-trade/refresh-ta`, { method: "POST", headers });
      if (resp.ok) {
        const d = await resp.json();
        toast.success(`TA refresh started (${d.db_cached} cached)`);
      }
    } catch (e) { toast.error("TA refresh failed"); }
    setRefreshingTA(false);
  };
  const updateSetting = async (key, value) => {
    try { await fetch(`${API}/auto-trade/settings`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ [key]: value }) }); fetchStatus(); } catch (e) {}
  };
  const updateSchedulerSetting = async (key, value) => {
    try { await fetch(`${API}/scheduler/settings`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ [key]: value }) }); fetchScheduler(); } catch (e) {}
  };

  if (loading) return <div className="flex items-center justify-center h-96"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>;

  const s = status?.settings || {};
  const regime = status?.market_regime || {};
  const today = status?.today || {};
  const sch = scheduler || {};
  const schSettings = sch.settings || {};
  const dynThresh = opportunities?.dynamic_thresholds || {};
  const riskMode = opportunities?.risk_mode || dynThresh?.risk_mode || "NORMAL";
  const pipelineFunnel = opportunities?.pipeline_funnel;
  const noTradeSummary = opportunities?.no_trade_summary;

  return (
    <div className="space-y-6 max-w-7xl mx-auto" data-testid="auto-trade-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Brain className="w-6 h-6 text-blue-400" />
            <h1 className="font-display text-2xl font-bold text-white">AI Auto-Trade</h1>
            <DeployBadge mode={sch.deployment_mode} />
            <RiskModeBadge mode={riskMode} />
            <RegimeBadge regime={regime} />
          </div>
          <p className="text-sm text-slate-500">Safety-first, high-discipline autonomous trading</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusIndicator status={sch.status} />
          {sch.status === "off" && (
            <Button size="sm" onClick={startScheduler} className="bg-emerald-600 hover:bg-emerald-500" data-testid="start-scheduler-btn">
              <Play className="w-4 h-4 mr-1" /> Start
            </Button>
          )}
          {sch.status === "running" && (
            <Button size="sm" variant="outline" onClick={stopScheduler} className="border-slate-700" data-testid="stop-scheduler-btn">
              <Square className="w-4 h-4 mr-1" /> Stop
            </Button>
          )}
          {sch.status === "emergency_stop" && (
            <Button size="sm" onClick={clearEmergency} className="bg-amber-600 hover:bg-amber-500" data-testid="clear-emergency-btn">
              <Power className="w-4 h-4 mr-1" /> Clear Emergency
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={emergencyStop}
            className="border-red-500/40 text-red-400 hover:bg-red-500/10" data-testid="emergency-stop-btn">
            <CircleStop className="w-4 h-4 mr-1" /> Emergency Stop
          </Button>
        </div>
      </div>

      {/* Pause Banner */}
      {sch.pause_reason && (
        <Card className="p-3 border-amber-500/30 bg-amber-500/5" data-testid="pause-banner">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <p className="text-sm text-amber-400">{sch.pause_reason}</p>
          </div>
        </Card>
      )}

      {/* Market Condition Adjustment Active */}
      {(riskMode === "DEFENSIVE" || riskMode === "CAUTIOUS" || sch.post_cooldown_active || sch.daily_loss_pct_of_max >= 60) && (
        <Card className="p-3 border-blue-500/30 bg-blue-500/5" data-testid="market-adjustment-banner">
          <div className="flex items-center gap-2 flex-wrap">
            <Shield className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-blue-400 font-medium">Market Condition Adjustment Active:</span>
            {riskMode !== "NORMAL" && <Badge variant="outline" className="text-[10px] border-blue-500/30 text-blue-300">Risk Mode: {riskMode}</Badge>}
            {sch.post_cooldown_active && <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-400">Post-Cooldown: Thresholds +5</Badge>}
            {sch.daily_loss_pct_of_max >= 60 && <Badge variant="outline" className="text-[10px] border-red-500/30 text-red-400">Soft Lock: {sch.daily_loss_pct_of_max}% loss used</Badge>}
          </div>
        </Card>
      )}

      {/* Dashboard Strip */}
      <div className="grid grid-cols-2 md:grid-cols-7 gap-3">
        <Card className="terminal-card p-3 text-center"><CountdownTimer seconds={dtCountdown} label="Next DT Scan" /></Card>
        <Card className="terminal-card p-3 text-center"><CountdownTimer seconds={ltCountdown} label="Next LT Scan" /></Card>
        <Card className="terminal-card p-3 text-center">
          <SessionBadge session={sch.market_session} />
          <p className="text-[10px] text-slate-500 mt-1">Risk: {sch.risk_multiplier ? `${(sch.risk_multiplier * 100).toFixed(0)}%` : '--'}</p>
        </Card>
        <Card className="terminal-card p-3 text-center">
          <p className="text-xl font-mono text-white">{sch.cycle_count || 0}</p>
          <p className="text-[10px] text-slate-500">Cycles</p>
        </Card>
        <Card className="terminal-card p-3 text-center">
          <p className={`text-xl font-mono ${today.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {today.pnl >= 0 ? '+' : ''}${today.pnl?.toFixed(2) || '0.00'}
          </p>
          <p className="text-[10px] text-slate-500">Today P&L</p>
        </Card>
        <Card className="terminal-card p-3 text-center">
          <p className="text-xl font-mono text-white">{status?.positions || 0}</p>
          <p className="text-[10px] text-slate-500">Positions</p>
        </Card>
        <Card className="terminal-card p-3 text-center">
          <p className="text-xs text-amber-400 font-mono">DT:{dynThresh.dt_threshold || '--'}</p>
          <p className="text-xs text-blue-400 font-mono">LT:{dynThresh.lt_threshold || '--'}</p>
          <p className="text-[10px] text-slate-500">Dynamic Thresholds</p>
        </Card>
      </div>

      {/* Active Risk Limits */}
      <Card className="terminal-card p-3">
        <div className="flex items-center gap-2 mb-2">
          <ShieldAlert className="w-4 h-4 text-red-400" />
          <span className="text-xs text-slate-400 font-medium">Active Risk Limits</span>
          {sch.cooldown_remaining_seconds > 0 && (
            <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-400 animate-pulse">
              Cooldown: {Math.floor(sch.cooldown_remaining_seconds / 60)}m {sch.cooldown_remaining_seconds % 60}s
            </Badge>
          )}
        </div>
        <div className="grid grid-cols-3 md:grid-cols-7 gap-3 text-xs">
          <div><p className="text-slate-500">Daily Loss</p><p className="text-red-400 font-mono">-{schSettings.max_daily_loss_pct || 3}%</p></div>
          <div><p className="text-slate-500">Drawdown</p><p className="text-red-400 font-mono">-{schSettings.max_portfolio_drawdown_pct || 10}%</p></div>
          <div><p className="text-slate-500">DT Conf</p><p className="text-amber-400 font-mono">{dynThresh.dt_threshold || schSettings.min_confidence_day || 80}</p></div>
          <div><p className="text-slate-500">LT Conf</p><p className="text-blue-400 font-mono">{dynThresh.lt_threshold || schSettings.min_confidence_long || 75}</p></div>
          <div><p className="text-slate-500">Cooldown</p><p className="text-slate-300 font-mono">{schSettings.max_consecutive_losses || 2} losses/{schSettings.cooldown_minutes || 30}m</p></div>
          <div><p className="text-slate-500">Losses</p><p className={`font-mono ${sch.consecutive_losses >= 2 ? 'text-red-400' : 'text-slate-300'}`}>{sch.consecutive_losses || 0}</p></div>
          <div><p className="text-slate-500">Loss Used</p><p className={`font-mono ${(sch.daily_loss_pct_of_max || 0) >= 60 ? 'text-red-400' : 'text-slate-300'}`}>{sch.daily_loss_pct_of_max || 0}%</p></div>
        </div>
      </Card>

      {/* Last Execution Summary */}
      {sch.last_cycle_result && (
        <Card className="terminal-card p-3" data-testid="last-execution-summary">
          <div className="flex items-center gap-2 mb-2">
            <MonitorCheck className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-slate-400">Last Execution</span>
            <Badge variant="outline" className={`text-[10px] ${sch.last_cycle_result.engine === 'day_trade' ? 'border-amber-500/30 text-amber-400' : 'border-blue-500/30 text-blue-400'}`}>
              {sch.last_cycle_result.engine === 'day_trade' ? 'Day Trade' : 'Long Term'}
            </Badge>
            {sch.last_cycle_result.risk_mode && <RiskModeBadge mode={sch.last_cycle_result.risk_mode} />}
            {sch.last_cycle_result.opportunity_quality && <OpportunityBadge quality={sch.last_cycle_result.opportunity_quality} />}
          </div>
          <div className="grid grid-cols-5 gap-3 text-xs">
            <div><p className="text-slate-500">Candidates</p><p className="text-white font-mono">{sch.last_cycle_result.candidates}</p></div>
            <div><p className="text-slate-500">Executed</p><p className="text-emerald-400 font-mono">{sch.last_cycle_result.executed}</p></div>
            <div><p className="text-slate-500">Skipped</p><p className="text-slate-400 font-mono">{sch.last_cycle_result.skipped}</p></div>
            <div><p className="text-slate-500">Session</p><p className="text-white capitalize">{sch.last_cycle_result.session?.replace("_", " ")}</p></div>
            <div><p className="text-slate-500">Threshold</p><p className="text-white font-mono">{sch.last_cycle_result.threshold_used}</p></div>
          </div>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => {
        setActiveTab(v);
        if (v === "notifications") fetchNotifications();
        if (v === "history") fetchHistory();
        if (v === "trade-log") fetchTradeLog();
      }}>
        <TabsList className="w-full justify-start bg-slate-900 border border-slate-800 p-1 h-auto flex-wrap">
          <TabsTrigger value="scheduler" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-400"><Timer className="w-4 h-4 mr-1" /> Scheduler</TabsTrigger>
          <TabsTrigger value="diagnostics" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400"><Filter className="w-4 h-4 mr-1" /> Diagnostics</TabsTrigger>
          <TabsTrigger value="candidates" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400"><Eye className="w-4 h-4 mr-1" /> Candidates</TabsTrigger>
          <TabsTrigger value="day-trades" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400"><Zap className="w-4 h-4 mr-1" /> Day ({opportunities?.day_trades?.length || 0})</TabsTrigger>
          <TabsTrigger value="long-term" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400"><TrendingUp className="w-4 h-4 mr-1" /> Long ({opportunities?.long_term?.length || 0})</TabsTrigger>
          <TabsTrigger value="mtf-heatmap" className="data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400"><Grid3x3 className="w-4 h-4 mr-1" /> MTF Heatmap</TabsTrigger>
          <TabsTrigger value="trade-log" className="data-[state=active]:bg-teal-500/20 data-[state=active]:text-teal-400"><Database className="w-4 h-4 mr-1" /> Trade Log</TabsTrigger>
          <TabsTrigger value="notifications" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400"><Bell className="w-4 h-4 mr-1" /> Alerts</TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400"><Activity className="w-4 h-4 mr-1" /> History</TabsTrigger>
          <TabsTrigger value="settings" className="data-[state=active]:bg-slate-500/20 data-[state=active]:text-white"><Settings className="w-4 h-4 mr-1" /> Config</TabsTrigger>
        </TabsList>

        {/* SCHEDULER TAB */}
        <TabsContent value="scheduler" className="space-y-4">
          {/* Deploy Stages */}
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-white font-medium flex items-center gap-2 mb-3"><Gauge className="w-4 h-4 text-blue-400" /> Deployment Stage</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { mode: "paper", label: "Paper Trading", desc: "Simulated orders", icon: MonitorCheck },
                { mode: "shadow", label: "Shadow Mode", desc: "Recommend only", icon: Eye },
                { mode: "limited_live", label: "Limited Live", desc: "Small positions", icon: Shield },
                { mode: "full_live", label: "Full Live", desc: "Full execution", icon: Zap },
              ].map(({ mode, label, desc, icon: Icon }) => {
                const active = sch.deployment_mode === mode;
                return (
                  <button key={mode} onClick={() => setDeployMode(mode)} data-testid={`deploy-${mode}`}
                    className={`p-3 rounded-lg border text-left transition-all ${active ? 'bg-blue-500/10 border-blue-500/40' : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={`w-4 h-4 ${active ? 'text-blue-400' : 'text-slate-500'}`} />
                      <span className={`text-xs font-medium ${active ? 'text-white' : 'text-slate-400'}`}>{label}</span>
                    </div>
                    <p className="text-[10px] text-slate-500">{desc}</p>
                    {active && <div className="w-full h-0.5 bg-blue-500 rounded mt-2" />}
                  </button>
                );
              })}
            </div>
          </Card>
          {/* Intervals */}
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-white font-medium mb-3 flex items-center gap-2"><Timer className="w-4 h-4 text-emerald-400" /> Scan Intervals</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div><label className="text-xs text-slate-500 block mb-1">DT: every {Math.floor((schSettings.dt_interval_seconds || 300) / 60)} min</label>
                <Slider value={[(schSettings.dt_interval_seconds || 300) / 60]} min={1} max={30} step={1} onValueChange={([v]) => updateSchedulerSetting("dt_interval_seconds", v * 60)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">LT: every {Math.floor((schSettings.lt_interval_seconds || 1800) / 60)} min</label>
                <Slider value={[(schSettings.lt_interval_seconds || 1800) / 60]} min={10} max={120} step={5} onValueChange={([v]) => updateSchedulerSetting("lt_interval_seconds", v * 60)} /></div>
            </div>
          </Card>
          {/* Session Rules */}
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-white font-medium mb-3 flex items-center gap-2"><Clock className="w-4 h-4 text-amber-400" /> Market Session Rules</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between"><div><p className="text-xs text-slate-300">Pre-Market Execution</p><p className="text-[10px] text-slate-500">Disabled by default for safety</p></div>
                <Switch checked={schSettings.pre_market_execution || false} onCheckedChange={(v) => updateSchedulerSetting("pre_market_execution", v)} /></div>
              <div className="flex items-center justify-between"><div><p className="text-xs text-slate-300">After-Hours Execution</p><p className="text-[10px] text-slate-500">Disabled by default for safety</p></div>
                <Switch checked={schSettings.after_hours_execution || false} onCheckedChange={(v) => updateSchedulerSetting("after_hours_execution", v)} /></div>
            </div>
          </Card>
          {/* Safety Controls */}
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-red-400 font-medium mb-3 flex items-center gap-2"><Shield className="w-4 h-4" /> Safety Controls</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div><label className="text-xs text-slate-500 block mb-1">Max Daily Loss: {schSettings.max_daily_loss_pct || 3}%</label>
                <Slider value={[schSettings.max_daily_loss_pct || 3]} min={1} max={10} step={0.5} onValueChange={([v]) => updateSchedulerSetting("max_daily_loss_pct", v)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">Max Drawdown: {schSettings.max_portfolio_drawdown_pct || 10}%</label>
                <Slider value={[schSettings.max_portfolio_drawdown_pct || 10]} min={3} max={25} step={1} onValueChange={([v]) => updateSchedulerSetting("max_portfolio_drawdown_pct", v)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">Loss Cooldown Trigger: {schSettings.max_consecutive_losses || 2} losses</label>
                <Slider value={[schSettings.max_consecutive_losses || 2]} min={1} max={10} step={1} onValueChange={([v]) => updateSchedulerSetting("max_consecutive_losses", v)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">Cooldown: {schSettings.cooldown_minutes || 30} min</label>
                <Slider value={[schSettings.cooldown_minutes || 30]} min={5} max={120} step={5} onValueChange={([v]) => updateSchedulerSetting("cooldown_minutes", v)} /></div>
            </div>
          </Card>
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-white font-medium mb-3">Manual Actions</h3>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700"><RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Scan Now</Button>
              <Button variant="outline" size="sm" onClick={refreshTA} disabled={refreshingTA} className="border-cyan-800 text-cyan-400 hover:bg-cyan-900/30"><Database className={`w-3 h-3 mr-1 ${refreshingTA ? 'animate-spin' : ''}`} /> Refresh TA Data</Button>
              <Button size="sm" onClick={executeCycle} disabled={executing} className="bg-emerald-600 hover:bg-emerald-500"><Play className={`w-3 h-3 mr-1 ${executing ? 'animate-spin' : ''}`} /> Execute Cycle</Button>
            </div>
          </Card>
        </TabsContent>

        {/* DIAGNOSTICS TAB */}
        <TabsContent value="diagnostics" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-purple-400 flex items-center gap-2"><Filter className="w-4 h-4" /> Trade Pipeline Diagnostics</h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700"><RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Scan</Button>
          </div>
          {/* Pipeline Funnel */}
          <PipelineFunnel funnel={pipelineFunnel} />
          {/* TA Analysis Status */}
          {opportunities?.stats && (
            <Card className="terminal-card p-4">
              <h3 className="text-xs text-cyan-400 mb-3 flex items-center gap-2"><Database className="w-4 h-4" /> Tiered TA Pipeline Diagnostics</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                <div><p className="text-slate-500">T1 Fast Scan</p><p className="text-cyan-400 font-mono text-lg">{opportunities.stats.ta_analyzed || 0}</p><p className="text-slate-600">{opportunities.timing?.tier1_scan_sec || '?'}s</p></div>
                <div><p className="text-slate-500">T1 Passed</p><p className="text-blue-400 font-mono text-lg">{opportunities.stats.tier1_passed || 0}</p></div>
                <div><p className="text-slate-500">T2 Deep</p><p className="text-indigo-400 font-mono text-lg">{opportunities.stats.tier2_deep || 0}</p><p className="text-slate-600">{opportunities.timing?.tier2_scan_sec || '?'}s</p></div>
                <div><p className="text-slate-500">DT Candidates</p><p className="text-amber-400 font-mono text-lg">{opportunities.stats.day_trade_candidates || 0}</p></div>
                <div><p className="text-slate-500">Total Cycle</p><p className="text-emerald-400 font-mono text-lg">{opportunities.timing?.total_cycle_sec || '?'}s</p></div>
              </div>
              {opportunities.timing?.ta_cache && (
                <p className="text-[10px] text-slate-600 mt-2">
                  Cache: {opportunities.timing.ta_cache.hit_rate || 0}% hit rate ({opportunities.timing.ta_cache.hits || 0} hits / {opportunities.timing.ta_cache.misses || 0} misses) | Bar cache: {opportunities.timing.bar_cache?.valid || 0} entries
                </p>
              )}
            </Card>
          )}
          {/* MTF & Momentum Mode Stats */}
          {opportunities?.stats && (
            <Card className="terminal-card p-4" data-testid="mtf-momentum-stats">
              <h3 className="text-xs text-cyan-400 mb-3 flex items-center gap-2"><Layers className="w-4 h-4" /> Multi-Timeframe & Momentum Mode</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                <div>
                  <p className="text-slate-500">MTF Conflicts</p>
                  <p className={`font-mono text-lg ${(opportunities.stats.mtf_conflict_rejections || 0) > 0 ? 'text-red-400' : 'text-slate-500'}`}>
                    {opportunities.stats.mtf_conflict_rejections || 0}
                  </p>
                  <p className="text-[10px] text-slate-600">5m/15m opposing</p>
                </div>
                <div>
                  <p className="text-slate-500">Momentum Eligible</p>
                  <p className="text-orange-400 font-mono text-lg">{opportunities.stats.momentum_mode_candidates || 0}</p>
                  <p className="text-[10px] text-slate-600">RelVol&gt;2 + breakout</p>
                </div>
                <div>
                  <p className="text-slate-500">Momentum Bypassed</p>
                  <p className="text-orange-300 font-mono text-lg">{opportunities.stats.momentum_bypass_active || 0}</p>
                  <p className="text-[10px] text-slate-600">Soft filters bypassed</p>
                </div>
                <div>
                  <p className="text-slate-500">Setups Found</p>
                  <p className="text-blue-400 font-mono text-lg">{opportunities.stats.setups_found || 0}</p>
                </div>
                <div>
                  <p className="text-slate-500">Filters Passed</p>
                  <p className="text-emerald-400 font-mono text-lg">{opportunities.stats.filters_passed || 0}</p>
                </div>
              </div>
              <div className="mt-2 pt-2 border-t border-slate-800">
                <p className="text-[10px] text-slate-600">
                  MTF Rule: LONG requires 5m bullish + 15m supportive | SHORT requires 5m bearish + 15m supportive | 1m = timing only
                </p>
                <p className="text-[10px] text-slate-600">
                  Momentum Mode: RelVol&gt;2.5, breakout/breakdown, strong candle, clear HH/HL or LH/LL, VWAP aligned (&lt;2%), tight spread — bypasses soft filters only
                </p>
              </div>
            </Card>
          )}
          {/* Confidence Distribution + Momentum % */}
          {opportunities?.stats?.confidence_distribution && (
            <Card className="terminal-card p-4" data-testid="confidence-distribution">
              <h3 className="text-xs text-amber-400 mb-3 flex items-center gap-2"><BarChart2 className="w-4 h-4" /> Confidence Score Distribution</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                <div className="text-center p-2 rounded bg-emerald-500/10 border border-emerald-500/20">
                  <p className="text-[10px] text-emerald-400">Elite (85-95)</p>
                  <p className="text-emerald-400 font-mono text-2xl">{opportunities.stats.confidence_distribution.elite_85_95 || 0}</p>
                </div>
                <div className="text-center p-2 rounded bg-blue-500/10 border border-blue-500/20">
                  <p className="text-[10px] text-blue-400">Strong (75-85)</p>
                  <p className="text-blue-400 font-mono text-2xl">{opportunities.stats.confidence_distribution.strong_75_85 || 0}</p>
                </div>
                <div className="text-center p-2 rounded bg-amber-500/10 border border-amber-500/20">
                  <p className="text-[10px] text-amber-400">Acceptable (65-75)</p>
                  <p className="text-amber-400 font-mono text-2xl">{opportunities.stats.confidence_distribution.acceptable_65_75 || 0}</p>
                </div>
                <div className="text-center p-2 rounded bg-red-500/10 border border-red-500/20">
                  <p className="text-[10px] text-red-400">Below 65</p>
                  <p className="text-red-400 font-mono text-2xl">{opportunities.stats.confidence_distribution.below_65 || 0}</p>
                </div>
                <div className="text-center p-2 rounded bg-orange-500/10 border border-orange-500/20">
                  <p className="text-[10px] text-orange-400">Momentum %</p>
                  <p className={`font-mono text-2xl ${(opportunities.stats.momentum_pct || 0) > 30 ? 'text-red-400' : 'text-orange-400'}`}>
                    {opportunities.stats.momentum_pct || 0}%
                  </p>
                  <p className="text-[10px] text-slate-500">target: 10-30%</p>
                </div>
              </div>
            </Card>
          )}
          {/* Market Session */}
          {opportunities?.market_session && (
            <Card className="terminal-card p-3">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-400" />
                <span className="text-xs text-slate-400">Market Session:</span>
                <Badge variant="outline" className={`text-[10px] ${
                  opportunities.market_session === 'regular' ? 'border-emerald-500/30 text-emerald-400' :
                  opportunities.market_session === 'pre_market' ? 'border-amber-500/30 text-amber-400' :
                  opportunities.market_session === 'closing' ? 'border-orange-500/30 text-orange-400' :
                  'border-red-500/30 text-red-400'
                }`}>
                  {opportunities.market_session.replace(/_/g, " ").toUpperCase()}
                </Badge>
                {opportunities.market_session === 'pre_market' && (
                  <span className="text-[10px] text-amber-400">Auto-execution disabled until 9:30 AM ET</span>
                )}
              </div>
            </Card>
          )}
          {/* No Trade Panel */}
          <NoTradePanel summary={noTradeSummary} />
          {/* Dynamic Thresholds */}
          {dynThresh.dt_threshold && (
            <Card className="terminal-card p-4">
              <h3 className="text-xs text-slate-400 mb-2">Dynamic Threshold Adjustments</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                <div><p className="text-slate-500">DT Threshold</p><p className="text-amber-400 font-mono text-lg">{dynThresh.dt_threshold}</p></div>
                <div><p className="text-slate-500">LT Threshold</p><p className="text-blue-400 font-mono text-lg">{dynThresh.lt_threshold}</p></div>
                <div><p className="text-slate-500">Risk Mode</p><RiskModeBadge mode={dynThresh.risk_mode} /></div>
                <div><p className="text-slate-500">Regime Adj.</p><p className="text-white capitalize">{dynThresh.regime_adjustment?.replace("_", " ")}</p></div>
                <div><p className="text-slate-500">Post-Cooldown</p><p className={dynThresh.post_cooldown_active ? 'text-amber-400' : 'text-slate-500'}>{dynThresh.post_cooldown_active ? 'ACTIVE (+5)' : 'No'}</p></div>
              </div>
            </Card>
          )}
          {/* Opportunity Quality */}
          {noTradeSummary && (
            <Card className="terminal-card p-4">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Opportunity Quality:</span>
                <OpportunityBadge quality={noTradeSummary.opportunity_quality} />
                <span className="text-xs text-slate-500">({noTradeSummary.dt_candidates} DT, {noTradeSummary.lt_candidates} LT candidates)</span>
              </div>
            </Card>
          )}
        </TabsContent>

        {/* CANDIDATES TAB */}
        <TabsContent value="candidates" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-slate-400">AI Classification Summary</h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700"><RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Scan</Button>
          </div>
          {opportunities?.stats && (
            <Card className="terminal-card p-4">
              <div className="grid grid-cols-3 md:grid-cols-9 gap-3 text-center">
                <div><p className="text-2xl font-mono text-white">{opportunities.stats.total_scanned}</p><p className="text-[10px] text-slate-500">Scanned</p></div>
                <div><p className="text-2xl font-mono text-cyan-400">{opportunities.stats.ta_analyzed || 0}</p><p className="text-[10px] text-slate-500">T1 Analyzed</p></div>
                <div><p className="text-2xl font-mono text-indigo-400">{opportunities.stats.tier2_deep || 0}</p><p className="text-[10px] text-slate-500">T2 Deep</p></div>
                <div><p className="text-2xl font-mono text-blue-400">{opportunities.stats.setups_found || 0}</p><p className="text-[10px] text-slate-500">Setups</p></div>
                <div><p className={`text-2xl font-mono ${(opportunities.stats.mtf_conflict_rejections || 0) > 0 ? 'text-red-400' : 'text-slate-500'}`}>{opportunities.stats.mtf_conflict_rejections || 0}</p><p className="text-[10px] text-slate-500">MTF Conflicts</p></div>
                <div><p className="text-2xl font-mono text-orange-400">{opportunities.stats.momentum_mode_candidates || 0}</p><p className="text-[10px] text-slate-500">Momentum</p></div>
                <div><p className="text-2xl font-mono text-amber-400">{opportunities.stats.day_trade_candidates}</p><p className="text-[10px] text-slate-500">Day Trades</p></div>
                <div><p className="text-2xl font-mono text-slate-400">{opportunities.stats.watchlist}</p><p className="text-[10px] text-slate-500">Watchlist</p></div>
                <div><p className="text-2xl font-mono text-red-400">{opportunities.stats.rejected}</p><p className="text-[10px] text-slate-500">Rejected</p></div>
              </div>
            </Card>
          )}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-xs text-amber-400 mb-2 flex items-center gap-1"><Zap className="w-3 h-3" /> Top Day Trades</h3>
              <div className="space-y-2">
                {(opportunities?.day_trades || []).slice(0, 5).map((item) => (
                  <ExplanationCard key={item.symbol} item={item} expanded={expandedCard === `dt-${item.symbol}`}
                    onToggle={() => setExpandedCard(expandedCard === `dt-${item.symbol}` ? null : `dt-${item.symbol}`)} />
                ))}
                {!opportunities?.day_trades?.length && <p className="text-xs text-slate-500 py-4 text-center">No day trade candidates</p>}
              </div>
            </div>
            <div>
              <h3 className="text-xs text-blue-400 mb-2 flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Top Long-Term</h3>
              <div className="space-y-2">
                {(opportunities?.long_term || []).slice(0, 5).map((item) => (
                  <ExplanationCard key={item.symbol} item={item} expanded={expandedCard === `lt-${item.symbol}`}
                    onToggle={() => setExpandedCard(expandedCard === `lt-${item.symbol}` ? null : `lt-${item.symbol}`)} />
                ))}
                {!opportunities?.long_term?.length && <p className="text-xs text-slate-500 py-4 text-center">No long-term candidates</p>}
              </div>
            </div>
          </div>
        </TabsContent>

        {/* DAY TRADES TAB */}
        <TabsContent value="day-trades" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-amber-400 flex items-center gap-1"><Zap className="w-4 h-4" /> Day Trading ({opportunities?.day_trades?.length || 0})</h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700"><RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Refresh</Button>
          </div>
          {(opportunities?.day_trades || []).map((item) => (
            <ExplanationCard key={item.symbol} item={item} expanded={expandedCard === `dtf-${item.symbol}`}
              onToggle={() => setExpandedCard(expandedCard === `dtf-${item.symbol}` ? null : `dtf-${item.symbol}`)} />
          ))}
          {!opportunities?.day_trades?.length && <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No candidates — click "Refresh TA Data" first, then "Scan Now"</Card>}
          {/* Rejected DT Near-Misses */}
          {(() => {
            const dtRejected = (opportunities?.rejected_details || []).filter(r => r.classification === "DAY_TRADE");
            if (dtRejected.length === 0) return null;
            return (
              <div className="mt-4">
                <h3 className="text-xs text-red-400/70 mb-2 flex items-center gap-1"><TriangleAlert className="w-3 h-3" /> Rejected / Near-Miss DT ({dtRejected.length})</h3>
                <div className="space-y-2">
                  {dtRejected.slice(0, 10).map((item) => (
                    <ExplanationCard key={`rej-${item.symbol}`} item={item} expanded={expandedCard === `rejdt-${item.symbol}`}
                      onToggle={() => setExpandedCard(expandedCard === `rejdt-${item.symbol}` ? null : `rejdt-${item.symbol}`)} />
                  ))}
                </div>
              </div>
            );
          })()}
        </TabsContent>

        {/* LONG TERM TAB */}
        <TabsContent value="long-term" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-blue-400 flex items-center gap-1"><TrendingUp className="w-4 h-4" /> Long-Term ({opportunities?.long_term?.length || 0})</h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700"><RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Refresh</Button>
          </div>
          {(opportunities?.long_term || []).map((item) => (
            <ExplanationCard key={item.symbol} item={item} expanded={expandedCard === `ltf-${item.symbol}`}
              onToggle={() => setExpandedCard(expandedCard === `ltf-${item.symbol}` ? null : `ltf-${item.symbol}`)} />
          ))}
          {!opportunities?.long_term?.length && <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No candidates</Card>}
        </TabsContent>

        {/* MTF HEATMAP TAB */}
        <TabsContent value="mtf-heatmap" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-cyan-400 flex items-center gap-1"><Grid3x3 className="w-4 h-4" /> MTF Heatmap — Multi-Timeframe Structure Grid</h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700"><RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Refresh</Button>
          </div>
          <MTFHeatmap heatmap={opportunities?.mtf_heatmap} distribution={opportunities?.mtf_heatmap_distribution} />
        </TabsContent>

        {/* TRADE LOG TAB */}
        <TabsContent value="trade-log" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-teal-400 flex items-center gap-1"><Database className="w-4 h-4" /> Trade Log (Full Lifecycle)</h2>
            <Button variant="outline" size="sm" onClick={fetchTradeLog} className="border-slate-700"><RefreshCw className="w-3 h-3 mr-1" /> Refresh</Button>
          </div>
          {tradeLog.length > 0 ? tradeLog.map((t, i) => (
            <Card key={i} className={`terminal-card p-4 border ${t.status === "OPEN" ? "border-emerald-500/20" : t.pnl_dollars >= 0 ? "border-blue-500/20" : "border-red-500/20"}`} data-testid={`trade-log-${i}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-white font-bold text-sm">{t.symbol}</span>
                  <Badge variant="outline" className={`text-[10px] ${t.direction === "LONG" ? "border-emerald-500/30 text-emerald-400" : "border-red-500/30 text-red-400"}`}>
                    {t.direction}
                  </Badge>
                  <Badge variant="outline" className={`text-[10px] ${t.action === "BUY" ? "border-emerald-500/30 text-emerald-400" : "border-red-500/30 text-red-400"}`}>
                    {t.action}
                  </Badge>
                  <Badge variant="outline" className={`text-[10px] ${t.status === "OPEN" ? "border-amber-500/30 text-amber-400" : "border-slate-700 text-slate-400"}`}>
                    {t.status}
                  </Badge>
                  {t.momentum_mode && <Badge variant="outline" className="text-[10px] border-orange-500/30 text-orange-400">MOMENTUM</Badge>}
                  {t.mtf_aligned && <Badge variant="outline" className="text-[10px] border-cyan-500/30 text-cyan-400">MTF OK</Badge>}
                </div>
                <span className="text-xs text-slate-500">{t.opened_at ? new Date(t.opened_at).toLocaleString() : ""}</span>
              </div>
              <div className="grid grid-cols-3 md:grid-cols-7 gap-2 text-xs">
                <div><p className="text-slate-500">Entry</p><p className="text-white font-mono">${t.entry_price}</p></div>
                <div><p className="text-slate-500">SL</p><p className="text-red-400 font-mono">${t.stop_loss}</p></div>
                <div><p className="text-slate-500">TP</p><p className="text-emerald-400 font-mono">${t.take_profit}</p></div>
                <div><p className="text-slate-500">Setup</p><p className="text-blue-400">{t.setup_type || "?"}</p></div>
                <div><p className="text-slate-500">Conf</p><p className="text-amber-400 font-mono">{t.confidence_score}</p></div>
                <div><p className="text-slate-500">R:R</p><p className="text-white font-mono">{t.rr_ratio}:1</p></div>
                <div>
                  <p className="text-slate-500">P&L</p>
                  <p className={`font-mono ${t.pnl_dollars == null ? "text-slate-500" : t.pnl_dollars >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {t.pnl_dollars != null ? `$${t.pnl_dollars} (${t.pnl_percent}%)` : "—"}
                  </p>
                </div>
              </div>
              {t.entry_reasons?.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-800">
                  <p className="text-[10px] text-emerald-400 mb-1">Entry Reasons:</p>
                  <p className="text-[10px] text-slate-400">{t.entry_reasons.slice(0, 4).join(" | ")}</p>
                </div>
              )}
              {t.exit_reasons?.length > 0 && (
                <div className="mt-1">
                  <p className="text-[10px] text-red-400">Exit: {t.exit_reasons.join(", ")}</p>
                </div>
              )}
            </Card>
          )) : (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">
              No trade logs yet. Trades will appear here once the system executes orders.
            </Card>
          )}
        </TabsContent>

        {/* NOTIFICATIONS TAB */}
        <TabsContent value="notifications" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-amber-400 flex items-center gap-1"><Bell className="w-4 h-4" /> Trade Notifications</h2>
            <Button variant="outline" size="sm" onClick={fetchNotifications} className="border-slate-700"><RefreshCw className="w-3 h-3 mr-1" /> Refresh</Button>
          </div>
          {notifications.length > 0 ? notifications.map((n, i) => {
            const cls = { critical: "border-red-500/30 bg-red-500/5", warning: "border-amber-500/30 bg-amber-500/5", info: "border-slate-700 bg-slate-900/50" };
            const ico = { critical: <CircleStop className="w-4 h-4 text-red-400" />, warning: <AlertTriangle className="w-4 h-4 text-amber-400" />, info: <Bell className="w-4 h-4 text-blue-400" /> };
            return (
              <Card key={i} className={`p-3 border ${cls[n.severity] || cls.info}`}>
                <div className="flex items-start gap-2">
                  {ico[n.severity] || ico.info}
                  <div className="flex-1"><p className="text-xs text-white">{n.message}</p><p className="text-[10px] text-slate-500">{new Date(n.timestamp).toLocaleString()}</p></div>
                  <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-500">{n.event}</Badge>
                </div>
              </Card>
            );
          }) : <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No notifications yet</Card>}
        </TabsContent>

        {/* HISTORY TAB */}
        <TabsContent value="history" className="space-y-3">
          <h2 className="text-sm text-purple-400 flex items-center gap-1"><Activity className="w-4 h-4" /> Trade History</h2>
          {history.length > 0 ? history.map((trade, i) => (
            <Card key={i} className="terminal-card p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className={`text-[10px] ${trade.action === "BUY" ? 'border-emerald-500/30 text-emerald-400' : 'border-red-500/30 text-red-400'}`}>{trade.action}</Badge>
                  <span className="text-white font-medium">{trade.symbol}</span>
                  <span className="text-xs text-slate-500">{trade.shares} shares</span>
                </div>
                <div className="text-right">
                  {trade.pnl !== undefined && trade.pnl !== null && (
                    <p className={`text-sm font-mono ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}</p>
                  )}
                  <p className="text-[10px] text-slate-600">{new Date(trade.timestamp).toLocaleString()}</p>
                </div>
              </div>
            </Card>
          )) : <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No trade history yet</Card>}
        </TabsContent>

        {/* SETTINGS TAB */}
        <TabsContent value="settings" className="space-y-4">
          <h2 className="text-sm text-slate-300">Engine Configuration</h2>
          <Card className="terminal-card p-4">
            <div className="flex items-center justify-between mb-4"><h3 className="text-sm text-amber-400 flex items-center gap-1"><Zap className="w-4 h-4" /> Day Trading</h3><Switch checked={s.dt_enabled} onCheckedChange={(v) => updateSetting("dt_enabled", v)} /></div>
            <div className="grid md:grid-cols-2 gap-4">
              <div><label className="text-xs text-slate-500 block mb-1">Confidence: {s.dt_confidence_threshold}</label><Slider value={[s.dt_confidence_threshold || 80]} min={50} max={95} step={5} onValueChange={([v]) => updateSetting("dt_confidence_threshold", v)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">Risk/Trade: {((s.dt_risk_per_trade_pct || 0.04) * 100).toFixed(0)}%</label><Slider value={[(s.dt_risk_per_trade_pct || 0.04) * 100]} min={1} max={10} step={1} onValueChange={([v]) => updateSetting("dt_risk_per_trade_pct", v / 100)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">Max Positions: {s.dt_max_positions}</label><Slider value={[s.dt_max_positions || 6]} min={1} max={15} step={1} onValueChange={([v]) => updateSetting("dt_max_positions", v)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">TP: {s.dt_take_profit_pct}%</label><Slider value={[s.dt_take_profit_pct || 2.5]} min={0.5} max={10} step={0.5} onValueChange={([v]) => updateSetting("dt_take_profit_pct", v)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">SL: {s.dt_stop_loss_pct}%</label><Slider value={[s.dt_stop_loss_pct || 0.8]} min={0.3} max={5} step={0.1} onValueChange={([v]) => updateSetting("dt_stop_loss_pct", v)} /></div>
            </div>
          </Card>
          <Card className="terminal-card p-4">
            <div className="flex items-center justify-between mb-4"><h3 className="text-sm text-blue-400 flex items-center gap-1"><TrendingUp className="w-4 h-4" /> Long-Term</h3><Switch checked={s.lt_enabled} onCheckedChange={(v) => updateSetting("lt_enabled", v)} /></div>
            <div className="grid md:grid-cols-2 gap-4">
              <div><label className="text-xs text-slate-500 block mb-1">Confidence: {s.lt_confidence_threshold}</label><Slider value={[s.lt_confidence_threshold || 75]} min={50} max={95} step={5} onValueChange={([v]) => updateSetting("lt_confidence_threshold", v)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">Max Position: {((s.lt_max_position_pct || 0.15) * 100).toFixed(0)}%</label><Slider value={[(s.lt_max_position_pct || 0.15) * 100]} min={5} max={25} step={1} onValueChange={([v]) => updateSetting("lt_max_position_pct", v / 100)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">Max Positions: {s.lt_max_positions}</label><Slider value={[s.lt_max_positions || 8]} min={1} max={20} step={1} onValueChange={([v]) => updateSetting("lt_max_positions", v)} /></div>
              <div><label className="text-xs text-slate-500 block mb-1">Trailing Stop: {s.lt_trailing_stop_pct}%</label><Slider value={[s.lt_trailing_stop_pct || 15]} min={5} max={30} step={1} onValueChange={([v]) => updateSetting("lt_trailing_stop_pct", v)} /></div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AutoTrade;
