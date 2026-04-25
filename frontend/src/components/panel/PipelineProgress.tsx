import type { PipelineStage, StageStatus } from "../../stores/appStore";

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: "intent", label: "Intent" },
  { key: "search", label: "Search" },
  { key: "execute", label: "Execute" },
];

const statusStyle: Record<StageStatus, string> = {
  pending: "border-white/20 text-[var(--color-text-secondary)]",
  active: "border-[var(--color-accent)] text-[var(--color-accent)] animate-pulse",
  done: "border-[var(--color-success)] text-[var(--color-success)]",
  error: "border-[var(--color-error)] text-[var(--color-error)]",
};

const statusIcon: Record<StageStatus, string> = {
  pending: "",
  active: "...",
  done: "OK",
  error: "!",
};

interface Props {
  stages: Record<PipelineStage, StageStatus>;
}

export function PipelineProgress({ stages }: Props) {
  return (
    <div className="flex items-center gap-2">
      {STAGES.map(({ key, label }, i) => (
        <div key={key} className="flex items-center gap-2">
          {i > 0 && <div className="h-px w-6 bg-white/20" />}
          <div
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs ${statusStyle[stages[key]]}`}
          >
            <span>{label}</span>
            {statusIcon[stages[key]] && (
              <span className="font-mono text-[10px]">{statusIcon[stages[key]]}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
