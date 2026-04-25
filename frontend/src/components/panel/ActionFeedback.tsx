import { useEffect, useState } from "react";
import type { ExecutionData } from "../../stores/appStore";

interface Props {
  execution: ExecutionData;
  autoHideMs?: number;
}

export function ActionFeedback({ execution, autoHideMs = 3000 }: Props) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), autoHideMs);
    return () => clearTimeout(timer);
  }, [execution, autoHideMs]);

  if (!visible) return null;

  return (
    <div
      className={`mt-4 flex items-center gap-2 rounded-lg px-4 py-3 text-sm transition-opacity duration-500 ${
        execution.success
          ? "bg-[var(--color-success)]/10 text-[var(--color-success)]"
          : "bg-[var(--color-error)]/10 text-[var(--color-error)]"
      }`}
    >
      <span className="text-lg">{execution.success ? "✓" : "✗"}</span>
      <span>{execution.message}</span>
    </div>
  );
}
