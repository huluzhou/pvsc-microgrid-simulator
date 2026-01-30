import ReactECharts from "echarts-for-react";

export interface DataPointLegacy {
  timestamp: number;
  value: number;
}

export interface DataPointWithJson {
  timestamp: number;
  value?: number;
  p_active?: number | null;
  p_reactive?: number | null;
  data_json?: Record<string, unknown> | null;
}

type DataPoint = DataPointLegacy | DataPointWithJson;

interface DataChartProps {
  title: string;
  data: DataPoint[];
  seriesKey?: string;
  unit?: string;
  color?: string;
  /** 启用鼠标滚轮缩放与拖拽平移，便于精细查看 */
  enableDataZoom?: boolean;
}

function getValueFromPoint(point: DataPoint, seriesKey: string): number | null {
  if ("value" in point && seriesKey === "active_power" && point.value !== undefined) return point.value;
  if ("p_active" in point && seriesKey === "active_power") return point.p_active ?? null;
  if ("p_reactive" in point && seriesKey === "reactive_power") return point.p_reactive ?? null;
  if ("data_json" in point && point.data_json && seriesKey in point.data_json) {
    const v = point.data_json[seriesKey];
    return typeof v === "number" ? v : null;
  }
  return null;
}

export default function DataChart({
  title,
  data,
  seriesKey = "active_power",
  unit = "",
  color = "#3b82f6",
  enableDataZoom = true,
}: DataChartProps) {
  const chartData = seriesKey
    ? (data as DataPointWithJson[])
        .map((point) => {
          const v = getValueFromPoint(point, seriesKey);
          return v !== null ? [point.timestamp * 1000, v] as [number, number] : null;
        })
        .filter((x): x is [number, number] => x !== null)
    : (data as DataPointLegacy[]).map((point) => [point.timestamp * 1000, point.value]);

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
      bottom: enableDataZoom ? "15%" : "3%",
      containLabel: true,
    },
    ...(enableDataZoom && {
      dataZoom: [
        { type: "inside", xAxisIndex: 0, start: 0, end: 100 },
        { type: "slider", xAxisIndex: 0, start: 0, end: 100, bottom: "2%", height: 20 },
      ],
    }),
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
        formatter: (value: unknown) => {
          const n = typeof value === "number" && Number.isFinite(value) ? value : 0;
          return `${Number(n).toFixed(1)} ${unit}`;
        },
      },
    },
    series: [
      {
        name: title || seriesKey,
        type: "line",
        smooth: true,
        data: chartData,
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
