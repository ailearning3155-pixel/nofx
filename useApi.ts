import axios from "axios";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: BASE, timeout: 15000 });

import { useState, useEffect, useCallback } from "react";

export function useFetch<T = any>(url: string, interval?: number) {
  const [data,    setData]    = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<T>(url);
      setData(res.data);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Error");
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    fetch();
    if (interval) {
      const id = setInterval(fetch, interval);
      return () => clearInterval(id);
    }
  }, [fetch, interval]);

  return { data, loading, error, refresh: fetch };
}
