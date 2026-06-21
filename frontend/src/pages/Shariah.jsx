import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SHARIAH_UNIVERSE } from "@/lib/mockData";
import { Moon, Search, CheckCircle, XCircle, AlertCircle, Info } from "lucide-react";

const STATUS_STYLE = {
  Compliant: { color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20", icon: CheckCircle },
  "Non-Compliant": { color: "text-red-400", bg: "bg-red-500/10 border-red-500/20", icon: XCircle },
  Questionable: { color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20", icon: AlertCircle },
};

const SCORE_STYLE = {
  Pass: { color: "text-emerald-400", label: "Pass" },
  Fail: { color: "text-red-400", label: "Fail" },
  Borderline: { color: "text-amber-400", label: "Borderline" },
};

const STATUSES = ["All", "Compliant", "Non-Compliant", "Questionable"];

export default function Shariah() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");

  const filtered = SHARIAH_UNIVERSE.filter((c) => {
    const matchSearch = !search || c.ticker.includes(search.toUpperCase()) || c.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "All" || c.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const compliantCount = SHARIAH_UNIVERSE.filter((c) => c.status === "Compliant").length;
  const nonCompliantCount = SHARIAH_UNIVERSE.filter((c) => c.status === "Non-Compliant").length;
  const questionableCount = SHARIAH_UNIVERSE.filter((c) => c.status === "Questionable").length;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Moon className="w-5 h-5 text-emerald-400" />
          <h1 className="text-2xl font-bold text-white">Shariah Compliance Screen</h1>
        </div>
        <p className="text-sm text-slate-500">
          Filter investments for Shariah compliance across business activities, debt, and interest income screens.
        </p>
      </div>

      {/* Important disclaimer */}
      <div className="glass-card p-5 border-amber-500/20">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-400 mb-2">Important — Permission Filter Only</p>
            <p className="text-sm text-slate-400 leading-relaxed">
              Shariah compliance screening is a <strong className="text-white">permission filter</strong>, not an investment recommendation.
              A company being Shariah compliant does not mean it is a good investment. You must still evaluate the business fundamentals,
              valuation, and risks independently. AlphaVault provides this screen as a starting point — always consult a qualified Shariah
              scholar or certified Islamic finance advisor for religious rulings on specific investments.
            </p>
            <p className="text-xs text-slate-600 mt-3">
              Screens applied: (1) Business activity — no interest-based banking, alcohol, tobacco, gambling, weapons, entertainment.
              (2) Debt ratio — total debt/total assets below 33%. (3) Interest income — interest receivable below 5% of total revenue.
              Data is approximate and may not reflect the most recent financial statements.
            </p>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Compliant", count: compliantCount, style: STATUS_STYLE.Compliant },
          { label: "Non-Compliant", count: nonCompliantCount, style: STATUS_STYLE["Non-Compliant"] },
          { label: "Questionable", count: questionableCount, style: STATUS_STYLE.Questionable },
        ].map((item) => (
          <button
            key={item.label}
            onClick={() => setStatusFilter(statusFilter === item.label ? "All" : item.label)}
            className={`glass-card p-4 text-center border transition-all ${statusFilter === item.label ? item.style.bg : "border-white/[0.06]"}`}
          >
            <p className={`text-2xl font-bold font-mono ${item.style.color}`}>{item.count}</p>
            <p className="text-xs text-slate-500 mt-1">{item.label}</p>
          </button>
        ))}
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 glass-card px-3 py-2 flex-1 min-w-[200px] max-w-sm">
          <Search className="w-4 h-4 text-slate-500" />
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search ticker or company..." className="bg-transparent text-sm text-white placeholder:text-slate-600 outline-none flex-1" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="glass-card px-3 py-2 text-sm text-slate-300 outline-none">
          {STATUSES.map((s) => <option key={s} value={s} className="bg-slate-900">{s}</option>)}
        </select>
        <span className="text-xs text-slate-600">{filtered.length} companies</span>
      </div>

      {/* Table */}
      <div className="glass-card overflow-x-auto">
        <table className="data-table min-w-[700px]">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Company</th>
              <th>Status</th>
              <th>Business Activity</th>
              <th>Debt Screen</th>
              <th>Interest Screen</th>
              <th>Notes</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => {
              const s = STATUS_STYLE[c.status];
              const StatusIcon = s.icon;
              return (
                <tr key={c.ticker}>
                  <td className="font-mono font-bold text-blue-400">{c.ticker}</td>
                  <td className="text-slate-200">{c.name}</td>
                  <td>
                    <span className={`flex items-center gap-1.5 text-xs font-semibold ${s.color}`}>
                      <StatusIcon className="w-3.5 h-3.5" />
                      {c.status}
                    </span>
                  </td>
                  <td>
                    <span className={`text-xs font-semibold ${SCORE_STYLE[c.businessScore]?.color || "text-slate-400"}`}>
                      {SCORE_STYLE[c.businessScore]?.label || c.businessScore}
                    </span>
                  </td>
                  <td>
                    <span className={`text-xs font-semibold ${SCORE_STYLE[c.debtScore]?.color || "text-slate-400"}`}>
                      {SCORE_STYLE[c.debtScore]?.label || c.debtScore}
                    </span>
                  </td>
                  <td>
                    <span className={`text-xs font-semibold ${SCORE_STYLE[c.cashScore]?.color || "text-slate-400"}`}>
                      {SCORE_STYLE[c.cashScore]?.label || c.cashScore}
                    </span>
                  </td>
                  <td className="text-xs text-slate-500 max-w-[200px]">{c.note}</td>
                  <td>
                    <button onClick={() => navigate(`/research?ticker=${c.ticker}`)}
                      className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
                      Research →
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Screening methodology */}
      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Screening Methodology</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              title: "Business Activity Screen",
              items: [
                "Interest-based banking or insurance — Fail",
                "Alcohol, tobacco, or pork products — Fail",
                "Gambling or lottery operations — Fail",
                "Weapons manufacturing (primary) — Fail",
                "Adult entertainment — Fail",
              ],
            },
            {
              title: "Debt Screen",
              items: [
                "Total interest-bearing debt / Total assets < 33% — Pass",
                "Market cap based calculation also applied",
                "Borderline: 25–33% ratio requires scholar review",
                "Post-acquisition debt spikes may trigger reassessment",
              ],
            },
            {
              title: "Interest Income Screen",
              items: [
                "Interest receivable / Total revenue < 5% — Pass",
                "Borderline: 3–5% requires purification calculation",
                "Fail: >5% of revenue from interest or prohibited activities",
                "Cash-rich tech companies may flag on this screen",
              ],
            },
          ].map((section) => (
            <div key={section.title}>
              <p className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">{section.title}</p>
              <ul className="space-y-1.5">
                {section.items.map((item, i) => (
                  <li key={i} className="text-xs text-slate-500 flex items-start gap-1.5">
                    <span className="text-slate-700 mt-0.5">•</span> {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-slate-700 pb-4">
        Shariah screening data is approximate and for reference only. Consult a qualified Islamic finance scholar before making investment decisions based on religious compliance.
      </p>
    </div>
  );
}
