/**
 * Modbus通信页面 - 浅色主题
 * 四类寄存器：Coils / Discrete Inputs / Input Registers / Holding Registers
 * 预定义寄存器按设备类型（v1.5.0），支持增删与就地编辑
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { Radio, Settings, RefreshCw, CheckCircle, Info } from 'lucide-react';
import { DeviceType, DEVICE_TYPES } from '../constants/deviceTypes';
import {
  type RegisterEntry,
  type ModbusRegisterType,
  getPredefinedRegistersForDeviceType,
  MODBUS_REGISTER_TYPE_LABELS,
} from '../constants/modbusRegisters';

interface DeviceModbusConfig {
  deviceId: string;
  enabled: boolean;
  remoteControlAllowed?: boolean;
  ipAddress: string;
  port: number;
  slaveId: number;
  registers: RegisterEntry[];
}

interface ModbusServerStatus {
  deviceId: string;
  running: boolean;
  connectedClients: number;
  lastCommandTime?: string;
  errorCount: number;
}

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
      // 仅显示拓扑中配置了 ip 和 port 的设备（兼容旧版 chuzhou 与新版拓扑）
      const modbusDevices = await invoke<Array<{ id: string; name: string; device_type: string; ip: string; port: number }>>('get_modbus_devices');
      const list = modbusDevices.map((d) => ({
        id: d.id,
        name: d.name,
        deviceType: d.device_type as DeviceType,
      }));
      setDevices(list);

      const defaultConfigs: Record<string, DeviceModbusConfig> = {};
      for (let index = 0; index < modbusDevices.length; index++) {
        const device = modbusDevices[index];
        let registers: RegisterEntry[];
        try {
          const fromBackend = await invoke<Array<{ address: number; value: number; type: string; name?: string; key?: string }>>('get_modbus_register_defaults', { deviceType: device.device_type });
          registers = fromBackend.map((r) => ({ address: r.address, value: r.value, type: r.type as ModbusRegisterType, name: r.name, key: r.key }));
        } catch {
          registers = getPredefinedRegistersForDeviceType(device.device_type).map((r) => ({ ...r }));
        }
        defaultConfigs[device.id] = {
          deviceId: device.id,
          enabled: false,
          remoteControlAllowed: true,
          ipAddress: device.ip,
          port: device.port,
          // 当前后端仅按端口区分设备，未真正使用从站ID，这里统一默认 1，避免递增编号造成误解
          slaveId: 1,
          registers,
        };
      }
      const runningIds = await invoke<string[]>('get_running_modbus_device_ids').catch((): string[] => []);
      setConfigs(defaultConfigs);
      setServerStatus((prev) => {
        const next = { ...prev };
        list.forEach((d) => {
          next[d.id] = { deviceId: d.id, running: runningIds.includes(d.id), connectedClients: 0, errorCount: 0 };
        });
        return next;
      });
    } catch (error) {
      console.error('Failed to load Modbus devices from topology:', error);
      setDevices([]);
      setConfigs({});
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { loadDevices(); }, [loadDevices]);

  // 仿真每步计算后后端会推送寄存器快照，联动更新前端寄存器值显示
  useEffect(() => {
    const unlisten = listen<{
      device_id: string;
      input_registers: Record<string, number>;
      holding_registers: Record<string, number>;
    }>('modbus-registers-updated', (event) => {
      const payload = event.payload;
      if (!payload?.device_id) return;
      setConfigs((prev) => {
        const c = prev[payload.device_id];
        if (!c?.registers) return prev;
        const regs = c.registers.map((r) => {
          const addr = String(r.address);
          if (r.type === 'input_registers' && payload.input_registers?.[addr] !== undefined) {
            return { ...r, value: payload.input_registers[addr] };
          }
          if (r.type === 'holding_registers' && payload.holding_registers?.[addr] !== undefined) {
            return { ...r, value: payload.holding_registers[addr] };
          }
          return r;
        });
        return { ...prev, [payload.device_id]: { ...c, registers: regs } };
      });
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  const updateConfig = useCallback((deviceId: string, updates: Partial<DeviceModbusConfig>) => {
    setConfigs((prev) => ({ ...prev, [deviceId]: { ...prev[deviceId], ...updates } }));
  }, []);

  const refreshServerStatus = useCallback(async () => {
    try {
      const runningIds = await invoke<string[]>('get_running_modbus_device_ids');
      setServerStatus((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((id) => {
          next[id] = { ...next[id], running: runningIds.includes(id) };
        });
        return next;
      });
    } catch {
      // ignore
    }
  }, []);

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
              <span className={`px-2 py-1 rounded text-xs font-medium ${serverStatus[selectedDevice!]?.running ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                {serverStatus[selectedDevice!]?.running ? '运行中' : '未运行'}
              </span>
              <button onClick={refreshServerStatus} className="p-1.5 hover:bg-gray-100 rounded transition-colors" title="刷新状态">
                <RefreshCw className="w-4 h-4 text-gray-500" />
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
                      <label className="block text-xs text-gray-600 mb-1" title="当前服务端按端口区分设备，未校验从站ID；客户端请求时通常使用 1">从站ID</label>
                      <input type="number" min={1} max={255} value={selectedConfig.slaveId} onChange={(e) => updateConfig(selectedDevice!, { slaveId: Number(e.target.value) || 1 })} className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm" />
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-3">寄存器列表（含义固定，可修改某含义的地址；值可编辑）</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm border border-gray-200">
                      <thead>
                        <tr className="bg-gray-50 border-b border-gray-200">
                          <th className="px-2 py-1.5 text-left font-medium text-gray-700">地址</th>
                          <th className="px-2 py-1.5 text-left font-medium text-gray-700">值</th>
                          <th className="px-2 py-1.5 text-left font-medium text-gray-700">类型</th>
                          <th className="px-2 py-1.5 text-left font-medium text-gray-700">名称</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedConfig.registers.map((reg, idx) => (
                          <tr key={`${reg.type}-${reg.address}-${idx}`} className="border-b border-gray-100">
                            <td className="px-2 py-1">
                              <input
                                type="number"
                                min={0}
                                max={65535}
                                value={reg.address}
                                onChange={(e) => {
                                  const next = [...selectedConfig.registers];
                                  next[idx] = { ...next[idx], address: Number(e.target.value) };
                                  updateConfig(selectedDevice!, { registers: next });
                                }}
                                className="w-20 px-1.5 py-0.5 border border-gray-300 rounded text-xs tabular-nums"
                              />
                            </td>
                            <td className="px-2 py-1">
                              <input
                                type="number"
                                min={reg.type === 'coils' || reg.type === 'discrete_inputs' ? 0 : 0}
                                max={reg.type === 'coils' || reg.type === 'discrete_inputs' ? 1 : 65535}
                                value={reg.value}
                                onChange={(e) => {
                                  const next = [...selectedConfig.registers];
                                  next[idx] = { ...next[idx], value: Number(e.target.value) };
                                  updateConfig(selectedDevice!, { registers: next });
                                }}
                                className="w-24 px-1.5 py-0.5 border border-gray-300 rounded text-xs"
                              />
                            </td>
                            <td className="px-2 py-1 text-gray-600 text-xs">{MODBUS_REGISTER_TYPE_LABELS[reg.type]}</td>
                            <td className="px-2 py-1 text-gray-600 text-xs">{reg.name ?? '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
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
                    <p>• Modbus 服务器随仿真启动自动启动；设备运行/关机请在「设备控制」页操作</p>
                    <p>• 每个设备独立运行一个 Modbus TCP 服务器，外部系统可通过写入功率寄存器控制设备</p>
                    <p>• 上方可针对单个设备开关「允许远程控制」；仿真页为全局总开关</p>
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
