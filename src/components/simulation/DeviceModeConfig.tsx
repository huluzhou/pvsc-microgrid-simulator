import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { CheckSquare, Square } from "lucide-react";

interface Device {
  id: string;
  name: string;
  device_type: string;
}

interface DeviceModeConfigProps {
  onModeChange?: () => void;
}

export default function DeviceModeConfig({ onModeChange }: DeviceModeConfigProps) {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevices, setSelectedDevices] = useState<Set<string>>(new Set());
  const [selectedMode, setSelectedMode] = useState<string>("random_data");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    try {
      const deviceList = await invoke<Device[]>("get_all_devices");
      setDevices(deviceList);
    } catch (error) {
      console.error("Failed to load devices:", error);
    }
  };

  const toggleDevice = (deviceId: string) => {
    setSelectedDevices((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(deviceId)) {
        newSet.delete(deviceId);
      } else {
        newSet.add(deviceId);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    setSelectedDevices(new Set(devices.map((d) => d.id)));
  };

  const deselectAll = () => {
    setSelectedDevices(new Set());
  };

  const handleBatchSetMode = async () => {
    if (selectedDevices.size === 0) {
      alert("请至少选择一个设备");
      return;
    }

    setIsLoading(true);
    try {
      await invoke("batch_set_device_mode", {
        deviceIds: Array.from(selectedDevices),
        mode: selectedMode,
      });
      alert("批量设置成功！");
      setSelectedDevices(new Set());
      onModeChange?.();
    } catch (error) {
      console.error("Failed to set device mode:", error);
      alert("设置失败：" + error);
    } finally {
      setIsLoading(false);
    }
  };

  const modeLabels: Record<string, string> = {
    random_data: "随机数据模式",
    manual: "手动模式",
    remote: "远程模式",
    historical_data: "历史数据模式",
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-lg font-semibold text-white mb-4">设备工作模式批量配置</h2>
      
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">
          选择工作模式
        </label>
        <select
          value={selectedMode}
          onChange={(e) => setSelectedMode(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded px-4 py-2 text-white w-full"
        >
          {Object.entries(modeLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="mb-4 flex gap-2">
        <button
          onClick={selectAll}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-white text-sm transition-colors"
        >
          全选
        </button>
        <button
          onClick={deselectAll}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-white text-sm transition-colors"
        >
          取消全选
        </button>
      </div>

      <div className="max-h-64 overflow-y-auto mb-4 border border-gray-700 rounded p-2">
        {devices.map((device) => (
          <div
            key={device.id}
            className="flex items-center gap-2 p-2 hover:bg-gray-700 rounded cursor-pointer"
            onClick={() => toggleDevice(device.id)}
          >
            {selectedDevices.has(device.id) ? (
              <CheckSquare className="w-5 h-5 text-blue-500" />
            ) : (
              <Square className="w-5 h-5 text-gray-500" />
            )}
            <div className="flex-1">
              <div className="text-sm text-white">{device.name}</div>
              <div className="text-xs text-gray-400">{device.device_type}</div>
            </div>
          </div>
        ))}
        {devices.length === 0 && (
          <div className="text-center text-gray-400 py-4">暂无设备</div>
        )}
      </div>

      <button
        onClick={handleBatchSetMode}
        disabled={isLoading || selectedDevices.size === 0}
        className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? "设置中..." : `批量设置为 ${modeLabels[selectedMode]}`}
      </button>
    </div>
  );
}
