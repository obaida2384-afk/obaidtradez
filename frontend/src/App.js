import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import LandingPage from "./pages/LandingPage";
import InfographicReport from "./pages/InfographicReport";
import ObaidChat from "./pages/ObaidChat";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

// Theme Provider Context
const ThemeContext = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') || 'light';
    }
    return 'light';
  });

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
      {children}
    </div>
  );
};

const ThemeToggle = ({ theme, toggleTheme }) => {
  const location = useLocation();
  const isChat = location.pathname === '/chat';
  
  return (
    <Button
      variant="outline"
      size="icon"
      onClick={toggleTheme}
      className={`fixed z-50 rounded-full border-border/50 bg-background/80 backdrop-blur-sm hover:bg-muted ${isChat ? 'top-4 right-4' : 'top-6 right-6'}`}
      data-testid="theme-toggle-btn"
    >
      {theme === 'light' ? (
        <Moon className="h-4 w-4" />
      ) : (
        <Sun className="h-4 w-4" />
      )}
    </Button>
  );
};

const Navigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  if (location.pathname === '/') return null;
  
  return (
    <nav className="fixed top-6 left-6 z-50 flex gap-2" data-testid="main-navigation">
      <Button
        variant={location.pathname === '/report' ? 'default' : 'outline'}
        size="sm"
        onClick={() => navigate('/report')}
        className="font-mono text-xs uppercase tracking-wider"
        data-testid="nav-report-btn"
      >
        Report
      </Button>
      <Button
        variant={location.pathname === '/chat' ? 'default' : 'outline'}
        size="sm"
        onClick={() => navigate('/chat')}
        className="font-mono text-xs uppercase tracking-wider"
        data-testid="nav-chat-btn"
      >
        Obaid AI
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate('/')}
        className="font-mono text-xs uppercase tracking-wider"
        data-testid="nav-home-btn"
      >
        Home
      </Button>
    </nav>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <ThemeContext>
          <Navigation />
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/report" element={<InfographicReport />} />
            <Route path="/chat" element={<ObaidChat />} />
          </Routes>
          <Toaster position="bottom-right" />
        </ThemeContext>
      </BrowserRouter>
    </div>
  );
}

export default App;
