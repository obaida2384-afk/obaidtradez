// Shared buy/sell recommendation derived from valuation upside, opportunity score and news tone.
export const RATING_STYLE = {
  "Strong Buy": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  "Buy": "text-emerald-300 bg-emerald-500/[0.08] border-emerald-500/20",
  "Hold": "text-slate-300 bg-slate-500/10 border-slate-500/20",
  "Not a Good Buy": "text-amber-400 bg-amber-500/10 border-amber-500/30",
  "Avoid": "text-red-400 bg-red-500/10 border-red-500/30",
};

export function getRating({ upsidePct, secondaryUpsidePct, opportunityScore, newsSentiment } = {}) {
  const ups = [upsidePct, secondaryUpsidePct].filter((x) => x != null && !Number.isNaN(Number(x))).map(Number);
  const blended = ups.length ? ups.reduce((a, b) => a + b, 0) / ups.length : null;

  let label = "Hold";
  if (blended != null || opportunityScore != null) {
    let score = 0;
    if (blended != null) {
      if (blended >= 25) score = 2;
      else if (blended >= 10) score = 1;
      else if (blended <= -20) score = -2;
      else if (blended <= -5) score = -1;
    }
    if (opportunityScore != null) {
      if (opportunityScore >= 80) score += 0.5;
      else if (opportunityScore < 50) score -= 0.5;
    }
    if (newsSentiment === "Positive") score += 0.25;
    else if (newsSentiment === "Negative") score -= 0.25;

    if (score >= 2) label = "Strong Buy";
    else if (score >= 0.75) label = "Buy";
    else if (score > -0.75) label = "Hold";
    else if (score > -2) label = "Not a Good Buy";
    else label = "Avoid";
  }
  return { label, className: RATING_STYLE[label] };
}
