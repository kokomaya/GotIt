import "./index.css";

export default function LauncherApp() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="flex h-[52px] w-[600px] items-center rounded-2xl bg-[var(--color-bg-secondary)]/80 px-4 backdrop-blur-xl">
        <span className="text-[var(--color-text-secondary)]">🎤</span>
        <input
          type="text"
          autoFocus
          placeholder="输入指令或点击麦克风说话..."
          className="ml-3 flex-1 border-none bg-transparent text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-secondary)]"
        />
        <span className="text-[var(--color-text-secondary)]">⏎</span>
      </div>
    </div>
  );
}
