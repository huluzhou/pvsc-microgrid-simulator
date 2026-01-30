/**
 * 设备控制页面 - 浅色主题
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Zap, Dice5, History, RefreshCw } from 'lucide-react';
import DeviceControlTable from '../components/device-control/DeviceControlTable';
import ManualSetpointForm from '../components/device-control/ManualSetpointForm';
import RandomConfigForm from '../components/device-control/RandomConfigForm';
import HistoricalConfigForm from '../components/device-control/HistoricalConfigForm';
import { useDeviceControlStore } from '../stores/deviceControl';
import { DeviceType } from '../constants/deviceTypes';
import { DataSourceType, ManualSetpoint } from '../types/dataSource';

interface DeviceInfo {
  id: string;
  name: string;
  deviceType: DeviceType;
}

// 设备控制不包含外部电网（外部电网不需用户控制）
const POWER_DEVICE_TYPES: DeviceType[] = ['static_generator', 'storage', 'load', 'charger'];

export default function DeviceControl() {
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<DeviceInfo | null>(null);
  const [configMode, setConfigMode] = useState<DataSourceType | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { deviceConfigs, selectedDeviceIds, setSelectedDevices, setDataSourceType, setManualSetpoint, setRandomConfig, setHistoricalConfig, batchSetDataSource } = useDeviceControlStore();

  const loadDevices = useCallback(async () => {
    setIsLoading(true);
    try {
      // 从后端元数据存储获取设备（与拓扑设计页面同步）
      const devicesMetadata = await invoke<Array<{ id: string; name: string; device_type: string }>>('get_all_devices');
      const powerDevices = devicesMetadata
        .filter((d) => POWER_DEVICE_TYPES.includes(d.device_type as DeviceType))
        .map((d) => ({ id: d.id, name: d.name, deviceType: d.device_type as DeviceType }));
      setDevices(powerDevices);
    } catch (error) {
      console.error('Failed to load devices from metadata:', error);
      // 如果后端元数据为空，尝试从默认拓扑文件加载
      try {
        const topologyData = await invoke<{ devices: Array<{ id: string; name: string; device_type: string }> }>('load_topology', { path: 'topology.json' });
        const powerDevices = topologyData.devices
          .filter((d) => POWER_DEVICE_TYPES.includes(d.device_type as DeviceType))
          .map((d) => ({ id: d.id, name: d.name, deviceType: d.device_type as DeviceType }));
        setDevices(powerDevices);
      } catch (fallbackError) {
        console.error('Failed to load from topology file:', fallbackError);
        setDevices([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { loadDevices(); }, [loadDevices]);

  const handleConfigureDevice = useCallback((device: DeviceInfo) => {
    setSelectedDevice(device);
    const config = deviceConfigs[device.id];
    setConfigMode(config?.dataSourceType || 'manual');
  }, [deviceConfigs]);

  const handleCloseConfig = useCallback(() => {
    setSelectedDevice(null);
    setConfigMode(null);
  }, []);

  const handleSaveManual = useCallback(async (setpoint: ManualSetpoint) => {
    if (!selectedDevice) return;
    setManualSetpoint(selectedDevice.id, setpoint);
    try {
      await invoke('set_device_mode', { deviceId: selectedDevice.id, mode: 'manual' });
      await invoke('update_device_properties_for_simulation', {
        deviceId: selectedDevice.id,
        properties: {
          rated_power: setpoint.activePower,
          p_kw: setpoint.activePower,
          q_kvar: setpoint.reactivePower ?? 0,
        },
      });
    } catch (e) {
      console.error('同步手动设定到仿真失败:', e);
      alert('保存成功，但同步到仿真失败: ' + e);
    }
    handleCloseConfig();
  }, [selectedDevice, setManualSetpoint, handleCloseConfig]);

  const handleSaveRandom = useCallback((config: any) => {
    if (selectedDevice) { setRandomConfig(selectedDevice.id, config); handleCloseConfig(); }
  }, [selectedDevice, setRandomConfig, handleCloseConfig]);

  const handleSaveHistorical = useCallback((config: any) => {
    if (selectedDevice) { setHistoricalConfig(selectedDevice.id, config); handleCloseConfig(); }
  }, [selectedDevice, setHistoricalConfig, handleCloseConfig]);

  const handleBatchSetDataSource = useCallback((type: DataSourceType) => {
    if (selectedDeviceIds.length === 0) return;
    batchSetDataSource(type);
  }, [selectedDeviceIds, batchSetDataSource]);

  const stats = useMemo(() => {
    const configured = Object.values(deviceConfigs).filter((c) => c.dataSourceType);
    return {
      total: devices.length,
      configured: configured.length,
      manual: configured.filter((c) => c.dataSourceType === 'manual').length,
      random: configured.filter((c) => c.dataSourceType === 'random').length,
      historical: configured.filter((c) => c.dataSourceType === 'historical').length,
    };
  }, [devices, deviceConfigs]);

  return (
    <div className="flex h-full bg-gray-50">
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 工具栏 */}
        <div className="px-4 py-2 bg-white border-b border-gray-200 flex items-center gap-4">
          <h1 className="text-base font-semibold text-gray-800">设备控制</h1>
          <div className="flex-1" />
          {selectedDeviceIds.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">已选 {selectedDeviceIds.length} 个设备</span>
              <div className="w-px h-5 bg-gray-300" />
              <button onClick={() => handleBatchSetDataSource('manual')} className="px-2 py-1 bg-blue-500 hover:bg-blue-600 rounded text-xs text-white flex items-center gap-1 transition-colors">
                <Zap className="w-3 h-3" />批量手动
              </button>
              <button onClick={() => handleBatchSetDataSource('random')} className="px-2 py-1 bg-purple-500 hover:bg-purple-600 rounded text-xs text-white flex items-center gap-1 transition-colors">
                <Dice5 className="w-3 h-3" />批量随机
              </button>
              <button onClick={() => handleBatchSetDataSource('historical')} className="px-2 py-1 bg-green-500 hover:bg-green-600 rounded text-xs text-white flex items-center gap-1 transition-colors">
                <History className="w-3 h-3" />批量历史
              </button>
            </div>
          )}
          <button onClick={loadDevices} disabled={isLoading} className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded transition-colors disabled:opacity-50" title="刷新设备列表">
            <RefreshCw className={`w-4 h-4 text-gray-600 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* 统计卡片 */}
        <div className="px-4 py-2 bg-white border-b border-gray-200">
          <div className="grid grid-cols-5 gap-3">
            <div className="p-2 bg-gray-50 rounded border border-gray-200">
              <div className="text-lg font-bold text-gray-800">{stats.total}</div>
              <div className="text-xs text-gray-500">功率设备</div>
            </div>
            <div className="p-2 bg-gray-50 rounded border border-gray-200">
              <div className="text-lg font-bold text-green-600">{stats.configured}</div>
              <div className="text-xs text-gray-500">已配置</div>
            </div>
            <div className="p-2 bg-gray-50 rounded border border-gray-200">
              <div className="text-lg font-bold text-blue-600">{stats.manual}</div>
              <div className="text-xs text-gray-500">手动数据</div>
            </div>
            <div className="p-2 bg-gray-50 rounded border border-gray-200">
              <div className="text-lg font-bold text-purple-600">{stats.random}</div>
              <div className="text-xs text-gray-500">随机数据</div>
            </div>
            <div className="p-2 bg-gray-50 rounded border border-gray-200">
              <div className="text-lg font-bold text-green-600">{stats.historical}</div>
              <div className="text-xs text-gray-500">历史数据</div>
            </div>
          </div>
        </div>

        {/* 设备表格 */}
        <div className="flex-1 overflow-auto bg-white">
          <DeviceControlTable devices={devices} configs={deviceConfigs} selectedIds={selectedDeviceIds} onSelect={setSelectedDevices} onConfigureDevice={handleConfigureDevice} onChangeDataSource={setDataSourceType} />
        </div>
      </div>

      {/* 配置面板 */}
      {selectedDevice && configMode && (
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
          <div className="px-3 py-2 border-b border-gray-200">
            <div className="flex gap-1">
              <button onClick={() => setConfigMode('manual')} className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-colors ${configMode === 'manual' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                <Zap className="w-3 h-3 inline mr-1" />手动
              </button>
              <button onClick={() => setConfigMode('random')} className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-colors ${configMode === 'random' ? 'bg-purple-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                <Dice5 className="w-3 h-3 inline mr-1" />随机
              </button>
              <button onClick={() => setConfigMode('historical')} className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-colors ${configMode === 'historical' ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                <History className="w-3 h-3 inline mr-1" />历史
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {configMode === 'manual' && <ManualSetpointForm deviceName={selectedDevice.name} initialValue={deviceConfigs[selectedDevice.id]?.manualSetpoint} onSave={handleSaveManual} onCancel={handleCloseConfig} />}
            {configMode === 'random' && <RandomConfigForm deviceName={selectedDevice.name} initialValue={deviceConfigs[selectedDevice.id]?.randomConfig} onSave={handleSaveRandom} onCancel={handleCloseConfig} />}
            {configMode === 'historical' && <HistoricalConfigForm deviceName={selectedDevice.name} deviceType={selectedDevice.deviceType} initialValue={deviceConfigs[selectedDevice.id]?.historicalConfig} onSave={handleSaveHistorical} onCancel={handleCloseConfig} />}
          </div>
        </div>
      )}
    </div>
  );
}
