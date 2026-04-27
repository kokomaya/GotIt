import { useEffect, useMemo, useState } from "react";
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

type SortKey = "name" | "path" | "size" | "modified";
type SortDir = "asc" | "desc";

interface Props {
  results: SearchResultItem[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onExecute: (index: number) => void;
}

export function ResultList({ results, selectedIndex, onSelect, onExecute }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("modified");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    const items = results.map((r, originalIndex) => ({ ...r, originalIndex }));
    items.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "name":
          cmp = a.filename.localeCompare(b.filename);
          break;
        case "path":
          cmp = a.path.localeCompare(b.path);
          break;
        case "size":
          cmp = a.size - b.size;
          break;
        case "modified":
          cmp = (a.modified ?? "").localeCompare(b.modified ?? "");
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return items;
  }, [results, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir(key === "modified" ? "desc" : "asc");
    }
  };

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
        if (sorted[selectedIndex]) {
          onExecute(sorted[selectedIndex].originalIndex);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedIndex, results.length, sorted, onSelect, onExecute]);

  if (results.length === 0) {
    return (
      <div className="py-8 text-center text-[var(--color-text-secondary)]">
        No matching files found
      </div>
    );
  }

  const SortIndicator = ({ col }: { col: SortKey }) =>
    sortKey === col ? (
      <span className="ml-1">{sortDir === "asc" ? "▲" : "▼"}</span>
    ) : null;

  return (
    <div>
      {/* Column headers */}
      <div className="mb-1 flex items-center gap-3 px-3 py-1 text-xs text-[var(--color-text-secondary)]">
        <span className="w-5" />
        <button
          onClick={() => handleSort("name")}
          className="min-w-0 flex-1 text-left hover:text-[var(--color-text-primary)]"
        >
          Name<SortIndicator col="name" />
        </button>
        <button
          onClick={() => handleSort("size")}
          className="w-16 shrink-0 text-right hover:text-[var(--color-text-primary)]"
        >
          Size<SortIndicator col="size" />
        </button>
        <button
          onClick={() => handleSort("modified")}
          className="w-20 shrink-0 text-right hover:text-[var(--color-text-primary)]"
        >
          Modified<SortIndicator col="modified" />
        </button>
        <span className="w-12 shrink-0" />
      </div>

      {/* Rows */}
      <div className="space-y-1">
        {sorted.map((r, displayIndex) => (
          <div
            key={r.path}
            onClick={() => onSelect(displayIndex)}
            onDoubleClick={() => onExecute(r.originalIndex)}
            className={`flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 transition-colors ${
              displayIndex === selectedIndex
                ? "bg-[var(--color-accent)]/10 text-[var(--color-text-primary)]"
                : "hover:bg-white/5"
            }`}
          >
            <span className="w-5 text-center text-lg">
              {r.filename.includes(".") ? "\u{1F4C4}" : "\u{1F4C1}"}
            </span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">{r.filename}</div>
              <div className="truncate text-xs text-[var(--color-text-secondary)]">
                {r.path}
              </div>
            </div>
            <div className="w-16 shrink-0 text-right text-xs text-[var(--color-text-secondary)]">
              {r.size > 0 && formatSize(r.size)}
            </div>
            <div className="w-20 shrink-0 text-right text-xs text-[var(--color-text-secondary)]">
              {r.modified && formatDate(r.modified)}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onExecute(r.originalIndex);
              }}
              className="w-12 shrink-0 rounded px-2 py-1 text-xs text-[var(--color-accent)] transition-colors hover:bg-[var(--color-accent)]/20"
            >
              Open
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
