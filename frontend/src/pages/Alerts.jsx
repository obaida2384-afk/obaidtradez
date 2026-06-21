import { useState, useEffect, useCallback } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Bell,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  AlertTriangle,
  Loader2,
  CheckCircle,
  Clock,
  RefreshCw,
  Volume2,
  X,
  History,
  Zap
} from "lucide-react";
import { toast } from "sonner";

// Alert type configuration
const ALERT_TYPES = {
  price_above: { 
    label: "Price Above", 
    icon: TrendingUp, 
    unit: "$",
    color: "text-emerald-400",
    bgColor: "bg-emerald-500/20"
  },
  price_below: { 
    label: "Price Below", 
    icon: TrendingDown, 
    unit: "$",
    color: "text-red-400",
    bgColor: "bg-red-500/20"
  },
  change_pct: { 
    label: "% Change", 
    icon: Percent, 
    unit: "%",
    color: "text-amber-400",
    bgColor: "bg-amber-500/20"
  },
  volume_spike: { 
    label: "Volume Spike", 
    icon: Volume2, 
    unit: "x",
    color: "text-purple-400",
    bgColor: "bg-purple-500/20"
  }
};

// Alert card component
const AlertCard = ({ alert, onToggle, onDelete, onReset }) => {
  const typeConfig = ALERT_TYPES[alert.alert_type] || ALERT_TYPES.price_above;
  const Icon = typeConfig.icon;
  
  return (
    <div 
      className={`p-4 rounded-lg border transition-all ${
        alert.triggered 
          ? 'border-amber-500/50 bg-amber-500/5' 
          : alert.enabled 
            ? 'border-slate-700 bg-slate-900' 
            : 'border-slate-800 bg-slate-900/50 opacity-60'
      }`}
      data-testid={`alert-card-${alert.id}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${typeConfig.bgColor}`}>
            <Icon className={`w-5 h-5 ${typeConfig.color}`} />
          </div>
          
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-lg text-white">{alert.symbol}</span>
              {alert.triggered && (
                <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30">
                  <Zap className="w-3 h-3 mr-1" /> Triggered
                </Badge>
              )}
            </div>
            <p className="text-sm text-slate-400">
              {typeConfig.label}: {typeConfig.unit}{alert.value}
            </p>
            {alert.note && (
              <p className="text-xs text-slate-500 mt-1">{alert.note}</p>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {alert.triggered ? (
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => onReset(alert.id)}
              className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
            >
              <RefreshCw className="w-3 h-3 mr-1" /> Reset
            </Button>
          ) : (
            <Switch
              checked={alert.enabled}
              onCheckedChange={() => onToggle(alert.id, !alert.enabled)}
            />
          )}
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => onDelete(alert.id)}
            className="text-slate-400 hover:text-red-400"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>
      
      {alert.triggered && alert.trigger_message && (
        <div className="mt-3 p-2 rounded bg-amber-500/10 border border-amber-500/20">
          <p className="text-xs text-amber-300">{alert.trigger_message}</p>
          <p className="text-xs text-slate-500 mt-1">
            Triggered at {new Date(alert.triggered_at).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  );
};

// History item component
const HistoryItem = ({ item }) => {
  const typeConfig = ALERT_TYPES[item.alert_type] || ALERT_TYPES.price_above;
  
  return (
    <div className="flex items-center justify-between p-3 border-b border-slate-800 last:border-0">
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded flex items-center justify-center ${typeConfig.bgColor}`}>
          <typeConfig.icon className={`w-4 h-4 ${typeConfig.color}`} />
        </div>
        <div>
          <p className="text-sm text-white font-mono">{item.symbol}</p>
          <p className="text-xs text-slate-500">{item.trigger_message}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-xs text-slate-400">
          {new Date(item.triggered_at).toLocaleDateString()}
        </p>
        <p className="text-xs text-slate-500">
          {new Date(item.triggered_at).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
};

const Alerts = () => {
  const { token } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  
  const [newAlert, setNewAlert] = useState({
    symbol: "",
    alert_type: "price_above",
    value: "",
    note: ""
  });

  const fetchAlerts = useCallback(async () => {
    try {
      const response = await fetch(`${API}/alerts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setAlerts(await response.json());
      }
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  }, [token]);

  const fetchHistory = useCallback(async () => {
    try {
      const response = await fetch(`${API}/alerts/history?limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setHistory(await response.json());
      }
    } catch (error) {
      console.error("Error fetching history:", error);
    }
  }, [token]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchAlerts(), fetchHistory()]);
      setLoading(false);
    };
    loadData();
  }, [fetchAlerts, fetchHistory]);

  const createAlert = async () => {
    if (!newAlert.symbol.trim() || !newAlert.value) {
      toast.error("Please fill in symbol and value");
      return;
    }
    
    setCreating(true);
    try {
      const response = await fetch(`${API}/alerts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          symbol: newAlert.symbol.toUpperCase(),
          alert_type: newAlert.alert_type,
          value: parseFloat(newAlert.value),
          note: newAlert.note || null
        })
      });
      
      if (response.ok) {
        const created = await response.json();
        setAlerts([created, ...alerts]);
        setNewAlert({ symbol: "", alert_type: "price_above", value: "", note: "" });
        toast.success(`Alert created for ${created.symbol}`);
      } else {
        toast.error("Failed to create alert");
      }
    } catch (error) {
      console.error("Create error:", error);
      toast.error("Error creating alert");
    } finally {
      setCreating(false);
    }
  };

  const toggleAlert = async (id, enabled) => {
    try {
      const response = await fetch(`${API}/alerts/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ enabled })
      });
      
      if (response.ok) {
        setAlerts(alerts.map(a => a.id === id ? { ...a, enabled } : a));
        toast.success(enabled ? "Alert enabled" : "Alert disabled");
      }
    } catch (error) {
      console.error("Toggle error:", error);
    }
  };

  const deleteAlert = async (id) => {
    try {
      const response = await fetch(`${API}/alerts/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        setAlerts(alerts.filter(a => a.id !== id));
        toast.success("Alert deleted");
      }
    } catch (error) {
      console.error("Delete error:", error);
    }
  };

  const resetAlert = async (id) => {
    try {
      const response = await fetch(`${API}/alerts/${id}/reset`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        setAlerts(alerts.map(a => a.id === id ? { 
          ...a, 
          triggered: false, 
          triggered_at: null,
          trigger_message: null 
        } : a));
        toast.success("Alert reset");
      }
    } catch (error) {
      console.error("Reset error:", error);
    }
  };

  const checkAlerts = async () => {
    setChecking(true);
    try {
      const response = await fetch(`${API}/alerts/check`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const result = await response.json();
        
        if (result.triggered.length > 0) {
          // Refresh alerts to show triggered state
          await fetchAlerts();
          await fetchHistory();
          
          result.triggered.forEach(t => {
            toast.success(t.message, {
              icon: <Zap className="w-4 h-4 text-amber-400" />,
              duration: 5000
            });
          });
        } else {
          toast.info(`Checked ${result.checked} alerts - no triggers`);
        }
      }
    } catch (error) {
      console.error("Check error:", error);
      toast.error("Error checking alerts");
    } finally {
      setChecking(false);
    }
  };

  const activeAlerts = alerts.filter(a => !a.triggered);
  const triggeredAlerts = alerts.filter(a => a.triggered);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-slate-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="alerts-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Bell className="w-6 h-6 text-amber-400" />
            <h1 className="font-display text-2xl font-bold text-white">Price Alerts</h1>
            {alerts.length > 0 && (
              <Badge variant="outline" className="border-slate-700">
                {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500">Get notified when prices hit your targets</p>
        </div>
        
        <div className="flex gap-2">
          <Button 
            variant="outline"
            size="sm"
            onClick={() => setShowHistory(!showHistory)}
            className="border-slate-700"
          >
            <History className="w-4 h-4 mr-1" />
            History
          </Button>
          <Button 
            onClick={checkAlerts}
            disabled={checking || alerts.length === 0}
            className="bg-amber-600 hover:bg-amber-500"
            data-testid="check-alerts-btn"
          >
            {checking ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-1" />
                Check Now
              </>
            )}
          </Button>
        </div>
      </div>

      {/* History Panel */}
      {showHistory && (
        <Card className="terminal-card overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="font-medium text-white">Alert History</h3>
            <Button variant="ghost" size="sm" onClick={() => setShowHistory(false)}>
              <X className="w-4 h-4" />
            </Button>
          </div>
          {history.length > 0 ? (
            <div className="max-h-64 overflow-y-auto">
              {history.map((item, i) => (
                <HistoryItem key={i} item={item} />
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 text-sm">
              No alert history yet
            </div>
          )}
        </Card>
      )}

      {/* Create Alert */}
      <Card className="terminal-card p-4">
        <h2 className="font-display font-semibold text-white mb-4">Create New Alert</h2>
        
        <div className="flex flex-wrap gap-3">
          <Input
            value={newAlert.symbol}
            onChange={(e) => setNewAlert({...newAlert, symbol: e.target.value.toUpperCase()})}
            placeholder="Symbol (e.g. AAPL)"
            className="w-32 bg-slate-900 border-slate-700 font-mono"
            data-testid="alert-symbol-input"
          />
          
          <Select 
            value={newAlert.alert_type} 
            onValueChange={(v) => setNewAlert({...newAlert, alert_type: v})}
          >
            <SelectTrigger className="w-40 bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ALERT_TYPES).map(([key, config]) => (
                <SelectItem key={key} value={key}>
                  <div className="flex items-center gap-2">
                    <config.icon className={`w-4 h-4 ${config.color}`} />
                    {config.label}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-sm">
              {ALERT_TYPES[newAlert.alert_type]?.unit || "$"}
            </span>
            <Input
              type="number"
              value={newAlert.value}
              onChange={(e) => setNewAlert({...newAlert, value: e.target.value})}
              placeholder="Value"
              className="w-28 pl-8 bg-slate-900 border-slate-700"
              data-testid="alert-value-input"
            />
          </div>
          
          <Input
            value={newAlert.note}
            onChange={(e) => setNewAlert({...newAlert, note: e.target.value})}
            placeholder="Note (optional)"
            className="w-40 bg-slate-900 border-slate-700"
          />
          
          <Button 
            onClick={createAlert} 
            disabled={creating}
            className="bg-amber-600 hover:bg-amber-500" 
            data-testid="create-alert-btn"
          >
            {creating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Plus className="w-4 h-4 mr-1" /> Create Alert
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Triggered Alerts */}
      {triggeredAlerts.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-amber-400 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Triggered Alerts ({triggeredAlerts.length})
          </h2>
          <div className="space-y-3">
            {triggeredAlerts.map(alert => (
              <AlertCard 
                key={alert.id}
                alert={alert}
                onToggle={toggleAlert}
                onDelete={deleteAlert}
                onReset={resetAlert}
              />
            ))}
          </div>
        </div>
      )}

      {/* Active Alerts */}
      <div>
        <h2 className="text-sm font-medium text-slate-400 mb-3">
          Active Alerts ({activeAlerts.length})
        </h2>
        
        {activeAlerts.length > 0 ? (
          <div className="space-y-3">
            {activeAlerts.map(alert => (
              <AlertCard 
                key={alert.id}
                alert={alert}
                onToggle={toggleAlert}
                onDelete={deleteAlert}
                onReset={resetAlert}
              />
            ))}
          </div>
        ) : (
          <Card className="terminal-card p-8 text-center">
            <Bell className="w-10 h-10 mx-auto mb-3 text-slate-600" />
            <p className="text-slate-500 mb-1">No active alerts</p>
            <p className="text-xs text-slate-600">Create an alert above to get started</p>
          </Card>
        )}
      </div>

      {/* Info */}
      <Card className="terminal-card p-4 border-blue-500/20 bg-blue-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-blue-200 font-medium mb-1">How Alerts Work</p>
            <p className="text-xs text-blue-200/70">
              Alerts are stored persistently and checked against real-time market data. 
              Click "Check Now" to manually verify all alerts, or they will be checked 
              automatically when you visit this page. Triggered alerts can be reset to 
              activate them again.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Alerts;
