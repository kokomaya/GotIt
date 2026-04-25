import { create } from "zustand";

export type AppPhase =
  | "dormant"
  | "launcher"
  | "processing"
  | "results"
  | "executed";

export type VoiceState = "idle" | "recording" | "transcribing";

export type PipelineStage = "intent" | "search" | "execute";
export type StageStatus = "pending" | "active" | "done" | "error";

export interface SearchResultItem {
  path: string;
  filename: string;
  size: number;
  modified: string | null;
}

export interface IntentData {
  action: string;
  query: string | null;
  target: string | null;
  filters: Record<string, string>;
  confidence: number;
}

export interface ExecutionData {
  success: boolean;
  action: string;
  message: string;
}

interface AppStore {
  phase: AppPhase;
  voiceState: VoiceState;
  inputText: string;
  transcript: string;
  intent: IntentData | null;
  results: SearchResultItem[];
  selectedIndex: number;
  execution: ExecutionData | null;
  error: string | null;
  stages: Record<PipelineStage, StageStatus>;

  setPhase: (phase: AppPhase) => void;
  setVoiceState: (state: VoiceState) => void;
  setInputText: (text: string) => void;

  submitInput: (text: string) => void;
  onTranscript: (text: string, partial: boolean) => void;
  onIntent: (data: IntentData) => void;
  onResults: (results: SearchResultItem[]) => void;
  onExecuted: (data: ExecutionData) => void;
  onError: (message: string) => void;
  setSelectedIndex: (index: number) => void;
  reset: () => void;
}

const initialStages: Record<PipelineStage, StageStatus> = {
  intent: "pending",
  search: "pending",
  execute: "pending",
};

export const useAppStore = create<AppStore>((set) => ({
  phase: "dormant",
  voiceState: "idle",
  inputText: "",
  transcript: "",
  intent: null,
  results: [],
  selectedIndex: 0,
  execution: null,
  error: null,
  stages: { ...initialStages },

  setPhase: (phase) => set({ phase }),
  setVoiceState: (state) => set({ voiceState: state }),
  setInputText: (text) => set({ inputText: text }),

  submitInput: (text) =>
    set({
      inputText: text,
      phase: "processing",
      error: null,
      intent: null,
      results: [],
      execution: null,
      selectedIndex: 0,
      stages: { intent: "active", search: "pending", execute: "pending" },
    }),

  onTranscript: (text, partial) =>
    set({ transcript: text, voiceState: partial ? "transcribing" : "idle" }),

  onIntent: (data) =>
    set({
      intent: data,
      stages: { intent: "done", search: "active", execute: "pending" },
    }),

  onResults: (results) =>
    set({
      results,
      phase: "results",
      stages: { intent: "done", search: "done", execute: "pending" },
    }),

  onExecuted: (data) =>
    set({
      execution: data,
      phase: "executed",
      stages: { intent: "done", search: "done", execute: "done" },
    }),

  onError: (message) =>
    set((state) => {
      const stages = { ...state.stages };
      for (const key of Object.keys(stages) as PipelineStage[]) {
        if (stages[key] === "active") stages[key] = "error";
      }
      return { error: message, stages };
    }),

  setSelectedIndex: (index) => set({ selectedIndex: index }),

  reset: () =>
    set({
      phase: "dormant",
      voiceState: "idle",
      inputText: "",
      transcript: "",
      intent: null,
      results: [],
      selectedIndex: 0,
      execution: null,
      error: null,
      stages: { ...initialStages },
    }),
}));
