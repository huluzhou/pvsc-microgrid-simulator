/**
 * 设备属性面板组件 - 浅色主题
 */
import { useState, useEffect, useMemo } from 'react';
import { X } from 'lucide-react';
import { DeviceType, DEVICE_TYPE_TO_CN } from '../../constants/deviceTypes';

interface DevicePropertiesPanelProps {
  device: {
    id: string;
    name: string;
    deviceType: string;
    properties: Record<string, any>;
  };
  onClose: () => void;
  onUpdate: (deviceId: string, updates: { name: string; properties: Record<string, any> }) => void;
}

// 设备属性字段定义
const DEVICE_PROPERTY_FIELDS: Record<string, Array<{
  key: string;
  label: string;
  type: 'number' | 'text' | 'select';
  unit?: string;
  options?: { value: string; label: string }[];
  defaultValue?: any;
}>> = {
  bus: [
    { key: 'voltage_kv', label: '额定电压', type: 'number', unit: 'kV', defaultValue: 10 },
  ],
  line: [
    { key: 'length_km', label: '长度', type: 'number', unit: 'km', defaultValue: 1 },
    { key: 'r_ohm_per_km', label: '电阻', type: 'number', unit: 'Ω/km', defaultValue: 0.1 },
    { key: 'x_ohm_per_km', label: '电抗', type: 'number', unit: 'Ω/km', defaultValue: 0.1 },
  ],
  transformer: [
    { key: 'sn_mva', label: '额定容量', type: 'number', unit: 'MVA', defaultValue: 1 },
    { key: 'hv_kv', label: '高压侧电压', type: 'number', unit: 'kV', defaultValue: 10 },
    { key: 'lv_kv', label: '低压侧电压', type: 'number', unit: 'kV', defaultValue: 0.4 },
  ],
  switch: [
    { key: 'is_closed', label: '开关状态', type: 'select', options: [
      { value: 'true', label: '闭合' },
      { value: 'false', label: '断开' },
    ], defaultValue: 'true' },
  ],
  static_generator: [
    { key: 'rated_power_kw', label: '额定功率', type: 'number', unit: 'kW', defaultValue: 100 },
    { key: 'efficiency', label: '效率', type: 'number', unit: '%', defaultValue: 95 },
  ],
  storage: [
    { key: 'capacity_kwh', label: '容量', type: 'number', unit: 'kWh', defaultValue: 100 },
    { key: 'max_power_kw', label: '最大功率', type: 'number', unit: 'kW', defaultValue: 50 },
    { key: 'initial_soc', label: '初始SOC', type: 'number', unit: '%', defaultValue: 50 },
  ],
  load: [
    { key: 'rated_power_kw', label: '额定功率', type: 'number', unit: 'kW', defaultValue: 50 },
    { key: 'power_factor', label: '功率因数', type: 'number', defaultValue: 0.9 },
  ],
  charger: [
    { key: 'rated_power_kw', label: '额定功率', type: 'number', unit: 'kW', defaultValue: 60 },
    { key: 'charger_type', label: '充电桩类型', type: 'select', options: [
      { value: 'dc_fast', label: '直流快充' },
      { value: 'ac_slow', label: '交流慢充' },
    ], defaultValue: 'dc_fast' },
  ],
  meter: [
    { key: 'meter_type', label: '电表类型', type: 'select', options: [
      { value: 'energy', label: '电能表' },
      { value: 'power', label: '功率表' },
    ], defaultValue: 'energy' },
  ],
  external_grid: [
    { key: 'voltage_kv', label: '电压等级', type: 'number', unit: 'kV', defaultValue: 10 },
    { key: 'short_circuit_power_mva', label: '短路容量', type: 'number', unit: 'MVA', defaultValue: 100 },
  ],
};

export default function DevicePropertiesPanel({
  device,
  onClose,
  onUpdate,
}: DevicePropertiesPanelProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});

  const deviceType = device.deviceType as DeviceType;
  const propertyFields = useMemo(() => 
    DEVICE_PROPERTY_FIELDS[deviceType] || [], 
    [deviceType]
  );

  useEffect(() => {
    const initialData: Record<string, any> = {
      name: device.name,
    };
    
    propertyFields.forEach((field) => {
      initialData[field.key] = device.properties[field.key] ?? field.defaultValue;
    });
    
    setFormData(initialData);
  }, [device, propertyFields]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const { name, ...properties } = formData;
    onUpdate(device.id, { name, properties });
  };

  const handleFieldChange = (key: string, value: any) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="absolute right-0 top-0 h-full w-72 bg-white border-l border-gray-200 shadow-lg z-10 flex flex-col">
      {/* 标题栏 */}
      <div className="px-3 py-2 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">设备属性</h2>
          <p className="text-xs text-gray-500">
            {DEVICE_TYPE_TO_CN[deviceType] || deviceType}
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-gray-100 transition-colors"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* 表单内容 */}
      <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* 设备名称 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            设备名称
          </label>
          <input
            type="text"
            value={formData.name || ''}
            onChange={(e) => handleFieldChange('name', e.target.value)}
            className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* 设备ID */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            设备ID
          </label>
          <input
            type="text"
            value={device.id}
            disabled
            className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
          />
        </div>

        {/* 动态属性字段 */}
        {propertyFields.map((field) => (
          <div key={field.key}>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              {field.label}
              {field.unit && <span className="text-gray-400 ml-1">({field.unit})</span>}
            </label>
            
            {field.type === 'number' && (
              <input
                type="number"
                step="any"
                value={formData[field.key] ?? ''}
                onChange={(e) => handleFieldChange(field.key, parseFloat(e.target.value) || 0)}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            )}
            
            {field.type === 'text' && (
              <input
                type="text"
                value={formData[field.key] ?? ''}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            )}
            
            {field.type === 'select' && field.options && (
              <select
                value={formData[field.key] ?? ''}
                onChange={(e) => handleFieldChange(field.key, e.target.value)}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              >
                {field.options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
          </div>
        ))}
      </form>

      {/* 底部按钮 */}
      <div className="px-3 py-2 border-t border-gray-200 flex gap-2">
        <button
          type="button"
          onClick={handleSubmit}
          className="flex-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-white text-sm transition-colors"
        >
          保存
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex-1 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 text-sm transition-colors"
        >
          取消
        </button>
      </div>
    </div>
  );
}
