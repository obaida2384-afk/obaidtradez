import { useState, useEffect } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { 
  Search as SearchIcon,
  Filter,
  TrendingUp,
  TrendingDown,
  Loader2,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Target,
  Zap
} from "lucide-react";

const Screener = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("trading"); // trading or investing
  const [sortField, setSortField] = useState("confidence");
  const [sortDir, setSortDir] = useState("desc");
  const { token } = useAuth();

  // Trading filters
  const [tradingFilters, setTradingFilters] = useState({
    minVolume: 1.0,
    minChange: 0,
    signal: "all"
  });

  // Investment filters
  const [investmentFilters, setInvestmentFilters] = useState({
    minScore: 50,
    minValuation: 0,
    signal: "all"
  });

  useEffect(() => {
    runScreen();
  }, [mode]);

  const runScreen = async () => {
    setLoading(true);
    try {
      const endpoint = mode === "trading" ? "/trading/scan" : "/investments/scan";
      const response = await fetch(`${API}${endpoint}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setResults(data.all || []);
      }
    } catch (error) {
      console.error("Screener error:", error);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...results];
    
    if (mode === "trading") {
      if (tradingFilters.minVolume > 0) {
        filtered = filtered.filter(s => (s.indicators?.volume_ratio || 0) >= tradingFilters.minVolume);
      }
      if (tradingFilters.minChange !== 0) {
        filtered = filtered.filter(s => (s.indicators?.change_pct || 0) >= tradingFilters.minChange);
      }
      if (tradingFilters.signal !== "all") {
        filtered = filtered.filter(s => s.signal === tradingFilters.signal);
      }
    } else {
      if (investmentFilters.minScore > 0) {
        filtered = filtered.filter(s => (s.overall_score || 0) >= investmentFilters.minScore);
      }
      if (investmentFilters.minValuation > 0) {
        filtered = filtered.filter(s => (s.valuation_score || 0) >= investmentFilters.minValuation);
      }
      if (investmentFilters.signal !== "all") {
        filtered = filtered.filter(s => s.signal === investmentFilters.signal);
      }
    }

    // Sort
    filtered.sort((a, b) => {
      let aVal, bVal;
      if (sortField === "confidence") {
        aVal = a.confidence || 0;
        bVal = b.confidence || 0;
      } else if (sortField === "score") {
        aVal = a.overall_score || 0;
        bVal = b.overall_score || 0;
      } else if (sortField === "volume") {
        aVal = a.indicators?.volume_ratio || 0;
        bVal = b.indicators?.volume_ratio || 0;
      } else if (sortField === "change") {
        aVal = a.indicators?.change_pct || 0;
        bVal = b.indicators?.change_pct || 0;
      } else {
        aVal = a.symbol;
        bVal = b.symbol;
      }
      return sortDir === "desc" ? bVal - aVal : aVal - bVal;
    });

    return filtered;
  };

  const resetFilters = () => {
    if (mode === "trading") {
      setTradingFilters({ minVolume: 1.0, minChange: 0, signal: "all" });
    } else {
      setInvestmentFilters({ minScore: 50, minValuation: 0, signal: "all" });
    }
  };

  const filteredResults = applyFilters();

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

  return (
    <div className="space-y-6" data-testid="screener-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <SearchIcon className="w-6 h-6 text-purple-400" />
            <h1 className="font-display text-2xl font-bold text-white">Stock Screener</h1>
          </div>
          <p className="text-sm text-slate-500">Filter and find opportunities</p>
        </div>
        
        {/* Mode Toggle */}
        <Tabs value={mode} onValueChange={setMode}>
          <TabsList className="bg-slate-900 border border-slate-800">
            <TabsTrigger value="trading" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400">
              <Zap className="w-4 h-4 mr-1" /> Trading
            </TabsTrigger>
            <TabsTrigger value="investing" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-400">
              <Target className="w-4 h-4 mr-1" /> Investing
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Filters */}
      <Card className="terminal-card p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-white">Filters</span>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={resetFilters}
            className="ml-auto text-slate-400 hover:text-white"
          >
            <RotateCcw className="w-3 h-3 mr-1" /> Reset
          </Button>
        </div>

        {mode === "trading" ? (
          <div className="grid md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-slate-500 mb-2 block">Min Volume Ratio</label>
              <div className="flex items-center gap-2">
                <Slider
                  value={[tradingFilters.minVolume]}
                  onValueChange={([v]) => setTradingFilters(f => ({...f, minVolume: v}))}
                  min={0}
                  max={5}
                  step={0.5}
                  className="flex-1"
                />
                <span className="text-sm font-mono text-white w-12">{tradingFilters.minVolume}x</span>
              </div>
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">Min % Change</label>
              <div className="flex items-center gap-2">
                <Slider
                  value={[tradingFilters.minChange]}
                  onValueChange={([v]) => setTradingFilters(f => ({...f, minChange: v}))}
                  min={-10}
                  max={10}
                  step={1}
                  className="flex-1"
                />
                <span className="text-sm font-mono text-white w-12">{tradingFilters.minChange}%</span>
              </div>
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">Signal</label>
              <Select value={tradingFilters.signal} onValueChange={(v) => setTradingFilters(f => ({...f, signal: v}))}>
                <SelectTrigger className="bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Signals</SelectItem>
                  <SelectItem value="Buy">Buy Only</SelectItem>
                  <SelectItem value="Watch">Watch Only</SelectItem>
                  <SelectItem value="Avoid">Avoid Only</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">Sort By</label>
              <Select value={sortField} onValueChange={setSortField}>
                <SelectTrigger className="bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="confidence">Confidence</SelectItem>
                  <SelectItem value="volume">Volume Ratio</SelectItem>
                  <SelectItem value="change">% Change</SelectItem>
                  <SelectItem value="symbol">Symbol</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        ) : (
          <div className="grid md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-slate-500 mb-2 block">Min Overall Score</label>
              <div className="flex items-center gap-2">
                <Slider
                  value={[investmentFilters.minScore]}
                  onValueChange={([v]) => setInvestmentFilters(f => ({...f, minScore: v}))}
                  min={0}
                  max={100}
                  step={5}
                  className="flex-1"
                />
                <span className="text-sm font-mono text-white w-12">{investmentFilters.minScore}</span>
              </div>
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">Min Valuation Score</label>
              <div className="flex items-center gap-2">
                <Slider
                  value={[investmentFilters.minValuation]}
                  onValueChange={([v]) => setInvestmentFilters(f => ({...f, minValuation: v}))}
                  min={0}
                  max={100}
                  step={5}
                  className="flex-1"
                />
                <span className="text-sm font-mono text-white w-12">{investmentFilters.minValuation}</span>
              </div>
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">Signal</label>
              <Select value={investmentFilters.signal} onValueChange={(v) => setInvestmentFilters(f => ({...f, signal: v}))}>
                <SelectTrigger className="bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Signals</SelectItem>
                  <SelectItem value="Buy">Buy Only</SelectItem>
                  <SelectItem value="Hold">Hold Only</SelectItem>
                  <SelectItem value="Watchlist">Watchlist</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-xs text-slate-500 mb-2 block">Sort By</label>
              <Select value={sortField} onValueChange={setSortField}>
                <SelectTrigger className="bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="score">Overall Score</SelectItem>
                  <SelectItem value="confidence">Confidence</SelectItem>
                  <SelectItem value="symbol">Symbol</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
      </Card>

      {/* Results Count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Showing <span className="text-white font-medium">{filteredResults.length}</span> results
        </p>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSortDir(d => d === "desc" ? "asc" : "desc")}
          className="text-slate-400"
        >
          {sortDir === "desc" ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          {sortDir === "desc" ? "Highest First" : "Lowest First"}
        </Button>
      </div>

      {/* Results Table */}
      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      ) : (
        <Card className="terminal-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-900 border-b border-slate-800">
                <tr>
                  <th className="text-left p-3 text-slate-500 font-medium">Symbol</th>
                  <th className="text-left p-3 text-slate-500 font-medium">Signal</th>
                  <th className="text-right p-3 text-slate-500 font-medium">Price</th>
                  {mode === "trading" ? (
                    <>
                      <th className="text-right p-3 text-slate-500 font-medium">Change</th>
                      <th className="text-right p-3 text-slate-500 font-medium">Vol Ratio</th>
                      <th className="text-right p-3 text-slate-500 font-medium">R:R</th>
                    </>
                  ) : (
                    <>
                      <th className="text-right p-3 text-slate-500 font-medium">Score</th>
                      <th className="text-right p-3 text-slate-500 font-medium">Valuation</th>
                      <th className="text-right p-3 text-slate-500 font-medium">Upside</th>
                    </>
                  )}
                  <th className="text-right p-3 text-slate-500 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((item) => (
                  <tr key={item.symbol} className="border-b border-slate-800/50 hover:bg-slate-900/50">
                    <td className="p-3">
                      <div>
                        <span className="font-mono font-medium text-white">{item.symbol}</span>
                        <p className="text-xs text-slate-500 truncate max-w-[150px]">{item.name}</p>
                      </div>
                    </td>
                    <td className="p-3">
                      <SignalBadge signal={item.signal} />
                    </td>
                    <td className="p-3 text-right font-mono text-white">
                      ${item.price?.toFixed(2)}
                    </td>
                    {mode === "trading" ? (
                      <>
                        <td className={`p-3 text-right font-mono ${item.indicators?.change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {item.indicators?.change_pct >= 0 ? '+' : ''}{item.indicators?.change_pct?.toFixed(2)}%
                        </td>
                        <td className="p-3 text-right font-mono text-white">
                          {item.indicators?.volume_ratio?.toFixed(1)}x
                        </td>
                        <td className="p-3 text-right font-mono text-slate-400">
                          {item.risk_reward || "—"}
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="p-3 text-right">
                          <span className={`font-mono font-medium ${item.overall_score >= 70 ? 'text-emerald-400' : item.overall_score >= 50 ? 'text-blue-400' : 'text-amber-400'}`}>
                            {item.overall_score?.toFixed(0)}
                          </span>
                        </td>
                        <td className="p-3 text-right font-mono text-slate-400">
                          {item.valuation_score?.toFixed(0)}
                        </td>
                        <td className={`p-3 text-right font-mono ${item.upside_potential?.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
                          {item.upside_potential || "—"}
                        </td>
                      </>
                    )}
                    <td className="p-3 text-right font-mono text-white">
                      {(item.confidence * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
                {filteredResults.length === 0 && (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-500">
                      No results match your filters
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};

export default Screener;
