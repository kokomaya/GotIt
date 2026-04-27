import { getCurrentWindow } from "@tauri-apps/api/window";

interface WindowControlsProps {
  onClose: () => void;
}

export function WindowControls({ onClose }: WindowControlsProps) {
  const isTauri = "__TAURI__" in window;

  const handleMinimize = async () => {
    if (isTauri) await getCurrentWindow().minimize();
  };

  const handleMaximize = async () => {
    if (isTauri) await getCurrentWindow().toggleMaximize();
  };

  const handleClose = async () => {
    if (isTauri) {
      await getCurrentWindow().hide();
    }
    onClose();
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={handleMinimize}
        className="flex h-7 w-7 items-center justify-center rounded text-[var(--color-text-secondary)] transition-colors hover:bg-white/10"
        title="Minimize"
      >
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect y="5" width="12" height="1.5" fill="currentColor" />
        </svg>
      </button>
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={handleMaximize}
        className="flex h-7 w-7 items-center justify-center rounded text-[var(--color-text-secondary)] transition-colors hover:bg-white/10"
        title="Maximize"
      >
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect
            x="1"
            y="1"
            width="10"
            height="10"
            rx="1"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          />
        </svg>
      </button>
      <button
        onPointerDown={(e) => e.stopPropagation()}
        onClick={handleClose}
        className="flex h-7 w-7 items-center justify-center rounded text-[var(--color-text-secondary)] transition-colors hover:bg-red-500/80 hover:text-white"
        title="Close"
      >
        <svg width="12" height="12" viewBox="0 0 12 12">
          <path
            d="M1 1L11 11M11 1L1 11"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </div>
  );
}
