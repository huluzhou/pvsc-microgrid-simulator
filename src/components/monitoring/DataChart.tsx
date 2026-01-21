import ReactECharts from "echarts-for-react";

interface DataPoint {
  timestamp: number;
  value: number;
}

interface DataChartProps {
  title: string;
  data: DataPoint[];
  unit?: string;
  color?: string;
}

export default function DataChart({
  title,
  data,
  unit = "",
  color = "#3b82f6",
}: DataChartProps) {
  const option = {
    title: {
      text: title,
      left: "center",
      textStyle: {
        color: "#fff",
      },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(0, 0, 0, 0.8)",
      borderColor: "#333",
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
      type: "time",
      boundaryGap: false,
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
        formatter: `{value} ${unit}`,
      },
    },
    series: [
      {
        name: title,
        type: "line",
        smooth: true,
        data: data.map((point) => [point.timestamp * 1000, point.value]),
        lineStyle: {
          color: color,
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              {
                offset: 0,
                color: color + "80",
              },
              {
                offset: 1,
                color: color + "00",
              },
            ],
          },
        },
      },
    ],
    backgroundColor: "transparent",
  };

  return (
    <div className="w-full h-full">
      <ReactECharts
        option={option}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "svg" }}
      />
    </div>
  );
}
