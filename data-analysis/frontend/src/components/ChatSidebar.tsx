import { useSessionStore } from "../store/sessions";
import "./ChatSidebar.css";

export default function ChatSidebar() {
  const sessions = useSessionStore((s) => s.sessions);
  const activeId = useSessionStore((s) => s.activeId);
  const createSession = useSessionStore((s) => s.createSession);
  const deleteSession = useSessionStore((s) => s.deleteSession);
  const selectSession = useSessionStore((s) => s.selectSession);

  return (
    <aside className="chat-sidebar">
      <div className="sidebar-header">
        <h2>会话管理</h2>
        <button className="btn-new" onClick={() => createSession()} title="新建会话">
          +
        </button>
      </div>

      <ul className="session-list">
        {sessions.length === 0 && (
          <li className="session-empty">暂无会话，点击 + 新建</li>
        )}
        {sessions.map((s) => (
          <li
            key={s.id}
            className={`session-item ${s.id === activeId ? "active" : ""}`}
            onClick={() => selectSession(s.id)}
          >
            <span className="session-title">{s.title}</span>
            <button
              className="btn-delete"
              onClick={(e) => {
                e.stopPropagation();
                deleteSession(s.id);
              }}
              title="删除会话"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
