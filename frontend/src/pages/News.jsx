import { useState, useEffect, useCallback } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  Newspaper, TrendingUp, TrendingDown, Minus, Search, Loader2, RefreshCw,
  ExternalLink, Clock, Zap, AlertTriangle, Brain, BarChart2, Shield, ArrowUpRight
} from "lucide-react";

// ===================== SENTIMENT GAUGE =====================
const SentimentGauge = ({ score, label }) => {
  const normalized = Math.max(-100, Math.min(100, score || 0));
  const pct = ((normalized + 100) / 200) * 100;
  const color = normalized > 20 ? "text-emerald-400" : normalized < -20 ? "text-red-400" : "text-amber-400";
  const bg = normalized > 20 ? "bg-emerald-500" : normalized < -20 ? "bg-red-500" : "bg-amber-500";

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1">
        <div className="flex justify-between text-[10px] text-slate-500 mb-1">
          <span>Bearish</span><span>Neutral</span><span>Bullish</span>
        </div>
        <div className="h-2 bg-slate-800 rounded-full relative overflow-hidden">
          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-slate-600" />
          <div
            className={`absolute top-0 bottom-0 rounded-full ${bg} transition-all`}
            style={{ left: `${Math.min(pct, 50)}%`, width: `${Math.abs(pct - 50)}%` }}
          />
        </div>
      </div>
      <div className="text-right">
        <p className={`text-xl font-mono font-bold ${color}`}>{normalized > 0 ? '+' : ''}{normalized}</p>
        <p className={`text-[10px] ${color}`}>{label}</p>
      </div>
    </div>
  );
};

// ===================== CATALYST BADGE =====================
const CatalystBadge = ({ type, strength }) => {
  const labels = {
    earnings_surprise: "Earnings",
    merger_acquisition: "M&A",
    guidance_change: "Guidance",
    regulatory: "Regulatory",
    product_launch: "Product",
    analyst_rating: "Analyst",
    insider_activity: "Insider",
    none: null
  };
  if (!type || type === "none") return null;
  return (
    <Badge variant="outline" className="text-[10px] bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse">
      <Zap className="w-3 h-3 mr-0.5" /> {labels[type] || type} Catalyst ({strength})
    </Badge>
  );
};

// ===================== ARTICLE CARD =====================
const ArticleCard = ({ article }) => (
  <div className="p-3 rounded bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-colors">
    <div className="flex items-start justify-between gap-3">
      <div className="flex-1 min-w-0">
        <a href={article.url} target="_blank" rel="noopener noreferrer"
          className="text-sm text-white hover:text-blue-400 transition-colors line-clamp-2 block">
          {article.title}
          <ExternalLink className="w-3 h-3 inline ml-1 opacity-50" />
        </a>
        {article.why_it_matters && (
          <p className="text-xs text-blue-300/80 mt-1 flex items-start gap-1">
            <Brain className="w-3 h-3 shrink-0 mt-0.5 text-blue-400" />
            {article.why_it_matters}
          </p>
        )}
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-[10px] text-slate-500">{article.source}</span>
          {article.published && (
            <span className="text-[10px] text-slate-600 flex items-center gap-0.5">
              <Clock className="w-2.5 h-2.5" />
              {new Date(article.published).toLocaleDateString()}
            </span>
          )}
          {article.relevance && (
            <Badge variant="outline" className="text-[9px] border-slate-700 text-slate-500 py-0">
              Rel: {article.relevance}
            </Badge>
          )}
          {article.sentiment && (
            <span className={`text-[10px] ${
              article.sentiment === 'positive' ? 'text-emerald-400' :
              article.sentiment === 'negative' ? 'text-red-400' : 'text-slate-400'
            }`}>
              {article.sentiment}
            </span>
          )}
        </div>
      </div>
    </div>
  </div>
);

// ===================== STOCK NEWS PANEL =====================
const StockNewsPanel = ({ data }) => {
  if (!data) return null;
  return (
    <div className="space-y-4" data-testid="stock-news-panel">
      {/* Sentiment + Catalyst Header */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-2">AI Sentiment Score</p>
          <SentimentGauge score={data.sentiment_score} label={data.sentiment_label} />
        </Card>
        <Card className="terminal-card p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-slate-500">News Intelligence</p>
            {data.ai_powered && <Badge variant="outline" className="text-[9px] border-blue-500/30 text-blue-400"><Brain className="w-2.5 h-2.5 mr-0.5" /> AI Powered</Badge>}
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div><p className="text-slate-500">Articles</p><p className="text-white font-mono">{data.unique_articles || 0} unique</p></div>
            <div><p className="text-slate-500">Sources</p><p className="text-white font-mono">{Object.keys(data.sources || {}).length}</p></div>
            <div><p className="text-slate-500">Momentum</p><p className={`capitalize ${data.news_momentum === 'accelerating' ? 'text-amber-400' : 'text-slate-300'}`}>{data.news_momentum}</p></div>
            <div>
              <p className="text-slate-500">Risk Flag</p>
              <p className={data.risk_flag ? 'text-red-400' : 'text-emerald-400'}>{data.risk_flag ? 'Yes' : 'Clear'}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Catalyst */}
      {data.catalyst_detected && (
        <Card className="terminal-card p-4 border-amber-500/20 bg-amber-500/5">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" />
            <div>
              <p className="text-sm text-amber-400 font-medium">Catalyst Detected</p>
              <p className="text-xs text-slate-400">{data.catalyst_type?.replace(/_/g, " ")} — Strength: {data.catalyst_strength}/100</p>
            </div>
          </div>
        </Card>
      )}

      {/* AI Summary */}
      {data.one_line_summary && (
        <Card className="terminal-card p-4 border-blue-500/10">
          <p className="text-xs text-blue-400 mb-1 flex items-center gap-1"><Brain className="w-3 h-3" /> AI Summary</p>
          <p className="text-sm text-slate-300">{data.one_line_summary}</p>
        </Card>
      )}

      {/* Top Articles */}
      <div className="space-y-2">
        <p className="text-xs text-slate-400">Top Articles</p>
        {(data.top_articles || []).map((a, i) => (
          <ArticleCard key={i} article={a} />
        ))}
      </div>
    </div>
  );
};

// ===================== MAIN NEWS PAGE =====================
const News = () => {
  const [searchSymbol, setSearchSymbol] = useState("");
  const [stockNews, setStockNews] = useState(null);
  const [breaking, setBreaking] = useState([]);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState("search");
  const { token } = useAuth();

  const headers = { Authorization: `Bearer ${token}` };

  const fetchBreaking = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/news/breaking`, { headers });
      if (resp.ok) setBreaking(await resp.json());
    } catch (e) { console.error(e); }
  }, [token]);

  const fetchOverview = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/news/overview`, { headers });
      if (resp.ok) setOverview(await resp.json());
    } catch (e) { console.error(e); }
  }, [token]);

  useEffect(() => {
    fetchBreaking();
    fetchOverview();
  }, [fetchBreaking, fetchOverview]);

  const analyzeStock = async (symbol) => {
    if (!symbol) return;
    setLoading(true);
    setStockNews(null);
    try {
      const resp = await fetch(`${API}/news/analyze/${symbol.toUpperCase()}`, { headers });
      if (resp.ok) {
        const data = await resp.json();
        setStockNews(data);
        setActiveTab("search");
      } else {
        toast.error("Failed to analyze news");
      }
    } catch (e) {
      toast.error("Analysis error");
    }
    setLoading(false);
  };

  const refreshAll = async () => {
    setRefreshing(true);
    try {
      const resp = await fetch(`${API}/news/refresh`, { method: "POST", headers });
      if (resp.ok) {
        toast.success("Refreshing news for top stocks...");
        setTimeout(() => { fetchBreaking(); fetchOverview(); }, 10000);
      }
    } catch (e) { toast.error("Refresh failed"); }
    setRefreshing(false);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto" data-testid="news-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Newspaper className="w-6 h-6 text-blue-400" />
            <h1 className="font-display text-2xl font-bold text-white">News & Sentiment</h1>
            {overview && (
              <Badge variant="outline" className="text-xs border-slate-700 text-slate-400">
                {overview.total_analyzed} stocks analyzed
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500">AI-powered multi-source news analysis with catalyst detection</p>
        </div>

        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && analyzeStock(searchSymbol)}
              placeholder="Analyze stock..."
              className="pl-10 w-40 md:w-48 bg-slate-900 border-slate-700"
              data-testid="news-search-input"
            />
          </div>
          <Button onClick={() => analyzeStock(searchSymbol)} disabled={loading || !searchSymbol.trim()} className="bg-blue-600 hover:bg-blue-500" data-testid="news-analyze-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Brain className="w-4 h-4 mr-1" /> Analyze</>}
          </Button>
          <Button variant="outline" onClick={refreshAll} disabled={refreshing} className="border-slate-700" data-testid="news-refresh-btn">
            <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? "Scanning..." : "Refresh All"}
          </Button>
        </div>
      </div>

      {/* Quick Stock Buttons */}
      <div className="flex gap-2 flex-wrap">
        {["NVDA", "AAPL", "TSLA", "MSFT", "AMZN", "META", "GOOGL", "AMD"].map(s => (
          <Button key={s} variant="outline" size="sm" onClick={() => { setSearchSymbol(s); analyzeStock(s); }}
            className="border-slate-700 text-xs h-7" data-testid={`quick-${s}`}>
            {s}
          </Button>
        ))}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full justify-start bg-slate-900 border border-slate-800 p-1 h-auto flex-wrap">
          <TabsTrigger value="search" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <Brain className="w-4 h-4 mr-1" /> AI Analysis
          </TabsTrigger>
          <TabsTrigger value="breaking" className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400">
            <Zap className="w-4 h-4 mr-1" /> Catalysts ({breaking.length})
          </TabsTrigger>
          <TabsTrigger value="overview" className="data-[state=active]:bg-slate-500/20 data-[state=active]:text-white">
            <BarChart2 className="w-4 h-4 mr-1" /> Overview
          </TabsTrigger>
        </TabsList>

        {/* AI ANALYSIS TAB */}
        <TabsContent value="search" className="space-y-4">
          {loading && (
            <Card className="terminal-card p-8 text-center">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
              <p className="text-sm text-slate-400">Fetching from 4 sources & running AI analysis...</p>
            </Card>
          )}
          {!loading && stockNews && (
            <div>
              <h2 className="text-lg text-white font-bold mb-3">{stockNews.symbol} News Intelligence</h2>
              <StockNewsPanel data={stockNews} />
            </div>
          )}
          {!loading && !stockNews && (
            <Card className="terminal-card p-12 text-center">
              <Brain className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500">Search a stock symbol to get AI-powered news analysis</p>
              <p className="text-xs text-slate-600 mt-1">Aggregates from FMP, Finnhub, Alpha Vantage & Marketaux</p>
            </Card>
          )}
        </TabsContent>

        {/* CATALYSTS TAB */}
        <TabsContent value="breaking" className="space-y-3">
          <h2 className="text-sm text-amber-400 flex items-center gap-1"><Zap className="w-4 h-4" /> Active Catalysts</h2>
          {breaking.length > 0 ? breaking.map((item, i) => (
            <Card key={i} className="terminal-card p-4 border-amber-500/10">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-white font-bold">{item.symbol}</span>
                  <CatalystBadge type={item.catalyst_type} strength={item.catalyst_strength} />
                  <Badge variant="outline" className={`text-[10px] ${
                    item.sentiment_label === 'Bullish' ? 'border-emerald-500/30 text-emerald-400' :
                    item.sentiment_label === 'Bearish' ? 'border-red-500/30 text-red-400' :
                    'border-slate-700 text-slate-400'
                  }`}>
                    {item.sentiment_label} ({item.sentiment_score > 0 ? '+' : ''}{item.sentiment_score})
                  </Badge>
                </div>
              </div>
              <p className="text-xs text-slate-300">{item.one_line_summary}</p>
              {item.top_articles?.map((a, j) => (
                <a key={j} href={a.url} target="_blank" rel="noopener noreferrer"
                  className="text-[11px] text-blue-400/70 hover:text-blue-400 block mt-1">
                  {a.title?.slice(0, 80)}... <ExternalLink className="w-2.5 h-2.5 inline" />
                </a>
              ))}
            </Card>
          )) : (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">
              No catalysts detected yet. Click "Refresh All" to scan top stocks.
            </Card>
          )}
        </TabsContent>

        {/* OVERVIEW TAB */}
        <TabsContent value="overview" className="space-y-4">
          {overview ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card className="terminal-card p-4 text-center">
                  <p className="text-2xl font-mono text-white">{overview.total_analyzed}</p>
                  <p className="text-[10px] text-slate-500">Stocks Analyzed</p>
                </Card>
                <Card className="terminal-card p-4 text-center">
                  <p className="text-2xl font-mono text-amber-400">{overview.with_catalysts}</p>
                  <p className="text-[10px] text-slate-500">With Catalysts</p>
                </Card>
                <Card className="terminal-card p-4 text-center">
                  <p className="text-2xl font-mono text-emerald-400">{overview.distribution?.Bullish?.count || 0}</p>
                  <p className="text-[10px] text-slate-500">Bullish</p>
                </Card>
                <Card className="terminal-card p-4 text-center">
                  <p className="text-2xl font-mono text-red-400">{overview.distribution?.Bearish?.count || 0}</p>
                  <p className="text-[10px] text-slate-500">Bearish</p>
                </Card>
              </div>
              <Card className="terminal-card p-4">
                <p className="text-xs text-slate-400 mb-3">Sentiment Distribution</p>
                {Object.entries(overview.distribution || {}).map(([label, data]) => (
                  <div key={label} className="flex items-center gap-3 mb-2">
                    <span className={`text-xs w-16 ${
                      label === 'Bullish' ? 'text-emerald-400' : label === 'Bearish' ? 'text-red-400' : 'text-slate-400'
                    }`}>{label}</span>
                    <div className="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${
                        label === 'Bullish' ? 'bg-emerald-500' : label === 'Bearish' ? 'bg-red-500' : 'bg-slate-500'
                      }`} style={{ width: `${Math.min(100, (data.count / Math.max(overview.total_analyzed, 1)) * 100)}%` }} />
                    </div>
                    <span className="text-xs text-slate-500 w-16 text-right">{data.count} (avg {data.avg_score > 0 ? '+' : ''}{data.avg_score})</span>
                  </div>
                ))}
              </Card>
            </>
          ) : (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              Loading overview...
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default News;
