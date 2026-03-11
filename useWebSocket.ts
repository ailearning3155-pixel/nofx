import { useState, useEffect, useRef, useCallback } from "react";

export function useWebSocket(path = "/ws/prices") {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}${path}`);
    ws.onopen    = () => setConnected(true);
    ws.onclose   = () => { setConnected(false); setTimeout(connect, 3000); };
    ws.onerror   = () => ws.close();
    ws.onmessage = (e) => {
      try { setMessages(prev => [...prev.slice(-99), JSON.parse(e.data)]); }
      catch {}
    };
    wsRef.current = ws;
  }, [path]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { connected, messages };
}
