import { useState, useEffect, useCallback, useRef } from "react";

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Small pulsing indicator for live data.
 */
export const LiveIndicator = ({ active }) => {
  if (!active) return null;
  return (
    <span className="inline-flex items-center ml-1">
      <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
    </span>
  );
};

/**
 * Hook for live price streaming via SSE with polling fallback.
 */
export function useLivePrices(token) {
  const [prices, setPrices] = useState({});
  const [engine, setEngine] = useState(null);
  const [reeval, setReeval] = useState(null);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef(null);
  const pollRef = useRef(null);

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const startStream = useCallback(async () => {
    try {
      await fetch(`${API}/api/live-prices/start`, { method: "POST", headers });

      const es = new EventSource(`${API}/api/live-prices/stream`);
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.prices) {
            setPrices((prev) => ({ ...prev, ...data.prices }));
          }
          if (data.engine) {
            setEngine(data.engine);
            setConnected(data.engine.ws_connected || false);
          }
          if (data.reeval) {
            setReeval(data.reeval);
          }
        } catch (e) {
          // ignore parse errors
        }
      };
      es.onerror = () => {
        es.close();
        setConnected(false);
        startPolling();
      };
      eventSourceRef.current = es;
    } catch (e) {
      startPolling();
    }
  }, [token]);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const resp = await fetch(`${API}/api/live-prices/all`, { headers });
        if (resp.ok) {
          const data = await resp.json();
          if (data.prices) setPrices(data.prices);
          if (data.engine) {
            setEngine(data.engine);
            setConnected(data.engine.ws_connected || false);
          }
        }
      } catch (e) {
        // silent
      }
    }, 3000);
  }, [token]);

  const stopStream = useCallback(async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    try {
      await fetch(`${API}/api/live-prices/stop`, { method: "POST", headers });
    } catch (e) {
      // ignore
    }
    setConnected(false);
  }, [token]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return { prices, engine, reeval, startStream, stopStream, connected };
}

/**
 * Hook for polling watchlist prices.
 */
export function useWatchlistPrices(interval = 15000, enabled = true) {
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(false);
  const pollRef = useRef(null);

  const fetchPrices = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("obaidtradez_token");
      const resp = await fetch(`${API}/api/prices/watchlist`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (resp.ok) {
        const data = await resp.json();
        setPrices(data.prices || {});
      }
    } catch (e) {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    fetchPrices();
    pollRef.current = setInterval(fetchPrices, interval);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [enabled, interval, fetchPrices]);

  return { prices, loading };
}

/**
 * Hook for polling positions prices.
 */
export function usePositionsPrices(interval = 15000, enabled = true) {
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(false);
  const pollRef = useRef(null);

  const fetchPrices = useCallback(async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("obaidtradez_token");
      const resp = await fetch(`${API}/api/prices/positions`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (resp.ok) {
        const data = await resp.json();
        setPrices(data.prices || {});
      }
    } catch (e) {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    fetchPrices();
    pollRef.current = setInterval(fetchPrices, interval);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [enabled, interval, fetchPrices]);

  return { prices, loading };
}
