import { useState, useEffect } from "react";
import { api } from "./useApi";

export function useSystemStatus(interval = 10000) {
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try { setStatus(await api.get("/status")); } catch {}
    };
    load();
    const id = setInterval(load, interval);
    return () => clearInterval(id);
  }, [interval]);

  return { status };
}
