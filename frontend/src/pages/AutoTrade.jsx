import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import {
  Zap, TrendingUp, Shield, AlertTriangle, Power, Activity,
  Clock, Target, DollarSign, BarChart2, Settings,
  Play, Pause, RefreshCw, Eye, ChevronDown, ChevronUp,
  ArrowUpRight, ArrowDownRight, Loader2, Brain, Lock
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

// ===================== STATUS BADGE =====================
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

// ===================== EXPLANATION CARD =====================
const ExplanationCard = ({ item, expanded, onToggle }) => {
  const exp = item.explanation || {};
  const isDay = item.classification === "DAY_TRADE";
  const signal = item.signal || {};

  return (
    <Card className="terminal-card overflow-hidden" data-testid={`candidate-${item.symbol}`}>
      <div className="p-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              isDay ? 'bg-amber-500/20' : 'bg-blue-500/20'
            }`}>
              {isDay ? <Zap className="w-5 h-5 text-amber-400" /> : <TrendingUp className="w-5 h-5 text-blue-400" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-white font-bold">{item.symbol}</span>
                <Badge variant="outline" className={`text-[10px] ${
                  isDay ? 'border-amber-500/30 text-amber-400' : 'border-blue-500/30 text-blue-400'
                }`}>
                  {isDay ? "DAY TRADE" : "LONG TERM"}
                </Badge>
                <Badge variant="outline" className={`text-[10px] ${
                  item.action === "BUY" ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10' :
                  item.action === "WATCHLIST" ? 'border-amber-500/30 text-amber-400' :
                  'border-red-500/30 text-red-400'
                }`}>
                  {item.action}
                </Badge>
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
          {/* Why Buy / Why Reject */}
          {exp.entry_reasons?.length > 0 && (
            <div className="p-3 rounded bg-emerald-500/5 border border-emerald-500/20">
              <p className="text-[10px] text-emerald-400 mb-1 font-medium">BUY REASONS</p>
              <ul className="space-y-1">
                {exp.entry_reasons.map((r, i) => (
                  <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                    <ArrowUpRight className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />
                    {r}
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
                    <AlertTriangle className="w-3 h-3 text-red-400 shrink-0 mt-0.5" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Exit Plan */}
          {exp.exit_plan && Object.keys(exp.exit_plan).length > 0 && (
            <div className="p-3 rounded bg-slate-900/50 border border-slate-800">
              <p className="text-[10px] text-slate-400 mb-2 font-medium">EXIT PLAN</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                {exp.exit_plan.entry && (
                  <div><p className="text-slate-500">Entry</p><p className="text-white font-mono">${exp.exit_plan.entry}</p></div>
                )}
                {exp.exit_plan.take_profit && (
                  <div><p className="text-slate-500">Take Profit</p><p className="text-emerald-400 font-mono">${exp.exit_plan.take_profit} ({exp.exit_plan.take_profit_pct > 0 ? '+' : ''}{exp.exit_plan.take_profit_pct}%)</p></div>
                )}
                {exp.exit_plan.stop_loss && (
                  <div><p className="text-slate-500">Stop Loss</p><p className="text-red-400 font-mono">${exp.exit_plan.stop_loss} ({exp.exit_plan.stop_loss_pct}%)</p></div>
                )}
                {exp.exit_plan.time_exit && (
                  <div><p className="text-slate-500">Time Exit</p><p className="text-slate-300">{exp.exit_plan.time_exit}</p></div>
                )}
              </div>
            </div>
          )}

          {/* Key Indicators */}
          {exp.key_indicators && (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs">
              {Object.entries(exp.key_indicators).filter(([k, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => (
                <div key={k} className="text-center p-1.5 rounded bg-slate-800/50">
                  <p className="text-[10px] text-slate-500">{k.replace(/_/g, " ")}</p>
                  <p className="text-white font-mono text-[11px]">{typeof v === "number" ? v.toFixed(1) : v}</p>
                </div>
              ))}
            </div>
          )}

          {/* Classification Scores */}
          <div className="flex gap-4 text-xs text-slate-500">
            <span>DT Score: <span className="text-amber-400 font-mono">{item.dt_score}</span></span>
            <span>LT Score: <span className="text-blue-400 font-mono">{item.lt_score}</span></span>
          </div>
        </div>
      )}
    </Card>
  );
};

// ===================== MAIN COMPONENT =====================
const AutoTrade = () => {
  const [status, setStatus] = useState(null);
  const [opportunities, setOpportunities] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [expandedCard, setExpandedCard] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [showSettings, setShowSettings] = useState(false);
  const { token } = useAuth();

  const headers = { Authorization: `Bearer ${token}` };

  const fetchStatus = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/auto-trade/status`, { headers });
      if (resp.ok) setStatus(await resp.json());
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

  useEffect(() => {
    Promise.all([fetchStatus(), fetchOpportunities(), fetchHistory()]).finally(() => setLoading(false));
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchOpportunities, fetchHistory]);

  const toggleAutoTrade = async () => {
    setToggling(true);
    try {
      const newState = !status?.auto_enabled;
      const resp = await fetch(`${API}/auto-trade/toggle?enabled=${newState}`, {
        method: "POST", headers
      });
      if (resp.ok) {
        await fetchStatus();
        toast.success(newState ? "Auto-Trading ENABLED" : "Auto-Trading DISABLED");
      }
    } catch (e) { toast.error("Toggle failed"); }
    setToggling(false);
  };

  const executeCycle = async () => {
    setExecuting(true);
    try {
      const resp = await fetch(`${API}/auto-trade/execute-cycle`, { method: "POST", headers });
      if (resp.ok) {
        toast.success("Auto-trade cycle executing...");
        setTimeout(() => { fetchStatus(); fetchHistory(); }, 5000);
      }
    } catch (e) { toast.error("Execution failed"); }
    setExecuting(false);
  };

  const emergencyPause = async () => {
    try {
      const resp = await fetch(`${API}/auto-trade/emergency-pause?pause=true`, { method: "POST", headers });
      if (resp.ok) {
        await fetchStatus();
        toast.error("EMERGENCY PAUSE ACTIVATED");
      }
    } catch (e) { toast.error("Pause failed"); }
  };

  const updateSetting = async (key, value) => {
    try {
      await fetch(`${API}/auto-trade/settings`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value })
      });
      await fetchStatus();
    } catch (e) { console.error(e); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  const s = status?.settings || {};
  const regime = status?.market_regime || {};
  const today = status?.today || {};

  return (
    <div className="space-y-6 max-w-7xl mx-auto" data-testid="auto-trade-page">
      {/* Header with Master Toggle */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Brain className="w-6 h-6 text-blue-400" />
            <h1 className="font-display text-2xl font-bold text-white">AI Auto-Trade</h1>
            <RegimeBadge regime={regime} />
          </div>
          <p className="text-sm text-slate-500">Dual-engine autonomous trading system</p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Master ON/OFF Toggle */}
          <div className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border ${
            status?.auto_enabled 
              ? 'bg-emerald-500/10 border-emerald-500/30' 
              : 'bg-slate-900 border-slate-700'
          }`} data-testid="auto-toggle-container">
            <div className={`w-3 h-3 rounded-full ${status?.auto_enabled ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`} />
            <span className={`text-sm font-medium ${status?.auto_enabled ? 'text-emerald-400' : 'text-slate-400'}`}>
              {status?.auto_enabled ? "AUTO ON" : "AUTO OFF"}
            </span>
            <Switch
              checked={status?.auto_enabled || false}
              onCheckedChange={toggleAutoTrade}
              disabled={toggling}
              data-testid="auto-trade-toggle"
            />
          </div>
          
          <Button variant="outline" onClick={emergencyPause} className="border-red-500/30 text-red-400 hover:bg-red-500/10" data-testid="emergency-pause-btn">
            <Pause className="w-4 h-4 mr-1" /> Emergency Stop
          </Button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Equity</p>
          <p className="text-xl font-mono text-white">${parseFloat(status?.account?.equity || 0).toLocaleString()}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Buying Power</p>
          <p className="text-xl font-mono text-white">${parseFloat(status?.account?.buying_power || 0).toLocaleString()}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Positions</p>
          <p className="text-xl font-mono text-white">{status?.positions || 0}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Today's P&L</p>
          <p className={`text-xl font-mono ${today.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {today.pnl >= 0 ? '+' : ''}${today.pnl?.toFixed(2) || '0.00'}
          </p>
          <p className="text-[10px] text-slate-600">{today.buys || 0} buys / {today.sells || 0} sells</p>
        </Card>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full justify-start bg-slate-900 border border-slate-800 p-1 h-auto flex-wrap">
          <TabsTrigger value="overview" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <Eye className="w-4 h-4 mr-1" /> Overview
          </TabsTrigger>
          <TabsTrigger value="day-trades" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400">
            <Zap className="w-4 h-4 mr-1" /> Day Trades ({opportunities?.day_trades?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="long-term" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <TrendingUp className="w-4 h-4 mr-1" /> Long Term ({opportunities?.long_term?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="watchlist" className="data-[state=active]:bg-slate-500/20 data-[state=active]:text-slate-400">
            <Clock className="w-4 h-4 mr-1" /> Watchlist ({opportunities?.watchlist?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400">
            <Activity className="w-4 h-4 mr-1" /> History
          </TabsTrigger>
          <TabsTrigger value="settings" className="data-[state=active]:bg-slate-500/20 data-[state=active]:text-white">
            <Settings className="w-4 h-4 mr-1" /> Settings
          </TabsTrigger>
        </TabsList>

        {/* OVERVIEW TAB */}
        <TabsContent value="overview" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-slate-400">System Overview</h2>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700">
                <RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Scan
              </Button>
              {status?.auto_enabled && (
                <Button size="sm" onClick={executeCycle} disabled={executing} className="bg-emerald-600 hover:bg-emerald-500">
                  <Play className={`w-3 h-3 mr-1 ${executing ? 'animate-spin' : ''}`} /> Execute Cycle
                </Button>
              )}
            </div>
          </div>
          
          {/* AI Classification Summary */}
          {opportunities?.stats && (
            <Card className="terminal-card p-4">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
                <div>
                  <p className="text-2xl font-mono text-white">{opportunities.stats.total_scanned}</p>
                  <p className="text-[10px] text-slate-500">Stocks Scanned</p>
                </div>
                <div>
                  <p className="text-2xl font-mono text-amber-400">{opportunities.stats.day_trade_candidates}</p>
                  <p className="text-[10px] text-slate-500">Day Trade Candidates</p>
                </div>
                <div>
                  <p className="text-2xl font-mono text-blue-400">{opportunities.stats.long_term_candidates}</p>
                  <p className="text-[10px] text-slate-500">Long Term Candidates</p>
                </div>
                <div>
                  <p className="text-2xl font-mono text-slate-400">{opportunities.stats.watchlist}</p>
                  <p className="text-[10px] text-slate-500">Watchlist</p>
                </div>
                <div>
                  <p className="text-2xl font-mono text-red-400">{opportunities.stats.rejected}</p>
                  <p className="text-[10px] text-slate-500">Rejected</p>
                </div>
              </div>
            </Card>
          )}

          {/* Market Regime */}
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-400 mb-3">Market Regime</p>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
              <div><p className="text-slate-500">Regime</p><p className="text-white font-medium capitalize">{regime.regime?.replace("_", " ")}</p></div>
              <div><p className="text-slate-500">Volatility</p><p className={`font-mono ${regime.volatility === 'low' ? 'text-emerald-400' : regime.volatility === 'high' ? 'text-red-400' : 'text-white'}`}>{regime.volatility_pct}%</p></div>
              <div><p className="text-slate-500">Trend</p><p className="text-white capitalize">{regime.trend?.replace("_", " ")}</p></div>
              <div><p className="text-slate-500">20d Momentum</p><p className={`font-mono ${regime.momentum_20d >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{regime.momentum_20d >= 0 ? '+' : ''}{regime.momentum_20d}%</p></div>
              <div><p className="text-slate-500">Score</p><p className={`font-mono ${regime.score >= 60 ? 'text-emerald-400' : regime.score >= 40 ? 'text-amber-400' : 'text-red-400'}`}>{regime.score}/100</p></div>
            </div>
          </Card>

          {/* Top Day Trade + Long Term side by side */}
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-xs text-amber-400 mb-2 flex items-center gap-1"><Zap className="w-3 h-3" /> Top Day Trade Candidates</h3>
              <div className="space-y-2">
                {(opportunities?.day_trades || []).slice(0, 5).map((item) => (
                  <ExplanationCard
                    key={item.symbol}
                    item={item}
                    expanded={expandedCard === `dt-${item.symbol}`}
                    onToggle={() => setExpandedCard(expandedCard === `dt-${item.symbol}` ? null : `dt-${item.symbol}`)}
                  />
                ))}
                {(!opportunities?.day_trades || opportunities.day_trades.length === 0) && (
                  <p className="text-xs text-slate-500 py-4 text-center">No day trade candidates right now</p>
                )}
              </div>
            </div>
            <div>
              <h3 className="text-xs text-blue-400 mb-2 flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Top Long-Term Picks</h3>
              <div className="space-y-2">
                {(opportunities?.long_term || []).slice(0, 5).map((item) => (
                  <ExplanationCard
                    key={item.symbol}
                    item={item}
                    expanded={expandedCard === `lt-${item.symbol}`}
                    onToggle={() => setExpandedCard(expandedCard === `lt-${item.symbol}` ? null : `lt-${item.symbol}`)}
                  />
                ))}
                {(!opportunities?.long_term || opportunities.long_term.length === 0) && (
                  <p className="text-xs text-slate-500 py-4 text-center">No long-term candidates right now</p>
                )}
              </div>
            </div>
          </div>
        </TabsContent>

        {/* DAY TRADES TAB */}
        <TabsContent value="day-trades" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-amber-400 flex items-center gap-1">
              <Zap className="w-4 h-4" /> Day Trading Candidates ({opportunities?.day_trades?.length || 0})
            </h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700">
              <RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
          {(opportunities?.day_trades || []).map((item) => (
            <ExplanationCard
              key={item.symbol}
              item={item}
              expanded={expandedCard === `dtf-${item.symbol}`}
              onToggle={() => setExpandedCard(expandedCard === `dtf-${item.symbol}` ? null : `dtf-${item.symbol}`)}
            />
          ))}
          {(!opportunities?.day_trades?.length) && (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No day trade candidates found. Try refreshing signals first.</Card>
          )}
        </TabsContent>

        {/* LONG TERM TAB */}
        <TabsContent value="long-term" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-blue-400 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" /> Long-Term Investment Picks ({opportunities?.long_term?.length || 0})
            </h2>
            <Button variant="outline" size="sm" onClick={fetchOpportunities} disabled={scanning} className="border-slate-700">
              <RefreshCw className={`w-3 h-3 mr-1 ${scanning ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
          {(opportunities?.long_term || []).map((item) => (
            <ExplanationCard
              key={item.symbol}
              item={item}
              expanded={expandedCard === `ltf-${item.symbol}`}
              onToggle={() => setExpandedCard(expandedCard === `ltf-${item.symbol}` ? null : `ltf-${item.symbol}`)}
            />
          ))}
          {(!opportunities?.long_term?.length) && (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No long-term candidates found. Try refreshing investment data first.</Card>
          )}
        </TabsContent>

        {/* WATCHLIST TAB */}
        <TabsContent value="watchlist" className="space-y-3">
          <h2 className="text-sm text-slate-400">AI Watchlist — Almost Ready</h2>
          <div className="grid gap-2">
            {(opportunities?.watchlist || []).slice(0, 30).map((item) => (
              <Card key={item.symbol} className="terminal-card p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-white font-medium text-sm">{item.symbol}</span>
                  <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-400">
                    DT:{item.dt_score} | LT:{item.lt_score}
                  </Badge>
                </div>
                <span className="text-xs text-slate-500">Watching</span>
              </Card>
            ))}
            {(!opportunities?.watchlist?.length) && (
              <p className="text-sm text-slate-500 text-center py-4">Watchlist is empty</p>
            )}
          </div>
        </TabsContent>

        {/* HISTORY TAB */}
        <TabsContent value="history" className="space-y-3">
          <h2 className="text-sm text-purple-400 flex items-center gap-1">
            <Activity className="w-4 h-4" /> Auto-Trade History
          </h2>
          {history.length > 0 ? (
            <div className="space-y-2">
              {history.map((trade, i) => (
                <Card key={i} className="terminal-card p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className={`text-[10px] ${
                        trade.action === "BUY" ? 'border-emerald-500/30 text-emerald-400' : 'border-red-500/30 text-red-400'
                      }`}>{trade.action}</Badge>
                      <span className="text-white font-medium">{trade.symbol}</span>
                      <span className="text-xs text-slate-500">{trade.shares} shares</span>
                      <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-400">
                        {trade.classification}
                      </Badge>
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
              ))}
            </div>
          ) : (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">No auto-trade history yet</Card>
          )}
        </TabsContent>

        {/* SETTINGS TAB */}
        <TabsContent value="settings" className="space-y-4">
          <h2 className="text-sm text-slate-300">Auto-Trade Configuration</h2>
          
          {/* Day Trading Settings */}
          <Card className="terminal-card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm text-amber-400 flex items-center gap-1"><Zap className="w-4 h-4" /> Day Trading Settings</h3>
              <Switch checked={s.dt_enabled} onCheckedChange={(v) => updateSetting("dt_enabled", v)} />
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Confidence Threshold: {s.dt_confidence_threshold}</label>
                <Slider value={[s.dt_confidence_threshold || 75]} min={50} max={95} step={5}
                  onValueChange={([v]) => updateSetting("dt_confidence_threshold", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Risk Per Trade: {((s.dt_risk_per_trade_pct || 0.04) * 100).toFixed(0)}%</label>
                <Slider value={[(s.dt_risk_per_trade_pct || 0.04) * 100]} min={1} max={10} step={1}
                  onValueChange={([v]) => updateSetting("dt_risk_per_trade_pct", v / 100)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max Positions: {s.dt_max_positions}</label>
                <Slider value={[s.dt_max_positions || 6]} min={1} max={15} step={1}
                  onValueChange={([v]) => updateSetting("dt_max_positions", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Take Profit: {s.dt_take_profit_pct}%</label>
                <Slider value={[s.dt_take_profit_pct || 2.5]} min={0.5} max={10} step={0.5}
                  onValueChange={([v]) => updateSetting("dt_take_profit_pct", v)} />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">Stop Loss: {s.dt_stop_loss_pct}%</label>
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

          {/* Long-Term Settings */}
          <Card className="terminal-card p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm text-blue-400 flex items-center gap-1"><TrendingUp className="w-4 h-4" /> Long-Term Settings</h3>
              <Switch checked={s.lt_enabled} onCheckedChange={(v) => updateSetting("lt_enabled", v)} />
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">Confidence Threshold: {s.lt_confidence_threshold}</label>
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

          {/* Global Risk Settings */}
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
                <label className="text-xs text-slate-500 block mb-1">Max Sector: {s.max_sector_concentration_pct}%</label>
                <Slider value={[s.max_sector_concentration_pct || 30]} min={10} max={50} step={5}
                  onValueChange={([v]) => updateSetting("max_sector_concentration_pct", v)} />
              </div>
              <div className="flex items-center justify-between">
                <label className="text-xs text-slate-500">Alert-Only Mode (no execution)</label>
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
