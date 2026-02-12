import type { ReactNode } from 'react';

/**
 * 分析摘要/详情可读化展示：将 JSON 转为结构化阅读形式
 */
interface AnalysisSummaryViewProps {
  data: Record<string, unknown>;
  depth?: number;
}

/** 指标名中文映射 */
const LABEL_MAP: Record<string, string> = {
  error: '错误',
  mean_kw: '均值 (kW)',
  max_kw: '最大值 (kW)',
  min_kw: '最小值 (kW)',
  std_kw: '标准差 (kW)',
  energy_charge_kwh: '充电量 (kWh)',
  energy_discharge_kwh: '放电量 (kWh)',
  round_trip_efficiency_pct: '往返效率 (%)',
  ramp_rate_max_kw_per_s: '最大爬升率 (kW/s)',
  performance_ratio: '性能比',
  time_utilization_pct: '时间利用率 (%)',
  control_deviation_pct: '有功功率控制偏差 (%)',
  rmse_kw: '参考信号 RMSE (kW)',
  correlation: '相关系数',
  availability_pct: '可用率 (%)',
  response_time_s: '响应时间 (s)',
  settling_time_s: '调节时间 (s)',
  transition_time_s: '充放电转换时间 (s)',
  capacity_utilization_pct: '容量利用率 (%)',
  power_utilization_pct: '功率利用率 (%)',
  total_energy_kwh: '总电量 (kWh)',
  total_cost_yuan: '总电费 (元)',
  hourly_energy_kwh: '分时电量 (kWh)',
  points: '数据点数',
};

function formatValue(v: unknown): string {
  if (v == null) return '—';
  if (typeof v === 'number') {
    if (Number.isNaN(v)) return '—';
    if (Number.isInteger(v)) return String(v);
    return v.toFixed(4).replace(/\.?0+$/, '');
  }
  if (typeof v === 'boolean') return v ? '是' : '否';
  if (typeof v === 'string') return v;
  if (Array.isArray(v)) return v.map(formatValue).join(', ');
  return '';
}

function renderValue(v: unknown): ReactNode {
  if (v == null) return <span className="text-gray-400">—</span>;
  if (typeof v === 'number') {
    if (Number.isNaN(v)) return <span className="text-gray-400">—</span>;
    const s = Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/\.?0+$/, '');
    return <span className="font-medium text-gray-800">{s}</span>;
  }
  if (typeof v === 'boolean') return <span className="text-gray-800">{v ? '是' : '否'}</span>;
  if (typeof v === 'string') return <span className="text-gray-800">{v}</span>;
  if (Array.isArray(v)) {
    return (
      <div className="text-gray-800">
        {v.length <= 12 ? v.map(formatValue).join(', ') : `${v.length} 项`}
      </div>
    );
  }
  if (typeof v === 'object' && v !== null) {
    return (
      <div className="ml-2 mt-1 pl-2 border-l-2 border-gray-200 space-y-1">
        {Object.entries(v as Record<string, unknown>).map(([k, val]) => (
          <div key={k} className="text-xs">
            <span className="text-gray-500">{LABEL_MAP[k] || k}:</span>{' '}
            {typeof val === 'object' && val !== null && !Array.isArray(val) ? (
              renderValue(val)
            ) : (
              <span className="text-gray-800">{formatValue(val)}</span>
            )}
          </div>
        ))}
      </div>
    );
  }
  return null;
}

export default function AnalysisSummaryView({ data, depth = 0 }: AnalysisSummaryViewProps) {
  if (!data || typeof data !== 'object') return null;

  const entries = Object.entries(data);
  if (entries.length === 0) return null;

  const isError = 'error' in data && typeof data.error === 'string';
  if (isError) {
    return (
      <div className="text-sm text-red-600">{String(data.error)}</div>
    );
  }

  return (
    <div className="space-y-2 text-sm">
      {entries.map(([key, value]) => {
        const label = LABEL_MAP[key] || key;
        const isNested = typeof value === 'object' && value !== null && !Array.isArray(value);
        return (
          <div key={key} className="break-words">
            <div className="flex items-start gap-2">
              <span className="text-gray-500 flex-shrink-0">{label}:</span>
              {isNested ? (
                <div className="flex-1 min-w-0">
                  <div className="bg-white/60 rounded p-2 border border-gray-100">
                    <AnalysisSummaryView data={value as Record<string, unknown>} depth={depth + 1} />
                  </div>
                </div>
              ) : (
                <span className="flex-1 min-w-0">{renderValue(value)}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
