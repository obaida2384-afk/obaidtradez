import { useState, useEffect } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Progress } from "@/components/ui/progress";
import { 
  Settings as SettingsIcon,
  Shield,
  Bell,
  Moon,
  LogOut,
  DollarSign,
  Percent,
  AlertTriangle,
  Calculator,
  TrendingUp,
  TrendingDown,
  Target,
  Loader2,
  Save,
  RefreshCw
} from "lucide-react";
import { toast } from "sonner";

// Position Size Calculator Component
const PositionCalculator = ({ token }) => {
  const [calculating, setCalculating] = useState(false);
  const [inputs, setInputs] = useState({
    account_value: 10000,
    entry_price: 100,
    stop_loss_price: 95,
    risk_per_trade: 0.02,
    max_position_pct: 0.10
  });
  const [result, setResult] = useState(null);

  const calculate = async () => {
    setCalculating(true);
    try {
      const response = await fetch(`${API}/risk/position-size`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(inputs)
      });
      if (response.ok) {
        setResult(await response.json());
      }
    } catch (error) {
      console.error("Calculation error:", error);
    } finally {
      setCalculating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <label className="text-xs text-slate-500 mb-1 block">Account Value</label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              type="number"
              value={inputs.account_value}
              onChange={(e) => setInputs({...inputs, account_value: parseFloat(e.target.value)})}
              className="pl-9 bg-slate-900 border-slate-700"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-slate-500 mb-1 block">Entry Price</label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              type="number"
              value={inputs.entry_price}
              onChange={(e) => setInputs({...inputs, entry_price: parseFloat(e.target.value)})}
              className="pl-9 bg-slate-900 border-slate-700"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-slate-500 mb-1 block">Stop Loss</label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              type="number"
              value={inputs.stop_loss_price}
              onChange={(e) => setInputs({...inputs, stop_loss_price: parseFloat(e.target.value)})}
              className="pl-9 bg-slate-900 border-slate-700"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-slate-500 mb-1 block">Risk Per Trade</label>
          <div className="flex items-center gap-2">
            <Slider
              value={[inputs.risk_per_trade * 100]}
              onValueChange={([v]) => setInputs({...inputs, risk_per_trade: v / 100})}
              min={0.5}
              max={5}
              step={0.5}
              className="flex-1"
            />
            <span className="text-sm font-mono text-white w-12">{(inputs.risk_per_trade * 100).toFixed(1)}%</span>
          </div>
        </div>
        <div>
          <label className="text-xs text-slate-500 mb-1 block">Max Position</label>
          <div className="flex items-center gap-2">
            <Slider
              value={[inputs.max_position_pct * 100]}
              onValueChange={([v]) => setInputs({...inputs, max_position_pct: v / 100})}
              min={5}
              max={25}
              step={1}
              className="flex-1"
            />
            <span className="text-sm font-mono text-white w-12">{(inputs.max_position_pct * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className="flex items-end">
          <Button onClick={calculate} disabled={calculating} className="w-full bg-blue-600 hover:bg-blue-500">
            {calculating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4 mr-1" />}
            Calculate
          </Button>
        </div>
      </div>

      {result && !result.error && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 p-4 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-center">
            <p className="text-xs text-slate-500">Shares</p>
            <p className="text-2xl font-mono font-bold text-white">{result.shares}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Position Value</p>
            <p className="text-xl font-mono text-emerald-400">${result.position_value.toLocaleString()}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Position %</p>
            <p className="text-xl font-mono text-white">{result.position_pct}%</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Risk Amount</p>
            <p className="text-xl font-mono text-red-400">${result.risk_amount}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Risk %</p>
            <p className="text-xl font-mono text-amber-400">{result.risk_pct}%</p>
          </div>
        </div>
      )}
    </div>
  );
};

// Risk/Reward Calculator Component
const RiskRewardCalculator = ({ token }) => {
  const [calculating, setCalculating] = useState(false);
  const [inputs, setInputs] = useState({
    entry_price: 100,
    stop_loss_price: 95,
    take_profit_price: 115
  });
  const [result, setResult] = useState(null);

  const calculate = async () => {
    setCalculating(true);
    try {
      const response = await fetch(`${API}/risk/risk-reward`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(inputs)
      });
      if (response.ok) {
        setResult(await response.json());
      }
    } catch (error) {
      console.error("Calculation error:", error);
    } finally {
      setCalculating(false);
    }
  };

  const getQualityColor = (quality) => {
    switch (quality) {
      case "Excellent": return "text-emerald-400";
      case "Good": return "text-blue-400";
      case "Fair": return "text-amber-400";
      default: return "text-red-400";
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <label className="text-xs text-slate-500 mb-1 block">Entry Price</label>
          <div className="relative">
            <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              type="number"
              value={inputs.entry_price}
              onChange={(e) => setInputs({...inputs, entry_price: parseFloat(e.target.value)})}
              className="pl-9 bg-slate-900 border-slate-700"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-slate-500 mb-1 block">Stop Loss</label>
          <div className="relative">
            <TrendingDown className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-red-400" />
            <Input
              type="number"
              value={inputs.stop_loss_price}
              onChange={(e) => setInputs({...inputs, stop_loss_price: parseFloat(e.target.value)})}
              className="pl-9 bg-slate-900 border-slate-700"
            />
          </div>
        </div>
        <div>
          <label className="text-xs text-slate-500 mb-1 block">Take Profit</label>
          <div className="relative">
            <TrendingUp className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-emerald-400" />
            <Input
              type="number"
              value={inputs.take_profit_price}
              onChange={(e) => setInputs({...inputs, take_profit_price: parseFloat(e.target.value)})}
              className="pl-9 bg-slate-900 border-slate-700"
            />
          </div>
        </div>
        <div className="flex items-end">
          <Button onClick={calculate} disabled={calculating} className="w-full bg-purple-600 hover:bg-purple-500">
            {calculating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4 mr-1" />}
            Calculate
          </Button>
        </div>
      </div>

      {result && !result.error && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-center">
            <p className="text-xs text-slate-500">Risk/Reward</p>
            <p className="text-2xl font-mono font-bold text-white">{result.ratio_display}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Quality</p>
            <p className={`text-xl font-bold ${getQualityColor(result.quality)}`}>{result.quality}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Risk</p>
            <p className="text-lg font-mono text-red-400">${result.risk} ({result.risk_pct}%)</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-slate-500">Reward</p>
            <p className="text-lg font-mono text-emerald-400">${result.reward} ({result.reward_pct}%)</p>
          </div>
        </div>
      )}
    </div>
  );
};

// Daily Risk Status Component
const DailyRiskStatus = ({ token }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API}/risk/daily-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setStatus(await response.json());
      }
    } catch (error) {
      console.error("Error fetching risk status:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="w-5 h-5 animate-spin text-slate-500" />
      </div>
    );
  }

  if (!status || status.account_value === 0) {
    return (
      <div className="p-4 text-center text-slate-500 text-sm">
        Connect Alpaca account to view daily risk status
      </div>
    );
  }

  const statusColors = {
    safe: "bg-emerald-500",
    caution: "bg-amber-500",
    stopped: "bg-red-500"
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-3 rounded bg-slate-900 border border-slate-800">
          <p className="text-xs text-slate-500">Account Value</p>
          <p className="text-xl font-mono text-white">${status.account_value.toLocaleString()}</p>
        </div>
        <div className="p-3 rounded bg-slate-900 border border-slate-800">
          <p className="text-xs text-slate-500">Daily P&L</p>
          <p className={`text-xl font-mono ${status.daily_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {status.daily_pnl >= 0 ? '+' : ''}${status.daily_pnl.toLocaleString()}
          </p>
        </div>
        <div className="p-3 rounded bg-slate-900 border border-slate-800">
          <p className="text-xs text-slate-500">Daily P&L %</p>
          <p className={`text-xl font-mono ${status.daily_pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {status.daily_pnl_pct >= 0 ? '+' : ''}{status.daily_pnl_pct.toFixed(2)}%
          </p>
        </div>
        <div className="p-3 rounded bg-slate-900 border border-slate-800">
          <p className="text-xs text-slate-500">Status</p>
          <div className="flex items-center gap-2 mt-1">
            <div className={`w-3 h-3 rounded-full ${statusColors[status.risk_status]}`} />
            <p className="text-lg font-medium text-white capitalize">{status.risk_status}</p>
          </div>
        </div>
      </div>
      
      {!status.can_trade && (
        <div className="p-3 rounded bg-red-500/10 border border-red-500/30 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <p className="text-sm text-red-400">
            Trading paused - Daily loss limit ({status.max_daily_loss_pct}%) exceeded
          </p>
        </div>
      )}
    </div>
  );
};

const Settings = () => {
  const { token, logout } = useAuth();
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  
  const [riskSettings, setRiskSettings] = useState({
    max_position_size: 0.05,
    max_daily_loss: 0.02,
    max_weekly_loss: 0.05,
    max_drawdown: 0.10,
    min_confidence: 0.60,
    cash_buffer: 0.10,
    default_stop_loss_pct: 0.05,
    default_take_profit_pct: 0.10
  });
  
  const [notificationSettings, setNotificationSettings] = useState({
    priceAlerts: true,
    tradeExecuted: true,
    dailySummary: true,
    weeklyReport: false
  });
  
  const [displaySettings, setDisplaySettings] = useState({
    theme: "dark",
    compactMode: false,
    showProfitInPercent: true
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${API}/risk/settings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setRiskSettings(data);
      }
    } catch (error) {
      console.error("Error fetching settings:", error);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API}/risk/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(riskSettings)
      });
      
      if (response.ok) {
        // Also save local settings
        localStorage.setItem('obaidtradez_settings', JSON.stringify({
          risk: riskSettings,
          notifications: notificationSettings,
          display: displaySettings
        }));
        toast.success("Settings saved successfully");
      } else {
        toast.error("Failed to save settings");
      }
    } catch (error) {
      console.error("Save error:", error);
      toast.error("Error saving settings");
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    toast.success("Logged out successfully");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-slate-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="settings-page">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <SettingsIcon className="w-6 h-6 text-slate-400" />
          <h1 className="font-display text-2xl font-bold text-white">Settings</h1>
        </div>
        <p className="text-sm text-slate-500">Configure your trading preferences and risk management</p>
      </div>

      {/* Daily Risk Status */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <h2 className="font-display font-semibold text-white">Daily Risk Status</h2>
        </div>
        <DailyRiskStatus token={token} />
      </Card>

      {/* Position Size Calculator */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Calculator className="w-5 h-5 text-blue-400" />
          <h2 className="font-display font-semibold text-white">Position Size Calculator</h2>
        </div>
        <PositionCalculator token={token} />
      </Card>

      {/* Risk/Reward Calculator */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <Target className="w-5 h-5 text-purple-400" />
          <h2 className="font-display font-semibold text-white">Risk/Reward Calculator</h2>
        </div>
        <RiskRewardCalculator token={token} />
      </Card>

      {/* Risk Management Settings */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-5 h-5 text-emerald-400" />
          <h2 className="font-display font-semibold text-white">Risk Management Rules</h2>
        </div>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Position Size (% of Portfolio)</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.max_position_size * 100]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, max_position_size: v / 100})}
                min={1}
                max={25}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{(riskSettings.max_position_size * 100).toFixed(0)}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Maximum allocation for any single position</p>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Daily Loss</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.max_daily_loss * 100]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, max_daily_loss: v / 100})}
                min={0.5}
                max={10}
                step={0.5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{(riskSettings.max_daily_loss * 100).toFixed(1)}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Stop trading after this daily loss</p>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Weekly Loss</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.max_weekly_loss * 100]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, max_weekly_loss: v / 100})}
                min={2}
                max={20}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{(riskSettings.max_weekly_loss * 100).toFixed(0)}%</span>
            </div>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Drawdown Tolerance</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.max_drawdown * 100]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, max_drawdown: v / 100})}
                min={5}
                max={30}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{(riskSettings.max_drawdown * 100).toFixed(0)}%</span>
            </div>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Default Stop Loss</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.default_stop_loss_pct * 100]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, default_stop_loss_pct: v / 100})}
                min={1}
                max={15}
                step={0.5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{(riskSettings.default_stop_loss_pct * 100).toFixed(1)}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Default stop loss for new trades</p>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Default Take Profit</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.default_take_profit_pct * 100]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, default_take_profit_pct: v / 100})}
                min={2}
                max={50}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{(riskSettings.default_take_profit_pct * 100).toFixed(0)}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Default take profit target</p>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Min Signal Confidence</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.min_confidence * 100]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, min_confidence: v / 100})}
                min={40}
                max={90}
                step={5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{(riskSettings.min_confidence * 100).toFixed(0)}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Only show signals above this confidence</p>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Cash Buffer</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.cash_buffer * 100]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, cash_buffer: v / 100})}
                min={0}
                max={50}
                step={5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{(riskSettings.cash_buffer * 100).toFixed(0)}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Keep this % of portfolio in cash</p>
          </div>
        </div>
      </Card>

      {/* Notifications */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Bell className="w-5 h-5 text-amber-400" />
          <h2 className="font-display font-semibold text-white">Notifications</h2>
        </div>
        
        <div className="space-y-4">
          {[
            { key: 'priceAlerts', label: 'Price Alerts', desc: 'Get notified when price targets are hit' },
            { key: 'tradeExecuted', label: 'Trade Executed', desc: 'Notify when automated trades complete' },
            { key: 'dailySummary', label: 'Daily Summary', desc: 'End of day portfolio summary' },
            { key: 'weeklyReport', label: 'Weekly Report', desc: 'Weekly performance report' }
          ].map(({ key, label, desc }) => (
            <div key={key} className="flex items-center justify-between">
              <div>
                <p className="text-sm text-white">{label}</p>
                <p className="text-xs text-slate-500">{desc}</p>
              </div>
              <Switch
                checked={notificationSettings[key]}
                onCheckedChange={(v) => setNotificationSettings({...notificationSettings, [key]: v})}
              />
            </div>
          ))}
        </div>
      </Card>

      {/* Display */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Moon className="w-5 h-5 text-purple-400" />
          <h2 className="font-display font-semibold text-white">Display</h2>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-white">Compact Mode</p>
              <p className="text-xs text-slate-500">Show more data with less spacing</p>
            </div>
            <Switch
              checked={displaySettings.compactMode}
              onCheckedChange={(v) => setDisplaySettings({...displaySettings, compactMode: v})}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-white">Show P&L in Percentage</p>
              <p className="text-xs text-slate-500">Display profits as % instead of $</p>
            </div>
            <Switch
              checked={displaySettings.showProfitInPercent}
              onCheckedChange={(v) => setDisplaySettings({...displaySettings, showProfitInPercent: v})}
            />
          </div>
        </div>
      </Card>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <Button onClick={saveSettings} disabled={saving} className="bg-emerald-600 hover:bg-emerald-500">
          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
          Save All Settings
        </Button>
        
        <Button onClick={handleLogout} variant="outline" className="border-red-500/30 text-red-400 hover:bg-red-500/10">
          <LogOut className="w-4 h-4 mr-2" />
          Logout
        </Button>
      </div>
    </div>
  );
};

export default Settings;
