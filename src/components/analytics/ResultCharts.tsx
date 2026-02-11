import ReactECharts from "echarts-for-react";

interface ChartData {
  title: string;
  chart_type: string;
  data: any;
}

interface ResultChartsProps {
  charts: ChartData[];
}

export default function ResultCharts({ charts }: ResultChartsProps) {
  if (charts.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        暂无图表数据
      </div>
    );
  }

  const colors = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {charts.map((chart, index) => {
        const d = chart.data || {};
        let series: Array<{ name: string; type: string; data: number[]; smooth?: boolean; itemStyle?: { color: string } }>;
        if (Array.isArray(d.series)) {
          series = d.series.map((s: { name: string; data: number[] }, i: number) => ({
            name: s.name,
            type: chart.chart_type === "bar" ? "bar" : "line",
            data: s.data,
            smooth: chart.chart_type === "line",
            itemStyle: { color: colors[i % colors.length] },
          }));
        } else if (d.energy && d.cost) {
          series = [
            { name: "电量(kWh)", type: "bar", data: d.energy, itemStyle: { color: colors[0] } },
            { name: "电费(元)", type: "bar", data: d.cost, itemStyle: { color: colors[1] } },
          ];
        } else {
          series = [
            {
              name: chart.title,
              type: chart.chart_type === "bar" ? "bar" : "line",
              data: d.y || d.values || [],
              smooth: chart.chart_type === "line",
              itemStyle: { color: colors[0] },
            },
          ];
        }
        const option = {
          title: {
            text: chart.title,
            left: "center",
            textStyle: {
              color: "#fff",
            },
          },
          tooltip: {
            trigger: "axis",
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            textStyle: {
              color: "#fff",
            },
          },
          grid: {
            left: "3%",
            right: "4%",
            bottom: "3%",
            containLabel: true,
          },
          xAxis: {
            type: (chart.chart_type === "line" && (Array.isArray(d.series) || !d.x?.length)) ? "time" : "category",
            data: d.x || [],
            axisLine: {
              lineStyle: {
                color: "#666",
              },
            },
            axisLabel: {
              color: "#999",
            },
          },
          yAxis: {
            type: "value",
            axisLine: {
              lineStyle: {
                color: "#666",
              },
            },
            axisLabel: {
              color: "#999",
            },
          },
          series,
          backgroundColor: "transparent",
        };

        return (
          <div key={index} className="bg-gray-800 rounded-lg p-4 h-64">
            <ReactECharts
              option={option}
              style={{ height: "100%", width: "100%" }}
              opts={{ renderer: "svg" }}
            />
          </div>
        );
      })}
    </div>
  );
}
