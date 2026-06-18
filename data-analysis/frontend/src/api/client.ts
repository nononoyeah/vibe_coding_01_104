import type { Session } from "../types";

/** 阶段2：mock 会话 API，阶段4 切换为真实后端 */

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function fetchSessions(): Promise<Session[]> {
  await delay(100);
  return [];
}

export async function createSessionApi(title: string): Promise<Session> {
  await delay(80);
  return {
    id: crypto.randomUUID(),
    title,
    messages: [],
    chartOption: null,
    updatedAt: Date.now(),
  };
}

export async function deleteSessionApi(_id: string): Promise<void> {
  await delay(80);
}
