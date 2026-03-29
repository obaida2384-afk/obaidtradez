import { useState, useEffect, useCallback, memo, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { useLivePrices, LiveIndicator } from "../hooks/useLivePrices";
import { 
  Zap, 
  TrendingUp, 
  TrendingDown,
  Target,
  AlertTriangle,
  Search,
  Loader2,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Activity,
  BarChart2,
  Clock,
  Star,
  Shield,
  Info,
  CheckCircle2,
  XCircle,
  Trophy
} from "lucide-react";
import { toast } from "sonner";

// Signal Badge - Enhanced with more signal types
const SignalBadge = ({ signal, size = "sm" }) => {
  const config = {
    "Strong Buy": { class: "bg-emerald-500/30 text-emerald-300 border-emerald-500/50", icon: CheckCircle2 },
    "Buy": { class: "signal-buy", icon: TrendingUp },
    "Watch": { class: "signal-watch", icon: Clock },
    "Avoid": { class: "signal-avoid", icon: TrendingDown }
  }[signal] || { class: "signal-watch", icon: Activity };
  
  const Icon = config.icon;
  const sizeClass = size === "lg" ? "text-sm px-3 py-1" : "text-xs px-2 py-0.5";
  
  return (
    <span className={`font-medium rounded flex items-center gap-1 w-fit border ${sizeClass} ${config.class}`}>
      <Icon className="w-3 h-3" />
      {signal}
    </span>
  );
};

// Category Badge - Enhanced
const CategoryBadge = ({ category }) => {
  const config = {
    "Hot": "bg-red-500/20 text-red-400 border-red-500/30",
    "Breakout": "bg-amber-500/20 text-amber-400 border-amber-500/30",
    "Momentum": "bg-blue-500/20 text-blue-400 border-blue-500/30",
    "High Volume": "bg-purple-500/20 text-purple-400 border-purple-500/30",
    "Watch": "bg-slate-500/20 text-slate-400 border-slate-500/30",
    "Medium": "bg-slate-500/20 text-slate-400 border-slate-500/30",
    "Avoid": "bg-red-500/20 text-red-400 border-red-500/30"
  }[category] || "bg-slate-500/20 text-slate-400 border-slate-500/30";
  
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${config}`}>
      {category}
    </span>
  );
};

// News Sentiment Badge
const NewsSentimentBadge = ({ sentiment, impact }) => {
  if (!sentiment || sentiment === 'Neutral') return null;
  
  const config = {
    "Bullish": { class: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", icon: "📈" },
    "Slightly Positive": { class: "bg-green-500/20 text-green-400 border-green-500/30", icon: "👍" },
    "Bearish": { class: "bg-red-500/20 text-red-400 border-red-500/30", icon: "📉" },
    "Slightly Negative": { class: "bg-orange-500/20 text-orange-400 border-orange-500/30", icon: "👎" },
    "Neutral": { class: "bg-slate-500/20 text-slate-400 border-slate-500/30", icon: "➖" }
  }[sentiment] || { class: "bg-slate-500/20 text-slate-400 border-slate-500/30", icon: "📰" };
  
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded border flex items-center gap-1 ${config.class}`}>
      <span>{config.icon}</span>
      <span>News: {sentiment}</span>
      {impact !== 0 && impact !== undefined && (
        <span className={impact > 0 ? 'text-emerald-400' : 'text-red-400'}>
          ({impact > 0 ? '+' : ''}{impact})
        </span>
      )}
    </span>
  );
};

// Top Trade Card - Premium display for best setups
const TopTradeCard = memo(({ signal, rank, livePrice }) => {
  const displayPrice = livePrice?.price || signal.price;
  const displayChange = livePrice?.change_pct ?? signal.indicators?.change_pct;
  
  // Parse R:R ratio
  const rrMatch = signal.risk_reward?.match(/1:([\d.]+)/);
  const rrValue = rrMatch ? parseFloat(rrMatch[1]) : 0;
  
  return (
    <Card className="terminal-card p-4 border-amber-500/30 bg-gradient-to-r from-amber-500/5 to-transparent" data-testid={`top-trade-${rank}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-400 font-bold">
            #{rank}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-lg text-white">{signal.symbol}</span>
              <SignalBadge signal={signal.signal} />
            </div>
            <p className="text-xs text-slate-500">{signal.name}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-lg text-white">${displayPrice?.toFixed(2)}</p>
          <p className={`text-sm font-mono ${displayChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {displayChange >= 0 ? '+' : ''}{displayChange?.toFixed(2)}%
          </p>
        </div>
      </div>
      
      {/* News Sentiment Badge */}
      {signal.news_sentiment && signal.news_sentiment !== 'Neutral' && (
        <div className="mb-3">
          <NewsSentimentBadge sentiment={signal.news_sentiment} impact={signal.news_impact} />
        </div>
      )}
      
      {/* Trade Setup - Prominent Display */}
      <div className="grid grid-cols-4 gap-2 mb-3 p-3 rounded bg-slate-900/50 border border-slate-800">
        <div className="text-center">
          <p className="text-[10px] text-slate-500 uppercase">Entry</p>
          <p className="text-sm font-mono text-emerald-400">{signal.entry_zone}</p>
        </div>
        <div className="text-center border-l border-slate-700">
          <p className="text-[10px] text-slate-500 uppercase">Stop Loss</p>
          <p className="text-sm font-mono text-red-400">${signal.stop_loss}</p>
        </div>
        <div className="text-center border-l border-slate-700">
          <p className="text-[10px] text-slate-500 uppercase">Target</p>
          <p className="text-sm font-mono text-emerald-400">${signal.take_profit}</p>
        </div>
        <div className="text-center border-l border-slate-700">
          <p className="text-[10px] text-slate-500 uppercase">R:R</p>
          <p className={`text-sm font-mono ${rrValue >= 2 ? 'text-emerald-400' : 'text-amber-400'}`}>
            {signal.risk_reward}
          </p>
        </div>
      </div>
      
      {/* Confidence & Reasoning */}
      <div className="flex items-center gap-2 mb-2">
        <Progress value={signal.confidence * 100} className="h-2 flex-1" />
        <span className="text-xs font-mono text-slate-400">{(signal.confidence * 100).toFixed(0)}%</span>
      </div>
      
      <p className="text-xs text-slate-400 leading-relaxed">
        <span className="text-slate-500">Why: </span>{signal.reasoning}
      </p>
      
      {/* Recent News Headlines */}
      {signal.news_headlines && signal.news_headlines.length > 0 && (
        <div className="mt-3 pt-3 border-t border-slate-800">
          <p className="text-[10px] text-slate-500 uppercase mb-2">Recent News</p>
          <div className="space-y-1">
            {signal.news_headlines.slice(0, 2).map((headline, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <span className={`text-[10px] ${
                  headline.sentiment === 'Positive' ? 'text-emerald-400' : 
                  headline.sentiment === 'Negative' ? 'text-red-400' : 'text-slate-400'
                }`}>
                  {headline.sentiment === 'Positive' ? '↑' : headline.sentiment === 'Negative' ? '↓' : '•'}
                </span>
                <p className="text-[10px] text-slate-400 line-clamp-1">{headline.title}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
});

// Diagnostics Panel
const DiagnosticsPanel = ({ diagnostics }) => {
  const [expanded, setExpanded] = useState(false);
  
  if (!diagnostics) return null;
  
  return (
    <Card className="terminal-card p-3 border-slate-700">
      <button 
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-slate-500" />
          <span className="text-sm text-slate-400">Signal Quality Diagnostics</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            {diagnostics.signals_generated} signals from {diagnostics.stocks_scanned} stocks
          </span>
          {expanded ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
        </div>
      </button>
      
      {expanded && (
        <div className="mt-3 pt-3 border-t border-slate-800 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="p-2 rounded bg-slate-900">
              <p className="text-xs text-slate-500">Scanned</p>
              <p className="text-lg font-mono text-white">{diagnostics.stocks_scanned}</p>
            </div>
            <div className="p-2 rounded bg-slate-900">
              <p className="text-xs text-slate-500">Passed Filters</p>
              <p className="text-lg font-mono text-emerald-400">{diagnostics.signals_generated}</p>
            </div>
            <div className="p-2 rounded bg-slate-900">
              <p className="text-xs text-slate-500">Excluded</p>
              <p className="text-lg font-mono text-red-400">{diagnostics.excluded_count}</p>
            </div>
          </div>
          
          <div>
            <p className="text-xs text-slate-500 mb-2">Filters Applied:</p>
            <div className="flex flex-wrap gap-1">
              {diagnostics.filters_applied?.map((filter, i) => (
                <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  {filter}
                </span>
              ))}
            </div>
          </div>
          
          {diagnostics.excluded_reasons?.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-2">Sample Exclusions:</p>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {diagnostics.excluded_reasons.slice(0, 5).map((item, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <XCircle className="w-3 h-3 text-red-400 flex-shrink-0" />
                    <span className="text-slate-400">{item.symbol}:</span>
                    <span className="text-slate-500 truncate">{item.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

// Trading Signal Card - memoized to prevent unnecessary re-renders
const TradingCard = memo(({ signal, expanded, onToggle, token, inWatchlist, onWatchlistToggle, livePrice }) => {
  const [flash, setFlash] = useState(null);
  const prevPriceRef = useRef(null);
  
  // Use live price if available
  const displayPrice = livePrice?.price || signal.price;
  const displayChange = livePrice?.change_pct ?? signal.indicators?.change_pct;
  const changeColor = displayChange >= 0 ? 'text-emerald-400' : 'text-red-400';
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  
  // Flash effect on price change
  useEffect(() => {
    if (prevPriceRef.current !== null && prevPriceRef.current !== displayPrice && displayPrice > 0) {
      setFlash(displayPrice > prevPriceRef.current ? "up" : "down");
      const timeout = setTimeout(() => setFlash(null), 500);
      return () => clearTimeout(timeout);
    }
    prevPriceRef.current = displayPrice;
  }, [displayPrice]);

  const handleWatchlistClick = async (e) => {
    e.stopPropagation();
    setWatchlistLoading(true);
    try {
      if (inWatchlist) {
        const response = await fetch(`${API}/watchlist/${signal.symbol}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` }
        });
        if (response.ok) {
          toast.success(`${signal.symbol} removed from watchlist`);
          onWatchlistToggle(signal.symbol, false);
        }
      } else {
        const response = await fetch(`${API}/watchlist`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ symbol: signal.symbol, source: "trading" })
        });
        if (response.ok) {
          toast.success(`${signal.symbol} added to watchlist`);
          onWatchlistToggle(signal.symbol, true);
        }
      }
    } catch (error) {
      toast.error("Failed to update watchlist");
    } finally {
      setWatchlistLoading(false);
    }
  };
  
  const flashClass = flash === "up" 
    ? "bg-emerald-500/20" 
    : flash === "down" 
      ? "bg-red-500/20" 
      : "";
  
  return (
    <Card 
      className={`terminal-card overflow-hidden transition-all ${expanded ? 'border-blue-500/50' : 'hover:border-slate-600'}`}
      data-testid={`trading-card-${signal.symbol}`}
    >
      <button 
        className="w-full p-4 text-left"
        onClick={onToggle}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold text-lg text-white">{signal.symbol}</span>
                {livePrice && <LiveIndicator active={true} />}
                <CategoryBadge category={signal.category} />
                <div
                  role="button"
                  tabIndex={0}
                  onClick={handleWatchlistClick}
                  onKeyDown={(e) => e.key === 'Enter' && handleWatchlistClick(e)}
                  className={`p-1 rounded transition-colors cursor-pointer ${watchlistLoading ? 'opacity-50' : ''} ${inWatchlist ? 'text-amber-400' : 'text-slate-600 hover:text-amber-400'}`}
                  data-testid={`watchlist-btn-${signal.symbol}`}
                >
                  {watchlistLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Star className={`w-4 h-4 ${inWatchlist ? 'fill-current' : ''}`} />
                  )}
                </div>
              </div>
              <p className="text-xs text-slate-500 truncate max-w-[200px]">{signal.name}</p>
            </div>
          </div>
          <div className={`text-right transition-all duration-300 rounded p-1 -m-1 ${flashClass}`}>
            <p className="font-mono text-lg text-white">${displayPrice?.toFixed(2)}</p>
            <p className={`text-sm font-mono ${changeColor}`}>
              {displayChange >= 0 ? '+' : ''}{displayChange?.toFixed(2)}%
            </p>
          </div>
        </div>
        
        <div className="flex items-center justify-between">
          <SignalBadge signal={signal.signal} size="lg" />
          <div className="flex items-center gap-4 text-xs">
            <div className="text-center">
              <p className="text-slate-500">Confidence</p>
              <p className="font-mono text-white">{(signal.confidence * 100).toFixed(0)}%</p>
            </div>
            <div className="text-center">
              <p className="text-slate-500">Vol Ratio</p>
              <p className="font-mono text-white">{signal.indicators?.volume_ratio?.toFixed(1)}x</p>
            </div>
            <div className="text-center">
              <p className="text-slate-500">R:R</p>
              <p className="font-mono text-white">{signal.risk_reward}</p>
            </div>
            <ChevronRight className={`w-5 h-5 text-slate-500 transition-transform ${expanded ? 'rotate-90' : ''}`} />
          </div>
        </div>
      </button>
      
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-800 space-y-4">
          {/* Entry/Exit Levels */}
          <div className="grid grid-cols-4 gap-3">
            <div className="p-3 rounded bg-slate-900 border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase mb-1">Entry Zone</p>
              <p className="font-mono text-sm text-blue-400">{signal.entry_zone}</p>
            </div>
            <div className="p-3 rounded bg-slate-900 border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase mb-1">Stop Loss</p>
              <p className="font-mono text-sm text-red-400">${signal.stop_loss?.toFixed(2)}</p>
            </div>
            <div className="p-3 rounded bg-slate-900 border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase mb-1">Take Profit</p>
              <p className="font-mono text-sm text-emerald-400">${signal.take_profit?.toFixed(2)}</p>
            </div>
            <div className="p-3 rounded bg-slate-900 border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase mb-1">Position Size</p>
              <p className="font-mono text-sm text-white">{signal.position_size}</p>
            </div>
          </div>
          
          {/* Technical Indicators */}
          <div>
            <p className="text-xs text-slate-500 mb-2">Technical Indicators</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="text-xs border-slate-700">
                50MA: {signal.indicators?.price_vs_50ma > 0 ? '+' : ''}{signal.indicators?.price_vs_50ma?.toFixed(1)}%
              </Badge>
              <Badge variant="outline" className="text-xs border-slate-700">
                200MA: {signal.indicators?.price_vs_200ma > 0 ? '+' : ''}{signal.indicators?.price_vs_200ma?.toFixed(1)}%
              </Badge>
              <Badge variant="outline" className="text-xs border-slate-700">
                52W Range: {signal.indicators?.["52_week_position"]?.toFixed(0)}%
              </Badge>
            </div>
          </div>
          
          {/* Reasoning */}
          <div>
            <p className="text-xs text-slate-500 mb-2">AI Analysis</p>
            <p className="text-sm text-slate-300 leading-relaxed">{signal.reasoning}</p>
          </div>
        </div>
      )}
    </Card>
  );
});

const Trading = () => {
  const [signals, setSignals] = useState(null);
  const [searchSymbol, setSearchSymbol] = useState("");
  const [searchResult, setSearchResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [expandedCard, setExpandedCard] = useState(null);
  const [activeTab, setActiveTab] = useState("hot");
  const [watchlistSymbols, setWatchlistSymbols] = useState(new Set());
  const { token } = useAuth();
  const [searchParams] = useSearchParams();

  // Extract all symbols from signals for live price streaming
  const allSymbols = signals?.all?.map(s => s.symbol) || [];
  const { prices: livePrices, loading: pricesLoading } = useLivePrices(allSymbols, 12000, allSymbols.length > 0);

  useEffect(() => {
    fetchSignals();
    fetchWatchlist();
    const symbol = searchParams.get("symbol");
    if (symbol) {
      setSearchSymbol(symbol);
      searchStock(symbol);
    }
  }, []);

  const fetchWatchlist = async () => {
    try {
      const response = await fetch(`${API}/watchlist`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const items = await response.json();
        setWatchlistSymbols(new Set(items.map(i => i.symbol)));
      }
    } catch (error) {
      console.error("Error fetching watchlist:", error);
    }
  };

  const handleWatchlistToggle = (symbol, added) => {
    setWatchlistSymbols(prev => {
      const newSet = new Set(prev);
      if (added) {
        newSet.add(symbol);
      } else {
        newSet.delete(symbol);
      }
      return newSet;
    });
  };

  const fetchSignals = async () => {
    try {
      const response = await fetch(`${API}/trading/scan`, {
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
      const response = await fetch(`${API}/trading/analyze/${symbol.toUpperCase()}`, {
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
      case "breakout": return signals.breakout || [];
      case "momentum": return signals.momentum || [];
      case "volume": return signals.high_volume || [];
      case "watch": return signals.watch || [];
      default: return signals.all || [];
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="trading-loading">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-slate-500 text-sm">Scanning trading opportunities...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="trading-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Zap className="w-6 h-6 text-amber-400" />
            <h1 className="font-display text-2xl font-bold text-white">Trading Signals</h1>
          </div>
          <p className="text-sm text-slate-500">Short-term momentum and technical setups</p>
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
              data-testid="trading-search-input"
            />
          </div>
          <Button 
            onClick={() => searchStock(searchSymbol)}
            disabled={searching || !searchSymbol.trim()}
            className="bg-blue-600 hover:bg-blue-500"
            data-testid="trading-search-btn"
          >
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Analyze"}
          </Button>
        </div>
      </div>

      {/* Search Result */}
      {searchResult && (
        <section>
          <h2 className="text-sm font-medium text-slate-400 mb-3">Search Result</h2>
          <TradingCard 
            signal={searchResult}
            expanded={expandedCard === searchResult.symbol}
            onToggle={() => setExpandedCard(expandedCard === searchResult.symbol ? null : searchResult.symbol)}
            token={token}
            inWatchlist={watchlistSymbols.has(searchResult.symbol)}
            onWatchlistToggle={handleWatchlistToggle}
            livePrice={livePrices[searchResult.symbol]}
          />
        </section>
      )}

      {/* Live Price Indicator */}
      {allSymbols.length > 0 && Object.keys(livePrices).length > 0 && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <LiveIndicator active={true} />
          <span>Live prices • Updates every 12s</span>
        </div>
      )}

      {/* Diagnostics Panel */}
      {signals?.diagnostics && (
        <DiagnosticsPanel diagnostics={signals.diagnostics} />
      )}

      {/* TOP TRADES TODAY - Premium Section */}
      {signals?.top_trades?.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Trophy className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white">Top Trades Today</h2>
            <Badge variant="outline" className="border-amber-500/30 text-amber-400 text-xs">
              Best Setups
            </Badge>
          </div>
          <div className="grid gap-4">
            {signals.top_trades.map((signal, index) => (
              <TopTradeCard 
                key={signal.symbol}
                signal={signal}
                rank={index + 1}
                livePrice={livePrices[signal.symbol]}
              />
            ))}
          </div>
        </section>
      )}

      {/* Signal Categories */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="w-full justify-start bg-slate-900 border border-slate-800 p-1 h-auto flex-wrap">
          <TabsTrigger value="hot" className="data-[state=active]:bg-red-500/20 data-[state=active]:text-red-400">
            <Zap className="w-4 h-4 mr-1" /> Hot ({signals?.hot?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="breakout" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400">
            <TrendingUp className="w-4 h-4 mr-1" /> Breakout ({signals?.breakout?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="momentum" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <Activity className="w-4 h-4 mr-1" /> Momentum ({signals?.momentum?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="volume" className="data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400">
            <BarChart2 className="w-4 h-4 mr-1" /> High Volume ({signals?.high_volume?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="watch" className="data-[state=active]:bg-slate-500/20 data-[state=active]:text-slate-400">
            <Clock className="w-4 h-4 mr-1" /> Watch ({signals?.watch?.length || 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-4">
          <div className="space-y-3">
            {getTabSignals().map((signal) => (
              <TradingCard 
                key={signal.symbol}
                signal={signal}
                expanded={expandedCard === signal.symbol}
                onToggle={() => setExpandedCard(expandedCard === signal.symbol ? null : signal.symbol)}
                token={token}
                inWatchlist={watchlistSymbols.has(signal.symbol)}
                onWatchlistToggle={handleWatchlistToggle}
                livePrice={livePrices[signal.symbol]}
              />
            ))}
            {getTabSignals().length === 0 && (
              <Card className="terminal-card p-8 text-center">
                <Shield className="w-10 h-10 mx-auto mb-3 text-slate-600" />
                <p className="text-slate-400 mb-1">No signals meet quality threshold</p>
                <p className="text-xs text-slate-600">
                  Strict filters are applied to surface only high-quality setups.
                  Check back during market hours for more opportunities.
                </p>
              </Card>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Risk Warning */}
      <Card className="terminal-card p-4 border-amber-500/20 bg-amber-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-200 font-medium mb-1">Quality-First Trading</p>
            <p className="text-xs text-amber-200/70">
              These signals use strict confluence filters (momentum + volume + structure). 
              Each setup includes entry, stop-loss, and take-profit with minimum 2:1 R:R.
              Never risk more than 2-3% per trade.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Trading;
