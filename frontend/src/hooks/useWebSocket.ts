import { useCallback, useEffect, useRef } from "react";
import { useAppStore } from "../stores/appStore";

const WS_URL = "ws://127.0.0.1:8765/ws/pipeline";
const RECONNECT_DELAY = 2000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number>(0);

  const submitInput = useAppStore((s) => s.submitInput);
  const onTranscript = useAppStore((s) => s.onTranscript);
  const onIntent = useAppStore((s) => s.onIntent);
  const onResults = useAppStore((s) => s.onResults);
  const onExecuted = useAppStore((s) => s.onExecuted);
  const onError = useAppStore((s) => s.onError);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      switch (msg.type) {
        case "transcript":
          onTranscript(msg.data.text, msg.data.partial);
          break;
        case "intent":
          onIntent(msg.data);
          break;
        case "results":
          onResults(msg.data);
          break;
        case "executed":
          onExecuted(msg.data);
          break;
        case "error":
          onError(msg.data.message);
          break;
      }
    };

    ws.onclose = () => {
      reconnectTimer.current = window.setTimeout(connect, RECONNECT_DELAY);
    };
  }, [onTranscript, onIntent, onResults, onExecuted, onError]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((type: string, data?: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, data }));
    }
  }, []);

  const submitText = useCallback(
    (text: string) => {
      submitInput(text);
      send("submit_text", { text });
    },
    [send, submitInput],
  );

  const executeResult = useCallback(
    (index: number) => send("execute", { index }),
    [send],
  );

  const cancel = useCallback(() => send("cancel"), [send]);

  return { submitText, executeResult, cancel, isConnected: () => wsRef.current?.readyState === WebSocket.OPEN };
}
