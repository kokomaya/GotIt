import { useEffect } from "react";
import type { SearchResultItem } from "../../stores/appStore";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString();
}

interface Props {
  results: SearchResultItem[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onExecute: (index: number) => void;
}

export function ResultList({ results, selectedIndex, onSelect, onExecute }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        onSelect(Math.min(selectedIndex + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        onSelect(Math.max(selectedIndex - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        onExecute(selectedIndex);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedIndex, results.length, onSelect, onExecute]);

  if (results.length === 0) {
    return (
      <div className="py-8 text-center text-[var(--color-text-secondary)]">
        No matching files found
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {results.map((r, i) => (
        <div
          key={r.path}
          onClick={() => onSelect(i)}
          onDoubleClick={() => onExecute(i)}
          className={`flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 transition-colors ${
            i === selectedIndex
              ? "bg-[var(--color-accent)]/10 text-[var(--color-text-primary)]"
              : "hover:bg-white/5"
          }`}
        >
          <span className="text-lg">
            {r.filename.includes(".") ? "\u{1F4C4}" : "\u{1F4C1}"}
          </span>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium">{r.filename}</div>
            <div className="truncate text-xs text-[var(--color-text-secondary)]">
              {r.path}
            </div>
          </div>
          <div className="flex shrink-0 gap-3 text-xs text-[var(--color-text-secondary)]">
            {r.size > 0 && <span>{formatSize(r.size)}</span>}
            {r.modified && <span>{formatDate(r.modified)}</span>}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onExecute(i);
            }}
            className="shrink-0 rounded px-2 py-1 text-xs text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)]/20"
          >
            Open
          </button>
        </div>
      ))}
    </div>
  );
}
