import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useChatStream } from "../hooks/useChatStream";
import { useSessionStore } from "../store/sessions";
import MessageList from "./MessageList";
import "./ChatPanel.css";

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
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
  const refreshSession = useSessionStore((s) => s.refreshSession);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeSession?.messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !activeSession || isStreaming) return;

    setInput("");
    setErrorMsg(null);
    addUserMessage(text);
    setStreaming(true);

    const assistantId = startAssistantMessage();
    const sessionId = activeSession.id;

    try {
      await sendMessage(sessionId, text, {
        onSql: (sql) => setMessageSql(assistantId, sql),
        onToken: (content) => appendAssistantToken(assistantId, content),
        onChart: (option) => setChartOption(option),
        onError: (message) => {
          setErrorMsg(message);
          finishAssistantMessage(assistantId);
        },
        onDone: () => {
          finishAssistantMessage(assistantId);
        },
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      const message = err instanceof Error ? err.message : "请求失败";
      setErrorMsg(message);
      finishAssistantMessage(assistantId);
    } finally {
      setStreaming(false);
      void refreshSession(sessionId).catch(() => {
        /* 刷新失败不阻塞发送 */
      });
    }
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
        {errorMsg && <div className="chat-error">{errorMsg}</div>}
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
