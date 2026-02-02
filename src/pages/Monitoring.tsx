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
}

interface DeviceDataPoint {
  device_id: string;
  timestamp: number;
  p_active: number | null;
  p_reactive: number | null;
  data_json: Record<string, unknown> | null;
}

interface SystemOverview {
  totalDevices: number;
  onlineDevices: number;
  totalGeneration: number;
  totalConsumption: number;
  gridExchange: number;
}

/** 安全格式化功率显示，避免 NaN / undefined 导致 "-.kw" 或闪烁 */
function formatPowerKw(value: number | null | undefined): string {
  if (value == null || typeof value !== 'number' || Number.isNaN(value)) return '-';
  return Number(value).toFixed(1);
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
  const [chartDataPoints, setChartDataPoints] = useState<DeviceDataPoint[]>([]);
  const [selectedChartSeries, setSelectedChartSeries] = useState<string>('active_power');
  const [chartSeriesOptions, setChartSeriesOptions] = useState<Array<{ key: string; label: string }>>([{ key: 'active_power', label: '有功功率 (kW)' }]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(() => Date.now());
  const [simulationState, setSimulationState] = useState<'Stopped' | 'Running' | 'Paused'>('Stopped');

  const loadDevices = useCallback(async () => {
    setIsLoading(true);
    try {
      const statuses = await invoke<DeviceStatus[]>('get_all_devices_status');
      setDevices(Array.isArray(statuses) ? statuses : []);
    } catch (error) {
      console.error('Failed to load devices:', error);
      setDevices([]);
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
      if (points.length > 0 && points[0].data_json) {
        const keys = Object.keys(points[0].data_json).filter((k) => typeof (points[0].data_json as Record<string, unknown>)[k] === 'number');
        const labels: Record<string, string> = {
          active_power: '有功功率 (kW)',
          reactive_power: '无功功率 (kVar)',
          p_from_mw: 'P_from (MW)',
          q_from_mvar: 'Q_from (MVar)',
          p_to_mw: 'P_to (MW)',
          q_to_mvar: 'Q_to (MVar)',
          pl_mw: 'Pl (MW)',
          ql_mvar: 'Ql (MVar)',
          p_hv_mw: 'P_HV (MW)',
          q_hv_mvar: 'Q_HV (MVar)',
          p_lv_mw: 'P_LV (MW)',
          q_lv_mvar: 'Q_LV (MVar)',
          vm_pu: '电压 (pu)',
          voltage: '电压 (V)',
        };
        const options = [{ key: 'active_power', label: labels.active_power || '有功' }, { key: 'reactive_power', label: labels.reactive_power || '无功' }, ...keys.filter((k) => !['active_power', 'reactive_power'].includes(k)).map((k) => ({ key: k, label: labels[k] || k }))];
        setChartSeriesOptions(options);
      } else {
        setChartSeriesOptions([{ key: 'active_power', label: '有功功率 (kW)' }, { key: 'reactive_power', label: '无功功率 (kVar)' }]);
      }
    } catch (_error) {
      console.error('[loadDeviceData] Error:', _error);
      setChartDataPoints([]);
    }
  }, [selectedChartSeries]);

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
    const onlineDevices = list.filter((d) => d.is_online);
    const generation = list
      .filter((d) => d.device_type === 'static_generator' && d.active_power != null && Number(d.active_power) > 0)
      .reduce((sum, d) => sum + (Number(d.active_power) || 0), 0);
    // 总消耗 = 负载 + 充电桩 + 储能（正=充电=消耗）；流入为正流出为负
    const loadCharger = list
      .filter((d) => ['load', 'charger'].includes(d.device_type) && d.active_power != null)
      .reduce((sum, d) => sum + Math.abs(Number(d.active_power) || 0), 0);
    const storageConsumption = list
      .filter((d) => d.device_type === 'storage' && d.active_power != null)
      .reduce((sum, d) => sum + Math.max(0, Number(d.active_power) || 0), 0);
    const consumption = loadCharger + storageConsumption;
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
      // #region agent log
      fetch('http://127.0.0.1:7244/ingest/b8e265ce-e1a5-4ce6-9816-ec26ce5c4c56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Monitoring.tsx:260',message:'device-data-update for selected device',data:{deviceId:device_id,timestamp:data.timestamp},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'ZOOM'})}).catch(()=>{});
      // #endregion
      const ts = typeof data.timestamp === 'number' ? data.timestamp : Date.now() / 1000;
      const newPoint: DeviceDataPoint = {
        device_id,
        timestamp: ts,
        p_active: data.active_power != null ? Number(data.active_power) : null,
        p_reactive: data.reactive_power != null ? Number(data.reactive_power) : null,
        data_json: null, // 事件未携带详细 data_json，仅用于有功/无功曲线
      };
      setChartDataPoints((prev) => {
        const lastTs = prev.length > 0 ? prev[prev.length - 1].timestamp : -Infinity;
        if (ts < lastTs) return prev;
        const next = ts === lastTs ? [...prev.slice(0, -1), newPoint] : [...prev, newPoint];
        // #region agent log
        fetch('http://127.0.0.1:7244/ingest/b8e265ce-e1a5-4ce6-9816-ec26ce5c4c56',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'Monitoring.tsx:274',message:'setChartDataPoints from event',data:{prevLength:prev.length,nextLength:next.length,wasReplaced:ts===lastTs},timestamp:Date.now(),sessionId:'debug-session',hypothesisId:'ZOOM'})}).catch(()=>{});
        // #endregion
        return next.length > 3000 ? next.slice(-3000) : next;
      });
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
                        {device.is_online ? (
                          <CheckCircle className={`w-3 h-3 ${isSelected ? 'text-green-200' : 'text-green-500'}`} />
                        ) : (
                          <XCircle className={`w-3 h-3 ${isSelected ? 'text-red-200' : 'text-red-500'}`} />
                        )}
                      </div>
                      <div className={`text-xs ${isSelected ? 'text-blue-100' : 'text-gray-500'}`}>
                        {DEVICE_TYPES[device.device_type]?.name ?? device.device_type}
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
                {chartDataPoints.length > 0 && chartDataPoints[chartDataPoints.length - 1].data_json && (() => {
                  const dj = chartDataPoints[chartDataPoints.length - 1].data_json!;
                  const numKeys = Object.entries(dj).filter(([, v]) => typeof v === 'number') as [string, number][];
                  if (numKeys.length === 0) return null;
                  return (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <div className="text-xs text-gray-500 mb-2">最新数据项</div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {numKeys.slice(0, 8).map(([k, v]) => (
                          <div key={k} className="p-2 bg-gray-50 rounded border border-gray-100">
                            <div className="text-xs text-gray-500 truncate">{k}</div>
                            <div className="text-sm font-medium text-gray-800">{(Number(v)).toFixed(3)}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
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
                    unit={selectedChartSeries.includes('q') || selectedChartSeries === 'reactive_power' ? 'kVar' : 'kW'}
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
