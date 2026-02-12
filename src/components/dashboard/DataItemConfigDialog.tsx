/**
 * 数据项单位与方向配置弹窗
 * 默认：功率 kW、电量 kWh，流入为正流出为负
 */
import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { DataItemDisplayConfig, DataItemUnit } from '../../types/dataItemConfig';

interface DataItemConfigDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (config: DataItemDisplayConfig) => void;
  dataItemKey: string;
  dataItemName?: string;
  initialConfig?: DataItemDisplayConfig | null;
}

const UNIT_OPTIONS: { value: DataItemUnit; label: string }[] = [
  { value: 'W', label: 'W' },
  { value: 'kW', label: 'kW' },
  { value: 'MW', label: 'MW' },
  { value: 'Wh', label: 'Wh' },
  { value: 'kWh', label: 'kWh' },
  { value: 'MWh', label: 'MWh' },
  { value: 'custom', label: '自定义' },
];

function inferDefaultUnit(dataItemName?: string): DataItemUnit {
  if (!dataItemName) return 'kW';
  const lower = dataItemName.toLowerCase();
  if (lower.includes('energy') || lower.includes('capacity')) return 'kWh';
  return 'kW';
}

export default function DataItemConfigDialog({
  open,
  onClose,
  onSave,
  dataItemKey,
  dataItemName,
  initialConfig,
}: DataItemConfigDialogProps) {
  const [unit, setUnit] = useState<DataItemUnit>(initialConfig?.unit ?? inferDefaultUnit(dataItemName));
  const [scaleToStandard, setScaleToStandard] = useState(
    initialConfig?.scaleToStandard != null ? String(initialConfig.scaleToStandard) : ''
  );
  const [invertDirection, setInvertDirection] = useState(initialConfig?.invertDirection ?? false);

  useEffect(() => {
    if (open) {
      setUnit(initialConfig?.unit ?? inferDefaultUnit(dataItemName));
      setScaleToStandard(initialConfig?.scaleToStandard != null ? String(initialConfig.scaleToStandard) : '');
      setInvertDirection(initialConfig?.invertDirection ?? false);
    }
  }, [open, initialConfig, dataItemName]);

  const handleSave = () => {
    const config: DataItemDisplayConfig = {
      unit,
      invertDirection,
    };
    if (unit === 'custom' && scaleToStandard) {
      const scale = parseFloat(scaleToStandard);
      if (!isNaN(scale)) config.scaleToStandard = scale;
    }
    onSave(config);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-sm border border-gray-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-800">数据项配置</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-500">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-4 py-3 space-y-3">
          <div className="text-xs text-gray-500 truncate" title={dataItemKey}>
            {dataItemKey}
          </div>
          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">单位</label>
            <select
              value={unit}
              onChange={(e) => setUnit(e.target.value as DataItemUnit)}
              className="w-full text-xs border border-gray-300 rounded px-2 py-1.5 bg-white"
            >
              {UNIT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          {unit === 'custom' && (
            <div>
              <label className="text-xs font-medium text-gray-700 block mb-1">
                换算系数（原始值 × 系数 = 标准单位）
              </label>
              <input
                type="number"
                step="any"
                value={scaleToStandard}
                onChange={(e) => setScaleToStandard(e.target.value)}
                placeholder="如 0.001"
                className="w-full text-xs border border-gray-300 rounded px-2 py-1.5"
              />
            </div>
          )}
          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={invertDirection}
                onChange={(e) => setInvertDirection(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600"
              />
              <span className="text-xs text-gray-700">取反方向</span>
            </label>
            <p className="text-xs text-gray-400 mt-0.5">数据源方向与默认（流入为正）相反时勾选</p>
          </div>
        </div>
        <div className="px-4 py-3 border-t border-gray-200 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  );
}
