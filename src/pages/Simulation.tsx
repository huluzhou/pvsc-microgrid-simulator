/**
 * 仿真运行页面 - 浅色主题
 */
import { useState, useEffect, useCallback } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { useDeviceControlStore } from '../stores/deviceControl';
import { Play, Pause, Square, RefreshCw, Settings, Radio, Clock, Activity, Zap, AlertTriangle, ChevronDown, ChevronRight, Info, AlertCircle } from 'lucide-react';

interface SimulationStatus {
  state: 'Stopped' | 'Running' | 'Paused';
  start_time?: number;
  elapsed_time: number;
  calculation_count: number;
  average_delay: number;
  errors?: SimulationError[];
}

interface SimulationError {
  error_type: string;  // "adapter" | "topology" | "calculation" | "runtime"
  severity: string;    // "error" | "warning" | "info"
  message: string;
  device_id?: string;
  details: any;
  timestamp: number;
}

interface SimulationConfig {
  calculationInterval: number;
  remoteControlEnabled: boolean;
  autoStartModbus: boolean;
}

export default function Simulation() {
  const [status, setStatus] = useState<SimulationStatus>({ state: 'Stopped', elapsed_time: 0, calculation_count: 0, average_delay: 0, errors: [] });
  const [config, setConfig] = useState<SimulationConfig>({ calculationInterval: 1000, remoteControlEnabled: true, autoStartModbus: false });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedErrors, setExpandedErrors] = useState<Set<number>>(new Set());
  const [errorFilter, setErrorFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all');

  const { deviceConfigs } = useDeviceControlStore();

  const loadStatus = useCallback(async () => {
    try {
      const currentStatus = await invoke<SimulationStatus>('get_simulation_status');
      setStatus(currentStatus);
      setError(null);
      
      // 同时加载错误信息（如果状态中没有）
      if (!currentStatus.errors || currentStatus.errors.length === 0) {
        try {
          const errors = await invoke<SimulationError[]>('get_simulation_errors');
          setStatus(prev => ({ ...prev, errors }));
        } catch (err) {
          // 忽略错误信息加载失败
        }
      }
    } catch (err) {
      setError('无法获取仿真状态');
    }
  }, []);

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 1000);

    // 监听错误更新事件
    const errorListener = listen('simulation-errors-update', (event: any) => {
      if (event.payload && event.payload.errors) {
        setStatus(prev => ({ ...prev, errors: event.payload.errors }));
      }
    });

    // 出现错误时后端会自动停止仿真（等价于按下停止按钮），立即刷新状态
    const autoStoppedListener = listen('simulation-auto-stopped', () => {
      loadStatus();
    });

    return () => {
      clearInterval(interval);
      errorListener.then(unlisten => unlisten());
      autoStoppedListener.then(unlisten => unlisten());
    };
  }, [loadStatus]);

  const handleStart = async () => {
    setIsLoading(true);
    try {
      // 先启动仿真（设置拓扑并启动 Python），再同步手动设定，这样 Python 已有拓扑后再应用功率
      await invoke('start_simulation', { config: { calculation_interval_ms: config.calculationInterval, remote_control_enabled: config.remoteControlEnabled } });
      // 运行仿真时自动启动所有 Modbus 服务器（拓扑中配置了 ip/port 的设备）
      try {
        await invoke('start_all_modbus_servers');
      } catch (e) {
        console.warn('自动启动 Modbus 服务器失败:', e);
      }
      // 启动后将设备控制中的设定同步到仿真，确保下一拍计算生效
      for (const [deviceId, cfg] of Object.entries(deviceConfigs)) {
        if (cfg?.dataSourceType === 'manual' && cfg.manualSetpoint) {
          try {
            await invoke('set_device_mode', { deviceId, mode: 'manual' });
            await invoke('set_device_manual_setpoint', {
              deviceId,
              activePower: cfg.manualSetpoint.activePower,
              reactivePower: cfg.manualSetpoint.reactivePower ?? 0,
            });
          } catch (e) {
            console.warn('同步设备手动设定失败:', deviceId, e);
          }
        } else if (cfg?.dataSourceType === 'random' && cfg.randomConfig) {
          const { minPower, maxPower } = cfg.randomConfig;
          try {
            await invoke('set_device_mode', { deviceId, mode: 'random_data' });
            await invoke('set_device_random_config', {
              deviceId,
              minPower,
              maxPower,
            });
          } catch (e) {
            console.warn('同步设备随机设定失败:', deviceId, e);
          }
        } else if (cfg?.dataSourceType === 'historical' && cfg.historicalConfig) {
          try {
            await invoke('set_device_mode', { deviceId, mode: 'historical_data' });
            await invoke('set_device_historical_config', {
              deviceId,
              config: cfg.historicalConfig,
            });
          } catch (e) {
            console.warn('同步设备历史配置失败:', deviceId, e);
          }
        }
      }
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

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error': return 'text-red-600 bg-red-50 border-red-200';
      case 'warning': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'info': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getErrorTypeLabel = (errorType: string) => {
    switch (errorType) {
      case 'adapter': return '适配器';
      case 'topology': return '拓扑';
      case 'calculation': return '计算';
      case 'runtime': return '运行时';
      default: return errorType;
    }
  };

  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case 'error': return '错误';
      case 'warning': return '警告';
      case 'info': return '信息';
      default: return severity;
    }
  };

  const toggleErrorExpanded = (index: number) => {
    setExpandedErrors(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const filteredErrors = status.errors?.filter(err => 
    errorFilter === 'all' || err.severity === errorFilter
  ) || [];

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
              <button onClick={handleStop} disabled={isLoading} className="px-4 py-2 bg-red-500 hover:bg-red-600 rounded text-white text-sm flex items-center gap-1.5 transition-colors disabled:opacity-50">
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
              <div className="p-3 bg-gray-50 rounded border border-gray-200" title="完成一次仿真计算（请求 Python 潮流计算并回传、写库、发事件）的平均耗时。若大于计算间隔，说明步长跟不上设定周期。">
                <div className="flex items-center gap-1 text-gray-500 mb-1"><Zap className="w-3 h-3" /><span className="text-xs">每步平均耗时</span></div>
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
                      <div className="text-xs font-medium text-gray-700">允许远程控制（全局总闸）</div>
                      <div className="text-xs text-gray-500">关则全部设备不接受远程控制；开时各设备是否允许在 Modbus 页按设备设置</div>
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
          {status.errors && status.errors.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  <h2 className="text-sm font-semibold text-gray-700">错误信息</h2>
                  <span className="text-xs text-gray-500">({status.errors.length})</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setErrorFilter('all')}
                    className={`px-2 py-1 text-xs rounded ${errorFilter === 'all' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600'}`}
                  >
                    全部
                  </button>
                  <button
                    onClick={() => setErrorFilter('error')}
                    className={`px-2 py-1 text-xs rounded ${errorFilter === 'error' ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-600'}`}
                  >
                    错误
                  </button>
                  <button
                    onClick={() => setErrorFilter('warning')}
                    className={`px-2 py-1 text-xs rounded ${errorFilter === 'warning' ? 'bg-yellow-500 text-white' : 'bg-gray-100 text-gray-600'}`}
                  >
                    警告
                  </button>
                  <button
                    onClick={() => setErrorFilter('info')}
                    className={`px-2 py-1 text-xs rounded ${errorFilter === 'info' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600'}`}
                  >
                    信息
                  </button>
                </div>
              </div>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredErrors.length === 0 ? (
                  <div className="text-sm text-gray-500 text-center py-4">暂无{errorFilter !== 'all' ? getSeverityLabel(errorFilter) : ''}信息</div>
                ) : (
                  filteredErrors.map((err, index) => {
                    const isExpanded = expandedErrors.has(index);
                    const severityColor = getSeverityColor(err.severity);
                    return (
                      <div key={index} className={`border rounded p-3 ${severityColor}`}>
                        <div 
                          className="flex items-start gap-2 cursor-pointer"
                          onClick={() => toggleErrorExpanded(index)}
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 mt-0.5 flex-shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 mt-0.5 flex-shrink-0" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-medium px-2 py-0.5 rounded bg-white/50">
                                {getErrorTypeLabel(err.error_type)}
                              </span>
                              <span className="text-xs font-medium px-2 py-0.5 rounded bg-white/50">
                                {getSeverityLabel(err.severity)}
                              </span>
                              {err.device_id && (
                                <span className="text-xs text-gray-600">设备: {err.device_id}</span>
                              )}
                              <span className="text-xs text-gray-500 ml-auto">
                                {err.timestamp > 10000000000 
                                  ? new Date(err.timestamp).toLocaleTimeString() 
                                  : new Date(err.timestamp * 1000).toLocaleTimeString()}
                              </span>
                            </div>
                            <div className="text-sm font-medium">{err.message}</div>
                            {isExpanded && (
                              <div className="mt-2 pt-2 border-t border-current/20">
                                <div className="text-xs font-medium mb-1">详细信息:</div>
                                <pre className="text-xs bg-white/50 p-2 rounded overflow-auto max-h-40">
                                  {JSON.stringify(err.details, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
