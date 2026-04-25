interface Props {
  isRecording: boolean;
  onToggle: () => void;
}

export function ModeIndicator({ isRecording, onToggle }: Props) {
  return (
    <button
      onClick={onToggle}
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors hover:bg-white/10"
      title={isRecording ? "Stop recording" : "Start voice input"}
    >
      {isRecording ? (
        <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-[var(--color-error)]" />
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--color-text-secondary)]">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      )}
    </button>
  );
}
