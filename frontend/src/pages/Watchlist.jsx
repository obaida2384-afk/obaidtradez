import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { COMPANY_UNIVERSE } from "@/lib/mockData";
import { toast } from "sonner";
import { Star, Plus, Trash2, Search, X } from "lucide-react";
import { usePrice, usePrices, LiveDot } from "@/contexts/PriceContext";

const fmt = (n, d = 1) => (n == null ? "—" : Number(n).toFixed(d));
const fmtM = (n) => {
  if (!n) return "N/A";
  if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}T`;
  if (n >= 1000) return `$${(n / 1000).toFixed(1)}B`;
  return `$${n}M`;
};

const DEFAULT_LISTS = [
  { id: "ai-tech", name: "AI & Technology", tickers: ["NVDA", "MSFT", "GOOGL", "META", "AMD"] },
  { id: "quality-compounders", name: "Quality Compounders", tickers: ["AAPL", "MSFT", "V", "AVGO"] },
  { id: "shariah", name: "Shariah Compliant", tickers: ["AAPL", "NVDA", "AMD", "LLY"] },
];

function WatchlistRow({ ticker, onRemove }) {
  const navigate = useNavigate();
  const c = COMPANY_UNIVERSE.find((co) => co.ticker === ticker);
  if (!c) return null;
  const up = c.pct >= 0;
  const dcfUp = c.dcfUpside >= 0;
  const scoreClass = c.opportunityScore >= 80 ? "score-high" : c.opportunityScore >= 65 ? "score-mid" : "score-low";

  return (
    <tr className="hover:bg-white/[0.025] transition-colors">
      <td>
        <button onClick={() => navigate(`/research?ticker=${ticker}`)} className="font-mono font-bold text-blue-400 hover:text-blue-300">
          {ticker}
        </button>
      </td>
      <td className="text-slate-200">{c.name}</td>
      <td className="font-mono text-white font-semibold">${c.price}</td>
      <td className={`font-mono font-semibold ${up ? "text-emerald-400" : "text-red-400"}`}>
        {up ? "+" : ""}{fmt(c.pct)}%
      </td>
      <td className="font-mono text-slate-300">{fmtM(c.marketCap)}</td>
      <td className="font-mono text-slate-400">{c.pe ? `${c.pe}x` : "—"}</td>
      <td className={`font-mono font-semibold ${dcfUp ? "text-emerald-400" : "text-red-400"}`}>
        {dcfUp ? "+" : ""}{fmt(c.dcfUpside)}%
      </td>
      <td>
        <span className={`text-xs font-medium ${
          c.analystRating === "Overweight" ? "text-emerald-400" :
          c.analystRating === "Underweight" ? "text-red-400" : "text-slate-400"
        }`}>{c.analystRating}</span>
      </td>
      <td>
        <div className={`score-ring ${scoreClass} w-8 h-8 text-xs`}>{c.opportunityScore}</div>
      </td>
      <td>
        <button onClick={() => onRemove(ticker)} className="text-slate-600 hover:text-red-400 transition-colors p-1">
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </td>
    </tr>
  );
}

function AddTickerModal({ onAdd, onClose }) {
  const [q, setQ] = useState("");
  const results = q.length > 0
    ? COMPANY_UNIVERSE.filter((c) =>
        c.ticker.includes(q.toUpperCase()) || c.name.toLowerCase().includes(q.toLowerCase())
      ).slice(0, 5)
    : [];

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-card p-5 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">Add to Watchlist</h3>
          <button onClick={onClose} className="text-slate-500 hover:text-white"><X className="w-4 h-4" /></button>
        </div>
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 mb-3">
          <Search className="w-4 h-4 text-slate-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value.toUpperCase())}
            placeholder="Search ticker..."
            className="bg-transparent text-sm text-white placeholder:text-slate-600 outline-none flex-1"
            autoFocus
          />
        </div>
        {results.map((c) => (
          <button
            key={c.ticker}
            onClick={() => { onAdd(c.ticker); onClose(); }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.05] text-left"
          >
            <span className="font-mono font-bold text-blue-400 w-14">{c.ticker}</span>
            <span className="text-sm text-slate-300 flex-1">{c.name}</span>
            <span className="text-xs text-slate-500">{c.sector}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Watchlist() {
  const [lists, setLists] = useState(DEFAULT_LISTS);
  const [activeList, setActiveList] = useState(DEFAULT_LISTS[0].id);
  const [showAdd, setShowAdd] = useState(false);
  const [newListName, setNewListName] = useState("");
  const [creatingList, setCreatingList] = useState(false);

  const current = lists.find((l) => l.id === activeList);

  const addTicker = (ticker) => {
    if (current.tickers.includes(ticker)) {
      toast.info(`${ticker} is already in this watchlist`);
      return;
    }
    setLists((prev) =>
      prev.map((l) => l.id === activeList ? { ...l, tickers: [...l.tickers, ticker] } : l)
    );
    toast.success(`${ticker} added to ${current.name}`);
  };

  const removeTicker = (ticker) => {
    setLists((prev) =>
      prev.map((l) => l.id === activeList ? { ...l, tickers: l.tickers.filter((t) => t !== ticker) } : l)
    );
  };

  const createList = () => {
    if (!newListName.trim()) return;
    const id = newListName.toLowerCase().replace(/\s+/g, "-");
    setLists((prev) => [...prev, { id, name: newListName.trim(), tickers: [] }]);
    setActiveList(id);
    setNewListName("");
    setCreatingList(false);
    toast.success(`"${newListName}" created`);
  };

  const deleteList = (id) => {
    if (lists.length === 1) return toast.error("Keep at least one watchlist");
    setLists((prev) => prev.filter((l) => l.id !== id));
    setActiveList(lists[0].id !== id ? lists[0].id : lists[1].id);
    toast.success("Watchlist deleted");
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {showAdd && <AddTickerModal onAdd={addTicker} onClose={() => setShowAdd(false)} />}

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white">Watchlist</h1>
          <p className="text-sm text-slate-500 mt-0.5">Track companies across multiple custom lists</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-1.5 text-sm bg-emerald-500/10 hover:bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 rounded-lg px-3 py-2 transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Company
          </button>
        </div>
      </div>

      {/* List tabs */}
      <div className="flex items-center gap-2 flex-wrap">
        {lists.map((l) => (
          <div key={l.id} className="flex items-center">
            <button
              onClick={() => setActiveList(l.id)}
              className={`px-4 py-2 rounded-l-lg text-sm font-medium transition-all ${
                activeList === l.id
                  ? "bg-white/[0.08] text-white border border-white/[0.1]"
                  : "text-slate-500 hover:text-slate-300 border border-transparent"
              }`}
            >
              <Star className={`w-3.5 h-3.5 inline mr-1.5 ${activeList === l.id ? "text-amber-400" : "text-slate-600"}`} />
              {l.name}
              <span className="ml-1.5 text-[10px] text-slate-600">({l.tickers.length})</span>
            </button>
            <button
              onClick={() => deleteList(l.id)}
              className={`px-2 py-2 rounded-r-lg text-slate-700 hover:text-red-400 transition-colors border-y border-r border-transparent ${
                activeList === l.id ? "border-white/[0.1] bg-white/[0.08]" : ""
              }`}
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
        {creatingList ? (
          <div className="flex items-center gap-2">
            <input
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && createList()}
              placeholder="List name..."
              className="input-dark py-1.5 text-sm w-36"
              autoFocus
            />
            <button onClick={createList} className="text-xs text-emerald-400 hover:text-emerald-300">Add</button>
            <button onClick={() => setCreatingList(false)} className="text-xs text-slate-500">Cancel</button>
          </div>
        ) : (
          <button
            onClick={() => setCreatingList(true)}
            className="text-sm text-slate-600 hover:text-slate-400 flex items-center gap-1 px-2 py-2 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" /> New list
          </button>
        )}
      </div>

      {/* Table */}
      {current && (
        <div className="glass-card overflow-x-auto">
          {current.tickers.length === 0 ? (
            <div className="text-center py-16 text-slate-600">
              <Star className="w-8 h-8 mx-auto mb-3 opacity-30" />
              <p className="text-sm">This watchlist is empty</p>
              <button onClick={() => setShowAdd(true)} className="text-sm text-emerald-400 mt-2 hover:text-emerald-300 flex items-center gap-1 mx-auto">
                <Plus className="w-4 h-4" /> Add your first company
              </button>
            </div>
          ) : (
            <table className="data-table min-w-[900px]">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th>Price</th>
                  <th>Today</th>
                  <th>Mkt Cap</th>
                  <th>P/E</th>
                  <th>DCF Upside</th>
                  <th>Rating</th>
                  <th>Score</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {current.tickers.map((t) => (
                  <WatchlistRow key={t} ticker={t} onRemove={removeTicker} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
