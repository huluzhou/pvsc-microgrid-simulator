/**
 * 性能分析数据项映射弹窗
 * 用户为各数据角色指定对应的数据列或手动输入值
 */
import { useState, useEffect } from 'react';
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

/** 分析标准选项 */
export const PERFORMANCE_STANDARDS = [
  { id: 'GB_T_36548_2024', label: 'GB/T 36548-2024 电化学储能接入电网测试' },
  { id: 'GB_T_34930_2017', label: 'GB/T 34930-2017 微电网运行控制' },
  { id: 'GB_T_36549_2018', label: 'GB/T 36549-2018 储能运行指标及评价' },
  { id: 'IEEE_2836_2021', label: 'IEEE 2836-2021 光储充储能性能测试' },
  { id: 'IEEE_1679_2020', label: 'IEEE 1679-2020 储能表征与评价' },
  { id: 'FEMP_BESS', label: 'FEMP BESS 效率与性能比' },
];

const ALIGNMENT_OPTIONS = [
  { value: 'ffill', label: '前向填充' },
  { value: 'linear', label: '线性插值' },
  { value: 'valid_only', label: '仅有效值' },
];

interface PerformanceDataMappingDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (mapping: PerformanceDataMapping) => void;
  availableColumns: AvailableColumn[];
  selectedStandards: string[];
  initialMapping?: Partial<PerformanceDataMapping> | null;
}

export default function PerformanceDataMappingDialog({
  open,
  onClose,
  onConfirm,
  availableColumns,
  selectedStandards,
  initialMapping,
}: PerformanceDataMappingDialogProps) {
  const [measuredPowerKey, setMeasuredPowerKey] = useState('');
  const [referencePowerKey, setReferencePowerKey] = useState('');
  const [ratedPowerKw, setRatedPowerKw] = useState<string>('');
  const [ratedCapacityKwh, setRatedCapacityKwh] = useState<string>('');
  const [alignmentMethod, setAlignmentMethod] = useState('ffill');

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
    onConfirm({
      measured_power_key: measuredPowerKey.trim(),
      reference_power_key: referencePowerKey.trim() || null,
      rated_power_kw: ratedPowerKw ? parseFloat(ratedPowerKw) : null,
      rated_capacity_kwh: ratedCapacityKwh ? parseFloat(ratedCapacityKwh) : null,
      alignment_method: alignmentMethod,
    });
    onClose();
  };

  if (!open) return null;

  const canConfirm = measuredPowerKey.trim().length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-800">性能分析数据项映射</h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          {selectedStandards.length > 0 && (
            <div className="text-xs text-gray-500">
              已选标准：{selectedStandards.map((s) => PERFORMANCE_STANDARDS.find((st) => st.id === s)?.label ?? s).join('、')}
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
            <p className="text-xs text-gray-400 mt-0.5">用于响应时间、控制偏差、可用率等指标</p>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">额定功率 (kW)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={ratedPowerKw}
              onChange={(e) => setRatedPowerKw(e.target.value)}
              placeholder="手动输入"
              className="w-full text-xs border border-gray-300 rounded px-2 py-1.5"
            />
            <p className="text-xs text-gray-400 mt-0.5">用于控制偏差、功率利用率</p>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">额定容量 (kWh)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={ratedCapacityKwh}
              onChange={(e) => setRatedCapacityKwh(e.target.value)}
              placeholder="手动输入"
              className="w-full text-xs border border-gray-300 rounded px-2 py-1.5"
            />
            <p className="text-xs text-gray-400 mt-0.5">用于容量比、容量利用率</p>
          </div>

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
          {!canConfirm && <span className="text-xs text-red-500">请指定实测功率数据项</span>}
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
