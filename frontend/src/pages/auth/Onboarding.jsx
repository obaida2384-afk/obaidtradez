import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { Zap, ChevronRight, ChevronLeft, Check } from "lucide-react";

const STEPS = [
  {
    id: "experience",
    title: "Investing Experience",
    subtitle: "Help us calibrate explanations and model detail for you.",
    field: "experience",
    options: [
      { value: "beginner", label: "Beginner", desc: "Learning the basics of investing" },
      { value: "intermediate", label: "Intermediate", desc: "Comfortable with fundamentals and valuation" },
      { value: "advanced", label: "Advanced", desc: "Professional or institutional-grade experience" },
      { value: "expert", label: "Expert / Professional", desc: "Buy-side, sell-side, or fund manager" },
    ],
  },
  {
    id: "style",
    title: "Investing Style",
    subtitle: "What best describes how you approach investment decisions?",
    field: "investingStyle",
    options: [
      { value: "long_term", label: "Long-Term Value", desc: "Hold great businesses for 5+ years" },
      { value: "growth", label: "Growth Investor", desc: "High-growth companies with expanding TAM" },
      { value: "garp", label: "GARP", desc: "Growth at a reasonable price" },
      { value: "special_situations", label: "Special Situations", desc: "Catalysts, turnarounds, spin-offs" },
    ],
  },
  {
    id: "orientation",
    title: "Return Orientation",
    subtitle: "What matters most in your return expectations?",
    field: "orientation",
    options: [
      { value: "growth", label: "Capital Growth", desc: "Maximize long-term price appreciation" },
      { value: "dividend", label: "Income & Dividends", desc: "Regular cash returns + moderate growth" },
      { value: "balanced", label: "Balanced", desc: "Both income and capital appreciation" },
      { value: "absolute", label: "Absolute Return", desc: "Positive returns in any market environment" },
    ],
  },
  {
    id: "shariah",
    title: "Shariah Preference",
    subtitle: "Would you like to filter for Shariah-compliant investments?",
    field: "shariahMode",
    options: [
      { value: false, label: "No preference", desc: "Show all investments regardless of compliance" },
      { value: true, label: "Shariah-compliant only", desc: "Filter results to compliant companies only" },
    ],
  },
  {
    id: "detail",
    title: "Model Detail Level",
    subtitle: "How much detail would you like in financial models and reports?",
    field: "modelDetail",
    options: [
      { value: "summary", label: "Summary", desc: "Key metrics, thesis, and rating only" },
      { value: "standard", label: "Standard", desc: "Full analysis with DCF and scenarios" },
      { value: "deep", label: "Deep Dive", desc: "Comprehensive institutional-grade with all assumptions" },
    ],
  },
];

export default function Onboarding() {
  const { completeOnboarding, user, isLoading } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [prefs, setPrefs] = useState({
    experience: "",
    investingStyle: "",
    orientation: "growth",
    shariahMode: false,
    modelDetail: "standard",
    sectors: [],
  });

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;
  const progress = ((step + 1) / STEPS.length) * 100;

  const select = (value) => {
    setPrefs((p) => ({ ...p, [current.field]: value }));
  };

  const next = () => {
    const val = prefs[current.field];
    if (val === "" || val === undefined || val === null) {
      return toast.error("Please make a selection to continue");
    }
    if (isLast) {
      completeOnboarding(prefs);
      toast.success(`Welcome to AlphaVault, ${user?.name?.split(" ")[0] || "Investor"}!`);
      navigate("/");
    } else {
      setStep((s) => s + 1);
    }
  };

  const currentValue = prefs[current.field];

  return (
    <div className="auth-bg min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-lg animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
            </div>
            <span className="text-white font-bold text-sm tracking-widest font-display">ALPHAVAULT</span>
          </div>
          <span className="text-xs text-slate-500">{step + 1} of {STEPS.length}</span>
        </div>

        {/* Progress */}
        <div className="h-1 bg-white/[0.06] rounded-full mb-8 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Step card */}
        <div className="glass-card p-8">
          <h2 className="text-xl font-bold text-white mb-1.5">{current.title}</h2>
          <p className="text-sm text-slate-500 mb-7">{current.subtitle}</p>

          <div className="space-y-2.5">
            {current.options.map((opt) => {
              const isSelected = currentValue === opt.value;
              return (
                <button
                  key={String(opt.value)}
                  onClick={() => select(opt.value)}
                  className={`w-full flex items-center gap-4 p-4 rounded-xl border text-left transition-all duration-150
                    ${isSelected
                      ? "border-emerald-500/50 bg-emerald-500/10"
                      : "border-white/[0.06] bg-white/[0.02] hover:border-white/[0.12] hover:bg-white/[0.04]"
                    }`}
                >
                  <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors
                    ${isSelected ? "border-emerald-500 bg-emerald-500" : "border-slate-600"}`}>
                    {isSelected && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
                  </div>
                  <div>
                    <p className={`text-sm font-semibold ${isSelected ? "text-emerald-300" : "text-slate-200"}`}>{opt.label}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{opt.desc}</p>
                  </div>
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-3 mt-8">
            {step > 0 && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-white/[0.08] text-slate-400 hover:text-white hover:border-white/[0.14] text-sm transition-colors"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
            )}
            <button
              onClick={next}
              className="flex-1 flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-sm py-2.5 rounded-lg transition-colors"
            >
              {isLast ? "Enter AlphaVault" : "Continue"}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-slate-700 mt-6">
          You can change these preferences anytime in Settings
        </p>
      </div>
    </div>
  );
}
