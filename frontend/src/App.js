import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import Dashboard from "./pages/Dashboard";
import StockDetail from "./pages/StockDetail";
import Screener from "./pages/Screener";
import Chat from "./pages/Chat";
import Rankings from "./pages/Rankings";
import { 
  LayoutDashboard, 
  Search, 
  MessageSquare, 
  TrendingUp,
  BarChart3
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Sidebar Navigation
const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  const navItems = [
    { path: "/", icon: LayoutDashboard, label: "Dashboard" },
    { path: "/rankings", icon: TrendingUp, label: "Rankings" },
    { path: "/screener", icon: BarChart3, label: "Screener" },
    { path: "/chat", icon: MessageSquare, label: "AI Chat" },
  ];
  
  return (
    <aside className="fixed left-0 top-0 h-full w-16 lg:w-56 bg-zinc-950 border-r border-zinc-800 z-40 flex flex-col" data-testid="sidebar">
      {/* Logo */}
      <div className="h-16 flex items-center justify-center lg:justify-start lg:px-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-md bg-blue-600 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <span className="hidden lg:block font-heading font-bold text-lg text-white">AlphaLens</span>
        </div>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 py-4">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`w-full flex items-center gap-3 px-4 py-3 transition-all duration-200 ${
                isActive 
                  ? "bg-blue-600/10 text-blue-400 border-r-2 border-blue-500" 
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50"
              }`}
              data-testid={`nav-${item.label.toLowerCase().replace(' ', '-')}`}
            >
              <item.icon className="w-5 h-5 mx-auto lg:mx-0" />
              <span className="hidden lg:block text-sm font-medium">{item.label}</span>
            </button>
          );
        })}
      </nav>
      
      {/* Footer */}
      <div className="p-4 border-t border-zinc-800">
        <p className="hidden lg:block text-[10px] text-zinc-500 text-center">
          For research only.<br/>Not financial advice.
        </p>
      </div>
    </aside>
  );
};

// Search Bar Component
const GlobalSearch = () => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();
  
  useEffect(() => {
    if (query.length < 1) {
      setResults([]);
      return;
    }
    
    const search = async () => {
      try {
        const response = await fetch(`${API}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        setResults(data.slice(0, 6));
        setIsOpen(true);
      } catch (e) {
        console.error(e);
      }
    };
    
    const debounce = setTimeout(search, 300);
    return () => clearTimeout(debounce);
  }, [query]);
  
  return (
    <div className="relative" data-testid="global-search">
      <div className="flex items-center bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 focus-within:border-blue-600 transition-colors">
        <Search className="w-4 h-4 text-zinc-500 mr-2" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          onBlur={() => setTimeout(() => setIsOpen(false), 200)}
          placeholder="Search stocks..."
          className="bg-transparent text-sm text-white placeholder:text-zinc-500 outline-none w-48 lg:w-64"
          data-testid="search-input"
        />
      </div>
      
      {isOpen && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-900 border border-zinc-800 rounded-md shadow-xl z-50 overflow-hidden">
          {results.map((stock, i) => (
            <button
              key={i}
              onClick={() => {
                navigate(`/stock/${stock.symbol}`);
                setQuery("");
                setIsOpen(false);
              }}
              className="w-full flex items-center justify-between px-3 py-2 hover:bg-zinc-800 transition-colors text-left"
              data-testid={`search-result-${stock.symbol}`}
            >
              <div>
                <span className="font-mono text-sm text-white">{stock.symbol}</span>
                <span className="text-xs text-zinc-500 ml-2 truncate max-w-[150px] inline-block align-middle">
                  {stock.name}
                </span>
              </div>
              <span className="text-[10px] text-zinc-600">{stock.exchangeShortName}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// Header
const Header = () => {
  return (
    <header className="h-16 bg-zinc-950/80 backdrop-blur-sm border-b border-zinc-800 flex items-center justify-between px-6 sticky top-0 z-30">
      <GlobalSearch />
      
      <div className="flex items-center gap-4">
        <div className="hidden md:flex items-center gap-2 text-xs text-zinc-500">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Live Data
        </div>
      </div>
    </header>
  );
};

// Main Layout
const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-zinc-950">
      <Sidebar />
      <div className="pl-16 lg:pl-56">
        <Header />
        <main className="p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App dark">
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/rankings" element={<Rankings />} />
            <Route path="/screener" element={<Screener />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/stock/:symbol" element={<StockDetail />} />
          </Routes>
        </Layout>
        <Toaster position="bottom-right" theme="dark" />
      </BrowserRouter>
    </div>
  );
}

export default App;
