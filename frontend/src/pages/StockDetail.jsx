import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from "recharts";
import { 
  ArrowLeft, 
  TrendingUp, 
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ExternalLink,
  Building2,
  Globe,
  Users
} from "lucide-react";
import { API } from "../App";

// Score Bar Component
const ScoreBar = ({ label, score, color = "blue" }) => {
  const colorClasses = {
    blue: "bg-blue-500",
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    red: "bg-red-500"
  };
  
  const getColor = (s) => {
    if (s >= 70) return "bg-emerald-500";
    if (s >= 55) return "bg-blue-500";
    if (s >= 40) return "bg-amber-500";
    return "bg-red-500";
  };
  
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-zinc-400">{label}</span>
        <span className="font-mono text-zinc-300">{score?.toFixed(0) || "—"}</span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-500 ${getColor(score)}`}
          style={{ width: `${Math.min(100, score || 0)}%` }}
        />
      </div>
    </div>
  );
};

// Metric Card
const MetricCard = ({ label, value, subValue, trend }) => (
  <div className="p-3 bg-zinc-800/50 rounded-md">
    <p className="data-label mb-1">{label}</p>
    <p className="font-mono text-lg text-white">{value || "—"}</p>
    {subValue && <p className="text-xs text-zinc-500">{subValue}</p>}
    {trend !== undefined && (
      <span className={`text-xs ${trend >= 0 ? "text-emerald-400" : "text-red-400"}`}>
        {trend >= 0 ? "+" : ""}{trend?.toFixed(1)}%
      </span>
    )}
  </div>
);

// Custom Tooltip for Charts
const ChartTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-zinc-900 border border-zinc-700 rounded-md p-3 shadow-xl">
        <p className="text-xs text-zinc-400 mb-1">{label}</p>
        <p className="font-mono text-white">${payload[0].value?.toFixed(2)}</p>
      </div>
    );
  }
  return null;
};

const StockDetail = () => {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [stock, setStock] = useState(null);
  const [historical, setHistorical] = useState([]);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStockData();
  }, [symbol]);

  const fetchStockData = async () => {
    setLoading(true);
    try {
      const [analysisRes, historicalRes, newsRes] = await Promise.all([
        fetch(`${API}/stock/${symbol}`),
        fetch(`${API}/stock/${symbol}/historical?days=180`),
        fetch(`${API}/stock/${symbol}/news?limit=5`)
      ]);
      
      if (analysisRes.ok) {
        setStock(await analysisRes.json());
      }
      
      if (historicalRes.ok) {
        const data = await historicalRes.json();
        const prices = (data.historical || []).reverse().map(d => ({
          date: d.date,
          price: d.close,
          volume: d.volume
        }));
        setHistorical(prices);
      }
      
      if (newsRes.ok) {
        setNews(await newsRes.json());
      }
    } catch (error) {
      console.error("Error fetching stock data:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="stock-detail-loading">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-zinc-500 text-sm">Analyzing {symbol}...</p>
        </div>
      </div>
    );
  }

  if (!stock) {
    return (
      <div className="text-center py-20">
        <p className="text-zinc-400">Unable to load data for {symbol}</p>
        <Button variant="outline" onClick={() => navigate("/")} className="mt-4">
          Back to Dashboard
        </Button>
      </div>
    );
  }

  const signalClass = {
    "Strong Candidate": "signal-strong",
    "Candidate": "signal-candidate",
    "Watchlist": "signal-watchlist",
    "Avoid": "signal-avoid"
  }[stock.investment_signal] || "signal-watchlist";

  return (
    <div className="space-y-6" data-testid="stock-detail">
      {/* Back Button */}
      <Button 
        variant="ghost" 
        size="sm" 
        onClick={() => navigate(-1)}
        className="text-zinc-400 hover:text-white -ml-2"
        data-testid="back-btn"
      >
        <ArrowLeft className="w-4 h-4 mr-1" /> Back
      </Button>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="font-heading text-3xl font-bold text-white">{stock.symbol}</h1>
            <span className={`text-sm font-medium px-3 py-1 rounded-full ${signalClass}`}>
              {stock.investment_signal}
            </span>
          </div>
          <p className="text-zinc-400 mb-2">{stock.company_name}</p>
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span className="flex items-center gap-1">
              <Building2 className="w-3 h-3" /> {stock.sector}
            </span>
            <span>{stock.industry}</span>
          </div>
        </div>

        <div className="text-right">
          <p className="font-mono text-4xl font-bold text-white">
            ${stock.price?.toFixed(2) || "—"}
          </p>
          <div className="flex items-center justify-end gap-2 mt-1">
            <Badge variant="outline" className="border-zinc-700 text-zinc-400">
              {stock.confidence} Confidence
            </Badge>
          </div>
        </div>
      </div>

      {/* Score Overview */}
      <Card className="terminal-card p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-heading text-lg font-semibold text-white">Overall Score</h2>
            <p className="text-xs text-zinc-500">Multi-factor analysis</p>
          </div>
          <div className="text-right">
            <span className={`font-mono text-4xl font-bold ${
              stock.overall_score >= 65 ? "text-emerald-400" :
              stock.overall_score >= 50 ? "text-blue-400" :
              stock.overall_score >= 35 ? "text-amber-400" : "text-red-400"
            }`}>
              {stock.overall_score?.toFixed(0)}
            </span>
            <span className="text-zinc-500 text-lg">/100</span>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <ScoreBar label="Valuation" score={stock.valuation_score} />
          <ScoreBar label="Fundamentals" score={stock.fundamentals_score} />
          <ScoreBar label="Growth" score={stock.growth_score} />
          <ScoreBar label="Momentum" score={stock.momentum_score} />
          <ScoreBar label="Technical" score={stock.technical_score} />
          <ScoreBar label="Sentiment" score={stock.sentiment_score} />
          <ScoreBar label="Risk (Lower=Riskier)" score={stock.risk_score} />
          <div className="p-3 bg-zinc-800/50 rounded-md">
            <p className="data-label mb-2">Strategy Fit</p>
            <div className="flex flex-wrap gap-1">
              {stock.strategy_fit?.length > 0 ? (
                stock.strategy_fit.map(s => (
                  <span key={s} className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded">
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-xs text-zinc-500">None matched</span>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Recommendation Reason */}
      <Card className="terminal-card p-6">
        <h3 className="font-heading font-semibold text-white mb-3">AI Analysis</h3>
        <p className="text-zinc-300 leading-relaxed">{stock.recommendation_reason}</p>
      </Card>

      {/* Main Content */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="bg-zinc-900 border border-zinc-800">
          <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
          <TabsTrigger value="valuation" data-testid="tab-valuation">Valuation</TabsTrigger>
          <TabsTrigger value="financials" data-testid="tab-financials">Financials</TabsTrigger>
          <TabsTrigger value="technicals" data-testid="tab-technicals">Technicals</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Price Chart */}
          <Card className="terminal-card p-6">
            <h3 className="font-heading font-semibold text-white mb-4">Price History (6M)</h3>
            {historical.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historical}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 10, fill: '#71717a' }}
                      tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis 
                      tick={{ fontSize: 10, fill: '#71717a' }}
                      domain={['auto', 'auto']}
                      tickFormatter={(v) => `$${v}`}
                    />
                    <Tooltip content={<ChartTooltip />} />
                    <Area 
                      type="monotone" 
                      dataKey="price" 
                      stroke="#2563eb" 
                      strokeWidth={2}
                      fill="url(#colorPrice)" 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-zinc-500 text-center py-10">Historical data unavailable</p>
            )}
          </Card>

          {/* Bull/Bear Case */}
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="terminal-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <h3 className="font-heading font-semibold text-white">Bull Case</h3>
              </div>
              <ul className="space-y-2">
                {stock.bull_case?.length > 0 ? (
                  stock.bull_case.map((point, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                      <TrendingUp className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                      {point}
                    </li>
                  ))
                ) : (
                  <li className="text-zinc-500 text-sm">No strong bullish factors identified</li>
                )}
              </ul>
            </Card>

            <Card className="terminal-card p-5">
              <div className="flex items-center gap-2 mb-4">
                <XCircle className="w-5 h-5 text-red-400" />
                <h3 className="font-heading font-semibold text-white">Bear Case</h3>
              </div>
              <ul className="space-y-2">
                {stock.bear_case?.length > 0 ? (
                  stock.bear_case.map((point, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                      <TrendingDown className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                      {point}
                    </li>
                  ))
                ) : (
                  <li className="text-zinc-500 text-sm">No major bearish concerns identified</li>
                )}
              </ul>
            </Card>
          </div>

          {/* Key Risks */}
          <Card className="terminal-card p-5">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              <h3 className="font-heading font-semibold text-white">Key Risks</h3>
            </div>
            <ul className="space-y-2">
              {stock.key_risks?.length > 0 ? (
                stock.key_risks.map((risk, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                    <span className="w-5 h-5 rounded bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs shrink-0">
                      {i + 1}
                    </span>
                    {risk}
                  </li>
                ))
              ) : (
                <li className="text-zinc-500 text-sm">No specific risks flagged</li>
              )}
            </ul>
          </Card>
        </TabsContent>

        <TabsContent value="valuation" className="space-y-4">
          <Card className="terminal-card p-6">
            <h3 className="font-heading font-semibold text-white mb-4">Valuation Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="P/E Ratio" value={stock.pe_ratio?.toFixed(1)} />
              <MetricCard label="Forward P/E" value={stock.forward_pe?.toFixed(1)} />
              <MetricCard label="PEG Ratio" value={stock.peg_ratio?.toFixed(2)} />
              <MetricCard label="P/B Ratio" value={stock.pb_ratio?.toFixed(2)} />
              <MetricCard label="EV/EBITDA" value={stock.ev_ebitda?.toFixed(1)} />
              <MetricCard label="Dividend Yield" value={stock.dividend_yield ? `${(stock.dividend_yield * 100).toFixed(2)}%` : "—"} />
              <MetricCard label="Market Cap" value={stock.market_cap ? `$${(stock.market_cap / 1e9).toFixed(1)}B` : "—"} />
              <MetricCard label="Valuation Score" value={`${stock.valuation_score?.toFixed(0)}/100`} />
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="financials" className="space-y-4">
          <Card className="terminal-card p-6">
            <h3 className="font-heading font-semibold text-white mb-4">Financial Strength</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="ROE" value={stock.roe ? `${(stock.roe * 100).toFixed(1)}%` : "—"} />
              <MetricCard label="ROA" value={stock.roa ? `${(stock.roa * 100).toFixed(1)}%` : "—"} />
              <MetricCard label="Gross Margin" value={stock.gross_margin ? `${(stock.gross_margin * 100).toFixed(1)}%` : "—"} />
              <MetricCard label="Operating Margin" value={stock.operating_margin ? `${(stock.operating_margin * 100).toFixed(1)}%` : "—"} />
              <MetricCard label="Net Margin" value={stock.net_margin ? `${(stock.net_margin * 100).toFixed(1)}%` : "—"} />
              <MetricCard label="Debt/Equity" value={stock.debt_to_equity?.toFixed(2)} />
              <MetricCard label="Current Ratio" value={stock.current_ratio?.toFixed(2)} />
              <MetricCard label="FCF/Share" value={stock.free_cash_flow ? `$${stock.free_cash_flow.toFixed(2)}` : "—"} />
            </div>
          </Card>

          <Card className="terminal-card p-6">
            <h3 className="font-heading font-semibold text-white mb-4">Growth Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard 
                label="Revenue Growth" 
                value={stock.revenue_growth ? `${(stock.revenue_growth * 100).toFixed(1)}%` : "—"} 
                trend={stock.revenue_growth ? stock.revenue_growth * 100 : undefined}
              />
              <MetricCard 
                label="Earnings Growth" 
                value={stock.earnings_growth ? `${(stock.earnings_growth * 100).toFixed(1)}%` : "—"}
                trend={stock.earnings_growth ? stock.earnings_growth * 100 : undefined}
              />
              <MetricCard label="Growth Score" value={`${stock.growth_score?.toFixed(0)}/100`} />
              <MetricCard label="Fundamentals Score" value={`${stock.fundamentals_score?.toFixed(0)}/100`} />
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="technicals" className="space-y-4">
          <Card className="terminal-card p-6">
            <h3 className="font-heading font-semibold text-white mb-4">Technical Indicators</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="Price vs 50 SMA" value={stock.price_to_sma50 ? `${stock.price_to_sma50.toFixed(1)}%` : "—"} />
              <MetricCard label="Price vs 200 SMA" value={stock.price_to_sma200 ? `${stock.price_to_sma200.toFixed(1)}%` : "—"} />
              <MetricCard label="52W High" value={stock.week_52_high ? `$${stock.week_52_high.toFixed(2)}` : "—"} />
              <MetricCard label="52W Low" value={stock.week_52_low ? `$${stock.week_52_low.toFixed(2)}` : "—"} />
              <MetricCard label="Distance from High" value={stock.distance_from_high ? `${stock.distance_from_high.toFixed(1)}%` : "—"} />
              <MetricCard label="Avg Volume" value={stock.avg_volume ? `${(stock.avg_volume / 1e6).toFixed(1)}M` : "—"} />
              <MetricCard label="Beta" value={stock.beta?.toFixed(2)} />
              <MetricCard label="Trading Signal" value={stock.trading_signal} />
            </div>
          </Card>

          <Card className="terminal-card p-6">
            <h3 className="font-heading font-semibold text-white mb-4">Technical Scores</h3>
            <div className="grid grid-cols-3 gap-4">
              <ScoreBar label="Momentum" score={stock.momentum_score} />
              <ScoreBar label="Technical Setup" score={stock.technical_score} />
              <ScoreBar label="Risk (Higher=Safer)" score={stock.risk_score} />
            </div>
          </Card>
        </TabsContent>
      </Tabs>

      {/* News Section */}
      {news.length > 0 && (
        <Card className="terminal-card p-6">
          <h3 className="font-heading font-semibold text-white mb-4">Recent News</h3>
          <div className="space-y-4">
            {news.map((item, i) => (
              <a
                key={i}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-3 bg-zinc-800/50 rounded-md hover:bg-zinc-800 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm text-white mb-1 line-clamp-2">{item.title}</p>
                    <p className="text-xs text-zinc-500">{item.site} • {new Date(item.publishedDate).toLocaleDateString()}</p>
                  </div>
                  <ExternalLink className="w-4 h-4 text-zinc-600 shrink-0" />
                </div>
              </a>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

export default StockDetail;
