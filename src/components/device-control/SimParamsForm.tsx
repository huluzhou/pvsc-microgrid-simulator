/**
 * 设备级仿真参数配置表单：采集频率、响应延迟、测量误差
 */
import { useState, useCallback } from 'react';
import { Settings, Clock, Activity, Gauge } from 'lucide-react';
import { DeviceSimParams } from '../../types/dataSource';

interface SimParamsFormProps {
  deviceName: string;
  initialValue?: DeviceSimParams;
  onSave: (params: DeviceSimParams) => void;
  onCancel: () => void;
}

const DEFAULT_PARAMS: DeviceSimParams = {
  samplingIntervalMs: 0,
  responseDelayMs: 0,
  measurementErrorPct: 0,
};

export default function SimParamsForm({ deviceName, initialValue, onSave, onCancel }: SimParamsFormProps) {
  const [params, setParams] = useState<DeviceSimParams>(initialValue ?? DEFAULT_PARAMS);

  const handleChange = useCallback((field: keyof DeviceSimParams, value: number) => {
    setParams((prev) => ({ ...prev, [field]: value }));
  }, []);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    onSave(params);
  }, [params, onSave]);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1">
          <Settings className="w-3.5 h-3.5" />仿真参数
        </h3>
        <span className="text-xs text-gray-500">{deviceName}</span>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* 采集频率 */}
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-gray-600 mb-1">
            <Clock className="w-3 h-3" />采集频率（Modbus 元数据更新间隔）
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              step="100"
              value={params.samplingIntervalMs}
              onChange={(e) => handleChange('samplingIntervalMs', Number(e.target.value))}
              className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-sm"
            />
            <span className="text-xs text-gray-500 shrink-0">毫秒</span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">0 = 每步更新。可设置大于仿真周期的值以降低更新频率。</p>
        </div>

        {/* 响应延迟 */}
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-gray-600 mb-1">
            <Activity className="w-3 h-3" />响应延迟（Modbus 指令到功率响应）
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              step="100"
              value={params.responseDelayMs}
              onChange={(e) => handleChange('responseDelayMs', Number(e.target.value))}
              className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-sm"
            />
            <span className="text-xs text-gray-500 shrink-0">毫秒</span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">0 = 无延迟。收到指令后经过此时间才生效（阶跃响应）。</p>
        </div>

        {/* 测量误差 */}
        <div>
          <label className="flex items-center gap-1 text-xs font-medium text-gray-600 mb-1">
            <Gauge className="w-3 h-3" />测量误差
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="50"
              step="0.1"
              value={params.measurementErrorPct}
              onChange={(e) => handleChange('measurementErrorPct', Number(e.target.value))}
              className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-sm"
            />
            <span className="text-xs text-gray-500 shrink-0">%</span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">0 = 无误差。在潮流结果上叠加高斯随机扰动。</p>
        </div>

        <div className="flex gap-2">
          <button type="submit" className="flex-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-white text-sm transition-colors">应用参数</button>
          <button type="button" onClick={onCancel} className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 text-sm transition-colors">取消</button>
        </div>
      </form>
    </div>
  );
}
