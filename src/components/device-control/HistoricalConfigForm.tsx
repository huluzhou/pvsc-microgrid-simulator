/**
 * 历史数据源配置表单组件 - 支持 CSV 和 SQLite，含时间范围选择
 */
import { useState, useEffect, useCallback } from 'react';
import { FileText, Upload, Settings2, Database } from 'lucide-react';
import { HistoricalConfig, HistoricalSourceType, PowerUnit, ColumnSource, LoadCalculation } from '../../types/dataSource';
import ColumnMappingDialog from './ColumnMappingDialog';

interface HistoricalConfigFormProps {
  deviceName: string;
  deviceType: string;
  initialValue?: HistoricalConfig;
  onSave: (config: HistoricalConfig) => void;
  onCancel: () => void;
}

const TIME_FORMAT_OPTIONS = [
  { value: '%Y-%m-%d %H:%M:%S', label: '2024-01-01 12:00:00' },
  { value: '%Y/%m/%d %H:%M:%S', label: '2024/01/01 12:00:00' },
  { value: '%Y-%m-%d %H:%M', label: '2024-01-01 12:00' },
];

function formatTimestamp(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export default function HistoricalConfigForm({ deviceName, deviceType, initialValue, onSave, onCancel }: HistoricalConfigFormProps) {
  const [sourceType, setSourceType] = useState<HistoricalSourceType>(initialValue?.sourceType ?? 'csv');
  const [filePath, setFilePath] = useState(initialValue?.filePath ?? '');
  const [timeColumn, setTimeColumn] = useState(initialValue?.timeColumn ?? 'timestamp');
  const [timeFormat, setTimeFormat] = useState(initialValue?.timeFormat ?? '%Y-%m-%d %H:%M:%S');
  const [powerColumn, setPowerColumn] = useState<ColumnSource | undefined>(initialValue?.powerColumn);
  const [loadCalculation, setLoadCalculation] = useState<LoadCalculation | undefined>(initialValue?.loadCalculation);
  const [sourceDeviceId, setSourceDeviceId] = useState(initialValue?.sourceDeviceId ?? '');
  const [startTime, setStartTime] = useState<number | undefined>(initialValue?.startTime);
  const [endTime, setEndTime] = useState<number | undefined>(initialValue?.endTime);
  const [playbackSpeed, setPlaybackSpeed] = useState(initialValue?.playbackSpeed ?? 1);
  const [loop, setLoop] = useState(initialValue?.loop ?? true);
  const [showColumnMapping, setShowColumnMapping] = useState(false);
  const [csvColumns] = useState<string[]>([]);

  // SQLite 相关
  const [sqliteDevices, setSqliteDevices] = useState<string[]>([]);
  const [timeRange, setTimeRange] = useState<[number, number] | null>(null);
  const [loadingDevices, setLoadingDevices] = useState(false);

  const isLoadDevice = deviceType === 'load';
  const isSqlite = sourceType === 'sqlite';

  useEffect(() => {
    if (initialValue) {
      setSourceType(initialValue.sourceType ?? 'csv');
      setFilePath(initialValue.filePath);
      setTimeColumn(initialValue.timeColumn);
      setTimeFormat(initialValue.timeFormat);
      setPowerColumn(initialValue.powerColumn);
      setLoadCalculation(initialValue.loadCalculation);
      setSourceDeviceId(initialValue.sourceDeviceId ?? '');
      setStartTime(initialValue.startTime);
      setEndTime(initialValue.endTime);
      setPlaybackSpeed(initialValue.playbackSpeed);
      setLoop(initialValue.loop);
    }
  }, [initialValue]);

  // SQLite 文件选择后加载设备列表
  const loadSqliteDevices = useCallback(async (path: string) => {
    if (!path) return;
    setLoadingDevices(true);
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const devices = await invoke<string[]>('list_sqlite_devices', { filePath: path });
      setSqliteDevices(devices);
      if (devices.length > 0 && !sourceDeviceId) {
        setSourceDeviceId(devices[0]);
      }
    } catch {
      setSqliteDevices([]);
    }
    setLoadingDevices(false);
  }, [sourceDeviceId]);

  // 加载时间范围
  const loadTimeRange = useCallback(async (path: string, sType: HistoricalSourceType, deviceId?: string) => {
    if (!path || sType !== 'sqlite') {
      setTimeRange(null);
      return;
    }
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const range = await invoke<[number, number]>('get_historical_time_range', {
        filePath: path,
        sourceType: sType,
        sourceDeviceId: deviceId || null,
      });
      setTimeRange(range);
      // 如果用户未手动设置时间范围，自动填充
      if (startTime === undefined) setStartTime(range[0]);
      if (endTime === undefined) setEndTime(range[1]);
    } catch {
      setTimeRange(null);
    }
  }, [startTime, endTime]);

  // 文件路径变化时加载元信息
  useEffect(() => {
    if (isSqlite && filePath) {
      loadSqliteDevices(filePath);
    }
  }, [filePath, isSqlite, loadSqliteDevices]);

  useEffect(() => {
    if (isSqlite && filePath && sourceDeviceId) {
      loadTimeRange(filePath, 'sqlite', sourceDeviceId);
    }
  }, [filePath, isSqlite, sourceDeviceId, loadTimeRange]);

  const handleSelectFile = useCallback(async () => {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      if (isSqlite) {
        // 使用 Tauri dialog 选择 SQLite 文件
        const { open } = await import('@tauri-apps/plugin-dialog');
        const selected = await open({
          multiple: false,
          filters: [{ name: 'SQLite', extensions: ['db', 'sqlite', 'sqlite3'] }],
        });
        if (selected) setFilePath(selected as string);
      } else {
        const selected = await invoke<string | null>('select_csv_file');
        if (selected) setFilePath(selected);
      }
    } catch {
      setFilePath(isSqlite ? '/path/to/data.db' : '/path/to/data.csv');
    }
  }, [isSqlite]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      sourceType,
      filePath,
      timeColumn,
      timeFormat,
      powerColumn: (!isSqlite && !isLoadDevice) ? powerColumn : undefined,
      loadCalculation: (!isSqlite && isLoadDevice) ? loadCalculation : undefined,
      sourceDeviceId: isSqlite ? sourceDeviceId : undefined,
      startTime,
      endTime,
      playbackSpeed,
      loop,
    });
  }, [sourceType, filePath, timeColumn, timeFormat, powerColumn, loadCalculation, sourceDeviceId, startTime, endTime, playbackSpeed, loop, isSqlite, isLoadDevice, onSave]);

  const isConfigValid = filePath && (isSqlite ? sourceDeviceId : (timeColumn && (isLoadDevice ? loadCalculation?.gridMeter?.columnName : powerColumn?.columnName)));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">历史数据配置</h3>
        <span className="text-xs text-gray-500">{deviceName}</span>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* 数据源类型切换 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">数据源类型</label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setSourceType('csv')}
              className={`flex-1 px-2 py-1.5 rounded text-xs flex items-center justify-center gap-1 transition-colors border ${sourceType === 'csv' ? 'bg-blue-50 border-blue-400 text-blue-700' : 'bg-gray-50 border-gray-300 text-gray-600 hover:bg-gray-100'}`}
            >
              <FileText className="w-3 h-3" />CSV 文件
            </button>
            <button
              type="button"
              onClick={() => setSourceType('sqlite')}
              className={`flex-1 px-2 py-1.5 rounded text-xs flex items-center justify-center gap-1 transition-colors border ${sourceType === 'sqlite' ? 'bg-blue-50 border-blue-400 text-blue-700' : 'bg-gray-50 border-gray-300 text-gray-600 hover:bg-gray-100'}`}
            >
              <Database className="w-3 h-3" />SQLite 数据库
            </button>
          </div>
        </div>

        {/* 文件选择 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">{isSqlite ? 'SQLite 数据库文件' : 'CSV 数据文件'}</label>
          <div className="flex gap-2">
            <input type="text" value={filePath} readOnly placeholder={isSqlite ? '请选择 .db/.sqlite 文件...' : '请选择CSV文件...'} className="flex-1 px-2 py-1 bg-gray-50 border border-gray-300 rounded text-sm" />
            <button type="button" onClick={handleSelectFile} className="px-2 py-1 bg-blue-500 hover:bg-blue-600 rounded text-white text-xs flex items-center gap-1 transition-colors">
              <Upload className="w-3 h-3" />选择
            </button>
          </div>
        </div>

        {/* SQLite: 设备选择 */}
        {isSqlite && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">源设备</label>
            {loadingDevices ? (
              <div className="text-xs text-gray-400">加载设备列表中...</div>
            ) : sqliteDevices.length > 0 ? (
              <select value={sourceDeviceId} onChange={(e) => setSourceDeviceId(e.target.value)} className="w-full px-2 py-1 bg-white border border-gray-300 rounded text-sm">
                {sqliteDevices.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            ) : (
              <div className="text-xs text-gray-400">{filePath ? '未找到设备数据' : '请先选择文件'}</div>
            )}
          </div>
        )}

        {/* CSV: 时间列和格式 */}
        {!isSqlite && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">时间列名</label>
              <input type="text" value={timeColumn} onChange={(e) => setTimeColumn(e.target.value)} className="w-full px-2 py-1 bg-white border border-gray-300 rounded text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">时间格式</label>
              <select value={timeFormat} onChange={(e) => setTimeFormat(e.target.value)} className="w-full px-2 py-1 bg-white border border-gray-300 rounded text-sm">
                {TIME_FORMAT_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
          </div>
        )}

        {/* CSV: 功率列（非负载） */}
        {!isSqlite && !isLoadDevice && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">功率数据列</label>
            <div className="flex gap-2">
              <input type="text" value={powerColumn?.columnName ?? ''} onChange={(e) => setPowerColumn({ columnName: e.target.value, unit: powerColumn?.unit ?? 'kW' })} placeholder="输入列名" className="flex-1 px-2 py-1 bg-white border border-gray-300 rounded text-sm" />
              <select value={powerColumn?.unit ?? 'kW'} onChange={(e) => setPowerColumn({ columnName: powerColumn?.columnName ?? '', unit: e.target.value as PowerUnit })} className="w-16 px-2 py-1 bg-white border border-gray-300 rounded text-sm">
                <option value="W">W</option>
                <option value="kW">kW</option>
                <option value="MW">MW</option>
              </select>
            </div>
          </div>
        )}

        {/* CSV: 负载计算配置 */}
        {!isSqlite && isLoadDevice && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-gray-600">负载计算配置</label>
              <button type="button" onClick={() => setShowColumnMapping(true)} className="px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-xs text-gray-700 flex items-center gap-1 transition-colors">
                <Settings2 className="w-3 h-3" />配置
              </button>
            </div>
            {loadCalculation?.gridMeter && (
              <div className="p-2 bg-gray-50 rounded border border-gray-200 text-xs">
                <div className="text-gray-600 mb-1">已配置:</div>
                <div className="space-y-0.5">
                  <div>关口: {loadCalculation.gridMeter.columnName} ({loadCalculation.gridMeter.unit})</div>
                  {loadCalculation.pvGeneration && <div>光伏: {loadCalculation.pvGeneration.columnName} ({loadCalculation.pvGeneration.unit})</div>}
                  {loadCalculation.storagePower && <div>储能: {loadCalculation.storagePower.columnName} ({loadCalculation.storagePower.unit})</div>}
                  {loadCalculation.chargerPower && <div>充电桩: {loadCalculation.chargerPower.columnName} ({loadCalculation.chargerPower.unit})</div>}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 时间范围（SQLite 支持） */}
        {isSqlite && timeRange && (
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              数据时间范围
              <span className="ml-2 font-normal text-gray-400">
                {formatTimestamp(timeRange[0])} ~ {formatTimestamp(timeRange[1])}
              </span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-gray-500 mb-0.5">起始</label>
                <input
                  type="datetime-local"
                  value={startTime ? new Date(startTime * 1000).toISOString().slice(0, 16) : ''}
                  onChange={(e) => setStartTime(e.target.value ? new Date(e.target.value).getTime() / 1000 : undefined)}
                  className="w-full px-2 py-1 bg-white border border-gray-300 rounded text-xs"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-0.5">结束</label>
                <input
                  type="datetime-local"
                  value={endTime ? new Date(endTime * 1000).toISOString().slice(0, 16) : ''}
                  onChange={(e) => setEndTime(e.target.value ? new Date(e.target.value).getTime() / 1000 : undefined)}
                  className="w-full px-2 py-1 bg-white border border-gray-300 rounded text-xs"
                />
              </div>
            </div>
          </div>
        )}

        {/* 回放速度与循环播放 - 修复布局：使回放速度占满宽度，循环播放独立一行 */}
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">回放速度</label>
          <div className="flex items-center gap-2">
            <input type="range" min="0.1" max="10" step="0.1" value={playbackSpeed} onChange={(e) => setPlaybackSpeed(Number(e.target.value))} className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
            <span className="text-gray-700 w-10 text-xs text-right shrink-0">{playbackSpeed}x</span>
          </div>
        </div>
        <div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} className="w-4 h-4 text-blue-500 bg-white border-gray-300 rounded focus:ring-blue-500" />
            <span className="text-xs text-gray-600">循环播放</span>
          </label>
        </div>

        {filePath && (
          <div className="p-2 bg-gray-50 rounded border border-gray-200">
            <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
              <FileText className="w-3 h-3" />已选择文件
            </div>
            <div className="text-xs text-gray-700 break-all">{filePath}</div>
          </div>
        )}
        <div className="flex gap-2">
          <button type="submit" disabled={!isConfigValid} className="flex-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-white text-sm transition-colors disabled:opacity-50">应用配置</button>
          <button type="button" onClick={onCancel} className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 text-sm transition-colors">取消</button>
        </div>
      </form>
      {showColumnMapping && (
        <ColumnMappingDialog columns={csvColumns} initialValue={loadCalculation} onSave={(calc) => { setLoadCalculation(calc); setShowColumnMapping(false); }} onClose={() => setShowColumnMapping(false)} />
      )}
    </div>
  );
}
