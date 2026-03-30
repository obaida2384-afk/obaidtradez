import { useState, useEffect, useCallback, memo, useRef, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { useLivePrices, LiveIndicator } from "../hooks/useLivePrices";
import { 
  PiggyBank,
  TrendingUp, 
  TrendingDown,
  Target,
  AlertTriangle,
  Search,
  Loader2,
  ChevronRight,
  ChevronLeft,
  DollarSign,
  Shield,
  BarChart3,
  Sparkles,
  RefreshCw,
  Filter,
  X,
  Building2,
  Globe,
  Gauge,
  Star,
  Clock,
  Download
} from "lucide-react";
import { toast } from "sonner";

// CSV Export Utility
const exportToCSV = (data, filename, columns) => {
  if (!data || data.length === 0) {
    toast.error("No data to export");
    return;
  }
  
  const headers = columns.map(col => col.label).join(',');
  const rows = data.map(item => {
    return columns.map(col => {
      let value = col.accessor(item);
      if (typeof value === 'string' && value.includes(',')) {
        value = `"${value}"`;
      }
      return value ?? '';
    }).join(',');
  });
  
  const csv = [headers, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  toast.success(`Exported ${data.length} rows to ${filename}.csv`);
};

// Score Bar
const ScoreBar = ({ label, score }) => {
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

// Data Completeness Indicator
const CompletenessIndicator = ({ value }) => {
  const getColor = () => {
    if (value >= 80) return "text-emerald-400";
    if (value >= 60) return "text-amber-400";
    return "text-red-400";
  };
  
  return (
    <span className={`text-[10px] ${getColor()}`} title={`${value}% data available`}>
      {value < 80 && <AlertTriangle className="w-3 h-3 inline mr-0.5" />}
      {value.toFixed(0)}%
    </span>
  );
};

// Investment Signal Card - memoized to prevent re-renders on 270+ cards
const InvestmentCard = memo(({ signal, expanded, onToggle, token, inWatchlist, onWatchlistToggle, livePrice }) => {
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [flash, setFlash] = useState(null);
  const prevPriceRef = useRef(null);
  
  // Use live price if available
  const displayPrice = livePrice?.price || signal.price;
  const displayChangePct = livePrice?.change_pct;
  
  // Flash effect on price change
  useEffect(() => {
    if (prevPriceRef.current !== null && prevPriceRef.current !== displayPrice && displayPrice > 0) {
      setFlash(displayPrice > prevPriceRef.current ? "up" : "down");
      const timeout = setTimeout(() => setFlash(null), 500);
      return () => clearTimeout(timeout);
    }
    prevPriceRef.current = displayPrice;
  }, [displayPrice]);
  
  const getScoreColor = (score) => {
    if (score >= 70) return "text-emerald-400";
    if (score >= 55) return "text-blue-400";
    if (score >= 40) return "text-amber-400";
    return "text-red-400";
  };
  
  const formatMarketCap = (cap) => {
    if (!cap) return "N/A";
    if (cap >= 1e12) return `$${(cap / 1e12).toFixed(1)}T`;
    if (cap >= 1e9) return `$${(cap / 1e9).toFixed(1)}B`;
    if (cap >= 1e6) return `$${(cap / 1e6).toFixed(0)}M`;
    return `$${cap.toLocaleString()}`;
  };

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
          body: JSON.stringify({ symbol: signal.symbol, source: "investments" })
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
                {signal.data_completeness < 80 && (
                  <CompletenessIndicator value={signal.data_completeness} />
                )}
              </div>
              <p className="text-xs text-slate-500 truncate max-w-[200px]">{signal.name}</p>
              <div className="flex items-center gap-2 mt-0.5">
                {signal.sector && (
                  <span className="text-[10px] text-slate-600">{signal.sector}</span>
                )}
                {signal.market_cap_label && (
                  <span className="text-[10px] text-slate-600">• {signal.market_cap_label}</span>
                )}
              </div>
            </div>
          </div>
          <div className={`text-right transition-all duration-300 rounded p-1 -m-1 ${flashClass}`}>
            <p className="font-mono text-lg text-white">${displayPrice?.toFixed(2)}</p>
            {displayChangePct !== undefined ? (
              <p className={`text-sm font-mono ${displayChangePct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {displayChangePct >= 0 ? '+' : ''}{displayChangePct.toFixed(2)}%
              </p>
            ) : signal.upside_potential && (
              <p className={`text-sm font-mono ${signal.upside_potential.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
                {signal.upside_potential} upside
              </p>
            )}
            <p className="text-[10px] text-slate-600">{formatMarketCap(signal.market_cap)}</p>
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
          {/* ====== DECISION CLARITY SECTION ====== */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {/* Why This Is Strong */}
            <div className="p-3 rounded-lg bg-gradient-to-br from-emerald-500/10 to-transparent border border-emerald-500/30">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <TrendingUp className="w-3 h-3 text-emerald-400" />
                </div>
                <p className="text-xs font-semibold text-emerald-400">Why It's Strong</p>
              </div>
              {signal.bull_case?.length > 0 ? (
                <ul className="space-y-1">
                  {signal.bull_case.slice(0, 3).map((item, i) => (
                    <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                      <span className="text-emerald-400 mt-0.5">✓</span> 
                      <span className="line-clamp-2">{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500">Strong fundamentals</p>
              )}
            </div>
            
            {/* Biggest Risk */}
            <div className="p-3 rounded-lg bg-gradient-to-br from-amber-500/10 to-transparent border border-amber-500/30">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-amber-500/20 flex items-center justify-center">
                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                </div>
                <p className="text-xs font-semibold text-amber-400">Biggest Risk</p>
              </div>
              {signal.score_drivers?.biggest_weakness ? (
                <p className="text-xs text-slate-300">{signal.score_drivers.biggest_weakness}</p>
              ) : signal.bear_case?.length > 0 ? (
                <p className="text-xs text-slate-300">{signal.bear_case[0]}</p>
              ) : signal.risks?.length > 0 ? (
                <p className="text-xs text-slate-300">{signal.risks[0]}</p>
              ) : (
                <p className="text-xs text-slate-500">No major risks identified</p>
              )}
            </div>
            
            {/* Valuation Verdict */}
            <div className="p-3 rounded-lg bg-gradient-to-br from-blue-500/10 to-transparent border border-blue-500/30">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <DollarSign className="w-3 h-3 text-blue-400" />
                </div>
                <p className="text-xs font-semibold text-blue-400">Valuation Verdict</p>
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Status:</span>
                  <span className={`text-xs font-medium ${
                    signal.valuation_summary?.classification?.includes('Under') ? 'text-emerald-400' : 
                    signal.valuation_summary?.classification?.includes('Over') ? 'text-red-400' : 'text-slate-300'
                  }`}>
                    {signal.valuation_summary?.classification || 'Fair Value'}
                  </span>
                </div>
                {signal.intrinsic_value && signal.price && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">Fair Value:</span>
                    <span className="text-xs font-mono text-white">${signal.intrinsic_value?.toFixed(2)}</span>
                  </div>
                )}
                {signal.upside_potential && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500">Upside:</span>
                    <span className={`text-xs font-mono ${signal.upside_potential.startsWith('+') ? 'text-emerald-400' : 'text-red-400'}`}>
                      {signal.upside_potential}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
          
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
          
          {/* Valuation Summary */}
          {signal.valuation_summary && (
            <div className="p-3 rounded bg-slate-900/50 border border-slate-800">
              <p className="text-xs text-blue-400 mb-2 flex items-center gap-1">
                <DollarSign className="w-3 h-3" /> Valuation Summary
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                {signal.valuation_summary.pe_ratio && (
                  <div>
                    <p className="text-slate-500">P/E Ratio</p>
                    <p className="font-mono text-white">{signal.valuation_summary.pe_ratio?.toFixed(1)}x</p>
                    <p className={`text-[10px] ${signal.valuation_summary.pe_vs_sector === 'Discount' ? 'text-emerald-400' : signal.valuation_summary.pe_vs_sector === 'Expensive' ? 'text-red-400' : 'text-slate-500'}`}>
                      {signal.valuation_summary.pe_vs_sector}
                    </p>
                  </div>
                )}
                {signal.valuation_summary.ev_ebitda && (
                  <div>
                    <p className="text-slate-500">EV/EBITDA</p>
                    <p className="font-mono text-white">{signal.valuation_summary.ev_ebitda?.toFixed(1)}x</p>
                    <p className="text-[10px] text-slate-500">{signal.valuation_summary.ev_ebitda_vs_sector}</p>
                  </div>
                )}
                {signal.valuation_summary.intrinsic_value && (
                  <div>
                    <p className="text-slate-500">Fair Value</p>
                    <p className="font-mono text-emerald-400">${signal.valuation_summary.intrinsic_value?.toFixed(2)}</p>
                  </div>
                )}
                <div>
                  <p className="text-slate-500">Classification</p>
                  <p className={`font-medium ${signal.valuation_summary.classification?.includes('Under') ? 'text-emerald-400' : signal.valuation_summary.classification?.includes('Over') ? 'text-red-400' : 'text-slate-300'}`}>
                    {signal.valuation_summary.classification || 'N/A'}
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Business Quality */}
          {signal.business_quality && (
            <div className="p-3 rounded bg-slate-900/50 border border-slate-800">
              <p className="text-xs text-purple-400 mb-2 flex items-center gap-1">
                <BarChart3 className="w-3 h-3" /> Business Quality
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                {signal.business_quality.roe !== null && signal.business_quality.roe !== undefined && (
                  <div>
                    <p className="text-slate-500">ROE</p>
                    <p className={`font-mono ${signal.business_quality.roe > 20 ? 'text-emerald-400' : signal.business_quality.roe > 12 ? 'text-white' : 'text-amber-400'}`}>
                      {signal.business_quality.roe?.toFixed(1)}%
                    </p>
                  </div>
                )}
                {signal.business_quality.net_margin !== null && signal.business_quality.net_margin !== undefined && (
                  <div>
                    <p className="text-slate-500">Net Margin</p>
                    <p className={`font-mono ${signal.business_quality.net_margin > 20 ? 'text-emerald-400' : signal.business_quality.net_margin > 10 ? 'text-white' : 'text-amber-400'}`}>
                      {signal.business_quality.net_margin?.toFixed(1)}%
                    </p>
                  </div>
                )}
                {signal.business_quality.gross_margin !== null && signal.business_quality.gross_margin !== undefined && (
                  <div>
                    <p className="text-slate-500">Gross Margin</p>
                    <p className="font-mono text-white">{signal.business_quality.gross_margin?.toFixed(1)}%</p>
                  </div>
                )}
                <div>
                  <p className="text-slate-500">Quality Rating</p>
                  <p className={`font-medium ${signal.business_quality.quality_rating === 'Excellent' ? 'text-emerald-400' : signal.business_quality.quality_rating === 'Good' ? 'text-blue-400' : 'text-slate-300'}`}>
                    {signal.business_quality.quality_rating}
                  </p>
                </div>
              </div>
            </div>
          )}
          
          {/* Growth Profile */}
          {signal.growth_profile && (
            <div className="p-3 rounded bg-slate-900/50 border border-slate-800">
              <p className="text-xs text-cyan-400 mb-2 flex items-center gap-1">
                <TrendingUp className="w-3 h-3" /> Growth Profile
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                {signal.growth_profile.revenue_growth !== null && signal.growth_profile.revenue_growth !== undefined && (
                  <div>
                    <p className="text-slate-500">Revenue Growth</p>
                    <p className={`font-mono ${signal.growth_profile.revenue_growth > 15 ? 'text-emerald-400' : signal.growth_profile.revenue_growth > 5 ? 'text-white' : signal.growth_profile.revenue_growth < 0 ? 'text-red-400' : 'text-amber-400'}`}>
                      {signal.growth_profile.revenue_growth > 0 ? '+' : ''}{signal.growth_profile.revenue_growth?.toFixed(1)}%
                    </p>
                  </div>
                )}
                {signal.growth_profile.earnings_growth !== null && signal.growth_profile.earnings_growth !== undefined && (
                  <div>
                    <p className="text-slate-500">EPS Growth</p>
                    <p className={`font-mono ${signal.growth_profile.earnings_growth > 15 ? 'text-emerald-400' : signal.growth_profile.earnings_growth > 5 ? 'text-white' : signal.growth_profile.earnings_growth < 0 ? 'text-red-400' : 'text-amber-400'}`}>
                      {signal.growth_profile.earnings_growth > 0 ? '+' : ''}{signal.growth_profile.earnings_growth?.toFixed(1)}%
                    </p>
                  </div>
                )}
                <div>
                  <p className="text-slate-500">Trend</p>
                  <p className={`font-medium ${signal.growth_profile.growth_trend === 'Accelerating' ? 'text-emerald-400' : signal.growth_profile.growth_trend === 'Declining' ? 'text-red-400' : 'text-slate-300'}`}>
                    {signal.growth_profile.growth_trend}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Rating</p>
                  <p className="text-slate-300">{signal.growth_profile.growth_rating}</p>
                </div>
              </div>
            </div>
          )}
          
          {/* Historical Performance (30yr) */}
          {signal.historical_performance && (
            <div className="p-3 rounded bg-slate-900/50 border border-slate-800" data-testid="historical-performance">
              <p className="text-xs text-amber-400 mb-2 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Historical Performance ({signal.historical_performance.years_of_data}yr data)
                <span className={`ml-auto text-[10px] font-medium px-2 py-0.5 rounded ${
                  signal.historical_performance.historical_rating === 'Exceptional' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                  signal.historical_performance.historical_rating === 'Strong' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' :
                  signal.historical_performance.historical_rating === 'Average' ? 'bg-slate-500/20 text-slate-400 border border-slate-500/30' :
                  'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {signal.historical_performance.historical_rating}
                </span>
              </p>
              
              {/* CAGR Returns */}
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2 text-xs mb-3">
                {[
                  { label: '1Y', value: signal.historical_performance.cagr_1yr },
                  { label: '3Y', value: signal.historical_performance.cagr_3yr },
                  { label: '5Y', value: signal.historical_performance.cagr_5yr },
                  { label: '10Y', value: signal.historical_performance.cagr_10yr },
                  { label: '20Y', value: signal.historical_performance.cagr_20yr },
                  { label: '30Y', value: signal.historical_performance.cagr_30yr },
                ].filter(c => c.value !== null && c.value !== undefined).map((c) => (
                  <div key={c.label} className="text-center p-1.5 rounded bg-slate-800/50">
                    <p className="text-slate-500 text-[10px]">{c.label} CAGR</p>
                    <p className={`font-mono font-medium ${c.value >= 15 ? 'text-emerald-400' : c.value >= 8 ? 'text-blue-400' : c.value >= 0 ? 'text-white' : 'text-red-400'}`}>
                      {c.value > 0 ? '+' : ''}{c.value?.toFixed(1)}%
                    </p>
                  </div>
                ))}
              </div>
              
              {/* Risk & Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                {signal.historical_performance.max_drawdown_pct !== null && (
                  <div>
                    <p className="text-slate-500">Max Drawdown</p>
                    <p className={`font-mono ${signal.historical_performance.max_drawdown_pct > -30 ? 'text-emerald-400' : signal.historical_performance.max_drawdown_pct > -50 ? 'text-amber-400' : 'text-red-400'}`}>
                      {signal.historical_performance.max_drawdown_pct?.toFixed(1)}%
                    </p>
                    {signal.historical_performance.recovery_months && (
                      <p className="text-[10px] text-slate-600">Recovery: {signal.historical_performance.recovery_months}mo</p>
                    )}
                  </div>
                )}
                {signal.historical_performance.annualized_volatility !== null && (
                  <div>
                    <p className="text-slate-500">Volatility</p>
                    <p className={`font-mono ${signal.historical_performance.annualized_volatility < 25 ? 'text-emerald-400' : signal.historical_performance.annualized_volatility < 40 ? 'text-amber-400' : 'text-red-400'}`}>
                      {signal.historical_performance.annualized_volatility?.toFixed(1)}%
                    </p>
                  </div>
                )}
                {signal.historical_performance.positive_years > 0 && (
                  <div>
                    <p className="text-slate-500">Win/Loss Years</p>
                    <p className="font-mono text-white">
                      <span className="text-emerald-400">{signal.historical_performance.positive_years}</span>
                      <span className="text-slate-600"> / </span>
                      <span className="text-red-400">{signal.historical_performance.negative_years}</span>
                    </p>
                  </div>
                )}
                {signal.historical_performance.current_vs_ath_pct !== null && (
                  <div>
                    <p className="text-slate-500">vs ATH</p>
                    <p className={`font-mono ${signal.historical_performance.current_vs_ath_pct > -10 ? 'text-emerald-400' : signal.historical_performance.current_vs_ath_pct > -30 ? 'text-amber-400' : 'text-red-400'}`}>
                      {signal.historical_performance.current_vs_ath_pct?.toFixed(1)}%
                    </p>
                    {signal.historical_performance.sma_200_trend && (
                      <p className={`text-[10px] ${signal.historical_performance.sma_200_trend === 'Above' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {signal.historical_performance.sma_200_trend} 200 SMA
                      </p>
                    )}
                  </div>
                )}
              </div>
              
              {/* Best/Worst Years */}
              {(signal.historical_performance.best_year || signal.historical_performance.worst_year) && (
                <div className="flex gap-4 mt-2 text-xs">
                  {signal.historical_performance.best_year && (
                    <span className="text-slate-500">
                      Best: <span className="text-emerald-400 font-mono">{signal.historical_performance.best_year} (+{signal.historical_performance.best_year_pct?.toFixed(0)}%)</span>
                    </span>
                  )}
                  {signal.historical_performance.worst_year && (
                    <span className="text-slate-500">
                      Worst: <span className="text-red-400 font-mono">{signal.historical_performance.worst_year} ({signal.historical_performance.worst_year_pct?.toFixed(0)}%)</span>
                    </span>
                  )}
                  {signal.historical_performance.total_return_pct !== null && (
                    <span className="text-slate-500 ml-auto">
                      Total Return: <span className={`font-mono ${signal.historical_performance.total_return_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {signal.historical_performance.total_return_pct > 0 ? '+' : ''}{signal.historical_performance.total_return_pct?.toFixed(0)}%
                      </span>
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
          
          {/* Score Drivers */}
          {signal.score_drivers && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {signal.score_drivers.boosters?.length > 0 && (
                <div className="p-3 rounded bg-emerald-500/5 border border-emerald-500/20">
                  <p className="text-xs text-emerald-400 mb-2">Score Boosters</p>
                  <ul className="space-y-1">
                    {signal.score_drivers.boosters.slice(0, 4).map((item, i) => (
                      <li key={i} className="text-xs text-slate-300 flex items-start gap-1">
                        <span className="text-emerald-400">+</span> {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {signal.score_drivers.detractors?.length > 0 && (
                <div className="p-3 rounded bg-red-500/5 border border-red-500/20">
                  <p className="text-xs text-red-400 mb-2">Score Detractors</p>
                  <ul className="space-y-1">
                    {signal.score_drivers.detractors.slice(0, 4).map((item, i) => (
                      <li key={i} className="text-xs text-slate-300 flex items-start gap-1">
                        <span className="text-red-400">-</span> {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          
          {/* Biggest Weakness */}
          {signal.score_drivers?.biggest_weakness && (
            <div className="flex items-center gap-2 text-xs">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              <span className="text-slate-500">Biggest weakness:</span>
              <span className="text-amber-400">{signal.score_drivers.biggest_weakness}</span>
            </div>
          )}
          
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
          
          {/* Percentile Rank */}
          {signal.percentile_rank && (
            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800">
              <span className="text-slate-500">Percentile Rank</span>
              <span className={`font-mono ${signal.percentile_rank >= 75 ? 'text-emerald-400' : signal.percentile_rank >= 50 ? 'text-blue-400' : 'text-slate-400'}`}>
                Top {(100 - signal.percentile_rank).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
});

// Filter Panel
// Screener Presets
const SCREENER_PRESETS = {
  "value_picks": {
    name: "Value Picks",
    icon: "💎",
    description: "Undervalued stocks with strong fundamentals",
    filters: { minValuation: 70, minQuality: 60, signal: "Buy" }
  },
  "growth_stocks": {
    name: "Growth Stocks",
    icon: "🚀",
    description: "High growth companies with momentum",
    filters: { minGrowth: 70, minScore: 60 }
  },
  "dividend_quality": {
    name: "Quality Dividend",
    icon: "💰",
    description: "High-quality dividend payers",
    filters: { minQuality: 75, minScore: 65 }
  },
  "safe_havens": {
    name: "Safe Havens",
    icon: "🛡️",
    description: "Low-risk, stable investments",
    filters: { minScore: 70, minQuality: 70, minValuation: 50 }
  },
  "bargain_hunters": {
    name: "Bargain Hunters",
    icon: "🔍",
    description: "Deep value opportunities",
    filters: { minValuation: 80, signal: "Buy" }
  },
  "tech_leaders": {
    name: "Tech Leaders",
    icon: "💻",
    description: "Top technology stocks",
    filters: { sector: "Technology", minScore: 60 }
  },
  "healthcare_picks": {
    name: "Healthcare Picks",
    icon: "🏥",
    description: "Healthcare & biotech opportunities",
    filters: { sector: "Healthcare", minScore: 55 }
  },
  "financial_strength": {
    name: "Financial Fortress",
    icon: "🏦",
    description: "Companies with rock-solid balance sheets",
    filters: { minQuality: 80, minScore: 65 }
  }
};

const FilterPanel = ({ filters, setFilters, filterOptions, onApply, onReset }) => {
  const [activePreset, setActivePreset] = useState(null);
  
  const applyPreset = (presetKey) => {
    const preset = SCREENER_PRESETS[presetKey];
    if (preset) {
      setFilters({
        ...filters,
        ...preset.filters
      });
      setActivePreset(presetKey);
      // Auto-apply after selecting preset
      setTimeout(() => onApply(), 100);
    }
  };
  
  const handleReset = () => {
    setActivePreset(null);
    onReset();
  };
  
  return (
    <Card className="terminal-card p-4 mb-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-white">Filters & Presets</span>
          {filterOptions?.total_signals > 0 && (
            <Badge variant="outline" className="text-xs border-slate-700">
              {filterOptions.total_signals} stocks
            </Badge>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={handleReset} className="text-slate-400 hover:text-white">
          <X className="w-3 h-3 mr-1" /> Reset
        </Button>
      </div>
      
      {/* Screener Presets */}
      <div className="mb-4">
        <label className="text-xs text-slate-500 mb-2 block">Quick Presets</label>
        <div className="flex flex-wrap gap-2">
          {Object.entries(SCREENER_PRESETS).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => applyPreset(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                activePreset === key 
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' 
                  : 'bg-slate-900 text-slate-400 border border-slate-700 hover:border-slate-600 hover:text-white'
              }`}
              title={preset.description}
            >
              <span>{preset.icon}</span>
              <span>{preset.name}</span>
            </button>
          ))}
        </div>
      </div>
      
      <div className="grid md:grid-cols-4 gap-4">
        {/* Market Cap */}
        <div>
          <label className="text-xs text-slate-500 mb-2 block">Market Cap</label>
          <Select 
            value={filters.marketCap || "all"} 
            onValueChange={(v) => setFilters({...filters, marketCap: v === "all" ? null : v})}
          >
            <SelectTrigger className="bg-slate-900 border-slate-700">
              <SelectValue placeholder="All Sizes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sizes</SelectItem>
              <SelectItem value="mega">Mega Cap (&gt;$200B)</SelectItem>
              <SelectItem value="large">Large Cap ($10B-$200B)</SelectItem>
              <SelectItem value="mid">Mid Cap ($2B-$10B)</SelectItem>
              <SelectItem value="small">Small Cap ($300M-$2B)</SelectItem>
              <SelectItem value="micro">Micro Cap (&lt;$300M)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        {/* Sector */}
        <div>
          <label className="text-xs text-slate-500 mb-2 block">Sector</label>
          <Select 
            value={filters.sector || "all"} 
            onValueChange={(v) => setFilters({...filters, sector: v === "all" ? null : v})}
          >
            <SelectTrigger className="bg-slate-900 border-slate-700">
              <SelectValue placeholder="All Sectors" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sectors</SelectItem>
              {filterOptions?.sectors?.map(s => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        {/* Signal */}
        <div>
          <label className="text-xs text-slate-500 mb-2 block">Signal</label>
          <Select 
            value={filters.signal || "all"} 
            onValueChange={(v) => setFilters({...filters, signal: v === "all" ? null : v})}
          >
            <SelectTrigger className="bg-slate-900 border-slate-700">
              <SelectValue placeholder="All Signals" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Signals</SelectItem>
              <SelectItem value="Buy">Buy ({filterOptions?.signals?.Buy || 0})</SelectItem>
              <SelectItem value="Hold">Hold ({filterOptions?.signals?.Hold || 0})</SelectItem>
              <SelectItem value="Watchlist">Watchlist ({filterOptions?.signals?.Watchlist || 0})</SelectItem>
              <SelectItem value="Sell">Sell ({filterOptions?.signals?.Sell || 0})</SelectItem>
            </SelectContent>
          </Select>
        </div>
        
        {/* Min Score */}
        <div>
          <label className="text-xs text-slate-500 mb-2 block">Min Score: {filters.minScore || 0}</label>
          <Slider
            value={[filters.minScore || 0]}
            onValueChange={([v]) => setFilters({...filters, minScore: v})}
            min={0}
            max={90}
            step={5}
            className="mt-2"
          />
        </div>
      </div>
      
      {/* Advanced Filters Row */}
      <div className="grid md:grid-cols-4 gap-4 mt-4">
        <div>
          <label className="text-xs text-slate-500 mb-2 block">Min Valuation Score</label>
          <Slider
            value={[filters.minValuation || 0]}
            onValueChange={([v]) => setFilters({...filters, minValuation: v})}
            min={0}
            max={90}
            step={5}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 mb-2 block">Min Quality Score</label>
          <Slider
            value={[filters.minQuality || 0]}
            onValueChange={([v]) => setFilters({...filters, minQuality: v})}
            min={0}
            max={90}
            step={5}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 mb-2 block">Min Growth Score</label>
          <Slider
            value={[filters.minGrowth || 0]}
            onValueChange={([v]) => setFilters({...filters, minGrowth: v})}
            min={0}
            max={90}
            step={5}
          />
        </div>
        <div className="flex items-end">
          <Button onClick={onApply} className="w-full bg-emerald-600 hover:bg-emerald-500">
            Apply Filters
          </Button>
        </div>
      </div>
    </Card>
  );
};

// Pagination
const Pagination = ({ page, totalPages, onPageChange }) => {
  if (totalPages <= 1) return null;
  
  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="border-slate-700"
      >
        <ChevronLeft className="w-4 h-4" />
      </Button>
      
      <div className="flex items-center gap-1">
        {[...Array(Math.min(5, totalPages))].map((_, i) => {
          let pageNum;
          if (totalPages <= 5) {
            pageNum = i + 1;
          } else if (page <= 3) {
            pageNum = i + 1;
          } else if (page >= totalPages - 2) {
            pageNum = totalPages - 4 + i;
          } else {
            pageNum = page - 2 + i;
          }
          
          return (
            <Button
              key={pageNum}
              variant={pageNum === page ? "default" : "outline"}
              size="sm"
              onClick={() => onPageChange(pageNum)}
              className={pageNum === page ? "bg-blue-600" : "border-slate-700"}
            >
              {pageNum}
            </Button>
          );
        })}
      </div>
      
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="border-slate-700"
      >
        <ChevronRight className="w-4 h-4" />
      </Button>
      
      <span className="text-xs text-slate-500 ml-2">
        Page {page} of {totalPages}
      </span>
    </div>
  );
};

const Investments = () => {
  const [signals, setSignals] = useState(null);
  const [browseData, setBrowseData] = useState(null);
  const [filterOptions, setFilterOptions] = useState(null);
  const [searchSymbol, setSearchSymbol] = useState("");
  const [searchResult, setSearchResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedCard, setExpandedCard] = useState(null);
  const [activeTab, setActiveTab] = useState("browse");
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(1);
  const [watchlistSymbols, setWatchlistSymbols] = useState(new Set());
  const [filters, setFilters] = useState({
    marketCap: null,
    sector: null,
    signal: null,
    minScore: 0,
    minValuation: 0,
    minQuality: 0,
    minGrowth: 0
  });
  const { token } = useAuth();
  const [searchParams] = useSearchParams();

  // Get visible symbols for live price streaming - limit to current page to avoid overload
  const visibleSymbols = useMemo(() => {
    if (activeTab === "browse") {
      return browseData?.signals?.map(s => s.symbol) || [];
    } else {
      // Category tabs - limit to first 30 visible
      const categorySignals = {
        hot: signals?.hot || [],
        bullish: signals?.bullish || [],
        undervalued: signals?.undervalued || [],
        watch: signals?.watch || [],
        bearish: [...(signals?.bearish || []), ...(signals?.overpriced || [])]
      }[activeTab] || [];
      return categorySignals.slice(0, 30).map(s => s.symbol);
    }
  }, [activeTab, browseData?.signals, signals]);
  
  // Live prices - 20s interval for investment view (longer hold periods = less frequent updates needed)
  const { prices: livePrices, loading: pricesLoading } = useLivePrices(visibleSymbols, 20000, visibleSymbols.length > 0);

  const fetchWatchlist = useCallback(async () => {
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
  }, [token]);

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

  const fetchFilterOptions = useCallback(async () => {
    try {
      const response = await fetch(`${API}/investments/filters`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setFilterOptions(await response.json());
      }
    } catch (error) {
      console.error("Error fetching filters:", error);
    }
  }, [token]);

  const fetchBrowseData = useCallback(async (pageNum = 1) => {
    try {
      const params = new URLSearchParams({
        page: pageNum.toString(),
        page_size: "30",
        sort_by: "overall_score",
        sort_dir: "desc"
      });
      
      // Apply filters
      if (filters.marketCap) {
        const ranges = {
          mega: { min: 200e9 },
          large: { min: 10e9, max: 200e9 },
          mid: { min: 2e9, max: 10e9 },
          small: { min: 300e6, max: 2e9 },
          micro: { max: 300e6 }
        };
        const range = ranges[filters.marketCap];
        if (range?.min) params.append("min_market_cap", range.min);
        if (range?.max) params.append("max_market_cap", range.max);
      }
      if (filters.sector) params.append("sectors", filters.sector);
      if (filters.signal) params.append("signals", filters.signal);
      if (filters.minScore > 0) params.append("min_score", filters.minScore);
      if (filters.minValuation > 0) params.append("min_valuation", filters.minValuation);
      if (filters.minQuality > 0) params.append("min_quality", filters.minQuality);
      if (filters.minGrowth > 0) params.append("min_growth", filters.minGrowth);
      
      const response = await fetch(`${API}/investments/browse?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setBrowseData(await response.json());
      }
    } catch (error) {
      console.error("Error fetching browse data:", error);
    }
  }, [token, filters]);

  const fetchSignals = useCallback(async () => {
    try {
      const response = await fetch(`${API}/investments/scan`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setSignals(await response.json());
      }
    } catch (error) {
      console.error("Error:", error);
    }
  }, [token]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchSignals(),
        fetchFilterOptions(),
        fetchBrowseData(1),
        fetchWatchlist()
      ]);
      setLoading(false);
      
      const symbol = searchParams.get("symbol");
      if (symbol) {
        setSearchSymbol(symbol);
        searchStock(symbol);
      }
    };
    loadData();
  }, []);

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

  const refreshUniverse = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API}/investments/refresh?limit=300`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      // Wait a bit then refresh data
      setTimeout(async () => {
        await fetchBrowseData(1);
        await fetchSignals();
        await fetchFilterOptions();
        setRefreshing(false);
      }, 3000);
    } catch (error) {
      console.error("Refresh error:", error);
      setRefreshing(false);
    }
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
    fetchBrowseData(newPage);
  };

  const applyFilters = () => {
    setPage(1);
    fetchBrowseData(1);
  };

  const resetFilters = () => {
    setFilters({
      marketCap: null,
      sector: null,
      signal: null,
      minScore: 0,
      minValuation: 0,
      minQuality: 0,
      minGrowth: 0
    });
    setPage(1);
    fetchBrowseData(1);
  };

  const getTabSignals = () => {
    if (!signals) return [];
    switch (activeTab) {
      case "hot": return signals.hot || [];
      case "bullish": return signals.bullish || [];
      case "undervalued": return signals.undervalued || [];
      case "watch": return signals.watch || [];
      case "bearish": return [...(signals.bearish || []), ...(signals.overpriced || [])];
      default: return [];
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="investments-loading">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-slate-500 text-sm">Loading investment universe...</p>
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
            {filterOptions?.total_signals > 0 && (
              <Badge variant="outline" className="text-xs border-emerald-500/30 text-emerald-400">
                {filterOptions.total_signals} stocks analyzed
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500">Broad market coverage with fundamental analysis</p>
        </div>
        
        {/* Actions */}
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && searchStock(searchSymbol)}
              placeholder="Search symbol..."
              className="pl-10 w-40 md:w-48 bg-slate-900 border-slate-700"
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
          <Button 
            variant="outline"
            onClick={refreshUniverse}
            disabled={refreshing}
            className="border-slate-700"
            data-testid="refresh-universe-btn"
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? "Scanning..." : "Refresh"}
          </Button>
          <Button 
            variant="outline"
            onClick={() => {
              const currentTab = signals[activeTab] || [];
              exportToCSV(currentTab, `investment_ideas_${activeTab}`, [
                { label: 'Symbol', accessor: (s) => s.symbol },
                { label: 'Name', accessor: (s) => s.name },
                { label: 'Sector', accessor: (s) => s.sector },
                { label: 'Signal', accessor: (s) => s.signal },
                { label: 'Category', accessor: (s) => s.category },
                { label: 'Overall Score', accessor: (s) => s.overall_score?.toFixed(1) },
                { label: 'Valuation Score', accessor: (s) => s.valuation_score?.toFixed(1) },
                { label: 'Quality Score', accessor: (s) => s.quality_score?.toFixed(1) },
                { label: 'Growth Score', accessor: (s) => s.growth_score?.toFixed(1) },
                { label: 'Price', accessor: (s) => s.price?.toFixed(2) },
                { label: 'Fair Value', accessor: (s) => s.intrinsic_value?.toFixed(2) },
                { label: 'Upside', accessor: (s) => s.upside_potential },
                { label: 'Market Cap', accessor: (s) => s.market_cap_label },
                { label: 'Confidence', accessor: (s) => (s.confidence * 100).toFixed(0) + '%' }
              ]);
            }}
            className="border-slate-700"
            data-testid="export-csv-btn"
          >
            <Download className="w-4 h-4 mr-1" />
            Export
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
            token={token}
            inWatchlist={watchlistSymbols.has(searchResult.symbol)}
            onWatchlistToggle={handleWatchlistToggle}
            livePrice={livePrices[searchResult.symbol]}
          />
        </section>
      )}

      {/* Live Price Indicator */}
      {visibleSymbols.length > 0 && Object.keys(livePrices).length > 0 && (
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <LiveIndicator active={true} />
          <span>Live prices • Updates every 20s • Showing {Object.keys(livePrices).length} prices</span>
        </div>
      )}

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="w-full justify-start bg-slate-900 border border-slate-800 p-1 h-auto flex-wrap">
          <TabsTrigger value="browse" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <Gauge className="w-4 h-4 mr-1" /> Browse All ({browseData?.total || 0})
          </TabsTrigger>
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

        {/* Browse Tab - Full Universe */}
        <TabsContent value="browse" className="mt-4">
          {/* Filter Toggle */}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setShowFilters(!showFilters)}
            className="mb-4 border-slate-700"
          >
            <Filter className="w-4 h-4 mr-1" />
            {showFilters ? "Hide Filters" : "Show Filters"}
          </Button>
          
          {/* Filter Panel */}
          {showFilters && (
            <FilterPanel 
              filters={filters}
              setFilters={setFilters}
              filterOptions={filterOptions}
              onApply={applyFilters}
              onReset={resetFilters}
            />
          )}
          
          {/* Results */}
          <div className="space-y-3">
            {browseData?.signals?.map((signal) => (
              <InvestmentCard 
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
            {(!browseData?.signals || browseData.signals.length === 0) && (
              <Card className="terminal-card p-8 text-center">
                <p className="text-slate-500 mb-2">No stocks found matching your criteria</p>
                <p className="text-xs text-slate-600">Try adjusting your filters or click "Refresh" to scan more stocks</p>
              </Card>
            )}
          </div>
          
          {/* Pagination */}
          <Pagination 
            page={browseData?.page || 1}
            totalPages={browseData?.total_pages || 1}
            onPageChange={handlePageChange}
          />
        </TabsContent>

        {/* Category Tabs */}
        {["hot", "bullish", "undervalued", "watch", "bearish"].map((tab) => (
          <TabsContent key={tab} value={tab} className="mt-4">
            <div className="space-y-3">
              {getTabSignals().map((signal) => (
                <InvestmentCard 
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
                  <p className="text-slate-500">No signals in this category</p>
                  <p className="text-xs text-slate-600 mt-1">Click "Refresh" to scan more stocks</p>
                </Card>
              )}
            </div>
          </TabsContent>
        ))}
      </Tabs>

      {/* Info Card */}
      <Card className="terminal-card p-4 border-blue-500/20 bg-blue-500/5">
        <div className="flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-blue-200 font-medium mb-1">Broad Market Coverage</p>
            <p className="text-xs text-blue-200/70">
              Our system scans hundreds of stocks across all market caps and sectors. Scoring is based on 
              valuation (P/E, EV/EBITDA), quality (ROE, margins), growth (revenue), financial strength (debt, liquidity), 
              and risk (beta, volatility). Stocks with incomplete data are included but marked accordingly.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Investments;
