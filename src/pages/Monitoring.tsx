/**
 * 实时监控页面 - 浅色主题
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { 
  RefreshCw, 
  Activity, 
  Zap, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  TrendingDown
} from 'lucide-react';
import { DEVICE_TYPES, DeviceType } from '../constants/deviceTypes';
import DataChart from '../components/monitoring/DataChart';

interface DeviceStatus {
  device_id: string;
  name: string;
  device_type: DeviceType;
  is_online: boolean;
  last_update?: number;
  active_power?: number;
  reactive_power?: number;
  voltage?: number;
  current?: number;
  data_source?: string;
}

interface SystemOverview {
  totalDevices: number;
  onlineDevices: number;
  totalGeneration: number;
  totalConsumption: number;
  gridExchange: number;
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

export default function Monitoring() {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [chartData, setChartData] = useState<Array<{ timestamp: number; value: number }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSimulationRunning] = useState(false);

  const loadDevices = useCallback(async () => {
    setIsLoading(true);
    try {
      const statuses = await invoke<DeviceStatus[]>('get_all_devices_status');
      setDevices(Array.isArray(statuses) ? statuses : []);
    } catch (error) {
      console.error('Failed to load devices:', error);
      setDevices([
        { device_id: 'device-1', name: '光伏-1', device_type: 'static_generator', is_online: true, active_power: 85.5, reactive_power: 12.3, voltage: 380, current: 145 },
        { device_id: 'device-2', name: '储能-2', device_type: 'storage', is_online: true, active_power: -25.0, reactive_power: 5.0, voltage: 380, current: 42 },
        { device_id: 'device-3', name: '负载-3', device_type: 'load', is_online: true, active_power: 45.0, reactive_power: 15.0, voltage: 378, current: 76 },
        { device_id: 'device-4', name: '充电桩-4', device_type: 'charger', is_online: false, active_power: 0, reactive_power: 0 },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadDeviceData = useCallback(async (deviceId: string) => {
    try {
      const data = await invoke<Array<[number, number | null, number | null]>>(
        'query_device_data',
        {
          device_id: deviceId,
          start_time: Date.now() / 1000 - 3600,
          end_time: Date.now() / 1000,
        }
      );
      const chartDataPoints = (data || [])
        .filter((row) => row[1] !== null && row[1] !== undefined)
        .map(([timestamp, power]) => ({ timestamp, value: Number(power) || 0 }));
      setChartData(chartDataPoints);
    } catch (_error) {
      setChartData([]);
    }
  }, []);

  const overview = useMemo<SystemOverview>(() => {
    const list = Array.isArray(devices) ? devices : [];
    const onlineDevices = list.filter((d) => d.is_online);
    const generation = list
      .filter((d) => d.device_type === 'static_generator' && d.active_power != null && Number(d.active_power) > 0)
      .reduce((sum, d) => sum + (Number(d.active_power) || 0), 0);
    const consumption = list
      .filter((d) => ['load', 'charger'].includes(d.device_type) && d.active_power != null)
      .reduce((sum, d) => sum + Math.abs(Number(d.active_power) || 0), 0);
    const gridExchange = list
      .filter((d) => d.device_type === 'external_grid')
      .reduce((sum, d) => sum + (Number(d.active_power) || 0), 0);
    return {
      totalDevices: list.length,
      onlineDevices: onlineDevices.length,
      totalGeneration: generation,
      totalConsumption: consumption,
      gridExchange,
    };
  }, [devices]);

  useEffect(() => {
    loadDevices();
    const interval = setInterval(loadDevices, 2000);
    const unsubscribePromise = listen('device-data-update', (event: any) => {
      const { device_id, data } = event.payload;
      setDevices((prevDevices) =>
        prevDevices.map((device) =>
          device.device_id === device_id
            ? { ...device, active_power: data.active_power, reactive_power: data.reactive_power, voltage: data.voltage, current: data.current, last_update: data.timestamp || Date.now() / 1000, is_online: true }
            : device
        )
      );
      if (selectedDevice === device_id) {
        setChartData((prev) => [
          ...prev.slice(-59),
          { timestamp: data.timestamp || Date.now() / 1000, value: data.active_power || 0 },
        ]);
      }
    });
    return () => {
      clearInterval(interval);
      unsubscribePromise.then((unsubscribe) => unsubscribe());
    };
  }, [loadDevices, selectedDevice]);

  useEffect(() => {
    if (selectedDevice) loadDeviceData(selectedDevice);
  }, [selectedDevice, loadDeviceData]);

  const selectedDeviceInfo = devices.find((d) => d.device_id === selectedDevice);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* 工具栏 */}
      <div className="px-4 py-2 bg-white border-b border-gray-200 flex items-center gap-4">
        <h1 className="text-base font-semibold text-gray-800">实时监控</h1>
        <div className="flex-1" />
        <span className={`text-xs ${isSimulationRunning ? 'text-green-600' : 'text-gray-400'}`}>
          {isSimulationRunning ? '仿真运行中' : '仿真未启动'}
        </span>
        <button onClick={loadDevices} disabled={isLoading} className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded transition-colors">
          <RefreshCw className={`w-4 h-4 text-gray-600 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* 系统概览 */}
      <div className="px-4 py-2 bg-white border-b border-gray-200">
        <div className="grid grid-cols-5 gap-3">
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="flex items-center gap-1 text-gray-500 mb-1">
              <Activity className="w-3 h-3" />
              <span className="text-xs">设备状态</span>
            </div>
            <div className="text-lg font-bold text-gray-800">{overview.onlineDevices}/{overview.totalDevices}</div>
          </div>
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="flex items-center gap-1 text-gray-500 mb-1">
              <TrendingUp className="w-3 h-3 text-orange-500" />
              <span className="text-xs">总发电</span>
            </div>
            <div className="text-lg font-bold text-orange-600">{(Number(overview.totalGeneration) || 0).toFixed(1)} kW</div>
          </div>
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="flex items-center gap-1 text-gray-500 mb-1">
              <TrendingDown className="w-3 h-3 text-purple-500" />
              <span className="text-xs">总消耗</span>
            </div>
            <div className="text-lg font-bold text-purple-600">{(Number(overview.totalConsumption) || 0).toFixed(1)} kW</div>
          </div>
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="flex items-center gap-1 text-gray-500 mb-1">
              <Zap className="w-3 h-3 text-blue-500" />
              <span className="text-xs">电网交换</span>
            </div>
            <div className={`text-lg font-bold ${(Number(overview.gridExchange) || 0) >= 0 ? 'text-blue-600' : 'text-green-600'}`}>
              {(Number(overview.gridExchange) || 0) >= 0 ? '+' : ''}{(Number(overview.gridExchange) || 0).toFixed(1)} kW
            </div>
          </div>
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="flex items-center gap-1 text-gray-500 mb-1">
              <Clock className="w-3 h-3" />
              <span className="text-xs">更新时间</span>
            </div>
            <div className="text-sm font-bold text-gray-800">{new Date().toLocaleTimeString()}</div>
          </div>
        </div>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 设备列表 */}
        <div className="w-72 bg-white border-r border-gray-200 overflow-y-auto">
          <div className="p-2 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700">设备列表</h2>
          </div>
          <div className="p-2 space-y-1">
            {devices.map((device) => {
              const isSelected = selectedDevice === device.device_id;
              return (
                <div
                  key={device.device_id}
                  onClick={() => setSelectedDevice(device.device_id)}
                  className={`p-2 rounded cursor-pointer transition-colors ${isSelected ? 'bg-blue-500 text-white' : 'bg-gray-50 hover:bg-gray-100'}`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded flex items-center justify-center ${isSelected ? 'bg-blue-400' : 'bg-white border border-gray-200'}`}>
                      <DeviceIcon type={device.device_type} size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1">
                        <span className={`text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-gray-800'}`}>{device.name}</span>
                        {device.is_online ? (
                          <CheckCircle className={`w-3 h-3 ${isSelected ? 'text-green-200' : 'text-green-500'}`} />
                        ) : (
                          <XCircle className={`w-3 h-3 ${isSelected ? 'text-red-200' : 'text-red-500'}`} />
                        )}
                      </div>
                      {device.active_power != null && Number(device.active_power) !== 0 && (
                        <div className={`text-xs ${isSelected ? 'text-blue-100' : 'text-gray-500'}`}>
                          P: {(Number(device.active_power)).toFixed(1)} kW
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
            {devices.length === 0 && (
              <div className="p-4 text-center text-gray-400 text-sm">暂无设备数据</div>
            )}
          </div>
        </div>

        {/* 设备详情 */}
        <div className="flex-1 overflow-y-auto p-4">
          {selectedDeviceInfo ? (
            <div className="space-y-4">
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-14 h-14 rounded-lg flex items-center justify-center bg-gray-50 border border-gray-200">
                    <DeviceIcon type={selectedDeviceInfo.device_type} size={36} />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-800">{selectedDeviceInfo.name}</h2>
                    <div className="text-sm text-gray-500">
                      {DEVICE_TYPES[selectedDeviceInfo.device_type]?.name} | ID: {selectedDeviceInfo.device_id}
                    </div>
                  </div>
                  <div className="ml-auto">
                    <span className={`px-2 py-1 rounded-full text-xs ${selectedDeviceInfo.is_online ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {selectedDeviceInfo.is_online ? '在线' : '离线'}
                    </span>
                  </div>
                </div>
                <div className="grid grid-cols-4 gap-3">
                  <div className="p-3 bg-gray-50 rounded border border-gray-200">
                    <div className="text-xs text-gray-500 mb-1">有功功率</div>
                    <div className="text-xl font-bold text-blue-600">{selectedDeviceInfo.active_power != null ? (Number(selectedDeviceInfo.active_power)).toFixed(1) : '-'} <span className="text-xs text-gray-400">kW</span></div>
                  </div>
                  <div className="p-3 bg-gray-50 rounded border border-gray-200">
                    <div className="text-xs text-gray-500 mb-1">无功功率</div>
                    <div className="text-xl font-bold text-purple-600">{selectedDeviceInfo.reactive_power != null ? (Number(selectedDeviceInfo.reactive_power)).toFixed(1) : '-'} <span className="text-xs text-gray-400">kVar</span></div>
                  </div>
                  <div className="p-3 bg-gray-50 rounded border border-gray-200">
                    <div className="text-xs text-gray-500 mb-1">电压</div>
                    <div className="text-xl font-bold text-yellow-600">{selectedDeviceInfo.voltage != null ? (Number(selectedDeviceInfo.voltage)).toFixed(0) : '-'} <span className="text-xs text-gray-400">V</span></div>
                  </div>
                  <div className="p-3 bg-gray-50 rounded border border-gray-200">
                    <div className="text-xs text-gray-500 mb-1">电流</div>
                    <div className="text-xl font-bold text-green-600">{selectedDeviceInfo.current != null ? (Number(selectedDeviceInfo.current)).toFixed(1) : '-'} <span className="text-xs text-gray-400">A</span></div>
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">功率趋势</h3>
                <div className="h-64">
                  <DataChart title="" data={chartData} unit="kW" color="#3b82f6" />
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400">
              <div className="text-center">
                <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>请从左侧选择设备查看详情</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
