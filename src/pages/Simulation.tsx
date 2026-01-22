/**
 * 仿真运行页面 - 浅色主题
 */
import { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Play, Pause, Square, RefreshCw, Settings, Radio, Clock, Activity, Zap, AlertTriangle } from 'lucide-react';

interface SimulationStatus {
  state: 'Stopped' | 'Running' | 'Paused';
  start_time?: number;
  elapsed_time: number;
  calculation_count: number;
  average_delay: number;
}

interface SimulationConfig {
  calculationInterval: number;
  remoteControlEnabled: boolean;
  autoStartModbus: boolean;
}

export default function Simulation() {
  const [status, setStatus] = useState<SimulationStatus>({ state: 'Stopped', elapsed_time: 0, calculation_count: 0, average_delay: 0 });
  const [config, setConfig] = useState<SimulationConfig>({ calculationInterval: 1000, remoteControlEnabled: false, autoStartModbus: false });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      const currentStatus = await invoke<SimulationStatus>('get_simulation_status');
      setStatus(currentStatus);
      setError(null);
    } catch (err) {
      setError('无法获取仿真状态');
    }
  }, []);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 1000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  const handleStart = async () => {
    setIsLoading(true);
    try {
      await invoke('start_simulation', { config: { calculation_interval_ms: config.calculationInterval, remote_control_enabled: config.remoteControlEnabled } });
      await loadStatus();
    } catch (err) {
      alert('启动失败：' + err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    try { await invoke('stop_simulation'); await loadStatus(); } catch (err) { alert('停止失败：' + err); } finally { setIsLoading(false); }
  };

  const handlePause = async () => {
    setIsLoading(true);
    try { await invoke('pause_simulation'); await loadStatus(); } catch (err) { alert('暂停失败：' + err); } finally { setIsLoading(false); }
  };

  const handleResume = async () => {
    setIsLoading(true);
    try { await invoke('resume_simulation'); await loadStatus(); } catch (err) { alert('恢复失败：' + err); } finally { setIsLoading(false); }
  };

  const toggleRemoteControl = async (enabled: boolean) => {
    try {
      await invoke('set_remote_control_enabled', { enabled });
      setConfig((prev) => ({ ...prev, remoteControlEnabled: enabled }));
    } catch (err) {
      alert('切换远程控制失败：' + err);
    }
  };

  const getStatusColor = () => {
    switch (status.state) {
      case 'Running': return 'text-green-600';
      case 'Paused': return 'text-yellow-600';
      default: return 'text-gray-400';
    }
  };

  const getStatusText = () => {
    switch (status.state) {
      case 'Running': return '运行中';
      case 'Paused': return '已暂停';
      default: return '已停止';
    }
  };

  const formatElapsedTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    if (hrs > 0) return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="px-4 py-2 bg-white border-b border-gray-200 flex items-center gap-4">
        <h1 className="text-base font-semibold text-gray-800">仿真运行</h1>
        <div className="flex-1" />
        <span className={`text-xs font-medium ${getStatusColor()}`}>{getStatusText()}</span>
        <button onClick={loadStatus} className="p-1.5 rounded hover:bg-gray-100 transition-colors"><RefreshCw className="w-4 h-4 text-gray-500" /></button>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded flex items-center gap-2 text-sm">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span className="text-red-700">{error}</span>
            </div>
          )}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">仿真控制</h2>
            <div className="flex flex-wrap gap-2">
              <button onClick={handleStart} disabled={isLoading || status.state === 'Running'} className="px-4 py-2 bg-green-500 hover:bg-green-600 rounded text-white text-sm flex items-center gap-1.5 transition-colors disabled:opacity-50">
                <Play className="w-4 h-4" />启动仿真
              </button>
              <button onClick={handleStop} disabled={isLoading || status.state === 'Stopped'} className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded text-white text-sm flex items-center gap-1.5 transition-colors disabled:opacity-50">
                <Square className="w-4 h-4" />停止仿真
              </button>
              <button onClick={handlePause} disabled={isLoading || status.state !== 'Running'} className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 rounded text-white text-sm flex items-center gap-1.5 transition-colors disabled:opacity-50">
                <Pause className="w-4 h-4" />暂停
              </button>
              <button onClick={handleResume} disabled={isLoading || status.state !== 'Paused'} className="px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded text-white text-sm flex items-center gap-1.5 transition-colors disabled:opacity-50">
                <Play className="w-4 h-4" />恢复
              </button>
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">运行状态</h2>
            <div className="grid grid-cols-4 gap-3">
              <div className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="flex items-center gap-1 text-gray-500 mb-1"><Clock className="w-3 h-3" /><span className="text-xs">运行时间</span></div>
                <div className="text-xl font-bold text-gray-800">{formatElapsedTime(status.elapsed_time)}</div>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="flex items-center gap-1 text-gray-500 mb-1"><Activity className="w-3 h-3" /><span className="text-xs">计算次数</span></div>
                <div className="text-xl font-bold text-gray-800">{status.calculation_count.toLocaleString()}</div>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="flex items-center gap-1 text-gray-500 mb-1"><Zap className="w-3 h-3" /><span className="text-xs">平均延迟</span></div>
                <div className="text-xl font-bold text-gray-800">{status.average_delay.toFixed(1)} <span className="text-xs text-gray-500">ms</span></div>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="flex items-center gap-1 text-gray-500 mb-1"><Clock className="w-3 h-3" /><span className="text-xs">开始时间</span></div>
                <div className="text-sm font-bold text-gray-800">{status.start_time ? new Date(status.start_time * 1000).toLocaleTimeString() : '-'}</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-3"><Settings className="w-4 h-4 text-gray-500" /><h2 className="text-sm font-semibold text-gray-700">仿真配置</h2></div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">计算间隔</label>
                <div className="flex items-center gap-3">
                  <input type="range" min="100" max="5000" step="100" value={config.calculationInterval} onChange={(e) => setConfig((prev) => ({ ...prev, calculationInterval: Number(e.target.value) }))} disabled={status.state === 'Running'} className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:opacity-50" />
                  <span className="text-gray-700 w-16 text-xs text-right">{config.calculationInterval} ms</span>
                </div>
              </div>
              <div className="p-3 bg-gray-50 rounded border border-gray-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Radio className="w-4 h-4 text-blue-500" />
                    <div>
                      <div className="text-xs font-medium text-gray-700">允许远程控制</div>
                      <div className="text-xs text-gray-500">外部系统可通过Modbus控制设备</div>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" checked={config.remoteControlEnabled} onChange={(e) => toggleRemoteControl(e.target.checked)} className="sr-only peer" />
                    <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-400 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
