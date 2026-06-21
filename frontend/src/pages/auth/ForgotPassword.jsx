import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Zap, ArrowLeft, Mail } from "lucide-react";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) return toast.error("Enter your email");
    await new Promise((r) => setTimeout(r, 600));
    setSent(true);
    toast.success("Reset instructions sent (demo mode)");
  };

  return (
    <div className="auth-bg flex items-center justify-center min-h-screen p-4">
      <div className="w-full max-w-sm animate-fade-in">
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
          {!sent ? (
            <>
              <h1 className="text-xl font-bold text-white mb-1.5">Reset your password</h1>
              <p className="text-sm text-slate-500 mb-7">Enter your email and we'll send instructions.</p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-slate-400 block mb-1.5">Email address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="input-dark"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-sm py-2.5 rounded-lg transition-colors"
                >
                  Send reset instructions
                </button>
              </form>
            </>
          ) : (
            <div className="text-center py-4">
              <div className="w-12 h-12 rounded-full bg-emerald-500/15 flex items-center justify-center mx-auto mb-4">
                <Mail className="w-6 h-6 text-emerald-400" />
              </div>
              <h2 className="text-lg font-bold text-white mb-2">Check your inbox</h2>
              <p className="text-sm text-slate-500">
                Reset instructions have been sent to <span className="text-slate-300">{email}</span>
              </p>
            </div>
          )}

          <Link to="/auth/login" className="flex items-center justify-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 mt-6 transition-colors">
            <ArrowLeft className="w-4 h-4" /> Back to sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
