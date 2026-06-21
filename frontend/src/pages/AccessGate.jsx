import { useState } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Lock, TrendingUp, Shield, AlertTriangle, Loader2, User } from "lucide-react";
import { toast } from "sonner";

const AccessGate = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Please enter your username and password");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/auth/access`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), code: password.trim() })
      });

      const data = await response.json();

      if (data.success && data.token) {
        login(data.token);
        toast.success("Access granted! Welcome to ObaidTradez");
      } else {
        setError(data.message || "Invalid username or password");
        toast.error("Invalid credentials");
      }
    } catch (err) {
      setError("Connection error. Please try again.");
      toast.error("Connection error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="access-gate" data-testid="access-gate">
      <div className="scan-line opacity-30"></div>

      <Card className="w-full max-w-md mx-4 bg-[#0d1117] border-slate-800 p-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-red-500/5 pointer-events-none"></div>

        <div className="relative z-10">
          <div className="flex justify-center mb-8">
            <div className="flex items-center gap-3">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-500 to-red-500 flex items-center justify-center animate-pulse-glow">
                <TrendingUp className="w-8 h-8 text-white" />
              </div>
            </div>
          </div>

          <div className="text-center mb-8">
            <h1 className="font-display text-2xl font-bold text-white tracking-wider mb-1">
              OBAID<span className="text-blue-400">TRADEZ</span>
            </h1>
            <p className="text-slate-500 text-sm">AI Trading & Investing Platform</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Username"
                className="pl-10 h-12 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500 focus-visible:ring-blue-500"
                disabled={loading}
                autoComplete="username"
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="pl-10 h-12 bg-slate-900 border-slate-700 text-white placeholder:text-slate-500 focus-visible:ring-blue-500"
                disabled={loading}
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm p-2 bg-red-500/10 rounded-md border border-red-500/20">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-12 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold"
              disabled={loading}
              data-testid="access-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Verifying...
                </>
              ) : (
                <>
                  <Shield className="w-4 h-4 mr-2" />
                  Access Platform
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-800">
            <div className="flex items-start gap-2 text-xs text-slate-500">
              <Shield className="w-4 h-4 shrink-0 mt-0.5" />
              <p>
                This platform is secured with private access. Unauthorized access attempts are logged and monitored.
              </p>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3">
            {[
              { label: "Trading", desc: "Short-term signals" },
              { label: "Investing", desc: "Long-term analysis" },
              { label: "AI Chatbot", desc: "Financial advisor" },
              { label: "Paper Trading", desc: "Alpaca integration" }
            ].map((feat) => (
              <div key={feat.label} className="p-3 rounded-md bg-slate-900/50 border border-slate-800">
                <p className="text-xs font-medium text-slate-300">{feat.label}</p>
                <p className="text-[10px] text-slate-600">{feat.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <p className="absolute bottom-4 text-[10px] text-slate-600 font-mono">
        v1.0.0 | Secure Access Only
      </p>
    </div>
  );
};

export default AccessGate;
