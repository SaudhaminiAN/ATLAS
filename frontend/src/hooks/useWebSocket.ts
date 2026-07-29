import { useCallback, useEffect, useRef, useState } from "react";
import { getAccessToken } from "../lib/api";

export type WsStatus = "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketOptions<T> {
  channel: string;
  onMessage: (payload: T) => void;
  enabled?: boolean;
}

function wsBaseUrl(): string {
  const api = import.meta.env.VITE_API_URL as string | undefined;
  if (api) {
    const url = new URL(api);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url.origin;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

export function useWebSocket<T>({
  channel,
  onMessage,
  enabled = true,
}: UseWebSocketOptions<T>) {
  const [status, setStatus] = useState<WsStatus>("disconnected");
  const onMessageRef = useRef(onMessage);
  const reconnectAttempt = useRef(0);
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (!enabled) return;

    const token = getAccessToken();
    const tokenQuery = token ? `&access_token=${encodeURIComponent(token)}` : "";
    const url = `${wsBaseUrl()}/api/v1/ws?channel=${encodeURIComponent(channel)}${tokenQuery}`;
    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      reconnectAttempt.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as { payload: T };
        onMessageRef.current(data.payload);
      } catch {
        /* ignore malformed */
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      wsRef.current = null;
      const delay = Math.min(1000 * 2 ** reconnectAttempt.current, 30000);
      reconnectAttempt.current += 1;
      timerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      setStatus("error");
      ws.close();
    };
  }, [channel, enabled]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { status };
}
