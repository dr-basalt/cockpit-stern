import { create } from "zustand";

export type AgentType = "sp" | "clone" | "anti" | "real";
export type Message = {
  role: "user" | "assistant";
  content: string;
  agent?: AgentType;
};

interface CockpitStore {
  profileId: string;
  sessionId: string;
  energy: number;
  activeAgent: AgentType;
  messages: Message[];
  streamMode: "ws" | "rest";
  loading: boolean;
  profile: Record<string, unknown> | null;

  setProfileId: (id: string) => void;
  setEnergy: (e: number) => void;
  setActiveAgent: (a: AgentType) => void;
  addMessage: (m: Message) => void;
  replaceLastAssistant: (content: string, agent: AgentType) => void;
  setStreamMode: (m: "ws" | "rest") => void;
  setLoading: (l: boolean) => void;
  setProfile: (p: Record<string, unknown>) => void;
  clearMessages: () => void;
}

export const useCockpitStore = create<CockpitStore>((set) => ({
  profileId: "",
  sessionId: crypto.randomUUID(),
  energy: 5,
  activeAgent: "sp",
  messages: [],
  streamMode: "rest",
  loading: false,
  profile: null,

  setProfileId: (id) => set({ profileId: id }),
  setEnergy: (energy) => set({ energy }),
  setActiveAgent: (activeAgent) => set({ activeAgent }),
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  replaceLastAssistant: (content, agent) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content, agent };
      }
      return { messages: msgs };
    }),
  setStreamMode: (streamMode) => set({ streamMode }),
  setLoading: (loading) => set({ loading }),
  setProfile: (profile) => set({ profile }),
  clearMessages: () => set({ messages: [] }),
}));
