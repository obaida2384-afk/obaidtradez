import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { 
  Bot,
  Play,
  Pause,
  TrendingUp,
  PiggyBank,
  AlertTriangle,
  Shield,
  Settings as SettingsIcon,
  DollarSign
} from "lucide-react";
import { toast } from "sonner";

const AutoTrade = () => {
  const [tradingEnabled, setTradingEnabled] = useState(false);
  const [investingEnabled, setInvestingEnabled] = useState(false);
  
  const [tradingSettings, setTradingSettings] = useState({
    strategy: "momentum",
    maxPositionSize: 5,
    maxDailyTrades: 3,
    minConfidence: 70,
    useStopLoss: true,
    stopLossPercent: 5
  });
  
  const [investingSettings, setInvestingSettings] = useState({
    strategy: "value",
    monthlyAmount: 1000,
    rebalanceFrequency: "monthly",
    minScore: 65,
    diversifyBySector: true
  });

  const toggleTrading = () => {
    setTradingEnabled(!tradingEnabled);
    if (!tradingEnabled) {
      toast.success("Auto-Trading enabled (Paper Mode)");
    } else {
      toast.info("Auto-Trading paused");
    }
  };

  const toggleInvesting = () => {
    setInvestingEnabled(!investingEnabled);
    if (!investingEnabled) {
      toast.success("Auto-Investing enabled");
    } else {
      toast.info("Auto-Investing paused");
    }
  };

  return (
    <div className="space-y-6" data-testid="autotrade-page">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Bot className="w-6 h-6 text-purple-400" />
          <h1 className="font-display text-2xl font-bold text-white">Automation</h1>
        </div>
        <p className="text-sm text-slate-500">Configure automated trading and investing</p>
      </div>

      {/* Auto Trading */}
      <Card className="terminal-card p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-amber-500/20 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h2 className="font-display font-semibold text-white">Auto-Trading</h2>
              <p className="text-sm text-slate-500">Short-term momentum & technical trades</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge className={tradingEnabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'}>
              {tradingEnabled ? 'Active' : 'Paused'}
            </Badge>
            <Button 
              onClick={toggleTrading}
              className={tradingEnabled ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'}
            >
              {tradingEnabled ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
              {tradingEnabled ? 'Pause' : 'Start'}
            </Button>
          </div>
        </div>
        
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Strategy</label>
            <Select 
              value={tradingSettings.strategy} 
              onValueChange={(v) => setTradingSettings({...tradingSettings, strategy: v})}
            >
              <SelectTrigger className="bg-slate-900 border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="momentum">Momentum</SelectItem>
                <SelectItem value="breakout">Breakout</SelectItem>
                <SelectItem value="mean_reversion">Mean Reversion</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Position Size (%)</label>
            <div className="flex items-center gap-2">
              <Slider
                value={[tradingSettings.maxPositionSize]}
                onValueChange={([v]) => setTradingSettings({...tradingSettings, maxPositionSize: v})}
                min={1}
                max={10}
                step={1}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-8">{tradingSettings.maxPositionSize}%</span>
            </div>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Min Confidence</label>
            <div className="flex items-center gap-2">
              <Slider
                value={[tradingSettings.minConfidence]}
                onValueChange={([v]) => setTradingSettings({...tradingSettings, minConfidence: v})}
                min={50}
                max={95}
                step={5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-10">{tradingSettings.minConfidence}%</span>
            </div>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Max Daily Trades</label>
            <Input
              type="number"
              value={tradingSettings.maxDailyTrades}
              onChange={(e) => setTradingSettings({...tradingSettings, maxDailyTrades: Number(e.target.value)})}
              className="bg-slate-900 border-slate-700"
              min={1}
              max={10}
            />
          </div>
          
          <div className="flex items-center justify-between col-span-2">
            <div>
              <p className="text-sm text-white">Use Stop-Loss</p>
              <p className="text-xs text-slate-500">Auto-exit at {tradingSettings.stopLossPercent}% loss</p>
            </div>
            <Switch
              checked={tradingSettings.useStopLoss}
              onCheckedChange={(v) => setTradingSettings({...tradingSettings, useStopLoss: v})}
            />
          </div>
        </div>
      </Card>

      {/* Auto Investing */}
      <Card className="terminal-card p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <PiggyBank className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <h2 className="font-display font-semibold text-white">Auto-Investing</h2>
              <p className="text-sm text-slate-500">Long-term value-based investing</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge className={investingEnabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-400'}>
              {investingEnabled ? 'Active' : 'Paused'}
            </Badge>
            <Button 
              onClick={toggleInvesting}
              className={investingEnabled ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'}
            >
              {investingEnabled ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
              {investingEnabled ? 'Pause' : 'Start'}
            </Button>
          </div>
        </div>
        
        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Strategy</label>
            <Select 
              value={investingSettings.strategy} 
              onValueChange={(v) => setInvestingSettings({...investingSettings, strategy: v})}
            >
              <SelectTrigger className="bg-slate-900 border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="value">Value Investing</SelectItem>
                <SelectItem value="growth">Growth Investing</SelectItem>
                <SelectItem value="dividend">Dividend Focused</SelectItem>
                <SelectItem value="balanced">Balanced</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Monthly Amount</label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                type="number"
                value={investingSettings.monthlyAmount}
                onChange={(e) => setInvestingSettings({...investingSettings, monthlyAmount: Number(e.target.value)})}
                className="pl-10 bg-slate-900 border-slate-700"
              />
            </div>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Rebalance Frequency</label>
            <Select 
              value={investingSettings.rebalanceFrequency} 
              onValueChange={(v) => setInvestingSettings({...investingSettings, rebalanceFrequency: v})}
            >
              <SelectTrigger className="bg-slate-900 border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
                <SelectItem value="quarterly">Quarterly</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Min Score Required</label>
            <div className="flex items-center gap-2">
              <Slider
                value={[investingSettings.minScore]}
                onValueChange={([v]) => setInvestingSettings({...investingSettings, minScore: v})}
                min={40}
                max={90}
                step={5}
                className="flex-1"
              />
              <span className="text-sm font-mono text-white w-10">{investingSettings.minScore}</span>
            </div>
          </div>
          
          <div className="flex items-center justify-between col-span-2">
            <div>
              <p className="text-sm text-white">Diversify by Sector</p>
              <p className="text-xs text-slate-500">Limit exposure to any single sector</p>
            </div>
            <Switch
              checked={investingSettings.diversifyBySector}
              onCheckedChange={(v) => setInvestingSettings({...investingSettings, diversifyBySector: v})}
            />
          </div>
        </div>
      </Card>

      {/* Warning */}
      <Card className="terminal-card p-4 border-red-500/20 bg-red-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-red-200 font-medium mb-1">Important Notice</p>
            <p className="text-xs text-red-200/70">
              Automated trading involves significant risk. All trades are executed on paper trading 
              accounts only. Never automate with real money unless you fully understand the risks. 
              Past performance does not guarantee future results.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default AutoTrade;
