import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import {
  Newspaper, Search, RefreshCw, TrendingUp, TrendingDown,
  AlertTriangle, ExternalLink, Clock, Zap, Filter, Target,
  Activity, BarChart2, Eye, Loader2, Radio, Flame, Shield
} from "lucide-react";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

const CategoryBadge = ({ category }) => {
  const cfg = {
    HOT: { cls: "bg-red-500/20 text-red-400 border-red-500/30", icon: Flame },
    BULLISH: { cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", icon: TrendingUp },
    BEARISH: { cls: "bg-red-500/20 text-red-400 border-red-500/30", icon: TrendingDown },
    WATCHLIST: { cls: "bg-amber-500/20 text-amber-400 border-amber-500/30", icon: Eye },
    IGNORE: { cls: "bg-slate-500/20 text-slate-500 border-slate-700", icon: Shield },
  };
  const c = cfg[category] || cfg.IGNORE;
  const Icon = c.icon;
  return (
    <Badge variant="outline" className={`text-[10px] font-bold ${c.cls}`} data-testid={`category-${category}`}>
      <Icon className="w-3 h-3 mr-1" /> {category}
    </Badge>
  );
};

const TradeImpactBadge = ({ impact }) => {
  const cls = {
    HIGH: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    MEDIUM: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    LOW: "bg-slate-500/20 text-slate-500 border-slate-700",
  };
  return <Badge variant="outline" className={`text-[10px] ${cls[impact] || cls.LOW}`}>{impact || "LOW"} Impact</Badge>;
};

const VelocityIndicator = ({ velocity, score }) => {
  const cls = {
    high: "text-red-400",
    medium: "text-amber-400",
    low: "text-slate-500",
    none: "text-slate-600",
  };
  return (
    <div className="flex items-center gap-1">
      <Radio className={`w-3 h-3 ${cls[velocity] || cls.low} ${velocity === 'high' ? 'animate-pulse' : ''}`} />
      <span className={`text-[10px] ${cls[velocity] || cls.low}`}>{velocity?.toUpperCase() || "LOW"}</span>
      {score > 0 && <span className="text-[10px] text-slate-600">({score})</span>}
    </div>
  );
};

const CatalystBar = ({ score }) => {
  const width = Math.min(100, Math.max(0, score || 0));
  const color = width >= 80 ? 'bg-emerald-500' : width >= 60 ? 'bg-amber-500' : width >= 40 ? 'bg-slate-500' : 'bg-slate-700';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-slate-800 rounded overflow-hidden">
        <div className={`h-full ${color} rounded transition-all`} style={{ width: `${width}%` }} />
      </div>
      <span className={`text-xs font-mono ${width >= 80 ? 'text-emerald-400' : width >= 60 ? 'text-amber-400' : 'text-slate-500'}`}>{score || 0}</span>
    </div>
  );
};

const News = () => {
  const [symbol, setSymbol] = useState("");
  const [analysis, setAnalysis] = useState(null);
  const [breaking, setBreaking] = useState([]);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("analysis");
  const { token } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };

  const fetchBreaking = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/news/breaking`, { headers });
      if (resp.ok) setBreaking(await resp.json());
    } catch (e) {}
  }, [token]);

  const fetchOverview = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/news/overview`, { headers });
      if (resp.ok) setOverview(await resp.json());
    } catch (e) {}
  }, [token]);

  useEffect(() => {
    fetchBreaking();
    fetchOverview();
  }, [fetchBreaking, fetchOverview]);

  const analyzeStock = async (sym) => {
    const s = (sym || symbol).toUpperCase().trim();
    if (!s) return;
    setSymbol(s);
    setLoading(true);
    setActiveTab("analysis");
    try {
      const resp = await fetch(`${API}/news/analyze/${s}`, { headers });
      if (resp.ok) {
        setAnalysis(await resp.json());
      } else {
        toast.error("Analysis failed");
      }
    } catch (e) { toast.error("Error"); }
    setLoading(false);
  };

  const refreshAll = async () => {
    try {
      const resp = await fetch(`${API}/news/refresh`, { method: "POST", headers });
      if (resp.ok) {
        const d = await resp.json();
        toast.success(d.message);
        setTimeout(() => { fetchBreaking(); fetchOverview(); }, 10000);
      }
    } catch (e) { toast.error("Refresh failed"); }
  };

  const quickStocks = ["NVDA", "AAPL", "TSLA", "MSFT", "AMZN", "META", "GOOGL", "AMD"];

  return (
    <div className="space-y-6 max-w-6xl mx-auto" data-testid="news-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Newspaper className="w-6 h-6 text-blue-400" />
            <h1 className="font-display text-2xl font-bold text-white">News & Catalyst Engine</h1>
            {overview && (
              <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-400">
                {overview.total_analyzed} analyzed
              </Badge>
            )}
            {overview?.hot_stocks > 0 && (
              <Badge variant="outline" className="text-[10px] border-red-500/30 text-red-400">
                <Flame className="w-3 h-3 mr-1" /> {overview.hot_stocks} HOT
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500">Multi-source ingestion + AI catalyst scoring + trade categories</p>
        </div>
      </div>

      {/* Search */}
      <Card className="terminal-card p-4">
        <div className="flex gap-2">
          <Input placeholder="Enter stock symbol (e.g., NVDA)" value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && analyzeStock()}
            className="bg-slate-900 border-slate-700 text-white" data-testid="news-search-input" />
          <Button onClick={() => analyzeStock()} disabled={loading || !symbol} className="bg-blue-600 hover:bg-blue-500" data-testid="news-analyze-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            <span className="ml-1">Analyze</span>
          </Button>
          <Button variant="outline" onClick={refreshAll} className="border-slate-700" data-testid="news-refresh-btn">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex flex-wrap gap-1.5 mt-3">
          {quickStocks.map((s) => (
            <Button key={s} size="sm" variant="outline" onClick={() => analyzeStock(s)}
              className="border-slate-700 text-xs h-7 px-2" data-testid={`quick-${s}`}>{s}</Button>
          ))}
        </div>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => {
        setActiveTab(v);
        if (v === "breaking") fetchBreaking();
        if (v === "overview") fetchOverview();
      }}>
        <TabsList className="bg-slate-900 border border-slate-800 p-1">
          <TabsTrigger value="analysis" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
            <Target className="w-4 h-4 mr-1" /> AI Analysis
          </TabsTrigger>
          <TabsTrigger value="breaking" className="data-[state=active]:bg-red-500/20 data-[state=active]:text-red-400">
            <Zap className="w-4 h-4 mr-1" /> Catalysts ({breaking.length})
          </TabsTrigger>
          <TabsTrigger value="overview" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-400">
            <BarChart2 className="w-4 h-4 mr-1" /> Overview
          </TabsTrigger>
        </TabsList>

        {/* AI ANALYSIS TAB */}
        <TabsContent value="analysis" className="space-y-4">
          {!analysis && !loading && (
            <Card className="terminal-card p-8 text-center">
              <Search className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500">Search a stock to see AI-powered catalyst analysis</p>
            </Card>
          )}
          {loading && (
            <Card className="terminal-card p-8 text-center">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
              <p className="text-slate-500">Analyzing {symbol}...</p>
            </Card>
          )}
          {analysis && !loading && (
            <>
              {/* Summary Header */}
              <Card className="terminal-card p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl text-white font-bold">{analysis.symbol}</h2>
                    <CategoryBadge category={analysis.category} />
                    <TradeImpactBadge impact={analysis.trade_impact} />
                    {analysis.is_tradeable && (
                      <Badge variant="outline" className="text-[10px] bg-emerald-500/10 border-emerald-500/30 text-emerald-400 animate-pulse">TRADE CANDIDATE</Badge>
                    )}
                  </div>
                  <VelocityIndicator velocity={analysis.news_velocity} score={analysis.news_velocity_score} />
                </div>
                {/* Trade description (actionable) */}
                <p className={`text-sm font-medium mb-3 ${
                  analysis.category === "HOT" ? 'text-emerald-400' :
                  analysis.category === "BULLISH" ? 'text-blue-400' :
                  analysis.category === "BEARISH" ? 'text-red-400' :
                  'text-slate-400'
                }`} data-testid="trade-description">
                  {analysis.trade_description || analysis.one_line_summary}
                </p>
                {/* Metrics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div>
                    <p className="text-[10px] text-slate-500">Catalyst Score</p>
                    <CatalystBar score={analysis.catalyst_score} />
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500">Sentiment</p>
                    <p className={`text-sm font-mono ${analysis.sentiment_score > 20 ? 'text-emerald-400' : analysis.sentiment_score < -20 ? 'text-red-400' : 'text-slate-400'}`}>
                      {analysis.sentiment_score > 0 ? '+' : ''}{analysis.sentiment_score} ({analysis.sentiment_label})
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500">Catalyst Type</p>
                    <p className="text-xs text-white capitalize">{(analysis.catalyst_type || "none").replace(/_/g, " ")}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500">Articles</p>
                    <p className="text-xs text-white font-mono">{analysis.total_raw_articles} raw / {analysis.high_signal_articles || analysis.unique_articles} signal</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500">News Velocity</p>
                    <VelocityIndicator velocity={analysis.news_velocity} score={analysis.news_velocity_score} />
                  </div>
                </div>
              </Card>

              {/* Filter Pipeline Stats */}
              {analysis.filter_stats && (
                <Card className="terminal-card p-3">
                  <p className="text-[10px] text-slate-500 mb-2">Filter Pipeline</p>
                  <div className="grid grid-cols-5 gap-2 text-xs">
                    <div className="text-center"><p className="text-slate-400 font-mono">{analysis.filter_stats.raw_ingested}</p><p className="text-[10px] text-slate-600">Ingested</p></div>
                    <div className="text-center"><p className="text-slate-400 font-mono">{analysis.filter_stats.after_relevance}</p><p className="text-[10px] text-slate-600">Relevant</p></div>
                    <div className="text-center"><p className="text-slate-400 font-mono">{analysis.filter_stats.after_dedup}</p><p className="text-[10px] text-slate-600">Unique</p></div>
                    <div className="text-center"><p className="text-emerald-400 font-mono">{analysis.filter_stats.high_signal_count}</p><p className="text-[10px] text-slate-600">High Signal</p></div>
                    <div className="text-center"><p className="text-red-400 font-mono">{analysis.filter_stats.filler_removed}</p><p className="text-[10px] text-slate-600">Filler</p></div>
                  </div>
                </Card>
              )}

              {/* Catalyst Explainability */}
              {analysis.catalyst_detected && (
                <Card className="terminal-card p-4 border-l-2 border-l-emerald-500/50">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <span className="text-xs text-white font-medium">Catalyst Analysis</span>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 w-24">Type:</span>
                      <span className="text-white capitalize">{(analysis.catalyst_type || "").replace(/_/g, " ")}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 w-24">Strength:</span>
                      <CatalystBar score={analysis.catalyst_strength || analysis.catalyst_score} />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 w-24">Label:</span>
                      <span className={`font-medium ${
                        analysis.catalyst_label?.includes("BULLISH") ? 'text-emerald-400' :
                        analysis.catalyst_label?.includes("BEARISH") ? 'text-red-400' :
                        'text-slate-400'
                      }`}>{analysis.catalyst_label}</span>
                    </div>
                    {analysis.trade_reasoning && (
                      <div className="flex items-start gap-2 mt-1 pt-1 border-t border-slate-800">
                        <span className="text-slate-500 w-24 shrink-0">Trade Logic:</span>
                        <span className="text-slate-300">{analysis.trade_reasoning}</span>
                      </div>
                    )}
                  </div>
                </Card>
              )}

              {/* Velocity Details */}
              {analysis.velocity_details && analysis.velocity_details.velocity !== "none" && (
                <Card className="terminal-card p-3">
                  <p className="text-[10px] text-slate-500 mb-2">Velocity Details</p>
                  <div className="grid grid-cols-5 gap-2 text-xs">
                    <div className="text-center"><p className={`font-mono ${analysis.velocity_details.velocity === 'high' ? 'text-red-400' : 'text-slate-400'}`}>{analysis.velocity_details.articles_24h}</p><p className="text-[10px] text-slate-600">24h Articles</p></div>
                    <div className="text-center"><p className={`font-mono ${analysis.velocity_details.articles_4h >= 3 ? 'text-red-400' : 'text-slate-400'}`}>{analysis.velocity_details.articles_4h}</p><p className="text-[10px] text-slate-600">4h Articles</p></div>
                    <div className="text-center"><p className="text-slate-400 font-mono">{analysis.velocity_details.sources}</p><p className="text-[10px] text-slate-600">Sources</p></div>
                    <div className="text-center"><p className="text-white capitalize">{analysis.velocity_details.trend}</p><p className="text-[10px] text-slate-600">Trend</p></div>
                    <div className="text-center"><p className={`font-mono ${analysis.velocity_details.velocity_score >= 60 ? 'text-red-400' : 'text-slate-400'}`}>{analysis.velocity_details.velocity_score}/100</p><p className="text-[10px] text-slate-600">Score</p></div>
                  </div>
                </Card>
              )}

              {/* Top Articles */}
              {analysis.top_articles?.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs text-slate-400">Key Articles ({analysis.top_articles.length})</h3>
                  {analysis.top_articles.map((a, i) => (
                    <Card key={i} className="terminal-card p-3" data-testid={`article-${i}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className={`text-[10px] ${
                              a.sentiment?.includes("positive") || a.sentiment === "strong_positive" ? 'border-emerald-500/30 text-emerald-400' :
                              a.sentiment?.includes("negative") || a.sentiment === "strong_negative" ? 'border-red-500/30 text-red-400' :
                              'border-slate-700 text-slate-400'
                            }`}>{a.sentiment?.replace("_", " ")}</Badge>
                            <span className="text-[10px] text-slate-500">{a.source}</span>
                            {a.source_credibility && (
                              <span className="text-[10px] text-slate-600">cred:{a.source_credibility?.toFixed(1)}</span>
                            )}
                          </div>
                          <a href={a.url} target="_blank" rel="noopener noreferrer"
                            className="text-sm text-white hover:text-blue-400 transition-colors leading-tight">
                            {a.title || "Untitled"} <ExternalLink className="w-3 h-3 inline" />
                          </a>
                          {a.why_it_matters && (
                            <p className="text-xs text-blue-400 mt-1">{a.why_it_matters}</p>
                          )}
                          {a.catalyst_contribution && (
                            <p className="text-xs text-amber-400 mt-0.5">Catalyst: {a.catalyst_contribution}</p>
                          )}
                        </div>
                        <span className="text-[10px] text-slate-600 shrink-0">{a.relevance}/100</span>
                      </div>
                    </Card>
                  ))}
                </div>
              )}

              {/* AI Badge */}
              {analysis.ai_powered && (
                <p className="text-[10px] text-slate-600 text-center">
                  Powered by GPT-5.2 | {analysis.article_count} articles processed | Analyzed: {new Date(analysis.analyzed_at).toLocaleString()}
                </p>
              )}
            </>
          )}
        </TabsContent>

        {/* BREAKING/CATALYSTS TAB */}
        <TabsContent value="breaking" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm text-red-400 flex items-center gap-1"><Zap className="w-4 h-4" /> Active Catalysts</h2>
            <Button variant="outline" size="sm" onClick={fetchBreaking} className="border-slate-700"><RefreshCw className="w-3 h-3 mr-1" /> Refresh</Button>
          </div>
          {breaking.length > 0 ? breaking.map((item, i) => (
            <Card key={i} className="terminal-card p-3 cursor-pointer hover:border-slate-700 transition-colors"
              onClick={() => analyzeStock(item.symbol)} data-testid={`breaking-${item.symbol}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-white font-bold">{item.symbol}</span>
                  <CategoryBadge category={item.category} />
                  <TradeImpactBadge impact={item.trade_impact} />
                  {item.is_tradeable && (
                    <Badge variant="outline" className="text-[10px] bg-emerald-500/10 border-emerald-500/30 text-emerald-400">TRADEABLE</Badge>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <VelocityIndicator velocity={item.news_velocity} score={item.news_velocity_score} />
                  <div className="text-right">
                    <p className={`text-sm font-mono ${item.sentiment_score > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {item.sentiment_score > 0 ? '+' : ''}{item.sentiment_score}
                    </p>
                    <p className="text-[10px] text-slate-500">{item.catalyst_label?.replace("_", " ")}</p>
                  </div>
                  <p className="text-xs text-white font-mono w-8 text-right">{item.catalyst_score}</p>
                </div>
              </div>
              <p className="text-xs text-slate-400 mt-1">{item.trade_description || item.one_line_summary}</p>
            </Card>
          )) : (
            <Card className="terminal-card p-8 text-center text-slate-500 text-sm">
              No catalysts detected. Run Refresh All to scan top stocks.
            </Card>
          )}
        </TabsContent>

        {/* OVERVIEW TAB */}
        <TabsContent value="overview" className="space-y-4">
          {overview ? (
            <>
              <Card className="terminal-card p-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div><p className="text-2xl font-mono text-white">{overview.total_analyzed}</p><p className="text-[10px] text-slate-500">Total Analyzed</p></div>
                  <div><p className="text-2xl font-mono text-emerald-400">{overview.tradeable_signals || 0}</p><p className="text-[10px] text-slate-500">Tradeable</p></div>
                  <div><p className="text-2xl font-mono text-red-400">{overview.hot_stocks || 0}</p><p className="text-[10px] text-slate-500">HOT</p></div>
                </div>
              </Card>
              {/* Sentiment Distribution */}
              {overview.sentiment_distribution && Object.keys(overview.sentiment_distribution).length > 0 && (
                <Card className="terminal-card p-4">
                  <h3 className="text-xs text-slate-400 mb-3">Sentiment Distribution</h3>
                  <div className="space-y-2">
                    {Object.entries(overview.sentiment_distribution).map(([label, data]) => (
                      <div key={label} className="flex items-center gap-3">
                        <span className={`text-xs w-28 ${
                          label.includes("Bullish") ? 'text-emerald-400' : label.includes("Bearish") ? 'text-red-400' : 'text-slate-400'
                        }`}>{label}</span>
                        <div className="flex-1 h-3 bg-slate-800 rounded overflow-hidden">
                          <div className={`h-full rounded ${
                            label.includes("Bullish") ? 'bg-emerald-500/40' : label.includes("Bearish") ? 'bg-red-500/40' : 'bg-slate-600'
                          }`} style={{ width: `${Math.min(100, (data.count / (overview.total_analyzed || 1)) * 100)}%` }} />
                        </div>
                        <span className="text-xs text-slate-400 font-mono w-8">{data.count}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
              {/* Category Distribution */}
              {overview.category_distribution && Object.keys(overview.category_distribution).length > 0 && (
                <Card className="terminal-card p-4">
                  <h3 className="text-xs text-slate-400 mb-3">Category Distribution</h3>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    {Object.entries(overview.category_distribution).map(([cat, data]) => (
                      <div key={cat} className="text-center p-2 rounded bg-slate-900/50 border border-slate-800">
                        <CategoryBadge category={cat} />
                        <p className="text-lg font-mono text-white mt-1">{data.count}</p>
                        <p className="text-[10px] text-slate-500">avg score: {data.avg_catalyst}</p>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </>
          ) : (
            <Card className="terminal-card p-8 text-center"><Loader2 className="w-6 h-6 text-blue-500 animate-spin mx-auto" /></Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default News;
