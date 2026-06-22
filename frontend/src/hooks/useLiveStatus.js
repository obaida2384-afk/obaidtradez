import { useState, useEffect } from "react";
import { fetchStatus } from "@/lib/companyUniverse";

// Reports whether the backend is serving live market data (FMP key + populated universe).
export function useLiveStatus() {
  const [status, setStatus] = useState({ live: false, fmp: false, news: false, universeCount: 0, universeUpdatedAt: null, loading: true });

  useEffect(() => {
    let active = true;
    fetchStatus()
      .then((d) => active && setStatus({ ...d, loading: false }))
      .catch(() => active && setStatus((s) => ({ ...s, loading: false })));
    return () => { active = false; };
  }, []);

  return status;
}
