import { useState, useEffect } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { 
  History,
  Play,
  TrendingUp,
  TrendingDown,
  Calendar,
  Loader2,
  AlertTriangle,
  DollarSign,
  BarChart3,
  Target,
  Percent,
  ChevronRight,
  Clock,
  RefreshCw
} from "lucide-react";
import { toast } from "sonner";

// Simple equity curve chart component
const EquityChart = ({ data, initialCapital }) => {
  if (!data || data.length === 0) return null;
  
  const maxEquity = Math.max(...data.map(d => d.equity));
  const minEquity = Math.min(...data.map(d => d.equity));
  const range = maxEquity - minEquity || 1;
  
  return (
    <div className="h-40 flex items-end gap-px">
      {data.map((point, i) => {
        const height = ((point.equity - minEquity) / range) * 100;
        const isProfit = point.equity >= initialCapital;
        
        return (
          <div
            key={i}
            className={`flex-1 rounded-t transition-all ${isProfit ? 'bg-emerald-500/60' : 'bg-red-500/60'}`}
            style={{ height: `${Math.max(height, 2)}%` }}
            title={`${point.date}: $${point.equity.toLocaleString()}`}
          />
        );
      })}
    </div>
  );
};

// Trade row component
const TradeRow = ({ trade, index }) => {
  const isProfit = trade.pnl >= 0;
  
  return (
    <div className={`flex items-center justify-between p-3 ${index % 2 === 0 ? 'bg-slate-900/50' : ''}`}>
      <div className="flex items-center gap-4">
        <span className="text-xs text-slate-500 w-6">{index + 1}</span>
        <div>
          <p className="text-sm text-slate-300">{trade.entry_date}</p>
          <p className="text-xs text-slate-500">→ {trade.exit_date}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-sm font-mono text-slate-300">
          ${trade.entry_price} → ${trade.exit_price}
        </p>
        <p className={`text-xs font-mono ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
          {isProfit ? '+' : ''}{trade.pnl_pct.toFixed(2)}% (${trade.pnl.toFixed(2)})
        </p>
      </div>
    </div>
  );
};

// Strategy card component
const StrategyCard = ({ strategy, selected, onSelect }) => {
  const icons = {
    momentum: TrendingUp,
    mean_reversion: RefreshCw,
    breakout: Target,
    ma_crossover: BarChart3,
    value: DollarSign
  };
  
  const Icon = icons[strategy.id] || BarChart3;
  
  return (
    <button
      onClick={() => onSelect(strategy.id)}
      className={`p-4 rounded-lg border text-left transition-all ${
        selected === strategy.id 
          ? 'border-cyan-500 bg-cyan-500/10' 
          : 'border-slate-700 bg-slate-900 hover:border-slate-600'
      }`}
    >
      <div className="flex items-center gap-3 mb-2">
        <Icon className={`w-5 h-5 ${selected === strategy.id ? 'text-cyan-400' : 'text-slate-400'}`} />
        <span className={`font-medium ${selected === strategy.id ? 'text-cyan-400' : 'text-white'}`}>
          {strategy.name}
        </span>
      </div>
      <p className="text-xs text-slate-500">{strategy.description}</p>
    </button>
  );
};

const Backtesting = () => {
  const { token } = useAuth();
  const [symbol, setSymbol] = useState("");
  const [strategy, setStrategy] = useState("momentum");
  const [period, setPeriod] = useState("1y");
  const [initialCapital, setInitialCapital] = useState(10000);
  const [stopLoss, setStopLoss] = useState(5);
  const [takeProfit, setTakeProfit] = useState(10);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [strategies, setStrategies] = useState([]);
  const [history, setHistory] = useState([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    fetchStrategies();
    fetchHistory();
  }, []);

  const fetchStrategies = async () => {
    try {
      const response = await fetch(`${API}/backtest/strategies`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setStrategies(await response.json());
      }
    } catch (error) {
      console.error("Error fetching strategies:", error);
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API}/backtest/history?limit=5`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setHistory(await response.json());
      }
    } catch (error) {
      console.error("Error fetching history:", error);
    }
  };

  const runBacktest = async () => {
    if (!symbol.trim()) {
      toast.error("Please enter a symbol");
      return;
    }
    
    setRunning(true);
    setResults(null);
    
    try {
      const response = await fetch(`${API}/backtest/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          strategy,
          period,
          initial_capital: initialCapital,
          stop_loss_pct: stopLoss / 100,
          take_profit_pct: takeProfit / 100
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.error) {
          toast.error(data.error);
        } else {
          setResults(data);
          fetchHistory(); // Refresh history
          toast.success("Backtest completed");
        }
      } else {
        toast.error("Failed to run backtest");
      }
    } catch (error) {
      console.error("Backtest error:", error);
      toast.error("Error running backtest");
    } finally {
      setRunning(false);
    }
  };

  const loadFromHistory = (item) => {
    setSymbol(item.symbol);
    setStrategy(item.strategy);
    setPeriod(item.period);
    setResults(item.result);
    setShowHistory(false);
  };

  return (
    <div className="space-y-6" data-testid="backtesting-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <History className="w-6 h-6 text-cyan-400" />
            <h1 className="font-display text-2xl font-bold text-white">Backtesting</h1>
          </div>
          <p className="text-sm text-slate-500">Test trading strategies against historical market data</p>
        </div>
        
        <Button 
          variant="outline" 
          size="sm"
          onClick={() => setShowHistory(!showHistory)}
          className="border-slate-700"
        >
          <Clock className="w-4 h-4 mr-1" />
          History ({history.length})
        </Button>
      </div>

      {/* History Panel */}
      {showHistory && history.length > 0 && (
        <Card className="terminal-card p-4">
          <h3 className="text-sm font-medium text-white mb-3">Recent Backtests</h3>
          <div className="space-y-2">
            {history.map((item, i) => (
              <button
                key={i}
                onClick={() => loadFromHistory(item)}
                className="w-full p-3 rounded bg-slate-900 border border-slate-800 hover:border-slate-600 flex items-center justify-between text-left"
              >
                <div>
                  <span className="font-mono text-white">{item.symbol}</span>
                  <span className="text-slate-500 mx-2">•</span>
                  <span className="text-sm text-slate-400">{item.strategy}</span>
                  <span className="text-slate-500 mx-2">•</span>
                  <span className="text-xs text-slate-500">{item.period}</span>
                </div>
                <div className={`font-mono ${item.result?.total_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {item.result?.total_return >= 0 ? '+' : ''}{item.result?.total_return?.toFixed(1)}%
                </div>
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Configuration */}
      <Card className="terminal-card p-6">
        <h2 className="text-lg font-display font-semibold text-white mb-4">Strategy Configuration</h2>
        
        {/* Symbol & Period Row */}
        <div className="grid md:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Symbol</label>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder="e.g. AAPL, TSLA, NVDA"
              className="bg-slate-900 border-slate-700 font-mono"
              data-testid="backtest-symbol"
            />
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
                <SelectItem value="10y">10 Years</SelectItem>
                <SelectItem value="20y">20 Years</SelectItem>
                <SelectItem value="30y">30 Years</SelectItem>
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
          
          <div className="flex items-end">
            <Button
              onClick={runBacktest}
              disabled={running || !symbol.trim()}
              className="w-full bg-cyan-600 hover:bg-cyan-500"
              data-testid="run-backtest-btn"
            >
              {running ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Run Backtest
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Strategy Selection */}
        <div className="mb-6">
          <label className="text-xs text-slate-500 mb-3 block">Trading Strategy</label>
          <div className="grid md:grid-cols-5 gap-3">
            {strategies.map(s => (
              <StrategyCard 
                key={s.id} 
                strategy={s} 
                selected={strategy}
                onSelect={setStrategy}
              />
            ))}
          </div>
        </div>

        {/* Risk Parameters */}
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Stop Loss: {stopLoss}%</label>
            <Slider
              value={[stopLoss]}
              onValueChange={([v]) => setStopLoss(v)}
              min={1}
              max={15}
              step={0.5}
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 mb-2 block">Take Profit: {takeProfit}%</label>
            <Slider
              value={[takeProfit]}
              onValueChange={([v]) => setTakeProfit(v)}
              min={2}
              max={50}
              step={1}
            />
          </div>
        </div>
      </Card>

      {/* Results */}
      {results && !results.error && (
        <>
          {/* Summary Stats */}
          <Card className="terminal-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-display font-semibold text-white">
                Results: {results.symbol}
              </h2>
              <Badge variant="outline" className="border-slate-700">
                {results.strategy} • {results.period}
              </Badge>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="p-4 rounded bg-slate-900 border border-slate-800">
                <p className="text-xs text-slate-500 mb-1">Total Return</p>
                <p className={`font-mono text-2xl ${results.total_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {results.total_return >= 0 ? '+' : ''}{results.total_return}%
                </p>
                {results.annualized_return !== undefined && (
                  <p className="text-xs text-slate-500 mt-1">
                    {results.annualized_return >= 0 ? '+' : ''}{results.annualized_return}% annualized
                  </p>
                )}
              </div>
              
              <div className="p-4 rounded bg-slate-900 border border-slate-800">
                <p className="text-xs text-slate-500 mb-1">Final Value</p>
                <p className="font-mono text-2xl text-white">
                  ${results.final_value?.toLocaleString()}
                </p>
                <p className="text-xs text-slate-500">
                  from ${results.initial_capital?.toLocaleString()} ({results.years_tested}yr)
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
                <p className={`font-mono text-2xl ${results.sharpe_ratio >= 1 ? 'text-emerald-400' : results.sharpe_ratio >= 0.5 ? 'text-amber-400' : 'text-slate-400'}`}>
                  {results.sharpe_ratio}
                </p>
              </div>
            </div>
            
            {/* Benchmark Comparison */}
            {results.benchmark_return !== null && results.benchmark_return !== undefined && (
              <div className="p-4 rounded bg-slate-900/50 border border-slate-700 mb-6" data-testid="benchmark-comparison">
                <p className="text-xs text-slate-500 mb-3">vs S&P 500 (SPY) Buy & Hold</p>
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center">
                    <p className="text-xs text-slate-500">Your Strategy</p>
                    <p className={`font-mono text-lg ${results.total_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {results.total_return >= 0 ? '+' : ''}{results.total_return}%
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-500">S&P 500</p>
                    <p className={`font-mono text-lg ${results.benchmark_return >= 0 ? 'text-blue-400' : 'text-red-400'}`}>
                      {results.benchmark_return >= 0 ? '+' : ''}{results.benchmark_return}%
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-slate-500">Alpha</p>
                    <p className={`font-mono text-lg ${results.alpha >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {results.alpha >= 0 ? '+' : ''}{results.alpha}%
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            <div className="grid md:grid-cols-5 gap-4">
              <div className="p-3 rounded bg-slate-800/50">
                <p className="text-xs text-slate-500">Win Rate</p>
                <p className={`font-mono text-lg ${results.win_rate >= 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {results.win_rate}%
                </p>
              </div>
              <div className="p-3 rounded bg-slate-800/50">
                <p className="text-xs text-slate-500">Total Trades</p>
                <p className="font-mono text-lg text-white">{results.total_trades}</p>
              </div>
              <div className="p-3 rounded bg-slate-800/50">
                <p className="text-xs text-slate-500">Wins / Losses</p>
                <p className="font-mono text-lg">
                  <span className="text-emerald-400">{results.wins}</span>
                  <span className="text-slate-500"> / </span>
                  <span className="text-red-400">{results.losses}</span>
                </p>
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

          {/* Equity Curve */}
          {results.equity_curve && results.equity_curve.length > 0 && (
            <Card className="terminal-card p-6">
              <h2 className="text-lg font-display font-semibold text-white mb-4">Equity Curve</h2>
              <div className="p-4 rounded bg-slate-900 border border-slate-800">
                <EquityChart data={results.equity_curve} initialCapital={results.initial_capital} />
                <div className="flex justify-between mt-2 text-xs text-slate-500">
                  <span>{results.equity_curve[0]?.date}</span>
                  <span>{results.equity_curve[results.equity_curve.length - 1]?.date}</span>
                </div>
              </div>
            </Card>
          )}

          {/* Trade Log */}
          {results.trades && results.trades.length > 0 && (
            <Card className="terminal-card overflow-hidden">
              <div className="p-4 border-b border-slate-800">
                <h2 className="text-lg font-display font-semibold text-white">
                  Recent Trades ({results.trades.length})
                </h2>
              </div>
              <div className="divide-y divide-slate-800">
                {results.trades.map((trade, i) => (
                  <TradeRow key={i} trade={trade} index={i} />
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {/* Info */}
      <Card className="terminal-card p-4 border-amber-500/20 bg-amber-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-200 font-medium mb-1">Backtesting Disclaimer</p>
            <p className="text-xs text-amber-200/70">
              Past performance does not guarantee future results. Backtests use historical data and 
              do not account for slippage, commissions, or market impact. Results are simulated based on 
              end-of-day prices. Use for research and strategy development only.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Backtesting;
