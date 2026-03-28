import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Bell,
  Plus,
  Trash2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  AlertTriangle
} from "lucide-react";
import { toast } from "sonner";

const Alerts = () => {
  const [alerts, setAlerts] = useState([
    { id: 1, symbol: "AAPL", type: "price_above", value: 200, enabled: true },
    { id: 2, symbol: "TSLA", type: "price_below", value: 250, enabled: true },
    { id: 3, symbol: "NVDA", type: "change_pct", value: 5, enabled: false }
  ]);
  
  const [newAlert, setNewAlert] = useState({
    symbol: "",
    type: "price_above",
    value: ""
  });

  const alertTypes = {
    "price_above": { label: "Price Above", icon: TrendingUp, unit: "$" },
    "price_below": { label: "Price Below", icon: TrendingDown, unit: "$" },
    "change_pct": { label: "% Change", icon: Percent, unit: "%" }
  };

  const addAlert = () => {
    if (!newAlert.symbol.trim() || !newAlert.value) {
      toast.error("Please fill in all fields");
      return;
    }
    
    const alert = {
      id: Date.now(),
      symbol: newAlert.symbol.toUpperCase(),
      type: newAlert.type,
      value: parseFloat(newAlert.value),
      enabled: true
    };
    
    setAlerts([...alerts, alert]);
    setNewAlert({ symbol: "", type: "price_above", value: "" });
    toast.success(`Alert created for ${alert.symbol}`);
  };

  const toggleAlert = (id) => {
    setAlerts(alerts.map(a => 
      a.id === id ? { ...a, enabled: !a.enabled } : a
    ));
  };

  const deleteAlert = (id) => {
    setAlerts(alerts.filter(a => a.id !== id));
    toast.success("Alert deleted");
  };

  return (
    <div className="space-y-6" data-testid="alerts-page">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Bell className="w-6 h-6 text-amber-400" />
          <h1 className="font-display text-2xl font-bold text-white">Price Alerts</h1>
        </div>
        <p className="text-sm text-slate-500">Get notified when prices hit your targets</p>
      </div>

      {/* Create Alert */}
      <Card className="terminal-card p-4">
        <h2 className="font-display font-semibold text-white mb-4">Create New Alert</h2>
        
        <div className="flex flex-wrap gap-3">
          <Input
            value={newAlert.symbol}
            onChange={(e) => setNewAlert({...newAlert, symbol: e.target.value.toUpperCase()})}
            placeholder="Symbol (e.g. AAPL)"
            className="w-32 bg-slate-900 border-slate-700"
            data-testid="alert-symbol-input"
          />
          
          <Select value={newAlert.type} onValueChange={(v) => setNewAlert({...newAlert, type: v})}>
            <SelectTrigger className="w-40 bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="price_above">Price Above</SelectItem>
              <SelectItem value="price_below">Price Below</SelectItem>
              <SelectItem value="change_pct">% Change</SelectItem>
            </SelectContent>
          </Select>
          
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
              {alertTypes[newAlert.type].unit}
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
          
          <Button onClick={addAlert} className="bg-amber-600 hover:bg-amber-500" data-testid="create-alert-btn">
            <Plus className="w-4 h-4 mr-1" /> Create Alert
          </Button>
        </div>
      </Card>

      {/* Active Alerts */}
      <Card className="terminal-card overflow-hidden">
        <div className="p-4 border-b border-slate-800">
          <h2 className="font-display font-semibold text-white">Your Alerts ({alerts.length})</h2>
        </div>
        
        {alerts.length > 0 ? (
          <div className="divide-y divide-slate-800">
            {alerts.map((alert) => {
              const typeConfig = alertTypes[alert.type];
              const Icon = typeConfig.icon;
              
              return (
                <div 
                  key={alert.id} 
                  className={`p-4 flex items-center justify-between ${!alert.enabled ? 'opacity-50' : ''}`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-md flex items-center justify-center ${
                      alert.type === 'price_above' ? 'bg-emerald-500/20' :
                      alert.type === 'price_below' ? 'bg-red-500/20' : 'bg-amber-500/20'
                    }`}>
                      <Icon className={`w-5 h-5 ${
                        alert.type === 'price_above' ? 'text-emerald-400' :
                        alert.type === 'price_below' ? 'text-red-400' : 'text-amber-400'
                      }`} />
                    </div>
                    
                    <div>
                      <p className="font-mono font-medium text-white">{alert.symbol}</p>
                      <p className="text-sm text-slate-500">
                        {typeConfig.label}: {typeConfig.unit}{alert.value}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4">
                    <Switch
                      checked={alert.enabled}
                      onCheckedChange={() => toggleAlert(alert.id)}
                    />
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => deleteAlert(alert.id)}
                      className="text-slate-400 hover:text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500">
            No alerts configured. Create one above!
          </div>
        )}
      </Card>

      {/* Info */}
      <Card className="terminal-card p-4 border-blue-500/20 bg-blue-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-blue-200 font-medium mb-1">Alert Notifications</p>
            <p className="text-xs text-blue-200/70">
              Alerts are checked in real-time during market hours. You'll receive notifications 
              when your conditions are met. Make sure to keep the app open or enable push notifications.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Alerts;
