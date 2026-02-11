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
import { getDataItemsForDevice, formatPowerKw, computeOverview, type SystemOverview } from '../utils/deviceDataItems';

interface DeviceStatus {
  device_id: string;
  name: string;
  device_type: DeviceType;
  is_online: boolean;
  last_update?: number;
  active_power?: number;
  reactive_power?: number;
  /** 仅电表有值：指向的设备 id，数据项与目标设备类型一致 */
  target_device_id?: string | null;
  /** 仅电表有值：从 Modbus 快照读取的电量（kWh/kVarh） */
  energy_export_kwh?: number | null;
  energy_import_kwh?: number | null;
  energy_total_kwh?: number | null;
  energy_reactive_export_kvarh?: number | null;
  energy_reactive_import_kvarh?: number | null;
  /** 仅储能有值：并离网模式，0=并网 1=离网（来自 Modbus HR 5095） */
  grid_mode?: number | null;
  /** 仅开关有值：闭合状态 */
  is_closed?: boolean | null;
}

interface DeviceDataPoint {
  device_id: string;
  timestamp: number;
  p_active: number | null;
  p_reactive: number | null;
  data_json: Record<string, unknown> | null;
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
      {type === 'switch' && (
        <>
          <line x1="6" y1="12" x2="11" y2="12" stroke={color} strokeWidth="2" />
          <line x1="13" y1="12" x2="18" y2="12" stroke={color} strokeWidth="2" />
          <circle cx="11" cy="12" r="2" fill={color} />
          <circle cx="13" cy="12" r="2" fill={color} />
        </>
      )}
      {!['static_generator', 'storage', 'load', 'charger', 'external_grid', 'switch'].includes(type) && (
        <rect x="4" y="4" width="16" height="16" fill="none" stroke={color} strokeWidth="2" />
      )}
    </svg>
  );
}

export default function Monitoring() {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [chartDataPoints, setChartDataPoints] = useState<DeviceDataPoint[]>([]);
  const [selectedChartSeries, setSelectedChartSeries] = useState<string>('active_power');
  const [chartSeriesOptions, setChartSeriesOptions] = useState<Array<{ key: string; label: string }>>([{ key: 'active_power', label: '有功功率 (kW)' }]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(() => Date.now());
  const [simulationState, setSimulationState] = useState<'Stopped' | 'Running' | 'Paused'>('Stopped');

  /**
   * 从拓扑元数据加载设备列表（主数据源），再叠加运行时状态。
   * 设备树始终以拓扑为准，不依赖 pandapower 返回的数据，
   * 避免开关断开导致计算失败/仿真自动停止后切换标签时设备消失。
   */
  const loadDevices = useCallback(async () => {
    setIsLoading(true);
    try {
      // 第1步：从拓扑元数据获取完整设备列表（轻量、可靠，不依赖仿真状态）
      const topoDevices = await invoke<Array<{ id: string; name: string; device_type: string; properties?: Record<string, unknown> }>>('get_all_devices');
      // 构建拓扑基准设备列表（所有设备始终显示，默认离线）
      const baseDevices: DeviceStatus[] = (Array.isArray(topoDevices) ? topoDevices : []).map((d) => ({
        device_id: d.id,
        name: d.name,
        device_type: d.device_type as DeviceType,
        is_online: false,
        is_closed: d.device_type === 'switch' ? (d.properties?.is_closed !== false) : undefined,
      }));

      // 第2步：尝试获取运行时状态（功率、在线状态等），失败时仍保留拓扑基准列表
      try {
        const statuses = await invoke<DeviceStatus[]>('get_all_devices_status');
        if (Array.isArray(statuses) && statuses.length > 0) {
          // 以运行时状态为主，但确保拓扑中的设备不会丢失
          const statusMap = new Map(statuses.map((s) => [s.device_id, s]));
          const merged = baseDevices.map((base) => statusMap.get(base.device_id) ?? base);
          // 追加运行时状态中存在但拓扑中不存在的设备（如动态添加的）
          for (const s of statuses) {
            if (!baseDevices.some((b) => b.device_id === s.device_id)) {
              merged.push(s);
            }
          }
          setDevices(merged);
        } else {
          setDevices(baseDevices);
        }
      } catch (statusError) {
        console.warn('获取运行时设备状态失败，使用拓扑基准列表:', statusError);
        setDevices(baseDevices);
      }
    } catch (error) {
      console.error('从拓扑加载设备失败:', error);
      // 连拓扑元数据都获取失败时，保留当前设备列表，不清空
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadDeviceData = useCallback(async (deviceId: string) => {
    try {
      const chartStart = await invoke<number | null>('get_latest_simulation_start_time');
      const now = Date.now() / 1000;
      const start = chartStart ?? (now - 3600);
      const data = await invoke<DeviceDataPoint[]>(
        'query_device_data',
        {
          deviceId: deviceId,
          startTime: start,
          endTime: now,
          maxPoints: 2000,
        }
      );
      const points: DeviceDataPoint[] = (data || []).map((p) => ({
        device_id: p.device_id,
        timestamp: p.timestamp,
        p_active: p.p_active ?? null,
        p_reactive: p.p_reactive ?? null,
        data_json: p.data_json && typeof p.data_json === 'object' ? (p.data_json as Record<string, unknown>) : null,
      }));
      setChartDataPoints(points);
      const device = devices.find((d) => d.device_id === deviceId);
      const items = getDataItemsForDevice(device?.device_type ?? 'load', device?.target_device_id, devices);
      const options = items.map(({ key, label }) => ({ key, label }));
      setChartSeriesOptions(options);
      if (options.length > 0 && !options.some((o) => o.key === selectedChartSeries)) {
        setSelectedChartSeries(options[0].key);
      }
    } catch (_error) {
      console.error('[loadDeviceData] Error:', _error);
      setChartDataPoints([]);
    }
  }, [selectedChartSeries, devices]);

  const refreshSimulationStatus = useCallback(async () => {
    try {
      const status = await invoke<{ state: string }>('get_simulation_status');
      setSimulationState((status?.state as 'Stopped' | 'Running' | 'Paused') ?? 'Stopped');
    } catch {
      setSimulationState('Stopped');
    }
  }, []);

  const overview = useMemo<SystemOverview>(() => {
    const list = Array.isArray(devices) ? devices : [];
    return computeOverview(list.map((d) => ({
      device_type: d.device_type,
      active_power: d.active_power,
      is_online: d.is_online,
    })));
  }, [devices]);

  useEffect(() => {
    const t = setInterval(() => setCurrentTime(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    refreshSimulationStatus();
    const statusInterval = setInterval(refreshSimulationStatus, 2000);
    return () => clearInterval(statusInterval);
  }, [refreshSimulationStatus]);

  useEffect(() => {
    loadDevices();
    const interval = setInterval(loadDevices, 2000);
    // 首拍完成后后端会写入 device_active，立即拉取一次设备状态，使设备树（含电表）正确显示在线
    const unsubCalcPromise = listen('calculation-result-update', () => {
      loadDevices();
    });
    const unsubscribePromise = listen('device-data-update', (event: any) => {
      const { device_id, data } = event.payload;
      setDevices((prevDevices) =>
        prevDevices.map((device) =>
          device.device_id === device_id
            ? { ...device, active_power: data.active_power, reactive_power: data.reactive_power, last_update: data.timestamp || Date.now() / 1000, is_online: true }
            : device
        )
      );
      // 趋势图：仅对当前选中设备从仿真引擎追加新点，避免周期性全量查询
      if (device_id !== selectedDevice || !data) return;
      const ts = typeof data.timestamp === 'number' ? data.timestamp : Date.now() / 1000;
      const dataJson = data.data_json && typeof data.data_json === 'object' ? (data.data_json as Record<string, unknown>) : null;
      const newPoint: DeviceDataPoint = {
        device_id,
        timestamp: ts,
        p_active: data.active_power != null ? Number(data.active_power) : null,
        p_reactive: data.reactive_power != null ? Number(data.reactive_power) : null,
        data_json: dataJson,
      };
      setChartDataPoints((prev) => {
        const lastTs = prev.length > 0 ? prev[prev.length - 1].timestamp : -Infinity;
        if (ts < lastTs) return prev;
        const next = ts === lastTs ? [...prev.slice(0, -1), newPoint] : [...prev, newPoint];
        return next.length > 3000 ? next.slice(-3000) : next;
      });
    });
    return () => {
      clearInterval(interval);
      unsubCalcPromise.then((unsubscribe) => unsubscribe());
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
        <span className={`text-xs ${simulationState === 'Running' ? 'text-green-600' : simulationState === 'Paused' ? 'text-amber-600' : 'text-gray-400'}`}>
          {simulationState === 'Running' ? '仿真运行中' : simulationState === 'Paused' ? '仿真已暂停' : '仿真未启动'}
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
            <div className="text-sm font-bold text-gray-800">{new Date(currentTime).toLocaleTimeString('zh-CN', { hour12: false })}</div>
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
                  onClick={() => {
                    // 即使是同一设备，也强制从 DB 重新加载完整数据（解决切换标签后数据不全的问题）
                    if (selectedDevice === device.device_id) {
                      loadDeviceData(device.device_id);
                    }
                    setSelectedDevice(device.device_id);
                  }}
                  className={`p-2 rounded cursor-pointer transition-colors ${isSelected ? 'bg-blue-500 text-white' : 'bg-gray-50 hover:bg-gray-100'}`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded flex items-center justify-center ${isSelected ? 'bg-blue-400' : 'bg-white border border-gray-200'}`}>
                      <DeviceIcon type={device.device_type} size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1">
                        <span className={`text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-gray-800'}`}>{device.name}</span>
                        {device.device_type === 'switch' ? (
                          <span className={`text-xs px-1 rounded ${device.is_closed !== false
                            ? (isSelected ? 'bg-green-300 text-green-800' : 'bg-green-100 text-green-700')
                            : (isSelected ? 'bg-red-300 text-red-800' : 'bg-red-100 text-red-700')}`}>
                            {device.is_closed !== false ? '闭合' : '断开'}
                          </span>
                        ) : device.is_online ? (
                          <CheckCircle className={`w-3 h-3 ${isSelected ? 'text-green-200' : 'text-green-500'}`} />
                        ) : (
                          <XCircle className={`w-3 h-3 ${isSelected ? 'text-red-200' : 'text-red-500'}`} />
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        <span className={`text-xs ${isSelected ? 'text-blue-100' : 'text-gray-500'}`}>
                          {DEVICE_TYPES[device.device_type]?.name ?? device.device_type}
                        </span>
                      </div>
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
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-gray-50 rounded border border-gray-200">
                    <div className="text-xs text-gray-500 mb-1">有功功率</div>
                    <div className="text-xl font-bold text-blue-600">{formatPowerKw(selectedDeviceInfo.active_power)} <span className="text-xs text-gray-400">kW</span></div>
                  </div>
                  <div className="p-3 bg-gray-50 rounded border border-gray-200">
                    <div className="text-xs text-gray-500 mb-1">无功功率</div>
                    <div className="text-xl font-bold text-purple-600">{formatPowerKw(selectedDeviceInfo.reactive_power)} <span className="text-xs text-gray-400">kVar</span></div>
                  </div>
                </div>
                {selectedDeviceInfo.device_type === 'storage' && selectedDeviceInfo.grid_mode != null && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="text-xs text-gray-500 mb-1">并离网状态</div>
                    <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-sm font-medium ${selectedDeviceInfo.grid_mode === 0 ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>
                      {selectedDeviceInfo.grid_mode === 0 ? '并网' : selectedDeviceInfo.grid_mode === 1 ? '离网' : `寄存器值 ${selectedDeviceInfo.grid_mode}`}
                    </div>
                    <span className="ml-2 text-xs text-gray-500">（Modbus HR 5095，0=并网参与计算，1=离网不参与）</span>
                  </div>
                )}
                {selectedDeviceInfo.device_type === 'meter' && (selectedDeviceInfo.energy_export_kwh != null || selectedDeviceInfo.energy_import_kwh != null || selectedDeviceInfo.energy_total_kwh != null || selectedDeviceInfo.energy_reactive_export_kvarh != null || selectedDeviceInfo.energy_reactive_import_kvarh != null) && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="text-xs text-gray-500 mb-2">电量数据（Modbus，显示单位 0.1 kWh/0.1 kVarh）</div>
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                      {selectedDeviceInfo.energy_export_kwh != null && (
                        <div className="p-2 bg-gray-50 rounded border border-gray-100">
                          <div className="text-xs text-gray-500">有功导出(上网)</div>
                          <div className="text-sm font-medium text-gray-800">{(selectedDeviceInfo.energy_export_kwh ?? 0) * 10} <span className="text-xs text-gray-500">×0.1 kWh</span></div>
                        </div>
                      )}
                      {selectedDeviceInfo.energy_import_kwh != null && (
                        <div className="p-2 bg-gray-50 rounded border border-gray-100">
                          <div className="text-xs text-gray-500">有功导入(下网)</div>
                          <div className="text-sm font-medium text-gray-800">{(selectedDeviceInfo.energy_import_kwh ?? 0) * 10} <span className="text-xs text-gray-500">×0.1 kWh</span></div>
                        </div>
                      )}
                      {selectedDeviceInfo.energy_total_kwh != null && (
                        <div className="p-2 bg-gray-50 rounded border border-gray-100">
                          <div className="text-xs text-gray-500">组合有功总电能</div>
                          <div className="text-sm font-medium text-gray-800">{(selectedDeviceInfo.energy_total_kwh ?? 0) * 10} <span className="text-xs text-gray-500">×0.1 kWh</span></div>
                        </div>
                      )}
                      {selectedDeviceInfo.energy_reactive_export_kvarh != null && (
                        <div className="p-2 bg-gray-50 rounded border border-gray-100">
                          <div className="text-xs text-gray-500">无功导出</div>
                          <div className="text-sm font-medium text-gray-800">{(selectedDeviceInfo.energy_reactive_export_kvarh ?? 0) * 10} <span className="text-xs text-gray-500">×0.1 kVarh</span></div>
                        </div>
                      )}
                      {selectedDeviceInfo.energy_reactive_import_kvarh != null && (
                        <div className="p-2 bg-gray-50 rounded border border-gray-100">
                          <div className="text-xs text-gray-500">无功导入</div>
                          <div className="text-sm font-medium text-gray-800">{(selectedDeviceInfo.energy_reactive_import_kvarh ?? 0) * 10} <span className="text-xs text-gray-500">×0.1 kVarh</span></div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                <div className="mt-3 pt-3 border-t border-gray-200 min-h-[4.5rem]">
                  <div className="text-xs text-gray-500 mb-2">最新数据项</div>
                  {(() => {
                    const lastPoint = chartDataPoints.length > 0 ? chartDataPoints[chartDataPoints.length - 1] : null;
                    const dj = lastPoint?.data_json;
                    if (!dj || typeof dj !== 'object') {
                      return <div className="text-sm text-gray-400 py-2">暂无明细数据</div>;
                    }
                    const items = getDataItemsForDevice(selectedDeviceInfo.device_type, selectedDeviceInfo.target_device_id, devices);
                    const entries = items
                      .filter((item) => item.key in dj && typeof dj[item.key] === 'number')
                      .map((item) => ({ key: item.key, label: item.label, unit: item.unit, value: Number(dj[item.key]) }));
                    if (entries.length === 0) {
                      return <div className="text-sm text-gray-400 py-2">暂无明细数据</div>;
                    }
                    return (
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {entries.map(({ key, label, value, unit }) => (
                          <div key={key} className="p-2 bg-gray-50 rounded border border-gray-100">
                            <div className="text-xs text-gray-500 truncate">{label}</div>
                            <div className="text-sm font-medium text-gray-800">{(value).toFixed(3)}{unit ? ` ${unit}` : ''}</div>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </div>
              </div>
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-700">数据趋势</h3>
                  <select
                    value={selectedChartSeries}
                    onChange={(e) => setSelectedChartSeries(e.target.value)}
                    className="text-xs border border-gray-300 rounded px-2 py-1 bg-white text-gray-700"
                  >
                    {chartSeriesOptions.map((opt) => (
                      <option key={opt.key} value={opt.key}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div className="h-64">
                  <DataChart
                    key={selectedDevice}
                    title=""
                    data={chartDataPoints}
                    seriesKey={selectedChartSeries}
                    unit={(() => {
                      const items = getDataItemsForDevice(selectedDeviceInfo.device_type, selectedDeviceInfo.target_device_id, devices);
                      const item = items.find((i) => i.key === selectedChartSeries);
                      return item?.unit ?? (selectedChartSeries.includes('q') || selectedChartSeries === 'reactive_power' ? 'MVar' : 'MW');
                    })()}
                    color="#3b82f6"
                    enableDataZoom={simulationState !== 'Running'}
                  />
                  {simulationState === 'Running' && (
                    <p className="text-xs text-blue-600 mt-1">仿真运行中，缩放已禁用（停止或暂停后可缩放查看）</p>
                  )}
                  {simulationState === 'Paused' && (
                    <p className="text-xs text-amber-600 mt-1">已暂停：可拖拽时间轴或鼠标滚轮缩放查看</p>
                  )}
                  {simulationState === 'Stopped' && chartDataPoints.length > 0 && (
                    <p className="text-xs text-gray-500 mt-1">可拖拽时间轴或鼠标滚轮缩放查看</p>
                  )}
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
