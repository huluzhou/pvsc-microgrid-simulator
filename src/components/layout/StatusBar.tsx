import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

export default function StatusBar() {
  const [status, setStatus] = useState<{
    state: string;
    elapsedTime: number;
  }>({ state: "stopped", elapsedTime: 0 });

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const simStatus = await invoke<{
          state: string;
          elapsed_time: number;
        }>("get_simulation_status");
        setStatus({
          state: simStatus.state,
          elapsedTime: simStatus.elapsed_time,
        });
      } catch (error) {
        // 忽略错误
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const getStatusColor = () => {
    switch (status.state) {
      case "running":
        return "bg-green-500";
      case "paused":
        return "bg-yellow-500";
      default:
        return "bg-gray-400";
    }
  };

  const getStatusText = () => {
    switch (status.state) {
      case "running":
        return "运行中";
      case "paused":
        return "已暂停";
      default:
        return "已停止";
    }
  };

  return (
    <footer className="h-7 bg-gray-100 border-t border-gray-200 flex items-center justify-between px-4 text-xs text-gray-600">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
          <span>{getStatusText()}</span>
        </div>
        {status.state === "running" && (
          <span>运行时间: {formatTime(status.elapsedTime)}</span>
        )}
      </div>
      <div>
        光储充微电网模拟器 v0.1.0
      </div>
    </footer>
  );
}
