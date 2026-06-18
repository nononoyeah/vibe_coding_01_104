import { create } from "zustand";
import { createSessionApi, deleteSessionApi } from "../api/client";
import type { Message, Session } from "../types";

type SessionStore = {
  sessions: Session[];
  activeId: string | null;
  isStreaming: boolean;
  createSession: () => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  selectSession: (id: string) => void;
  addUserMessage: (content: string) => string;
  startAssistantMessage: () => string;
  appendAssistantToken: (msgId: string, token: string) => void;
  setMessageSql: (msgId: string, sql: string) => void;
  finishAssistantMessage: (msgId: string) => void;
  setChartOption: (option: Record<string, unknown>) => void;
  setStreaming: (v: boolean) => void;
  getActiveSession: () => Session | undefined;
};

export const useSessionStore = create<SessionStore>((set, get) => ({
  sessions: [],
  activeId: null,
  isStreaming: false,

  createSession: async () => {
    const session = await createSessionApi("新对话");
    set((s) => ({
      sessions: [session, ...s.sessions],
      activeId: session.id,
    }));
  },

  deleteSession: async (id) => {
    await deleteSessionApi(id);
    set((s) => {
      const sessions = s.sessions.filter((x) => x.id !== id);
      const activeId =
        s.activeId === id ? (sessions[0]?.id ?? null) : s.activeId;
      return { sessions, activeId };
    });
  },

  selectSession: (id) => set({ activeId: id }),

  addUserMessage: (content) => {
    const msg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      createdAt: Date.now(),
    };
    set((s) => updateSession(s, (sess) => ({
      ...sess,
      messages: [...sess.messages, msg],
      title: sess.messages.length === 0 ? content.slice(0, 20) : sess.title,
      updatedAt: Date.now(),
    })));
    return msg.id;
  },

  startAssistantMessage: () => {
    const msg: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      streaming: true,
      createdAt: Date.now(),
    };
    set((s) => updateSession(s, (sess) => ({
      ...sess,
      messages: [...sess.messages, msg],
      updatedAt: Date.now(),
    })));
    return msg.id;
  },

  appendAssistantToken: (msgId, token) => {
    set((s) => updateSession(s, (sess) => ({
      ...sess,
      messages: sess.messages.map((m) =>
        m.id === msgId ? { ...m, content: m.content + token } : m
      ),
    })));
  },

  setMessageSql: (msgId, sql) => {
    set((s) => updateSession(s, (sess) => ({
      ...sess,
      messages: sess.messages.map((m) =>
        m.id === msgId ? { ...m, sql } : m
      ),
    })));
  },

  finishAssistantMessage: (msgId) => {
    set((s) => updateSession(s, (sess) => ({
      ...sess,
      messages: sess.messages.map((m) =>
        m.id === msgId ? { ...m, streaming: false } : m
      ),
      updatedAt: Date.now(),
    })));
  },

  setChartOption: (option) => {
    set((s) => updateSession(s, (sess) => ({
      ...sess,
      chartOption: option,
    })));
  },

  setStreaming: (v) => set({ isStreaming: v }),

  getActiveSession: () => {
    const { sessions, activeId } = get();
    return sessions.find((s) => s.id === activeId);
  },
}));

function updateSession(
  state: { sessions: Session[]; activeId: string | null },
  updater: (s: Session) => Session
) {
  if (!state.activeId) return state;
  return {
    sessions: state.sessions.map((s) =>
      s.id === state.activeId ? updater(s) : s
    ),
  };
}
