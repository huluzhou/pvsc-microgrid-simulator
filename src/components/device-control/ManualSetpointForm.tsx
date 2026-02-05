/**
 * 手动功率设置表单组件 - 浅色主题
 * 支持按拓扑中的额定功率限制滑块范围（额定功率范围内手动设置）
 */
import { useState, useEffect, useCallback } from 'react';
import { ManualSetpoint } from '../../types/dataSource';

interface ManualSetpointFormProps {
  deviceName: string;
  /** 拓扑中的额定功率（kW），用于滑块 min/max；未设置时默认 500 */
  ratedPowerKw?: number;
  initialValue?: ManualSetpoint;
  onSave: (setpoint: ManualSetpoint) => void;
  onCancel: () => void;
}

const DEFAULT_RATED_KW = 500;

export default function ManualSetpointForm({ deviceName, ratedPowerKw, initialValue, onSave, onCancel }: ManualSetpointFormProps) {
  const maxKw = Math.max(1, Number(ratedPowerKw) || DEFAULT_RATED_KW);
  const [activePower, setActivePower] = useState(initialValue?.activePower ?? 0);
  const [reactivePower, setReactivePower] = useState(initialValue?.reactivePower ?? 0);

  useEffect(() => {
    if (initialValue) {
      setActivePower(initialValue.activePower);
      setReactivePower(initialValue.reactivePower);
    }
  }, [initialValue]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    onSave({ activePower, reactivePower });
  }, [activePower, reactivePower, onSave]);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">手动功率设置</h3>
        <span className="text-xs text-gray-500">{deviceName}</span>
      </div>
      {ratedPowerKw != null && ratedPowerKw > 0 && (
        <div className="text-xs text-gray-500 mb-2">额定功率范围：±{maxKw} kW（来自拓扑）</div>
      )}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">有功功率 P (kW)</label>
          <div className="flex items-center gap-2">
            <input type="range" min={-maxKw} max={maxKw} step="1" value={activePower} onChange={(e) => setActivePower(Number(e.target.value))} className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
            <input type="number" min={-maxKw} max={maxKw} value={activePower} onChange={(e) => setActivePower(Number(e.target.value))} className="w-20 px-2 py-1 bg-white border border-gray-300 rounded text-sm text-right" />
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>-{maxKw} kW</span><span>+{maxKw} kW</span>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">无功功率 Q (kVar)</label>
          <div className="flex items-center gap-2">
            <input type="range" min={-maxKw} max={maxKw} step="1" value={reactivePower} onChange={(e) => setReactivePower(Number(e.target.value))} className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
            <input type="number" min={-maxKw} max={maxKw} value={reactivePower} onChange={(e) => setReactivePower(Number(e.target.value))} className="w-20 px-2 py-1 bg-white border border-gray-300 rounded text-sm text-right" />
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>-{maxKw} kVar</span><span>+{maxKw} kVar</span>
          </div>
        </div>
        <div className="p-2 bg-gray-50 rounded border border-gray-200">
          <div className="text-xs text-gray-500 mb-1">设定值预览</div>
          <div className="grid grid-cols-2 gap-2">
            <div><div className="text-lg font-bold text-blue-600">{activePower.toFixed(1)} kW</div><div className="text-xs text-gray-500">有功功率</div></div>
            <div><div className="text-lg font-bold text-purple-600">{reactivePower.toFixed(1)} kVar</div><div className="text-xs text-gray-500">无功功率</div></div>
          </div>
        </div>
        <div className="flex gap-2">
          <button type="submit" className="flex-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-white text-sm transition-colors">应用设定</button>
          <button type="button" onClick={onCancel} className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 text-sm transition-colors">取消</button>
        </div>
      </form>
    </div>
  );
}
