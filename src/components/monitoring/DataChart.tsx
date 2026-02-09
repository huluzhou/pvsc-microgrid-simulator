import { useRef, useCallback, useState, useEffect } from "react";
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
  /** 缩放/拖拽后可见时间范围变化时回调 (startSec, endSec)，用于按可见范围重新请求数据 */
  onVisibleRangeChange?: (startSec: number, endSec: number) => void;
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

const DEBOUNCE_MS = 300;

export default function DataChart({
  title,
  data,
  seriesKey = "active_power",
  unit = "",
  color = "#3b82f6",
  enableDataZoom = true,
  onVisibleRangeChange,
}: DataChartProps) {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chartRef = useRef<ReactECharts | null>(null);
  const prevEnableDataZoomRef = useRef(enableDataZoom);
  const [zoomRange, setZoomRange] = useState({ start: 0, end: 100 });

  // 当 enableDataZoom 从 false 变为 true 时，重置缩放到全范围
  useEffect(() => {
    if (enableDataZoom && !prevEnableDataZoomRef.current) {
      setZoomRange({ start: 0, end: 100 });
    }
    prevEnableDataZoomRef.current = enableDataZoom;
  }, [enableDataZoom]);

  const handleDataZoom = useCallback(
    (params?: { batch?: Array<{ startValue?: number; endValue?: number; start?: number; end?: number }> }) => {
      // 保存当前缩放状态，防止 enableDataZoom 变化时回弹
      const batch = params?.batch?.[0];
      if (batch != null && typeof batch.start === 'number' && typeof batch.end === 'number') {
        setZoomRange({ start: batch.start, end: batch.end });
      }
      
      if (!onVisibleRangeChange) return;
      const clear = () => {
        if (debounceRef.current) {
          clearTimeout(debounceRef.current);
          debounceRef.current = null;
        }
      };
      clear();
      debounceRef.current = setTimeout(() => {
        debounceRef.current = null;
        const ref = chartRef.current;
        if (!ref) return;
        try {
          const instance = ref.getEchartsInstance();
          const batch = params?.batch?.[0];
          let loSec: number;
          let hiSec: number;
          if (
            batch != null &&
            typeof batch.startValue === "number" &&
            typeof batch.endValue === "number"
          ) {
            loSec = batch.startValue / 1000;
            hiSec = batch.endValue / 1000;
          } else {
            const opt = instance.getOption();
            const xAxis = Array.isArray(opt.xAxis) ? opt.xAxis[0] : opt.xAxis;
            const min = (xAxis as { min?: number })?.min;
            const max = (xAxis as { max?: number })?.max;
            if (typeof min !== "number" || typeof max !== "number") return;
            loSec = min / 1000;
            hiSec = max / 1000;
          }
          if (hiSec > loSec) onVisibleRangeChange(loSec, hiSec);
        } catch {
          // ignore
        }
      }, DEBOUNCE_MS);
    },
    [onVisibleRangeChange]
  );

  const chartData = seriesKey
    ? (data as DataPointWithJson[])
        .map((point) => {
          const v = getValueFromPoint(point, seriesKey);
          return v !== null ? [point.timestamp * 1000, v] as [number, number] : null;
        })
        .filter((x): x is [number, number] => x !== null)
    : (data as DataPointLegacy[]).map((point) => [point.timestamp * 1000, point.value]);

  // 根据纵轴数值范围决定小数位数，避免 toFixed(1) 导致刻度标签重复（如 10.01/10.02 都显示为 10.0）
  const yValues = chartData.map(([, y]) => y);
  const yMin = yValues.length ? Math.min(...yValues) : 0;
  const yMax = yValues.length ? Math.max(...yValues) : 0;
  const yRange = Math.max(yMax - yMin, 0) || 1;
  const yDecimals =
    yRange < 0.01 ? 4 : yRange < 0.1 ? 3 : yRange < 1 ? 2 : yRange < 10 ? 1 : 0;

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
        { type: "inside", xAxisIndex: 0, start: zoomRange.start, end: zoomRange.end },
        { type: "slider", xAxisIndex: 0, start: zoomRange.start, end: zoomRange.end, bottom: "2%", height: 20 },
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
          return `${Number(n).toFixed(yDecimals)} ${unit}`;
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
        ref={(r) => { chartRef.current = r; }}
        option={option}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "svg" }}
        onEvents={enableDataZoom ? { datazoom: handleDataZoom } : undefined}
        notMerge={false}
        lazyUpdate={true}
      />
    </div>
  );
}
