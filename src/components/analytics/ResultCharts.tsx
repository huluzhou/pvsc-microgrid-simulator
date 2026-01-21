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

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {charts.map((chart, index) => {
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
            type: chart.chart_type === "line" ? "time" : "category",
            data: chart.data?.x || [],
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
          series: [
            {
              name: chart.title,
              type: chart.chart_type === "bar" ? "bar" : "line",
              data: chart.data?.y || chart.data?.values || [],
              smooth: chart.chart_type === "line",
              itemStyle: {
                color: "#3b82f6",
              },
            },
          ],
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
