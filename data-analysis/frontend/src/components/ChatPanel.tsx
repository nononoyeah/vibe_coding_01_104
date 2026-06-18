import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useChatStream } from "../hooks/useChatStream";
import { useSessionStore } from "../store/sessions";
import MessageList from "./MessageList";
import "./ChatPanel.css";

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const { sendMessage } = useChatStream();

  const activeSession = useSessionStore((s) => s.getActiveSession());
  const isStreaming = useSessionStore((s) => s.isStreaming);
  const addUserMessage = useSessionStore((s) => s.addUserMessage);
  const startAssistantMessage = useSessionStore((s) => s.startAssistantMessage);
  const appendAssistantToken = useSessionStore((s) => s.appendAssistantToken);
  const setMessageSql = useSessionStore((s) => s.setMessageSql);
  const finishAssistantMessage = useSessionStore((s) => s.finishAssistantMessage);
  const setChartOption = useSessionStore((s) => s.setChartOption);
  const setStreaming = useSessionStore((s) => s.setStreaming);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeSession?.messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !activeSession || isStreaming) return;

    setInput("");
    addUserMessage(text);
    setStreaming(true);

    const assistantId = startAssistantMessage();

    await sendMessage(text, {
      onSql: (sql) => setMessageSql(assistantId, sql),
      onToken: (token) => appendAssistantToken(assistantId, token),
      onChart: (option) => setChartOption(option),
      onDone: () => {
        finishAssistantMessage(assistantId);
        setStreaming(false);
      },
    });
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!activeSession) {
    return (
      <section className="chat-panel">
        <div className="chat-no-session">
          <p>请先在左侧新建或选择一个会话</p>
        </div>
      </section>
    );
  }

  return (
    <section className="chat-panel">
      <div className="chat-messages">
        <MessageList messages={activeSession.messages} />
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <textarea
          className="chat-input"
          placeholder="输入数据分析问题，Enter 发送，Shift+Enter 换行"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
          rows={2}
        />
        <button
          className="btn-send"
          onClick={handleSend}
          disabled={!input.trim() || isStreaming}
        >
          {isStreaming ? "生成中..." : "发送"}
        </button>
      </div>
    </section>
  );
}
