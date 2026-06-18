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

export type StreamEvent =
  | { type: "sql"; sql: string }
  | { type: "token"; token: string }
  | { type: "chart"; option: Record<string, unknown> }
  | { type: "done" };
