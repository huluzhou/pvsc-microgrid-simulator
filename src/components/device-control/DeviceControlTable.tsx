/**
 * 设备控制表格组件 - 浅色主题
 */
import { memo, useCallback } from 'react';
import { Settings, Zap, Dice5, History, MoreVertical } from 'lucide-react';
import { DEVICE_TYPES, DeviceType } from '../../constants/deviceTypes';
import { DataSourceType, DeviceControlConfig } from '../../types/dataSource';

interface DeviceInfo {
  id: string;
  name: string;
  deviceType: DeviceType;
}

interface DeviceControlTableProps {
  devices: DeviceInfo[];
  configs: Record<string, DeviceControlConfig>;
  selectedIds: string[];
  onSelect: (ids: string[]) => void;
  onConfigureDevice: (device: DeviceInfo) => void;
  onChangeDataSource: (deviceId: string, type: DataSourceType) => void;
}

// 数据源类型图标
function DataSourceIcon({ type }: { type?: DataSourceType }) {
  switch (type) {
    case 'manual':
      return <Zap className="w-4 h-4 text-blue-500" />;
    case 'random':
      return <Dice5 className="w-4 h-4 text-purple-500" />;
    case 'historical':
      return <History className="w-4 h-4 text-green-500" />;
    default:
      return <Settings className="w-4 h-4 text-gray-400" />;
  }
}

// 设备图标缩略图
function DeviceIcon({ type }: { type: DeviceType }) {
  const info = DEVICE_TYPES[type];
  const color = info?.color || '#666';
  
  return (
    <svg width="24" height="24" viewBox="0 0 24 24">
      {type === 'static_generator' && (
        <>
          <circle cx="12" cy="12" r="8" fill="none" stroke={color} strokeWidth="2" />
          <text x="12" y="15" textAnchor="middle" fontSize="6" fontWeight="bold" fill={color}>PV</text>
        </>
      )}
      {type === 'storage' && (
        <>
          <rect x="4" y="8" width="14" height="10" fill="none" stroke={color} strokeWidth="2" />
          <rect x="18" y="11" width="2" height="4" fill="none" stroke={color} strokeWidth="2" />
        </>
      )}
      {type === 'load' && (
        <path d="M12,4 L4,20 L20,20 Z" fill="none" stroke={color} strokeWidth="2" />
      )}
      {type === 'charger' && (
        <>
          <rect x="6" y="8" width="12" height="14" fill="none" stroke={color} strokeWidth="2" />
          <rect x="9" y="4" width="6" height="4" fill="none" stroke={color} strokeWidth="2" />
        </>
      )}
      {type === 'external_grid' && (
        <>
          <rect x="4" y="4" width="16" height="16" fill="none" stroke={color} strokeWidth="2" />
          <line x1="10" y1="4" x2="10" y2="20" stroke={color} strokeWidth="1" />
          <line x1="14" y1="4" x2="14" y2="20" stroke={color} strokeWidth="1" />
          <line x1="4" y1="10" x2="20" y2="10" stroke={color} strokeWidth="1" />
          <line x1="4" y1="14" x2="20" y2="14" stroke={color} strokeWidth="1" />
        </>
      )}
      {!['static_generator', 'storage', 'load', 'charger', 'external_grid'].includes(type) && (
        <rect x="4" y="4" width="16" height="16" fill="none" stroke={color} strokeWidth="2" />
      )}
    </svg>
  );
}

// 单行设备组件
const DeviceRow = memo(function DeviceRow({
  device,
  config,
  isSelected,
  onSelectToggle,
  onConfigure,
  onChangeDataSource,
}: {
  device: DeviceInfo;
  config?: DeviceControlConfig;
  isSelected: boolean;
  onSelectToggle: () => void;
  onConfigure: () => void;
  onChangeDataSource: (type: DataSourceType) => void;
}) {
  const deviceInfo = DEVICE_TYPES[device.deviceType];

  return (
    <tr className={`border-b border-gray-200 ${isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'}`}>
      {/* 选择框 */}
      <td className="px-4 py-3">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onSelectToggle}
          className="w-4 h-4 text-blue-500 bg-white border-gray-300 rounded focus:ring-blue-500"
        />
      </td>

      {/* 设备信息 */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div 
            className="w-8 h-8 rounded flex items-center justify-center bg-gray-50 border border-gray-200"
          >
            <DeviceIcon type={device.deviceType} />
          </div>
          <div>
            <div className="text-sm font-medium text-gray-800">{device.name}</div>
            <div className="text-xs text-gray-500">{deviceInfo?.name}</div>
          </div>
        </div>
      </td>

      {/* 数据源类型 */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <DataSourceIcon type={config?.dataSourceType} />
          <select
            value={config?.dataSourceType ?? ''}
            onChange={(e) => onChangeDataSource(e.target.value as DataSourceType)}
            className="px-2 py-1 bg-white border border-gray-300 rounded text-sm text-gray-700"
          >
            <option value="">未配置</option>
            <option value="manual">手动设置</option>
            <option value="random">随机数据</option>
            <option value="historical">历史数据</option>
          </select>
        </div>
      </td>

      {/* 当前配置摘要 */}
      <td className="px-4 py-3 text-sm text-gray-600">
        {config?.dataSourceType === 'manual' && config.manualSetpoint && (
          <span>P={config.manualSetpoint.activePower}kW, Q={config.manualSetpoint.reactivePower}kVar</span>
        )}
        {config?.dataSourceType === 'random' && config.randomConfig && (
          <span>{config.randomConfig.minPower}~{config.randomConfig.maxPower}kW</span>
        )}
        {config?.dataSourceType === 'historical' && config.historicalConfig && (
          <span className="truncate max-w-[150px] inline-block">
            {config.historicalConfig.filePath.split('/').pop()}
          </span>
        )}
        {!config?.dataSourceType && <span className="text-gray-400">-</span>}
      </td>

      {/* 操作按钮 */}
      <td className="px-4 py-3">
        <button
          onClick={onConfigure}
          className="p-2 hover:bg-gray-100 rounded transition-colors"
          title="配置详情"
        >
          <MoreVertical className="w-4 h-4 text-gray-500" />
        </button>
      </td>
    </tr>
  );
});

export default function DeviceControlTable({
  devices,
  configs,
  selectedIds,
  onSelect,
  onConfigureDevice,
  onChangeDataSource,
}: DeviceControlTableProps) {
  const handleSelectAll = useCallback(() => {
    if (selectedIds.length === devices.length) {
      onSelect([]);
    } else {
      onSelect(devices.map((d) => d.id));
    }
  }, [devices, selectedIds, onSelect]);

  const handleToggleSelect = useCallback(
    (deviceId: string) => {
      if (selectedIds.includes(deviceId)) {
        onSelect(selectedIds.filter((id) => id !== deviceId));
      } else {
        onSelect([...selectedIds, deviceId]);
      }
    },
    [selectedIds, onSelect]
  );

  const isAllSelected = devices.length > 0 && selectedIds.length === devices.length;
  const isPartialSelected = selectedIds.length > 0 && selectedIds.length < devices.length;

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-100 text-left">
            <th className="px-4 py-3 w-12">
              <input
                type="checkbox"
                checked={isAllSelected}
                ref={(el) => {
                  if (el) el.indeterminate = isPartialSelected;
                }}
                onChange={handleSelectAll}
                className="w-4 h-4 text-blue-500 bg-white border-gray-300 rounded focus:ring-blue-500"
              />
            </th>
            <th className="px-4 py-3 text-sm font-semibold text-gray-600">设备</th>
            <th className="px-4 py-3 text-sm font-semibold text-gray-600">数据源</th>
            <th className="px-4 py-3 text-sm font-semibold text-gray-600">配置摘要</th>
            <th className="px-4 py-3 text-sm font-semibold text-gray-600 w-16">操作</th>
          </tr>
        </thead>
        <tbody>
          {devices.length === 0 ? (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                暂无功率设备，请先在拓扑设计中添加设备
              </td>
            </tr>
          ) : (
            devices.map((device) => (
              <DeviceRow
                key={device.id}
                device={device}
                config={configs[device.id]}
                isSelected={selectedIds.includes(device.id)}
                onSelectToggle={() => handleToggleSelect(device.id)}
                onConfigure={() => onConfigureDevice(device)}
                onChangeDataSource={(type) => onChangeDataSource(device.id, type)}
              />
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
