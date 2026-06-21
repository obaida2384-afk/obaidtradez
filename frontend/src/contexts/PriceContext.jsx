/**
 * PriceContext — global real-time price layer.
 *
 * Polls /api/prices/batch every 2 seconds for all registered tickers.
 * Pages call usePrices(tickers) or usePrice(ticker) to subscribe.
 * Ref-counted registry: safe for multiple components watching the same ticker.
 * PriceDisplay renders price + % change with a green/red flash on each update.
 */

import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";

const BACKEND = process.env.REACT_APP_BACKEND_URL || "https://obaidtradez-backend-production.up.railway.app";
const POLL_MS = 2000;   // poll every 2 seconds
const BATCH_SIZE = 50;  // max symbols per request

const Ctx = createContext({ prices: {}, register: () => {}, unregister: () => {}, live: false });

// ─────────────────────────────────────────────────────────────────────────────

export function PriceProvider({ children }) {
  const [prices, setPrices] = useState({});
  const [live, setLive]     = useState(false);

  // ticker → ref-count map (shared mutable ref — no re-render on change)
  const registry = useRef(new Map());
  const pending  = useRef(false);

  const register = useCallback((tickers) => {
    tickers.forEach((t) => {
      const k = t.toUpperCase();
      registry.current.set(k, (registry.current.get(k) || 0) + 1);
    });
  }, []);

  const unregister = useCallback((tickers) => {
    tickers.forEach((t) => {
      const k = t.toUpperCase();
      const n = registry.current.get(k) || 0;
      if (n <= 1) registry.current.delete(k);
      else        registry.current.set(k, n - 1);
    });
  }, []);

  useEffect(() => {
    const poll = async () => {
      if (pending.current) return;
      const symbols = [...registry.current.keys()];
      if (!symbols.length) return;

      pending.current = true;
      try {
        const updates = {};
        for (let i = 0; i < symbols.length; i += BATCH_SIZE) {
          const batch = symbols.slice(i, i + BATCH_SIZE);
          const r = await fetch(`${BACKEND}/api/prices/batch`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify(batch),
          });
          if (r.ok) {
            const d = await r.json();
            if (d.prices) Object.assign(updates, d.prices);
          }
        }
        if (Object.keys(updates).length) {
          setPrices((prev) => ({ ...prev, ...updates }));
          setLive(true);
        }
      } catch {
        // silent — keep showing last known prices
      } finally {
        pending.current = false;
      }
    };

    poll();                                    // fetch immediately on mount
    const id = setInterval(poll, POLL_MS);
    return () => clearInterval(id);
  }, []);

  return (
    <Ctx.Provider value={{ prices, register, unregister, live }}>
      {children}
    </Ctx.Provider>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Hooks

/**
 * Register a list of tickers and return the live prices map.
 * Automatically unregisters on unmount.
 */
export function usePrices(tickers = []) {
  const { prices, register, unregister } = useContext(Ctx);
  const key = tickers.slice().sort().join(",");

  useEffect(() => {
    if (!tickers.length) return;
    register(tickers);
    return () => unregister(tickers);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return prices;
}

/** Subscribe to a single ticker. Returns the price object or null. */
export function usePrice(ticker) {
  const { prices, register, unregister } = useContext(Ctx);

  useEffect(() => {
    if (!ticker) return;
    register([ticker]);
    return () => unregister([ticker]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  return ticker ? (prices[ticker.toUpperCase()] ?? null) : null;
}

/** True once the first successful batch fetch completes. */
export function usePriceLive() {
  return useContext(Ctx).live;
}

// ─────────────────────────────────────────────────────────────────────────────
// UI helpers

/**
 * Renders "$214.23 +0.42%" with a green/red flash every time the price
 * ticks. Falls back to static fallbackPrice / fallbackPct when live data
 * hasn't arrived yet.
 */
export function PriceDisplay({
  ticker,
  fallbackPrice,
  fallbackPct,
  showChange = true,
  priceClass = "font-mono font-semibold text-white",
  changeClass = "",
}) {
  const live = usePrice(ticker);
  const prevRef = useRef(null);
  const [flash, setFlash] = useState(null); // "up" | "down" | null

  const price = live?.price   ?? fallbackPrice;
  const pct   = live?.change_pct ?? fallbackPct;

  useEffect(() => {
    if (live?.price == null) return;
    if (prevRef.current !== null && live.price !== prevRef.current) {
      const dir = live.price > prevRef.current ? "up" : "down";
      setFlash(dir);
      const t = setTimeout(() => setFlash(null), 700);
      return () => clearTimeout(t);
    }
    prevRef.current = live.price;
  }, [live?.price]);

  const up = (pct ?? 0) >= 0;
  const flashCls = flash === "up" ? "price-flash-up" : flash === "down" ? "price-flash-down" : "";

  return (
    <span className="inline-flex items-baseline gap-1.5">
      <span className={`${priceClass} ${flashCls}`}>
        {price != null ? `$${Number(price).toFixed(2)}` : "—"}
      </span>
      {showChange && pct != null && (
        <span className={`text-xs font-mono ${up ? "text-emerald-400" : "text-red-400"} ${changeClass}`}>
          {up ? "+" : ""}{Number(pct).toFixed(2)}%
        </span>
      )}
    </span>
  );
}

/** Pulsing green "LIVE" badge shown once real prices arrive. */
export function LiveDot({ className = "" }) {
  const live = usePriceLive();
  if (!live) return null;
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 ${className}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
      LIVE
    </span>
  );
}

/**
 * Horizontal auto-scrolling ticker strip.
 * Pass an array of { ticker, name } objects.
 */
export function TickerStrip({ tickers }) {
  const prices = usePrices(tickers.map((t) => t.ticker));
  const stripRef = useRef(null);

  // auto-scroll
  useEffect(() => {
    const el = stripRef.current;
    if (!el) return;
    let pos = 0;
    const id = setInterval(() => {
      pos += 0.5;
      if (pos >= el.scrollWidth / 2) pos = 0;
      el.scrollLeft = pos;
    }, 16);
    return () => clearInterval(id);
  }, []);

  const items = [...tickers, ...tickers]; // duplicate for seamless loop

  return (
    <div
      ref={stripRef}
      className="overflow-hidden whitespace-nowrap select-none"
      style={{ WebkitMaskImage: "linear-gradient(to right, transparent, black 6%, black 94%, transparent)" }}
    >
      {items.map((t, i) => {
        const p = prices[t.ticker];
        const up = p ? p.change_pct >= 0 : null;
        return (
          <span key={i} className="inline-flex items-center gap-2 mr-8 text-xs">
            <span className="font-mono font-bold text-slate-300">{t.ticker}</span>
            {p ? (
              <>
                <span className="font-mono text-white">${p.price.toFixed(2)}</span>
                <span className={`font-mono ${up ? "text-emerald-400" : "text-red-400"}`}>
                  {up ? "▲" : "▼"}{Math.abs(p.change_pct).toFixed(2)}%
                </span>
              </>
            ) : (
              <span className="text-slate-600">—</span>
            )}
          </span>
        );
      })}
    </div>
  );
}
