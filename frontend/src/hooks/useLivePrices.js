import { useState, useEffect, useCallback, useRef } from "react";

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Hook for live price streaming via SSE with polling fallback.
 * Returns: { prices, engine, startStream, stopStream, connected }
 */
export function useLivePrices(token) {
  const [prices, setPrices] = useState({});
  const [engine, setEngine] = useState(null);
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef(null);
  const pollRef = useRef(null);

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const startStream = useCallback(async () => {
    try {
      // Start the backend engine first
      await fetch(`${API}/live-prices/start`, { method: "POST", headers });

      // Try SSE stream
      const es = new EventSource(`${API}/live-prices/stream`);
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
        } catch (e) {
          // ignore parse errors
        }
      };
      es.onerror = () => {
        // SSE failed — fall back to polling
        es.close();
        setConnected(false);
        startPolling();
      };
      eventSourceRef.current = es;
    } catch (e) {
      // Fallback to polling
      startPolling();
    }
  }, [token]);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const resp = await fetch(`${API}/live-prices/all`, { headers });
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
      await fetch(`${API}/live-prices/stop`, { method: "POST", headers });
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

  return { prices, engine, startStream, stopStream, connected };
}
