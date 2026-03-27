import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { 
  Search, 
  Filter,
  Loader2,
  ChevronRight,
  RotateCcw
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
    "Strong Candidate": "bg-emerald-500/20 text-emerald-400",
    "Candidate": "bg-blue-500/20 text-blue-400",
    "Watchlist": "bg-amber-500/20 text-amber-400",
    "Avoid": "bg-red-500/20 text-red-400",
  }[signal] || "bg-zinc-500/20 text-zinc-400";
  
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${classes}`}>
      {signal}
    </span>
  );
};

const SECTORS = [
  "Technology",
  "Healthcare",
  "Financial Services",
  "Consumer Cyclical",
  "Consumer Defensive",
  "Industrials",
  "Energy",
  "Utilities",
  "Real Estate",
  "Communication Services",
  "Basic Materials"
];

const Screener = () => {
  const [filters, setFilters] = useState({
    minMarketCap: 10,
    maxMarketCap: 1000,
    sector: "all",
    minPe: 0,
    maxPe: 50,
    minRoe: 0,
    minDividendYield: 0,
    minRevenueGrowth: -20,
    strategy: "all"
  });
  
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const navigate = useNavigate();

  const runScreener = async () => {
    setLoading(true);
    setHasSearched(true);
    
    try {
      const params = {
        limit: 20
      };
      
      if (filters.minMarketCap > 0) {
        params.min_market_cap = filters.minMarketCap * 1e9;
      }
      if (filters.maxMarketCap < 1000) {
        params.max_market_cap = filters.maxMarketCap * 1e9;
      }
      if (filters.sector && filters.sector !== "all") {
        params.sector = filters.sector;
      }
      if (filters.strategy && filters.strategy !== "all") {
        params.strategy = filters.strategy;
      }
      if (filters.minRoe > 0) {
        params.min_roe = filters.minRoe / 100;
      }

      const response = await fetch(`${API}/screener`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params)
      });
      
      if (response.ok) {
        let data = await response.json();
        
        // Apply client-side filters
        if (filters.minPe > 0 || filters.maxPe < 50) {
          data = data.filter(s => {
            const pe = s.pe_ratio;
            if (!pe) return true;
            return pe >= filters.minPe && pe <= filters.maxPe;
          });
        }
        
        setResults(data);
      }
    } catch (error) {
      console.error("Screener error:", error);
    } finally {
      setLoading(false);
    }
  };

  const resetFilters = () => {
    setFilters({
      minMarketCap: 10,
      maxMarketCap: 1000,
      sector: "all",
      minPe: 0,
      maxPe: 50,
      minRoe: 0,
      minDividendYield: 0,
      minRevenueGrowth: -20,
      strategy: "all"
    });
    setResults([]);
    setHasSearched(false);
  };

  return (
    <div className="space-y-6" data-testid="screener-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl font-bold text-white mb-1">Stock Screener</h1>
          <p className="text-sm text-zinc-500">Filter and find stocks based on your criteria</p>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={resetFilters}
            className="border-zinc-700 text-zinc-400 hover:text-white"
            data-testid="reset-filters-btn"
          >
            <RotateCcw className="w-4 h-4 mr-1" />
            Reset
          </Button>
          <Button 
            onClick={runScreener}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-500"
            data-testid="run-screener-btn"
          >
            {loading ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <Search className="w-4 h-4 mr-1" />}
            Screen Stocks
          </Button>
        </div>
      </div>

      <div className="grid lg:grid-cols-[300px_1fr] gap-6">
        {/* Filters Panel */}
        <Card className="terminal-card p-4 h-fit">
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-zinc-800">
            <Filter className="w-4 h-4 text-blue-400" />
            <h2 className="font-heading font-semibold text-white">Filters</h2>
          </div>

          <div className="space-y-5">
            {/* Strategy */}
            <div>
              <Label className="text-xs text-zinc-400 mb-2 block">Strategy</Label>
              <Select 
                value={filters.strategy} 
                onValueChange={(v) => setFilters(f => ({ ...f, strategy: v }))}
              >
                <SelectTrigger className="bg-zinc-800 border-zinc-700" data-testid="strategy-select">
                  <SelectValue placeholder="All Strategies" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Strategies</SelectItem>
                  <SelectItem value="value">Value</SelectItem>
                  <SelectItem value="growth">Growth</SelectItem>
                  <SelectItem value="momentum">Momentum</SelectItem>
                  <SelectItem value="quality">Quality</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Sector */}
            <div>
              <Label className="text-xs text-zinc-400 mb-2 block">Sector</Label>
              <Select 
                value={filters.sector} 
                onValueChange={(v) => setFilters(f => ({ ...f, sector: v }))}
              >
                <SelectTrigger className="bg-zinc-800 border-zinc-700" data-testid="sector-select">
                  <SelectValue placeholder="All Sectors" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sectors</SelectItem>
                  {SECTORS.map(s => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Market Cap */}
            <div>
              <div className="flex justify-between mb-2">
                <Label className="text-xs text-zinc-400">Market Cap (Billions)</Label>
                <span className="text-xs font-mono text-zinc-500">
                  ${filters.minMarketCap}B - ${filters.maxMarketCap >= 1000 ? '∞' : filters.maxMarketCap + 'B'}
                </span>
              </div>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-zinc-500 w-8">Min</span>
                  <Slider
                    value={[filters.minMarketCap]}
                    onValueChange={([v]) => setFilters(f => ({ ...f, minMarketCap: v }))}
                    min={0}
                    max={500}
                    step={10}
                    className="flex-1"
                    data-testid="min-market-cap-slider"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-zinc-500 w-8">Max</span>
                  <Slider
                    value={[filters.maxMarketCap]}
                    onValueChange={([v]) => setFilters(f => ({ ...f, maxMarketCap: v }))}
                    min={10}
                    max={1000}
                    step={10}
                    className="flex-1"
                    data-testid="max-market-cap-slider"
                  />
                </div>
              </div>
            </div>

            {/* P/E Range */}
            <div>
              <div className="flex justify-between mb-2">
                <Label className="text-xs text-zinc-400">P/E Ratio</Label>
                <span className="text-xs font-mono text-zinc-500">
                  {filters.minPe} - {filters.maxPe >= 50 ? '∞' : filters.maxPe}
                </span>
              </div>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-zinc-500 w-8">Min</span>
                  <Slider
                    value={[filters.minPe]}
                    onValueChange={([v]) => setFilters(f => ({ ...f, minPe: v }))}
                    min={0}
                    max={40}
                    step={1}
                    className="flex-1"
                  />
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-zinc-500 w-8">Max</span>
                  <Slider
                    value={[filters.maxPe]}
                    onValueChange={([v]) => setFilters(f => ({ ...f, maxPe: v }))}
                    min={5}
                    max={50}
                    step={1}
                    className="flex-1"
                  />
                </div>
              </div>
            </div>

            {/* Min ROE */}
            <div>
              <div className="flex justify-between mb-2">
                <Label className="text-xs text-zinc-400">Min ROE (%)</Label>
                <span className="text-xs font-mono text-zinc-500">{filters.minRoe}%</span>
              </div>
              <Slider
                value={[filters.minRoe]}
                onValueChange={([v]) => setFilters(f => ({ ...f, minRoe: v }))}
                min={0}
                max={40}
                step={5}
                className="flex-1"
                data-testid="min-roe-slider"
              />
            </div>
          </div>
        </Card>

        {/* Results */}
        <Card className="terminal-card overflow-hidden">
          <div className="p-4 border-b border-zinc-800">
            <h2 className="font-heading font-semibold text-white">
              Results {results.length > 0 && `(${results.length})`}
            </h2>
          </div>

          {loading ? (
            <div className="p-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-blue-500" />
              <p className="text-zinc-500 text-sm">Screening stocks...</p>
            </div>
          ) : results.length > 0 ? (
            <div className="max-h-[600px] overflow-y-auto">
              {/* Table Header */}
              <div className="grid grid-cols-[1fr_100px_80px_80px_80px_80px_40px] gap-2 px-4 py-2 bg-zinc-900 text-xs text-zinc-500 uppercase tracking-wider sticky top-0">
                <span>Stock</span>
                <span className="text-right">Price</span>
                <span className="text-center">Signal</span>
                <span className="text-center">Value</span>
                <span className="text-center">Growth</span>
                <span className="text-center">Score</span>
                <span></span>
              </div>
              
              {results.map((stock) => (
                <button
                  key={stock.symbol}
                  onClick={() => navigate(`/stock/${stock.symbol}`)}
                  className="w-full grid grid-cols-[1fr_100px_80px_80px_80px_80px_40px] gap-2 items-center px-4 py-3 hover:bg-zinc-800/50 transition-colors border-b border-zinc-800/50 text-left"
                  data-testid={`result-${stock.symbol}`}
                >
                  <div className="min-w-0">
                    <p className="font-mono font-semibold text-white">{stock.symbol}</p>
                    <p className="text-xs text-zinc-500 truncate">{stock.company_name}</p>
                  </div>
                  <p className="font-mono text-sm text-white text-right">${stock.price?.toFixed(2) || "—"}</p>
                  <div className="text-center">
                    <SignalBadge signal={stock.investment_signal} />
                  </div>
                  <div className="text-center">
                    <ScoreBadge score={stock.valuation_score} />
                  </div>
                  <div className="text-center">
                    <ScoreBadge score={stock.growth_score} />
                  </div>
                  <div className="text-center">
                    <ScoreBadge score={stock.overall_score} />
                  </div>
                  <ChevronRight className="w-4 h-4 text-zinc-600" />
                </button>
              ))}
            </div>
          ) : hasSearched ? (
            <div className="p-12 text-center">
              <p className="text-zinc-500 mb-2">No stocks match your criteria</p>
              <p className="text-xs text-zinc-600">Try adjusting your filters</p>
            </div>
          ) : (
            <div className="p-12 text-center">
              <Search className="w-10 h-10 text-zinc-700 mx-auto mb-3" />
              <p className="text-zinc-500 mb-2">Set your filters and click "Screen Stocks"</p>
              <p className="text-xs text-zinc-600">Results will appear here</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default Screener;
