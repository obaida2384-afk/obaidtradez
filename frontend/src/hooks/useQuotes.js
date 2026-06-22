import { useState, useEffect } from "react";
import { fetchQuotes } from "@/lib/companyUniverse";

// Polls live batch quotes for the given tickers and returns a {ticker: {price,change,changePct}} map.
export function useQuotes(tickers, intervalMs = 20000) {
  const [prices, setPrices] = useState({});
  const key = (tickers || []).slice(0, 60).join(",");

  useEffect(() => {
    if (!key) return;
    let active = true;
    const syms = key.split(",");
    const load = async () => {
      try {
        const data = await fetchQuotes(syms);
        if (active && data?.prices) setPrices(data.prices);
      } catch (_) { /* keep last known */ }
    };
    load();
    const id = setInterval(load, intervalMs);
    return () => { active = false; clearInterval(id); };
  }, [key, intervalMs]);

  return prices;
}
