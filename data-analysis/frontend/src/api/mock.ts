export const MOCK_CHART_OPTION: Record<string, unknown> = {
  title: { text: "月度销售额", left: "center", textStyle: { fontSize: 14 } },
  tooltip: { trigger: "axis" },
  xAxis: {
    type: "category",
    data: ["1月", "2月", "3月", "4月", "5月", "6月"],
  },
  yAxis: { type: "value", name: "万元" },
  series: [
    {
      name: "销售额",
      type: "bar",
      data: [120, 200, 150, 80, 70, 110],
      itemStyle: { color: "#4f46e5" },
    },
  ],
};

export const MOCK_SQL =
  "SELECT strftime('%Y-%m', order_date) AS month, SUM(total_amount) AS sales\nFROM orders\nGROUP BY month\nORDER BY month;";

export const MOCK_ANSWER =
  "根据查询结果，上半年销售额在 2 月达到峰值 200 万元，4 月最低为 80 万元。已为您生成柱状图，可在右侧查看。";
