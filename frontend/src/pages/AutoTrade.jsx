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
  CircleStop, Radio, MonitorCheck, Gauge, ShieldAlert
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
  return (
    <Badge variant="outline" className={`text-[10px] font-bold ${c.cls}`} data-testid="deploy-mode-badge">
      {c.label}
    </Badge>
  );
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

const ExplanationCard = ({ item, expanded, onToggle }) => {
  const exp = item.explanation || {};
  const isDay = item.classification === "DAY_TRADE";
  const signal = item.signal || {};
  return (
    <Card className="terminal-card overflow-hidden" data-testid={`candidate-${item.symbol}`}>
      <div className="p-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isDay ? 'bg-amber-500/20' : 'bg-blue-500/20'}`}>
              {isDay ? <Zap className="w-5 h-5 text-amber-400" /> : <TrendingUp className="w-5 h-5 text-blue-400" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-white font-bold">{item.symbol}</span>
                <Badge variant="outline" className={`text-[10px] ${isDay ? 'border-amber-500/30 text-amber-400' : 'border-blue-500/30 text-blue-400'}`}>
                  {isDay ? "DAY TRADE" : "LONG TERM"}
                </Badge>
                <Badge variant="outline" className={`text-[10px] ${
                  item.action === "BUY" ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10' :
                  item.action === "WATCHLIST" ? 'border-amber-500/30 text-amber-400' :
                  'border-red-500/30 text-red-400'
                }`}>{item.action}</Badge>
              </div>
              <p className="text-xs text-slate-500">{signal.name || signal.company_name || ""}</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-white font-mono">${(signal.price || signal.entry || 0).toFixed(2)}</p>
              <p className="text-xs text-slate-500">Conf: <span className={`font-bold ${
                item.confidence >= 80 ? 'text-emerald-400' : item.confidence >= 60 ? 'text-amber-400' : 'text-red-400'
              }`}>{item.confidence}/100</span></p>
            </div>
            {expanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
          </div>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-800 pt-3">
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
                {exp.exit_plan.take_profit && <div><p className="text-slate-500">TP</p><p className="text-emerald-400 font-mono">${exp.exit_plan.take_profit} ({exp.exit_plan.take_profit_pct > 0 ? '+' : ''}{exp.exit_plan.take_profit_pct}%)</p></div>}
                {exp.exit_plan.stop_loss && <div><p className="text-slate-500">SL</p><p className="text-red-400 font-mono">${exp.exit_plan.stop_loss} ({exp.exit_plan.stop_loss_pct}%)</p></div>}
                {exp.exit_plan.time_exit && <div><p className="text-slate-500">Time</p><p className="text-slate-300">{exp.exit_plan.time_exit}</p></div>}
              </div>
            </div>
          )}
          {exp.key_indicators && (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs">
              {Object.entries(exp.key_indicators).filter(([, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => (
                <div key={k} className="text-center p-1.5 rounded bg-slate-800/50">
                  <p className="text-[10px] text-slate-500">{k.replace(/_/g, " ")}</p>
                  <p className="text-white font-mono text-[11px]">{typeof v === "number" ? v.toFixed(1) : v}</p>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-4 text-xs text-slate-500">
            <span>DT Score: <span className="text-amber-400 font-mono">{item.dt_score}</span></span>
            <span>LT Score: <span className="text-blue-400 font-mono">{item.lt_score}</span></span>
          </div>
        </div>
      )}
    </Card>
  );
};

const AutoTrade = () => {
  const [status, setStatus] = useState(null);
  const [scheduler, setScheduler] = useState(null);
  const [opportunities, setOpportunities] = useState(null);
  const [history, setHistory] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [execLog, setExecLog] = useState([]);
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

  const fetchExecLog = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/scheduler/execution-log?limit=30`, { headers });
      if (resp.ok) setExecLog(await resp.json());
    } catch (e) { console.error(e); }
  }, [token]);

  useEffect(() => {
    Promise.all([fetchStatus(), fetchScheduler(), fetchOpportunities(), fetchHistory()]).finally(() => setLoading(false));
    const interval = setInterval(() => { fetchScheduler(); fetchStatus(); }, 15000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchScheduler, fetchOpportunities, fetchHistory]);

  // Countdown timer
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
      if (resp.ok) {
        const d = await resp.json();
        toast.success(`Scheduler started (${d.deployment_mode} mode)`);
        fetchScheduler();
      } else {
        const d = await resp.json();
        toast.error(d.message || "Failed to start");
      }
    } catch (e) { toast.error("Start failed"); }
  };

  const stopScheduler = async () => {
    try {
      const resp = await fetch(`${API}/scheduler/stop`, { method: "POST", headers });
      if (resp.ok) { toast.success("Scheduler stopped"); fetchScheduler(); }
    } catch (e) { toast.error("Stop failed"); }
  };

  const emergencyStop = async () => {
    try {
      const resp = await fetch(`${API}/scheduler/emergency-stop`, { method: "POST", headers });
      if (resp.ok) { toast.error("EMERGENCY STOP ACTIVATED"); fetchScheduler(); fetchStatus(); }
    } catch (e) { toast.error("Emergency stop failed"); }
  };

  const clearEmergency = async () => {
    try {
      const resp = await fetch(`${API}/scheduler/clear-emergency`, { method: "POST", headers });
      if (resp.ok) { toast.success("Emergency cleared"); fetchScheduler(); fetchStatus(); }
    } catch (e) { toast.error("Clear failed"); }
  };

  const setDeployMode = async (mode) => {
    try {
      const resp = await fetch(`${API}/scheduler/deploy-mode?mode=${mode}`, { method: "POST", headers });
      const d = await resp.json();
      if (d.error) { toast.error(d.error); } else { toast.success(`Mode: ${d.deployment_mode}`); fetchScheduler(); }
    } catch (e) { toast.error("Mode change failed"); }
  };

  const executeCycle = async () => {
    setExecuting(true);
    try {
      const resp = await fetch(`${API}/auto-trade/execute-cycle`, { method: "POST", headers });
      if (resp.ok) {
        toast.success("Cycle executing...");
        setTimeout(() => { fetchStatus(); fetchHistory(); fetchExecLog(); }, 5000);
      }
    } catch (e) { toast.error("Execution failed"); }
    setExecuting(false);
  };

  const updateSetting = async (key, value) => {
    try {
      await fetch(`${API}/auto-trade/settings`, {
        method: "POST", headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value })
      });
      fetchStatus();
    } catch (e) { console.error(e); }
  };

  const updateSchedulerSetting = async (key, value) => {
    try {
      await fetch(`${API}/scheduler/settings`, {
        method: "POST", headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value })
      });
      fetchScheduler();
    } catch (e) { console.error(e); }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96"><Loader2 className="w-8 h-8 text-blue-500 animate-spin" /></div>;
  }

  const s = status?.settings || {};
  const regime = status?.market_regime || {};
  const today = status?.today || {};
  const sch = scheduler || {};
  const schSettings = sch.settings || {};

  return (
    <div className="space-y-6 max-w-7xl mx-auto" data-testid="auto-trade-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Brain className="w-6 h-6 text-blue-400" />
            <h1 className="font-display text-2xl font-bold text-white">AI Auto-Trade</h1>
            <DeployBadge mode={sch.deployment_mode} />
            <RegimeBadge regime={regime} />
          </div>
          <p className="text-sm text-slate-500">Safety-first autonomous trading with dual engines</p>
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

      {/* Pause Reason Banner */}
      {sch.pause_reason && (
        <Card className="p-3 border-amber-500/30 bg-amber-500/5" data-testid="pause-banner">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <p className="text-sm text-amber-400">{sch.pause_reason}</p>
          </div>
        </Card>
      )}

      {/* Scheduler Dashboard Strip */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <Card className="terminal-card p-3 text-center">
          <CountdownTimer seconds={dtCountdown} label="Next DT Scan" />
        </Card>
        <Card className="terminal-card p-3 text-center">
          <CountdownTimer seconds={ltCountdown} label="Next LT Scan" />
        </Card>
        <Card className="terminal-card p-3 text-center">
          <SessionBadge session={sch.market_session} />
          <p className="text-[10px] text-slate-500 mt-1">Risk: {sch.risk_multiplier ? `${(sch.risk_multiplier * 100).toFixed(0)}%` : '--'}</p>
        </Card>
        <Card className="terminal-card p-3 text-center">
          <p className="text-xl font-mono text-white">{sch.cycle_count || 0}</p>
          <p className="text-[10px] text-slate-500">Cycles Run</p>
        </Card>
        <Card className="terminal-card p-3 text-center">
          <p className={`text-xl font-mono ${today.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {today.pnl >= 0 ? '+' : ''}${today.pnl?.toFixed(2) || '0.00'}
          </p>
          <p className="text-[10px] text-slate-500">Today P&L</p>
        </Card>
        <Card className="terminal-card p-3 text-center">
          <p className="text-xl font-mono text-white">{status?.positions || 0}</p>
          <p className="text-[10px] text-slate-500">Open Positions</p>
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
          {sch.api_failure_count > 0 && (
            <Badge variant="outline" className="text-[10px] border-red-500/30 text-red-400">
              API Fails: {sch.api_failure_count}
            </Badge>
          )}
        </div>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3 text-xs">
          <div><p className="text-slate-500">Max Daily Loss</p><p className="text-red-400 font-mono">-{schSettings.max_daily_loss_pct || 3}%</p></div>
          <div><p className="text-slate-500">Max Drawdown</p><p className="text-red-400 font-mono">-{schSettings.max_portfolio_drawdown_pct || 10}%</p></div>
          <div><p className="text-slate-500">DT Confidence</p><p className="text-amber-400 font-mono">{schSettings.min_confidence_day || 60}</p></div>
          <div><p className="text-slate-500">LT Confidence</p><p className="text-blue-400 font-mono">{schSettings.min_confidence_long || 55}</p></div>
          <div><p className="text-slate-500">Loss Cooldown</p><p className="text-slate-300 font-mono">{schSettings.max_consecutive_losses || 3} losses / {schSettings.cooldown_minutes || 30}m</p></div>
          <div><p className="text-slate-500">Consec Losses</p><p className={`font-mono ${sch.consecutive_losses >= 2 ? 'text-red-400' : 'text-slate-300'}`}>{sch.consecutive_losses || 0}</p></div>
        </div>
      </Card>

      {/* Last Execution Summary */}
      {sch.last_cycle_result && (
        <Card className="terminal-card p-3" data-testid="last-execution-summary">
          <div className="flex items-center gap-2 mb-2">
            <MonitorCheck className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-slate-400">Last Execution</span>
            <Badge variant="outline" className={`text-[10px] ${
              sch.last_cycle_result.engine === 'day_trade' ? 'border-amber-500/30 text-amber-400' : 'border-blue-500/30 text-blue-400'
            }`}>{sch.last_cycle_result.engine === 'day_trade' ? 'Day Trade' : 'Long Term'}</Badge>
          </div>
          <div className="grid grid-cols-4 gap-3 text-xs">
            <div><p className="text-slate-500">Candidates</p><p className="text-white font-mono">{sch.last_cycle_result.candidates}</p></div>
            <div><p className="text-slate-500">Executed</p><p className="text-emerald-400 font-mono">{sch.last_cycle_result.executed}</p></div>
            <div><p className="text-slate-500">Skipped</p><p className="text-slate-400 font-mono">{sch.last_cycle_result.skipped}</p></div>
            <div><p className="text-slate-500">Session</p><p className="text-white capitalize">{sch.last_cycle_result.session?.replace("_", " ")}</p></div>
          </div>
        </Card>
      )}

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => {
        setActiveTab(v);
        if (v === "notifications") fetchNotifications();
        if (v === "exec-log") fetchExecLog();
        if (v === "history") fetchHistory();
      }}>
        <TabsList className="w-full justify-start bg-slate-900 border border-slate-800 p-1 h-auto flex-wrap">
          <TabsTrigger value="scheduler" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-400">
            <Timer className="w-4 h-4 mr-1" /> Scheduler
          </TabsTrigger>
          <TabsTrigger value="overview" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <Eye className="w-4 h-4 mr-1" /> Candidates
          </TabsTrigger>
          <TabsTrigger value="day-trades" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400">
            <Zap className="w-4 h-4 mr-1" /> Day ({opportunities?.day_trades?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="long-term" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <TrendingUp className="w-4 h-4 mr-1" /> Long ({opportunities?.long_term?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="notifications" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400">
            <Bell className="w-4 h-4 mr-1" /> Alerts
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400">
            <Activity className="w-4 h-4 mr-1" /> History
          </TabsTrigger>
          <TabsTrigger value="settings" className="data-[state=active]:bg-slate-500/20 data-[state=active]:text-white">
            <Settings className="w-4 h-4 mr-1" /> Config
          </TabsTrigger>
        </TabsList>

        {/* SCHEDULER TAB */}
        <TabsContent value="scheduler" className="space-y-4">
          {/* Deployment Mode */}
          <Card className="terminal-card p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm text-white font-medium flex items-center gap-2">
                  <Gauge className="w-4 h-4 text-blue-400" /> Deployment Stage
                </h3>
                <p className="text-xs text-slate-500">Progress through stages before going live</p>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { mode: "paper", label: "Paper Trading", desc: "Simulated orders", icon: MonitorCheck, color: "blue" },
                { mode: "shadow", label: "Shadow Mode", desc: "Recommend only", icon: Eye, color: "purple" },
                { mode: "limited_live", label: "Limited Live", desc: "Small positions", icon: Shield, color: "amber" },
                { mode: "full_live", label: "Full Live", desc: "Full execution", icon: Zap, color: "red" },
              ].map((stage) => {
                const active = sch.deployment_mode === stage.mode;
                const Icon = stage.icon;
                return (
                  <button key={stage.mode} onClick={() => setDeployMode(stage.mode)}
                    data-testid={`deploy-${stage.mode}`}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      active
                        ? `bg-${stage.color}-500/10 border-${stage.color}-500/40`
                        : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                    }`}>
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={`w-4 h-4 ${active ? `text-${stage.color}-400` : 'text-slate-500'}`} />
                      <span className={`text-xs font-medium ${active ? 'text-white' : 'text-slate-400'}`}>{stage.label}</span>
                    </div>
                    <p className="text-[10px] text-slate-500">{stage.desc}</p>
                    {active && <div className={`w-full h-0.5 bg-${stage.color}-500 rounded mt-2`} />}
                  </button>
                );
              })}
            </div>
          </Card>

          {/* Scheduler Settings */}
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-white font-medium mb-3 flex items-center gap-2">
              <Timer className="w-4 h-4 text-emerald-400" /> Scheduler Intervals
            </h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Day Trade Scan: every {Math.floor((schSettings.dt_interval_seconds || 300) / 60)} min</label>
                <Slider value={[(schSettings.dt_interval_seconds || 300) / 60]} min={1} max={30} step={1}
                  onValueChange={([v]) => updateSchedulerSetting("dt_interval_seconds", v * 60)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Long-Term Scan: every {Math.floor((schSettings.lt_interval_seconds || 1800) / 60)} min</label>
                <Slider value={[(schSettings.lt_interval_seconds || 1800) / 60]} min={10} max={120} step={5}
                  onValueChange={([v]) => updateSchedulerSetting("lt_interval_seconds", v * 60)} />
              </div>
            </div>
          </Card>

          {/* Market Session Rules */}
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-white font-medium mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" /> Market Session Rules
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-300">Pre-Market Execution</p>
                  <p className="text-[10px] text-slate-500">Allow trades before 9:30 AM ET</p>
                </div>
                <Switch checked={schSettings.pre_market_execution || false}
                  onCheckedChange={(v) => updateSchedulerSetting("pre_market_execution", v)} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-300">After-Hours Execution</p>
                  <p className="text-[10px] text-slate-500">Allow trades after 4:00 PM ET</p>
                </div>
                <Switch checked={schSettings.after_hours_execution || false}
                  onCheckedChange={(v) => updateSchedulerSetting("after_hours_execution", v)} />
              </div>
            </div>
          </Card>

          {/* Safety Controls */}
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-red-400 font-medium mb-3 flex items-center gap-2">
              <Shield className="w-4 h-4" /> Safety Controls
            </h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Daily Loss: {schSettings.max_daily_loss_pct || 3}%</label>
                <Slider value={[schSettings.max_daily_loss_pct || 3]} min={1} max={10} step={0.5}
                  onValueChange={([v]) => updateSchedulerSetting("max_daily_loss_pct", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Drawdown: {schSettings.max_portfolio_drawdown_pct || 10}%</label>
                <Slider value={[schSettings.max_portfolio_drawdown_pct || 10]} min={3} max={25} step={1}
                  onValueChange={([v]) => updateSchedulerSetting("max_portfolio_drawdown_pct", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Consecutive Loss Cooldown: {schSettings.max_consecutive_losses || 3} losses</label>
                <Slider value={[schSettings.max_consecutive_losses || 3]} min={1} max={10} step={1}
                  onValueChange={([v]) => updateSchedulerSetting("max_consecutive_losses", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Cooldown Duration: {schSettings.cooldown_minutes || 30} min</label>
                <Slider value={[schSettings.cooldown_minutes || 30]} min={5} max={120} step={5}
                  onValueChange={([v]) => updateSchedulerSetting("cooldown_minutes", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Live Position Size: {((schSettings.live_position_size_multiplier || 0.5) * 100).toFixed(0)}%</label>
                <Slider value={[(schSettings.live_position_size_multiplier || 0.5) * 100]} min={10} max={100} step={10}
                  onValueChange={([v]) => updateSchedulerSetting("live_position_size_multiplier", v / 100)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Live Confidence Boost: +{schSettings.live_confidence_boost || 10}</label>
                <Slider value={[schSettings.live_confidence_boost || 10]} min={0} max={25} step={5}
                  onValueChange={([v]) => updateSchedulerSetting("live_confidence_boost", v)} />
              </div>
            </div>
          </Card>

          {/* Manual Actions */}
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-white font-medium mb-3">Manual Actions</h3>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700">
                <RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Scan Now
              </Button>
              <Button size="sm" onClick={executeCycle} disabled={executing} className="bg-emerald-600 hover:bg-emerald-500">
                <Play className={`w-3 h-3 mr-1 ${executing ? 'animate-spin' : ''}`} /> Execute Cycle
              </Button>
            </div>
          </Card>
        </TabsContent>

        {/* CANDIDATES/OVERVIEW TAB */}
        <TabsContent value="overview" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-slate-400">AI Classification Summary</h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700">
              <RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Scan
            </Button>
          </div>
          {opportunities?.stats && (
            <Card className="terminal-card p-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
                <div><p className="text-2xl font-mono text-white">{opportunities.stats.total_scanned}</p><p className="text-[10px] text-slate-500">Scanned</p></div>
                <div><p className="text-2xl font-mono text-amber-400">{opportunities.stats.day_trade_candidates}</p><p className="text-[10px] text-slate-500">Day Trades</p></div>
                <div><p className="text-2xl font-mono text-blue-400">{opportunities.stats.long_term_candidates}</p><p className="text-[10px] text-slate-500">Long Term</p></div>
                <div><p className="text-2xl font-mono text-slate-400">{opportunities.stats.watchlist}</p><p className="text-[10px] text-slate-500">Watchlist</p></div>
                <div><p className="text-2xl font-mono text-red-400">{opportunities.stats.rejected}</p><p className="text-[10px] text-slate-500">Rejected</p></div>
              </div>
            </Card>
          )}
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-400 mb-3">Market Regime</p>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
              <div><p className="text-slate-500">Regime</p><p className="text-white capitalize">{regime.regime?.replace("_", " ")}</p></div>
              <div><p className="text-slate-500">Volatility</p><p className="text-white font-mono">{regime.volatility_pct}%</p></div>
              <div><p className="text-slate-500">Trend</p><p className="text-white capitalize">{regime.trend?.replace("_", " ")}</p></div>
              <div><p className="text-slate-500">Momentum</p><p className={`font-mono ${regime.momentum_20d >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{regime.momentum_20d >= 0 ? '+' : ''}{regime.momentum_20d}%</p></div>
              <div><p className="text-slate-500">Score</p><p className="text-white font-mono">{regime.score}/100</p></div>
            </div>
          </Card>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-xs text-amber-400 mb-2 flex items-center gap-1"><Zap className="w-3 h-3" /> Top Day Trades</h3>
              <div className="space-y-2">
                {(opportunities?.day_trades || []).slice(0, 5).map((item) => (
                  <ExplanationCard key={item.symbol} item={item}
                    expanded={expandedCard === `dt-${item.symbol}`}
                    onToggle={() => setExpandedCard(expandedCard === `dt-${item.symbol}` ? null : `dt-${item.symbol}`)} />
                ))}
                {!opportunities?.day_trades?.length && <p className="text-xs text-slate-500 py-4 text-center">No day trade candidates</p>}
              </div>
            </div>
            <div>
              <h3 className="text-xs text-blue-400 mb-2 flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Top Long-Term</h3>
              <div className="space-y-2">
                {(opportunities?.long_term || []).slice(0, 5).map((item) => (
                  <ExplanationCard key={item.symbol} item={item}
                    expanded={expandedCard === `lt-${item.symbol}`}
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
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700">
              <RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
          {(opportunities?.day_trades || []).map((item) => (
            <ExplanationCard key={item.symbol} item={item}
              expanded={expandedCard === `dtf-${item.symbol}`}
              onToggle={() => setExpandedCard(expandedCard === `dtf-${item.symbol}` ? null : `dtf-${item.symbol}`)} />
          ))}
          {!opportunities?.day_trades?.length && <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No candidates</Card>}
        </TabsContent>

        {/* LONG TERM TAB */}
        <TabsContent value="long-term" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-blue-400 flex items-center gap-1"><TrendingUp className="w-4 h-4" /> Long-Term ({opportunities?.long_term?.length || 0})</h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700">
              <RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
          {(opportunities?.long_term || []).map((item) => (
            <ExplanationCard key={item.symbol} item={item}
              expanded={expandedCard === `ltf-${item.symbol}`}
              onToggle={() => setExpandedCard(expandedCard === `ltf-${item.symbol}` ? null : `ltf-${item.symbol}`)} />
          ))}
          {!opportunities?.long_term?.length && <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No candidates</Card>}
        </TabsContent>

        {/* NOTIFICATIONS TAB */}
        <TabsContent value="notifications" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-amber-400 flex items-center gap-1"><Bell className="w-4 h-4" /> Trade Notifications</h2>
            <Button variant="outline" size="sm" onClick={fetchNotifications} className="border-slate-700">
              <RefreshCw className="w-3 h-3 mr-1" /> Refresh
            </Button>
          </div>
          {notifications.length > 0 ? notifications.map((n, i) => {
            const sevColors = {
              critical: "border-red-500/30 bg-red-500/5",
              warning: "border-amber-500/30 bg-amber-500/5",
              info: "border-slate-700 bg-slate-900/50",
            };
            const sevIcon = {
              critical: <CircleStop className="w-4 h-4 text-red-400" />,
              warning: <AlertTriangle className="w-4 h-4 text-amber-400" />,
              info: <Bell className="w-4 h-4 text-blue-400" />,
            };
            return (
              <Card key={i} className={`p-3 border ${sevColors[n.severity] || sevColors.info}`}>
                <div className="flex items-start gap-2">
                  {sevIcon[n.severity] || sevIcon.info}
                  <div className="flex-1">
                    <p className="text-xs text-white">{n.message}</p>
                    <p className="text-[10px] text-slate-500">{new Date(n.timestamp).toLocaleString()}</p>
                  </div>
                  <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-500">{n.event}</Badge>
                </div>
              </Card>
            );
          }) : (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No notifications yet. Start the scheduler to see activity.</Card>
          )}
        </TabsContent>

        {/* HISTORY TAB */}
        <TabsContent value="history" className="space-y-3">
          <h2 className="text-sm text-purple-400 flex items-center gap-1"><Activity className="w-4 h-4" /> Trade History</h2>
          {history.length > 0 ? history.map((trade, i) => (
            <Card key={i} className="terminal-card p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className={`text-[10px] ${
                    trade.action === "BUY" ? 'border-emerald-500/30 text-emerald-400' : 'border-red-500/30 text-red-400'
                  }`}>{trade.action}</Badge>
                  <span className="text-white font-medium">{trade.symbol}</span>
                  <span className="text-xs text-slate-500">{trade.shares} shares</span>
                  <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-400">{trade.classification}</Badge>
                </div>
                <div className="text-right">
                  {trade.pnl !== undefined && trade.pnl !== null && (
                    <p className={`text-sm font-mono ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </p>
                  )}
                  <p className="text-[10px] text-slate-600">{new Date(trade.timestamp).toLocaleString()}</p>
                </div>
              </div>
            </Card>
          )) : (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No trade history yet</Card>
          )}
        </TabsContent>

        {/* SETTINGS TAB */}
        <TabsContent value="settings" className="space-y-4">
          <h2 className="text-sm text-slate-300">Engine Configuration</h2>
          <Card className="terminal-card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm text-amber-400 flex items-center gap-1"><Zap className="w-4 h-4" /> Day Trading</h3>
              <Switch checked={s.dt_enabled} onCheckedChange={(v) => updateSetting("dt_enabled", v)} />
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Confidence: {s.dt_confidence_threshold}</label>
                <Slider value={[s.dt_confidence_threshold || 75]} min={50} max={95} step={5}
                  onValueChange={([v]) => updateSetting("dt_confidence_threshold", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Risk/Trade: {((s.dt_risk_per_trade_pct || 0.04) * 100).toFixed(0)}%</label>
                <Slider value={[(s.dt_risk_per_trade_pct || 0.04) * 100]} min={1} max={10} step={1}
                  onValueChange={([v]) => updateSetting("dt_risk_per_trade_pct", v / 100)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Positions: {s.dt_max_positions}</label>
                <Slider value={[s.dt_max_positions || 6]} min={1} max={15} step={1}
                  onValueChange={([v]) => updateSetting("dt_max_positions", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">TP: {s.dt_take_profit_pct}%</label>
                <Slider value={[s.dt_take_profit_pct || 2.5]} min={0.5} max={10} step={0.5}
                  onValueChange={([v]) => updateSetting("dt_take_profit_pct", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">SL: {s.dt_stop_loss_pct}%</label>
                <Slider value={[s.dt_stop_loss_pct || 0.8]} min={0.3} max={5} step={0.1}
                  onValueChange={([v]) => updateSetting("dt_stop_loss_pct", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Time Exit: {s.dt_time_exit_days} day(s)</label>
                <Slider value={[s.dt_time_exit_days || 2]} min={1} max={5} step={1}
                  onValueChange={([v]) => updateSetting("dt_time_exit_days", v)} />
              </div>
            </div>
          </Card>
          <Card className="terminal-card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm text-blue-400 flex items-center gap-1"><TrendingUp className="w-4 h-4" /> Long-Term</h3>
              <Switch checked={s.lt_enabled} onCheckedChange={(v) => updateSetting("lt_enabled", v)} />
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Confidence: {s.lt_confidence_threshold}</label>
                <Slider value={[s.lt_confidence_threshold || 70]} min={50} max={95} step={5}
                  onValueChange={([v]) => updateSetting("lt_confidence_threshold", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Position: {((s.lt_max_position_pct || 0.15) * 100).toFixed(0)}%</label>
                <Slider value={[(s.lt_max_position_pct || 0.15) * 100]} min={5} max={25} step={1}
                  onValueChange={([v]) => updateSetting("lt_max_position_pct", v / 100)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Positions: {s.lt_max_positions}</label>
                <Slider value={[s.lt_max_positions || 8]} min={1} max={20} step={1}
                  onValueChange={([v]) => updateSetting("lt_max_positions", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Trailing Stop: {s.lt_trailing_stop_pct}%</label>
                <Slider value={[s.lt_trailing_stop_pct || 15]} min={5} max={30} step={1}
                  onValueChange={([v]) => updateSetting("lt_trailing_stop_pct", v)} />
              </div>
            </div>
          </Card>
          <Card className="terminal-card p-4">
            <h3 className="text-sm text-red-400 flex items-center gap-1 mb-4"><Shield className="w-4 h-4" /> Risk Management</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Daily Loss: {s.max_daily_loss_pct}%</label>
                <Slider value={[s.max_daily_loss_pct || 3]} min={1} max={10} step={0.5}
                  onValueChange={([v]) => updateSetting("max_daily_loss_pct", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Drawdown: {s.max_portfolio_drawdown_pct}%</label>
                <Slider value={[s.max_portfolio_drawdown_pct || 10]} min={3} max={25} step={1}
                  onValueChange={([v]) => updateSetting("max_portfolio_drawdown_pct", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Sector Cap: {s.max_sector_concentration_pct}%</label>
                <Slider value={[s.max_sector_concentration_pct || 30]} min={10} max={50} step={5}
                  onValueChange={([v]) => updateSetting("max_sector_concentration_pct", v)} />
              </div>
              <div className="flex items-center justify-between">
                <label className="text-xs text-slate-500">Alert-Only (no trades)</label>
                <Switch checked={s.alert_only_mode} onCheckedChange={(v) => updateSetting("alert_only_mode", v)} />
              </div>
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AutoTrade;
