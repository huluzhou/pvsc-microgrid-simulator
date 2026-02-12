/**
 * 性能分析数据项映射弹窗
 * 根据所选指标动态展示需配置的数据项，并提示用户
 */
import { useState, useEffect, useMemo } from 'react';
import { X } from 'lucide-react';

/** 可选列 */
export interface AvailableColumn {
  key: string;
  label: string;
}

/** 数据角色到 key 的映射（与 Rust PerformanceDataMapping 对应） */
export interface PerformanceDataMapping {
  measured_power_key: string;
  reference_power_key: string | null;
  rated_power_kw: number | null;
  rated_capacity_kwh: number | null;
  alignment_method: string;
}

/** 单指标定义：id、名称、来源标准、所需数据 */
export interface PerformanceIndicator {
  id: string;
  label: string;
  standard: string;
  requiredData: ('measured_power' | 'reference_power' | 'rated_power' | 'rated_capacity')[];
}

/** 性能分析指标列表（默认分析全部），每个指标标注来源标准 */
export const PERFORMANCE_INDICATORS: PerformanceIndicator[] = [
  { id: 'mean_kw', label: '均值', standard: '通用', requiredData: ['measured_power'] },
  { id: 'max_kw', label: '最大值', standard: '通用', requiredData: ['measured_power'] },
  { id: 'min_kw', label: '最小值', standard: '通用', requiredData: ['measured_power'] },
  { id: 'std_kw', label: '标准差/功率波动性', standard: 'GB/T 34930', requiredData: ['measured_power'] },
  { id: 'energy_charge_kwh', label: '充电量', standard: 'IEEE 2836/1679/FEMP', requiredData: ['measured_power'] },
  { id: 'energy_discharge_kwh', label: '放电量', standard: 'IEEE 2836/1679/FEMP', requiredData: ['measured_power'] },
  { id: 'round_trip_efficiency_pct', label: '往返效率', standard: 'IEEE 2836/1679/FEMP', requiredData: ['measured_power'] },
  { id: 'ramp_rate_max_kw_per_s', label: '最大爬升率', standard: 'GB/T 36548、IEEE 2836', requiredData: ['measured_power'] },
  { id: 'performance_ratio', label: '性能比', standard: 'FEMP', requiredData: ['measured_power'] },
  { id: 'time_utilization_pct', label: '时间利用率', standard: 'GB/T 36549', requiredData: ['measured_power'] },
  { id: 'control_deviation_pct', label: '有功功率控制偏差', standard: 'GB/T 36548', requiredData: ['measured_power', 'reference_power', 'rated_power'] },
  { id: 'rmse_kw', label: '参考信号 RMSE', standard: 'IEEE 2836', requiredData: ['measured_power', 'reference_power'] },
  { id: 'correlation', label: '参考信号相关系数', standard: 'IEEE 2836', requiredData: ['measured_power', 'reference_power'] },
  { id: 'availability_pct', label: '可用率', standard: 'FEMP', requiredData: ['measured_power', 'reference_power'] },
  { id: 'response_time_s', label: '响应时间', standard: 'GB/T 36548', requiredData: ['measured_power', 'reference_power'] },
  { id: 'settling_time_s', label: '调节时间', standard: 'GB/T 36548', requiredData: ['measured_power', 'reference_power'] },
  { id: 'transition_time_s', label: '充放电转换时间', standard: 'GB/T 36548', requiredData: ['measured_power', 'reference_power'] },
  { id: 'capacity_utilization_pct', label: '容量利用率', standard: 'GB/T 36549', requiredData: ['measured_power', 'rated_capacity'] },
  { id: 'power_utilization_pct', label: '功率利用率', standard: 'GB/T 36549', requiredData: ['measured_power', 'rated_power'] },
  { id: 'demonstrated_capacity_kwh', label: 'Demonstrated Capacity', standard: 'FEMP', requiredData: ['measured_power'] },
  { id: 'capacity_ratio', label: '容量比', standard: 'FEMP', requiredData: ['measured_power', 'rated_capacity'] },
];

const ALIGNMENT_OPTIONS = [
  { value: 'ffill', label: '前向填充' },
  { value: 'linear', label: '线性插值' },
  { value: 'valid_only', label: '仅有效值' },
];

/** 根据所选指标计算所需数据角色；未选任何指标时至少需要实测功率 */
export function getRequiredDataRoles(selectedIndicatorIds: string[]): Set<'measured_power' | 'reference_power' | 'rated_power' | 'rated_capacity'> {
  const roles = new Set<'measured_power' | 'reference_power' | 'rated_power' | 'rated_capacity'>();
  for (const ind of PERFORMANCE_INDICATORS) {
    if (selectedIndicatorIds.includes(ind.id)) {
      for (const r of ind.requiredData) roles.add(r);
    }
  }
  if (roles.size === 0) roles.add('measured_power');
  return roles;
}

/** 根据所选指标生成需配置提示文案 */
export function getRequiredDataPrompt(roles: Set<string>): string[] {
  const lines: string[] = [];
  if (roles.has('measured_power')) lines.push('• 实测功率：选择功率数据列');
  if (roles.has('reference_power')) lines.push('• 功率指令/参考信号：选择参考功率列（用于控制偏差、RMSE、可用率、响应时间等）');
  if (roles.has('rated_power')) lines.push('• 额定功率：手动输入 kW（用于控制偏差、功率利用率）');
  if (roles.has('rated_capacity')) lines.push('• 额定容量：手动输入 kWh（用于容量比、容量利用率）');
  return lines;
}

interface PerformanceDataMappingDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (mapping: PerformanceDataMapping) => void;
  availableColumns: AvailableColumn[];
  selectedIndicatorIds: string[];
  initialMapping?: Partial<PerformanceDataMapping> | null;
}

export default function PerformanceDataMappingDialog({
  open,
  onClose,
  onConfirm,
  availableColumns,
  selectedIndicatorIds,
  initialMapping,
}: PerformanceDataMappingDialogProps) {
  const [measuredPowerKey, setMeasuredPowerKey] = useState('');
  const [referencePowerKey, setReferencePowerKey] = useState('');
  const [ratedPowerKw, setRatedPowerKw] = useState<string>('');
  const [ratedCapacityKwh, setRatedCapacityKwh] = useState<string>('');
  const [alignmentMethod, setAlignmentMethod] = useState('ffill');

  const requiredRoles = useMemo(() => getRequiredDataRoles(selectedIndicatorIds), [selectedIndicatorIds]);
  const requiredPrompt = useMemo(() => getRequiredDataPrompt(requiredRoles), [requiredRoles]);

  useEffect(() => {
    if (open) {
      setMeasuredPowerKey(initialMapping?.measured_power_key ?? '');
      setReferencePowerKey(initialMapping?.reference_power_key ?? '');
      setRatedPowerKw(initialMapping?.rated_power_kw != null ? String(initialMapping.rated_power_kw) : '');
      setRatedCapacityKwh(initialMapping?.rated_capacity_kwh != null ? String(initialMapping.rated_capacity_kwh) : '');
      setAlignmentMethod(initialMapping?.alignment_method ?? 'ffill');
    }
  }, [open, initialMapping]);

  const handleConfirm = () => {
    if (!measuredPowerKey.trim()) return;
    const needsRef = requiredRoles.has('reference_power');
    const needsRatedP = requiredRoles.has('rated_power');
    const needsRatedC = requiredRoles.has('rated_capacity');
    if (needsRef && !referencePowerKey.trim()) return;
    if (needsRatedP && (!ratedPowerKw || parseFloat(ratedPowerKw) <= 0)) return;
    if (needsRatedC && (!ratedCapacityKwh || parseFloat(ratedCapacityKwh) <= 0)) return;

    onConfirm({
      measured_power_key: measuredPowerKey.trim(),
      reference_power_key: requiredRoles.has('reference_power') ? (referencePowerKey.trim() || null) : null,
      rated_power_kw: requiredRoles.has('rated_power') && ratedPowerKw ? parseFloat(ratedPowerKw) : null,
      rated_capacity_kwh: requiredRoles.has('rated_capacity') && ratedCapacityKwh ? parseFloat(ratedCapacityKwh) : null,
      alignment_method: alignmentMethod,
    });
    onClose();
  };

  if (!open) return null;

  const needsRef = requiredRoles.has('reference_power');
  const needsRatedP = requiredRoles.has('rated_power');
  const needsRatedC = requiredRoles.has('rated_capacity');

  const canConfirm =
    measuredPowerKey.trim().length > 0 &&
    (!needsRef || referencePowerKey.trim().length > 0) &&
    (!needsRatedP || (ratedPowerKw && parseFloat(ratedPowerKw) > 0)) &&
    (!needsRatedC || (ratedCapacityKwh && parseFloat(ratedCapacityKwh) > 0));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-800">性能分析数据项配置</h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          {requiredPrompt.length > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded p-2 text-xs text-blue-800">
              <div className="font-medium mb-1">根据所选指标，需配置以下数据项：</div>
              {requiredPrompt.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">
              实测功率 <span className="text-red-500">*</span>
            </label>
            <select
              value={measuredPowerKey}
              onChange={(e) => setMeasuredPowerKey(e.target.value)}
              className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 bg-white"
            >
              <option value="">请选择数据项</option>
              {availableColumns.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {needsRef && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">
                功率指令/参考信号 <span className="text-red-500">*</span>
              </label>
              <select
                value={referencePowerKey}
                onChange={(e) => setReferencePowerKey(e.target.value)}
                className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 bg-white"
              >
                <option value="">请选择数据项</option>
                {availableColumns.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {!needsRef && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">功率指令/参考信号</label>
              <select
                value={referencePowerKey}
                onChange={(e) => setReferencePowerKey(e.target.value)}
                className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 bg-white"
              >
                <option value="">不指定</option>
                {availableColumns.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {needsRatedP && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">
                额定功率 (kW) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={ratedPowerKw}
                onChange={(e) => setRatedPowerKw(e.target.value)}
                placeholder="请输入"
                className="w-full text-xs border border-gray-300 rounded px-2 py-1.5"
              />
            </div>
          )}

          {!needsRatedP && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">额定功率 (kW)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={ratedPowerKw}
                onChange={(e) => setRatedPowerKw(e.target.value)}
                placeholder="可选，用于功率利用率"
                className="w-full text-xs border border-gray-300 rounded px-2 py-1.5"
              />
            </div>
          )}

          {needsRatedC && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">
                额定容量 (kWh) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={ratedCapacityKwh}
                onChange={(e) => setRatedCapacityKwh(e.target.value)}
                placeholder="请输入"
                className="w-full text-xs border border-gray-300 rounded px-2 py-1.5"
              />
            </div>
          )}

          {!needsRatedC && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">额定容量 (kWh)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={ratedCapacityKwh}
                onChange={(e) => setRatedCapacityKwh(e.target.value)}
                placeholder="可选，用于容量比、容量利用率"
                className="w-full text-xs border border-gray-300 rounded px-2 py-1.5"
              />
            </div>
          )}

          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">数据对齐方式</label>
            <select
              value={alignmentMethod}
              onChange={(e) => setAlignmentMethod(e.target.value)}
              className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 bg-white"
            >
              {ALIGNMENT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between gap-2">
          {!canConfirm && (
            <span className="text-xs text-red-500">
              {!measuredPowerKey.trim()
                ? '请指定实测功率数据项'
                : needsRef && !referencePowerKey.trim()
                  ? '请指定功率指令/参考信号'
                  : needsRatedP && (!ratedPowerKw || parseFloat(ratedPowerKw) <= 0)
                    ? '请输入额定功率'
                    : needsRatedC && (!ratedCapacityKwh || parseFloat(ratedCapacityKwh) <= 0)
                      ? '请输入额定容量'
                      : '请补全必填项'}
            </span>
          )}
          <div className="flex gap-2 ml-auto">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              disabled={!canConfirm}
              className={`px-3 py-1.5 text-xs rounded ${
                canConfirm ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              确认
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
