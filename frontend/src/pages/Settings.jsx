import { useState } from "react";
import { useAuth } from "../App";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Settings as SettingsIcon,
  Shield,
  Bell,
  Moon,
  LogOut,
  DollarSign,
  Percent,
  AlertTriangle
} from "lucide-react";
import { toast } from "sonner";

const Settings = () => {
  const { logout } = useAuth();
  
  const [riskSettings, setRiskSettings] = useState({
    maxPositionSize: 5,
    maxDailyLoss: 2,
    maxWeeklyLoss: 5,
    maxDrawdown: 10,
    minConfidence: 60,
    cashBuffer: 10
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

  const saveSettings = () => {
    // In production, this would save to the backend
    localStorage.setItem('obaidtradez_settings', JSON.stringify({
      risk: riskSettings,
      notifications: notificationSettings,
      display: displaySettings
    }));
    toast.success("Settings saved successfully");
  };

  const handleLogout = () => {
    logout();
    toast.success("Logged out successfully");
  };

  return (
    <div className="space-y-6" data-testid="settings-page">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <SettingsIcon className="w-6 h-6 text-slate-400" />
          <h1 className="font-display text-2xl font-bold text-white">Settings</h1>
        </div>
        <p className="text-sm text-slate-500">Configure your trading preferences</p>
      </div>

      {/* Risk Management */}
      <Card className="terminal-card p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-5 h-5 text-blue-400" />
          <h2 className="font-display font-semibold text-white">Risk Management</h2>
        </div>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Position Size (% of Portfolio)</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.maxPositionSize]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, maxPositionSize: v})}
                min={1}
                max={25}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{riskSettings.maxPositionSize}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Maximum allocation for any single position</p>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Daily Loss</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.maxDailyLoss]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, maxDailyLoss: v})}
                min={1}
                max={10}
                step={0.5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{riskSettings.maxDailyLoss}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Stop trading after this daily loss</p>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Weekly Loss</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.maxWeeklyLoss]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, maxWeeklyLoss: v})}
                min={2}
                max={20}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{riskSettings.maxWeeklyLoss}%</span>
            </div>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Drawdown Tolerance</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.maxDrawdown]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, maxDrawdown: v})}
                min={5}
                max={30}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{riskSettings.maxDrawdown}%</span>
            </div>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Min Signal Confidence</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.minConfidence]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, minConfidence: v})}
                min={40}
                max={90}
                step={5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{riskSettings.minConfidence}%</span>
            </div>
            <p className="text-xs text-slate-600 mt-1">Only show signals above this confidence</p>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Cash Buffer</label>
            <div className="flex items-center gap-3">
              <Slider
                value={[riskSettings.cashBuffer]}
                onValueChange={([v]) => setRiskSettings({...riskSettings, cashBuffer: v})}
                min={0}
                max={30}
                step={5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-12">{riskSettings.cashBuffer}%</span>
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
        <Button onClick={saveSettings} className="bg-blue-600 hover:bg-blue-500">
          Save Settings
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
