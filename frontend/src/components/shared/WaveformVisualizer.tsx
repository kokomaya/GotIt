export function WaveformVisualizer() {
  return (
    <div className="flex h-4 items-end gap-[2px]">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="w-[3px] rounded-full bg-[var(--color-accent)]"
          style={{
            animation: `waveform 0.8s ease-in-out ${i * 0.1}s infinite alternate`,
          }}
        />
      ))}
      <style>{`
        @keyframes waveform {
          from { height: 4px; }
          to { height: 16px; }
        }
      `}</style>
    </div>
  );
}
