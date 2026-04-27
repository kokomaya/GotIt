import { useRef, useEffect } from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  history?: string[];
  historyIndex: number;
  onHistoryNavigate: (direction: "up" | "down") => void;
}

export function InputBar({
  value,
  onChange,
  onSubmit,
  onCancel,
  historyIndex,
  onHistoryNavigate,
}: Props) {
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    ref.current?.focus();
  }, []);

  return (
    <input
      ref={ref}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter" && value.trim()) onSubmit();
        else if (e.key === "Escape") onCancel();
        else if (e.key === "ArrowUp") {
          e.preventDefault();
          onHistoryNavigate("up");
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          onHistoryNavigate("down");
        }
      }}
      placeholder="输入指令或点击麦克风说话..."
      className="mx-3 flex-1 border-none bg-transparent text-base text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-secondary)]"
    />
  );
}
