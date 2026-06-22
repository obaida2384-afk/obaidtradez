// Builds the Research-page company object from LIVE data (DCF payload + universe record),
// falling back to a mock entry only for purely-qualitative fields (e.g. moat).
export function buildResearchCompany({ dcf, universe, mock } = {}) {
  const co = dcf?.company || {};
  const a = dcf?.assumptions || {};
  const an = dcf?.analyst || {};
  const comps = dcf?.comps || {};
  const memo = dcf?.memo || {};
  const histRows = dcf?.historicals?.rows || [];
  const u = universe || {};
  const m = mock || {};

  const years = histRows.map((r) => r.year);
  const revenueHistory = histRows.map((r) => r.revenue);
  const ebitdaHistory = histRows.map((r) => r.ebitda);
  const fcfHistory = histRows.map((r) => r.freeCashFlow);

  // 5-year revenue forecast projected from the real DCF growth assumptions.
  const lastRev = revenueHistory.length ? revenueHistory[revenueHistory.length - 1] : co.revenue;
  const revGrowth = a.revGrowth || [];
  const revenueForcast = [];
  let prev = lastRev;
  for (let i = 0; i < 5; i++) {
    const g = revGrowth[i] ?? co.revenueGrowth ?? 10;
    prev = prev != null ? prev * (1 + g / 100) : null;
    revenueForcast.push(prev != null ? Math.round(prev) : null);
  }

  const avgPt = an.targetConsensus ?? u.avgPt ?? m.avgPt ?? null;
  const impliedUpside = an.impliedUpside ?? u.dcfUpside ?? m.dcfUpside ?? null;

  return {
    ticker: co.ticker || u.ticker || m.ticker,
    name: co.name || u.name || m.name,
    sector: co.sector || u.sector || m.sector || "—",
    industry: co.industry || u.industry || m.industry || "—",
    price: co.price ?? u.price ?? m.price,
    change: m.change ?? 0,
    pct: m.pct ?? 0,
    marketCap: co.marketCap ?? u.marketCap ?? m.marketCap ?? null,
    description: co.description || m.description || `${co.name || u.name || "The company"} operates in the ${co.sector || u.sector || "market"} sector.`,
    risks: (co.risks && co.risks.length ? co.risks : m.risks) || [],
    moat: m.moat || null,

    pe: u.pe ?? m.pe ?? comps.medianPe ?? null,
    evEbitda: u.evEbitda ?? m.evEbitda ?? comps.medianEvEbitda ?? null,
    revenueGrowth: co.revenueGrowth ?? u.revenueGrowth ?? m.revenueGrowth ?? null,
    grossMargin: u.grossMargin ?? m.grossMargin ?? null,
    fcfMargin: u.fcfMargin ?? m.fcfMargin ?? null,
    ebitdaMargin: co.ebitdaMargin ?? u.ebitdaMargin ?? m.ebitdaMargin ?? null,
    roe: u.roe ?? m.roe ?? null,
    analystRating: an.consensus || u.analystRating || m.analystRating || "—",
    avgPt,
    dcfUpside: impliedUpside,

    wacc: a.wacc ?? m.wacc ?? null,
    tgr: a.tgr ?? m.tgr ?? null,
    exitMultiple: a.exitMultiple ?? co.exitMultiple ?? m.exitMultiple ?? null,
    impliedPrice: avgPt,

    years,
    revenueHistory,
    ebitdaHistory,
    fcfHistory,
    revenueForcast,

    bullPrice: an.targetHigh ?? (avgPt ? Math.round(avgPt * 1.15) : null),
    baseprice: avgPt,
    bearPrice: an.targetLow ?? (avgPt ? Math.round(avgPt * 0.85) : null),
    bullCase: { thesis: memo.headline ? `Upside: ${memo.headline}` : "Faster growth and margin expansion than consensus." },
    baseCase: { thesis: memo.summary || "Consensus growth and margins broadly hold." },
    bearCase: { thesis: (co.risks && co.risks[0]) ? co.risks[0] : "Multiple compression and slower-than-expected growth." },

    memo,
    shariah: u.shariah || m.shariah,
    _live: !!(dcf || universe),
  };
}
