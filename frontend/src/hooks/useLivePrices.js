import { useState, useEffect, useCallback, useRef } from "react";
import { API } from "../App";

/**
 * Custom hook for live price streaming
 * @param {string[]} symbols - Array of stock symbols to track
 * @param {number} interval - Update interval in milliseconds (default: 10000 = 10s)
 * @param {boolean} enabled - Whether streaming is enabled
 * @returns {object} - { prices, loading, error, refresh }
 */
export const useLivePrices = (symbols, interval = 10000, enabled = true) => {
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchPrices = useCallback(async () => {
    if (!enabled || !symbols || symbols.length === 0) return;
    
    const token = localStorage.getItem("obaidtradez_token");
    if (!token) return;

    try {
      setLoading(true);
      const response = await fetch(`${API}/prices/batch`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(symbols)
      });

      if (response.ok && mountedRef.current) {
        const data = await response.json();
        setPrices(data.prices || {});
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err.message);
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [symbols, enabled]);

  useEffect(() => {
    mountedRef.current = true;
    
    // Initial fetch
    if (enabled && symbols?.length > 0) {
      fetchPrices();
    }

    // Set up interval
    if (enabled && interval > 0) {
      intervalRef.current = setInterval(fetchPrices, interval);
    }

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchPrices, enabled, interval, symbols?.length]);

  const refresh = useCallback(() => {
    fetchPrices();
  }, [fetchPrices]);

  return { prices, loading, error, refresh };
};

/**
 * Hook for watchlist live prices
 */
export const useWatchlistPrices = (interval = 15000, enabled = true) => {
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchPrices = useCallback(async () => {
    if (!enabled) return;
    
    const token = localStorage.getItem("obaidtradez_token");
    if (!token) return;

    try {
      setLoading(true);
      const response = await fetch(`${API}/prices/watchlist`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok && mountedRef.current) {
        const data = await response.json();
        setPrices(data.prices || {});
      }
    } catch (err) {
      console.error("Watchlist prices error:", err);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [enabled]);

  useEffect(() => {
    mountedRef.current = true;
    
    if (enabled) {
      fetchPrices();
      intervalRef.current = setInterval(fetchPrices, interval);
    }

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchPrices, enabled, interval]);

  return { prices, loading, refresh: fetchPrices };
};

/**
 * Hook for positions live prices
 */
export const usePositionsPrices = (interval = 15000, enabled = true) => {
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchPrices = useCallback(async () => {
    if (!enabled) return;
    
    const token = localStorage.getItem("obaidtradez_token");
    if (!token) return;

    try {
      setLoading(true);
      const response = await fetch(`${API}/prices/positions`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok && mountedRef.current) {
        const data = await response.json();
        setPrices(data.prices || {});
      }
    } catch (err) {
      console.error("Positions prices error:", err);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [enabled]);

  useEffect(() => {
    mountedRef.current = true;
    
    if (enabled) {
      fetchPrices();
      intervalRef.current = setInterval(fetchPrices, interval);
    }

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchPrices, enabled, interval]);

  return { prices, loading, refresh: fetchPrices };
};

/**
 * Component for displaying live price with animation
 */
export const LivePrice = ({ symbol, prices, className = "" }) => {
  const [flash, setFlash] = useState(null);
  const prevPriceRef = useRef(null);
  
  const priceData = prices?.[symbol];
  const price = priceData?.price || 0;
  const change = priceData?.change_pct || 0;
  
  useEffect(() => {
    if (prevPriceRef.current !== null && prevPriceRef.current !== price) {
      setFlash(price > prevPriceRef.current ? "up" : "down");
      const timeout = setTimeout(() => setFlash(null), 500);
      return () => clearTimeout(timeout);
    }
    prevPriceRef.current = price;
  }, [price]);

  const flashClass = flash === "up" 
    ? "bg-emerald-500/30" 
    : flash === "down" 
      ? "bg-red-500/30" 
      : "";

  return (
    <div className={`transition-all duration-300 rounded px-1 ${flashClass} ${className}`}>
      <span className="font-mono text-white">${price.toFixed(2)}</span>
      <span className={`text-xs ml-1 ${change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
        {change >= 0 ? '+' : ''}{change.toFixed(2)}%
      </span>
    </div>
  );
};

/**
 * Compact live price badge
 */
export const LivePriceBadge = ({ symbol, prices }) => {
  const priceData = prices?.[symbol];
  const price = priceData?.price || 0;
  const change = priceData?.change_pct || 0;
  const isUp = change >= 0;

  if (!price) return null;

  return (
    <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono ${
      isUp ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
    }`}>
      ${price.toFixed(2)}
      <span className="opacity-70">
        {isUp ? '↑' : '↓'}{Math.abs(change).toFixed(1)}%
      </span>
    </div>
  );
};

/**
 * Live indicator dot
 */
export const LiveIndicator = ({ active = true }) => {
  if (!active) return null;
  
  return (
    <span className="relative flex h-2 w-2">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
    </span>
  );
};

export default useLivePrices;
