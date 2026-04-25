import { useAppStore } from "../stores/appStore";

export function useVoice() {
  const voiceState = useAppStore((s) => s.voiceState);
  const transcript = useAppStore((s) => s.transcript);
  const setVoiceState = useAppStore((s) => s.setVoiceState);

  return {
    isRecording: voiceState === "recording",
    isTranscribing: voiceState === "transcribing",
    transcript,
    startRecording: () => setVoiceState("recording"),
    stopRecording: () => setVoiceState("idle"),
  };
}
