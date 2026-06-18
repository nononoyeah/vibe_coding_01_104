import type { StreamEvent } from "../types";

function parseSseBlock(block: string): { event: string; data: StreamEvent } | null {
  if (!block.trim()) return null;

  let eventName = "message";
  let dataLine = "";

  for (const line of block.split("\n")) {
    const trimmed = line.trimEnd();
    if (!trimmed || trimmed.startsWith(":")) continue;
    if (trimmed.startsWith("event:")) {
      eventName = trimmed.slice(6).trim();
      continue;
    }
    if (trimmed.startsWith("data:")) {
      dataLine = trimmed.slice(5).trim();
    }
  }

  if (!dataLine) return null;
  return { event: eventName, data: JSON.parse(dataLine) as StreamEvent };
}

/** 增量 SSE 解析器：按块 feed，收到完整 event 即返回 */
export function createSseParser() {
  let buffer = "";

  return {
    feed(chunk: string): Array<{ event: string; data: StreamEvent }> {
      buffer += chunk.replace(/\r\n/g, "\n");
      const events: Array<{ event: string; data: StreamEvent }> = [];

      let sep = buffer.indexOf("\n\n");
      while (sep !== -1) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const parsed = parseSseBlock(block);
        if (parsed) events.push(parsed);
        sep = buffer.indexOf("\n\n");
      }

      return events;
    },
    flush(): Array<{ event: string; data: StreamEvent }> {
      const parsed = parseSseBlock(buffer);
      buffer = "";
      return parsed ? [parsed] : [];
    },
  };
}

/** 一次性解析完整 SSE 文本（测试用） */
export function parseSseText(raw: string): Array<{ event: string; data: StreamEvent }> {
  const normalized = raw.replace(/\r\n/g, "\n");
  const blocks = normalized.split("\n\n").filter((b) => b.trim());
  const events: Array<{ event: string; data: StreamEvent }> = [];
  for (const block of blocks) {
    const parsed = parseSseBlock(block);
    if (parsed) events.push(parsed);
  }
  return events;
}
