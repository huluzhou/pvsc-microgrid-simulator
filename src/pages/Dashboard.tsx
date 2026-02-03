/**
 * 数据看板 - 本地 DB / CSV / 远程 SSH 数据源，设备列表由数据推导，UI 与监控一致
 */
import { useState, useCallback, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { open as openDialog, save as saveDialog } from '@tauri-apps/plugin-dialog';
import {
  RefreshCw,
  Activity,
  AlertTriangle,
  Clock,
  LayoutDashboard,
  Download,
} from 'lucide-react';
import { useEffect } from 'react';
import { DEVICE_TYPES, DeviceType, DEVICE_TYPE_TO_CN } from '../constants/deviceTypes';
import DataChart from '../components/monitoring/DataChart';
import {
  getDataItemsForDevice,
  computeOverview,
  type SystemOverview,
  type DeviceItemForDataItems,
} from '../utils/deviceDataItems';

interface DeviceMetadata {
  id: string;
  name: string;
  device_type: string;
}

type DataSourceType = 'local_default' | 'local_file' | 'csv' | 'ssh';

interface DeviceDataPoint {
  device_id: string;
  timestamp: number;
  p_active: number | null;
  p_reactive: number | null;
  data_json: Record<string, unknown> | null;
}

interface DashboardDevice {
  device_id: string;
  name: string;
  device_type: DeviceType;
  active_power?: number;
  reactive_power?: number;
}

function DeviceIcon({ type, size = 24 }: { type: string; size?: number }) {
  const info = DEVICE_TYPES[type as DeviceType];
  const color = info?.color || '#666';
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
      <rect x="4" y="4" width="16" height="16" fill="none" stroke={color} strokeWidth="2" />
    </svg>
  );
}

export default function Dashboard() {
  const [dataSource, setDataSource] = useState<DataSourceType>('local_default');
  const [deviceIds, setDeviceIds] = useState<string[]>([]);
  const [pointsByDevice, setPointsByDevice] = useState<Record<string, DeviceDataPoint[]>>({});
  const [localDbPath, setLocalDbPath] = useState<string | null>(null);
  const [sshConnected, setSshConnected] = useState(false);
  const [sshConfig, setSshConfig] = useState({ host: '', port: 22, user: '', password: '' });
  const [remoteDbPath, setRemoteDbPath] = useState('');
  const [startTime, setStartTime] = useState<number>(() => (Date.now() / 1000) - 7 * 24 * 3600);
  const [endTime, setEndTime] = useState<number>(() => Date.now() / 1000);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [chartDataPoints, setChartDataPoints] = useState<DeviceDataPoint[]>([]);
  const [selectedChartSeries, setSelectedChartSeries] = useState<string>('active_power');
  const [chartSeriesOptions, setChartSeriesOptions] = useState<Array<{ key: string; label: string }>>([
    { key: 'active_power', label: '有功功率 (kW)' },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deviceMetadataMap, setDeviceMetadataMap] = useState<Record<string, DeviceMetadata>>({});

  const devices: DashboardDevice[] = useMemo(() => {
    return deviceIds.map((id) => {
      const meta = deviceMetadataMap[id];
      const points = pointsByDevice[id] || [];
      const last = points.length > 0 ? points[points.length - 1] : null;
      const deviceType = (meta?.device_type as DeviceType) || 'load';
      return {
        device_id: id,
        name: meta?.name ?? id,
        device_type: deviceType,
        active_power: last?.p_active ?? undefined,
        reactive_power: last?.p_reactive ?? undefined,
      };
    });
  }, [deviceIds, pointsByDevice, deviceMetadataMap]);

  const overview: SystemOverview = useMemo(() => {
    return computeOverview(
      devices.map((d) => ({
        device_type: d.device_type,
        active_power: d.active_power,
        is_online: true,
      }))
    );
  }, [devices]);

  const loadLocalDefault = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      const result = await invoke<{ device_ids: string[]; deviceTypes: Record<string, string> }>('get_dashboard_device_ids');
      const ids = result?.device_ids ?? [];
      setDeviceIds(Array.isArray(ids) ? ids : []);
      setPointsByDevice({});
      setLocalDbPath(null);
      const metaList = await invoke<DeviceMetadata[]>('get_all_devices').catch(() => []);
      const base = Array.isArray(metaList) ? Object.fromEntries(metaList.map((d) => [d.id, d])) : {};
      const typesFromDb = result?.deviceTypes ?? {};
      const merged: Record<string, DeviceMetadata> = { ...base };
      for (const id of ids) {
        merged[id] = {
          id,
          name: merged[id]?.name ?? id,
          device_type: typesFromDb[id] ?? merged[id]?.device_type ?? 'load',
        };
      }
      setDeviceMetadataMap(merged);
    } catch (e) {
      setError(String(e));
      setDeviceIds([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadLocalFile = useCallback(async () => {
    setError(null);
    try {
      const defaultPath = await invoke<string>('get_app_database_path').catch(() => undefined);
      const path = await openDialog({
        title: '选择本地数据库',
        filters: [{ name: 'SQLite', extensions: ['db', 'sqlite'] }],
        ...(defaultPath ? { defaultPath } : {}),
      });
      if (!path || typeof path !== 'string') return;
      const result = await invoke<{ device_ids: string[]; deviceTypes: Record<string, string> }>('dashboard_list_devices_from_path', { dbPath: path });
      const ids = result?.device_ids ?? [];
      setDeviceIds(Array.isArray(ids) ? ids : []);
      setPointsByDevice({});
      setLocalDbPath(path);
      setDataSource('local_file');
      const metaList = await invoke<DeviceMetadata[]>('get_all_devices').catch(() => []);
      const base = Array.isArray(metaList) ? Object.fromEntries(metaList.map((d) => [d.id, d])) : {};
      const typesFromDb = result?.deviceTypes ?? {};
      const merged: Record<string, DeviceMetadata> = { ...base };
      for (const id of ids) {
        merged[id] = {
          id,
          name: merged[id]?.name ?? id,
          device_type: typesFromDb[id] ?? merged[id]?.device_type ?? 'load',
        };
      }
      setDeviceMetadataMap(merged);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const refreshLocalFile = useCallback(async () => {
    if (!localDbPath) return;
    setError(null);
    setIsLoading(true);
    try {
      const result = await invoke<{ device_ids: string[]; deviceTypes: Record<string, string> }>('dashboard_list_devices_from_path', { dbPath: localDbPath });
      const ids = result?.device_ids ?? [];
      setDeviceIds(Array.isArray(ids) ? ids : []);
      const metaList = await invoke<DeviceMetadata[]>('get_all_devices').catch(() => []);
      const base = Array.isArray(metaList) ? Object.fromEntries(metaList.map((d) => [d.id, d])) : {};
      const typesFromDb = result?.deviceTypes ?? {};
      const merged: Record<string, DeviceMetadata> = { ...base };
      for (const id of ids) {
        merged[id] = {
          id,
          name: merged[id]?.name ?? id,
          device_type: typesFromDb[id] ?? merged[id]?.device_type ?? 'load',
        };
      }
      setDeviceMetadataMap(merged);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }, [localDbPath]);

  const loadCsv = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      const path = await openDialog({
        title: '选择 CSV 文件',
        filters: [{ name: 'CSV', extensions: ['csv'] }],
      });
      if (!path || typeof path !== 'string') return;
      const result = await invoke<{ device_ids: string[]; points_by_device: Record<string, Array<{
        device_id: string;
        timestamp: number;
        p_active: number | null;
        p_reactive: number | null;
        data_json: unknown;
      }>> }>('dashboard_parse_csv', { filePath: path });
      setDeviceIds(result.device_ids || []);
      const byDevice: Record<string, DeviceDataPoint[]> = {};
      for (const [id, pts] of Object.entries(result.points_by_device || {})) {
        byDevice[id] = (pts || []).map((p) => ({
          device_id: p.device_id,
          timestamp: p.timestamp,
          p_active: p.p_active ?? null,
          p_reactive: p.p_reactive ?? null,
          data_json: p.data_json && typeof p.data_json === 'object' ? (p.data_json as Record<string, unknown>) : null,
        }));
      }
      setPointsByDevice(byDevice);
      setDataSource('csv');
    } catch (e) {
      setError(String(e));
      setDeviceIds([]);
      setPointsByDevice({});
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sshConnect = useCallback(async () => {
    setError(null);
    setIsLoading(true);
    try {
      await invoke('ssh_connect', {
        config: {
          host: sshConfig.host,
          port: sshConfig.port,
          user: sshConfig.user,
          authMethod: { Password: sshConfig.password },
        },
      });
      setSshConnected(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }, [sshConfig]);

  const sshDisconnect = useCallback(async () => {
    setError(null);
    try {
      await invoke('ssh_disconnect');
      setSshConnected(false);
    } catch (e) {
      setError(String(e));
    }
  }, []);

  const loadRemote = useCallback(async () => {
    if (!sshConnected || !remoteDbPath.trim()) {
      setError('请先连接 SSH 并填写远端数据库路径');
      return;
    }
    setError(null);
    setIsLoading(true);
    try {
      const result = await invoke<{ device_ids: string[]; points_by_device: Record<string, Array<{
        device_id: string;
        timestamp: number;
        p_active: number | null;
        p_reactive: number | null;
        data_json: unknown;
      }>> }>('ssh_query_remote_device_data', {
        dbPath: remoteDbPath.trim(),
        startTime: startTime,
        endTime: endTime,
        maxPoints: 2000,
      });
      setDeviceIds(result.device_ids || []);
      const byDevice: Record<string, DeviceDataPoint[]> = {};
      for (const [id, pts] of Object.entries(result.points_by_device || {})) {
        byDevice[id] = (pts || []).map((p) => ({
          device_id: p.device_id,
          timestamp: p.timestamp,
          p_active: p.p_active ?? null,
          p_reactive: p.p_reactive ?? null,
          data_json: p.data_json && typeof p.data_json === 'object' ? (p.data_json as Record<string, unknown>) : null,
        }));
      }
      setPointsByDevice(byDevice);
      setDataSource('ssh');
      const metaList = await invoke<DeviceMetadata[]>('get_all_devices').catch(() => []);
      setDeviceMetadataMap(Array.isArray(metaList) ? Object.fromEntries(metaList.map((d) => [d.id, d])) : {});
    } catch (e) {
      setError(String(e));
      setDeviceIds([]);
      setPointsByDevice({});
    } finally {
      setIsLoading(false);
    }
  }, [sshConnected, remoteDbPath, startTime, endTime]);

  const exportRemoteCsv = useCallback(async () => {
    if (!sshConnected || !remoteDbPath.trim()) {
      setError('请先连接 SSH 并填写远端数据库路径');
      return;
    }
    setError(null);
    try {
      const path = await saveDialog({
        title: '导出远程查询结果为 CSV',
        defaultPath: `device_data_${new Date().toISOString().slice(0, 10)}.csv`,
        filters: [{ name: 'CSV', extensions: ['csv'] }],
      });
      if (!path || typeof path !== 'string') return;
      setIsLoading(true);
      const result = await invoke<{ device_ids: string[]; points_by_device: Record<string, Array<{
        device_id: string;
        timestamp: number;
        p_active: number | null;
        p_reactive: number | null;
        data_json: unknown;
      }>> }>('ssh_query_remote_device_data', {
        dbPath: remoteDbPath.trim(),
        startTime,
        endTime,
        maxPoints: 50_000,
        exportPath: path,
      });
      setDeviceIds(result.device_ids || []);
      const byDevice: Record<string, DeviceDataPoint[]> = {};
      for (const [id, pts] of Object.entries(result.points_by_device || {})) {
        byDevice[id] = (pts || []).map((p) => ({
          device_id: p.device_id,
          timestamp: p.timestamp,
          p_active: p.p_active ?? null,
          p_reactive: p.p_reactive ?? null,
          data_json: p.data_json && typeof p.data_json === 'object' ? (p.data_json as Record<string, unknown>) : null,
        }));
      }
      setPointsByDevice(byDevice);
      setDataSource('ssh');
    } catch (e) {
      setError(String(e));
    } finally {
      setIsLoading(false);
    }
  }, [sshConnected, remoteDbPath, startTime, endTime]);

  const loadDeviceData = useCallback(
    async (deviceId: string) => {
      if (dataSource === 'csv' || dataSource === 'ssh') {
        const pts = pointsByDevice[deviceId] || [];
        setChartDataPoints(pts);
        const items = getDataItemsForDevice('load', null, devices as DeviceItemForDataItems[]);
        const options = items.map(({ key, label }) => ({ key, label }));
        setChartSeriesOptions(options);
        if (options.length > 0 && !options.some((o) => o.key === selectedChartSeries)) {
          setSelectedChartSeries(options[0].key);
        }
        return;
      }
      try {
        const start = startTime;
        const end = endTime;
        let data: DeviceDataPoint[];
        if (dataSource === 'local_file' && localDbPath) {
          data = await invoke<DeviceDataPoint[]>('query_device_data_from_path', {
            dbPath: localDbPath,
            deviceId,
            startTime: start,
            endTime: end,
            maxPoints: 2000,
          });
        } else {
          data = await invoke<DeviceDataPoint[]>('query_device_data', {
            deviceId,
            startTime: start,
            endTime: end,
            maxPoints: 2000,
          });
        }
        const points = (data || []).map((p) => ({
          device_id: p.device_id,
          timestamp: p.timestamp,
          p_active: p.p_active ?? null,
          p_reactive: p.p_reactive ?? null,
          data_json: p.data_json && typeof p.data_json === 'object' ? (p.data_json as Record<string, unknown>) : null,
        }));
        setChartDataPoints(points);
        const items = getDataItemsForDevice('load', null, devices as DeviceItemForDataItems[]);
        const options = items.map(({ key, label }) => ({ key, label }));
        setChartSeriesOptions(options);
        if (options.length > 0 && !options.some((o) => o.key === selectedChartSeries)) {
          setSelectedChartSeries(options[0].key);
        }
      } catch (_e) {
        setChartDataPoints([]);
      }
    },
    [dataSource, localDbPath, pointsByDevice, startTime, endTime, devices, selectedChartSeries]
  );

  const onSelectDevice = useCallback(
    (deviceId: string) => {
      setSelectedDevice(deviceId);
      loadDeviceData(deviceId);
    },
    [loadDeviceData]
  );

  const selectedDeviceInfo = devices.find((d) => d.device_id === selectedDevice);

  useEffect(() => {
    if (dataSource === 'local_default') {
      loadLocalDefault();
    }
  }, []);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="px-4 py-2 bg-white border-b border-gray-200 flex items-center gap-4 flex-wrap">
        <h1 className="text-base font-semibold text-gray-800 flex items-center gap-2">
          <LayoutDashboard className="w-5 h-5" />
          数据看板
        </h1>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500">数据源：</span>
          <button
            onClick={() => { setDataSource('local_default'); loadLocalDefault(); }}
            className={`px-2 py-1 rounded text-xs ${dataSource === 'local_default' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
          >
            当前应用数据库
          </button>
          <button
            onClick={loadLocalFile}
            className={`px-2 py-1 rounded text-xs ${dataSource === 'local_file' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
          >
            选择本地数据库
          </button>
          <button
            onClick={loadCsv}
            title="支持长表 CSV：device_id, timestamp 或 local_timestamp, p_active 或 p_mw, p_reactive 或 q_mvar, 可选 data_json"
            className={`px-2 py-1 rounded text-xs ${dataSource === 'csv' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
          >
            CSV 文件
          </button>
          <div className="flex items-center gap-1">
            <input
              placeholder="主机"
              value={sshConfig.host}
              onChange={(e) => setSshConfig((c) => ({ ...c, host: e.target.value }))}
              className="w-24 px-1 py-0.5 border rounded text-xs"
            />
            <input
              type="number"
              placeholder="端口"
              value={sshConfig.port}
              onChange={(e) => setSshConfig((c) => ({ ...c, port: Number(e.target.value) || 22 }))}
              className="w-14 px-1 py-0.5 border rounded text-xs"
            />
            <input
              placeholder="用户"
              value={sshConfig.user}
              onChange={(e) => setSshConfig((c) => ({ ...c, user: e.target.value }))}
              className="w-20 px-1 py-0.5 border rounded text-xs"
            />
            <input
              type="password"
              placeholder="密码"
              value={sshConfig.password}
              onChange={(e) => setSshConfig((c) => ({ ...c, password: e.target.value }))}
              className="w-20 px-1 py-0.5 border rounded text-xs"
            />
            {!sshConnected ? (
              <button onClick={sshConnect} disabled={isLoading} className="px-2 py-1 bg-green-600 text-white rounded text-xs">
                连接 SSH
              </button>
            ) : (
              <button onClick={sshDisconnect} className="px-2 py-1 bg-gray-500 text-white rounded text-xs">
                断开
              </button>
            )}
            {sshConnected && (
              <>
                <input
                  placeholder="远端 DB 路径"
                  value={remoteDbPath}
                  onChange={(e) => setRemoteDbPath(e.target.value)}
                  className="w-40 px-1 py-0.5 border rounded text-xs"
                />
                <button onClick={loadRemote} disabled={isLoading} className="px-2 py-1 bg-blue-600 text-white rounded text-xs">
                  加载远程数据
                </button>
                <button onClick={exportRemoteCsv} disabled={isLoading} className="px-2 py-1 bg-gray-600 text-white rounded text-xs flex items-center gap-1" title="将当前时间范围的远程查询结果导出为 CSV 文件">
                  <Download className="w-3 h-3" />
                  导出 CSV
                </button>
              </>
            )}
          </div>
        </div>
        {(dataSource === 'local_default' || dataSource === 'local_file') && (
          <button onClick={dataSource === 'local_default' ? loadLocalDefault : refreshLocalFile} disabled={isLoading || (dataSource === 'local_file' && !localDbPath)} className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded">
            <RefreshCw className={`w-4 h-4 text-gray-600 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>
      {error && (
        <div className="px-4 py-2 bg-red-50 border-b border-red-200 flex items-center gap-2 text-red-700 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
      <div className="px-4 py-2 bg-white border-b border-gray-200">
        <div className="grid grid-cols-2 gap-3 max-w-md">
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="flex items-center gap-1 text-gray-500 mb-1">
              <Activity className="w-3 h-3" />
              <span className="text-xs">设备数</span>
            </div>
            <div className="text-lg font-bold text-gray-800">{overview.totalDevices}</div>
          </div>
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="flex items-center gap-1 text-gray-500 mb-1">
              <Clock className="w-3 h-3" />
              <span className="text-xs">数据源</span>
            </div>
            <div className="text-sm font-bold text-gray-800">
              {dataSource === 'local_default' && '当前 DB'}
              {dataSource === 'local_file' && '本地文件'}
              {dataSource === 'csv' && 'CSV'}
              {dataSource === 'ssh' && '远程 SSH'}
            </div>
          </div>
        </div>
      </div>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-72 bg-white border-r border-gray-200 overflow-y-auto">
          <div className="p-2 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-700">设备列表（来自数据）</h2>
          </div>
          <div className="p-2 space-y-1">
            {devices.map((device) => {
              const isSelected = selectedDevice === device.device_id;
              return (
                <div
                  key={device.device_id}
                  onClick={() => onSelectDevice(device.device_id)}
                  className={`p-2 rounded cursor-pointer transition-colors ${isSelected ? 'bg-blue-500 text-white' : 'bg-gray-50 hover:bg-gray-100'}`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded flex items-center justify-center ${isSelected ? 'bg-blue-400' : 'bg-white border border-gray-200'}`}>
                      <DeviceIcon type={device.device_type} size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{device.name}</div>
                      <div className={`text-xs ${isSelected ? 'text-blue-100' : 'text-gray-500'}`}>
                        {device.device_id}
                      </div>
                      <div className={`text-xs ${isSelected ? 'text-blue-200' : 'text-gray-400'}`}>
                        {DEVICE_TYPE_TO_CN[device.device_type as DeviceType] ?? device.device_type}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
            {devices.length === 0 && (
              <div className="p-4 text-center text-gray-400 text-sm">请选择数据源并加载数据</div>
            )}
          </div>
        </div>
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
                    <div className="text-sm text-gray-500">ID: {selectedDeviceInfo.device_id}</div>
                    <div className="text-sm text-gray-500">类型: {DEVICE_TYPE_TO_CN[selectedDeviceInfo.device_type as DeviceType] ?? selectedDeviceInfo.device_type}</div>
                  </div>
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
                      const items = getDataItemsForDevice(selectedDeviceInfo.device_type, null, devices as DeviceItemForDataItems[]);
                      const item = items.find((i) => i.key === selectedChartSeries);
                      return item?.unit ?? (selectedChartSeries.includes('q') || selectedChartSeries === 'reactive_power' ? 'MVar' : 'MW');
                    })()}
                    color="#3b82f6"
                    enableDataZoom={true}
                  />
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
