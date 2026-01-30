/**
 * Modbus通信页面 - 浅色主题
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Radio, Play, Square, Settings, RefreshCw, CheckCircle, Info } from 'lucide-react';
import { DeviceType, DEVICE_TYPES } from '../constants/deviceTypes';

interface DeviceModbusConfig {
  deviceId: string;
  enabled: boolean;
  remoteControlAllowed?: boolean;
  ipAddress: string;
  port: number;
  slaveId: number;
  registerMapping: RegisterMapping;
}

interface RegisterMapping {
  activePower: number;
  reactivePower: number;
  voltage?: number;
  current?: number;
  status?: number;
}

interface ModbusServerStatus {
  deviceId: string;
  running: boolean;
  connectedClients: number;
  lastCommandTime?: string;
  errorCount: number;
}

const POWER_DEVICE_TYPES: DeviceType[] = ['static_generator', 'storage', 'load', 'charger', 'external_grid'];

const DEFAULT_REGISTER_MAPPING: RegisterMapping = {
  activePower: 0,
  reactivePower: 2,
  voltage: 4,
  current: 6,
  status: 8,
};

// 设备图标
function DeviceIcon({ type, size = 24 }: { type: DeviceType; size?: number }) {
  const info = DEVICE_TYPES[type];
  const color = info?.color || '#666';
  
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
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

export default function Modbus() {
  const [devices, setDevices] = useState<Array<{ id: string; name: string; deviceType: DeviceType }>>([]);
  const [configs, setConfigs] = useState<Record<string, DeviceModbusConfig>>({});
  const [serverStatus, setServerStatus] = useState<Record<string, ModbusServerStatus>>({});
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadDevices = useCallback(async () => {
    setIsLoading(true);
    try {
      // 从后端元数据存储获取设备（与拓扑设计页面同步）
      const devicesMetadata = await invoke<Array<{ id: string; name: string; device_type: string }>>('get_all_devices');
      const powerDevices = devicesMetadata
        .filter((d) => POWER_DEVICE_TYPES.includes(d.device_type as DeviceType))
        .map((d) => ({ id: d.id, name: d.name, deviceType: d.device_type as DeviceType }));
      setDevices(powerDevices);

      const defaultConfigs: Record<string, DeviceModbusConfig> = {};
      powerDevices.forEach((device, index) => {
        defaultConfigs[device.id] = {
          deviceId: device.id,
          enabled: false,
          remoteControlAllowed: true,
          ipAddress: '127.0.0.1',
          port: 5020 + index,
          slaveId: index + 1,
          registerMapping: { ...DEFAULT_REGISTER_MAPPING },
        };
      });
      setConfigs(defaultConfigs);
    } catch (error) {
      console.error('Failed to load devices from metadata:', error);
      // 如果后端元数据为空，尝试从默认拓扑文件加载
      try {
        const topologyData = await invoke<{ devices: Array<{ id: string; name: string; device_type: string }> }>('load_topology', { path: 'topology.json' });
        const powerDevices = topologyData.devices
          .filter((d) => POWER_DEVICE_TYPES.includes(d.device_type as DeviceType))
          .map((d) => ({ id: d.id, name: d.name, deviceType: d.device_type as DeviceType }));
        setDevices(powerDevices);

        const defaultConfigs: Record<string, DeviceModbusConfig> = {};
        powerDevices.forEach((device, index) => {
          defaultConfigs[device.id] = {
            deviceId: device.id,
            enabled: false,
            remoteControlAllowed: true,
            ipAddress: '127.0.0.1',
            port: 5020 + index,
            slaveId: index + 1,
            registerMapping: { ...DEFAULT_REGISTER_MAPPING },
          };
        });
        setConfigs(defaultConfigs);
      } catch (fallbackError) {
        console.error('Failed to load from topology file:', fallbackError);
        setDevices([]);
        setConfigs({});
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { loadDevices(); }, [loadDevices]);

  const updateConfig = useCallback((deviceId: string, updates: Partial<DeviceModbusConfig>) => {
    setConfigs((prev) => ({ ...prev, [deviceId]: { ...prev[deviceId], ...updates } }));
  }, []);

  const toggleServer = useCallback(async (deviceId: string) => {
    const config = configs[deviceId];
    if (!config) return;
    try {
      if (serverStatus[deviceId]?.running) {
        await invoke('stop_device_modbus', { deviceId });
        setServerStatus((prev) => ({ ...prev, [deviceId]: { ...prev[deviceId], running: false } }));
      } else {
        await invoke('start_device_modbus', { deviceId, config: { ip_address: config.ipAddress, port: config.port, slave_id: config.slaveId } });
        setServerStatus((prev) => ({ ...prev, [deviceId]: { deviceId, running: true, connectedClients: 0, errorCount: 0 } }));
      }
    } catch (error) {
      alert('操作失败：' + error);
    }
  }, [configs, serverStatus]);

  const stats = useMemo(() => {
    const enabledConfigs = Object.values(configs).filter((c) => c.enabled);
    const runningServers = Object.values(serverStatus).filter((s) => s.running);
    return {
      total: devices.length,
      enabled: enabledConfigs.length,
      running: runningServers.length,
      totalClients: runningServers.reduce((sum, s) => sum + s.connectedClients, 0),
    };
  }, [devices, configs, serverStatus]);

  const selectedConfig = selectedDevice ? configs[selectedDevice] : null;

  return (
    <div className="flex h-full bg-gray-50">
      {/* 左侧设备列表 */}
      <div className="w-72 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-3 py-2 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-800">Modbus服务器</h2>
          <button onClick={loadDevices} disabled={isLoading} className="p-1.5 hover:bg-gray-100 rounded transition-colors">
            <RefreshCw className={`w-4 h-4 text-gray-500 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        <div className="px-3 py-2 border-b border-gray-200 grid grid-cols-2 gap-2 text-center">
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="text-lg font-bold text-green-600">{stats.running}</div>
            <div className="text-xs text-gray-500">运行中</div>
          </div>
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="text-lg font-bold text-blue-600">{stats.totalClients}</div>
            <div className="text-xs text-gray-500">连接数</div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {devices.map((device) => {
            const config = configs[device.id];
            const status = serverStatus[device.id];
            return (
              <div
                key={device.id}
                onClick={() => setSelectedDevice(device.id)}
                className={`p-2 rounded mb-1 cursor-pointer transition-colors ${selectedDevice === device.id ? 'bg-blue-500 text-white' : 'bg-gray-50 hover:bg-gray-100'}`}
              >
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded flex items-center justify-center ${selectedDevice === device.id ? 'bg-blue-400' : 'bg-white border border-gray-200'}`}>
                    <DeviceIcon type={device.deviceType} size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm font-medium truncate ${selectedDevice === device.id ? 'text-white' : 'text-gray-800'}`}>{device.name}</div>
                    <div className={`text-xs ${selectedDevice === device.id ? 'text-blue-100' : 'text-gray-500'}`}>{config?.ipAddress}:{config?.port}</div>
                  </div>
                  {status?.running ? (
                    <CheckCircle className={`w-4 h-4 ${selectedDevice === device.id ? 'text-green-200' : 'text-green-500'}`} />
                  ) : (
                    <Radio className={`w-4 h-4 ${selectedDevice === device.id ? 'text-gray-300' : 'text-gray-400'}`} />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 右侧配置面板 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selectedConfig ? (
          <>
            <div className="px-4 py-2 bg-white border-b border-gray-200 flex items-center gap-4">
              <h1 className="text-base font-semibold text-gray-800">
                {devices.find((d) => d.id === selectedDevice)?.name} - Modbus配置
              </h1>
              <div className="flex-1" />
              <button
                onClick={() => toggleServer(selectedDevice!)}
                className={`px-3 py-1.5 rounded text-white text-sm flex items-center gap-1.5 transition-colors ${serverStatus[selectedDevice!]?.running ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'}`}
              >
                {serverStatus[selectedDevice!]?.running ? (<><Square className="w-4 h-4" />停止</>) : (<><Play className="w-4 h-4" />启动</>)}
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <div className="max-w-2xl space-y-4">
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2"><Settings className="w-4 h-4" />网络配置</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">IP地址</label>
                      <input type="text" value={selectedConfig.ipAddress} onChange={(e) => updateConfig(selectedDevice!, { ipAddress: e.target.value })} className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">端口</label>
                      <input type="number" value={selectedConfig.port} onChange={(e) => updateConfig(selectedDevice!, { port: Number(e.target.value) })} className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">从站ID</label>
                      <input type="number" value={selectedConfig.slaveId} onChange={(e) => updateConfig(selectedDevice!, { slaveId: Number(e.target.value) })} className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm" />
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">寄存器映射</h3>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">有功功率 (读写)</label>
                        <div className="flex gap-2">
                          <input type="number" value={selectedConfig.registerMapping.activePower} onChange={(e) => updateConfig(selectedDevice!, { registerMapping: { ...selectedConfig.registerMapping, activePower: Number(e.target.value) } })} className="flex-1 px-2 py-1.5 bg-white border border-gray-300 rounded text-sm" />
                          <span className="px-2 py-1.5 bg-gray-100 rounded text-gray-500 text-xs">0x{selectedConfig.registerMapping.activePower.toString(16).padStart(4, '0')}</span>
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">无功功率 (读写)</label>
                        <div className="flex gap-2">
                          <input type="number" value={selectedConfig.registerMapping.reactivePower} onChange={(e) => updateConfig(selectedDevice!, { registerMapping: { ...selectedConfig.registerMapping, reactivePower: Number(e.target.value) } })} className="flex-1 px-2 py-1.5 bg-white border border-gray-300 rounded text-sm" />
                          <span className="px-2 py-1.5 bg-gray-100 rounded text-gray-500 text-xs">0x{selectedConfig.registerMapping.reactivePower.toString(16).padStart(4, '0')}</span>
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">电压 (只读)</label>
                        <input type="number" value={selectedConfig.registerMapping.voltage} onChange={(e) => updateConfig(selectedDevice!, { registerMapping: { ...selectedConfig.registerMapping, voltage: Number(e.target.value) } })} className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm" />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">电流 (只读)</label>
                        <input type="number" value={selectedConfig.registerMapping.current} onChange={(e) => updateConfig(selectedDevice!, { registerMapping: { ...selectedConfig.registerMapping, current: Number(e.target.value) } })} className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm" />
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">远程控制</h3>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedConfig.remoteControlAllowed !== false}
                      onChange={async (e) => {
                        const checked = e.target.checked;
                        updateConfig(selectedDevice!, { remoteControlAllowed: checked });
                        try {
                          await invoke('set_device_remote_control_enabled', { deviceId: selectedDevice!, enabled: checked });
                        } catch (err) {
                          console.error('设置设备远程控制失败:', err);
                        }
                      }}
                      className="w-4 h-4 rounded border-gray-300 text-blue-600"
                    />
                    <span className="text-sm text-gray-700">允许该设备远程控制（Modbus 写入生效）</span>
                  </label>
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <h3 className="text-sm font-semibold text-blue-700 mb-2 flex items-center gap-2"><Info className="w-4 h-4" />使用说明</h3>
                  <div className="text-xs text-blue-600 space-y-1">
                    <p>• 每个设备独立运行一个Modbus TCP服务器</p>
                    <p>• 外部系统可通过写入功率寄存器控制设备</p>
                    <p>• 上方可针对单个设备开关“允许远程控制”；仿真页为全局总开关</p>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <Radio className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>请从左侧选择设备进行配置</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
