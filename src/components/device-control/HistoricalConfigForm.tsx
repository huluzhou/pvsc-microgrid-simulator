/**
 * 历史数据源配置表单组件 - 浅色主题
 */
import { useState, useEffect, useCallback } from 'react';
import { FileText, Upload, Settings2 } from 'lucide-react';
import { HistoricalConfig, PowerUnit, ColumnSource, LoadCalculation } from '../../types/dataSource';
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

export default function HistoricalConfigForm({ deviceName, deviceType, initialValue, onSave, onCancel }: HistoricalConfigFormProps) {
  const [filePath, setFilePath] = useState(initialValue?.filePath ?? '');
  const [timeColumn, setTimeColumn] = useState(initialValue?.timeColumn ?? 'timestamp');
  const [timeFormat, setTimeFormat] = useState(initialValue?.timeFormat ?? '%Y-%m-%d %H:%M:%S');
  const [powerColumn, setPowerColumn] = useState<ColumnSource | undefined>(initialValue?.powerColumn);
  const [loadCalculation, setLoadCalculation] = useState<LoadCalculation | undefined>(initialValue?.loadCalculation);
  const [playbackSpeed, setPlaybackSpeed] = useState(initialValue?.playbackSpeed ?? 1);
  const [loop, setLoop] = useState(initialValue?.loop ?? true);
  const [showColumnMapping, setShowColumnMapping] = useState(false);
  const [csvColumns] = useState<string[]>([]);

  const isLoadDevice = deviceType === 'load';

  useEffect(() => {
    if (initialValue) {
      setFilePath(initialValue.filePath);
      setTimeColumn(initialValue.timeColumn);
      setTimeFormat(initialValue.timeFormat);
      setPowerColumn(initialValue.powerColumn);
      setLoadCalculation(initialValue.loadCalculation);
      setPlaybackSpeed(initialValue.playbackSpeed);
      setLoop(initialValue.loop);
    }
  }, [initialValue]);

  const handleSelectFile = useCallback(async () => {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      const selected = await invoke<string | null>('select_csv_file');
      if (selected) setFilePath(selected);
    } catch (error) {
      setFilePath('/path/to/data.csv');
    }
  }, []);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    onSave({ filePath, timeColumn, timeFormat, powerColumn: isLoadDevice ? undefined : powerColumn, loadCalculation: isLoadDevice ? loadCalculation : undefined, playbackSpeed, loop });
  }, [filePath, timeColumn, timeFormat, powerColumn, loadCalculation, playbackSpeed, loop, isLoadDevice, onSave]);

  const isConfigValid = filePath && timeColumn && (isLoadDevice ? loadCalculation?.gridMeter?.columnName : powerColumn?.columnName);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">历史数据配置</h3>
        <span className="text-xs text-gray-500">{deviceName}</span>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">CSV 数据文件</label>
          <div className="flex gap-2">
            <input type="text" value={filePath} readOnly placeholder="请选择CSV文件..." className="flex-1 px-2 py-1 bg-gray-50 border border-gray-300 rounded text-sm" />
            <button type="button" onClick={handleSelectFile} className="px-2 py-1 bg-blue-500 hover:bg-blue-600 rounded text-white text-xs flex items-center gap-1 transition-colors">
              <Upload className="w-3 h-3" />选择
            </button>
          </div>
        </div>
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
        {!isLoadDevice && (
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
        {isLoadDevice && (
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
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">回放速度</label>
            <div className="flex items-center gap-2">
              <input type="range" min="0.1" max="10" step="0.1" value={playbackSpeed} onChange={(e) => setPlaybackSpeed(Number(e.target.value))} className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
              <span className="text-gray-700 w-10 text-xs text-right">{playbackSpeed}x</span>
            </div>
          </div>
          <div className="flex items-center">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} className="w-4 h-4 text-blue-500 bg-white border-gray-300 rounded focus:ring-blue-500" />
              <span className="text-xs text-gray-600">循环播放</span>
            </label>
          </div>
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
