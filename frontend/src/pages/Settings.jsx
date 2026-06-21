import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import {
  Settings as SettingsIcon, User, Key, Brain, Shield, LogOut,
  Eye, EyeOff, CheckCircle, Save, ChevronDown, ChevronUp,
} from "lucide-react";

const API_KEY_CONFIG = [
  {
    key: "fmp",
    label: "Financial Modeling Prep (FMP)",
    placeholder: "Enter your FMP API key...",
    description: "Powers live financial statements, income statements, balance sheets, cash flow, and DCF data for all companies.",
    docsHint: "financialmodelingprep.com/developer/docs",
    enables: ["Live financial data", "Real-time earnings", "SEC filings", "Historical financials"],
  },
  {
    key: "polygon",
    label: "Polygon.io",
    placeholder: "Enter your Polygon.io API key...",
    description: "Provides real-time and historical stock price data, market indices, and options flow.",
    docsHint: "polygon.io/docs",
    enables: ["Live price quotes", "Historical OHLCV data", "Market indices", "Options data"],
  },
  {
    key: "benzinga",
    label: "Benzinga News",
    placeholder: "Enter your Benzinga API key...",
    description: "Streams real-time financial news, press releases, earnings transcripts, and analyst upgrades/downgrades.",
    docsHint: "docs.benzinga.io",
    enables: ["Real-time news feed", "Analyst actions", "Press releases", "Earnings transcripts"],
  },
  {
    key: "openai",
    label: "OpenAI",
    placeholder: "Enter your OpenAI API key (sk-...)...",
    description: "Used for GPT-4 based natural language analysis, news summarisation, and investment thesis generation.",
    docsHint: "platform.openai.com/api-keys",
    enables: ["AI thesis generation", "News summarisation", "Natural language search", "Earnings Q&A"],
  },
  {
    key: "anthropic",
    label: "Anthropic (Claude)",
    placeholder: "Enter your Anthropic API key (sk-ant-...)...",
    description: "Powers Claude-based deep financial analysis, long-context document reading, and Shariah screening reasoning.",
    docsHint: "console.anthropic.com/settings/keys",
    enables: ["Deep financial analysis", "Long document Q&A", "Shariah reasoning", "Risk factor extraction"],
  },
];

const EXPERIENCE_OPTS = ["Beginner", "Intermediate", "Advanced", "Professional"];
const STYLE_OPTS = ["Value", "Growth", "Blend", "Income", "Momentum"];
const ORIENTATION_OPTS = ["Long-term (5+ years)", "Medium-term (1–5 years)", "Opportunistic"];
const MODEL_DETAIL_OPTS = ["Summary only", "Standard detail", "Full institutional detail"];

function ApiKeyField({ config, savedValue, onSave }) {
  const [value, setValue] = useState(savedValue || "");
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const isSaved = !!savedValue;

  const handleSave = () => {
    if (!value.trim()) { toast.error("Enter an API key before saving"); return; }
    onSave(config.key, value.trim());
    toast.success(`${config.label} key saved`);
  };

  const handleClear = () => {
    setValue("");
    onSave(config.key, "");
    toast.info(`${config.label} key removed`);
  };

  return (
    <div className="border border-white/[0.06] rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/[0.02] transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          {isSaved
            ? <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            : <Key className="w-4 h-4 text-slate-600 shrink-0" />}
          <div>
            <p className="text-sm font-medium text-slate-200">{config.label}</p>
            <p className="text-xs text-slate-600 mt-0.5">{isSaved ? "Connected" : "Not configured"}</p>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-white/[0.04]">
          <p className="text-xs text-slate-500 leading-relaxed mt-3 mb-3">{config.description}</p>
          <div className="flex flex-wrap gap-1.5 mb-4">
            {config.enables.map((e) => (
              <span key={e} className="text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5">{e}</span>
            ))}
          </div>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={visible ? "text" : "password"}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={config.placeholder}
                className="input-dark pr-10 font-mono text-xs"
              />
              <button type="button" onClick={() => setVisible((p) => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                {visible ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
            <button onClick={handleSave}
              className="flex items-center gap-1.5 px-3 py-2 bg-emerald-500/10 hover:bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap">
              <Save className="w-3.5 h-3.5" /> Save
            </button>
            {isSaved && (
              <button onClick={handleClear}
                className="px-3 py-2 bg-red-500/10 hover:bg-red-500/15 text-red-400 border border-red-500/20 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap">
                Remove
              </button>
            )}
          </div>
          <p className="text-[10px] text-slate-700 mt-2">Docs: {config.docsHint}</p>
        </div>
      )}
    </div>
  );
}

function SelectField({ label, value, options, onChange }) {
  return (
    <div>
      <label className="text-xs text-slate-400 block mb-1.5">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="glass-card px-3 py-2 text-sm text-slate-300 outline-none w-full">
        {options.map((o) => <option key={o} value={o} className="bg-slate-900">{o}</option>)}
      </select>
    </div>
  );
}

export default function Settings() {
  const { user, updateUser, updatePreferences, updateApiKeys, logout } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [prefs, setPrefs] = useState(user?.preferences || {});

  const connectedCount = Object.values(user?.apiKeys || {}).filter(Boolean).length;
  const totalKeys = API_KEY_CONFIG.length;

  const saveProfile = () => {
    updateUser({ name: name.trim() });
    toast.success("Profile updated");
  };

  const savePref = (key, val) => {
    const updated = { ...prefs, [key]: val };
    setPrefs(updated);
    updatePreferences(updated);
    toast.success("Preference saved");
  };

  const saveApiKey = (key, value) => {
    updateApiKeys({ [key]: value });
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-3xl">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <SettingsIcon className="w-5 h-5 text-slate-400" />
          <h1 className="text-2xl font-bold text-white">Settings</h1>
        </div>
        <p className="text-sm text-slate-500">Manage your profile, investing preferences, and API connections.</p>
      </div>

      {connectedCount === 0 ? (
        <div className="glass-card p-4 border-amber-500/20 flex items-start gap-3">
          <div className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-amber-400">Demo Mode Active</p>
            <p className="text-xs text-slate-500 mt-0.5">
              All data shown is simulated. Connect at least one API key below to switch to live market data.
            </p>
          </div>
        </div>
      ) : (
        <div className="glass-card p-4 border-emerald-500/20 flex items-start gap-3">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mt-1.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-emerald-400">Live Data Mode — {connectedCount}/{totalKeys} APIs Connected</p>
            <p className="text-xs text-slate-500 mt-0.5">
              Real market data is active for connected providers. Unconfigured providers fall back to demo data.
            </p>
          </div>
        </div>
      )}

      {/* Profile */}
      <section className="glass-card p-6">
        <div className="flex items-center gap-2 mb-5">
          <User className="w-4 h-4 text-slate-400" />
          <h2 className="text-sm font-semibold text-white">Profile</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className="input-dark" placeholder="Your name" />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Email</label>
            <input value={user?.email || ""} disabled className="input-dark opacity-50 cursor-not-allowed" />
          </div>
        </div>
        <button onClick={saveProfile}
          className="mt-4 flex items-center gap-1.5 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/15 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm font-semibold transition-colors">
          <Save className="w-3.5 h-3.5" /> Save Profile
        </button>
      </section>

      {/* Investing Preferences */}
      <section className="glass-card p-6">
        <div className="flex items-center gap-2 mb-5">
          <Brain className="w-4 h-4 text-violet-400" />
          <h2 className="text-sm font-semibold text-white">Investing Preferences</h2>
          <span className="text-xs text-slate-600 ml-auto">Used to personalise AI analysis</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <SelectField label="Experience Level" value={prefs.experience || "Intermediate"}
            options={EXPERIENCE_OPTS} onChange={(v) => savePref("experience", v)} />
          <SelectField label="Investing Style" value={prefs.investingStyle || "Blend"}
            options={STYLE_OPTS} onChange={(v) => savePref("investingStyle", v)} />
          <SelectField label="Time Horizon" value={prefs.orientation || "Long-term (5+ years)"}
            options={ORIENTATION_OPTS} onChange={(v) => savePref("orientation", v)} />
          <SelectField label="Model Output Detail" value={prefs.modelDetail || "Standard detail"}
            options={MODEL_DETAIL_OPTS} onChange={(v) => savePref("modelDetail", v)} />
        </div>
        <div className="mt-4 border-t border-white/[0.04] pt-4 flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-300">Shariah Compliance Filter</p>
            <p className="text-xs text-slate-600 mt-0.5">When enabled, only Shariah-compliant companies appear in Discovery and Top Plays</p>
          </div>
          <button onClick={() => savePref("shariahMode", !prefs.shariahMode)}
            className={`relative w-11 h-6 rounded-full transition-colors ${prefs.shariahMode ? "bg-emerald-500" : "bg-slate-700"}`}>
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${prefs.shariahMode ? "translate-x-5" : "translate-x-0"}`} />
          </button>
        </div>
      </section>

      {/* API Keys */}
      <section className="glass-card p-6">
        <div className="flex items-center gap-2 mb-2">
          <Key className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-semibold text-white">API Keys</h2>
          <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full border ${connectedCount > 0 ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" : "text-slate-500 bg-slate-500/10 border-slate-500/20"}`}>
            {connectedCount}/{totalKeys} connected
          </span>
        </div>
        <p className="text-xs text-slate-600 mb-5 leading-relaxed">
          API keys are stored locally in your browser and never transmitted to AlphaVault servers.
          Keys are only sent directly to the respective provider's API from your browser.
        </p>
        <div className="space-y-2">
          {API_KEY_CONFIG.map((config) => (
            <ApiKeyField key={config.key} config={config}
              savedValue={user?.apiKeys?.[config.key] || ""} onSave={saveApiKey} />
          ))}
        </div>
      </section>

      {/* Account */}
      <section className="glass-card p-6 border-red-500/10">
        <div className="flex items-center gap-2 mb-5">
          <Shield className="w-4 h-4 text-red-400" />
          <h2 className="text-sm font-semibold text-white">Account</h2>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-300">Sign Out</p>
            <p className="text-xs text-slate-600 mt-0.5">You will be returned to the login screen. Local portfolio data is preserved.</p>
          </div>
          <button onClick={logout}
            className="flex items-center gap-1.5 px-4 py-2 bg-red-500/10 hover:bg-red-500/15 text-red-400 border border-red-500/20 rounded-lg text-sm font-semibold transition-colors">
            <LogOut className="w-3.5 h-3.5" /> Sign Out
          </button>
        </div>
      </section>

      <p className="text-xs text-slate-700 pb-6">
        AlphaVault does not store your API keys or personal data on any server. All data is held locally in your browser's localStorage.
      </p>
    </div>
  );
}
