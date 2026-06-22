// Institutional DCF workbook generator (ExcelJS) — multi-sheet, formula-driven,
// professionally formatted (Wall Street navy + gold). Built from the live DCF payload.

let ExcelJSModule = null;
async function getExcelJS() {
  if (ExcelJSModule) return ExcelJSModule;
  const mod = await import("exceljs");
  ExcelJSModule = mod.default || mod;
  return ExcelJSModule;
}

// ── palette (navy + gold "Wall Street Classic") ────────────────────────────────
const NAVY = "FF14213D";   // deep navy hero
const DARK = "FF1F3864";   // header navy
const SUB = "FFDCE6F1";    // light blue subheader
const GOLD = "FFC9A227";   // rich gold accent
const GOLDLT = "FFF6E7A8"; // light gold band
const CREAM = "FFFBF8EF";  // cream cell
const YEL = "FFFFF2CC";    // yellow input
const GRAY = "FFF2F2F2";   // gray formula
const GREEN = "FF1E7B34";
const RED = "FFC00000";
const WHITE = "FFFFFFFF";
const MUTE = "FF808080";
const BORDER = { style: "thin", color: { argb: "FFBFBFBF" } };
const GOLDRULE = { style: "medium", color: { argb: GOLD } };
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
    cell.border = { ...allBorders, bottom: opts.sub ? BORDER : GOLDRULE };
  });
  r.height = opts.height || 20;
  return r;
}

function pct(v) { return v == null ? null : v / 100; }
const recColor = (rec) => /Strong Buy|^Buy/.test(rec || "") ? GREEN : /Avoid|Not a Good|Sell/.test(rec || "") ? RED : GOLD;

export async function generateExcelModel(model) {
  const ExcelJS = await getExcelJS();
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
  const cover = wb.addWorksheet("Cover", { properties: { tabColor: { argb: GOLD } }, views: [{ showGridLines: false }] });
  cover.columns = [{ width: 3 }, { width: 26 }, { width: 22 }, { width: 22 }, { width: 16 }];
  // navy hero band
  for (let rr = 1; rr <= 5; rr++) {
    cover.getRow(rr).height = rr === 2 ? 30 : rr === 3 ? 22 : 16;
    for (let cc = 1; cc <= 5; cc++) cover.getCell(rr, cc).fill = fill(NAVY);
  }
  cover.mergeCells("B2:E2");
  cover.getCell("B2").value = "ALPHA VAULT  ·  EQUITY RESEARCH";
  cover.getCell("B2").font = { bold: true, size: 20, color: { argb: WHITE } };
  cover.getCell("B2").alignment = { vertical: "middle" };
  cover.mergeCells("B3:E3");
  cover.getCell("B3").value = "Discounted Cash Flow Valuation Model";
  cover.getCell("B3").font = { italic: true, size: 11, color: { argb: GOLDLT } };
  // gold rule
  for (let cc = 1; cc <= 5; cc++) cover.getCell(6, cc).fill = fill(GOLD);
  cover.getRow(6).height = 4;

  // company title + rating badge
  cover.getCell("B8").value = `${company.name || ticker}  (${ticker})`;
  cover.getCell("B8").font = { bold: true, size: 16, color: { argb: DARK } };
  cover.mergeCells("B8:D8");
  const badge = cover.getCell("E8");
  badge.value = (model.recommendation || "—").toUpperCase();
  badge.fill = fill(recColor(model.recommendation));
  badge.font = { bold: true, size: 12, color: { argb: WHITE } };
  badge.alignment = { horizontal: "center", vertical: "middle" };
  badge.border = allBorders;
  cover.getRow(8).height = 26;

  const coverRows = [
    ["Sector", company.sector],
    ["Industry", company.industry],
    ["Current Price", company.price != null ? `$${company.price}` : "—"],
    ["Analyst Consensus", analyst?.consensus || "—"],
    ["Consensus Target", analyst?.targetConsensus != null ? `$${analyst.targetConsensus}` : "—"],
    ["Target Range", analyst?.targetLow != null ? `$${analyst.targetLow} – $${analyst.targetHigh}` : "—"],
    ["Implied Upside (Analyst)", analyst?.impliedUpside != null ? `${analyst.impliedUpside}%` : "—"],
    ["Model Date", new Date().toISOString().slice(0, 10)],
    ["Live Price As Of", model.priceAsOf ? new Date(model.priceAsOf).toLocaleString() : "—"],
  ];
  coverRows.forEach(([k, val], i) => {
    const row = 10 + i;
    const kc = cover.getCell(`B${row}`);
    kc.value = k; kc.font = { bold: true, color: { argb: DARK } };
    kc.fill = fill(i % 2 ? CREAM : WHITE); kc.border = allBorders;
    cover.mergeCells(`C${row}:E${row}`);
    const vc = cover.getCell(`C${row}`);
    vc.value = val == null ? "—" : val;
    vc.alignment = { horizontal: "right" };
    vc.fill = fill(i % 2 ? CREAM : WHITE);
    cover.getCell(`D${row}`).fill = fill(i % 2 ? CREAM : WHITE);
    cover.getCell(`E${row}`).fill = fill(i % 2 ? CREAM : WHITE);
    cover.getCell(`E${row}`).border = { right: BORDER };
  });
  const disc = 10 + coverRows.length + 1;
  cover.mergeCells(`B${disc}:E${disc}`);
  cover.getCell(`B${disc}`).value = "Educational research only. Not investment advice. Outputs depend on assumptions, which are uncertain.";
  cover.getCell(`B${disc}`).font = { italic: true, size: 9, color: { argb: MUTE } };

  // ════════════════════════ DCF MODEL (formula-driven) ════════════════════════
  const ws = wb.addWorksheet("DCF Model", { properties: { tabColor: { argb: DARK } }, views: [{ showGridLines: false }] });
  ws.columns = [{ width: 30 }, { width: 14 }, { width: 14 }, { width: 14 }, { width: 14 }, { width: 14 }, { width: 14 }];
  ws.mergeCells("A1:G1");
  ws.getCell("A1").value = `${company.name} (${ticker}) — DCF Model`;
  ws.getCell("A1").font = { bold: true, size: 14, color: { argb: WHITE } };
  ws.getCell("A1").fill = fill(NAVY);
  ws.getCell("A1").border = { bottom: GOLDRULE };
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
  const set = (label, formula, fmt, color, gold) => {
    v += 1;
    ws.getCell(`A${v}`).value = label;
    const c = ws.getCell(`C${v}`);
    c.value = { formula };
    c.numFmt = fmt;
    c.font = { bold: true, color: color ? { argb: color } : undefined };
    c.fill = fill(gold ? GOLDLT : GRAY);
    c.border = allBorders;
    c.alignment = { horizontal: "right" };
    return v;
  };
  const sumPV = set("PV of Forecast UFCF ($M)", `SUM(C${PV}:G${PV})`, usd);
  const tv = set("Terminal Value ($M, Gordon)", `G${UFCF}*(1+$C$8)/($C$7-$C$8)`, usd);
  const pvtv = set("PV of Terminal Value ($M)", `C${tv}*G${DF}`, usd);
  const ev = set("Enterprise Value ($M)", `C${sumPV}+C${pvtv}`, usd);
  const eq = set("(–) Debt (+) Cash → Equity ($M)", `C${ev}-$C$9+$C$10`, usd);
  const impl = set("Implied Value / Share", `C${eq}/$C$11`, ps, GREEN, true);
  set("Implied Upside / (Downside)", `C${impl}/$C$12-1`, pf, undefined, true);

  v += 2;
  ws.getCell(`A${v}`).value = "Recommendation";
  ws.getCell(`A${v}`).font = { bold: true };
  const recCell = ws.getCell(`C${v}`);
  recCell.value = model.recommendation || "—";
  recCell.font = { bold: true, color: { argb: WHITE } };
  recCell.fill = fill(recColor(model.recommendation));
  recCell.border = allBorders;
  recCell.alignment = { horizontal: "right" };

  // shared JS inputs for scenario + sensitivity
  const jsInputs = { baseRev, growth: growth.map((x) => x / 100), margin: margin.map((x) => x / 100), daP: daP.map((x) => x / 100), capexP: capexP.map((x) => x / 100), nwcP: nwcP.map((x) => x / 100), tax: (a.taxRate ?? 21) / 100, debt: a.debt ?? 0, cash: a.cash ?? 0, shares: a.sharesOut || 1 };
  const baseW = (a.wacc ?? 9) / 100, baseT = (a.tgr ?? 3) / 100;

  // ════════════════════════ SCENARIO ANALYSIS (Bull/Base/Bear) + Football Field ═══
  buildScenarioSheet(wb, { company, analyst, jsInputs, baseW, baseT, recommendation: model.recommendation });

  // ════════════════════════ HISTORICAL FINANCIALS ════════════════════════
  if (hist?.rows?.length) {
    const h = wb.addWorksheet("Historical Financials", { views: [{ showGridLines: false }] });
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
      row.getCell(1).font = { bold: true, color: { argb: DARK } };
      hist.rows.forEach((x, ci) => {
        const c = row.getCell(2 + ci);
        c.value = key.includes("Margin") ? pct(x[key]) : x[key];
        c.numFmt = fmt;
        c.alignment = { horizontal: "right" };
        c.border = allBorders;
        if (li % 2) c.fill = fill(CREAM);
      });
    });
    h.getCell(`A${3 + lines.length}`).value = `Source: ${hist.source}`;
    h.getCell(`A${3 + lines.length}`).font = { italic: true, size: 9, color: { argb: MUTE } };
  }

  // ════════════════════════ SENSITIVITY (green→red color scale) ════════════════════════
  const sens = wb.addWorksheet("Sensitivity", { views: [{ showGridLines: false }] });
  sens.columns = [{ width: 16 }, { width: 12 }, { width: 12 }, { width: 12 }, { width: 12 }, { width: 12 }];
  sens.mergeCells("A1:F1");
  sens.getCell("A1").value = "Implied Value / Share — WACC (rows) vs Terminal Growth (cols)";
  sens.getCell("A1").font = { bold: true, color: { argb: WHITE } };
  sens.getCell("A1").fill = fill(NAVY);
  sens.getCell("A1").border = { bottom: GOLDRULE };
  const waccs = [-0.015, -0.0075, 0, 0.0075, 0.015].map((d) => baseW + d);
  const tgrs = [0.02, 0.025, 0.03, 0.035, 0.04];
  sens.getRow(3).getCell(1).value = "WACC \\ TGR";
  tgrs.forEach((t, i) => { const c = sens.getRow(3).getCell(2 + i); c.value = t; c.numFmt = pf; c.fill = fill(SUB); c.font = { bold: true, color: { argb: DARK } }; c.alignment = { horizontal: "right" }; });
  waccs.forEach((w, wi) => {
    const row = sens.getRow(4 + wi);
    const lc = row.getCell(1); lc.value = w; lc.numFmt = pf; lc.fill = fill(SUB); lc.font = { bold: true, color: { argb: DARK } };
    tgrs.forEach((t, ti) => {
      const c = row.getCell(2 + ti);
      c.value = computeImplied(jsInputs, w, t);
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
    const cw = wb.addWorksheet("Comparables", { views: [{ showGridLines: false }] });
    cw.columns = [{ width: 10 }, { width: 28 }, { width: 14 }, { width: 10 }, { width: 12 }, { width: 10 }, { width: 12 }, { width: 12 }];
    headerRow(cw, 1, ["Ticker", "Company", "Mkt Cap ($M)", "P/E", "EV/EBITDA", "P/S", "Rev Gr.", "EBITDA M."]);
    comps.rows.forEach((row, i) => {
      const rr = cw.getRow(2 + i);
      rr.values = [row.ticker, row.name, row.marketCap, row.pe, row.evEbitda, row.ps, row.revenueGrowth != null ? row.revenueGrowth / 100 : null, row.ebitdaMargin != null ? row.ebitdaMargin / 100 : null];
      rr.getCell(3).numFmt = usd; rr.getCell(7).numFmt = pf; rr.getCell(8).numFmt = pf;
      if (row.isTarget) rr.eachCell((c) => { c.fill = fill(GOLDLT); c.font = { bold: true }; });
      else if (i % 2) rr.eachCell((c) => { c.fill = fill(CREAM); });
      rr.eachCell((c) => { c.border = allBorders; });
    });
    const mr = cw.getRow(3 + comps.rows.length);
    mr.getCell(2).value = "Peer Median"; mr.getCell(2).font = { bold: true };
    mr.getCell(4).value = comps.medianPe; mr.getCell(5).value = comps.medianEvEbitda;
  }

  // ════════════════════════ ANALYST & MACRO ════════════════════════
  const am = wb.addWorksheet("Analyst & Macro", { views: [{ showGridLines: false }] });
  am.columns = [{ width: 26 }, { width: 22 }];
  headerRow(am, 1, ["Analyst Recommendations", ""]);
  const amRows = [
    ["Consensus", analyst?.consensus], ["Strong Buy", analyst?.strongBuy], ["Buy", analyst?.buy],
    ["Hold", analyst?.hold], ["Sell", analyst?.sell], ["Strong Sell", analyst?.strongSell],
    ["Target (Consensus)", analyst?.targetConsensus != null ? `$${analyst.targetConsensus}` : "—"],
    ["Target Range", analyst ? `$${analyst.targetLow}–$${analyst.targetHigh}` : "—"],
    ["Implied Upside", analyst?.impliedUpside != null ? `${analyst.impliedUpside}%` : "—"],
  ];
  amRows.forEach(([k, val], i) => { const row = am.getRow(2 + i); row.getCell(1).value = k; row.getCell(1).font = { bold: true }; row.getCell(2).value = val == null ? "—" : val; row.getCell(2).alignment = { horizontal: "right" }; });
  let mrow = 2 + amRows.length + 1;
  headerRow(am, mrow, ["Macro (Treasury / WACC inputs)", ""]);
  const macroRows = [
    ["Risk-Free (10Y UST)", macro?.riskFreeRate10y != null ? `${macro.riskFreeRate10y}%` : "—"],
    ["As Of", macro?.asOf || "—"],
    ...Object.entries(macro?.yieldCurve || {}).map(([k, vv]) => [k, `${vv}%`]),
  ];
  macroRows.forEach(([k, val], i) => { const row = am.getRow(mrow + 1 + i); row.getCell(1).value = k; row.getCell(1).font = { bold: true }; row.getCell(2).value = val; row.getCell(2).alignment = { horizontal: "right" }; });

  // ════════════════════════ ASSUMPTIONS (sources) ════════════════════════
  if (a.meta) {
    const as = wb.addWorksheet("Assumptions", { views: [{ showGridLines: false }] });
    as.columns = [{ width: 22 }, { width: 40 }, { width: 50 }, { width: 12 }];
    headerRow(as, 1, ["Assumption", "Source", "Reasoning", "Confidence"]);
    Object.entries(a.meta).forEach(([k, m], i) => {
      const row = as.getRow(2 + i);
      row.getCell(1).value = k; row.getCell(1).font = { bold: true };
      row.getCell(2).value = m.source; row.getCell(3).value = m.reasoning;
      const cc = row.getCell(4); cc.value = m.confidence;
      cc.font = { bold: true, color: { argb: m.confidence === "High" ? GREEN : m.confidence === "Low" ? RED : DARK } };
      row.eachCell((c) => { c.alignment = { vertical: "top", wrapText: true }; c.border = allBorders; });
    });
  }

  // ════════════════════════ INVESTMENT MEMO ════════════════════════
  const mw = wb.addWorksheet("Investment Memo", { views: [{ showGridLines: false }] });
  mw.columns = [{ width: 100 }];
  mw.getCell("A1").value = memo?.headline || `${company.name} (${ticker}) — Investment Memo`;
  mw.getCell("A1").font = { bold: true, size: 13, color: { argb: WHITE } };
  mw.getCell("A1").fill = fill(NAVY);
  mw.getCell("A1").border = { bottom: GOLDRULE };
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
  mw.getCell(`A${dr}`).font = { italic: true, size: 9, color: { argb: MUTE } };

  // ════════════════════════ NEWS & CATALYSTS ════════════════════════
  const news = model.news;
  if (news?.articles?.length) {
    const nw = wb.addWorksheet("News & Catalysts", { properties: { tabColor: { argb: DARK } }, views: [{ showGridLines: false }] });
    nw.columns = [{ width: 20 }, { width: 66 }, { width: 20 }, { width: 12 }, { width: 16 }];
    const sent = news.sentiment || {};
    nw.mergeCells("A1:E1");
    nw.getCell("A1").value = `${ticker} — News & Catalysts  (Tone: ${sent.tone || "Neutral"} · ${sent.positive || 0} positive / ${sent.negative || 0} negative)`;
    nw.getCell("A1").font = { bold: true, size: 13, color: { argb: WHITE } };
    nw.getCell("A1").fill = fill(NAVY);
    nw.getCell("A1").border = { bottom: GOLDRULE };
    nw.getRow(1).height = 24;
    headerRow(nw, 3, ["Date", "Headline", "Source", "Sentiment", "Tickers"], { sub: true });
    news.articles.forEach((art, i) => {
      const row = nw.getRow(4 + i);
      row.getCell(1).value = art.date || "—";
      if (art.url) {
        row.getCell(2).value = { text: art.title || "", hyperlink: art.url };
        row.getCell(2).font = { color: { argb: DARK }, underline: true };
      } else {
        row.getCell(2).value = art.title || "";
      }
      row.getCell(3).value = art.source || "—";
      const sc = row.getCell(4);
      sc.value = art.sentiment || "Neutral";
      sc.font = { bold: true, color: { argb: art.sentiment === "Positive" ? GREEN : art.sentiment === "Negative" ? RED : MUTE } };
      row.getCell(5).value = (art.tickers || []).join(", ");
      row.alignment = { vertical: "top", wrapText: true };
      row.eachCell((cc) => { cc.border = allBorders; });
    });
    const srcRow = 5 + news.articles.length;
    nw.getCell(`A${srcRow}`).value = `Source: ${news.source || "StockNewsAPI"}`;
    nw.getCell(`A${srcRow}`).font = { italic: true, size: 9, color: { argb: MUTE } };
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

// ── Scenario Analysis (Bull / Base / Bear) + football-field valuation ──────────
function buildScenarioSheet(wb, { company, analyst, jsInputs, baseW, baseT, recommendation }) {
  const usd = "#,##0", pf = "0.0%", ps = "$#,##0.00";
  const price = company.price || 0;
  const sc = wb.addWorksheet("Scenario Analysis", { properties: { tabColor: { argb: GOLD } }, views: [{ showGridLines: false }] });
  sc.columns = [{ width: 30 }].concat(Array.from({ length: 30 }, () => ({ width: 3.4 })));

  sc.mergeCells("A1:AE1");
  sc.getCell("A1").value = `${company.name || company.ticker} — Scenario Analysis & Valuation Range`;
  sc.getCell("A1").font = { bold: true, size: 14, color: { argb: WHITE } };
  sc.getCell("A1").fill = fill(NAVY);
  sc.getCell("A1").border = { bottom: GOLDRULE };
  sc.getRow(1).height = 26;

  // scenario tweaks
  const cap = (arr, lo, hi) => arr.map((x) => Math.min(hi, Math.max(lo, x)));
  const mk = (gMul, mAdj, wAdj, tAdj) => ({
    ...jsInputs,
    growth: cap(jsInputs.growth.map((g) => g * gMul), -0.1, 0.6),
    margin: cap(jsInputs.margin.map((m) => m + mAdj), 0.01, 0.7),
  });
  const bear = computeImplied(mk(0.6, -0.02), baseW + 0.015, Math.max(0.005, baseT - 0.005));
  const base = computeImplied(jsInputs, baseW, baseT);
  const bull = computeImplied(mk(1.3, 0.015), Math.max(0.04, baseW - 0.01), baseT + 0.005);

  const upPct = (val) => (price && val != null ? val / price - 1 : null);
  const cards = [
    ["Bear Case", bear, RED, "Growth −40%, margins −200bps, WACC +150bps"],
    ["Base Case", base, DARK, "Live analyst-driven assumptions"],
    ["Bull Case", bull, GREEN, "Growth +30%, margins +150bps, WACC −100bps"],
  ];
  // header
  const hdr = sc.getRow(3); hdr.height = 20;
  const hdrCells = [[1, "Scenario"], [2, "Implied / Share"], [6, "Upside"], [9, "Key Assumptions"]];
  for (let cc = 1; cc <= 31; cc++) { const c = hdr.getCell(cc); c.fill = fill(SUB); c.border = { ...allBorders, bottom: BORDER }; }
  hdrCells.forEach(([col, t]) => { const c = hdr.getCell(col); c.value = t; c.font = { bold: true, color: { argb: DARK } }; });
  cards.forEach(([label, val, color, note], i) => {
    const row = sc.getRow(4 + i);
    const lc = row.getCell(1); lc.value = label; lc.font = { bold: true, color: { argb: color } }; lc.border = allBorders;
    sc.mergeCells(`B${4 + i}:E${4 + i}`);
    const vc = row.getCell(2); vc.value = val; vc.numFmt = ps; vc.font = { bold: true }; vc.alignment = { horizontal: "right" }; vc.border = allBorders; vc.fill = fill(i % 2 ? CREAM : WHITE);
    sc.getCell(`C${4 + i}`).fill = fill(i % 2 ? CREAM : WHITE);
    sc.getCell(`D${4 + i}`).fill = fill(i % 2 ? CREAM : WHITE);
    sc.getCell(`E${4 + i}`).fill = fill(i % 2 ? CREAM : WHITE);
    sc.mergeCells(`F${4 + i}:H${4 + i}`);
    const uc = row.getCell(6); const up = upPct(val);
    uc.value = up; uc.numFmt = pf; uc.alignment = { horizontal: "right" };
    uc.font = { bold: true, color: { argb: up != null && up >= 0 ? GREEN : RED } }; uc.border = allBorders;
    sc.getCell(`G${4 + i}`).border = { bottom: BORDER, top: BORDER }; sc.getCell(`H${4 + i}`).border = { right: BORDER, bottom: BORDER, top: BORDER };
    sc.mergeCells(`I${4 + i}:AE${4 + i}`);
    const nc = row.getCell(9); nc.value = note; nc.font = { italic: true, size: 10, color: { argb: MUTE } }; nc.alignment = { vertical: "middle" };
  });
  // current price row
  const pr = sc.getRow(7);
  pr.getCell(1).value = "Current Price"; pr.getCell(1).font = { bold: true, color: { argb: GOLD } }; pr.getCell(1).border = allBorders;
  sc.mergeCells("B7:E7");
  pr.getCell(2).value = price; pr.getCell(2).numFmt = ps; pr.getCell(2).font = { bold: true }; pr.getCell(2).alignment = { horizontal: "right" }; pr.getCell(2).border = allBorders; pr.getCell(2).fill = fill(GOLDLT);
  ["C7", "D7", "E7"].forEach((a) => sc.getCell(a).fill = fill(GOLDLT));

  // ── Football field ──
  sc.mergeCells("A9:AE9");
  sc.getCell("A9").value = "Valuation Football Field";
  sc.getCell("A9").font = { bold: true, size: 12, color: { argb: WHITE } };
  sc.getCell("A9").fill = fill(DARK);
  sc.getCell("A9").border = { bottom: GOLDRULE };
  sc.getRow(9).height = 20;

  const ranges = [];
  if (bear != null && bull != null) ranges.push({ label: "DCF (Bear→Bull)", lo: Math.min(bear, bull), hi: Math.max(bear, bull), color: DARK });
  if (analyst?.targetLow != null && analyst?.targetHigh != null) ranges.push({ label: "Analyst Target", lo: analyst.targetLow, hi: analyst.targetHigh, color: GOLD });
  if (company.fiftyTwoWeekLow != null && company.fiftyTwoWeekHigh != null) ranges.push({ label: "52-Week Range", lo: company.fiftyTwoWeekLow, hi: company.fiftyTwoWeekHigh, color: "FF7F7F7F" });

  if (ranges.length) {
    const allVals = ranges.flatMap((r) => [r.lo, r.hi]).concat(price || []);
    let lo = Math.min(...allVals), hi = Math.max(...allVals);
    const pad = (hi - lo) * 0.08 || hi * 0.08 || 1;
    lo = Math.max(0, lo - pad); hi = hi + pad;
    const N = 28; // axis columns B..AC (2..29)
    const colFor = (val) => 2 + Math.round(((val - lo) / (hi - lo)) * (N - 1));
    const priceCol = price ? colFor(price) : null;

    let fr = 11;
    ranges.forEach((rg, i) => {
      const row = sc.getRow(fr + i);
      row.height = 18;
      row.getCell(1).value = rg.label;
      row.getCell(1).font = { bold: true, size: 10, color: { argb: DARK } };
      const c1 = colFor(rg.lo), c2 = colFor(rg.hi);
      for (let cc = 2; cc <= N + 1; cc++) {
        const cell = row.getCell(cc);
        if (cc >= c1 && cc <= c2) cell.fill = fill(rg.color);
        else cell.fill = fill("FFF2F2F2");
        if (priceCol && cc === priceCol) cell.fill = fill(GOLD); // price marker
      }
      // labels
      row.getCell(N + 3).value = `$${rg.lo.toFixed(0)} – $${rg.hi.toFixed(0)}`;
      row.getCell(N + 3).font = { size: 10, color: { argb: MUTE } };
    });
    const legRow = fr + ranges.length + 1;
    sc.getCell(`A${legRow}`).value = "Gold marker = current price.  Axis: " + `$${lo.toFixed(0)} → $${hi.toFixed(0)}`;
    sc.getCell(`A${legRow}`).font = { italic: true, size: 9, color: { argb: MUTE } };
    sc.mergeCells(`A${legRow}:AE${legRow}`);
  }
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
