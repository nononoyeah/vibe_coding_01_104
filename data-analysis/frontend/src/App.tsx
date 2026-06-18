import { useEffect, useState } from "react";
import ChartPanel from "./components/ChartPanel";
import ChatPanel from "./components/ChatPanel";
import ChatSidebar from "./components/ChatSidebar";
import "./App.css";

type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1>智能数据分析系统</h1>
          <p className="app-subtitle">阶段2 · 前端 UI（mock 驱动）</p>
        </div>
        <div className="health-status">
          {health && (
            <span className="health-ok">
              后端 {health.version}
            </span>
          )}
          {error && <span className="health-error">后端离线</span>}
        </div>
      </header>

      <main className="layout">
        <div className="panel sidebar">
          <ChatSidebar />
        </div>
        <div className="panel chat">
          <ChatPanel />
        </div>
        <div className="panel chart">
          <ChartPanel />
        </div>
      </main>
    </div>
  );
}
