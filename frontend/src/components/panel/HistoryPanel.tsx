import { useEffect, useState } from "react";

interface HistoryRecord {
  input_text: string;
  intent_action: string | null;
  success: boolean;
  message: string;
  timestamp: number;
}

interface Props {
  onRerun: (text: string) => void;
}

export function HistoryPanel({ onRerun }: Props) {
  const [items, setItems] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8765/api/history")
      .then((r) => r.json())
      .then((data) => {
        setItems(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="py-8 text-center text-sm text-[var(--color-text-secondary)]">
        Loading history...
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-[var(--color-text-secondary)]">
        No history yet
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {items.map((item, i) => (
        <div
          key={i}
          className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-white/5"
          onClick={() => onRerun(item.input_text)}
          title="Click to re-execute"
        >
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${
              item.success ? "bg-[var(--color-success)]" : "bg-[var(--color-error)]"
            }`}
          />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm text-[var(--color-text-primary)]">
              {item.input_text}
            </div>
            <div className="truncate text-xs text-[var(--color-text-secondary)]">
              {item.intent_action && (
                <span className="mr-2">{item.intent_action}</span>
              )}
              {item.message && (
                <span className="opacity-70">{item.message}</span>
              )}
            </div>
          </div>
          <span className="shrink-0 text-xs text-[var(--color-text-secondary)]">
            {formatTime(item.timestamp)}
          </span>
        </div>
      ))}
    </div>
  );
}

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  const now = new Date();
  const diff = now.getTime() - d.getTime();

  if (diff < 60_000) return "just now";
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}h ago`;

  return d.toLocaleDateString();
}
