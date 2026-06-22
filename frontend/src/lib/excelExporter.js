// Institutional DCF workbook generator (ExcelJS) — multi-sheet, formula-driven,
// professionally formatted. Built from the live DCF model payload.

let ExcelJSModule = null;
async function getExcelJS() {
  if (ExcelJSModule) return ExcelJSModule;
  const mod = await import("exceljs");
  ExcelJSModule = mod.default || mod;
  return ExcelJSModule;
}

// ── palette ───────────────────────────────────────────────────────────────────
const DARK = "FF1F3864";   // dark blue header
const SUB = "FFD9E1F2";    // light blue subheader
const YEL = "FFFFF2CC";    // yellow input
const GRAY = "FFF2F2F2";   // gray formula
const GREEN = "FF107C41";
const RED = "FFC00000";
const WHITE = "FFFFFFFF";
const BORDER = { style: "thin", color: { argb: "FFBFBFBF" } };
const fill = (argb) => ({ type: "pattern", pattern: "solid", fgColor: { argb } });
const allBorders = { top: BORDER, left: BORDER, bottom: BORDER, right: BORDER };

function headerRow(ws, row, labels, opts = {}) {
  const r = ws.getRow(row);
  labels.forEach((t, i) => {
    const cell = r.getCell(i + 1);
    cell.value = t;
    cell.fill = fill(opts.sub ? SUB : DARK);
    cell.font = { bold: true, color: { argb: opts.sub ? DARK : WHITE }, size: opts.size || 11 };
    cell.alignment = { vertical: "middle", horizontal: i === 0 ? "left" : "right" };
    cell.border = allBorders;
  });
  r.height = opts.height || 20;
  return r;
}

function pct(v) { return v == null ? null : v / 100; }

export async function generateExcelModel(model) {
  const ExcelJS = await getExcelJS();
  // Accept either the rich payload or a bare company (graceful fallback).
  const company = model.company || model;
  const a = model.assumptions || {};
  const hist = model.historicals;
  const comps = model.comps;
  const analyst = model.analyst;
  const macro = model.macro;
  const memo = model.memo;
  const ticker = company.ticker || "TICKER";

  const wb = new ExcelJS.Workbook();
  wb.creator = "ALPHA VAULT";
  wb.created = new Date();

  // ════════════════════════ COVER ════════════════════════
  const cover = wb.addWorksheet("Cover", { properties: { tabColor: { argb: DARK } } });
  cover.columns = [{ width: 4 }, { width: 30 }, { width: 30 }, { width: 20 }];
  cover.mergeCells("B2:D2");
  cover.getCell("B2").value = "ALPHA VAULT — EQUITY RESEARCH";
  cover.getCell("B2").font = { bold: true, size: 18, color: { argb: DARK } };
  cover.mergeCells("B3:D3");
  cover.getCell("B3").value = "Discounted Cash Flow Model";
  cover.getCell("B3").font = { italic: true, size: 11, color: { argb: "FF808080" } };
  const coverRows = [
    ["Company", company.name],
    ["Ticker", ticker],
    ["Sector", company.sector],
    ["Industry", company.industry],
    ["Current Price", company.price != null ? `$${company.price}` : "—"],
    ["Analyst Consensus", analyst?.consensus || "—"],
    ["Consensus Target", analyst?.targetConsensus != null ? `$${analyst.targetConsensus}` : "—"],
    ["Recommendation", model.recommendation || "—"],
    ["Model Date", new Date().toISOString().slice(0, 10)],
  ];
  coverRows.forEach(([k, v], i) => {
    const row = 6 + i;
    cover.getCell(`B${row}`).value = k;
    cover.getCell(`B${row}`).font = { bold: true, color: { argb: DARK } };
    cover.getCell(`C${row}`).value = v == null ? "—" : v;
  });
  const recArgbCover = /Strong Buy|^Buy/.test(model.recommendation || "") ? GREEN : /Avoid|Not a Good/.test(model.recommendation || "") ? RED : DARK;
  cover.getCell("C13").font = { bold: true, color: { argb: recArgbCover } };
  cover.getCell("B16").value = "Educational research only. Not investment advice. Outputs depend on assumptions, which are uncertain.";
  cover.getCell("B16").font = { italic: true, size: 9, color: { argb: "FF808080" } };
  cover.mergeCells("B16:D16");

  // ════════════════════════ DCF MODEL (formula-driven) ════════════════════════
  const ws = wb.addWorksheet("DCF Model", { properties: { tabColor: { argb: DARK } } });
  ws.columns = [{ width: 30 }, { width: 14 }, { width: 14 }, { width: 14 }, { width: 14 }, { width: 14 }, { width: 14 }];
  ws.mergeCells("A1:G1");
  ws.getCell("A1").value = `${company.name} (${ticker}) — DCF Model`;
  ws.getCell("A1").font = { bold: true, size: 14, color: { argb: WHITE } };
  ws.getCell("A1").fill = fill(DARK);
  ws.getRow(1).height = 26;
  ws.getCell("A1").alignment = { vertical: "middle" };

  const usd = "#,##0";
  const pf = "0.0%";
  const ps = "$#,##0.00";

  const baseRev = company.revenue || 0;
  const growth = (a.revGrowth || [8, 7, 6, 5, 4]).slice(0, 5);
  const margin = (a.ebitdaMargin || [20, 20, 20, 20, 20]).slice(0, 5);
  const daP = (a.daPercent || [6, 6, 6, 6, 6]).slice(0, 5);
  const capexP = (a.capexPercent || [4, 4, 4, 4, 4]).slice(0, 5);
  const nwcP = (a.nwcPercent || [2, 2, 2, 2, 2]).slice(0, 5);

  // INPUTS (yellow)
  headerRow(ws, 3, ["Key Inputs (editable)", "", "", "", "", "", ""]);
  const inputCells = [
    ["Base Revenue ($M)", baseRev, usd, "C5"],
    ["Tax Rate", pct(a.taxRate ?? 21), pf, "C6"],
    ["WACC", pct(a.wacc ?? 9), pf, "C7"],
    ["Terminal Growth", pct(a.tgr ?? 3), pf, "C8"],
    ["Total Debt ($M)", a.debt ?? 0, usd, "C9"],
    ["Cash ($M)", a.cash ?? 0, usd, "C10"],
    ["Diluted Shares (M)", a.sharesOut ?? 0, usd, "C11"],
    ["Current Price", company.price ?? 0, ps, "C12"],
  ];
  inputCells.forEach(([label, val, fmt], i) => {
    const row = 5 + i;
    ws.getCell(`A${row}`).value = label;
    const c = ws.getCell(`C${row}`);
    c.value = val;
    c.numFmt = fmt;
    c.fill = fill(YEL);
    c.font = { bold: true };
    c.border = allBorders;
    c.alignment = { horizontal: "right" };
  });

  // Forecast driver rows (yellow inputs), period header row 14
  const yearStart = (company.years && company.years.length ? company.years[company.years.length - 1] : new Date().getFullYear()) + 1;
  headerRow(ws, 14, ["Forecast Drivers", "Y1", "Y2", "Y3", "Y4", "Y5"].concat([""]), { sub: true });
  ws.getRow(14).getCell(7).value = "";
  const periodRow = 15;
  ws.getCell(`A${periodRow}`).value = "Fiscal Year";
  for (let i = 0; i < 5; i++) {
    const col = 3 + i; // C..G
    const cell = ws.getRow(periodRow).getCell(col);
    cell.value = yearStart + i;
    cell.font = { bold: true };
    cell.alignment = { horizontal: "right" };
  }
  const driverDefs = [
    ["Revenue Growth %", growth, pf, true],
    ["EBITDA Margin %", margin, pf, true],
    ["D&A % of Revenue", daP, pf, true],
    ["CapEx % of Revenue", capexP, pf, true],
    ["Δ NWC % of Revenue", nwcP, pf, true],
  ];
  const driverRowStart = 16;
  driverDefs.forEach(([label, arr, fmt], di) => {
    const row = driverRowStart + di;
    ws.getCell(`A${row}`).value = label;
    for (let i = 0; i < 5; i++) {
      const col = 3 + i;
      const cell = ws.getRow(row).getCell(col);
      cell.value = pct(arr[i]);
      cell.numFmt = fmt;
      cell.fill = fill(YEL);
      cell.border = allBorders;
      cell.alignment = { horizontal: "right" };
    }
  });
  const G_ROW = driverRowStart, M_ROW = driverRowStart + 1, DA_ROW = driverRowStart + 2,
    CX_ROW = driverRowStart + 3, NWC_ROW = driverRowStart + 4;

  // BUILD (gray formulas)
  let r = driverRowStart + 6; // 22
  headerRow(ws, r - 1, ["Unlevered Free Cash Flow Build", "", "", "", "", "", ""]);
  const cols = ["C", "D", "E", "F", "G"];
  const colLetter = (i) => cols[i];
  const prevRevRef = (i) => (i === 0 ? "$C$5" : `${colLetter(i - 1)}${r}`);

  const REV = r;
  ws.getCell(`A${REV}`).value = "Revenue ($M)";
  cols.forEach((cl, i) => { const c = ws.getCell(`${cl}${REV}`); c.value = { formula: `${prevRevRef(i)}*(1+${cl}${G_ROW})` }; c.numFmt = usd; });
  const EBITDA = r + 1;
  ws.getCell(`A${EBITDA}`).value = "EBITDA ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${EBITDA}`); c.value = { formula: `${cl}${REV}*${cl}${M_ROW}` }; c.numFmt = usd; });
  const DA = r + 2;
  ws.getCell(`A${DA}`).value = "(–) D&A ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${DA}`); c.value = { formula: `${cl}${REV}*${cl}${DA_ROW}` }; c.numFmt = usd; });
  const EBIT = r + 3;
  ws.getCell(`A${EBIT}`).value = "EBIT ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${EBIT}`); c.value = { formula: `${cl}${EBITDA}-${cl}${DA}` }; c.numFmt = usd; });
  const TAX = r + 4;
  ws.getCell(`A${TAX}`).value = "(–) Taxes ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${TAX}`); c.value = { formula: `MAX(0,${cl}${EBIT})*$C$6` }; c.numFmt = usd; });
  const NOPAT = r + 5;
  ws.getCell(`A${NOPAT}`).value = "NOPAT ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${NOPAT}`); c.value = { formula: `${cl}${EBIT}-${cl}${TAX}` }; c.numFmt = usd; });
  const ADDDA = r + 6;
  ws.getCell(`A${ADDDA}`).value = "(+) D&A ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${ADDDA}`); c.value = { formula: `${cl}${DA}` }; c.numFmt = usd; });
  const CAPEX = r + 7;
  ws.getCell(`A${CAPEX}`).value = "(–) CapEx ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${CAPEX}`); c.value = { formula: `${cl}${REV}*${cl}${CX_ROW}` }; c.numFmt = usd; });
  const DNWC = r + 8;
  ws.getCell(`A${DNWC}`).value = "(–) Δ NWC ($M)";
  cols.forEach((cl, i) => { const c = ws.getCell(`${cl}${DNWC}`); c.value = { formula: `(${cl}${REV}-${prevRevRef(i)})*${cl}${NWC_ROW}` }; c.numFmt = usd; });
  const UFCF = r + 9;
  ws.getCell(`A${UFCF}`).value = "Unlevered FCF ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${UFCF}`); c.value = { formula: `${cl}${NOPAT}+${cl}${ADDDA}-${cl}${CAPEX}-${cl}${DNWC}` }; c.numFmt = usd; c.font = { bold: true }; });
  const DF = r + 10;
  ws.getCell(`A${DF}`).value = "Discount Factor";
  cols.forEach((cl, i) => { const c = ws.getCell(`${cl}${DF}`); c.value = { formula: `1/(1+$C$7)^${i + 1}` }; c.numFmt = "0.000"; });
  const PV = r + 11;
  ws.getCell(`A${PV}`).value = "PV of UFCF ($M)";
  cols.forEach((cl) => { const c = ws.getCell(`${cl}${PV}`); c.value = { formula: `${cl}${UFCF}*${cl}${DF}` }; c.numFmt = usd; c.font = { bold: true }; });

  // style build block gray + borders
  for (let rr = REV; rr <= PV; rr++) {
    cols.forEach((cl) => {
      const c = ws.getCell(`${cl}${rr}`);
      if (!c.fill || !c.fill.fgColor) c.fill = fill(GRAY);
      c.border = allBorders;
      c.alignment = { horizontal: "right" };
    });
  }

  // ── Valuation summary ──
  let v = PV + 2;
  headerRow(ws, v, ["Valuation Summary", "", "", "", "", "", ""]);
  const set = (label, formula, fmt, color) => {
    v += 1;
    ws.getCell(`A${v}`).value = label;
    const c = ws.getCell(`C${v}`);
    c.value = { formula };
    c.numFmt = fmt;
    c.font = { bold: true, color: color ? { argb: color } : undefined };
    c.fill = fill(GRAY);
    c.border = allBorders;
    c.alignment = { horizontal: "right" };
    return v;
  };
  const sumPV = set("PV of Forecast UFCF ($M)", `SUM(C${PV}:G${PV})`, usd);
  const tv = set("Terminal Value ($M, Gordon)", `G${UFCF}*(1+$C$8)/($C$7-$C$8)`, usd);
  const pvtv = set("PV of Terminal Value ($M)", `C${tv}*G${DF}`, usd);
  const ev = set("Enterprise Value ($M)", `C${sumPV}+C${pvtv}`, usd);
  const eq = set("(–) Debt (+) Cash → Equity ($M)", `C${ev}-$C$9+$C$10`, usd);
  const impl = set("Implied Value / Share", `C${eq}/$C$11`, ps, GREEN);
  set("Implied Upside / (Downside)", `C${impl}/$C$12-1`, pf);

  v += 2;
  ws.getCell(`A${v}`).value = "Recommendation";
  ws.getCell(`A${v}`).font = { bold: true };
  const recArgb = /Strong Buy|^Buy/.test(model.recommendation || "") ? GREEN : /Avoid|Not a Good/.test(model.recommendation || "") ? RED : DARK;
  const recCell = ws.getCell(`C${v}`);
  recCell.value = model.recommendation || "—";
  recCell.font = { bold: true, color: { argb: recArgb } };
  recCell.fill = fill(GRAY);
  recCell.border = allBorders;
  recCell.alignment = { horizontal: "right" };

  // ════════════════════════ HISTORICAL FINANCIALS ════════════════════════
  if (hist?.rows?.length) {
    const h = wb.addWorksheet("Historical Financials");
    h.columns = [{ width: 26 }].concat(hist.rows.map(() => ({ width: 14 })));
    headerRow(h, 1, ["Line Item ($M)"].concat(hist.rows.map((x) => `FY${x.year}`)));
    const lines = [
      ["Revenue", "revenue", usd], ["Gross Profit", "grossProfit", usd], ["Gross Margin", "grossMargin", pf],
      ["Operating Income", "operatingIncome", usd], ["EBITDA", "ebitda", usd], ["EBITDA Margin", "ebitdaMargin", pf],
      ["Net Income", "netIncome", usd], ["Diluted EPS", "eps", "$#,##0.00"], ["Free Cash Flow", "freeCashFlow", usd],
    ];
    lines.forEach(([label, key, fmt], li) => {
      const row = h.getRow(2 + li);
      row.getCell(1).value = label;
      hist.rows.forEach((x, ci) => {
        const c = row.getCell(2 + ci);
        c.value = key.includes("Margin") ? pct(x[key]) : x[key];
        c.numFmt = fmt;
        c.alignment = { horizontal: "right" };
        c.border = allBorders;
      });
    });
    h.getCell(`A${3 + lines.length}`).value = `Source: ${hist.source}`;
    h.getCell(`A${3 + lines.length}`).font = { italic: true, size: 9, color: { argb: "FF808080" } };
  }

  // ════════════════════════ SENSITIVITY (green→red color scale) ════════════════════════
  const sens = wb.addWorksheet("Sensitivity");
  sens.columns = [{ width: 16 }, { width: 12 }, { width: 12 }, { width: 12 }, { width: 12 }, { width: 12 }];
  sens.mergeCells("A1:F1");
  sens.getCell("A1").value = "Implied Value / Share — WACC (rows) vs Terminal Growth (cols)";
  sens.getCell("A1").font = { bold: true, color: { argb: WHITE } };
  sens.getCell("A1").fill = fill(DARK);
  const baseW = (a.wacc ?? 9) / 100, baseT = (a.tgr ?? 3) / 100;
  const waccs = [-0.015, -0.0075, 0, 0.0075, 0.015].map((d) => baseW + d);
  const tgrs = [0.02, 0.025, 0.03, 0.035, 0.04];
  const inputs = { baseRev, growth: growth.map((x) => x / 100), margin: margin.map((x) => x / 100), daP: daP.map((x) => x / 100), capexP: capexP.map((x) => x / 100), nwcP: nwcP.map((x) => x / 100), tax: (a.taxRate ?? 21) / 100, debt: a.debt ?? 0, cash: a.cash ?? 0, shares: a.sharesOut || 1 };
  sens.getRow(3).getCell(1).value = "WACC \\ TGR";
  tgrs.forEach((t, i) => { const c = sens.getRow(3).getCell(2 + i); c.value = t; c.numFmt = pf; c.fill = fill(SUB); c.font = { bold: true, color: { argb: DARK } }; c.alignment = { horizontal: "right" }; });
  waccs.forEach((w, wi) => {
    const row = sens.getRow(4 + wi);
    const lc = row.getCell(1); lc.value = w; lc.numFmt = pf; lc.fill = fill(SUB); lc.font = { bold: true, color: { argb: DARK } };
    tgrs.forEach((t, ti) => {
      const c = row.getCell(2 + ti);
      c.value = computeImplied(inputs, w, t);
      c.numFmt = "$#,##0.00";
      c.alignment = { horizontal: "right" };
      c.border = allBorders;
    });
  });
  sens.addConditionalFormatting({
    ref: `B4:F${3 + waccs.length}`,
    rules: [{ type: "colorScale", cfvo: [{ type: "min" }, { type: "percentile", value: 50 }, { type: "max" }], color: [{ argb: RED }, { argb: "FFFFEB84" }, { argb: GREEN }] }],
  });

  // ════════════════════════ COMPARABLES ════════════════════════
  if (comps?.rows?.length) {
    const cw = wb.addWorksheet("Comparables");
    cw.columns = [{ width: 10 }, { width: 28 }, { width: 14 }, { width: 10 }, { width: 12 }, { width: 10 }, { width: 12 }, { width: 12 }];
    headerRow(cw, 1, ["Ticker", "Company", "Mkt Cap ($M)", "P/E", "EV/EBITDA", "P/S", "Rev Gr.", "EBITDA M."]);
    comps.rows.forEach((row, i) => {
      const rr = cw.getRow(2 + i);
      rr.values = [row.ticker, row.name, row.marketCap, row.pe, row.evEbitda, row.ps, row.revenueGrowth != null ? row.revenueGrowth / 100 : null, row.ebitdaMargin != null ? row.ebitdaMargin / 100 : null];
      rr.getCell(3).numFmt = usd; rr.getCell(7).numFmt = pf; rr.getCell(8).numFmt = pf;
      if (row.isTarget) rr.eachCell((c) => { c.fill = fill(SUB); c.font = { bold: true }; });
      rr.eachCell((c) => { c.border = allBorders; });
    });
    const mr = cw.getRow(3 + comps.rows.length);
    mr.getCell(2).value = "Peer Median"; mr.getCell(2).font = { bold: true };
    mr.getCell(4).value = comps.medianPe; mr.getCell(5).value = comps.medianEvEbitda;
  }

  // ════════════════════════ ANALYST & MACRO ════════════════════════
  const am = wb.addWorksheet("Analyst & Macro");
  am.columns = [{ width: 26 }, { width: 22 }];
  headerRow(am, 1, ["Analyst Recommendations", ""]);
  const amRows = [
    ["Consensus", analyst?.consensus], ["Strong Buy", analyst?.strongBuy], ["Buy", analyst?.buy],
    ["Hold", analyst?.hold], ["Sell", analyst?.sell], ["Strong Sell", analyst?.strongSell],
    ["Target (Consensus)", analyst?.targetConsensus != null ? `$${analyst.targetConsensus}` : "—"],
    ["Target Range", analyst ? `$${analyst.targetLow}–$${analyst.targetHigh}` : "—"],
    ["Implied Upside", analyst?.impliedUpside != null ? `${analyst.impliedUpside}%` : "—"],
  ];
  amRows.forEach(([k, val], i) => { const row = am.getRow(2 + i); row.getCell(1).value = k; row.getCell(1).font = { bold: true }; row.getCell(2).value = val == null ? "—" : val; });
  let mrow = 2 + amRows.length + 1;
  headerRow(am, mrow, ["Macro (Treasury / WACC inputs)", ""]);
  const macroRows = [
    ["Risk-Free (10Y UST)", macro?.riskFreeRate10y != null ? `${macro.riskFreeRate10y}%` : "—"],
    ["As Of", macro?.asOf || "—"],
    ...Object.entries(macro?.yieldCurve || {}).map(([k, vv]) => [k, `${vv}%`]),
  ];
  macroRows.forEach(([k, val], i) => { const row = am.getRow(mrow + 1 + i); row.getCell(1).value = k; row.getCell(1).font = { bold: true }; row.getCell(2).value = val; });

  // ════════════════════════ ASSUMPTIONS (sources) ════════════════════════
  if (a.meta) {
    const as = wb.addWorksheet("Assumptions");
    as.columns = [{ width: 22 }, { width: 40 }, { width: 50 }, { width: 12 }];
    headerRow(as, 1, ["Assumption", "Source", "Reasoning", "Confidence"]);
    Object.entries(a.meta).forEach(([k, m], i) => {
      const row = as.getRow(2 + i);
      row.getCell(1).value = k; row.getCell(1).font = { bold: true };
      row.getCell(2).value = m.source; row.getCell(3).value = m.reasoning;
      const cc = row.getCell(4); cc.value = m.confidence;
      cc.font = { bold: true, color: { argb: m.confidence === "High" ? GREEN : m.confidence === "Low" ? RED : "FF1F3864" } };
      row.eachCell((c) => { c.alignment = { vertical: "top", wrapText: true }; c.border = allBorders; });
    });
  }

  // ════════════════════════ INVESTMENT MEMO ════════════════════════
  const mw = wb.addWorksheet("Investment Memo");
  mw.columns = [{ width: 100 }];
  mw.getCell("A1").value = memo?.headline || `${company.name} (${ticker}) — Investment Memo`;
  mw.getCell("A1").font = { bold: true, size: 13, color: { argb: WHITE } };
  mw.getCell("A1").fill = fill(DARK);
  mw.getRow(1).height = 24;
  mw.getCell("A3").value = memo?.summary || "";
  mw.getCell("A3").alignment = { wrapText: true, vertical: "top" };
  mw.getRow(3).height = 90;
  if (company.risks?.length) {
    mw.getCell("A5").value = "Risk Factors";
    mw.getCell("A5").font = { bold: true, color: { argb: DARK } };
    company.risks.forEach((rk, i) => { mw.getCell(`A${6 + i}`).value = `•  ${rk}`; mw.getCell(`A${6 + i}`).alignment = { wrapText: true }; });
  }
  const dr = 6 + (company.risks?.length || 0) + 1;
  mw.getCell(`A${dr}`).value = memo?.disclaimer || "Educational research only. Not investment advice.";
  mw.getCell(`A${dr}`).font = { italic: true, size: 9, color: { argb: "FF808080" } };

  // ════════════════════════ NEWS & CATALYSTS ════════════════════════
  const news = model.news;
  if (news?.articles?.length) {
    const nw = wb.addWorksheet("News & Catalysts", { properties: { tabColor: { argb: DARK } } });
    nw.columns = [{ width: 20 }, { width: 66 }, { width: 20 }, { width: 12 }, { width: 16 }];
    const sent = news.sentiment || {};
    nw.mergeCells("A1:E1");
    nw.getCell("A1").value = `${ticker} — News & Catalysts  (Tone: ${sent.tone || "Neutral"} · ${sent.positive || 0} positive / ${sent.negative || 0} negative)`;
    nw.getCell("A1").font = { bold: true, size: 13, color: { argb: WHITE } };
    nw.getCell("A1").fill = fill(DARK);
    nw.getRow(1).height = 24;
    headerRow(nw, 3, ["Date", "Headline", "Source", "Sentiment", "Tickers"], { sub: true });
    news.articles.forEach((art, i) => {
      const row = nw.getRow(4 + i);
      row.getCell(1).value = art.date || "—";
      if (art.url) {
        row.getCell(2).value = { text: art.title || "", hyperlink: art.url };
        row.getCell(2).font = { color: { argb: "FF1F3864" }, underline: true };
      } else {
        row.getCell(2).value = art.title || "";
      }
      row.getCell(3).value = art.source || "—";
      const sc = row.getCell(4);
      sc.value = art.sentiment || "Neutral";
      sc.font = { bold: true, color: { argb: art.sentiment === "Positive" ? GREEN : art.sentiment === "Negative" ? RED : "FF808080" } };
      row.getCell(5).value = (art.tickers || []).join(", ");
      row.alignment = { vertical: "top", wrapText: true };
      row.eachCell((cc) => { cc.border = allBorders; });
    });
    const srcRow = 5 + news.articles.length;
    nw.getCell(`A${srcRow}`).value = `Source: ${news.source || "StockNewsAPI"}`;
    nw.getCell(`A${srcRow}`).font = { italic: true, size: 9, color: { argb: "FF808080" } };
  }

  // ── download ──
  const buf = await wb.xlsx.writeBuffer();
  const blob = new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${ticker}_DCF_Model.xlsx`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  return true;
}

// JS replica of the DCF for the sensitivity grid (values only).
function computeImplied(inp, wacc, tgr) {
  if (wacc <= tgr) return null;
  let prev = inp.baseRev, pvSum = 0, ufcf5 = 0, df5 = 1;
  for (let i = 0; i < 5; i++) {
    const rev = prev * (1 + inp.growth[i]);
    const ebitda = rev * inp.margin[i];
    const da = rev * inp.daP[i];
    const ebit = ebitda - da;
    const tax = Math.max(0, ebit) * inp.tax;
    const nopat = ebit - tax;
    const capex = rev * inp.capexP[i];
    const dnwc = (rev - prev) * inp.nwcP[i];
    const ufcf = nopat + da - capex - dnwc;
    const df = 1 / Math.pow(1 + wacc, i + 1);
    pvSum += ufcf * df;
    prev = rev;
    if (i === 4) { ufcf5 = ufcf; df5 = df; }
  }
  const tv = (ufcf5 * (1 + tgr)) / (wacc - tgr);
  const ev = pvSum + tv * df5;
  const equity = ev - inp.debt + inp.cash;
  return inp.shares ? equity / inp.shares : null;
}
