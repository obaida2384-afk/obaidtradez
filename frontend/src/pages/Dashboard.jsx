import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  TrendingUp, 
  TrendingDown, 
  ArrowRight,
  Sparkles,
  AlertTriangle,
  Target,
  ChevronRight
} from "lucide-react";
import { API } from "../App";

// Score Badge Component
const ScoreBadge = ({ score, size = "md" }) => {
  const getScoreClass = (s) => {
    if (s >= 70) return "score-excellent";
    if (s >= 55) return "score-good";
    if (s >= 45) return "score-neutral";
    if (s >= 30) return "score-poor";
    return "score-bad";
  };
  
  const sizeClass = size === "lg" ? "text-lg px-3 py-1" : "text-xs px-2 py-0.5";
  
  return (
    <span className={`font-mono font-bold rounded ${sizeClass} ${getScoreClass(score)}`}>
      {score?.toFixed(0) || "—"}
    </span>
  );
};

// Signal Badge Component
const SignalBadge = ({ signal }) => {
  const signalClass = {
    "Strong Candidate": "signal-strong",
    "Candidate": "signal-candidate",
    "Watchlist": "signal-watchlist",
    "Avoid": "signal-avoid",
    "Breakout Candidate": "signal-strong",
    "Swing Candidate": "signal-candidate",
    "Weak Setup": "signal-watchlist",
  }[signal] || "signal-watchlist";
  
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${signalClass}`}>
      {signal}
    </span>
  );
};

// Price Change Component
const PriceChange = ({ value }) => {
  if (!value) return <span className="text-zinc-500">—</span>;
  const isPositive = value >= 0;
  return (
    <span className={`font-mono text-sm ${isPositive ? "price-up" : "price-down"}`}>
      {isPositive ? "+" : ""}{value?.toFixed(2)}%
    </span>
  );
};

// Stock Row Component
const StockRow = ({ stock, onClick }) => {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-4 p-4 hover:bg-zinc-800/50 transition-colors border-b border-zinc-800/50 last:border-0 text-left"
      data-testid={`stock-row-${stock.symbol}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono font-semibold text-white">{stock.symbol}</span>
          <SignalBadge signal={stock.investment_signal} />
        </div>
        <p className="text-xs text-zinc-500 truncate">{stock.company_name}</p>
      </div>
      
      <div className="text-right">
        <p className="font-mono text-sm text-white">${stock.price?.toFixed(2) || "—"}</p>
        <p className="text-xs text-zinc-500">{stock.sector}</p>
      </div>
      
      <div className="w-16 text-center">
        <ScoreBadge score={stock.overall_score} />
      </div>
      
      <ChevronRight className="w-4 h-4 text-zinc-600" />
    </button>
  );
};

// Recommendation Card
const RecommendationCard = ({ stock, rank }) => {
  const navigate = useNavigate();
  
  return (
    <Card 
      className="terminal-card p-4 cursor-pointer"
      onClick={() => navigate(`/stock/${stock.symbol}`)}
      data-testid={`rec-card-${stock.symbol}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 rounded bg-zinc-800 flex items-center justify-center text-xs font-mono text-zinc-400">
            #{rank}
          </span>
          <div>
            <p className="font-mono font-semibold text-white">{stock.symbol}</p>
            <p className="text-xs text-zinc-500 truncate max-w-[120px]">{stock.company_name}</p>
          </div>
        </div>
        <ScoreBadge score={stock.overall_score} size="lg" />
      </div>
      
      <div className="flex items-center gap-2 mb-3">
        <SignalBadge signal={stock.investment_signal} />
        <Badge variant="outline" className="text-[10px] border-zinc-700 text-zinc-400">
          {stock.confidence} Confidence
        </Badge>
      </div>
      
      <p className="text-xs text-zinc-400 line-clamp-2 mb-3">
        {stock.recommendation_reason}
      </p>
      
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="data-label">Valuation</p>
          <ScoreBadge score={stock.valuation_score} />
        </div>
        <div>
          <p className="data-label">Growth</p>
          <ScoreBadge score={stock.growth_score} />
        </div>
        <div>
          <p className="data-label">Momentum</p>
          <ScoreBadge score={stock.momentum_score} />
        </div>
      </div>
      
      {stock.strategy_fit?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t border-zinc-800">
          {stock.strategy_fit.slice(0, 3).map((strategy) => (
            <span key={strategy} className="text-[10px] px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded">
              {strategy}
            </span>
          ))}
        </div>
      )}
    </Card>
  );
};

const Dashboard = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const fetchRecommendations = async () => {
    try {
      const response = await fetch(`${API}/recommendations?limit=10`);
      const data = await response.json();
      setRecommendations(data);
    } catch (error) {
      console.error("Error fetching recommendations:", error);
    } finally {
      setLoading(false);
    }
  };

  const topPicks = recommendations.filter(s => s.investment_signal === "Strong Candidate" || s.overall_score >= 65).slice(0, 3);
  const watchlist = recommendations.filter(s => s.investment_signal === "Watchlist" || (s.overall_score >= 45 && s.overall_score < 65)).slice(0, 3);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="dashboard-loading">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-zinc-500 text-sm">Analyzing stocks...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white mb-1">Dashboard</h1>
          <p className="text-sm text-zinc-500">AI-powered stock recommendations</p>
        </div>
        <Button 
          onClick={() => navigate("/chat")}
          className="bg-blue-600 hover:bg-blue-500"
          data-testid="ask-ai-btn"
        >
          <Sparkles className="w-4 h-4 mr-2" />
          Ask AlphaLens AI
        </Button>
      </div>

      {/* Disclaimer */}
      <div className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 rounded-md">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
        <p className="text-xs text-amber-200/80">
          For research purposes only. Not financial advice. Always do your own due diligence before investing.
        </p>
      </div>

      {/* Top Recommendations */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Target className="w-5 h-5 text-emerald-500" />
            <h2 className="font-heading text-lg font-semibold text-white">Top Recommendations</h2>
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => navigate("/rankings")}
            className="text-zinc-400 hover:text-white"
            data-testid="view-all-rankings"
          >
            View All <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
        
        <div className="grid md:grid-cols-3 gap-4">
          {topPicks.length > 0 ? (
            topPicks.map((stock, i) => (
              <RecommendationCard key={stock.symbol} stock={stock} rank={i + 1} />
            ))
          ) : (
            recommendations.slice(0, 3).map((stock, i) => (
              <RecommendationCard key={stock.symbol} stock={stock} rank={i + 1} />
            ))
          )}
        </div>
      </section>

      {/* Two Column Layout */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* All Analyzed Stocks */}
        <Card className="terminal-card">
          <div className="p-4 border-b border-zinc-800">
            <h3 className="font-heading font-semibold text-white">Analyzed Stocks</h3>
            <p className="text-xs text-zinc-500">Ranked by overall score</p>
          </div>
          <div className="max-h-[400px] overflow-y-auto">
            {recommendations.map((stock) => (
              <StockRow 
                key={stock.symbol} 
                stock={stock} 
                onClick={() => navigate(`/stock/${stock.symbol}`)}
              />
            ))}
          </div>
        </Card>

        {/* Quick Stats */}
        <div className="space-y-4">
          {/* Strategy Distribution */}
          <Card className="terminal-card p-4">
            <h3 className="font-heading font-semibold text-white mb-4">Strategy Fit Distribution</h3>
            <div className="space-y-3">
              {["Value", "Growth", "Momentum", "Quality", "GARP"].map((strategy) => {
                const count = recommendations.filter(s => s.strategy_fit?.includes(strategy)).length;
                const pct = (count / recommendations.length) * 100;
                return (
                  <div key={strategy}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-zinc-400">{strategy}</span>
                      <span className="font-mono text-zinc-300">{count} stocks</span>
                    </div>
                    <div className="score-bar">
                      <div 
                        className="score-bar-fill bg-blue-500" 
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Signal Summary */}
          <Card className="terminal-card p-4">
            <h3 className="font-heading font-semibold text-white mb-4">Signal Summary</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { signal: "Strong Candidate", icon: TrendingUp, color: "text-emerald-400" },
                { signal: "Candidate", icon: Target, color: "text-blue-400" },
                { signal: "Watchlist", icon: AlertTriangle, color: "text-amber-400" },
                { signal: "Avoid", icon: TrendingDown, color: "text-red-400" },
              ].map(({ signal, icon: Icon, color }) => {
                const count = recommendations.filter(s => s.investment_signal === signal).length;
                return (
                  <div key={signal} className="flex items-center gap-3 p-3 bg-zinc-800/50 rounded-md">
                    <Icon className={`w-5 h-5 ${color}`} />
                    <div>
                      <p className="font-mono text-lg text-white">{count}</p>
                      <p className="text-[10px] text-zinc-500">{signal}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
