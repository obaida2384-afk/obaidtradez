import { useState, useEffect, useCallback, useMemo } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  PiggyBank, TrendingUp, TrendingDown, Target, AlertTriangle,
  Loader2, DollarSign, Shield, BarChart3, RefreshCw, Plus, Minus,
  ChevronRight, Layers, PieChart, ArrowUpRight, ArrowDownRight,
  Briefcase, Gem, Search as SearchIcon, CheckCircle2, XCircle, Info
} from "lucide-react";
import { toast } from "sonner";

// ---- Helpers ----
const fmt = (n, decimals = 2) => n != null ? Number(n).toFixed(decimals) : "—";
const fmtUSD = (n) => n != null ? `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—";
const pctColor = (v) => v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-slate-400";
const bucketLabel = { core: "Core", quality_growth: "Quality Growth", opportunistic_value: "Opportunistic Value" };
const bucketIcon = { core: Layers, quality_growth: Gem, opportunistic_value: Target };
const bucketAccent = { core: "border-blue-500/40 bg-blue-500/5", quality_growth: "border-emerald-500/40 bg-emerald-500/5", opportunistic_value: "border-amber-500/40 bg-amber-500/5" };
const bucketBadge = { core: "bg-blue-500/20 text-blue-400", quality_growth: "bg-emerald-500/20 text-emerald-400", opportunistic_value: "bg-amber-500/20 text-amber-400" };
const priorityColor = { high: "text-red-400", medium: "text-amber-400", low: "text-slate-400" };
const actionColor = { BUY: "bg-emerald-500/20 text-emerald-400", ADD: "bg-blue-500/20 text-blue-400", TRIM: "bg-amber-500/20 text-amber-400", SELL: "bg-red-500/20 text-red-400", HOLD: "bg-slate-500/20 text-slate-400", REBALANCE: "bg-purple-500/20 text-purple-400" };

// ---- Diversification Ring ----
const DiversificationRing = ({ score }) => {
  const r = 40, stroke = 8, circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 70 ? "#10b981" : score >= 40 ? "#f59e0b" : "#ef4444";
  return (
    <div className="relative w-28 h-28 mx-auto" data-testid="diversification-ring">
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" stroke="#1e293b" strokeWidth={stroke} />
        <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          className="transition-all duration-700" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-white">{score}</span>
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">Diversity</span>
      </div>
    </div>
  );
};

// ---- Bucket Allocation Bar ----
const BucketBar = ({ bucket, info }) => {
  const Icon = bucketIcon[bucket] || Layers;
  const pct = info?.allocation_pct || 0;
  const tMin = info?.target_min || 0;
  const tMax = info?.target_max || 0;
  const status = info?.status || "empty";
  const statusBadge = status === "healthy" ? "bg-emerald-500/20 text-emerald-400"
    : status === "overweight" ? "bg-red-500/20 text-red-400"
    : status === "underweight" ? "bg-amber-500/20 text-amber-400"
    : "bg-slate-700 text-slate-400";
  return (
    <div className={`p-3 rounded-lg border ${bucketAccent[bucket]}`} data-testid={`bucket-bar-${bucket}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-medium text-white">{bucketLabel[bucket]}</span>
        </div>
        <Badge className={`text-[10px] ${statusBadge}`}>{status}</Badge>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden mb-1">
        <div className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(pct, 100)}%`, background: pct > tMax ? "#ef4444" : pct < tMin ? "#f59e0b" : "#10b981" }} />
      </div>
      <div className="flex justify-between text-[10px] text-slate-500">
        <span>{fmt(pct, 1)}%</span>
        <span>Target: {tMin}–{tMax}%</span>
      </div>
    </div>
  );
};

// ---- Position Row ----
const PositionRow = ({ pos, onViewThesis }) => {
  const pnl = pos.pnl_pct || 0;
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-slate-900/50 hover:bg-slate-800/60 transition group cursor-pointer"
      onClick={() => onViewThesis(pos.symbol)} data-testid={`position-row-${pos.symbol}`}>
      <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center text-xs font-bold text-white shrink-0">
        {pos.symbol?.slice(0, 3)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white truncate">{pos.symbol}</span>
          <Badge className={`text-[10px] ${bucketBadge[pos.bucket]}`}>{bucketLabel[pos.bucket]}</Badge>
          {pos.asset_type === "etf" && <Badge className="text-[10px] bg-indigo-500/20 text-indigo-400">ETF</Badge>}
        </div>
        <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-0.5">
          <span>{pos.shares} shares</span>
          <span>Avg {fmtUSD(pos.avg_cost)}</span>
          <span>Stage {pos.stage}/4</span>
        </div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-sm font-medium text-white">{fmtUSD(pos.current_value)}</div>
        <div className={`text-xs font-mono ${pctColor(pnl)}`}>
          {pnl > 0 ? "+" : ""}{fmt(pnl, 1)}%
        </div>
      </div>
      <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition shrink-0" />
    </div>
  );
};

// ---- Recommendation Card ----
const RecommendationCard = ({ rec, onAction }) => {
  const ActionBadge = actionColor[rec.action] || actionColor.HOLD;
  return (
    <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition"
      data-testid={`rec-card-${rec.symbol}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Badge className={`text-xs font-semibold ${ActionBadge}`}>{rec.action}</Badge>
          <span className="text-sm font-medium text-white">{rec.symbol}</span>
          {rec.name && <span className="text-xs text-slate-500 hidden sm:inline">{rec.name}</span>}
        </div>
        <span className={`text-[10px] font-medium uppercase ${priorityColor[rec.priority]}`}>{rec.priority}</span>
      </div>
      <p className="text-xs text-slate-400 leading-relaxed mb-2">{rec.reason}</p>
      <div className="flex items-center gap-2">
        {rec.stage_info && <Badge className="text-[10px] bg-slate-800 text-slate-300">{rec.stage_info}</Badge>}
        {rec.bucket && <Badge className={`text-[10px] ${bucketBadge[rec.bucket]}`}>{bucketLabel[rec.bucket]}</Badge>}
        {rec.action === "BUY" && !rec.symbol.startsWith("BUCKET:") && (
          <Button size="sm" variant="ghost" className="ml-auto h-6 text-[10px] text-emerald-400 hover:bg-emerald-500/10"
            onClick={() => onAction(rec)} data-testid={`rec-buy-${rec.symbol}`}>
            <Plus className="w-3 h-3 mr-1" />Stage In
          </Button>
        )}
      </div>
    </div>
  );
};

// ---- Thesis Modal ----
const ThesisPanel = ({ thesis, onClose }) => {
  if (!thesis) return null;
  const healthColor = thesis.health_status === "strong" ? "text-emerald-400"
    : thesis.health_status === "weak" ? "text-red-400" : "text-amber-400";
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="bg-slate-900 border-slate-700 max-w-md w-full p-6" onClick={e => e.stopPropagation()}
        data-testid="thesis-panel">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">{thesis.symbol} — Thesis Health</h3>
            <span className="text-xs text-slate-500">{thesis.name} · {bucketLabel[thesis.bucket]}</span>
          </div>
          <div className="text-right">
            <span className={`text-2xl font-bold ${healthColor}`}>{thesis.health_score}</span>
            <span className="text-xs text-slate-500 block">/100</span>
          </div>
        </div>
        <div className="space-y-3">
          <div>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Original Thesis</span>
            <p className="text-sm text-slate-300 mt-1">{thesis.original_thesis}</p>
          </div>
          <div>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider">Status</span>
            <Badge className={`text-xs ml-2 ${healthColor === "text-emerald-400" ? "bg-emerald-500/20 text-emerald-400"
              : healthColor === "text-red-400" ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"}`}>
              {thesis.health_status}
            </Badge>
          </div>
          {thesis.signals?.length > 0 && (
            <div>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">Signals</span>
              <div className="mt-1 space-y-1">
                {thesis.signals.map((s, i) => (
                  <div key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                    <Info className="w-3 h-3 mt-0.5 text-slate-600 shrink-0" />
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-500">Held {thesis.days_held} days · Stage {thesis.stage}/4</span>
            <Badge className={`text-xs ${actionColor[thesis.recommendation]}`}>{thesis.recommendation}</Badge>
          </div>
        </div>
        <Button variant="ghost" className="w-full mt-4 text-slate-400" onClick={onClose} data-testid="thesis-close-btn">Close</Button>
      </Card>
    </div>
  );
};

// ---- Stage Buy Modal ----
const StageBuyModal = ({ symbol, name, bucket, onClose, onSubmit }) => {
  const [shares, setShares] = useState("");
  const [price, setPrice] = useState("");
  const [thesis, setThesis] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!shares || !price) { toast.error("Enter shares and price"); return; }
    setSubmitting(true);
    try {
      await onSubmit({ symbol, bucket, shares: parseFloat(shares), price: parseFloat(price), thesis, name });
      onClose();
    } catch {
      toast.error("Failed to execute stage buy");
    }
    setSubmitting(false);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="bg-slate-900 border-slate-700 max-w-sm w-full p-6" onClick={e => e.stopPropagation()}
        data-testid="stage-buy-modal">
        <h3 className="text-lg font-semibold text-white mb-1">Stage Buy — {symbol}</h3>
        <p className="text-xs text-slate-500 mb-4">{name} · {bucketLabel[bucket]}</p>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-slate-500">Shares</label>
            <Input type="number" placeholder="e.g. 5" value={shares} onChange={e => setShares(e.target.value)}
              className="bg-slate-800 border-slate-700 text-white mt-1" data-testid="stage-buy-shares" />
          </div>
          <div>
            <label className="text-xs text-slate-500">Price ($)</label>
            <Input type="number" placeholder="e.g. 180.00" value={price} onChange={e => setPrice(e.target.value)}
              className="bg-slate-800 border-slate-700 text-white mt-1" data-testid="stage-buy-price" />
          </div>
          <div>
            <label className="text-xs text-slate-500">Investment Thesis (optional)</label>
            <Input placeholder="Why this stock?" value={thesis} onChange={e => setThesis(e.target.value)}
              className="bg-slate-800 border-slate-700 text-white mt-1" data-testid="stage-buy-thesis" />
          </div>
          <div className="flex gap-2 pt-2">
            <Button variant="ghost" className="flex-1 text-slate-400" onClick={onClose}>Cancel</Button>
            <Button className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" onClick={handleSubmit}
              disabled={submitting} data-testid="stage-buy-submit">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Plus className="w-4 h-4 mr-1" />Stage Buy</>}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

// ===================== MAIN PAGE =====================
export default function LongTermInvest() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [portfolio, setPortfolio] = useState(null);
  const [recommendations, setRecs] = useState([]);
  const [universe, setUniverse] = useState(null);
  const [thesis, setThesis] = useState(null);
  const [stageBuy, setStageBuy] = useState(null);
  const [tab, setTab] = useState("portfolio");
  const [search, setSearch] = useState("");

  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const fetchPortfolio = useCallback(async () => {
    try {
      const res = await fetch(`${API}/lt-invest/portfolio`, { headers });
      const data = await res.json();
      setPortfolio(data);
    } catch { toast.error("Failed to load portfolio"); }
  }, [headers]);

  const fetchRecs = useCallback(async () => {
    try {
      const res = await fetch(`${API}/lt-invest/recommendations`, { headers });
      const data = await res.json();
      setRecs(data.recommendations || []);
    } catch { toast.error("Failed to load recommendations"); }
  }, [headers]);

  const fetchUniverse = useCallback(async () => {
    try {
      const res = await fetch(`${API}/lt-invest/universe`, { headers });
      const data = await res.json();
      setUniverse(data);
    } catch { toast.error("Failed to load universe"); }
  }, [headers]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchPortfolio(), fetchRecs(), fetchUniverse()]);
    setLoading(false);
  }, [fetchPortfolio, fetchRecs, fetchUniverse]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleViewThesis = async (symbol) => {
    try {
      const res = await fetch(`${API}/lt-invest/thesis/${symbol}`, { headers });
      const data = await res.json();
      setThesis(data);
    } catch { toast.error("Failed to load thesis"); }
  };

  const handleStageBuy = async (data) => {
    const res = await fetch(`${API}/lt-invest/stage-buy`, {
      method: "POST", headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed");
    toast.success(`Staged into ${data.symbol} (${data.shares} shares)`);
    loadAll();
  };

  const summary = portfolio?.summary || {};
  const positions = portfolio?.positions || [];
  const buckets = portfolio?.bucket_breakdown || {};

  if (loading) return (
    <div className="flex items-center justify-center h-96" data-testid="lt-loading">
      <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
    </div>
  );

  return (
    <div className="space-y-6 p-4 md:p-6 max-w-6xl mx-auto" data-testid="lt-invest-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-blue-500" />
            Long-Term Portfolio
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">ETF core + Quality Growth + Opportunistic Value</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadAll} className="border-slate-700 text-slate-300 hover:bg-slate-800"
          data-testid="lt-refresh-btn">
          <RefreshCw className="w-4 h-4 mr-1" />Refresh
        </Button>
      </div>

      {/* Summary Strip */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3" data-testid="lt-summary-strip">
        <Card className="bg-slate-900/60 border-slate-800 p-3">
          <span className="text-[10px] text-slate-500 uppercase">Total Value</span>
          <div className="text-lg font-bold text-white mt-1">{fmtUSD(summary.total_value)}</div>
        </Card>
        <Card className="bg-slate-900/60 border-slate-800 p-3">
          <span className="text-[10px] text-slate-500 uppercase">P&L</span>
          <div className={`text-lg font-bold mt-1 ${pctColor(summary.total_pnl_pct)}`}>
            {summary.total_pnl_pct > 0 ? "+" : ""}{fmt(summary.total_pnl_pct, 1)}%
          </div>
          <span className={`text-[10px] ${pctColor(summary.total_pnl_usd)}`}>{fmtUSD(summary.total_pnl_usd)}</span>
        </Card>
        <Card className="bg-slate-900/60 border-slate-800 p-3">
          <span className="text-[10px] text-slate-500 uppercase">Positions</span>
          <div className="text-lg font-bold text-white mt-1">{summary.position_count || 0}</div>
        </Card>
        <Card className="bg-slate-900/60 border-slate-800 p-3 flex flex-col items-center">
          <DiversificationRing score={summary.diversification_score || 0} />
        </Card>
        <Card className="bg-slate-900/60 border-slate-800 p-3">
          <span className="text-[10px] text-slate-500 uppercase">Rebalance</span>
          <div className="mt-1">
            {summary.needs_rebalance
              ? <Badge className="bg-amber-500/20 text-amber-400 text-xs"><AlertTriangle className="w-3 h-3 mr-1" />Needed</Badge>
              : <Badge className="bg-emerald-500/20 text-emerald-400 text-xs"><CheckCircle2 className="w-3 h-3 mr-1" />OK</Badge>}
          </div>
          {summary.rebalance_reasons?.length > 0 && (
            <span className="text-[10px] text-slate-500 mt-1 block">{summary.rebalance_reasons.length} issues</span>
          )}
        </Card>
      </div>

      {/* Bucket Allocation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="lt-bucket-bars">
        {Object.keys(bucketLabel).map(b => (
          <BucketBar key={b} bucket={b} info={buckets[b]} />
        ))}
      </div>

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab} data-testid="lt-tabs">
        <TabsList className="bg-slate-900 border border-slate-800">
          <TabsTrigger value="portfolio" data-testid="lt-tab-portfolio">
            <Briefcase className="w-4 h-4 mr-1" />Portfolio
          </TabsTrigger>
          <TabsTrigger value="recommendations" data-testid="lt-tab-recs">
            <Target className="w-4 h-4 mr-1" />Recommendations
            {recommendations.length > 0 && (
              <Badge className="ml-1 text-[10px] bg-blue-500/20 text-blue-400">{recommendations.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="universe" data-testid="lt-tab-universe">
            <PieChart className="w-4 h-4 mr-1" />Universe
          </TabsTrigger>
        </TabsList>

        {/* Portfolio Tab */}
        <TabsContent value="portfolio" className="mt-4">
          {positions.length === 0 ? (
            <Card className="bg-slate-900/40 border-slate-800 p-8 text-center">
              <Briefcase className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No long-term positions yet.</p>
              <p className="text-xs text-slate-500 mt-1">Go to Recommendations or Universe to add your first position.</p>
            </Card>
          ) : (
            <div className="space-y-2" data-testid="lt-positions-list">
              {positions.map(pos => (
                <PositionRow key={pos.symbol} pos={pos} onViewThesis={handleViewThesis} />
              ))}
            </div>
          )}
        </TabsContent>

        {/* Recommendations Tab */}
        <TabsContent value="recommendations" className="mt-4">
          {recommendations.length === 0 ? (
            <Card className="bg-slate-900/40 border-slate-800 p-8 text-center">
              <CheckCircle2 className="w-10 h-10 text-emerald-600 mx-auto mb-3" />
              <p className="text-sm text-slate-400">No recommendations at this time.</p>
            </Card>
          ) : (
            <div className="space-y-2" data-testid="lt-recs-list">
              {recommendations.map((rec, i) => (
                <RecommendationCard key={`${rec.symbol}-${i}`} rec={rec}
                  onAction={(r) => setStageBuy({ symbol: r.symbol, name: r.name, bucket: r.bucket })} />
              ))}
            </div>
          )}
        </TabsContent>

        {/* Universe Tab */}
        <TabsContent value="universe" className="mt-4">
          <div className="mb-3">
            <div className="relative">
              <SearchIcon className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <Input placeholder="Search universe..." value={search} onChange={e => setSearch(e.target.value)}
                className="bg-slate-800 border-slate-700 text-white pl-9" data-testid="lt-universe-search" />
            </div>
          </div>
          {universe && Object.entries({
            core: { label: "Core ETFs", data: universe.core },
            quality_growth: { label: "Quality Growth", data: universe.quality_growth },
            opportunistic_value: { label: "Opportunistic Value", data: universe.opportunistic_value },
          }).map(([bucket, { label, data }]) => {
            const filtered = Object.entries(data || {}).filter(([sym, info]) =>
              !search || sym.toLowerCase().includes(search.toLowerCase()) ||
              (info.name || "").toLowerCase().includes(search.toLowerCase())
            );
            if (filtered.length === 0) return null;
            return (
              <div key={bucket} className="mb-4" data-testid={`lt-universe-${bucket}`}>
                <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                  {(() => { const Icon = bucketIcon[bucket]; return <Icon className="w-4 h-4 text-slate-400" />; })()}
                  {label}
                  <Badge className="text-[10px] bg-slate-800 text-slate-400">{filtered.length}</Badge>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {filtered.map(([sym, info]) => {
                    const held = positions.some(p => p.symbol === sym);
                    return (
                      <div key={sym}
                        className={`p-2.5 rounded-lg border transition cursor-pointer hover:border-slate-600 ${held ? "border-emerald-500/30 bg-emerald-500/5" : "border-slate-800 bg-slate-900/40"}`}
                        onClick={() => !held && setStageBuy({ symbol: sym, name: info.name, bucket })}
                        data-testid={`universe-item-${sym}`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="text-sm font-medium text-white">{sym}</span>
                            <span className="text-xs text-slate-500 ml-2">{info.name}</span>
                          </div>
                          {held ? (
                            <Badge className="text-[10px] bg-emerald-500/20 text-emerald-400">Held</Badge>
                          ) : (
                            <Plus className="w-4 h-4 text-slate-600 hover:text-emerald-400 transition" />
                          )}
                        </div>
                        {info.sector && <span className="text-[10px] text-slate-600 mt-0.5 block">{info.sector}</span>}
                        {info.category && <span className="text-[10px] text-slate-600 mt-0.5 block">{info.category}</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </TabsContent>
      </Tabs>

      {/* Modals */}
      {thesis && <ThesisPanel thesis={thesis} onClose={() => setThesis(null)} />}
      {stageBuy && <StageBuyModal {...stageBuy} onClose={() => setStageBuy(null)} onSubmit={handleStageBuy} />}
    </div>
  );
}
