import { useState } from "react";
import "./index.css";
import { InputBar } from "./components/launcher/InputBar";
import { ModeIndicator } from "./components/launcher/ModeIndicator";
import { useWebSocket } from "./hooks/useWebSocket";

export default function LauncherApp() {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const { submitText } = useWebSocket();

  const handleSubmit = () => {
    if (!text.trim()) return;
    submitText(text.trim());
    setText("");
  };

  const handleCancel = () => {
    setText("");
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
          onChange={setText}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
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
