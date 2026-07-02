import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type TelemetryRecord = {
  request_id: string;
  timestamp: string;
  prompt: string;
  tag: string;
  strategy: string;
  cloud_score: number;
  edge_score: number;
  tier1_state: Record<string, unknown>;
  opa_status: string;
  opa_violations: string[];
  selected_route: string;
  selected_model: string;
  latency_ms: number;
  is_fallback: boolean;
  cloud_expected_cost: number;
  edge_expected_cost: number;
  cloud_base_score?: number;
  edge_base_score?: number;
  primary_reason?: string;
  telemetry_snapshot?: Record<string, unknown>;
};

export type Message = {
  role: 'user' | 'assistant';
  content: string;
};

type AppState = {
  apiKey: string;
  setApiKey: (key: string) => void;
  strategy: string;
  setStrategy: (strategy: string) => void;
  requestTag: string;
  setRequestTag: (tag: string) => void;
  messages: Message[];
  addMessage: (msg: Message) => void;
  clearMessages: () => void;
  telemetryRecords: TelemetryRecord[];
  addTelemetryRecord: (record: TelemetryRecord) => void;
  clearTelemetryRecords: () => void;
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      apiKey: '',
      setApiKey: (key) => set({ apiKey: key }),
      strategy: 'PROPOSED',
      setStrategy: (strategy) => set({ strategy }),
      requestTag: 'default',
      setRequestTag: (tag) => set({ requestTag: tag }),
      messages: [],
      addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
      clearMessages: () => set({ messages: [] }),
      telemetryRecords: [],
      addTelemetryRecord: (record) => set((state) => ({ 
        telemetryRecords: [...state.telemetryRecords, record] 
      })),
      clearTelemetryRecords: () => set({ telemetryRecords: [] }),
    }),
    {
      name: 'cats-storage',
      // Only persist configuration, not transient state like messages/telemetry if desired, 
      // but in Streamlit they were session state. Persisting them makes it nicer.
    }
  )
);
