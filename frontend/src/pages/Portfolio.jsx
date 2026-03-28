import { useState, useEffect } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  Wallet,
  TrendingUp,
  TrendingDown,
  PieChart,
  DollarSign,
  Loader2,
  RefreshCw,
  Percent
} from "lucide-react";
import { Button } from "@/components/ui/button";

const Portfolio = () => {
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuth();

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const fetchPortfolio = async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      const [accountRes, positionsRes, ordersRes] = await Promise.all([
        fetch(`${API}/account`, { headers }),
        fetch(`${API}/positions`, { headers }),
        fetch(`${API}/orders?status=all`, { headers })
      ]);

      if (accountRes.ok) setAccount(await accountRes.json());
      if (positionsRes.ok) setPositions(await positionsRes.json());
      if (ordersRes.ok) setOrders(await ordersRes.json());
    } catch (error) {
      console.error("Portfolio error:", error);
    } finally {
      setLoading(false);
    }
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
  const dayPL = parseFloat(account?.equity) - parseFloat(account?.last_equity || account?.equity || 0);
  const dayPLPct = account?.last_equity ? ((dayPL / parseFloat(account.last_equity)) * 100) : 0;

  return (
    <div className="space-y-6" data-testid="portfolio-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Wallet className="w-6 h-6 text-emerald-400" />
            <h1 className="font-display text-2xl font-bold text-white">Portfolio</h1>
          </div>
          <p className="text-sm text-slate-500">Alpaca Paper Trading Account</p>
        </div>
        <Button variant="outline" onClick={fetchPortfolio} className="border-slate-700">
          <RefreshCw className="w-4 h-4 mr-2" /> Refresh
        </Button>
      </div>

      {/* Account Summary */}
      {account && (
        <div className="grid md:grid-cols-4 gap-4">
          <Card className="terminal-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-emerald-500/20 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Portfolio Value</p>
                <p className="font-mono text-xl text-white">${equity.toLocaleString()}</p>
              </div>
            </div>
          </Card>
          
          <Card className="terminal-card p-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-md ${dayPL >= 0 ? 'bg-emerald-500/20' : 'bg-red-500/20'} flex items-center justify-center`}>
                {dayPL >= 0 ? (
                  <TrendingUp className="w-5 h-5 text-emerald-400" />
                ) : (
                  <TrendingDown className="w-5 h-5 text-red-400" />
                )}
              </div>
              <div>
                <p className="text-xs text-slate-500">Today's P&L</p>
                <p className={`font-mono text-xl ${dayPL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {dayPL >= 0 ? '+' : ''}${dayPL.toFixed(2)}
                </p>
              </div>
            </div>
          </Card>
          
          <Card className="terminal-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-blue-500/20 flex items-center justify-center">
                <Wallet className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Buying Power</p>
                <p className="font-mono text-xl text-white">${buyingPower.toLocaleString()}</p>
              </div>
            </div>
          </Card>
          
          <Card className="terminal-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-md bg-slate-700 flex items-center justify-center">
                <PieChart className="w-5 h-5 text-slate-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500">Cash</p>
                <p className="font-mono text-xl text-white">${cash.toLocaleString()}</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Positions */}
      <Card className="terminal-card overflow-hidden">
        <div className="p-4 border-b border-slate-800">
          <h2 className="font-display font-semibold text-white">Open Positions ({positions.length})</h2>
        </div>
        
        {positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-900">
                <tr>
                  <th className="text-left p-3 text-slate-500 font-medium">Symbol</th>
                  <th className="text-right p-3 text-slate-500 font-medium">Qty</th>
                  <th className="text-right p-3 text-slate-500 font-medium">Avg Cost</th>
                  <th className="text-right p-3 text-slate-500 font-medium">Current</th>
                  <th className="text-right p-3 text-slate-500 font-medium">Market Value</th>
                  <th className="text-right p-3 text-slate-500 font-medium">P&L</th>
                  <th className="text-right p-3 text-slate-500 font-medium">% Change</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => {
                  const unrealizedPL = parseFloat(pos.unrealized_pl || 0);
                  const unrealizedPLPct = parseFloat(pos.unrealized_plpc || 0) * 100;
                  
                  return (
                    <tr key={pos.symbol} className="border-b border-slate-800/50 hover:bg-slate-900/50">
                      <td className="p-3 font-mono font-medium text-white">{pos.symbol}</td>
                      <td className="p-3 text-right font-mono text-white">{pos.qty}</td>
                      <td className="p-3 text-right font-mono text-slate-400">${parseFloat(pos.avg_entry_price).toFixed(2)}</td>
                      <td className="p-3 text-right font-mono text-white">${parseFloat(pos.current_price).toFixed(2)}</td>
                      <td className="p-3 text-right font-mono text-white">${parseFloat(pos.market_value).toLocaleString()}</td>
                      <td className={`p-3 text-right font-mono ${unrealizedPL >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {unrealizedPL >= 0 ? '+' : ''}${unrealizedPL.toFixed(2)}
                      </td>
                      <td className={`p-3 text-right font-mono ${unrealizedPLPct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {unrealizedPLPct >= 0 ? '+' : ''}{unrealizedPLPct.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500">
            No open positions
          </div>
        )}
      </Card>

      {/* Recent Orders */}
      <Card className="terminal-card overflow-hidden">
        <div className="p-4 border-b border-slate-800">
          <h2 className="font-display font-semibold text-white">Recent Orders</h2>
        </div>
        
        {orders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-900">
                <tr>
                  <th className="text-left p-3 text-slate-500 font-medium">Symbol</th>
                  <th className="text-left p-3 text-slate-500 font-medium">Side</th>
                  <th className="text-left p-3 text-slate-500 font-medium">Type</th>
                  <th className="text-right p-3 text-slate-500 font-medium">Qty</th>
                  <th className="text-right p-3 text-slate-500 font-medium">Price</th>
                  <th className="text-left p-3 text-slate-500 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {orders.slice(0, 10).map((order) => (
                  <tr key={order.id} className="border-b border-slate-800/50 hover:bg-slate-900/50">
                    <td className="p-3 font-mono font-medium text-white">{order.symbol}</td>
                    <td className="p-3">
                      <Badge className={order.side === 'buy' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}>
                        {order.side?.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="p-3 text-slate-400">{order.type}</td>
                    <td className="p-3 text-right font-mono text-white">{order.qty}</td>
                    <td className="p-3 text-right font-mono text-slate-400">
                      ${parseFloat(order.filled_avg_price || order.limit_price || 0).toFixed(2)}
                    </td>
                    <td className="p-3">
                      <Badge variant="outline" className="text-xs border-slate-700">
                        {order.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500">
            No recent orders
          </div>
        )}
      </Card>
    </div>
  );
};

export default Portfolio;
