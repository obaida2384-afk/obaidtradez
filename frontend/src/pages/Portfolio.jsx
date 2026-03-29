import { useState, useEffect, useCallback, memo, useRef } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { usePositionsPrices, LiveIndicator } from "../hooks/useLivePrices";
import { 
  Wallet,
  TrendingUp,
  TrendingDown,
  PieChart as PieChartIcon,
  DollarSign,
  Loader2,
  RefreshCw,
  Percent,
  BarChart3,
  LineChart as LineChartIcon,
  Activity,
  Target,
  AlertTriangle
} from "lucide-react";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";
import { toast } from "sonner";

// Chart colors
const COLORS = {
  primary: "#22c55e",
  secondary: "#3b82f6",
  danger: "#ef4444",
  warning: "#f59e0b",
  purple: "#a855f7",
  cyan: "#06b6d4",
  slate: "#64748b"
};

const SECTOR_COLORS = [
  "#22c55e", "#3b82f6", "#a855f7", "#f59e0b", "#ef4444",
  "#06b6d4", "#ec4899", "#84cc16", "#f97316", "#6366f1"
];

// Custom tooltip styles
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
        <p className="text-xs text-slate-400 mb-1">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm font-mono" style={{ color: entry.color }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
            {entry.name.includes('%') || entry.name.includes('Rate') ? '%' : ''}
            {entry.name.includes('Equity') || entry.name.includes('P&L') ? '' : ''}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// Equity Chart Component
const EquityChart = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        No portfolio history available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.3}/>
            <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          dataKey="date" 
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickFormatter={(val) => val.slice(5)}
        />
        <YAxis 
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickFormatter={(val) => `$${(val/1000).toFixed(0)}k`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="equity"
          name="Equity"
          stroke={COLORS.primary}
          fill="url(#equityGradient)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

// Drawdown Chart Component
const DrawdownChart = ({ data, maxDrawdown, loading }) => {
  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        No drawdown data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={COLORS.danger} stopOpacity={0.4}/>
            <stop offset="95%" stopColor={COLORS.danger} stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          dataKey="date" 
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickFormatter={(val) => val.slice(5)}
        />
        <YAxis 
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickFormatter={(val) => `-${val}%`}
          domain={[0, Math.max(maxDrawdown * 1.2, 5)]}
          reversed
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="drawdown"
          name="Drawdown %"
          stroke={COLORS.danger}
          fill="url(#drawdownGradient)"
          strokeWidth={2}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

// Win Rate Trend Chart
const WinRateChart = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
      </div>
    );
  }

  if (!data || !data.trend || data.trend.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        No trade history for win rate analysis
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data.trend}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          dataKey="trade_num" 
          tick={{ fill: '#64748b', fontSize: 11 }}
          label={{ value: 'Trade #', position: 'insideBottom', offset: -5, fill: '#64748b' }}
        />
        <YAxis 
          tick={{ fill: '#64748b', fontSize: 11 }}
          domain={[0, 100]}
          tickFormatter={(val) => `${val}%`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Line
          type="monotone"
          dataKey="win_rate"
          name="Rolling Win Rate"
          stroke={COLORS.secondary}
          strokeWidth={2}
          dot={{ fill: COLORS.secondary, strokeWidth: 0, r: 3 }}
        />
        {/* 50% reference line */}
        <Line
          type="monotone"
          dataKey={() => 50}
          stroke={COLORS.warning}
          strokeDasharray="5 5"
          strokeWidth={1}
          dot={false}
          name="50% Baseline"
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

// Strategy Performance Chart
const StrategyChart = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        Run backtests to see strategy performance
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          type="number" 
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickFormatter={(val) => `${val}%`}
        />
        <YAxis 
          type="category" 
          dataKey="strategy" 
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          width={100}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Bar 
          dataKey="avg_return" 
          name="Avg Return %" 
          fill={COLORS.primary}
          radius={[0, 4, 4, 0]}
        />
        <Bar 
          dataKey="avg_win_rate" 
          name="Avg Win Rate %" 
          fill={COLORS.secondary}
          radius={[0, 4, 4, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
};

// Sector Allocation Pie Chart
const SectorChart = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500">
        No positions for sector allocation
      </div>
    );
  }

  const CustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, sector }) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    
    return (
      <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11}>
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="flex items-center">
      <ResponsiveContainer width="60%" height={280}>
        <PieChart>
          <Pie
            data={data}
            dataKey="percentage"
            nameKey="sector"
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={2}
            labelLine={false}
            label={CustomLabel}
          >
            {data.map((entry, index) => (
              <Cell key={entry.sector} fill={SECTOR_COLORS[index % SECTOR_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `${value}%`} />
        </PieChart>
      </ResponsiveContainer>
      <div className="w-[40%] space-y-2">
        {data.slice(0, 6).map((item, index) => (
          <div key={item.sector} className="flex items-center gap-2">
            <div 
              className="w-3 h-3 rounded" 
              style={{ backgroundColor: SECTOR_COLORS[index % SECTOR_COLORS.length] }}
            />
            <span className="text-xs text-slate-400 truncate flex-1">{item.sector}</span>
            <span className="text-xs font-mono text-white">{item.percentage}%</span>
          </div>
        ))}
        {data.length > 6 && (
          <p className="text-xs text-slate-600">+{data.length - 6} more sectors</p>
        )}
      </div>
    </div>
  );
};

// P&L Breakdown Cards
const PnLBreakdown = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => (
          <div key={i} className="h-20 bg-slate-800 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center text-slate-500 py-8">
        No P&L data available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
          <p className="text-xs text-slate-500 mb-1">Realized P&L</p>
          <p className={`text-xl font-mono ${data.realized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {data.realized_pnl >= 0 ? '+' : ''}${data.realized_pnl?.toLocaleString() || '0'}
          </p>
          <p className={`text-xs font-mono ${data.realized_pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {data.realized_pnl_pct >= 0 ? '+' : ''}{data.realized_pnl_pct}%
          </p>
        </div>
        
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
          <p className="text-xs text-slate-500 mb-1">Unrealized P&L</p>
          <p className={`text-xl font-mono ${data.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {data.unrealized_pnl >= 0 ? '+' : ''}${data.unrealized_pnl?.toLocaleString() || '0'}
          </p>
          <p className={`text-xs font-mono ${data.unrealized_pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {data.unrealized_pnl_pct >= 0 ? '+' : ''}{data.unrealized_pnl_pct?.toFixed(2)}%
          </p>
        </div>
        
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
          <p className="text-xs text-slate-500 mb-1">Total P&L</p>
          <p className={`text-xl font-mono ${data.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {data.total_pnl >= 0 ? '+' : ''}${data.total_pnl?.toLocaleString() || '0'}
          </p>
        </div>
        
        <div className="p-4 rounded-lg bg-slate-900 border border-slate-800">
          <p className="text-xs text-slate-500 mb-1">Avg Trade Return</p>
          <p className={`text-xl font-mono ${data.avg_trade_return >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {data.avg_trade_return >= 0 ? '+' : ''}{data.avg_trade_return}%
          </p>
        </div>
      </div>

      {/* Best and Worst Trades */}
      <div className="grid grid-cols-2 gap-4">
        {data.best_trade && (
          <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/20">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-emerald-400">Best Trade</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-mono text-white">{data.best_trade.symbol}</span>
              <span className="font-mono text-emerald-400">+{data.best_trade.pnl_pct}%</span>
            </div>
          </div>
        )}
        {data.worst_trade && (
          <div className="p-3 rounded bg-red-500/10 border border-red-500/20">
            <div className="flex items-center gap-2 mb-1">
              <TrendingDown className="w-4 h-4 text-red-400" />
              <span className="text-xs text-red-400">Worst Trade</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-mono text-white">{data.worst_trade.symbol}</span>
              <span className="font-mono text-red-400">{data.worst_trade.pnl_pct}%</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const Portfolio = () => {
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [period, setPeriod] = useState("1M");
  const [activeTab, setActiveTab] = useState("overview");
  const { token } = useAuth();

  // Live prices for positions - 15s interval
  const { prices: livePrices, loading: pricesLoading } = usePositionsPrices(15000, positions.length > 0);

  const fetchPortfolio = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      const [accountRes, positionsRes] = await Promise.all([
        fetch(`${API}/account`, { headers }),
        fetch(`${API}/positions`, { headers })
      ]);

      if (accountRes.ok) setAccount(await accountRes.json());
      if (positionsRes.ok) setPositions(await positionsRes.json());
    } catch (error) {
      console.error("Portfolio error:", error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  const fetchAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);
    try {
      const response = await fetch(`${API}/portfolio/analytics?period=${period}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        setAnalytics(await response.json());
      }
    } catch (error) {
      console.error("Analytics error:", error);
    } finally {
      setAnalyticsLoading(false);
    }
  }, [token, period]);

  useEffect(() => {
    fetchPortfolio();
  }, [fetchPortfolio]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics, period]);

  const handleRefresh = () => {
    fetchPortfolio();
    fetchAnalytics();
    toast.success("Portfolio refreshed");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="portfolio-loading">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-slate-500 text-sm">Loading portfolio...</p>
        </div>
      </div>
    );
  }

  const equity = parseFloat(account?.equity || 0);
  const cash = parseFloat(account?.cash || 0);
  const buyingPower = parseFloat(account?.buying_power || 0);
  const lastEquity = parseFloat(account?.last_equity || account?.equity || 0);
  const dayPL = lastEquity > 0 ? equity - lastEquity : 0;
  const dayPLPct = lastEquity > 0 ? ((dayPL / lastEquity) * 100) : 0;

  return (
    <div className="space-y-6" data-testid="portfolio-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Wallet className="w-6 h-6 text-emerald-400" />
            <h1 className="font-display text-2xl font-bold text-white">Portfolio Analytics</h1>
          </div>
          <p className="text-sm text-slate-500">Alpaca Paper Trading Account</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-24 bg-slate-900 border-slate-700">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1D">1 Day</SelectItem>
              <SelectItem value="1W">1 Week</SelectItem>
              <SelectItem value="1M">1 Month</SelectItem>
              <SelectItem value="3M">3 Months</SelectItem>
              <SelectItem value="1Y">1 Year</SelectItem>
              <SelectItem value="ALL">All Time</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleRefresh} className="border-slate-700">
            <RefreshCw className="w-4 h-4 mr-2" /> Refresh
          </Button>
        </div>
      </div>

      {/* Account Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="terminal-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-4 h-4 text-emerald-400" />
            <span className="text-xs text-slate-500">Total Equity</span>
          </div>
          <p className="text-2xl font-mono font-bold text-white">${equity.toLocaleString()}</p>
        </Card>
        
        <Card className="terminal-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-slate-500">Day P&L</span>
          </div>
          <p className={`text-2xl font-mono font-bold ${dayPL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {dayPL >= 0 ? '+' : ''}${dayPL.toFixed(2)}
          </p>
          <p className={`text-xs font-mono ${dayPLPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {dayPLPct >= 0 ? '+' : ''}{dayPLPct.toFixed(2)}%
          </p>
        </Card>
        
        <Card className="terminal-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Wallet className="w-4 h-4 text-amber-400" />
            <span className="text-xs text-slate-500">Cash</span>
          </div>
          <p className="text-2xl font-mono font-bold text-white">${cash.toLocaleString()}</p>
        </Card>
        
        <Card className="terminal-card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-purple-400" />
            <span className="text-xs text-slate-500">Buying Power</span>
          </div>
          <p className="text-2xl font-mono font-bold text-white">${buyingPower.toLocaleString()}</p>
        </Card>
      </div>

      {/* Win Rate Summary */}
      {analytics?.win_rate && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-500 mb-1">Win Rate</p>
            <p className={`text-2xl font-mono font-bold ${analytics.win_rate.overall >= 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {analytics.win_rate.overall}%
            </p>
          </Card>
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-500 mb-1">Total Trades</p>
            <p className="text-2xl font-mono font-bold text-white">{analytics.win_rate.total_trades}</p>
          </Card>
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-500 mb-1">Wins / Losses</p>
            <p className="text-2xl font-mono">
              <span className="text-emerald-400">{analytics.win_rate.wins}</span>
              <span className="text-slate-500"> / </span>
              <span className="text-red-400">{analytics.win_rate.losses}</span>
            </p>
          </Card>
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-500 mb-1">Max Drawdown</p>
            <p className="text-2xl font-mono font-bold text-red-400">-{analytics.max_drawdown?.toFixed(2)}%</p>
          </Card>
        </div>
      )}

      {/* Charts Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-slate-900 border border-slate-800">
          <TabsTrigger value="overview" className="data-[state=active]:bg-slate-800">
            <LineChartIcon className="w-4 h-4 mr-1" /> Equity
          </TabsTrigger>
          <TabsTrigger value="drawdown" className="data-[state=active]:bg-slate-800">
            <TrendingDown className="w-4 h-4 mr-1" /> Drawdown
          </TabsTrigger>
          <TabsTrigger value="winrate" className="data-[state=active]:bg-slate-800">
            <Percent className="w-4 h-4 mr-1" /> Win Rate
          </TabsTrigger>
          <TabsTrigger value="strategy" className="data-[state=active]:bg-slate-800">
            <BarChart3 className="w-4 h-4 mr-1" /> Strategy
          </TabsTrigger>
          <TabsTrigger value="sector" className="data-[state=active]:bg-slate-800">
            <PieChartIcon className="w-4 h-4 mr-1" /> Sectors
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <Card className="terminal-card p-6">
            <h3 className="text-sm font-medium text-slate-400 mb-4">Portfolio Equity Over Time</h3>
            <EquityChart data={analytics?.history} loading={analyticsLoading} />
          </Card>
        </TabsContent>

        <TabsContent value="drawdown" className="mt-4">
          <Card className="terminal-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-slate-400">Drawdown Analysis</h3>
              {analytics?.max_drawdown > 0 && (
                <Badge className="bg-red-500/20 text-red-400 border-red-500/30">
                  Max Drawdown: -{analytics.max_drawdown?.toFixed(2)}%
                </Badge>
              )}
            </div>
            <DrawdownChart 
              data={analytics?.drawdowns} 
              maxDrawdown={analytics?.max_drawdown || 0}
              loading={analyticsLoading} 
            />
          </Card>
        </TabsContent>

        <TabsContent value="winrate" className="mt-4">
          <Card className="terminal-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-slate-400">Win Rate Trend (Rolling 20 Trades)</h3>
              {analytics?.win_rate?.overall && (
                <Badge className={`${analytics.win_rate.overall >= 50 ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-amber-500/20 text-amber-400 border-amber-500/30'}`}>
                  Overall: {analytics.win_rate.overall}%
                </Badge>
              )}
            </div>
            <WinRateChart data={analytics?.win_rate} loading={analyticsLoading} />
          </Card>
        </TabsContent>

        <TabsContent value="strategy" className="mt-4">
          <Card className="terminal-card p-6">
            <h3 className="text-sm font-medium text-slate-400 mb-4">Performance by Strategy (from Backtests)</h3>
            <StrategyChart data={analytics?.strategy_performance} loading={analyticsLoading} />
          </Card>
        </TabsContent>

        <TabsContent value="sector" className="mt-4">
          <Card className="terminal-card p-6">
            <h3 className="text-sm font-medium text-slate-400 mb-4">Sector Allocation</h3>
            <SectorChart data={analytics?.sector_allocation} loading={analyticsLoading} />
          </Card>
        </TabsContent>
      </Tabs>

      {/* P&L Breakdown */}
      <Card className="terminal-card p-6">
        <h3 className="text-lg font-display font-semibold text-white mb-4">P&L Breakdown</h3>
        <PnLBreakdown data={analytics?.pnl_breakdown} loading={analyticsLoading} />
      </Card>

      {/* Current Positions */}
      {positions.length > 0 && (
        <Card className="terminal-card overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <h3 className="text-lg font-display font-semibold text-white">
              Current Positions ({positions.length})
            </h3>
            {Object.keys(livePrices).length > 0 && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <LiveIndicator active={true} />
                <span>Live</span>
              </div>
            )}
          </div>
          <div className="divide-y divide-slate-800">
            {positions.map((pos) => {
              const livePrice = livePrices[pos.symbol];
              const currentPrice = livePrice?.price || parseFloat(pos.current_price || 0);
              const entryPrice = parseFloat(pos.avg_entry_price || 0);
              const qty = parseFloat(pos.qty || 0);
              
              // Calculate P&L from live price if available
              const marketValue = livePrice?.price ? livePrice.price * qty : parseFloat(pos.market_value || 0);
              const costBasis = entryPrice * qty;
              const unrealizedPL = marketValue - costBasis;
              const unrealizedPLPct = costBasis > 0 ? ((marketValue / costBasis) - 1) * 100 : 0;
              const isPositive = unrealizedPL >= 0;
              
              return (
                <div key={pos.symbol} className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-white">{pos.symbol}</span>
                        {livePrice && <LiveIndicator active={true} />}
                      </div>
                      <p className="text-xs text-slate-500">
                        {qty.toFixed(2)} shares @ ${entryPrice.toFixed(2)}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-2 justify-end">
                      <p className="font-mono text-white">${marketValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
                      {livePrice && (
                        <span className={`text-xs font-mono ${livePrice.change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {livePrice.change_pct >= 0 ? '↑' : '↓'}{Math.abs(livePrice.change_pct).toFixed(1)}%
                        </span>
                      )}
                    </div>
                    <p className={`text-sm font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                      {isPositive ? '+' : ''}{unrealizedPLPct.toFixed(2)}% (${unrealizedPL.toFixed(2)})
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* No positions message */}
      {positions.length === 0 && (
        <Card className="terminal-card p-8 text-center">
          <AlertTriangle className="w-10 h-10 mx-auto mb-3 text-slate-600" />
          <p className="text-slate-400 mb-1">No open positions</p>
          <p className="text-xs text-slate-600">Your positions will appear here once you start trading</p>
        </Card>
      )}
    </div>
  );
};

export default Portfolio;
