import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { Eye, EyeOff, Zap, ArrowRight, Check } from "lucide-react";

export default function Signup() {
  const { signup, isLoading } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);

  const checks = [
    { label: "8+ characters", pass: password.length >= 8 },
    { label: "Uppercase letter", pass: /[A-Z]/.test(password) },
    { label: "Number", pass: /[0-9]/.test(password) },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !email || !password) return toast.error("All fields required");
    if (password.length < 8) return toast.error("Password must be at least 8 characters");
    const result = await signup(email, password, name.trim());
    if (result.success) {
      toast.success("Account created — let's set up your profile");
    }
  };

  return (
    <div className="auth-bg flex items-center justify-center min-h-screen p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="flex items-center gap-3 mb-10 justify-center">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center shadow-lg shadow-emerald-900/40">
            <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-white font-bold text-lg tracking-widest font-display leading-none">ALPHA</p>
            <p className="text-emerald-400 font-bold text-lg tracking-widest font-display leading-none">VAULT</p>
          </div>
        </div>

        <div className="glass-card p-8">
          <h1 className="text-xl font-bold text-white mb-1.5">Create your account</h1>
          <p className="text-sm text-slate-500 mb-7">Institutional investment research, powered by AI</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1.5">Full name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="input-dark"
                autoComplete="name"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1.5">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="input-dark"
                autoComplete="email"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Create a strong password"
                  className="input-dark pr-10"
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {password && (
                <div className="flex gap-3 mt-2">
                  {checks.map((c) => (
                    <span key={c.label} className={`flex items-center gap-1 text-[11px] ${c.pass ? "text-emerald-400" : "text-slate-600"}`}>
                      <Check className="w-3 h-3" />
                      {c.label}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm py-2.5 rounded-lg transition-colors mt-2"
            >
              {isLoading ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Create account <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <p className="text-center text-xs text-slate-600 mt-5">
            By creating an account you agree to use this platform for research only.
            <br />Not financial advice. Investing involves risk.
          </p>

          <p className="text-center text-sm text-slate-500 mt-4">
            Already have an account?{" "}
            <Link to="/auth/login" className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
