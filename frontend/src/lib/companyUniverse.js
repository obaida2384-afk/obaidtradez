const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Backend stores marketCap in absolute dollars; the UI helpers expect millions.
const toMillions = (mc) => (mc == null ? null : Math.round(mc / 1e6));

// Map an API universe record into the shape the existing UI components expect.
export function normalizeCompany(r) {
  if (!r) return null;
  const vm = r.valuationMultiples || {};
  return {
    ticker: r.ticker,
    name: r.companyName,
    sector: r.sector || "Unknown",
    industry: r.industry,
    opportunityScore: r.opportunityScore ?? 0,
    riskScore: r.riskScore,
    marketCap: toMillions(r.marketCap),
    price: r.price,
    revenueGrowth: r.revenueGrowth,
    revenueAcceleration: r.revenueAcceleration,
    ebitdaMargin: r.ebitdaMargin,
    grossMargin: r.ebitdaMargin,
    fcfMargin: r.fcfMargin,
    epsGrowth: r.epsGrowth,
    analystRating: r.analystRating,
    avgPt: r.analystPriceTarget,
    dcfUpside: r.analystUpsidePct,
    pe: vm.pe,
    evEbitda: vm.evEbitda,
    peers: r.peerComparison || [],
    thesis: r.thesis,
    bullCase: r.bullCase,
    baseCase: r.baseCase,
    bearCase: r.bearCase,
    catalysts: r.catalysts || [],
    macroSensitivity: r.macroSensitivity,
    shariah: r.shariahStatus || "Unknown",
    source: r.source || {},
    lastUpdated: r.lastUpdated,
    live: true,
  };
}

export async function fetchCompanies({
  page = 1,
  limit = 60,
  sector,
  search,
  minOpportunity,
  sortBy = "opportunityScore",
  order = -1,
} = {}) {
  const params = new URLSearchParams({ page, limit, sort_by: sortBy, order });
  if (sector && sector !== "All") params.set("sector", sector);
  if (search) params.set("search", search);
  if (minOpportunity != null) params.set("min_opportunity", minOpportunity);

  const res = await fetch(`${API}/universe/companies?${params.toString()}`);
  if (!res.ok) throw new Error(`Universe request failed: ${res.status}`);
  const data = await res.json();
  return {
    ...data,
    companies: (data.companies || []).map(normalizeCompany),
  };
}

export async function fetchMarketNews(items = 24) {
  const res = await fetch(`${API}/news/market?items=${items}`);
  if (!res.ok) throw new Error(`Market news failed: ${res.status}`);
  return res.json();
}

export async function fetchNewsSuggestions(limit = 12) {
  const res = await fetch(`${API}/news/suggestions?limit=${limit}`);
  if (!res.ok) throw new Error(`News suggestions failed: ${res.status}`);
  return res.json();
}

export async function fetchCompanyNews(ticker, items = 12) {
  const res = await fetch(`${API}/news/company/${ticker}?items=${items}`);
  if (!res.ok) throw new Error(`Company news failed: ${res.status}`);
  return res.json();
}

export async function fetchQuotes(tickers) {
  if (!tickers?.length) return { prices: {} };
  const res = await fetch(`${API}/prices/quotes?symbols=${tickers.join(",")}`);
  if (!res.ok) throw new Error(`Quotes failed: ${res.status}`);
  return res.json();
}

export async function fetchDcf(ticker) {
  const res = await fetch(`${API}/modeling/dcf/${ticker}`);
  if (!res.ok) throw new Error(`DCF request failed: ${res.status}`);
  return res.json();
}

export async function fetchCompany(ticker) {
  const res = await fetch(`${API}/universe/company/${ticker}`);
  if (!res.ok) return null;
  return normalizeCompany(await res.json());
}

export async function fetchCoverage() {
  const res = await fetch(`${API}/universe/coverage`);
  if (!res.ok) throw new Error(`Coverage request failed: ${res.status}`);
  return res.json();
}

export async function fetchFutureGiants({ limit = 12 } = {}) {
  const params = new URLSearchParams({ limit });
  const res = await fetch(`${API}/universe/future-giants?${params.toString()}`);
  if (!res.ok) throw new Error(`Future giants request failed: ${res.status}`);
  const data = await res.json();
  return {
    ...data,
    companies: (data.companies || []).map((c) => ({
      ...c,
      marketCap: c.marketCap == null ? null : Math.round(c.marketCap / 1e6),
    })),
  };
}

export async function fetchShortTermGrowth({ limit = 30, maxMegacap = 6 } = {}) {
  const params = new URLSearchParams({ limit, max_megacap: maxMegacap });
  const res = await fetch(`${API}/universe/short-term-growth?${params.toString()}`);
  if (!res.ok) throw new Error(`Short-term growth request failed: ${res.status}`);
  const data = await res.json();
  return {
    ...data,
    companies: (data.companies || []).map((c) => ({
      ...c,
      marketCap: c.marketCap == null ? null : Math.round(c.marketCap / 1e6),
    })),
  };
}
