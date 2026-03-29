import { useState, useEffect, useCallback } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useWatchlistPrices, LiveIndicator } from "../hooks/useLivePrices";
import { 
  Star,
  Plus,
  Trash2,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Loader2,
  Search,
  X,
  AlertTriangle,
  ExternalLink,
  Edit2,
  Check,
  Minus
} from "lucide-react";
import { toast } from "sonner";

// Category badge colors
const getCategoryStyle = (category) => {
  switch (category?.toLowerCase()) {
    case "hot":
      return "bg-red-500/20 text-red-400 border-red-500/30";
    case "bullish":
      return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
    case "undervalued":
      return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    case "watch":
      return "bg-amber-500/20 text-amber-400 border-amber-500/30";
    case "bearish":
      return "bg-rose-500/20 text-rose-400 border-rose-500/30";
    default:
      return "bg-slate-500/20 text-slate-400 border-slate-500/30";
  }
};

const getSignalStyle = (signal) => {
  switch (signal?.toLowerCase()) {
    case "strong buy":
      return "text-emerald-400";
    case "buy":
      return "text-green-400";
    case "hold":
      return "text-amber-400";
    case "sell":
      return "text-rose-400";
    case "strong sell":
      return "text-red-400";
    default:
      return "text-slate-400";
  }
};

// Watchlist item card
const WatchlistCard = ({ item, onRemove, onUpdateNote, livePrice }) => {
  const [editingNote, setEditingNote] = useState(false);
  const [note, setNote] = useState(item.note || "");
  const [flash, setFlash] = useState(null);
  const prevPriceRef = useState(null);
  
  // Use live price if available, otherwise fall back to item price
  const displayPrice = livePrice?.price || item.price || 0;
  const displayChange = livePrice?.change_pct ?? (typeof item.change_pct === 'number' ? item.change_pct : parseFloat(item.change_pct) || 0);
  const isPositive = displayChange >= 0;

  // Flash effect on price change
  useEffect(() => {
    if (prevPriceRef.current !== null && prevPriceRef.current !== displayPrice && displayPrice > 0) {
      setFlash(displayPrice > prevPriceRef.current ? "up" : "down");
      const timeout = setTimeout(() => setFlash(null), 500);
      return () => clearTimeout(timeout);
    }
    prevPriceRef.current = displayPrice;
  }, [displayPrice]);

  const handleSaveNote = () => {
    onUpdateNote(item.symbol, note);
    setEditingNote(false);
  };

  const flashClass = flash === "up" 
    ? "bg-emerald-500/20" 
    : flash === "down" 
      ? "bg-red-500/20" 
      : "";

  return (
    <Card 
      className="terminal-card p-4 hover:border-slate-600 transition-all"
      data-testid={`watchlist-card-${item.symbol}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xl font-bold text-white">{item.symbol}</span>
              {livePrice && <LiveIndicator active={true} />}
              {item.score !== null && (
                <div className={`px-2 py-0.5 rounded text-sm font-bold ${
                  item.score >= 70 ? 'bg-emerald-500/20 text-emerald-400' :
                  item.score >= 50 ? 'bg-amber-500/20 text-amber-400' :
                  'bg-red-500/20 text-red-400'
                }`}>
                  {item.score}
                </div>
              )}
            </div>
            <Badge variant="outline" className={getCategoryStyle(item.category)}>
              {item.category}
            </Badge>
          </div>
          
          <p className="text-sm text-slate-400 mb-3">{item.name}</p>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className={`transition-all duration-300 rounded p-1 -m-1 ${flashClass}`}>
              <p className="text-xs text-slate-500">Price</p>
              <p className="font-mono text-lg text-white">${displayPrice?.toFixed(2) || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Change</p>
              <div className={`flex items-center gap-1 ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                <span className="font-mono text-lg">{isPositive ? '+' : ''}{displayChange.toFixed(2)}%</span>
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500">Signal</p>
              <p className={`font-medium ${getSignalStyle(item.signal)}`}>{item.signal}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Sector</p>
              <p className="text-sm text-slate-300">{item.sector}</p>
            </div>
          </div>

          {item.upside !== null && item.upside !== undefined && (
            <div className="mt-3 flex items-center gap-4">
              <div>
                <span className="text-xs text-slate-500">Upside: </span>
                <span className={`font-mono ${String(item.upside).startsWith('-') ? 'text-red-400' : 'text-emerald-400'}`}>
                  {item.upside}
                </span>
              </div>
              {item.confidence !== null && (
                <div>
                  <span className="text-xs text-slate-500">Confidence: </span>
                  <span className="font-mono text-slate-300">{(item.confidence * 100).toFixed(0)}%</span>
                </div>
              )}
            </div>
          )}

          {/* Note section */}
          <div className="mt-3">
            {editingNote ? (
              <div className="flex items-center gap-2">
                <Input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add a note..."
                  className="flex-1 h-8 text-sm bg-slate-900 border-slate-700"
                  autoFocus
                />
                <Button size="sm" variant="ghost" onClick={handleSaveNote}>
                  <Check className="w-4 h-4 text-emerald-400" />
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditingNote(false)}>
                  <X className="w-4 h-4 text-slate-400" />
                </Button>
              </div>
            ) : (
              <div 
                className="flex items-center gap-2 cursor-pointer group"
                onClick={() => setEditingNote(true)}
              >
                {item.note ? (
                  <p className="text-xs text-slate-500 italic">"{item.note}"</p>
                ) : (
                  <p className="text-xs text-slate-600 group-hover:text-slate-400">+ Add note</p>
                )}
                <Edit2 className="w-3 h-3 text-slate-600 opacity-0 group-hover:opacity-100" />
              </div>
            )}
          </div>
        </div>

        <Button 
          variant="ghost" 
          size="sm"
          onClick={() => onRemove(item.symbol)}
          className="text-slate-400 hover:text-red-400 shrink-0"
          data-testid={`remove-${item.symbol}`}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between">
        <span className="text-xs text-slate-600">
          Added {new Date(item.added_at).toLocaleDateString()}
        </span>
        <Badge variant="outline" className="text-xs border-slate-700 text-slate-500">
          via {item.source}
        </Badge>
      </div>
    </Card>
  );
};

// Quick add component
const QuickAdd = ({ onAdd, loading }) => {
  const [symbol, setSymbol] = useState("");

  const handleAdd = () => {
    if (symbol.trim()) {
      onAdd(symbol.trim().toUpperCase());
      setSymbol("");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleAdd();
    }
  };

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1 max-w-xs">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <Input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          onKeyPress={handleKeyPress}
          placeholder="Add symbol (e.g. AAPL)"
          className="pl-9 bg-slate-900 border-slate-700 font-mono"
          data-testid="quick-add-input"
        />
      </div>
      <Button 
        onClick={handleAdd} 
        disabled={loading || !symbol.trim()}
        className="bg-amber-600 hover:bg-amber-500"
        data-testid="quick-add-btn"
      >
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4 mr-1" />}
        Add
      </Button>
    </div>
  );
};

const Watchlist = () => {
  const { token } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [adding, setAdding] = useState(false);
  const [filter, setFilter] = useState("");

  const fetchWatchlist = useCallback(async () => {
    try {
      const response = await fetch(`${API}/watchlist`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setItems(await response.json());
      }
    } catch (error) {
      console.error("Error fetching watchlist:", error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  const handleAdd = async (symbol) => {
    setAdding(true);
    try {
      const response = await fetch(`${API}/watchlist`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ symbol, source: "manual" })
      });
      
      const result = await response.json();
      if (result.success) {
        toast.success(result.message);
        fetchWatchlist(); // Refresh to get full data
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      console.error("Add error:", error);
      toast.error("Failed to add to watchlist");
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (symbol) => {
    try {
      const response = await fetch(`${API}/watchlist/${symbol}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const result = await response.json();
      if (result.success) {
        setItems(items.filter(i => i.symbol !== symbol));
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      console.error("Remove error:", error);
      toast.error("Failed to remove from watchlist");
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const response = await fetch(`${API}/watchlist/refresh`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        await fetchWatchlist();
        toast.success("Watchlist refreshed");
      }
    } catch (error) {
      console.error("Refresh error:", error);
      toast.error("Failed to refresh watchlist");
    } finally {
      setRefreshing(false);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm("Remove all stocks from your watchlist?")) return;
    
    try {
      const response = await fetch(`${API}/watchlist/all`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const result = await response.json();
      if (result.success) {
        setItems([]);
        toast.success(`Removed ${result.removed} stocks from watchlist`);
      }
    } catch (error) {
      console.error("Clear error:", error);
      toast.error("Failed to clear watchlist");
    }
  };

  const handleUpdateNote = async (symbol, note) => {
    try {
      await fetch(`${API}/watchlist/${symbol}/note?note=${encodeURIComponent(note)}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setItems(items.map(i => i.symbol === symbol ? { ...i, note } : i));
    } catch (error) {
      console.error("Note update error:", error);
    }
  };

  // Filter items
  const filteredItems = items.filter(item => {
    if (!filter) return true;
    const f = filter.toLowerCase();
    return item.symbol.toLowerCase().includes(f) ||
           item.name?.toLowerCase().includes(f) ||
           item.category?.toLowerCase().includes(f) ||
           item.sector?.toLowerCase().includes(f);
  });

  // Stats
  const stats = {
    total: items.length,
    bullish: items.filter(i => ['hot', 'bullish', 'undervalued'].includes(i.category?.toLowerCase())).length,
    bearish: items.filter(i => i.category?.toLowerCase() === 'bearish').length,
    avgScore: items.length > 0 
      ? Math.round(items.filter(i => i.score).reduce((acc, i) => acc + (i.score || 0), 0) / items.filter(i => i.score).length)
      : 0
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-slate-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="watchlist-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Star className="w-6 h-6 text-amber-400" />
            <h1 className="font-display text-2xl font-bold text-white">Watchlist</h1>
            {items.length > 0 && (
              <Badge variant="outline" className="border-slate-700">
                {items.length} stock{items.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-500">Your personal stock watchlist</p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button 
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing || items.length === 0}
            className="border-slate-700"
          >
            <RefreshCw className={`w-4 h-4 mr-1 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          {items.length > 0 && (
            <Button 
              variant="outline"
              size="sm"
              onClick={handleClearAll}
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              Clear All
            </Button>
          )}
        </div>
      </div>

      {/* Quick Add & Filter */}
      <Card className="terminal-card p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <QuickAdd onAdd={handleAdd} loading={adding} />
          
          {items.length > 0 && (
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Filter watchlist..."
                className="pl-9 bg-slate-900 border-slate-700"
              />
              {filter && (
                <button 
                  onClick={() => setFilter("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                >
                  <X className="w-4 h-4 text-slate-500 hover:text-white" />
                </button>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Stats */}
      {items.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-500 mb-1">Total Stocks</p>
            <p className="text-2xl font-mono font-bold text-white">{stats.total}</p>
          </Card>
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-500 mb-1">Bullish</p>
            <p className="text-2xl font-mono font-bold text-emerald-400">{stats.bullish}</p>
          </Card>
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-500 mb-1">Bearish</p>
            <p className="text-2xl font-mono font-bold text-red-400">{stats.bearish}</p>
          </Card>
          <Card className="terminal-card p-4">
            <p className="text-xs text-slate-500 mb-1">Avg Score</p>
            <p className={`text-2xl font-mono font-bold ${
              stats.avgScore >= 70 ? 'text-emerald-400' :
              stats.avgScore >= 50 ? 'text-amber-400' : 'text-red-400'
            }`}>{stats.avgScore || '—'}</p>
          </Card>
        </div>
      )}

      {/* Watchlist Items */}
      {filteredItems.length > 0 ? (
        <div className="space-y-3">
          {filteredItems.map(item => (
            <WatchlistCard
              key={item.id}
              item={item}
              onRemove={handleRemove}
              onUpdateNote={handleUpdateNote}
            />
          ))}
        </div>
      ) : items.length > 0 ? (
        <Card className="terminal-card p-8 text-center">
          <Search className="w-10 h-10 mx-auto mb-3 text-slate-600" />
          <p className="text-slate-500 mb-1">No matches found</p>
          <p className="text-xs text-slate-600">Try a different search term</p>
        </Card>
      ) : (
        <Card className="terminal-card p-12 text-center">
          <Star className="w-12 h-12 mx-auto mb-4 text-slate-700" />
          <p className="text-lg text-slate-400 mb-2">Your watchlist is empty</p>
          <p className="text-sm text-slate-600 mb-4">
            Add stocks using the search above or by clicking the star icon on Trading and Investment cards
          </p>
        </Card>
      )}

      {/* Info */}
      <Card className="terminal-card p-4 border-blue-500/20 bg-blue-500/5">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-blue-200 font-medium mb-1">Watchlist Tips</p>
            <p className="text-xs text-blue-200/70">
              Add stocks from the Trading or Investments tabs using the star icon. Your watchlist persists across sessions.
              Scores and signals are refreshed when you load this page or click "Refresh". Add notes to remember why you added each stock.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Watchlist;
