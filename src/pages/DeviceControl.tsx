/**
 * 设备控制页面 - 浅色主题
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Zap, Dice5, History, RefreshCw, Settings } from 'lucide-react';
import DeviceControlTable from '../components/device-control/DeviceControlTable';
import ManualSetpointForm from '../components/device-control/ManualSetpointForm';
import RandomConfigForm from '../components/device-control/RandomConfigForm';
import HistoricalConfigForm from '../components/device-control/HistoricalConfigForm';
import SimParamsForm from '../components/device-control/SimParamsForm';
import SwitchControl from '../components/device-control/SwitchControl';
import { useDeviceControlStore } from '../stores/deviceControl';
import { DeviceType } from '../constants/deviceTypes';
import { DataSourceType, ManualSetpoint, DeviceControlConfig, HistoricalConfig, DeviceSimParams, RandomConfig } from '../types/dataSource';

interface DeviceInfo {
  id: string;
  name: string;
  deviceType: DeviceType;
  /** 拓扑中的属性（含 rated_power_kw / max_power_kw 等），供手动设定范围 */
  properties?: Record<string, unknown>;
}

// 设备控制：功率设备 + 开关，不包含外部电网（外部电网不需用户控制）
const POWER_DEVICE_TYPES: DeviceType[] = ['static_generator', 'storage', 'load', 'charger'];
const CONTROLLABLE_DEVICE_TYPES: DeviceType[] = [...POWER_DEVICE_TYPES, 'switch'];

/** 从设备属性取额定功率（kW），用于手动设定滑块范围。储能用 max_power_kw，其余用 rated_power_kw */
function getRatedPowerKw(device: DeviceInfo): number | undefined {
  const p = device.properties;
  if (!p) return undefined;
  if (device.deviceType === 'storage') {
    const v = p.max_power_kw ?? p.rated_power_kw;
    return typeof v === 'number' ? v : (typeof v === 'string' ? Number(v) : undefined);
  }
  const v = p.rated_power_kw ?? p.rated_power;
  return typeof v === 'number' ? v : (typeof v === 'string' ? Number(v) : undefined);
}

export default function DeviceControl() {
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [modbusDevices, setModbusDevices] = useState<Array<{ id: string; name: string; device_type: string; ip: string; port: number }>>([]);
  const [runningModbusIds, setRunningModbusIds] = useState<string[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<DeviceInfo | null>(null);
  const [configMode, setConfigMode] = useState<DataSourceType | 'sim_params' | 'switch' | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { deviceConfigs, deviceSimParams, selectedDeviceIds, setSelectedDevices, setDataSourceType, setManualSetpoint, setRandomConfig, setHistoricalConfig, setDeviceSimParams, batchSetDataSource } = useDeviceControlStore();

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
      // 直接使用后端当前 metadata（由拓扑设计页保存/加载时更新），不先加载 topology.json，避免覆盖用户刚保存的拓扑
      const [devicesMetadata, modbusList, runningIds] = await Promise.all([
        invoke<Array<{ id: string; name: string; device_type: string; properties?: Record<string, unknown> }>>('get_all_devices'),
        invoke<Array<{ id: string; name: string; device_type: string; ip: string; port: number }>>('get_modbus_devices').catch(() => []),
        invoke<string[]>('get_running_modbus_device_ids').catch(() => []),
      ]);
      const powerDevices: DeviceInfo[] = devicesMetadata
        .filter((d) => CONTROLLABLE_DEVICE_TYPES.includes(d.device_type as DeviceType))
        .map((d) => ({
          id: d.id,
          name: d.name,
          deviceType: d.device_type as DeviceType,
          properties: d.properties ?? {},
        }));
      setDevices(powerDevices);
      setModbusDevices(modbusList);
      setRunningModbusIds(runningIds);
    } catch (error) {
      console.error('Failed to load devices from metadata:', error);
      try {
        const topologyData = await invoke<{ devices: Array<{ id: string; name: string; device_type: string; properties?: Record<string, unknown> }> }>('load_topology', { path: 'topology.json' });
        const powerDevices: DeviceInfo[] = (topologyData.devices ?? [])
          .filter((d) => CONTROLLABLE_DEVICE_TYPES.includes(d.device_type as DeviceType))
          .map((d) => ({
            id: d.id,
            name: d.name,
            deviceType: d.device_type as DeviceType,
            properties: d.properties ?? {},
          }));
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
    // 开关设备默认使用开关控制模式，其他设备使用手动设定
    if (device.deviceType === 'switch') {
      setConfigMode('switch');
    } else {
      const config = deviceConfigs[device.id];
      setConfigMode(config?.dataSourceType || 'manual');
    }
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
    async (config: RandomConfig) => {
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

  const handleSaveSimParams = useCallback(
    async (params: DeviceSimParams) => {
      if (!selectedDevice) return;
      setDeviceSimParams(selectedDevice.id, params);
      try {
        await invoke('set_device_sim_params', {
          deviceId: selectedDevice.id,
          params,
        });
      } catch (e) {
        console.warn('同步仿真参数到后端失败:', selectedDevice.id, e);
      }
      handleCloseConfig();
    },
    [selectedDevice, setDeviceSimParams, handleCloseConfig]
  );

  /** 表格中开关设备一键切换（不打开侧面板） */
  const handleToggleSwitchInline = useCallback(
    async (deviceId: string, isClosed: boolean) => {
      try {
        await invoke('update_switch_state', { deviceId, isClosed });
        await loadDevices();
      } catch (e) {
        console.error('切换开关状态失败:', e);
        alert('操作失败: ' + e);
      }
    },
    [loadDevices]
  );

  const handleSaveSwitch = useCallback(
    async (isClosed: boolean) => {
      if (!selectedDevice) return;
      try {
        // 调用专用的开关状态更新方法，同时更新 topology 和 pandapower 网络
        await invoke('update_switch_state', {
          deviceId: selectedDevice.id,
          isClosed,
        });
        // 刷新设备列表以更新开关状态
        await loadDevices();
      } catch (e) {
        console.error('更新开关状态失败:', e);
        alert('操作失败: ' + e);
        return;
      }
      handleCloseConfig();
    },
    [selectedDevice, handleCloseConfig, loadDevices]
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
            onToggleSwitch={handleToggleSwitchInline}
          />
        </div>
      </div>

      {/* 配置面板 */}
      {selectedDevice && configMode && (
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
          <div className="px-3 py-2 border-b border-gray-200">
            {selectedDevice.deviceType === 'switch' ? (
              <div className="text-sm font-medium text-gray-700">开关控制</div>
            ) : (
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
                <button onClick={() => setConfigMode('sim_params')} className={`flex-1 px-2 py-1.5 rounded text-xs font-medium transition-colors ${configMode === 'sim_params' ? 'bg-orange-500 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                  <Settings className="w-3 h-3 inline mr-1" />参数
                </button>
              </div>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            {configMode === 'switch' && (
              <SwitchControl
                initialClosed={selectedDevice.properties?.is_closed !== false}
                onSave={handleSaveSwitch}
                onCancel={handleCloseConfig}
              />
            )}
            {configMode === 'manual' && (
              <ManualSetpointForm
                deviceName={selectedDevice.name}
                ratedPowerKw={getRatedPowerKw(selectedDevice)}
                initialValue={deviceConfigs[selectedDevice.id]?.manualSetpoint}
                onSave={handleSaveManual}
                onCancel={handleCloseConfig}
              />
            )}
            {configMode === 'random' && <RandomConfigForm deviceName={selectedDevice.name} initialValue={deviceConfigs[selectedDevice.id]?.randomConfig} onSave={handleSaveRandom} onCancel={handleCloseConfig} />}
            {configMode === 'historical' && <HistoricalConfigForm deviceName={selectedDevice.name} deviceType={selectedDevice.deviceType} initialValue={deviceConfigs[selectedDevice.id]?.historicalConfig} onSave={handleSaveHistorical} onCancel={handleCloseConfig} />}
            {configMode === 'sim_params' && <SimParamsForm deviceName={selectedDevice.name} initialValue={deviceSimParams[selectedDevice.id]} onSave={handleSaveSimParams} onCancel={handleCloseConfig} />}
          </div>
        </div>
      )}
    </div>
  );
}
