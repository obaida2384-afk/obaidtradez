import { useState, useEffect, useCallback, memo, useRef } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useLivePrices, usePositionsPrices, LiveIndicator } from "../hooks/useLivePrices";
import { 
  Bot,
  Shield,
  AlertTriangle,
  AlertOctagon,
  Play,
  Pause,
  Check,
  X,
  Clock,
  Loader2,
  RefreshCw,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Target,
  History,
  FileText,
  Zap,
  Ban,
  ChevronRight,
  Sun,
  Moon,
  Sunrise,
  Sunset
} from "lucide-react";
import { toast } from "sonner";

// Market Status Badge Component
const MarketStatusBadge = ({ status, extended }) => {
  const configs = {
    open: { 
      color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", 
      icon: Sun,
      pulse: true 
    },
    pre_market: { 
      color: "bg-amber-500/20 text-amber-400 border-amber-500/30", 
      icon: Sunrise,
      pulse: false 
    },
    after_hours: { 
      color: "bg-orange-500/20 text-orange-400 border-orange-500/30", 
      icon: Sunset,
      pulse: false 
    },
    closed: { 
      color: "bg-slate-500/20 text-slate-400 border-slate-500/30", 
      icon: Moon,
      pulse: false 
    }
  };
  
  const config = configs[status] || configs.closed;
  const Icon = config.icon;
  
  return (
    <Badge 
      variant="outline" 
      className={`${config.color} border font-mono text-xs`}
      data-testid="market-status-badge"
    >
      <Icon className={`w-3 h-3 mr-1 ${config.pulse ? 'animate-pulse' : ''}`} />
      {status === 'open' ? 'Market Open' : 
       status === 'pre_market' ? 'Pre-Market' :
       status === 'after_hours' ? 'After-Hours' : 'Closed'}
      {extended && status !== 'open' && (
        <span className="ml-1 text-[10px] opacity-70">(Extended ON)</span>
      )}
    </Badge>
  );
};

// Status badge component
const StatusBadge = ({ status }) => {
  const configs = {
    pending: { color: "bg-amber-500/20 text-amber-400 border-amber-500/30", icon: Clock },
    approved: { color: "bg-blue-500/20 text-blue-400 border-blue-500/30", icon: Check },
    executing: { color: "bg-purple-500/20 text-purple-400 border-purple-500/30", icon: Loader2 },
    executed: { color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", icon: Check },
    rejected: { color: "bg-red-500/20 text-red-400 border-red-500/30", icon: X },
    cancelled: { color: "bg-slate-500/20 text-slate-400 border-slate-500/30", icon: Ban },
    failed: { color: "bg-red-500/20 text-red-400 border-red-500/30", icon: AlertTriangle }
  };
  
  const config = configs[status] || configs.pending;
  const Icon = config.icon;
  
  return (
    <Badge variant="outline" className={config.color}>
      <Icon className={`w-3 h-3 mr-1 ${status === 'executing' ? 'animate-spin' : ''}`} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
};

// Trade card component - memoized
const TradeCard = memo(({ trade, onApprove, onReject, onCancel, onExecute, loading, livePrice }) => {
  const isPending = trade.status === "pending";
  const isApproved = trade.status === "approved";
  const canExecute = isApproved;
  const canCancel = isPending || isApproved;
  
  // Use live price if available
  const displayPrice = livePrice?.price || trade.entry_price;
  
  return (
    <Card className="terminal-card p-4" data-testid={`trade-card-${trade.id}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            trade.side === 'buy' ? 'bg-emerald-500/20' : 'bg-red-500/20'
          }`}>
            {trade.side === 'buy' ? (
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-400" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-lg text-white">{trade.symbol}</span>
              {livePrice && <LiveIndicator active={true} />}
              <StatusBadge status={trade.status} />
            </div>
            <p className="text-xs text-slate-500">
              {trade.side.toUpperCase()} • {trade.qty ? `${trade.qty} shares` : `$${trade.notional}`}
              {livePrice && ` • Live: $${livePrice.price.toFixed(2)}`}
            </p>
          </div>
        </div>
        
        <div className="text-right">
          <p className="text-xs text-slate-500">Strategy</p>
          <p className="text-sm text-slate-300">{trade.strategy}</p>
        </div>
      </div>
      
      {/* Trade Details */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        {trade.entry_price && (
          <div>
            <p className="text-xs text-slate-500">Entry</p>
            <p className="font-mono text-sm text-white">${trade.entry_price}</p>
          </div>
        )}
        {trade.stop_loss && (
          <div>
            <p className="text-xs text-slate-500">Stop Loss</p>
            <p className="font-mono text-sm text-red-400">${trade.stop_loss}</p>
          </div>
        )}
        {trade.take_profit && (
          <div>
            <p className="text-xs text-slate-500">Take Profit</p>
            <p className="font-mono text-sm text-emerald-400">${trade.take_profit}</p>
          </div>
        )}
        {trade.confidence && (
          <div>
            <p className="text-xs text-slate-500">Confidence</p>
            <p className={`font-mono text-sm ${trade.confidence >= 0.7 ? 'text-emerald-400' : trade.confidence >= 0.5 ? 'text-amber-400' : 'text-red-400'}`}>
              {(trade.confidence * 100).toFixed(0)}%
            </p>
          </div>
        )}
      </div>
      
      {/* Reason */}
      {trade.reason && (
        <p className="text-xs text-slate-500 mb-3 italic">"{trade.reason}"</p>
      )}
      
      {/* Execution Details */}
      {trade.alpaca_order_id && (
        <div className="mb-3 p-2 rounded bg-slate-800/50">
          <p className="text-xs text-slate-500">Alpaca Order ID</p>
          <p className="font-mono text-xs text-slate-300">{trade.alpaca_order_id}</p>
          {trade.filled_avg_price && (
            <p className="text-xs text-emerald-400 mt-1">
              Filled @ ${trade.filled_avg_price} • {trade.filled_qty} shares
            </p>
          )}
        </div>
      )}
      
      {/* Failure Reason */}
      {trade.failure_reason && (
        <div className="mb-3 p-2 rounded bg-red-500/10 border border-red-500/20">
          <p className="text-xs text-red-400">{trade.failure_reason}</p>
        </div>
      )}
      
      {/* Actions */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-800">
        <span className="text-xs text-slate-600">
          {new Date(trade.created_at).toLocaleString()}
        </span>
        
        <div className="flex items-center gap-2">
          {isPending && (
            <>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => onReject(trade.id)}
                disabled={loading}
                className="border-red-500/30 text-red-400 hover:bg-red-500/10"
              >
                <X className="w-3 h-3 mr-1" /> Reject
              </Button>
              <Button 
                size="sm"
                onClick={() => onApprove(trade.id)}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-500"
              >
                <Check className="w-3 h-3 mr-1" /> Approve
              </Button>
            </>
          )}
          
          {canExecute && (
            <Button 
              size="sm"
              onClick={() => onExecute(trade.id)}
              disabled={loading}
              className="bg-emerald-600 hover:bg-emerald-500"
            >
              {loading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Play className="w-3 h-3 mr-1" />}
              Execute
            </Button>
          )}
          
          {canCancel && (
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => onCancel(trade.id)}
              disabled={loading}
              className="border-slate-700"
            >
              <Ban className="w-3 h-3 mr-1" /> Cancel
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
});

// Audit log entry component
const AuditEntry = ({ entry }) => {
  const actionColors = {
    trade_queued: "text-amber-400",
    trade_approved: "text-blue-400",
    trade_rejected: "text-red-400",
    trade_cancelled: "text-slate-400",
    trade_executed: "text-emerald-400",
    trade_blocked: "text-red-400",
    trade_failed: "text-red-400",
    trade_error: "text-red-400",
    kill_switch_toggle: "text-purple-400"
  };
  
  return (
    <div className="flex items-center justify-between p-3 border-b border-slate-800 last:border-0">
      <div className="flex items-center gap-3">
        <div className={`text-sm font-mono ${actionColors[entry.action] || 'text-slate-400'}`}>
          {entry.action.replace(/_/g, ' ')}
        </div>
        {entry.data?.symbol && (
          <Badge variant="outline" className="border-slate-700 text-xs">
            {entry.data.symbol}
          </Badge>
        )}
      </div>
      <span className="text-xs text-slate-600">
        {new Date(entry.timestamp).toLocaleString()}
      </span>
    </div>
  );
};

// Quick trade form component
const QuickTradeForm = ({ onSubmit, loading }) => {
  const [form, setForm] = useState({
    symbol: "",
    side: "buy",
    qty: "",
    reason: "",
    strategy: "manual"
  });
  
  const handleSubmit = () => {
    if (!form.symbol.trim()) {
      toast.error("Symbol is required");
      return;
    }
    if (!form.qty || parseFloat(form.qty) <= 0) {
      toast.error("Quantity must be greater than 0");
      return;
    }
    
    onSubmit({
      symbol: form.symbol.toUpperCase(),
      side: form.side,
      qty: parseFloat(form.qty),
      reason: form.reason,
      strategy: form.strategy
    });
    
    setForm({ symbol: "", side: "buy", qty: "", reason: "", strategy: "manual" });
  };
  
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Input
          value={form.symbol}
          onChange={(e) => setForm({...form, symbol: e.target.value.toUpperCase()})}
          placeholder="Symbol"
          className="bg-slate-900 border-slate-700 font-mono"
        />
        <Select value={form.side} onValueChange={(v) => setForm({...form, side: v})}>
          <SelectTrigger className="bg-slate-900 border-slate-700">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="buy">Buy</SelectItem>
            <SelectItem value="sell">Sell</SelectItem>
          </SelectContent>
        </Select>
        <Input
          type="number"
          value={form.qty}
          onChange={(e) => setForm({...form, qty: e.target.value})}
          placeholder="Quantity"
          className="bg-slate-900 border-slate-700"
        />
        <Select value={form.strategy} onValueChange={(v) => setForm({...form, strategy: v})}>
          <SelectTrigger className="bg-slate-900 border-slate-700">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="manual">Manual</SelectItem>
            <SelectItem value="momentum">Momentum</SelectItem>
            <SelectItem value="value">Value</SelectItem>
            <SelectItem value="breakout">Breakout</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex gap-3">
        <Input
          value={form.reason}
          onChange={(e) => setForm({...form, reason: e.target.value})}
          placeholder="Reason for trade (optional)"
          className="flex-1 bg-slate-900 border-slate-700"
        />
        <Button onClick={handleSubmit} disabled={loading} className="bg-amber-600 hover:bg-amber-500">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clock className="w-4 h-4 mr-1" />}
          Queue Trade
        </Button>
      </div>
    </div>
  );
};

const AutoTrade = () => {
  const { token } = useAuth();
  const [settings, setSettings] = useState(null);
  const [trades, setTrades] = useState([]);
  const [stats, setStats] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("queue");
  const [statusFilter, setStatusFilter] = useState("");
  const [marketStatus, setMarketStatus] = useState(null);

  // Get symbols from queue for live prices
  const queueSymbols = trades.map(t => t.symbol).filter(Boolean);
  const { prices: queuePrices } = useLivePrices(queueSymbols, 12000, queueSymbols.length > 0);
  
  // Live prices for positions
  const { prices: positionPrices } = usePositionsPrices(15000, positions.length > 0);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      const [settingsRes, tradesRes, statsRes, auditRes, accountRes, positionsRes, marketRes] = await Promise.all([
        fetch(`${API}/paper/settings`, { headers }),
        fetch(`${API}/paper/queue${statusFilter ? `?status=${statusFilter}` : ''}`, { headers }),
        fetch(`${API}/paper/stats`, { headers }),
        fetch(`${API}/paper/audit?limit=30`, { headers }),
        fetch(`${API}/account`, { headers }),
        fetch(`${API}/positions`, { headers }),
        fetch(`${API}/paper/market-status`, { headers })
      ]);
      
      if (settingsRes.ok) setSettings(await settingsRes.json());
      if (tradesRes.ok) setTrades(await tradesRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
      if (auditRes.ok) setAuditLog(await auditRes.json());
      if (accountRes.ok) setAccount(await accountRes.json());
      if (positionsRes.ok) setPositions(await positionsRes.json());
      if (marketRes.ok) setMarketStatus(await marketRes.json());
    } catch (error) {
      console.error("Fetch error:", error);
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const updateSettings = async (newSettings) => {
    try {
      const response = await fetch(`${API}/paper/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(newSettings)
      });
      
      if (response.ok) {
        setSettings(newSettings);
        toast.success("Settings updated");
      }
    } catch (error) {
      toast.error("Failed to update settings");
    }
  };

  const toggleKillSwitch = async () => {
    try {
      const response = await fetch(`${API}/paper/kill-switch?active=${!settings.kill_switch}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const result = await response.json();
        setSettings({...settings, kill_switch: result.kill_switch});
        toast[result.kill_switch ? 'error' : 'success'](
          result.kill_switch ? "Kill switch ACTIVATED - All execution blocked" : "Kill switch deactivated"
        );
        fetchData(); // Refresh audit log
      }
    } catch (error) {
      toast.error("Failed to toggle kill switch");
    }
  };

  const queueTrade = async (tradeData) => {
    setActionLoading(true);
    try {
      const response = await fetch(`${API}/paper/queue`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(tradeData)
      });
      
      if (response.ok) {
        toast.success(`${tradeData.symbol} queued for review`);
        fetchData();
      } else {
        toast.error("Failed to queue trade");
      }
    } catch (error) {
      toast.error("Error queuing trade");
    } finally {
      setActionLoading(false);
    }
  };

  const handleApprove = async (tradeId) => {
    setActionLoading(true);
    try {
      const response = await fetch(`${API}/paper/trade/${tradeId}/approve`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success("Trade approved");
        fetchData();
      }
    } catch (error) {
      toast.error("Failed to approve trade");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (tradeId) => {
    setActionLoading(true);
    try {
      const response = await fetch(`${API}/paper/trade/${tradeId}/reject`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success("Trade rejected");
        fetchData();
      }
    } catch (error) {
      toast.error("Failed to reject trade");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async (tradeId) => {
    setActionLoading(true);
    try {
      const response = await fetch(`${API}/paper/trade/${tradeId}/cancel`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        toast.success("Trade cancelled");
        fetchData();
      }
    } catch (error) {
      toast.error("Failed to cancel trade");
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecute = async (tradeId) => {
    setActionLoading(true);
    try {
      const response = await fetch(`${API}/paper/trade/${tradeId}/execute`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const result = await response.json();
      
      if (result.success) {
        toast.success("Trade executed successfully", {
          description: `Order ${result.alpaca_order?.id?.slice(0, 8)}... submitted to Alpaca`
        });
        fetchData();
      } else {
        // Check if it's a market hours violation
        const isMarketHoursBlock = result.violations?.some(v => 
          v.includes("Extended hours") || v.includes("Market is currently")
        );
        
        if (isMarketHoursBlock) {
          toast.error("Trade blocked by market hours", {
            description: "Enable 'Allow Extended Hours Trading' in settings or wait for regular market hours (9:30 AM - 4:00 PM ET).",
            duration: 6000
          });
        } else {
          toast.error(result.error || "Execution failed");
        }
        
        // Show all violations
        if (result.violations) {
          result.violations.forEach(v => {
            if (!isMarketHoursBlock || !v.includes("Extended hours")) {
              toast.warning(v, { duration: 5000 });
            }
          });
        }
        fetchData();
      }
    } catch (error) {
      toast.error("Error executing trade");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-slate-500" />
      </div>
    );
  }

  const equity = parseFloat(account?.equity || 0);
  const buyingPower = parseFloat(account?.buying_power || 0);
  const cash = parseFloat(account?.cash || 0);

  return (
    <div className="space-y-6" data-testid="paper-execution-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Bot className="w-6 h-6 text-purple-400" />
            <h1 className="font-display text-2xl font-bold text-white">Paper Execution</h1>
            <Badge variant="outline" className="border-amber-500/30 text-amber-400">
              Paper Trading Only
            </Badge>
            {marketStatus && (
              <MarketStatusBadge 
                status={marketStatus.status} 
                extended={marketStatus.extended_hours_enabled}
              />
            )}
          </div>
          <p className="text-sm text-slate-500">
            Queue and execute trades on Alpaca Paper account
            {marketStatus?.message && (
              <span className="ml-2 text-slate-600">• {marketStatus.message}</span>
            )}
          </p>
        </div>
        
        <Button variant="outline" onClick={fetchData} className="border-slate-700">
          <RefreshCw className="w-4 h-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Market Hours Warning */}
      {marketStatus && !marketStatus.can_trade_now && (
        <Card className="p-4 border-amber-500/50 bg-amber-500/10">
          <div className="flex items-center gap-3">
            <Clock className="w-6 h-6 text-amber-400" />
            <div>
              <p className="text-amber-400 font-medium">Trading Outside Regular Hours</p>
              <p className="text-xs text-amber-300">
                {marketStatus.label}. Trades cannot be executed until {marketStatus.next_open || 'market opens'}.
                {!marketStatus.extended_hours_enabled && (
                  <span> Enable "Allow Extended Hours" in settings to trade during pre-market and after-hours sessions.</span>
                )}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Kill Switch Alert */}
      {settings?.kill_switch && (
        <Card className="p-4 border-red-500 bg-red-500/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertOctagon className="w-6 h-6 text-red-400" />
              <div>
                <p className="text-red-400 font-medium">KILL SWITCH ACTIVE</p>
                <p className="text-xs text-red-300">All trade execution is blocked</p>
              </div>
            </div>
            <Button onClick={toggleKillSwitch} className="bg-red-600 hover:bg-red-500">
              Deactivate Kill Switch
            </Button>
          </div>
        </Card>
      )}

      {/* Account & Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Buying Power</p>
          <p className="text-xl font-mono text-white">${buyingPower.toLocaleString()}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Cash</p>
          <p className="text-xl font-mono text-white">${cash.toLocaleString()}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Pending</p>
          <p className="text-xl font-mono text-amber-400">{stats?.pending || 0}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Approved</p>
          <p className="text-xl font-mono text-blue-400">{stats?.approved || 0}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Executed</p>
          <p className="text-xl font-mono text-emerald-400">{stats?.executed || 0}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Failed</p>
          <p className="text-xl font-mono text-red-400">{stats?.failed || 0}</p>
        </Card>
      </div>

      {/* Safety Controls */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-5 h-5 text-emerald-400" />
          <h2 className="font-display font-semibold text-white">Safety Controls</h2>
        </div>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded bg-slate-900 border border-slate-800">
              <div>
                <p className="text-sm text-white">Kill Switch</p>
                <p className="text-xs text-slate-500">Block all execution immediately</p>
              </div>
              <Button 
                variant={settings?.kill_switch ? "default" : "outline"}
                onClick={toggleKillSwitch}
                className={settings?.kill_switch ? "bg-red-600 hover:bg-red-500" : "border-red-500/30 text-red-400"}
              >
                {settings?.kill_switch ? <AlertOctagon className="w-4 h-4 mr-1" /> : <Shield className="w-4 h-4 mr-1" />}
                {settings?.kill_switch ? "ACTIVE" : "Inactive"}
              </Button>
            </div>
            
            <div className="flex items-center justify-between p-3 rounded bg-slate-900 border border-slate-800">
              <div>
                <p className="text-sm text-white">Manual Approval Required</p>
                <p className="text-xs text-slate-500">All trades must be approved before execution</p>
              </div>
              <Switch
                checked={settings?.manual_approval !== false}
                onCheckedChange={(v) => updateSettings({...settings, manual_approval: v})}
              />
            </div>
            
            <div className="flex items-center justify-between p-3 rounded bg-slate-900 border border-slate-800">
              <div>
                <p className="text-sm text-white">Auto Execution</p>
                <p className="text-xs text-slate-500">Execute approved trades automatically</p>
              </div>
              <Switch
                checked={settings?.auto_execution === true}
                onCheckedChange={(v) => updateSettings({...settings, auto_execution: v})}
              />
            </div>
            
            <div className="flex items-center justify-between p-3 rounded bg-slate-900 border border-amber-500/30">
              <div>
                <p className="text-sm text-white flex items-center gap-2">
                  Allow Extended Hours Trading
                  {marketStatus && marketStatus.status !== 'open' && !settings?.block_extended_hours && (
                    <Badge variant="outline" className="border-amber-500/30 text-amber-400 text-[10px]">
                      Active
                    </Badge>
                  )}
                </p>
                <p className="text-xs text-slate-500">
                  Trade during pre-market (4AM-9:30AM ET) and after-hours (4PM-8PM ET)
                </p>
              </div>
              <Switch
                checked={settings?.block_extended_hours === false}
                onCheckedChange={(v) => updateSettings({...settings, block_extended_hours: !v})}
              />
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="text-xs text-slate-500 mb-2 block">
                Max Position Size: {((settings?.max_position_pct || 0.05) * 100).toFixed(0)}%
              </label>
              <Slider
                value={[(settings?.max_position_pct || 0.05) * 100]}
                onValueChange={([v]) => updateSettings({...settings, max_position_pct: v / 100})}
                min={1}
                max={25}
                step={1}
              />
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">
                Cash Buffer: {((settings?.cash_buffer || 0.10) * 100).toFixed(0)}%
              </label>
              <Slider
                value={[(settings?.cash_buffer || 0.10) * 100]}
                onValueChange={([v]) => updateSettings({...settings, cash_buffer: v / 100})}
                min={0}
                max={50}
                step={5}
              />
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">
                Min Confidence: {((settings?.min_confidence || 0.60) * 100).toFixed(0)}%
              </label>
              <Slider
                value={[(settings?.min_confidence || 0.60) * 100]}
                onValueChange={([v]) => updateSettings({...settings, min_confidence: v / 100})}
                min={40}
                max={90}
                step={5}
              />
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">
                Max Daily Loss: {((settings?.max_daily_loss_pct || 0.02) * 100).toFixed(1)}%
              </label>
              <Slider
                value={[(settings?.max_daily_loss_pct || 0.02) * 100]}
                onValueChange={([v]) => updateSettings({...settings, max_daily_loss_pct: v / 100})}
                min={0.5}
                max={10}
                step={0.5}
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Quick Trade Form */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Clock className="w-5 h-5 text-amber-400" />
          <h2 className="font-display font-semibold text-white">Queue New Trade</h2>
        </div>
        <QuickTradeForm onSubmit={queueTrade} loading={actionLoading} />
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between mb-4">
          <TabsList className="bg-slate-900 border border-slate-800">
            <TabsTrigger value="queue" className="data-[state=active]:bg-slate-800">
              <Clock className="w-4 h-4 mr-1" /> Queue
            </TabsTrigger>
            <TabsTrigger value="executed" className="data-[state=active]:bg-slate-800">
              <Check className="w-4 h-4 mr-1" /> Executed
            </TabsTrigger>
            <TabsTrigger value="positions" className="data-[state=active]:bg-slate-800">
              <Target className="w-4 h-4 mr-1" /> Positions
            </TabsTrigger>
            <TabsTrigger value="audit" className="data-[state=active]:bg-slate-800">
              <FileText className="w-4 h-4 mr-1" /> Audit Log
            </TabsTrigger>
          </TabsList>
          
          {activeTab === "queue" && (
            <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-32 bg-slate-900 border-slate-700">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="approved">Approved</SelectItem>
                <SelectItem value="rejected">Rejected</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>

        <TabsContent value="queue" className="mt-0">
          {/* Live Price Indicator */}
          {queueSymbols.length > 0 && Object.keys(queuePrices).length > 0 && (
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
              <LiveIndicator active={true} />
              <span>Live prices • Updates every 12s</span>
            </div>
          )}
          {trades.length > 0 ? (
            <div className="space-y-3">
              {trades.filter(t => t.status !== 'executed').map(trade => (
                <TradeCard
                  key={trade.id}
                  trade={trade}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onCancel={handleCancel}
                  onExecute={handleExecute}
                  loading={actionLoading}
                  livePrice={queuePrices[trade.symbol]}
                />
              ))}
            </div>
          ) : (
            <Card className="terminal-card p-8 text-center">
              <Clock className="w-10 h-10 mx-auto mb-3 text-slate-600" />
              <p className="text-slate-400 mb-1">No trades in queue</p>
              <p className="text-xs text-slate-600">Use the form above to queue a new trade</p>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="executed" className="mt-0">
          {trades.filter(t => t.status === 'executed').length > 0 ? (
            <div className="space-y-3">
              {trades.filter(t => t.status === 'executed').map(trade => (
                <TradeCard
                  key={trade.id}
                  trade={trade}
                  onApprove={handleApprove}
                  onReject={handleReject}
                  onCancel={handleCancel}
                  onExecute={handleExecute}
                  loading={actionLoading}
                  livePrice={queuePrices[trade.symbol]}
                />
              ))}
            </div>
          ) : (
            <Card className="terminal-card p-8 text-center">
              <Check className="w-10 h-10 mx-auto mb-3 text-slate-600" />
              <p className="text-slate-400 mb-1">No executed trades</p>
              <p className="text-xs text-slate-600">Approved trades will appear here after execution</p>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="positions" className="mt-0">
          {positions.length > 0 ? (
            <Card className="terminal-card overflow-hidden">
              <div className="p-3 border-b border-slate-800 flex items-center justify-between">
                <span className="text-sm text-slate-400">Positions ({positions.length})</span>
                {Object.keys(positionPrices).length > 0 && (
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <LiveIndicator active={true} />
                    <span>Live</span>
                  </div>
                )}
              </div>
              <div className="divide-y divide-slate-800">
                {positions.map((pos) => {
                  const livePrice = positionPrices[pos.symbol];
                  const qty = parseFloat(pos.qty || 0);
                  const entryPrice = parseFloat(pos.avg_entry_price || 0);
                  const marketValue = livePrice?.price ? livePrice.price * qty : parseFloat(pos.market_value || 0);
                  const costBasis = entryPrice * qty;
                  const unrealizedPL = marketValue - costBasis;
                  const unrealizedPLPct = costBasis > 0 ? ((marketValue / costBasis) - 1) * 100 : 0;
                  const isPositive = unrealizedPL >= 0;
                  
                  return (
                    <div key={pos.symbol} className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-white">{pos.symbol}</span>
                            {livePrice && <LiveIndicator active={true} />}
                          </div>
                          <p className="text-xs text-slate-500">
                            {qty.toFixed(2)} shares @ ${entryPrice.toFixed(2)}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center gap-2 justify-end">
                          <p className="font-mono text-white">${marketValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
                          {livePrice && (
                            <span className={`text-xs font-mono ${livePrice.change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              {livePrice.change_pct >= 0 ? '↑' : '↓'}{Math.abs(livePrice.change_pct).toFixed(1)}%
                            </span>
                          )}
                        </div>
                        <p className={`text-sm font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                          {isPositive ? '+' : ''}{unrealizedPLPct.toFixed(2)}% (${unrealizedPL.toFixed(2)})
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          ) : (
            <Card className="terminal-card p-8 text-center">
              <Target className="w-10 h-10 mx-auto mb-3 text-slate-600" />
              <p className="text-slate-400 mb-1">No open positions</p>
              <p className="text-xs text-slate-600">Executed buy orders will create positions here</p>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="audit" className="mt-0">
          {auditLog.length > 0 ? (
            <Card className="terminal-card overflow-hidden">
              <div className="max-h-96 overflow-y-auto">
                {auditLog.map((entry, i) => (
                  <AuditEntry key={i} entry={entry} />
                ))}
              </div>
            </Card>
          ) : (
            <Card className="terminal-card p-8 text-center">
              <FileText className="w-10 h-10 mx-auto mb-3 text-slate-600" />
              <p className="text-slate-400 mb-1">No audit entries</p>
              <p className="text-xs text-slate-600">All actions will be logged here</p>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Warning */}
      <Card className="terminal-card p-4 border-amber-500/20 bg-amber-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-200 font-medium mb-1">Paper Trading Mode</p>
            <p className="text-xs text-amber-200/70">
              This is connected to Alpaca Paper Trading only. No real money is at risk. 
              All trades go through a review queue and must be explicitly approved before execution.
              Use the kill switch to immediately halt all execution if needed.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default AutoTrade;
