/**
 * 多数据项并行查看图表 - 在同一图表中绘制多条曲线
 * 支持最多 8 条曲线，自动配色，可滚动图例
 */
import { useRef, useCallback, useState, useEffect } from "react";
import ReactECharts from "echarts-for-react";

/** 单条曲线的数据 */
export interface SeriesItem {
  /** 唯一标识 */
  key: string;
  /** 显示在图例中的标签（简化后的名称） */
  label: string;
  /** 时间序列数据 */
  data: Array<{ timestamp: number; value: number }>;
  /** 可选颜色（不提供则自动分配） */
  color?: string;
}

interface MultiSeriesChartProps {
  /** 多条数据曲线 */
  series: SeriesItem[];
  /** 启用缩放与拖拽 */
  enableDataZoom?: boolean;
}

// 自动配色色板（8 色）
const COLOR_PALETTE = [
  "#3b82f6", // blue
  "#ef4444", // red
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#84cc16", // lime
];

export default function MultiSeriesChart({
  series,
  enableDataZoom = true,
}: MultiSeriesChartProps) {
  const chartRef = useRef<ReactECharts | null>(null);
  const [zoomRange, setZoomRange] = useState({ start: 0, end: 100 });

  // 当数据源变化时重置缩放
  useEffect(() => {
    setZoomRange({ start: 0, end: 100 });
  }, [series.length]);

  const handleDataZoom = useCallback(
    (params?: { batch?: Array<{ start?: number; end?: number }> }) => {
      const batch = params?.batch?.[0];
      if (batch != null && typeof batch.start === "number" && typeof batch.end === "number") {
        setZoomRange({ start: batch.start, end: batch.end });
      }
    },
    []
  );

  // 构建 ECharts 系列数据
  const echartsSeries = series.map((s, idx) => {
    const color = s.color || COLOR_PALETTE[idx % COLOR_PALETTE.length];
    return {
      name: s.label,
      type: "line" as const,
      smooth: true,
      symbol: "none",
      sampling: "lttb" as const,
      data: s.data.map((p) => [p.timestamp * 1000, p.value]),
      lineStyle: { color, width: 1.5 },
      itemStyle: { color },
    };
  });

  const option = {
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(0, 0, 0, 0.85)",
      borderColor: "#333",
      textStyle: { color: "#fff", fontSize: 11 },
      confine: true,
    },
    legend: {
      type: "scroll",
      bottom: enableDataZoom ? 30 : 0,
      left: "center",
      textStyle: { color: "#666", fontSize: 11 },
      pageTextStyle: { color: "#666" },
      pageIconColor: "#666",
      pageIconInactiveColor: "#ccc",
      itemWidth: 14,
      itemHeight: 10,
    },
    grid: {
      left: "3%",
      right: "4%",
      top: "4%",
      bottom: enableDataZoom ? "22%" : "14%",
      containLabel: true,
    },
    ...(enableDataZoom && {
      dataZoom: [
        { type: "inside", xAxisIndex: 0, start: zoomRange.start, end: zoomRange.end },
        { type: "slider", xAxisIndex: 0, start: zoomRange.start, end: zoomRange.end, bottom: "2%", height: 18 },
      ],
    }),
    xAxis: {
      type: "time",
      boundaryGap: false,
      axisLine: { lineStyle: { color: "#ddd" } },
      axisLabel: { color: "#888", fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      axisLine: { lineStyle: { color: "#ddd" } },
      axisLabel: { color: "#888", fontSize: 10 },
      splitLine: { lineStyle: { color: "#f0f0f0" } },
    },
    series: echartsSeries,
    backgroundColor: "transparent",
  };

  if (series.length === 0) {
    return (
      <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
        请从左侧选择数据项进行查看
      </div>
    );
  }

  return (
    <div className="w-full h-full">
      <ReactECharts
        ref={(r) => { chartRef.current = r; }}
        option={option}
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "svg" }}
        onEvents={enableDataZoom ? { datazoom: handleDataZoom } : undefined}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
}
