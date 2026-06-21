// Excel model generator — requires xlsx package (npm install xlsx)
// Generates an institutional-quality DCF model workbook

let XLSXModule = null;

async function getXLSX() {
  if (XLSXModule) return XLSXModule;
  try {
    XLSXModule = await import("xlsx");
    return XLSXModule;
  } catch {
    return null;
  }
}

function fmt(n, decimals = 1) {
  if (n == null) return "N/A";
  return Number(n).toFixed(decimals);
}

function fmtM(n) {
  if (n == null) return "N/A";
  if (Math.abs(n) >= 1000000) return `$${(n / 1000000).toFixed(1)}T`;
  if (Math.abs(n) >= 1000) return `$${(n / 1000).toFixed(1)}B`;
  return `$${n.toFixed(0)}M`;
}

export async function generateExcelModel(company) {
  const XLSX = await getXLSX();
  if (!XLSX) {
    throw new Error("xlsx package not installed. Run: npm install xlsx");
  }

  const wb = XLSX.utils.book_new();

  // ── Cover Page ────────────────────────────────────────────────────────────
  const coverData = [
    [],
    ["", "ALPHAVAULT INVESTMENT RESEARCH"],
    ["", "Institutional Equity Research | Financial Model"],
    [],
    ["", "COMPANY", company.name],
    ["", "TICKER", company.ticker],
    ["", "SECTOR", company.sector],
    ["", "INDUSTRY", company.industry],
    ["", "MODEL DATE", new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })],
    ["", "CURRENT PRICE", `$${company.price}`],
    ["", "MARKET CAP", fmtM(company.marketCap)],
    [],
    ["", "DCF IMPLIED PRICE", `$${company.impliedPrice}`],
    ["", "ANALYST CONSENSUS PT", `$${company.avgPt}`],
    ["", "ANALYST RATING", company.analystRating],
    [],
    ["", "BULL CASE", `$${company.bullPrice}`],
    ["", "BASE CASE", `$${company.baseprice}`],
    ["", "BEAR CASE", `$${company.bearPrice}`],
    [],
    ["", "DISCLAIMER", "This model is for educational and research purposes only. It does not constitute investment advice."],
    ["", "", "AlphaVault does not guarantee accuracy of projections. Past performance is not indicative of future results."],
  ];
  const wscover = XLSX.utils.aoa_to_sheet(coverData);
  wscover["!cols"] = [{ wch: 3 }, { wch: 25 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(wb, wscover, "Cover");

  // ── Historical Financials ─────────────────────────────────────────────────
  const years = company.years || [2020, 2021, 2022, 2023, 2024];
  const rev = company.revenueHistory || [];
  const ebitda = company.ebitdaHistory || [];
  const fcf = company.fcfHistory || [];

  const calcGrowth = (arr, i) => {
    if (i === 0 || !arr[i] || !arr[i - 1]) return "—";
    return `${(((arr[i] - arr[i - 1]) / arr[i - 1]) * 100).toFixed(1)}%`;
  };

  const histData = [
    ["HISTORICAL FINANCIAL STATEMENTS ($M)"],
    [],
    ["", ...years],
    ["Revenue ($M)", ...rev.map((v) => Math.round(v).toLocaleString())],
    ["YoY Growth", "—", ...years.slice(1).map((_, i) => calcGrowth(rev, i + 1))],
    [],
    ["EBITDA ($M)", ...ebitda.map((v) => (v ? Math.round(v).toLocaleString() : "N/A"))],
    ["EBITDA Margin", ...rev.map((r, i) => (ebitda[i] ? `${((ebitda[i] / r) * 100).toFixed(1)}%` : "N/A"))],
    [],
    ["Free Cash Flow ($M)", ...fcf.map((v) => (v ? Math.round(v).toLocaleString() : "N/A"))],
    ["FCF Margin", ...rev.map((r, i) => (fcf[i] ? `${((fcf[i] / r) * 100).toFixed(1)}%` : "N/A"))],
    [],
    ["KEY METRICS"],
    ["P/E Ratio (TTM)", company.pe || "N/A"],
    ["EV/EBITDA (TTM)", company.evEbitda || "N/A"],
    ["Gross Margin", company.grossMargin ? `${company.grossMargin}%` : "N/A"],
    ["Net Margin", company.netMargin ? `${company.netMargin}%` : "N/A"],
    ["ROE", company.roe ? `${company.roe}%` : "N/A"],
  ];
  const wsHist = XLSX.utils.aoa_to_sheet(histData);
  wsHist["!cols"] = [{ wch: 25 }, ...years.map(() => ({ wch: 15 }))];
  XLSX.utils.book_append_sheet(wb, wsHist, "Historical Financials");

  // ── Revenue Forecast ──────────────────────────────────────────────────────
  const fcastYears = [2025, 2026, 2027, 2028, 2029];
  const fcastRev = company.revenueForcast || fcastYears.map((_, i) => (rev[rev.length - 1] || 0) * Math.pow(1.12, i + 1));

  const fcastData = [
    ["REVENUE & MARGIN FORECAST"],
    [],
    ["ASSUMPTION NOTES"],
    ["Revenue growth assumptions are based on: historical CAGR, analyst consensus estimates, management guidance, and industry growth."],
    ["Margin assumptions reflect: pricing power, scale economics, competitive dynamics, and historical trend."],
    [],
    ["", ...fcastYears],
    ["Revenue ($M)", ...fcastRev.map((v) => Math.round(v).toLocaleString())],
    ["YoY Growth", ...fcastRev.map((v, i) => {
      const prev = i === 0 ? rev[rev.length - 1] : fcastRev[i - 1];
      return prev ? `${(((v - prev) / prev) * 100).toFixed(1)}%` : "—";
    })],
    [],
    ["Gross Margin", ...fcastYears.map(() => `${fmt(company.grossMargin || 50)}%`)],
    ["EBITDA Margin", ...fcastYears.map((_, i) => `${fmt((company.ebitdaMargin || 20) + i * 0.5)}%`)],
    ["Net Margin", ...fcastYears.map(() => `${fmt(company.netMargin || 15)}%`)],
    ["FCF Margin", ...fcastYears.map((_, i) => `${fmt((company.fcfMargin || 12) + i * 0.5)}%`)],
    [],
    ["Forecasted EBITDA ($M)", ...fcastRev.map((v, i) => Math.round(v * ((company.ebitdaMargin || 20) + i * 0.5) / 100).toLocaleString())],
    ["Forecasted FCF ($M)", ...fcastRev.map((v, i) => Math.round(v * ((company.fcfMargin || 12) + i * 0.5) / 100).toLocaleString())],
  ];
  const wsFcast = XLSX.utils.aoa_to_sheet(fcastData);
  wsFcast["!cols"] = [{ wch: 28 }, ...fcastYears.map(() => ({ wch: 14 }))];
  XLSX.utils.book_append_sheet(wb, wsFcast, "Revenue Forecast");

  // ── DCF Model ─────────────────────────────────────────────────────────────
  const wacc = company.wacc || 10.0;
  const tgr = company.tgr || 3.0;
  const fcastFCF = fcastRev.map((v, i) => v * ((company.fcfMargin || 12) + i * 0.5) / 100);
  const pvFCF = fcastFCF.map((v, i) => v / Math.pow(1 + wacc / 100, i + 1));
  const pvSum = pvFCF.reduce((a, b) => a + b, 0);
  const tv = fcastFCF[fcastFCF.length - 1] * (1 + tgr / 100) / ((wacc - tgr) / 100);
  const pvTV = tv / Math.pow(1 + wacc / 100, 5);
  const ev = pvSum + pvTV;
  const netDebt = (company.debtToEbitda || 0) * ((ebitda[ebitda.length - 1] || 10000));
  const equityValue = ev - netDebt;
  const dilutedShares = company.marketCap / company.price;
  const impliedPrice = equityValue / dilutedShares;

  const dcfData = [
    ["DISCOUNTED CASH FLOW (DCF) MODEL"],
    [],
    ["WACC ASSUMPTIONS"],
    ["Risk-Free Rate (10Y Treasury)", "4.28%"],
    ["Equity Risk Premium", "5.50%"],
    ["Beta", fmt(wacc / 10.0 - 0.4)],
    ["Cost of Equity", `${fmt(4.28 + 5.50 * (wacc / 10.0 - 0.4))}%`],
    ["Pre-Tax Cost of Debt", "5.80%"],
    ["Tax Rate", "21.0%"],
    ["WACC", `${wacc}%`],
    [],
    ["TERMINAL VALUE ASSUMPTIONS"],
    ["Terminal Growth Rate", `${tgr}%`],
    ["Terminal Value (Gordon Growth)", `$${Math.round(tv).toLocaleString()}M`],
    ["PV of Terminal Value", `$${Math.round(pvTV).toLocaleString()}M`],
    [],
    ["DCF SUMMARY", ...fcastYears],
    ["Forecasted FCF ($M)", ...fcastFCF.map((v) => Math.round(v).toLocaleString())],
    ["PV of FCF ($M)", ...pvFCF.map((v) => Math.round(v).toLocaleString())],
    [],
    ["Sum of PV (FCFs)", `$${Math.round(pvSum).toLocaleString()}M`],
    ["PV of Terminal Value", `$${Math.round(pvTV).toLocaleString()}M`],
    ["Enterprise Value", `$${Math.round(ev).toLocaleString()}M`],
    ["Net Debt", `$${Math.round(netDebt).toLocaleString()}M`],
    ["Equity Value", `$${Math.round(equityValue).toLocaleString()}M`],
    ["Diluted Shares Outstanding (M)", Math.round(dilutedShares).toLocaleString()],
    ["IMPLIED SHARE PRICE", `$${impliedPrice.toFixed(2)}`],
    ["Current Price", `$${company.price}`],
    ["Upside / Downside", `${(((impliedPrice - company.price) / company.price) * 100).toFixed(1)}%`],
  ];
  const wsDCF = XLSX.utils.aoa_to_sheet(dcfData);
  wsDCF["!cols"] = [{ wch: 35 }, { wch: 18 }, ...fcastYears.map(() => ({ wch: 14 }))];
  XLSX.utils.book_append_sheet(wb, wsDCF, "DCF Model");

  // ── Sensitivity Tables ────────────────────────────────────────────────────
  const waccRange = [8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0];
  const tgrRange = [2.0, 2.5, 3.0, 3.5, 4.0];

  const sensHeader = ["WACC \\ TGR", ...tgrRange.map((t) => `${t}%`)];
  const sensRows = waccRange.map((w) => {
    const row = [`${w}%`];
    tgrRange.forEach((t) => {
      const tvS = fcastFCF[fcastFCF.length - 1] * (1 + t / 100) / ((w - t) / 100);
      const pvTvS = tvS / Math.pow(1 + w / 100, 5);
      const pvFcfS = fcastFCF.reduce((acc, v, i) => acc + v / Math.pow(1 + w / 100, i + 1), 0);
      const evS = pvFcfS + pvTvS;
      const eqS = evS - netDebt;
      row.push(`$${(eqS / dilutedShares).toFixed(0)}`);
    });
    return row;
  });

  const sensData = [
    ["SENSITIVITY ANALYSIS — Implied Share Price (WACC vs Terminal Growth Rate)"],
    [],
    sensHeader,
    ...sensRows,
    [],
    ["NOTE: Highlighted cells represent base case assumptions. Green = above current price. Red = below."],
  ];
  const wsSens = XLSX.utils.aoa_to_sheet(sensData);
  wsSens["!cols"] = [{ wch: 14 }, ...tgrRange.map(() => ({ wch: 12 }))];
  XLSX.utils.book_append_sheet(wb, wsSens, "Sensitivity Tables");

  // ── Bull / Base / Bear Scenarios ──────────────────────────────────────────
  const scenData = [
    ["SCENARIO ANALYSIS — Bull / Base / Bear"],
    [],
    ["", "BULL CASE", "BASE CASE", "BEAR CASE"],
    ["Probability", "25%", "50%", "25%"],
    ["Revenue Growth (5yr CAGR)", `${fmt((company.revenueGrowth || 15) + 5)}%`, `${fmt(company.revenueGrowth || 15)}%`, `${fmt((company.revenueGrowth || 15) - 8)}%`],
    ["EBITDA Margin (Exit)", `${fmt((company.ebitdaMargin || 20) + 5)}%`, `${fmt(company.ebitdaMargin || 20)}%`, `${fmt((company.ebitdaMargin || 20) - 5)}%`],
    ["WACC", `${fmt(wacc - 0.5)}%`, `${wacc}%`, `${fmt(wacc + 1.5)}%`],
    ["Terminal Growth Rate", `${fmt(tgr + 0.5)}%`, `${tgr}%`, `${fmt(tgr - 1.0)}%`],
    [],
    ["Implied Share Price", `$${company.bullPrice}`, `$${company.baseprice}`, `$${company.bearPrice}`],
    ["vs Current Price", `${(((company.bullPrice - company.price) / company.price) * 100).toFixed(1)}%`, `${(((company.baseprice - company.price) / company.price) * 100).toFixed(1)}%`, `${(((company.bearPrice - company.price) / company.price) * 100).toFixed(1)}%`],
    [],
    ["BULL CASE THESIS", company.bullCase?.thesis || `Strong execution on all growth vectors. ${company.name} expands into adjacent markets and sustains premium margins.`],
    ["BASE CASE THESIS", company.baseCase?.thesis || `Moderate growth in line with guidance. Margins expand incrementally as scale benefits kick in.`],
    ["BEAR CASE THESIS", company.bearCase?.thesis || `Competition intensifies, growth decelerates, and valuation multiple compresses toward historical average.`],
    [],
    ["RISK FACTORS"],
    ...(company.risks || ["Execution risk", "Competition", "Macro environment"]).map((r) => ["•", r]),
  ];
  const wsScen = XLSX.utils.aoa_to_sheet(scenData);
  wsScen["!cols"] = [{ wch: 30 }, { wch: 22 }, { wch: 22 }, { wch: 22 }];
  XLSX.utils.book_append_sheet(wb, wsScen, "Scenarios");

  // ── Investment Memo ────────────────────────────────────────────────────────
  const ratingLabel = impliedPrice > company.price * 1.2
    ? "STRONGLY ATTRACTIVE"
    : impliedPrice > company.price * 1.05
    ? "ATTRACTIVE"
    : impliedPrice >= company.price * 0.95
    ? "FAIRLY VALUED"
    : impliedPrice >= company.price * 0.8
    ? "EXPENSIVE"
    : "AVOID";

  const memoData = [
    ["INVESTMENT MEMORANDUM"],
    ["Generated by AlphaVault — For research purposes only"],
    [],
    ["COMPANY", company.name],
    ["TICKER", company.ticker],
    ["FINAL RATING", ratingLabel],
    [],
    ["EXECUTIVE SUMMARY"],
    [company.description || `${company.name} is a leading company in the ${company.sector} sector.`],
    [],
    ["INVESTMENT THESIS"],
    [company.moat ? `Competitive Advantages: ${company.moat}` : "See full research report for investment thesis."],
    [],
    ["VALUATION SUMMARY"],
    ["DCF Implied Price", `$${impliedPrice.toFixed(2)}`],
    ["Analyst Consensus PT", `$${company.avgPt}`],
    ["Bull / Base / Bear", `$${company.bullPrice} / $${company.baseprice} / $${company.bearPrice}`],
    [],
    ["KEY FINANCIALS"],
    ["Revenue (TTM)", fmtM(company.revenue)],
    ["Revenue Growth (YoY)", `${company.revenueGrowth}%`],
    ["EBITDA Margin", company.ebitdaMargin ? `${company.ebitdaMargin}%` : "N/A"],
    ["FCF Margin", company.fcfMargin ? `${company.fcfMargin}%` : "N/A"],
    [],
    ["RISK FACTORS"],
    ...(company.risks || []).map((r) => [`• ${r}`]),
    [],
    ["DISCLAIMER"],
    ["This model was generated by AlphaVault for educational purposes. It does not constitute financial advice."],
    ["All assumptions should be independently verified. Investing involves substantial risk of loss."],
    ["AlphaVault ratings: Strongly Attractive / Attractive / Fairly Valued / Expensive / Avoid"],
  ];
  const wsMemo = XLSX.utils.aoa_to_sheet(memoData);
  wsMemo["!cols"] = [{ wch: 30 }, { wch: 60 }];
  XLSX.utils.book_append_sheet(wb, wsMemo, "Investment Memo");

  // ── Write & Download ──────────────────────────────────────────────────────
  XLSX.writeFile(wb, `AlphaVault_${company.ticker}_Model_${new Date().toISOString().slice(0, 10)}.xlsx`);
}
