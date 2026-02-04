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
import { DataSourceType, ManualSetpoint, DeviceControlConfig, HistoricalConfig } from '../types/dataSource';

interface DeviceInfo {
  id: string;
  name: string;
  deviceType: DeviceType;
}

// 设备控制不包含外部电网（外部电网不需用户控制）
const POWER_DEVICE_TYPES: DeviceType[] = ['static_generator', 'storage', 'load', 'charger'];

export default function DeviceControl() {
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [modbusDevices, setModbusDevices] = useState<Array<{ id: string; name: string; device_type: string; ip: string; port: number }>>([]);
  const [runningModbusIds, setRunningModbusIds] = useState<string[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<DeviceInfo | null>(null);
  const [configMode, setConfigMode] = useState<DataSourceType | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { deviceConfigs, selectedDeviceIds, setSelectedDevices, setDataSourceType, setManualSetpoint, setRandomConfig, setHistoricalConfig, batchSetDataSource } = useDeviceControlStore();

  /** 将单设备数据源配置同步到仿真后端（仿真运行中热切换生效） */
  const syncDeviceDataSourceToBackend = useCallback(async (deviceId: string, type: DataSourceType, config: DeviceControlConfig | undefined) => {
    if (!type) return;
    try {
      const modeMap: Record<DataSourceType, string> = {
        manual: 'manual',
        random: 'random_data',
        historical: 'historical_data',
      };
      await invoke('set_device_mode', { deviceId, mode: modeMap[type] });
      if (type === 'manual' && config?.manualSetpoint) {
        await invoke('set_device_manual_setpoint', {
          deviceId,
          activePower: config.manualSetpoint.activePower,
          reactivePower: config.manualSetpoint.reactivePower ?? 0,
        });
        await invoke('update_device_properties_for_simulation', {
          deviceId,
          properties: {
            rated_power: config.manualSetpoint.activePower,
            p_kw: config.manualSetpoint.activePower,
            q_kvar: config.manualSetpoint.reactivePower ?? 0,
          },
        });
      } else if (type === 'random' && config?.randomConfig) {
        await invoke('set_device_random_config', {
          deviceId,
          minPower: config.randomConfig.minPower,
          maxPower: config.randomConfig.maxPower,
        });
      } else if (type === 'historical' && config?.historicalConfig) {
        await invoke('set_device_historical_config', {
          deviceId,
          config: config.historicalConfig,
        });
      }
    } catch (e) {
      console.warn('同步数据源到仿真失败:', deviceId, type, e);
    }
  }, []);

  /** 表格下拉切换数据源时：先更新 store，再同步到后端（热切换） */
  const handleChangeDataSource = useCallback(
    async (deviceId: string, type: DataSourceType) => {
      setDataSourceType(deviceId, type);
      const config = useDeviceControlStore.getState().deviceConfigs[deviceId];
      await syncDeviceDataSourceToBackend(deviceId, type, config);
    },
    [setDataSourceType, syncDeviceDataSourceToBackend]
  );

  const loadDevices = useCallback(async () => {
    setIsLoading(true);
    try {
      const [devicesMetadata, modbusList, runningIds] = await Promise.all([
        invoke<Array<{ id: string; name: string; device_type: string }>>('get_all_devices'),
        invoke<Array<{ id: string; name: string; device_type: string; ip: string; port: number }>>('get_modbus_devices').catch(() => []),
        invoke<string[]>('get_running_modbus_device_ids').catch(() => []),
      ]);
      const powerDevices = devicesMetadata
        .filter((d) => POWER_DEVICE_TYPES.includes(d.device_type as DeviceType))
        .map((d) => ({ id: d.id, name: d.name, deviceType: d.device_type as DeviceType }));
      setDevices(powerDevices);
      setModbusDevices(modbusList);
      setRunningModbusIds(runningIds);
    } catch (error) {
      console.error('Failed to load devices from metadata:', error);
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

  const refreshRunningModbusIds = useCallback(async () => {
    try {
      const ids = await invoke<string[]>('get_running_modbus_device_ids');
      setRunningModbusIds(ids);
    } catch {
      // ignore
    }
  }, []);

  const handleToggleModbus = useCallback(
    async (deviceId: string, turnOn: boolean) => {
      const modbusDevice = modbusDevices.find((d) => d.id === deviceId);
      const device = devices.find((d) => d.id === deviceId);
      if (turnOn) {
        if (!modbusDevice || !device) return;
        try {
          const registers = await invoke<Array<{ address: number; value: number; type: string; name?: string; key?: string }>>('get_modbus_register_defaults', {
            deviceType: device.deviceType,
          });
          await invoke('start_device_modbus', {
            deviceId,
            deviceType: device.deviceType,
            config: {
              ip_address: modbusDevice.ip,
              port: modbusDevice.port,
              registers,
            },
          });
          await invoke('update_device_properties_for_simulation', {
            deviceId,
            properties: { on_off: 1 },
          });
        } catch (e) {
          console.error('开机/启动 Modbus 失败:', e);
          alert('操作失败：' + e);
          return;
        }
      } else {
        try {
          await invoke('stop_device_modbus', { deviceId });
          await invoke('update_device_properties_for_simulation', {
            deviceId,
            properties: { on_off: 0 },
          });
        } catch (e) {
          console.error('关机/停止 Modbus 失败:', e);
          alert('操作失败：' + e);
          return;
        }
      }
      await refreshRunningModbusIds();
    },
    [modbusDevices, devices, refreshRunningModbusIds]
  );

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
      await invoke('set_device_manual_setpoint', {
        deviceId: selectedDevice.id,
        activePower: setpoint.activePower,
        reactivePower: setpoint.reactivePower ?? 0,
      });
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

  const handleSaveRandom = useCallback(
    async (config: { minPower: number; maxPower: number; updateInterval?: number; volatility?: number }) => {
      if (!selectedDevice) return;
      setRandomConfig(selectedDevice.id, config);
      try {
        await syncDeviceDataSourceToBackend(selectedDevice.id, 'random', {
          deviceId: selectedDevice.id,
          dataSourceType: 'random',
          randomConfig: config,
        });
      } catch (e) {
        console.warn('同步随机配置到仿真失败:', selectedDevice.id, e);
      }
      handleCloseConfig();
    },
    [selectedDevice, setRandomConfig, syncDeviceDataSourceToBackend, handleCloseConfig]
  );

  const handleSaveHistorical = useCallback(
    async (config: HistoricalConfig) => {
      if (!selectedDevice) return;
      setHistoricalConfig(selectedDevice.id, config);
      try {
        await syncDeviceDataSourceToBackend(selectedDevice.id, 'historical', {
          deviceId: selectedDevice.id,
          dataSourceType: 'historical',
          historicalConfig: config,
        });
      } catch (e) {
        console.warn('同步历史配置到仿真失败:', selectedDevice.id, e);
      }
      handleCloseConfig();
    },
    [selectedDevice, setHistoricalConfig, syncDeviceDataSourceToBackend, handleCloseConfig]
  );

  /** 批量设置数据源：先更新 store，再逐个同步到后端（热切换） */
  const handleBatchSetDataSource = useCallback(
    async (type: DataSourceType) => {
      if (selectedDeviceIds.length === 0) return;
      batchSetDataSource(type);
      const configs = useDeviceControlStore.getState().deviceConfigs;
      for (const deviceId of selectedDeviceIds) {
        await syncDeviceDataSourceToBackend(deviceId, type, configs[deviceId]);
      }
    },
    [selectedDeviceIds, batchSetDataSource, syncDeviceDataSourceToBackend]
  );

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
          <DeviceControlTable
            devices={devices}
            configs={deviceConfigs}
            selectedIds={selectedDeviceIds}
            onSelect={setSelectedDevices}
            onConfigureDevice={handleConfigureDevice}
            onChangeDataSource={handleChangeDataSource}
            modbusDeviceIds={modbusDevices.map((d) => d.id)}
            runningModbusIds={runningModbusIds}
            onToggleModbus={handleToggleModbus}
          />
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
