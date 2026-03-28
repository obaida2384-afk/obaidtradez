import { useState, useEffect } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Newspaper,
  TrendingUp, 
  TrendingDown,
  Minus,
  Search,
  Loader2,
  RefreshCw,
  ExternalLink,
  Clock,
  Filter
} from "lucide-react";

// Sentiment Badge
const SentimentBadge = ({ sentiment, score }) => {
  const config = {
    "Positive": { class: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", icon: TrendingUp },
    "Negative": { class: "bg-red-500/20 text-red-400 border-red-500/30", icon: TrendingDown },
    "Neutral": { class: "bg-slate-500/20 text-slate-400 border-slate-500/30", icon: Minus }
  }[sentiment] || { class: "bg-slate-500/20 text-slate-400 border-slate-500/30", icon: Minus };
  
  const Icon = config.icon;
  
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded border flex items-center gap-1 ${config.class}`}>
      <Icon className="w-3 h-3" />
      {sentiment}
      {score && <span className="opacity-70">({(score * 100).toFixed(0)}%)</span>}
    </span>
  );
};

// News Card
const NewsCard = ({ news }) => {
  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Card className="terminal-card p-4 hover:border-slate-600 transition-all" data-testid={`news-card`}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex-1">
          <a 
            href={news.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="font-medium text-white hover:text-blue-400 transition-colors line-clamp-2"
          >
            {news.title}
          </a>
        </div>
        <SentimentBadge sentiment={news.sentiment} score={news.sentiment_score} />
      </div>
      
      {news.summary && (
        <p className="text-sm text-slate-400 mb-3 line-clamp-2">{news.summary}</p>
      )}
      
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>{news.source}</span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDate(news.published)}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {news.symbols?.slice(0, 3).map((symbol) => (
            <Badge key={symbol} variant="outline" className="text-xs border-slate-700 text-slate-400">
              {symbol}
            </Badge>
          ))}
          <a 
            href={news.url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-slate-500 hover:text-white"
          >
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>
    </Card>
  );
};

const News = () => {
  const [marketNews, setMarketNews] = useState([]);
  const [symbolNews, setSymbolNews] = useState([]);
  const [searchSymbol, setSearchSymbol] = useState("");
  const [searchedSymbol, setSearchedSymbol] = useState("");
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [activeTab, setActiveTab] = useState("market");
  const [sentimentFilter, setSentimentFilter] = useState("all");
  const { token } = useAuth();

  useEffect(() => {
    fetchMarketNews();
  }, []);

  const fetchMarketNews = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API}/news/market`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setMarketNews(await response.json());
      }
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const searchNews = async (symbol) => {
    if (!symbol.trim()) return;
    setSearching(true);
    setSymbolNews([]);
    
    try {
      const response = await fetch(`${API}/news/${symbol.toUpperCase()}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setSymbolNews(await response.json());
        setSearchedSymbol(symbol.toUpperCase());
        setActiveTab("symbol");
      }
    } catch (error) {
      console.error("Search error:", error);
    } finally {
      setSearching(false);
    }
  };

  const filterNews = (news) => {
    if (sentimentFilter === "all") return news;
    return news.filter(n => n.sentiment.toLowerCase() === sentimentFilter);
  };

  const getSentimentStats = (news) => {
    const total = news.length;
    const positive = news.filter(n => n.sentiment === "Positive").length;
    const negative = news.filter(n => n.sentiment === "Negative").length;
    const neutral = news.filter(n => n.sentiment === "Neutral").length;
    
    return {
      total,
      positive,
      negative,
      neutral,
      positivePct: total > 0 ? ((positive / total) * 100).toFixed(0) : 0,
      negativePct: total > 0 ? ((negative / total) * 100).toFixed(0) : 0
    };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]" data-testid="news-loading">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin mx-auto mb-4 text-blue-500" />
          <p className="text-slate-500 text-sm">Fetching market news...</p>
        </div>
      </div>
    );
  }

  const currentNews = activeTab === "market" ? marketNews : symbolNews;
  const stats = getSentimentStats(currentNews);

  return (
    <div className="space-y-6" data-testid="news-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Newspaper className="w-6 h-6 text-blue-400" />
            <h1 className="font-display text-2xl font-bold text-white">News & Sentiment</h1>
          </div>
          <p className="text-sm text-slate-500">Real-time market news with sentiment analysis</p>
        </div>
        
        {/* Search */}
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && searchNews(searchSymbol)}
              placeholder="Symbol news..."
              className="pl-10 w-40 md:w-48 bg-slate-900 border-slate-700"
              data-testid="news-search-input"
            />
          </div>
          <Button 
            onClick={() => searchNews(searchSymbol)}
            disabled={searching || !searchSymbol.trim()}
            className="bg-blue-600 hover:bg-blue-500"
            data-testid="news-search-btn"
          >
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
          </Button>
          <Button 
            variant="outline"
            onClick={fetchMarketNews}
            className="border-slate-700"
            data-testid="refresh-news-btn"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Sentiment Overview */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Total Articles</p>
          <p className="font-mono text-2xl text-white">{stats.total}</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Positive</p>
          <p className="font-mono text-2xl text-emerald-400">{stats.positive}</p>
          <p className="text-xs text-emerald-400/70">{stats.positivePct}%</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Negative</p>
          <p className="font-mono text-2xl text-red-400">{stats.negative}</p>
          <p className="text-xs text-red-400/70">{stats.negativePct}%</p>
        </Card>
        <Card className="terminal-card p-4">
          <p className="text-xs text-slate-500 mb-1">Neutral</p>
          <p className="font-mono text-2xl text-slate-400">{stats.neutral}</p>
        </Card>
      </div>

      {/* Tabs & Filter */}
      <div className="flex items-center justify-between">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-900 border border-slate-800">
            <TabsTrigger value="market" className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400">
              Market News
            </TabsTrigger>
            {searchedSymbol && (
              <TabsTrigger value="symbol" className="data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-400">
                {searchedSymbol} News ({symbolNews.length})
              </TabsTrigger>
            )}
          </TabsList>
        </Tabs>
        
        {/* Sentiment Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={sentimentFilter}
            onChange={(e) => setSentimentFilter(e.target.value)}
            className="text-sm bg-slate-900 border border-slate-700 rounded px-2 py-1 text-white"
            data-testid="sentiment-filter"
          >
            <option value="all">All Sentiment</option>
            <option value="positive">Positive Only</option>
            <option value="negative">Negative Only</option>
            <option value="neutral">Neutral Only</option>
          </select>
        </div>
      </div>

      {/* News List */}
      <div className="space-y-3">
        {filterNews(currentNews).map((news, i) => (
          <NewsCard key={i} news={news} />
        ))}
        {filterNews(currentNews).length === 0 && (
          <Card className="terminal-card p-8 text-center">
            <p className="text-slate-500">No news articles found</p>
          </Card>
        )}
      </div>
    </div>
  );
};

export default News;
