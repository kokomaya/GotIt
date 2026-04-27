import { useState } from "react";
import "./index.css";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { useAppStore } from "./stores/appStore";
import { useWebSocket } from "./hooks/useWebSocket";
import { WindowControls } from "./components/panel/WindowControls";
import { PipelineProgress } from "./components/panel/PipelineProgress";
import { ResultList } from "./components/panel/ResultList";
import { ActionFeedback } from "./components/panel/ActionFeedback";
import { HistoryPanel } from "./components/panel/HistoryPanel";

function handleDragStart(e: React.PointerEvent) {
  if ("__TAURI__" in window) {
    e.preventDefault();
    getCurrentWindow().startDragging();
  }
}

type Tab = "current" | "history";

export default function App() {
  const {
    phase,
    inputText,
    intent,
    results,
    selectedIndex,
    execution,
    error,
    stages,
    setSelectedIndex,
    reset,
  } = useAppStore();

  const { submitText, executeResult } = useWebSocket();
  const [activeTab, setActiveTab] = useState<Tab>("current");

  const handleRerun = (text: string) => {
    setActiveTab("current");
    submitText(text);
  };

  if (phase === "dormant") {
    return (
      <div
        className="relative flex min-h-screen flex-col items-center justify-center bg-[var(--color-bg-primary)]"
        onPointerDown={handleDragStart}
      >
        <h1 className="text-2xl font-bold text-[var(--color-accent)]">GotIt</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          Waiting for input...
        </p>
        <div className="absolute right-2 top-2">
          <WindowControls onClose={reset} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-bg-primary)]">
      {/* Header — draggable title bar */}
      <div
        className="flex items-center border-b border-white/10 px-5 py-2"
        onPointerDown={handleDragStart}
      >
        <h1 className="text-base font-semibold text-[var(--color-accent)]">
          GotIt
        </h1>
        {/* Tab switcher */}
        <div className="ml-6 flex gap-1">
          <button
            onClick={() => setActiveTab("current")}
            className={`rounded px-3 py-1 text-xs transition-colors ${
              activeTab === "current"
                ? "bg-white/10 text-[var(--color-text-primary)]"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            Current
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`rounded px-3 py-1 text-xs transition-colors ${
              activeTab === "history"
                ? "bg-white/10 text-[var(--color-text-primary)]"
                : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
            }`}
          >
            History
          </button>
        </div>
        <div className="ml-auto">
          <WindowControls onClose={reset} />
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {activeTab === "history" ? (
          <HistoryPanel onRerun={handleRerun} />
        ) : (
          <>
            {/* Input display + progress */}
            <div className="mb-4 flex items-center justify-between">
              <span className="text-sm text-[var(--color-text-secondary)]">
                &ldquo;{inputText}&rdquo;
              </span>
              <PipelineProgress stages={stages} />
            </div>

            {/* Intent info */}
            {intent && (
              <div className="mb-3 rounded-lg bg-[var(--color-bg-surface)] px-4 py-2 text-xs text-[var(--color-text-secondary)]">
                <span className="font-medium text-[var(--color-text-primary)]">
                  {intent.action}
                </span>
                {intent.query && <span className="ml-2">query: {intent.query}</span>}
                {intent.target && <span className="ml-2">target: {intent.target}</span>}
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="mb-3 rounded-lg bg-[var(--color-error)]/10 px-4 py-3 text-sm text-[var(--color-error)]">
                {error}
              </div>
            )}

            {/* Results */}
            {results.length > 0 && (
              <ResultList
                results={results}
                selectedIndex={selectedIndex}
                onSelect={setSelectedIndex}
                onExecute={executeResult}
              />
            )}

            {/* Processing state */}
            {phase === "processing" && results.length === 0 && !error && (
              <div className="flex items-center justify-center py-12">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-accent)] border-t-transparent" />
                <span className="ml-3 text-sm text-[var(--color-text-secondary)]">
                  Processing...
                </span>
              </div>
            )}

            {/* Execution feedback */}
            {execution && <ActionFeedback execution={execution} />}
          </>
        )}
      </div>
    </div>
  );
}
