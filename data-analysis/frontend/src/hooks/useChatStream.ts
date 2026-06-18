import { useCallback, useRef } from "react";
import { createSseParser } from "../lib/parseSse";
import type { StreamEvent } from "../types";

export type StreamCallbacks = {
  onSql: (sql: string) => void;
  onToken: (content: string) => void;
  onChart: (option: Record<string, unknown>) => void;
  onResult?: (result: Extract<StreamEvent, { type: "result" }>) => void;
  onError: (message: string) => void;
  onDone: () => void;
};

function dispatchEvent(data: StreamEvent, callbacks: StreamCallbacks): "done" | "error" | void {
  switch (data.type) {
    case "sql":
      callbacks.onSql(data.sql);
      break;
    case "result":
      callbacks.onResult?.(data);
      break;
    case "token":
      callbacks.onToken(data.content);
      break;
    case "chart":
      callbacks.onChart(data.option);
      break;
    case "error":
      callbacks.onError(data.message);
      return "error";
    case "done":
      callbacks.onDone();
      return "done";
  }
}

export function useChatStream() {
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (sessionId: string, message: string, callbacks: StreamCallbacks) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ session_id: sessionId, message }),
        signal: controller.signal,
      });

      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          if (body?.detail) detail = String(body.detail);
        } catch {
          /* ignore */
        }
        callbacks.onError(detail);
        return;
      }

      if (!res.body) {
        callbacks.onError("浏览器不支持流式响应");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      const parser = createSseParser();
      let finished = false;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (controller.signal.aborted) return;

          if (value) {
            for (const { data } of parser.feed(decoder.decode(value, { stream: true }))) {
              if (controller.signal.aborted) return;
              const status = dispatchEvent(data, callbacks);
              if (status === "error") return;
              if (status === "done") finished = true;
            }
          }

          if (done) break;
        }

        for (const { data } of parser.flush()) {
          if (controller.signal.aborted) return;
          const status = dispatchEvent(data, callbacks);
          if (status === "error") return;
          if (status === "done") finished = true;
        }
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        throw err;
      }

      if (!finished && !controller.signal.aborted) {
        callbacks.onDone();
      }
    },
    [],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  return { sendMessage, abort };
}

export type { StreamEvent };
