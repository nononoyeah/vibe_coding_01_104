import ReactECharts from "echarts-for-react";
import { useSessionStore } from "../store/sessions";
import "./ChartPanel.css";

export default function ChartPanel() {
  const activeSession = useSessionStore((s) => s.getActiveSession());
  const chartOption = activeSession?.chartOption;

  return (
    <aside className="chart-panel">
      <h2>可视化图表</h2>
      {chartOption ? (
        <div className="chart-container">
          <ReactECharts
            option={chartOption}
            style={{ height: "100%", width: "100%" }}
            opts={{ renderer: "canvas" }}
          />
        </div>
      ) : (
        <div className="chart-placeholder">
          <p>发送问题后，图表将在此展示</p>
          <span className="chart-hint">提问后将根据查询结果自动生成 ECharts 配置</span>
        </div>
      )}
    </aside>
  );
}
