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
  allNodes?: Array<{ id: string; data: { deviceType: string } }>; // 所有节点，用于计算端口
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
  allNodes = [],
}: DevicePropertiesPanelProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [newCustomKey, setNewCustomKey] = useState('');
  const [newCustomValue, setNewCustomValue] = useState('');

  const deviceType = device.deviceType as DeviceType;
  const propertyFields = useMemo(() => 
    DEVICE_PROPERTY_FIELDS[deviceType] || [], 
    [deviceType]
  );

  // 保留字段（不作为自定义字段显示）
  const reservedKeys = useMemo(() => {
    const keys = new Set<string>();
    // 基础字段
    keys.add('name');
    // 联动连接字段
    [
      'bus',
      'from_bus',
      'to_bus',
      'hv_bus',
      'lv_bus',
      'element_type',
      'element',
      'side',
    ].forEach(k => keys.add(k));
    // 仿真参数字段
    [
      'response_delay',
      'measurement_error',
      'data_collection_frequency',
    ].forEach(k => keys.add(k));
    // 预定义属性字段
    propertyFields.forEach(f => keys.add(f.key));
    return keys;
  }, [propertyFields]);

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

      // 为需要通信的设备预置通信相关自定义字段（仅在不存在时设置默认值）
      // 注意：外部电网和负载不需要通信配置，因为它们不能直接上传数据
      const needsCommConfig =
        deviceType === 'static_generator' ||  // 光伏
        deviceType === 'storage' ||            // 储能
        deviceType === 'charger' ||            // 充电桩
        deviceType === 'meter';                // 测量设备

      if (needsCommConfig) {
        // IP 默认值
        if (initialData.ip === undefined) {
          initialData.ip = device.properties.ip ?? '0.0.0.0';
        }
        
        // 端口默认值：根据设备类型和同类型设备数量计算
        if (initialData.port === undefined) {
          const existingPort = device.properties.port;
          if (existingPort !== undefined) {
            initialData.port = existingPort;
          } else {
            // 计算同类型设备数量（不包括当前设备）
            const sameTypeCount = allNodes.filter(
              (n) => n.data.deviceType === deviceType && n.id !== device.id
            ).length;
            
            // 根据设备类型设置端口基地址
            let basePort = 5020; // 默认值
            if (deviceType === 'charger') {
              basePort = 702; // 充电桩
            } else if (deviceType === 'meter') {
              basePort = 403; // 电表
            } else if (deviceType === 'static_generator') {
              basePort = 602; // 光伏
            } else if (deviceType === 'storage') {
              basePort = 502; // 储能设备
            }
            // 注意：负载(load)和外部电网(external_grid)不需要通信配置
            
            // 端口 = 基地址 + 同类型设备数量
            initialData.port = basePort + sameTypeCount;
          }
        }
        
        if (initialData.baudrate === undefined) {
          initialData.baudrate = device.properties.baudrate ?? 9600;
        }
        if (initialData.parity === undefined) {
          initialData.parity = device.properties.parity ?? 'none';
        }
        if (initialData.comm_mode === undefined) {
          initialData.comm_mode = device.properties.comm_mode ?? 'tcp';
        }
      }

      // 将已有的自定义字段也一并载入（排除保留字段和空值字段）
      Object.entries(device.properties).forEach(([key, value]) => {
        if (!reservedKeys.has(key)) {
          // 过滤掉空值：null、undefined、空字符串、空对象、空数组
          if (value !== null && 
              value !== undefined && 
              value !== '' &&
              !(typeof value === 'object' && Object.keys(value).length === 0) &&
              !(Array.isArray(value) && value.length === 0)) {
            initialData[key] = value;
          }
        }
      });
      
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
  }, [device, propertyFields, reservedKeys]);

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
    
    // 更新画布上的设备节点（本地状态）
    onUpdate(device.id, { name, properties: updatedProperties });
    
    // 同步到后端 metadata，使设备控制等页面立即生效（额定功率等），无需再点左上角保存
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('update_device_metadata', {
        payload: {
          device_id: device.id,
          name: name ?? device.name,
          properties: updatedProperties,
        },
      });
    } catch (error) {
      console.error('同步设备元数据失败:', error);
      // 不阻止保存，只记录错误
    }
    
    // 更新设备仿真参数（通过 Tauri 命令）
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

  // 删除自定义字段
  const removeCustomField = (key: string) => {
    setFormData((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  // 计算当前自定义字段列表
  const customKeys = useMemo(() => {
    return Object.keys(formData).filter(
      (key) => !reservedKeys.has(key)
    );
  }, [formData, reservedKeys]);

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

        {/* 自定义属性字段 */}
        <div className="border-t border-gray-200 my-3"></div>
        <div className="mb-2">
          <h3 className="text-xs font-semibold text-gray-700 mb-2">自定义属性</h3>
          <p className="text-[11px] text-gray-400">
            这里可以为设备添加额外的自定义属性键值对，这些字段会一并保存在拓扑文件中。
          </p>
        </div>

        {/* 已有自定义字段列表 */}
        {customKeys.map((key) => (
          <div key={key} className="mb-2">
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={key}
                disabled
                className="w-24 px-2 py-1 bg-gray-50 border border-gray-200 rounded text-xs text-gray-500"
              />
              <span className="text-xs text-gray-400 px-1">=</span>

              {/* 针对预定义通信字段使用下拉枚举 */}
              {key === 'baudrate' ? (
                <select
                  value={formData[key] ?? ''}
                  onChange={(e) => handleFieldChange(key, Number(e.target.value))}
                  className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-xs text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">选择波特率</option>
                  <option value={4800}>4800</option>
                  <option value={9600}>9600</option>
                  <option value={19200}>19200</option>
                  <option value={38400}>38400</option>
                  <option value={57600}>57600</option>
                  <option value={115200}>115200</option>
                </select>
              ) : key === 'parity' ? (
                <select
                  value={formData[key] ?? 'none'}
                  onChange={(e) => handleFieldChange(key, e.target.value)}
                  className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-xs text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="none">无校验 (none)</option> 
                  <option value="even">偶校验 (even)</option>
                  <option value="odd">奇校验 (odd)</option>
                </select>
              ) : key === 'comm_mode' ? (
                <select
                  value={formData[key] ?? 'tcp'}
                  onChange={(e) => handleFieldChange(key, e.target.value)}
                  className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-xs text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                >
                  <option value="tcp">TCP</option>
                  <option value="rs485">RS-485</option>
                </select>
              ) : (
                <input
                  type="text"
                  value={formData[key] ?? ''}
                  onChange={(e) => handleFieldChange(key, e.target.value)}
                  className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-xs text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              )}

              <button
                type="button"
                onClick={() => removeCustomField(key)}
                className="px-2 py-1 text-[11px] border border-red-300 text-red-500 rounded hover:bg-red-50"
              >
                删
              </button>
            </div>
          </div>
        ))}

        {/* 新增自定义字段 */}
        <div className="mt-2 space-y-1">
          <label className="block text-xs font-medium text-gray-600 mb-1">
            新增自定义属性
          </label>
          <div className="flex gap-1 mb-1">
            <input
              type="text"
              placeholder="键（英文/下划线）"
              value={newCustomKey}
              onChange={(e) => setNewCustomKey(e.target.value)}
              className="w-2/5 px-2 py-1.5 bg-white border border-gray-300 rounded text-xs text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
            <input
              type="text"
              placeholder="值"
              value={newCustomValue}
              onChange={(e) => setNewCustomValue(e.target.value)}
              className="flex-1 px-2 py-1.5 bg-white border border-gray-300 rounded text-xs text-gray-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
            <button
              type="button"
              onClick={() => {
                const key = newCustomKey.trim();
                if (!key) return;
                if (reservedKeys.has(key)) {
                  alert('该键名与内置字段冲突，请使用其他名称。');
                  return;
                }
                setFormData((prev) => ({
                  ...prev,
                  [key]: newCustomValue,
                }));
                setNewCustomKey('');
                setNewCustomValue('');
              }}
              className="px-2 py-1 bg-blue-500 hover:bg-blue-600 rounded text-[11px] text-white"
            >
              添加
            </button>
          </div>
          <p className="text-[11px] text-gray-400">
            注意：自定义键名不应与上方固定字段（如 voltage_kv、bus 等）重复。
          </p>
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
