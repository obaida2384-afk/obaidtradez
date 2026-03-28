import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign,
  PieChart,
  Zap,
  Target,
  AlertTriangle,
  ArrowRight,
  Loader2,
  RefreshCw,
  Wallet,
  BarChart3
} from "lucide-react";

// Signal Badge Component
const SignalBadge = ({ signal }) => {
  const config = {
    "Buy": "signal-buy",
    "Watch": "signal-watch",
    "Hold": "signal-hold",
    "Avoid": "signal-avoid",
    "Sell": "signal-avoid",
    "Watchlist": "signal-watch"
  }[signal] || "signal-watch";
  
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded ${config}`}>
      {signal}
    </span>
  );
};

// Score Display
const ScoreDisplay = ({ score, label, size = "sm" }) => {
  const getColor = (s) => {
    if (s >= 70) return "text-emerald-400";
    if (s >= 55) return "text-blue-400";
    if (s >= 40) return "text-amber-400";
    return "text-red-400";
  };
  
  return (
    <div className="text-center">
      <p className={`font-mono font-bold ${size === "lg" ? "text-2xl" : "text-lg"} ${getColor(score)}`}>
        {score?.toFixed(0) || "—"}
      </p>
      {label && <p className="text-[10px] text-slate-500 uppercase">{label}</p>}
    </div>
  );
};

// Trading Signal Card
const TradingSignalCard = ({ signal, onClick }) => (
  <Card 
    className="terminal-card p-4 hover:border-slate-600 cursor-pointer transition-all"
    onClick={onClick}
    data-testid={`trading-signal-${signal.symbol}`}
  >
    <div className="flex items-start justify-between mb-2">
      <div>
        <p className="font-mono font-bold text-white">{signal.symbol}</p>
        <p className="text-xs text-slate-500 truncate max-w-[140px]">{signal.name}</p>
      </div>
      <SignalBadge signal={signal.signal} />
    </div>
    
    <div className="flex items-center gap-3 mb-2">
      <p className="text-lg font-mono text-white">${signal.price?.toFixed(2)}</p>
      <span className={`text-xs font-mono ${signal.indicators?.change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
        {signal.indicators?.change_pct >= 0 ? '+' : ''}{signal.indicators?.change_pct?.toFixed(2)}%
      </span>
    </div>
    
    <div className="grid grid-cols-3 gap-2 text-center text-xs mb-2">
      <div>
        <p className="text-slate-500">Vol</p>
        <p className="text-white font-mono">{signal.indicators?.volume_ratio?.toFixed(1)}x</p>
      </div>
      <div>
        <p className="text-slate-500">Conf</p>
        <p className="text-white font-mono">{(signal.confidence * 100).toFixed(0)}%</p>
      </div>
      <div>
        <p className="text-slate-500">R:R</p>
        <p className="text-white font-mono">{signal.risk_reward || "—"}</p>
      </div>
    </div>
    
    <p className="text-xs text-slate-400 line-clamp-1">{signal.reasoning}</p>
  </Card>
);

// Investment Signal Card
const InvestmentSignalCard = ({ signal, onClick }) => (
  <Card 
    className="terminal-card p-4 hover:border-slate-600 cursor-pointer transition-all"
    onClick={onClick}
    data-testid={`investment-signal-${signal.symbol}`}
  >
    <div className="flex items-start justify-between mb-2">
      <div>
        <p className="font-mono font-bold text-white">{signal.symbol}</p>
        <p className="text-xs text-slate-500 truncate max-w-[140px]">{signal.name}</p>
      </div>
      <SignalBadge signal={signal.signal} />
    </div>
    
    <div className="flex items-center gap-3 mb-3">
      <ScoreDisplay score={signal.overall_score} size="lg" />
      {signal.upside_potential && (
        <Badge variant="outline" className={`text-xs ${signal.upside_potential.startsWith('+') ? 'border-emerald-500/30 text-emerald-400' : 'border-red-500/30 text-red-400'}`}>
          {signal.upside_potential}
        </Badge>
      )}
    </div>
    
    <div className="grid grid-cols-4 gap-1 text-center mb-3">
      <div>
        <p className="text-[9px] text-slate-500">VAL</p>
        <p className="text-xs font-mono text-white">{signal.valuation_score?.toFixed(0)}</p>
      </div>
      <div>
        <p className="text-[9px] text-slate-500">QTY</p>
        <p className="text-xs font-mono text-white">{signal.quality_score?.toFixed(0)}</p>
      </div>
      <div>
        <p className="text-[9px] text-slate-500">GRW</p>
        <p className="text-xs font-mono text-white">{signal.growth_score?.toFixed(0)}</p>
      </div>
      <div>
        <p className="text-[9px] text-slate-500">STR</p>
        <p className="text-xs font-mono text-white">{signal.financial_strength?.toFixed(0)}</p>
      </div>
    </div>
    
    {signal.bull_case?.length > 0 && (
      <p className="text-xs text-emerald-400 line-clamp-1">
        <TrendingUp className="w-3 h-3 inline mr-1" />
        {signal.bull_case[0]}
      </p>
    )}
  </Card>
);

const Dashboard = () => {
  const [tradingSignals, setTradingSignals] = useState(null);
  const [investmentSignals, setInvestmentSignals] = useState(null);
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { token } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      const [tradingRes, investmentRes, accountRes, positionsRes] = await Promise.all([
        fetch(`${API}/trading/scan`, { headers }),
        fetch(`${API}/investments/scan`, { headers }),
        fetch(`${API}/account`, { headers }).catch(() => null),
        fetch(`${API}/positions`, { headers }).catch(() => null)
      ]);

      if (tradingRes.ok) {
        setTradingSignals(await tradingRes.json());
      }
      if (investmentRes.ok) {
        setInvestmentSignals(await investmentRes.json());
      }
      if (accountRes?.ok) {
        setAccount(await accountRes.json());
      }
      if (positionsRes?.ok) {
        setPositions(await positionsRes.json());
      }
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="dashboard-loading">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-slate-500 text-sm">Scanning market opportunities...</p>
        </div>
      </div>
    );
  }

  const equity = parseFloat(account?.equity || 0);
  const buyingPower = parseFloat(account?.buying_power || 0);
  const cash = parseFloat(account?.cash || 0);

  return (
    <div className="space-y-6" data-testid="dashboard">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-white mb-1">Dashboard</h1>
          <p className="text-sm text-slate-500">AI-powered market intelligence</p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline"
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="border-slate-700 text-slate-300 hover:text-white"
            data-testid="refresh-btn"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button 
            onClick={() => navigate("/chatbot")}
            className="bg-blue-600 hover:bg-blue-500"
            data-testid="ask-ai-btn"
          >
            <Zap className="w-4 h-4 mr-2" />
            Ask AI
          </Button>
        </div>
      </div>

      {/* Account Overview */}
      {account && (
        <section className="grid md:grid-cols-4 gap-4">
          <Card className="terminal-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-emerald-500/20 flex items-center justify-center">
                <Wallet className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Portfolio Value</p>
                <p className="font-mono text-xl text-white">${equity.toLocaleString()}</p>
              </div>
            </div>
          </Card>
          
          <Card className="terminal-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-blue-500/20 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Buying Power</p>
                <p className="font-mono text-xl text-white">${buyingPower.toLocaleString()}</p>
              </div>
            </div>
          </Card>
          
          <Card className="terminal-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-amber-500/20 flex items-center justify-center">
                <PieChart className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Open Positions</p>
                <p className="font-mono text-xl text-white">{positions.length}</p>
              </div>
            </div>
          </Card>
          
          <Card className="terminal-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-slate-700 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-slate-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Cash</p>
                <p className="font-mono text-xl text-white">${cash.toLocaleString()}</p>
              </div>
            </div>
          </Card>
        </section>
      )}

      {/* Trading Signals Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" />
            <h2 className="font-display text-lg font-semibold text-white">Hot Trading Signals</h2>
            <Badge variant="outline" className="text-xs border-amber-500/30 text-amber-400">Short-term</Badge>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => navigate("/trading")}
            className="text-slate-400 hover:text-white"
          >
            View All <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {(tradingSignals?.hot || tradingSignals?.momentum || []).slice(0, 4).map((signal) => (
            <TradingSignalCard 
              key={signal.symbol} 
              signal={signal}
              onClick={() => navigate(`/trading?symbol=${signal.symbol}`)}
            />
          ))}
          {(!tradingSignals?.hot?.length && !tradingSignals?.momentum?.length) && (
            <Card className="terminal-card p-8 col-span-4 text-center">
              <p className="text-slate-500">No hot trading signals at the moment</p>
            </Card>
          )}
        </div>
      </section>

      {/* Investment Signals Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-emerald-400" />
            <h2 className="font-display text-lg font-semibold text-white">Top Investment Ideas</h2>
            <Badge variant="outline" className="text-xs border-emerald-500/30 text-emerald-400">Long-term</Badge>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => navigate("/investments")}
            className="text-slate-400 hover:text-white"
          >
            View All <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
        
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {(investmentSignals?.hot || investmentSignals?.bullish || []).slice(0, 4).map((signal) => (
            <InvestmentSignalCard 
              key={signal.symbol} 
              signal={signal}
              onClick={() => navigate(`/investments?symbol=${signal.symbol}`)}
            />
          ))}
          {(!investmentSignals?.hot?.length && !investmentSignals?.bullish?.length) && (
            <Card className="terminal-card p-8 col-span-4 text-center">
              <p className="text-slate-500">No hot investment signals at the moment</p>
            </Card>
          )}
        </div>
      </section>

      {/* Risk Warning */}
      <Card className="terminal-card p-4 border-amber-500/20 bg-amber-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-200 font-medium mb-1">Risk Disclaimer</p>
            <p className="text-xs text-amber-200/70">
              All signals are generated by AI analysis and are for educational purposes only. 
              Past performance does not guarantee future results. Always do your own research and 
              consider your risk tolerance before trading.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Dashboard;
