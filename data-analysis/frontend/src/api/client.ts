import type { Session } from "../types";

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export async function fetchSessions(): Promise<Session[]> {
  return request<Session[]>("/api/sessions");
}

export async function fetchSession(sessionId: string): Promise<Session> {
  return request<Session>(`/api/sessions/${sessionId}`);
}

export async function createSessionApi(title = "新对话"): Promise<Session> {
  return request<Session>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
}

export async function deleteSessionApi(sessionId: string): Promise<void> {
  await request<void>(`/api/sessions/${sessionId}`, { method: "DELETE" });
}
