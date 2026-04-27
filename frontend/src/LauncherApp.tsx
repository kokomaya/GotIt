import { useState, useEffect, useRef } from "react";
import "./index.css";
import { InputBar } from "./components/launcher/InputBar";
import { ModeIndicator } from "./components/launcher/ModeIndicator";
import { useWebSocket } from "./hooks/useWebSocket";
import { useTauriWindow } from "./hooks/useTauriWindow";

export default function LauncherApp() {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const savedInput = useRef("");
  const { submitText, fetchInputHistory, inputHistory } = useWebSocket();
  const { hideLauncher, showMain } = useTauriWindow();

  useEffect(() => {
    fetchInputHistory();
  }, [fetchInputHistory]);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    submitText(text.trim());
    setText("");
    setHistoryIndex(-1);
    await hideLauncher();
    await showMain();
  };

  const handleCancel = async () => {
    setText("");
    setHistoryIndex(-1);
    await hideLauncher();
  };

  const handleHistoryNavigate = (direction: "up" | "down") => {
    if (inputHistory.length === 0) return;

    if (direction === "up") {
      if (historyIndex === -1) {
        savedInput.current = text;
      }
      const next = Math.min(historyIndex + 1, inputHistory.length - 1);
      setHistoryIndex(next);
      setText(inputHistory[next]);
    } else {
      if (historyIndex <= 0) {
        setHistoryIndex(-1);
        setText(savedInput.current);
      } else {
        const next = historyIndex - 1;
        setHistoryIndex(next);
        setText(inputHistory[next]);
      }
    }
  };

  return (
    <div className="flex h-screen items-center justify-center">
      <div className="flex h-[52px] w-[600px] items-center rounded-2xl border border-white/10 bg-[var(--color-bg-secondary)]/80 px-3 shadow-2xl backdrop-blur-xl transition-all duration-200 hover:border-[var(--color-accent)]/30">
        <ModeIndicator
          isRecording={isRecording}
          onToggle={() => setIsRecording(!isRecording)}
        />
        <InputBar
          value={text}
          onChange={(v) => {
            setText(v);
            setHistoryIndex(-1);
          }}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          history={inputHistory}
          historyIndex={historyIndex}
          onHistoryNavigate={handleHistoryNavigate}
        />
        <button
          onClick={handleSubmit}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[var(--color-text-secondary)] transition-colors hover:bg-white/10 hover:text-[var(--color-accent)]"
          title="Submit (Enter)"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="9 10 4 15 9 20" />
            <path d="M20 4v7a4 4 0 0 1-4 4H4" />
          </svg>
        </button>
      </div>
    </div>
  );
}
