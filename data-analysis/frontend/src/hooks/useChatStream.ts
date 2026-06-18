import { useCallback, useRef } from "react";
import { MOCK_ANSWER, MOCK_CHART_OPTION, MOCK_SQL } from "../api/mock";
import type { StreamEvent } from "../types";

type StreamCallbacks = {
  onSql: (sql: string) => void;
  onToken: (token: string) => void;
  onChart: (option: Record<string, unknown>) => void;
  onDone: () => void;
};

/** 阶段2：伪 SSE 流式输出；阶段4 替换为真实 EventSource/fetch stream */
export function useChatStream() {
  const abortRef = useRef(false);

  const sendMessage = useCallback(
    async (question: string, callbacks: StreamCallbacks) => {
      abortRef.current = false;

      await sleep(300);
      if (abortRef.current) return;
      callbacks.onSql(MOCK_SQL);

      await sleep(400);
      if (abortRef.current) return;

      const answer =
        question.includes("销售") || question.includes("月")
          ? MOCK_ANSWER
          : `已收到您的问题：「${question}」。这是 mock 回复，阶段4 将接入真实大模型与数据库查询。`;

      for (const char of answer) {
        if (abortRef.current) return;
        callbacks.onToken(char);
        await sleep(25);
      }

      await sleep(200);
      if (abortRef.current) return;
      callbacks.onChart(MOCK_CHART_OPTION);
      callbacks.onDone();
    },
    []
  );

  const abort = useCallback(() => {
    abortRef.current = true;
  }, []);

  return { sendMessage, abort };
}

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

export type { StreamEvent };
