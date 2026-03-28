import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { 
  History,
  Play,
  TrendingUp,
  TrendingDown,
  Calendar,
  Loader2,
  AlertTriangle,
  DollarSign
} from "lucide-react";

const Backtesting = () => {
  const [symbol, setSymbol] = useState("");
  const [strategy, setStrategy] = useState("momentum");
  const [period, setPeriod] = useState("1y");
  const [initialCapital, setInitialCapital] = useState(10000);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);

  const runBacktest = async () => {
    if (!symbol.trim()) return;
    setRunning(true);
    
    // Simulated backtest - in production this would call a real API
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Mock results
    const mockResults = {
      symbol: symbol.toUpperCase(),
      strategy: strategy,
      period: period,
      initial_capital: initialCapital,
      final_value: initialCapital * (1 + Math.random() * 0.5 - 0.1),
      total_return: (Math.random() * 60 - 10).toFixed(2),
      max_drawdown: (Math.random() * 25 + 5).toFixed(2),
      win_rate: (Math.random() * 30 + 50).toFixed(1),
      total_trades: Math.floor(Math.random() * 50 + 10),
      sharpe_ratio: (Math.random() * 2 + 0.5).toFixed(2),
      best_trade: (Math.random() * 15 + 2).toFixed(2),
      worst_trade: (Math.random() * -10 - 2).toFixed(2)
    };
    
    setResults(mockResults);
    setRunning(false);
  };

  return (
    <div className="space-y-6" data-testid="backtesting-page">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <History className="w-6 h-6 text-cyan-400" />
          <h1 className="font-display text-2xl font-bold text-white">Backtesting</h1>
        </div>
        <p className="text-sm text-slate-500">Test trading strategies against historical data</p>
      </div>

      {/* Configuration */}
      <Card className="terminal-card p-6">
        <h2 className="text-lg font-display font-semibold text-white mb-4">Strategy Configuration</h2>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Symbol</label>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL"
              className="bg-slate-900 border-slate-700"
              data-testid="backtest-symbol"
            />
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Strategy</label>
            <Select value={strategy} onValueChange={setStrategy}>
              <SelectTrigger className="bg-slate-900 border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="momentum">Momentum</SelectItem>
                <SelectItem value="mean_reversion">Mean Reversion</SelectItem>
                <SelectItem value="breakout">Breakout</SelectItem>
                <SelectItem value="ma_crossover">MA Crossover</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Time Period</label>
            <Select value={period} onValueChange={setPeriod}>
              <SelectTrigger className="bg-slate-900 border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="3m">3 Months</SelectItem>
                <SelectItem value="6m">6 Months</SelectItem>
                <SelectItem value="1y">1 Year</SelectItem>
                <SelectItem value="2y">2 Years</SelectItem>
                <SelectItem value="5y">5 Years</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Initial Capital</label>
            <div className="flex items-center gap-2">
              <DollarSign className="w-4 h-4 text-slate-500" />
              <Input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(Number(e.target.value))}
                className="bg-slate-900 border-slate-700"
              />
            </div>
          </div>
        </div>

        <Button
          onClick={runBacktest}
          disabled={running || !symbol.trim()}
          className="bg-cyan-600 hover:bg-cyan-500"
          data-testid="run-backtest-btn"
        >
          {running ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Running Backtest...
            </>
          ) : (
            <>
              <Play className="w-4 h-4 mr-2" />
              Run Backtest
            </>
          )}
        </Button>
      </Card>

      {/* Results */}
      {results && (
        <Card className="terminal-card p-6">
          <h2 className="text-lg font-display font-semibold text-white mb-4">
            Backtest Results: {results.symbol} - {results.strategy}
          </h2>
          
          <div className="grid md:grid-cols-4 gap-4 mb-6">
            <div className="p-4 rounded bg-slate-900 border border-slate-800">
              <p className="text-xs text-slate-500 mb-1">Total Return</p>
              <p className={`font-mono text-2xl ${parseFloat(results.total_return) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {parseFloat(results.total_return) >= 0 ? '+' : ''}{results.total_return}%
              </p>
            </div>
            
            <div className="p-4 rounded bg-slate-900 border border-slate-800">
              <p className="text-xs text-slate-500 mb-1">Final Value</p>
              <p className="font-mono text-2xl text-white">
                ${results.final_value.toLocaleString(undefined, {maximumFractionDigits: 2})}
              </p>
            </div>
            
            <div className="p-4 rounded bg-slate-900 border border-slate-800">
              <p className="text-xs text-slate-500 mb-1">Max Drawdown</p>
              <p className="font-mono text-2xl text-red-400">
                -{results.max_drawdown}%
              </p>
            </div>
            
            <div className="p-4 rounded bg-slate-900 border border-slate-800">
              <p className="text-xs text-slate-500 mb-1">Sharpe Ratio</p>
              <p className="font-mono text-2xl text-white">
                {results.sharpe_ratio}
              </p>
            </div>
          </div>
          
          <div className="grid md:grid-cols-4 gap-4">
            <div className="p-3 rounded bg-slate-800/50">
              <p className="text-xs text-slate-500">Win Rate</p>
              <p className="font-mono text-lg text-white">{results.win_rate}%</p>
            </div>
            <div className="p-3 rounded bg-slate-800/50">
              <p className="text-xs text-slate-500">Total Trades</p>
              <p className="font-mono text-lg text-white">{results.total_trades}</p>
            </div>
            <div className="p-3 rounded bg-slate-800/50">
              <p className="text-xs text-slate-500">Best Trade</p>
              <p className="font-mono text-lg text-emerald-400">+{results.best_trade}%</p>
            </div>
            <div className="p-3 rounded bg-slate-800/50">
              <p className="text-xs text-slate-500">Worst Trade</p>
              <p className="font-mono text-lg text-red-400">{results.worst_trade}%</p>
            </div>
          </div>
        </Card>
      )}

      {/* Info */}
      <Card className="terminal-card p-4 border-amber-500/20 bg-amber-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-200 font-medium mb-1">Backtesting Disclaimer</p>
            <p className="text-xs text-amber-200/70">
              Past performance does not guarantee future results. Backtests use historical data and 
              do not account for slippage, commissions, or market impact. Use results for research only.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Backtesting;
