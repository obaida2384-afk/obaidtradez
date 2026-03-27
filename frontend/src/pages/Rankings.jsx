import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  TrendingUp, 
  Zap, 
  Target, 
  Shield,
  ChevronRight,
  Loader2
} from "lucide-react";
import { API } from "../App";

// Score Badge
const ScoreBadge = ({ score }) => {
  const getScoreClass = (s) => {
    if (s >= 70) return "bg-emerald-500/15 text-emerald-400";
    if (s >= 55) return "bg-blue-500/15 text-blue-400";
    if (s >= 45) return "bg-zinc-500/15 text-zinc-400";
    if (s >= 30) return "bg-amber-500/15 text-amber-400";
    return "bg-red-500/15 text-red-400";
  };
  
  return (
    <span className={`font-mono font-bold text-sm px-2 py-0.5 rounded ${getScoreClass(score)}`}>
      {score?.toFixed(0) || "—"}
    </span>
  );
};

// Signal Badge
const SignalBadge = ({ signal }) => {
  const classes = {
    "Strong Candidate": "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
    "Candidate": "bg-blue-500/20 text-blue-400 border-blue-500/40",
    "Watchlist": "bg-amber-500/20 text-amber-400 border-amber-500/40",
    "Avoid": "bg-red-500/20 text-red-400 border-red-500/40",
  }[signal] || "bg-zinc-500/20 text-zinc-400 border-zinc-500/40";
  
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${classes}`}>
      {signal}
    </span>
  );
};

// Stock Row in Rankings
const RankingRow = ({ stock, rank, onClick }) => {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 p-4 hover:bg-zinc-800/50 transition-colors border-b border-zinc-800/50 last:border-0 text-left"
      data-testid={`ranking-${stock.symbol}`}
    >
      <div className="w-8 h-8 rounded bg-zinc-800 flex items-center justify-center">
        <span className="font-mono text-sm text-zinc-400">#{rank}</span>
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono font-semibold text-white">{stock.symbol}</span>
          <SignalBadge signal={stock.investment_signal} />
        </div>
        <p className="text-xs text-zinc-500 truncate">{stock.company_name}</p>
      </div>
      
      <div className="hidden md:block text-right w-24">
        <p className="font-mono text-sm text-white">${stock.price?.toFixed(2) || "—"}</p>
        <p className="text-xs text-zinc-500">{stock.sector}</p>
      </div>
      
      <div className="grid grid-cols-4 gap-2 text-center hidden lg:grid">
        <div>
          <p className="data-label">Value</p>
          <ScoreBadge score={stock.valuation_score} />
        </div>
        <div>
          <p className="data-label">Fund</p>
          <ScoreBadge score={stock.fundamentals_score} />
        </div>
        <div>
          <p className="data-label">Growth</p>
          <ScoreBadge score={stock.growth_score} />
        </div>
        <div>
          <p className="data-label">Mom</p>
          <ScoreBadge score={stock.momentum_score} />
        </div>
      </div>
      
      <div className="w-16 text-center">
        <p className="data-label">Overall</p>
        <ScoreBadge score={stock.overall_score} />
      </div>
      
      <ChevronRight className="w-4 h-4 text-zinc-600" />
    </button>
  );
};

const Rankings = () => {
  const [activeStrategy, setActiveStrategy] = useState("value");
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const strategies = [
    { id: "value", label: "Value", icon: Target, description: "Low valuation, strong fundamentals" },
    { id: "growth", label: "Growth", icon: TrendingUp, description: "High revenue & earnings growth" },
    { id: "momentum", label: "Momentum", icon: Zap, description: "Strong price trends & technicals" },
    { id: "quality", label: "Quality", icon: Shield, description: "High ROE, stable margins, low debt" },
  ];

  useEffect(() => {
    fetchRankings(activeStrategy);
  }, [activeStrategy]);

  const fetchRankings = async (strategy) => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/rankings/${strategy}?limit=15`);
      if (response.ok) {
        const data = await response.json();
        setStocks(data);
      }
    } catch (error) {
      console.error("Error fetching rankings:", error);
    } finally {
      setLoading(false);
    }
  };

  const activeStrategyData = strategies.find(s => s.id === activeStrategy);

  return (
    <div className="space-y-6" data-testid="rankings-page">
      {/* Header */}
      <div>
        <h1 className="font-heading text-2xl font-bold text-white mb-1">Strategy Rankings</h1>
        <p className="text-sm text-zinc-500">Top stocks ranked by investment strategy</p>
      </div>

      {/* Strategy Tabs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {strategies.map((strategy) => {
          const isActive = activeStrategy === strategy.id;
          return (
            <button
              key={strategy.id}
              onClick={() => setActiveStrategy(strategy.id)}
              className={`p-4 rounded-md border transition-all text-left ${
                isActive 
                  ? "bg-blue-600/10 border-blue-500/50 text-white" 
                  : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700"
              }`}
              data-testid={`strategy-${strategy.id}`}
            >
              <div className="flex items-center gap-2 mb-2">
                <strategy.icon className={`w-5 h-5 ${isActive ? "text-blue-400" : "text-zinc-500"}`} />
                <span className="font-semibold">{strategy.label}</span>
              </div>
              <p className="text-xs text-zinc-500">{strategy.description}</p>
            </button>
          );
        })}
      </div>

      {/* Rankings Table */}
      <Card className="terminal-card overflow-hidden">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h2 className="font-heading font-semibold text-white flex items-center gap-2">
              {activeStrategyData?.icon && <activeStrategyData.icon className="w-5 h-5 text-blue-400" />}
              Top {activeStrategyData?.label} Stocks
            </h2>
            <p className="text-xs text-zinc-500">{activeStrategyData?.description}</p>
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => fetchRankings(activeStrategy)}
            className="border-zinc-700 text-zinc-400 hover:text-white"
            disabled={loading}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Refresh"}
          </Button>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-blue-500" />
            <p className="text-zinc-500 text-sm">Analyzing stocks...</p>
          </div>
        ) : stocks.length > 0 ? (
          <div className="max-h-[600px] overflow-y-auto">
            {stocks.map((stock, i) => (
              <RankingRow 
                key={stock.symbol} 
                stock={stock} 
                rank={i + 1}
                onClick={() => navigate(`/stock/${stock.symbol}`)}
              />
            ))}
          </div>
        ) : (
          <div className="p-12 text-center">
            <p className="text-zinc-500">No stocks found for this strategy</p>
          </div>
        )}
      </Card>

      {/* Strategy Explanation */}
      <Card className="terminal-card p-6">
        <h3 className="font-heading font-semibold text-white mb-4">How {activeStrategyData?.label} Scoring Works</h3>
        <div className="grid md:grid-cols-2 gap-6 text-sm text-zinc-400">
          {activeStrategy === "value" && (
            <>
              <div>
                <p className="text-white font-medium mb-2">Key Metrics</p>
                <ul className="space-y-1">
                  <li>• P/E ratio below sector average</li>
                  <li>• Low EV/EBITDA multiple</li>
                  <li>• Attractive PEG ratio (&lt;1.5)</li>
                  <li>• Strong free cash flow</li>
                </ul>
              </div>
              <div>
                <p className="text-white font-medium mb-2">Scoring Weight</p>
                <ul className="space-y-1">
                  <li>• Valuation: 40%</li>
                  <li>• Fundamentals: 30%</li>
                  <li>• Risk: 20%</li>
                  <li>• Growth: 10%</li>
                </ul>
              </div>
            </>
          )}
          {activeStrategy === "growth" && (
            <>
              <div>
                <p className="text-white font-medium mb-2">Key Metrics</p>
                <ul className="space-y-1">
                  <li>• Revenue growth &gt;10% YoY</li>
                  <li>• Earnings growth acceleration</li>
                  <li>• Improving margins</li>
                  <li>• Market share expansion</li>
                </ul>
              </div>
              <div>
                <p className="text-white font-medium mb-2">Scoring Weight</p>
                <ul className="space-y-1">
                  <li>• Growth: 40%</li>
                  <li>• Momentum: 25%</li>
                  <li>• Fundamentals: 20%</li>
                  <li>• Valuation: 15%</li>
                </ul>
              </div>
            </>
          )}
          {activeStrategy === "momentum" && (
            <>
              <div>
                <p className="text-white font-medium mb-2">Key Metrics</p>
                <ul className="space-y-1">
                  <li>• Price above 50 & 200-day MA</li>
                  <li>• Strong relative strength</li>
                  <li>• Volume confirmation</li>
                  <li>• Near 52-week highs</li>
                </ul>
              </div>
              <div>
                <p className="text-white font-medium mb-2">Scoring Weight</p>
                <ul className="space-y-1">
                  <li>• Momentum: 40%</li>
                  <li>• Technical: 30%</li>
                  <li>• Growth: 15%</li>
                  <li>• Risk: 15%</li>
                </ul>
              </div>
            </>
          )}
          {activeStrategy === "quality" && (
            <>
              <div>
                <p className="text-white font-medium mb-2">Key Metrics</p>
                <ul className="space-y-1">
                  <li>• ROE &gt;15%</li>
                  <li>• Stable/expanding margins</li>
                  <li>• Low debt-to-equity</li>
                  <li>• Consistent earnings</li>
                </ul>
              </div>
              <div>
                <p className="text-white font-medium mb-2">Scoring Weight</p>
                <ul className="space-y-1">
                  <li>• Fundamentals: 40%</li>
                  <li>• Risk: 25%</li>
                  <li>• Valuation: 20%</li>
                  <li>• Growth: 15%</li>
                </ul>
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  );
};

export default Rankings;
