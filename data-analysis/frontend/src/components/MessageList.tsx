import type { Message } from "../types";
import "./MessageList.css";

type Props = {
  messages: Message[];
};

export default function MessageList({ messages }: Props) {
  if (messages.length === 0) {
    return (
      <div className="message-empty">
        <p>向数据助手提问，例如：</p>
        <ul>
          <li>按月统计销售额并画柱状图</li>
          <li>销量前 5 的商品有哪些？</li>
        </ul>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((m) => (
        <div key={m.id} className={`message-bubble ${m.role}`}>
          <div className="message-role">{m.role === "user" ? "你" : "助手"}</div>
          {m.sql && (
            <pre className="message-sql">
              <span className="sql-label">SQL</span>
              {m.sql}
            </pre>
          )}
          <div className="message-content">
            {m.content}
            {m.streaming && <span className="cursor-blink">|</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
