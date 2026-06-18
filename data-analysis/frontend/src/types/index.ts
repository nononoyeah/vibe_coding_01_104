export type MessageRole = "user" | "assistant";

export type Message = {
  id: string;
  role: MessageRole;
  content: string;
  sql?: string;
  streaming?: boolean;
  createdAt: number;
};

export type Session = {
  id: string;
  title: string;
  messages: Message[];
  chartOption: Record<string, unknown> | null;
  updatedAt: number;
};

/** POST /api/chat 请求体（与后端 ChatRequest 一致，snake_case） */
export type ChatRequestBody = {
  session_id: string;
  message: string;
};

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
  phase?: number;
};

/** SSE data 字段 JSON（与 phase3-llm-io-spec §5 一致） */
export type StreamEvent =
  | { type: "sql"; sql: string }
  | { type: "result"; columns: string[]; rows: unknown[][]; row_count: number }
  | { type: "token"; content: string }
  | { type: "chart"; option: Record<string, unknown> }
  | { type: "done"; usage?: Record<string, unknown> }
  | { type: "error"; message: string };
