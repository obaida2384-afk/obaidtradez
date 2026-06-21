import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { PriceProvider } from "@/contexts/PriceContext";

// Auth pages
import Login from "@/pages/auth/Login";
import Signup from "@/pages/auth/Signup";
import ForgotPassword from "@/pages/auth/ForgotPassword";
import Onboarding from "@/pages/auth/Onboarding";

// Main pages
import Dashboard from "@/pages/Dashboard";
import Research from "@/pages/Research";
import Modeling from "@/pages/Modeling";
import Discovery from "@/pages/Discovery";
import TopPlays from "@/pages/TopPlays";
import FutureGiants from "@/pages/FutureGiants";
import Watchlist from "@/pages/Watchlist";
import Portfolio from "@/pages/Portfolio";
import MarketMacro from "@/pages/MarketMacro";
import News from "@/pages/News";
import Shariah from "@/pages/Shariah";
import Settings from "@/pages/Settings";

import {
  LayoutDashboard,
  Search,
  BarChart3,
  Sparkles,
  TrendingUp,
  Telescope,
  Star,
  Wallet,
  Globe,
  Newspaper,
  Moon,
  Settings as SettingsIcon,
  Menu,
  X,
  ChevronRight,
  Zap,
} from "lucide-react";

const NAV_GROUPS = [
  {
    label: null,
    items: [
      { path: "/", icon: LayoutDashboard, label: "Dashboard" },
    ],
  },
  {
    label: "Research",
    items: [
      { path: "/research", icon: Search, label: "Company Research" },
      { path: "/modeling", icon: BarChart3, label: "Financial Modeling" },
    ],
  },
  {
    label: "AI Intelligence",
    items: [
      { path: "/discovery", icon: Sparkles, label: "Discovery" },
      { path: "/top-plays", icon: TrendingUp, label: "Top Plays" },
      { path: "/future-giants", icon: Telescope, label: "Future Giants" },
    ],
  },
  {
    label: "Portfolio",
    items: [
      { path: "/watchlist", icon: Star, label: "Watchlist" },
      { path: "/portfolio", icon: Wallet, label: "Portfolio" },
    ],
  },
  {
    label: "Market",
    items: [
      { path: "/market", icon: Globe, label: "Market & Macro" },
      { path: "/news", icon: Newspaper, label: "News & Catalysts" },
      { path: "/shariah", icon: Moon, label: "Shariah Screen" },
    ],
  },
  {
    label: "Account",
    items: [
      { path: "/settings", icon: SettingsIcon, label: "Settings" },
    ],
  },
];

function Sidebar({ mobileOpen, onClose }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  useEffect(() => {
    onClose();
  }, [location.pathname]); // eslint-disable-line

  const isActive = (path) =>
    path === "/" ? location.pathname === "/" : location.pathname.startsWith(path);

  return (
    <>
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/70 backdrop-blur-sm z-40"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed left-0 top-0 h-full z-50 flex flex-col
          w-60 md:w-[60px] lg:w-60 bg-[#07070d] border-r border-white/[0.04]
          transition-transform duration-300
          ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}
      >
        {/* Logo */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-white/[0.04] shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center shrink-0 shadow-lg shadow-emerald-900/30">
              <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <div className="md:hidden lg:block overflow-hidden">
              <p className="text-white font-bold text-sm tracking-widest font-display leading-none">ALPHA</p>
              <p className="text-emerald-400 font-bold text-sm tracking-widest font-display leading-none">VAULT</p>
            </div>
          </div>
          <button onClick={onClose} className="md:hidden text-slate-500 hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {NAV_GROUPS.map((group, gi) => (
            <div key={gi} className={gi > 0 ? "pt-3" : ""}>
              {group.label && (
                <p className="md:hidden lg:block text-[10px] font-semibold text-slate-600 uppercase tracking-widest px-3 pb-1.5">
                  {group.label}
                </p>
              )}
              {group.items.map((item) => {
                const active = isActive(item.path);
                return (
                  <button
                    key={item.path}
                    onClick={() => navigate(item.path)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 group relative
                      ${active
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "text-slate-500 hover:text-slate-200 hover:bg-white/[0.04]"
                      }`}
                  >
                    <item.icon className={`w-[18px] h-[18px] shrink-0 md:mx-auto lg:mx-0 ${active ? "text-emerald-400" : ""}`} />
                    <span className="md:hidden lg:block truncate font-medium">{item.label}</span>
                    {active && (
                      <span className="md:hidden lg:flex ml-auto">
                        <ChevronRight className="w-3.5 h-3.5 text-emerald-500" />
                      </span>
                    )}
                    {/* Tooltip for collapsed state */}
                    <span className="hidden md:block lg:hidden absolute left-full ml-3 px-2 py-1 bg-slate-800 text-white text-xs rounded whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50">
                      {item.label}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* User footer */}
        <div className="p-3 border-t border-white/[0.04] shrink-0">
          <div className="md:hidden lg:flex items-center gap-2.5 px-2 py-1.5">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center shrink-0">
              <span className="text-white text-xs font-bold">
                {user?.name?.[0]?.toUpperCase() || "U"}
              </span>
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-slate-200 truncate">{user?.name || "Investor"}</p>
              <p className="text-[10px] text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <div className="md:flex lg:hidden justify-center py-1">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center">
              <span className="text-white text-xs font-bold">
                {user?.name?.[0]?.toUpperCase() || "U"}
              </span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

function Header({ onMenuOpen }) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleSearch = (e) => {
    if (e.key === "Enter" && query.trim()) {
      navigate(`/research?ticker=${query.toUpperCase()}`);
      setQuery("");
    }
  };

  const hasApiKeys = user?.apiKeys && Object.values(user.apiKeys).some(Boolean);

  return (
    <header className="h-14 bg-[#07070d]/90 backdrop-blur-sm border-b border-white/[0.04] flex items-center justify-between px-4 md:px-5 sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuOpen}
          className="md:hidden p-2 rounded-lg text-slate-500 hover:text-white hover:bg-white/[0.06]"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.06] rounded-lg px-3 py-1.5 w-48 md:w-72 focus-within:border-emerald-500/40 transition-colors">
          <Search className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value.toUpperCase())}
            onKeyDown={handleSearch}
            placeholder="Search ticker or company..."
            className="bg-transparent text-sm text-white placeholder:text-slate-600 outline-none flex-1 min-w-0"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        {!hasApiKeys && (
          <button
            onClick={() => navigate("/settings")}
            className="hidden sm:flex items-center gap-1.5 text-[11px] bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full px-3 py-1 hover:bg-amber-500/15 transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            Demo Mode · Connect APIs
          </button>
        )}
        {hasApiKeys && (
          <div className="flex items-center gap-1.5 text-[11px] text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="hidden sm:inline">Live Data</span>
          </div>
        )}
      </div>
    </header>
  );
}

function AppLayout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#08080f]">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="md:pl-[60px] lg:pl-60">
        <Header onMenuOpen={() => setMobileOpen(true)} />
        <main className="p-4 lg:p-6 max-w-[1600px]">{children}</main>
      </div>
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, hasCompletedOnboarding } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" state={{ from: location }} replace />;
  }
  if (!hasCompletedOnboarding && location.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
}

function AuthRoute({ children }) {
  const { isAuthenticated, hasCompletedOnboarding } = useAuth();
  if (isAuthenticated && hasCompletedOnboarding) {
    return <Navigate to="/" replace />;
  }
  if (isAuthenticated && !hasCompletedOnboarding) {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Auth routes — no layout */}
      <Route path="/auth/login" element={<AuthRoute><Login /></AuthRoute>} />
      <Route path="/auth/signup" element={<AuthRoute><Signup /></AuthRoute>} />
      <Route path="/auth/forgot-password" element={<ForgotPassword />} />
      <Route path="/onboarding" element={<Onboarding />} />

      {/* Protected app routes — with layout */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/research" element={<Research />} />
                <Route path="/modeling" element={<Modeling />} />
                <Route path="/discovery" element={<Discovery />} />
                <Route path="/top-plays" element={<TopPlays />} />
                <Route path="/future-giants" element={<FutureGiants />} />
                <Route path="/watchlist" element={<Watchlist />} />
                <Route path="/portfolio" element={<Portfolio />} />
                <Route path="/market" element={<MarketMacro />} />
                <Route path="/news" element={<News />} />
                <Route path="/shariah" element={<Shariah />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <PriceProvider>
        <BrowserRouter>
          <AppRoutes />
          <Toaster position="bottom-right" theme="dark" richColors />
        </BrowserRouter>
      </PriceProvider>
    </AuthProvider>
  );
}
