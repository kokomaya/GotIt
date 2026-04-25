import "./index.css";
import { useAppStore } from "./stores/appStore";
import { useWebSocket } from "./hooks/useWebSocket";
import { PipelineProgress } from "./components/panel/PipelineProgress";
import { ResultList } from "./components/panel/ResultList";
import { ActionFeedback } from "./components/panel/ActionFeedback";

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

  const { executeResult } = useWebSocket();

  if (phase === "dormant") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--color-bg-primary)]">
        <h1 className="text-2xl font-bold text-[var(--color-accent)]">GotIt</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          Waiting for input...
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-bg-primary)]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-3">
        <h1 className="text-base font-semibold text-[var(--color-accent)]">GotIt</h1>
        <button
          onClick={reset}
          className="rounded px-2 py-1 text-xs text-[var(--color-text-secondary)] transition-colors hover:bg-white/10"
          title="Close (Esc)"
        >
          Close
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 px-5 py-4">
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
      </div>
    </div>
  );
}
