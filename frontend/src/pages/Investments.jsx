import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { 
  PiggyBank,
  TrendingUp, 
  TrendingDown,
  Target,
  AlertTriangle,
  Search,
  Loader2,
  ChevronRight,
  DollarSign,
  Shield,
  BarChart3,
  Sparkles
} from "lucide-react";

// Score Bar
const ScoreBar = ({ label, score, color = "blue" }) => {
  const getColor = () => {
    if (score >= 70) return "bg-emerald-500";
    if (score >= 55) return "bg-blue-500";
    if (score >= 40) return "bg-amber-500";
    return "bg-red-500";
  };
  
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-500 w-16">{label}</span>
      <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
        <div 
          className={`h-full ${getColor()} transition-all duration-500`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <span className="text-xs font-mono text-white w-8 text-right">{score?.toFixed(0)}</span>
    </div>
  );
};

// Signal Badge
const SignalBadge = ({ signal, size = "sm" }) => {
  const config = {
    "Buy": { class: "signal-buy", icon: TrendingUp },
    "Hold": { class: "signal-hold", icon: Shield },
    "Watchlist": { class: "signal-watch", icon: Target },
    "Sell": { class: "signal-avoid", icon: TrendingDown }
  }[signal] || { class: "signal-watch", icon: BarChart3 };
  
  const Icon = config.icon;
  const sizeClass = size === "lg" ? "text-sm px-3 py-1" : "text-xs px-2 py-0.5";
  
  return (
    <span className={`font-medium rounded flex items-center gap-1 w-fit ${sizeClass} ${config.class}`}>
      <Icon className="w-3 h-3" />
      {signal}
    </span>
  );
};

// Category Badge
const CategoryBadge = ({ category }) => {
  const config = {
    "Hot": "bg-red-500/20 text-red-400 border-red-500/30",
    "Bullish": "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    "Undervalued": "bg-blue-500/20 text-blue-400 border-blue-500/30",
    "Watch": "bg-amber-500/20 text-amber-400 border-amber-500/30",
    "Bearish": "bg-red-500/20 text-red-400 border-red-500/30",
    "Overpriced": "bg-purple-500/20 text-purple-400 border-purple-500/30"
  }[category] || "bg-slate-500/20 text-slate-400 border-slate-500/30";
  
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${config}`}>
      {category}
    </span>
  );
};

// Investment Signal Card
const InvestmentCard = ({ signal, expanded, onToggle }) => {
  const getScoreColor = (score) => {
    if (score >= 70) return "text-emerald-400";
    if (score >= 55) return "text-blue-400";
    if (score >= 40) return "text-amber-400";
    return "text-red-400";
  };
  
  return (
    <Card 
      className={`terminal-card overflow-hidden transition-all ${expanded ? 'border-blue-500/50' : 'hover:border-slate-600'}`}
      data-testid={`investment-card-${signal.symbol}`}
    >
      <button 
        className="w-full p-4 text-left"
        onClick={onToggle}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-xl font-mono font-bold ${getScoreColor(signal.overall_score)} bg-slate-800`}>
              {signal.overall_score?.toFixed(0)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-lg text-white">{signal.symbol}</span>
                <CategoryBadge category={signal.category} />
              </div>
              <p className="text-xs text-slate-500 truncate max-w-[200px]">{signal.name}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-mono text-lg text-white">${signal.price?.toFixed(2)}</p>
            {signal.upside_potential && (
              <p className={`text-sm font-mono ${signal.upside_potential.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
                {signal.upside_potential} upside
              </p>
            )}
          </div>
        </div>
        
        <div className="flex items-center justify-between">
          <SignalBadge signal={signal.signal} size="lg" />
          <div className="flex items-center gap-4 text-xs">
            <div className="text-center">
              <p className="text-slate-500">Confidence</p>
              <p className="font-mono text-white">{(signal.confidence * 100).toFixed(0)}%</p>
            </div>
            {signal.intrinsic_value && (
              <div className="text-center">
                <p className="text-slate-500">Fair Value</p>
                <p className="font-mono text-emerald-400">${signal.intrinsic_value?.toFixed(2)}</p>
              </div>
            )}
            <ChevronRight className={`w-5 h-5 text-slate-500 transition-transform ${expanded ? 'rotate-90' : ''}`} />
          </div>
        </div>
      </button>
      
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-800 space-y-4">
          {/* Score Breakdown */}
          <div>
            <p className="text-xs text-slate-500 mb-3">Score Breakdown</p>
            <div className="space-y-2">
              <ScoreBar label="Valuation" score={signal.valuation_score} />
              <ScoreBar label="Quality" score={signal.quality_score} />
              <ScoreBar label="Growth" score={signal.growth_score} />
              <ScoreBar label="Strength" score={signal.financial_strength} />
              <ScoreBar label="Risk" score={signal.risk_score} />
            </div>
          </div>
          
          {/* Bull Case */}
          {signal.bull_case?.length > 0 && (
            <div>
              <p className="text-xs text-emerald-400 mb-2 flex items-center gap-1">
                <TrendingUp className="w-3 h-3" /> Bull Case
              </p>
              <ul className="space-y-1">
                {signal.bull_case.map((item, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="text-emerald-400">•</span> {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Bear Case */}
          {signal.bear_case?.length > 0 && (
            <div>
              <p className="text-xs text-red-400 mb-2 flex items-center gap-1">
                <TrendingDown className="w-3 h-3" /> Bear Case
              </p>
              <ul className="space-y-1">
                {signal.bear_case.map((item, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="text-red-400">•</span> {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Risks */}
          {signal.risks?.length > 0 && (
            <div>
              <p className="text-xs text-amber-400 mb-2 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Key Risks
              </p>
              <div className="flex flex-wrap gap-2">
                {signal.risks.map((risk, i) => (
                  <Badge key={i} variant="outline" className="text-xs border-amber-500/30 text-amber-400">
                    {risk}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          
          {/* AI Summary */}
          <div className="p-3 rounded bg-slate-900 border border-slate-800">
            <p className="text-xs text-slate-500 mb-1 flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> AI Analysis
            </p>
            <p className="text-sm text-slate-300">{signal.reasoning}</p>
          </div>
        </div>
      )}
    </Card>
  );
};

const Investments = () => {
  const [signals, setSignals] = useState(null);
  const [searchSymbol, setSearchSymbol] = useState("");
  const [searchResult, setSearchResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [expandedCard, setExpandedCard] = useState(null);
  const [activeTab, setActiveTab] = useState("hot");
  const { token } = useAuth();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    fetchSignals();
    const symbol = searchParams.get("symbol");
    if (symbol) {
      setSearchSymbol(symbol);
      searchStock(symbol);
    }
  }, []);

  const fetchSignals = async () => {
    try {
      const response = await fetch(`${API}/investments/scan`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setSignals(await response.json());
      }
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const searchStock = async (symbol) => {
    if (!symbol.trim()) return;
    setSearching(true);
    setSearchResult(null);
    
    try {
      const response = await fetch(`${API}/investments/analyze/${symbol.toUpperCase()}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setSearchResult(await response.json());
        setExpandedCard(symbol.toUpperCase());
      }
    } catch (error) {
      console.error("Search error:", error);
    } finally {
      setSearching(false);
    }
  };

  const getTabSignals = () => {
    if (!signals) return [];
    switch (activeTab) {
      case "hot": return signals.hot || [];
      case "bullish": return signals.bullish || [];
      case "undervalued": return signals.undervalued || [];
      case "watch": return signals.watch || [];
      case "bearish": return [...(signals.bearish || []), ...(signals.overpriced || [])];
      default: return signals.all || [];
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="investments-loading">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-slate-500 text-sm">Analyzing investment opportunities...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="investments-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <PiggyBank className="w-6 h-6 text-emerald-400" />
            <h1 className="font-display text-2xl font-bold text-white">Investment Ideas</h1>
          </div>
          <p className="text-sm text-slate-500">Long-term value and fundamental analysis</p>
        </div>
        
        {/* Search */}
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && searchStock(searchSymbol)}
              placeholder="Search symbol..."
              className="pl-10 w-40 md:w-56 bg-slate-900 border-slate-700"
              data-testid="investments-search-input"
            />
          </div>
          <Button 
            onClick={() => searchStock(searchSymbol)}
            disabled={searching || !searchSymbol.trim()}
            className="bg-emerald-600 hover:bg-emerald-500"
            data-testid="investments-search-btn"
          >
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Analyze"}
          </Button>
        </div>
      </div>

      {/* Search Result */}
      {searchResult && (
        <section>
          <h2 className="text-sm font-medium text-slate-400 mb-3">Search Result</h2>
          <InvestmentCard 
            signal={searchResult}
            expanded={expandedCard === searchResult.symbol}
            onToggle={() => setExpandedCard(expandedCard === searchResult.symbol ? null : searchResult.symbol)}
          />
        </section>
      )}

      {/* Signal Categories */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="w-full justify-start bg-slate-900 border border-slate-800 p-1 h-auto flex-wrap">
          <TabsTrigger value="hot" className="data-[state=active]:bg-red-500/20 data-[state=active]:text-red-400">
            <Target className="w-4 h-4 mr-1" /> Hot ({signals?.hot?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="bullish" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-400">
            <TrendingUp className="w-4 h-4 mr-1" /> Bullish ({signals?.bullish?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="undervalued" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <DollarSign className="w-4 h-4 mr-1" /> Undervalued ({signals?.undervalued?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="watch" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400">
            <Shield className="w-4 h-4 mr-1" /> Watch ({signals?.watch?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="bearish" className="data-[state=active]:bg-slate-500/20 data-[state=active]:text-slate-400">
            <TrendingDown className="w-4 h-4 mr-1" /> Bearish ({(signals?.bearish?.length || 0) + (signals?.overpriced?.length || 0)})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-4">
          <div className="space-y-3">
            {getTabSignals().map((signal) => (
              <InvestmentCard 
                key={signal.symbol}
                signal={signal}
                expanded={expandedCard === signal.symbol}
                onToggle={() => setExpandedCard(expandedCard === signal.symbol ? null : signal.symbol)}
              />
            ))}
            {getTabSignals().length === 0 && (
              <Card className="terminal-card p-8 text-center">
                <p className="text-slate-500">No signals in this category</p>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Info Card */}
      <Card className="terminal-card p-4 border-blue-500/20 bg-blue-500/5">
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-blue-200 font-medium mb-1">Investment Analysis</p>
            <p className="text-xs text-blue-200/70">
              Our scoring model evaluates valuation (P/E, EV/EBITDA), quality (ROE, margins), 
              growth (revenue, earnings), financial strength (debt, liquidity), and risk (beta, volatility). 
              A higher score indicates stronger fundamentals and better value.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Investments;
