import { useState, useEffect, createContext, useContext } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import AccessGate from "./pages/AccessGate";
import Dashboard from "./pages/Dashboard";
import Trading from "./pages/Trading";
import Investments from "./pages/Investments";
import Chatbot from "./pages/Chatbot";
import News from "./pages/News";
import Screener from "./pages/Screener";
import Backtesting from "./pages/Backtesting";
import Portfolio from "./pages/Portfolio";
import Alerts from "./pages/Alerts";
import AutoTrade from "./pages/AutoTrade";
import Settings from "./pages/Settings";
import Watchlist from "./pages/Watchlist";
import LongTermInvest from "./pages/LongTermInvest";
import { 
  LayoutDashboard, 
  TrendingUp, 
  PiggyBank, 
  MessageSquare, 
  Newspaper,
  Search,
  History,
  Wallet,
  Bell,
  Bot,
  Settings as SettingsIcon,
  Star,
  Menu,
  X,
  Briefcase
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem('obaidtradez_token'));
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  // Only show loading spinner if there's a token to verify — no token means show password prompt immediately
  const [loading, setLoading] = useState(() => !!localStorage.getItem('obaidtradez_token'));

  useEffect(() => {
    verifyToken();
  }, [token]);

  const verifyToken = async () => {
    if (!token) {
      setIsAuthenticated(false);
      setLoading(false);
      return;
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${API}/auth/verify`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      const data = await response.json();
      setIsAuthenticated(data.valid);
      if (!data.valid) {
        localStorage.removeItem('obaidtradez_token');
      }
    } catch {
      setIsAuthenticated(false);
      localStorage.removeItem('obaidtradez_token');
    }
    setLoading(false);
  };

  const login = (newToken) => {
    localStorage.setItem('obaidtradez_token', newToken);
    setToken(newToken);
    setIsAuthenticated(true);
  };

  const logout = () => {
    localStorage.removeItem('obaidtradez_token');
    setToken(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ token, isAuthenticated, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// Sidebar
const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  
  const navItems = [
    { path: "/", icon: LayoutDashboard, label: "Dashboard" },
    { path: "/trading", icon: TrendingUp, label: "Trading" },
    { path: "/investments", icon: PiggyBank, label: "Investments" },
    { path: "/long-term", icon: Briefcase, label: "Long-Term" },
    { path: "/watchlist", icon: Star, label: "Watchlist" },
    { path: "/chatbot", icon: MessageSquare, label: "Chatbot" },
    { path: "/screener", icon: Search, label: "Screener" },
    { path: "/news", icon: Newspaper, label: "News" },
    { path: "/backtesting", icon: History, label: "Backtesting" },
    { path: "/portfolio", icon: Wallet, label: "Portfolio" },
    { path: "/alerts", icon: Bell, label: "Alerts" },
    { path: "/auto", icon: Bot, label: "Auto Trade" },
    { path: "/settings", icon: SettingsIcon, label: "Settings" },
  ];

  // Close on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);
  
  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="md:hidden fixed top-3 left-3 z-50 p-2 rounded-lg bg-slate-900 border border-slate-700"
        data-testid="mobile-menu-btn"
      >
        <Menu className="w-5 h-5 text-white" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`sidebar fixed left-0 top-0 h-full z-50 flex flex-col transition-transform duration-300 ease-in-out
          w-64 md:w-16 lg:w-56
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-500 to-red-500 flex items-center justify-center shrink-0">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <div className="md:hidden lg:block">
              <span className="font-display font-bold text-sm text-white tracking-wider">OBAID</span>
              <span className="font-display font-bold text-sm text-blue-400 tracking-wider">TRADEZ</span>
            </div>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1 rounded text-slate-400 hover:text-white"
            data-testid="mobile-menu-close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Navigation */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setMobileOpen(false);
                }}
                className={`sidebar-item w-full ${isActive ? 'active' : ''}`}
                data-testid={`nav-${item.label.toLowerCase().replace(/[^a-z]/g, '-')}`}
              >
                <item.icon className="w-5 h-5 md:mx-auto lg:mx-0 shrink-0" />
                <span className="md:hidden lg:block text-sm">{item.label}</span>
              </button>
            );
          })}
        </nav>
        
        {/* Status */}
        <div className="p-4 border-t border-slate-800">
          <div className="md:hidden lg:flex items-center gap-2 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-slate-500">Paper Trading</span>
          </div>
        </div>
      </aside>
    </>
  );
};

// Header with search
const Header = () => {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  
  const handleSearch = (e) => {
    if (e.key === 'Enter' && query.trim()) {
      navigate(`/trading?symbol=${query.toUpperCase()}`);
    }
  };
  
  return (
    <header className="h-14 bg-[#080810]/80 backdrop-blur-sm border-b border-slate-800 flex items-center justify-between px-4 md:px-6 sticky top-0 z-30">
      <div className="flex items-center gap-3 bg-slate-900 border border-slate-800 rounded-md px-3 py-1.5 ml-10 md:ml-0">
        <Search className="w-4 h-4 text-slate-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value.toUpperCase())}
          onKeyDown={handleSearch}
          placeholder="Search symbols..."
          className="bg-transparent text-sm text-white placeholder:text-slate-500 outline-none w-32 md:w-40 lg:w-64"
          data-testid="search-input"
        />
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span className="text-slate-400">Live</span>
        </div>
      </div>
    </header>
  );
};

// Protected Layout
const ProtectedLayout = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-500 text-sm">Loading ObaidTradez...</p>
        </div>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <AccessGate />;
  }
  
  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      <Sidebar />
      <div className="md:pl-16 lg:pl-56">
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
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/*" element={
              <ProtectedLayout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/trading" element={<Trading />} />
                  <Route path="/investments" element={<Investments />} />
                  <Route path="/long-term" element={<LongTermInvest />} />
                  <Route path="/watchlist" element={<Watchlist />} />
                  <Route path="/chatbot" element={<Chatbot />} />
                  <Route path="/screener" element={<Screener />} />
                  <Route path="/news" element={<News />} />
                  <Route path="/backtesting" element={<Backtesting />} />
                  <Route path="/portfolio" element={<Portfolio />} />
                  <Route path="/alerts" element={<Alerts />} />
                  <Route path="/auto" element={<AutoTrade />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </ProtectedLayout>
            } />
          </Routes>
          <Toaster position="bottom-right" theme="dark" />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
