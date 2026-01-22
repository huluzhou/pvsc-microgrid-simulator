/**
 * 随机数据源配置表单组件 - 浅色主题
 */
import { useState, useEffect, useCallback } from 'react';
import { RandomConfig } from '../../types/dataSource';

interface RandomConfigFormProps {
  deviceName: string;
  initialValue?: RandomConfig;
  onSave: (config: RandomConfig) => void;
  onCancel: () => void;
}

export default function RandomConfigForm({ deviceName, initialValue, onSave, onCancel }: RandomConfigFormProps) {
  const [minPower, setMinPower] = useState(initialValue?.minPower ?? 0);
  const [maxPower, setMaxPower] = useState(initialValue?.maxPower ?? 100);
  const [updateInterval, setUpdateInterval] = useState(initialValue?.updateInterval ?? 1);
  const [volatility, setVolatility] = useState(initialValue?.volatility ?? 0.1);

  useEffect(() => {
    if (initialValue) {
      setMinPower(initialValue.minPower);
      setMaxPower(initialValue.maxPower);
      setUpdateInterval(initialValue.updateInterval);
      setVolatility(initialValue.volatility);
    }
  }, [initialValue]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    onSave({ minPower, maxPower, updateInterval, volatility });
  }, [minPower, maxPower, updateInterval, volatility, onSave]);

  const isPowerRangeValid = minPower <= maxPower;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">随机数据配置</h3>
        <span className="text-xs text-gray-500">{deviceName}</span>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">最小功率 (kW)</label>
            <input type="number" value={minPower} onChange={(e) => setMinPower(Number(e.target.value))} className="w-full px-2 py-1 bg-white border border-gray-300 rounded text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">最大功率 (kW)</label>
            <input type="number" value={maxPower} onChange={(e) => setMaxPower(Number(e.target.value))} className="w-full px-2 py-1 bg-white border border-gray-300 rounded text-sm" />
          </div>
        </div>
        {!isPowerRangeValid && <div className="text-xs text-red-500">最小功率不能大于最大功率</div>}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">更新间隔 (秒)</label>
          <div className="flex items-center gap-2">
            <input type="range" min="0.1" max="10" step="0.1" value={updateInterval} onChange={(e) => setUpdateInterval(Number(e.target.value))} className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
            <span className="text-gray-700 w-12 text-xs text-right">{updateInterval.toFixed(1)}s</span>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">波动率 (0-100%)</label>
          <div className="flex items-center gap-2">
            <input type="range" min="0" max="1" step="0.01" value={volatility} onChange={(e) => setVolatility(Number(e.target.value))} className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
            <span className="text-gray-700 w-12 text-xs text-right">{(volatility * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className="p-2 bg-gray-50 rounded border border-gray-200">
          <div className="text-xs text-gray-500 mb-1">配置预览</div>
          <div className="text-xs text-gray-700">{minPower} ~ {maxPower} kW, 每{updateInterval}s更新</div>
        </div>
        <div className="flex gap-2">
          <button type="submit" disabled={!isPowerRangeValid} className="flex-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-white text-sm transition-colors disabled:opacity-50">应用配置</button>
          <button type="button" onClick={onCancel} className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 text-sm transition-colors">取消</button>
        </div>
      </form>
    </div>
  );
}
