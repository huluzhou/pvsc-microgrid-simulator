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
    const loadDeviceMetadata = async () => {
      const initialData: Record<string, any> = {
        name: device.name,
      };
      
      propertyFields.forEach((field) => {
        initialData[field.key] = device.properties[field.key] ?? field.defaultValue;
      });
      
      // 从设备 properties 中读取仿真参数（如果已保存）
      initialData.response_delay = device.properties.response_delay ?? null;
      initialData.measurement_error = device.properties.measurement_error ?? null;
      initialData.data_collection_frequency = device.properties.data_collection_frequency ?? null;
      
      // 尝试从后端获取设备元数据（如果 properties 中没有）
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const metadata = await invoke<{
          response_delay?: number | null;
          measurement_error?: number | null;
          data_collection_frequency?: number | null;
        }>('get_device', { deviceId: device.id });
        
        // 如果 properties 中没有，使用元数据中的值
        if (initialData.response_delay === null && metadata.response_delay !== null && metadata.response_delay !== undefined) {
          initialData.response_delay = metadata.response_delay;
        }
        if (initialData.measurement_error === null && metadata.measurement_error !== null && metadata.measurement_error !== undefined) {
          initialData.measurement_error = metadata.measurement_error;
        }
        if (initialData.data_collection_frequency === null && metadata.data_collection_frequency !== null && metadata.data_collection_frequency !== undefined) {
          initialData.data_collection_frequency = metadata.data_collection_frequency;
        }
      } catch (error) {
        // 如果获取失败，使用 properties 中的值（已设置）
        console.warn('Failed to load device metadata:', error);
      }
      
      setFormData(initialData);
    };
    
    loadDeviceMetadata();
  }, [device, propertyFields]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const { name, response_delay, measurement_error, data_collection_frequency, ...properties } = formData;
    
    // 将仿真参数也保存到 properties 中，以便保存到拓扑文件
    const updatedProperties = {
      ...properties,
      ...(response_delay !== null && response_delay !== undefined ? { response_delay } : {}),
      ...(measurement_error !== null && measurement_error !== undefined ? { measurement_error } : {}),
      ...(data_collection_frequency !== null && data_collection_frequency !== undefined ? { data_collection_frequency } : {}),
    };
    
    // 更新设备基本属性和仿真参数
    onUpdate(device.id, { name, properties: updatedProperties });
    
    // 更新设备仿真参数（通过 Tauri 命令，保存到设备元数据）
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('update_device_config', {
        config: {
          device_id: device.id,
          work_mode: null,
          response_delay: response_delay !== null && response_delay !== undefined ? response_delay : null,
          measurement_error: measurement_error !== null && measurement_error !== undefined ? measurement_error : null,
          data_collection_frequency: data_collection_frequency !== null && data_collection_frequency !== undefined ? data_collection_frequency : null,
        },
      });
    } catch (error) {
      console.error('Failed to update device config:', error);
      // 不阻止保存，只记录错误
    }
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

        {/* 连接属性字段（只读，由连接联动自动更新） */}
        {(deviceType === 'static_generator' || deviceType === 'storage' || deviceType === 'load' || deviceType === 'charger' || deviceType === 'external_grid') && device.properties.bus !== undefined && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              连接的母线索引 (bus)
            </label>
            <input
              type="text"
              value={device.properties.bus ?? ''}
              disabled
              className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
            />
          </div>
        )}
        
        {deviceType === 'line' && (
          <>
            {device.properties.from_bus !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  起始母线索引 (from_bus)
                </label>
                <input
                  type="text"
                  value={device.properties.from_bus ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
            {device.properties.to_bus !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  终止母线索引 (to_bus)
                </label>
                <input
                  type="text"
                  value={device.properties.to_bus ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
          </>
        )}
        
        {deviceType === 'transformer' && (
          <>
            {device.properties.hv_bus !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  高压侧母线索引 (hv_bus)
                </label>
                <input
                  type="text"
                  value={device.properties.hv_bus ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
            {device.properties.lv_bus !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  低压侧母线索引 (lv_bus)
                </label>
                <input
                  type="text"
                  value={device.properties.lv_bus ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
          </>
        )}
        
        {deviceType === 'switch' && (
          <>
            {device.properties.bus !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  连接母线索引 (bus)
                </label>
                <input
                  type="text"
                  value={device.properties.bus ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
            {device.properties.element_type !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  元素类型 (element_type)
                </label>
                <input
                  type="text"
                  value={device.properties.element_type ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
            {device.properties.element !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  元素索引 (element)
                </label>
                <input
                  type="text"
                  value={device.properties.element ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
          </>
        )}
        
        {deviceType === 'meter' && (
          <>
            {device.properties.element_type !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  连接元件类型 (element_type)
                </label>
                <input
                  type="text"
                  value={device.properties.element_type ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
            {device.properties.element !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  连接元件索引 (element)
                </label>
                <input
                  type="text"
                  value={device.properties.element ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
            {device.properties.side !== undefined && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  连接端口 (side)
                </label>
                <input
                  type="text"
                  value={device.properties.side ?? ''}
                  disabled
                  className="w-full px-2 py-1.5 bg-gray-50 border border-gray-200 rounded text-sm text-gray-500"
                />
              </div>
            )}
          </>
        )}

        {/* 分隔线 */}
        {((deviceType === 'line' && (device.properties.from_bus !== undefined || device.properties.to_bus !== undefined)) ||
          (deviceType === 'transformer' && (device.properties.hv_bus !== undefined || device.properties.lv_bus !== undefined)) ||
          (deviceType === 'switch' && (device.properties.bus !== undefined || device.properties.element_type !== undefined || device.properties.element !== undefined)) ||
          (deviceType === 'meter' && (device.properties.element_type !== undefined || device.properties.element !== undefined)) ||
          ((deviceType === 'static_generator' || deviceType === 'storage' || deviceType === 'load' || deviceType === 'charger' || deviceType === 'external_grid') && device.properties.bus !== undefined)) && (
          <div className="border-t border-gray-200 my-3"></div>
        )}

        {/* 仿真参数设置 */}
        <div className="border-t border-gray-200 my-3"></div>
        <div className="mb-2">
          <h3 className="text-xs font-semibold text-gray-700 mb-2">仿真参数</h3>
        </div>
        
        {/* 响应延迟 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            响应延迟
            <span className="text-gray-400 ml-1">(秒)</span>
          </label>
          <input
            type="number"
            step="0.001"
            min="0"
            value={formData.response_delay ?? (device.properties.response_delay ?? '')}
            onChange={(e) => handleFieldChange('response_delay', e.target.value ? parseFloat(e.target.value) : null)}
            className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            placeholder="0.1"
          />
          <p className="text-xs text-gray-400 mt-1">设备响应延迟时间（秒），例如：0.1 表示 100ms</p>
        </div>

        {/* 测量误差 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            测量误差
            <span className="text-gray-400 ml-1">(%)</span>
          </label>
          <input
            type="number"
            step="0.1"
            min="0"
            max="100"
            value={formData.measurement_error ?? (device.properties.measurement_error ?? '')}
            onChange={(e) => handleFieldChange('measurement_error', e.target.value ? parseFloat(e.target.value) : null)}
            className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            placeholder="1.0"
          />
          <p className="text-xs text-gray-400 mt-1">测量误差百分比，例如：1.0 表示 ±1%</p>
        </div>

        {/* 数据采集频率 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            数据采集频率
            <span className="text-gray-400 ml-1">(秒)</span>
          </label>
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={formData.data_collection_frequency ?? (device.properties.data_collection_frequency ?? '')}
            onChange={(e) => handleFieldChange('data_collection_frequency', e.target.value ? parseFloat(e.target.value) : null)}
            className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            placeholder="1.0"
          />
          <p className="text-xs text-gray-400 mt-1">数据采集间隔时间（秒），例如：1.0 表示每秒采集一次</p>
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
