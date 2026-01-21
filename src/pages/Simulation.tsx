import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Play, Pause, Square, RefreshCw } from "lucide-react";
import DeviceModeConfig from "../components/simulation/DeviceModeConfig";

interface SimulationStatus {
  state: "Stopped" | "Running" | "Paused";
  start_time?: number;
  elapsed_time: number;
  calculation_count: number;
  average_delay: number;
}

export default function Simulation() {
  const [status, setStatus] = useState<SimulationStatus>({
    state: "Stopped",
    elapsed_time: 0,
    calculation_count: 0,
    average_delay: 0,
  });
  const [isLoading, setIsLoading] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      const currentStatus = await invoke<SimulationStatus>("get_simulation_status");
      setStatus(currentStatus);
    } catch (error) {
      console.error("Failed to load simulation status:", error);
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
      await invoke("start_simulation");
      await loadStatus();
    } catch (error) {
      console.error("Failed to start simulation:", error);
      alert("启动失败：" + error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    setIsLoading(true);
    try {
      await invoke("stop_simulation");
      await loadStatus();
    } catch (error) {
      console.error("Failed to stop simulation:", error);
      alert("停止失败：" + error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePause = async () => {
    setIsLoading(true);
    try {
      await invoke("pause_simulation");
      await loadStatus();
    } catch (error) {
      console.error("Failed to pause simulation:", error);
      alert("暂停失败：" + error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResume = async () => {
    setIsLoading(true);
    try {
      await invoke("resume_simulation");
      await loadStatus();
    } catch (error) {
      console.error("Failed to resume simulation:", error);
      alert("恢复失败：" + error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = () => {
    switch (status.state) {
      case "Running":
        return "text-green-500";
      case "Paused":
        return "text-yellow-500";
      default:
        return "text-gray-500";
    }
  };

  const getStatusText = () => {
    switch (status.state) {
      case "Running":
        return "运行中";
      case "Paused":
        return "已暂停";
      default:
        return "已停止";
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-white">仿真控制</h1>

      {/* 控制面板 */}
      <div className="bg-gray-800 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">控制面板</h2>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${getStatusColor()}`}>
              {getStatusText()}
            </span>
            <button
              onClick={loadStatus}
              className="p-2 rounded hover:bg-gray-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>
        <div className="flex gap-4">
          <button
            onClick={handleStart}
            disabled={isLoading || status.state === "Running"}
            className="px-6 py-3 bg-green-600 hover:bg-green-700 rounded text-white flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-5 h-5" />
            启动
          </button>
          <button
            onClick={handleStop}
            disabled={isLoading || status.state === "Stopped"}
            className="px-6 py-3 bg-red-600 hover:bg-red-700 rounded text-white flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Square className="w-5 h-5" />
            停止
          </button>
          <button
            onClick={handlePause}
            disabled={isLoading || status.state !== "Running"}
            className="px-6 py-3 bg-yellow-600 hover:bg-yellow-700 rounded text-white flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Pause className="w-5 h-5" />
            暂停
          </button>
          <button
            onClick={handleResume}
            disabled={isLoading || status.state !== "Paused"}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded text-white flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-5 h-5" />
            恢复
          </button>
        </div>
      </div>

      {/* 状态信息 */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-white mb-4">状态信息</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <div className="text-sm text-gray-400 mb-1">运行时间</div>
            <div className="text-xl font-semibold text-white">
              {Math.floor(status.elapsed_time / 60)}:{(status.elapsed_time % 60).toString().padStart(2, "0")}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400 mb-1">计算次数</div>
            <div className="text-xl font-semibold text-white">
              {status.calculation_count.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400 mb-1">平均延迟</div>
            <div className="text-xl font-semibold text-white">
              {status.average_delay.toFixed(2)} ms
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-400 mb-1">开始时间</div>
            <div className="text-xl font-semibold text-white">
              {status.start_time
                ? new Date(status.start_time * 1000).toLocaleTimeString()
                : "-"}
            </div>
          </div>
        </div>
      </div>

      {/* 设备模式配置 */}
      <div className="mt-6">
        <DeviceModeConfig />
      </div>
    </div>
  );
}
