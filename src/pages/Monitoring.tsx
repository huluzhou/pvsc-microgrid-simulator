import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import DeviceList from "../components/monitoring/DeviceList";
import DataChart from "../components/monitoring/DataChart";
import { RefreshCw, AlertTriangle } from "lucide-react";

interface DeviceStatus {
  device_id: string;
  name: string;
  is_online: boolean;
  last_update?: number;
  current_voltage?: number;
  current_current?: number;
  current_power?: number;
}

export default function Monitoring() {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [chartData, setChartData] = useState<Array<{ timestamp: number; value: number }>>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadDevices = useCallback(async () => {
    setIsLoading(true);
    try {
      const statuses = await invoke<DeviceStatus[]>("get_all_devices_status");
      setDevices(statuses);
    } catch (error) {
      console.error("Failed to load devices:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadDeviceData = useCallback(async (deviceId: string) => {
    try {
      const data = await invoke<Array<[number, number | null, number | null, number | null]>>(
        "query_device_data",
        {
          deviceId,
          startTime: Date.now() / 1000 - 3600, // 最近1小时
          endTime: Date.now() / 1000,
        }
      );

      // 转换为图表数据格式
      const chartDataPoints = data
        .filter(([_, voltage]) => voltage !== null)
        .map(([timestamp, voltage]) => ({
          timestamp,
          value: voltage || 0,
        }));

      setChartData(chartDataPoints);
    } catch (error) {
      console.error("Failed to load device data:", error);
    }
  }, []);

  useEffect(() => {
    loadDevices();
    const interval = setInterval(loadDevices, 5000); // 每5秒刷新一次
    return () => clearInterval(interval);
  }, [loadDevices]);

  useEffect(() => {
    if (selectedDevice) {
      loadDeviceData(selectedDevice);
      const interval = setInterval(() => loadDeviceData(selectedDevice), 5000);
      return () => clearInterval(interval);
    }
  }, [selectedDevice, loadDeviceData]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">实时监控</h1>
        <button
          onClick={loadDevices}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white flex items-center gap-2 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          刷新
        </button>
      </div>
      <div className="flex-1 flex overflow-hidden">
        <div className="w-1/3 border-r border-gray-700">
          <DeviceList
            devices={devices}
            onDeviceClick={(deviceId) => setSelectedDevice(deviceId)}
          />
        </div>
        <div className="flex-1 p-6">
          {selectedDevice ? (
            <div className="h-full flex flex-col">
              <h2 className="text-xl font-semibold text-white mb-4">
                {devices.find((d) => d.device_id === selectedDevice)?.name || "设备数据"}
              </h2>
              <div className="flex-1 grid grid-cols-1 gap-4">
                <div className="bg-gray-800 rounded-lg p-4 h-64">
                  <DataChart
                    title="电压趋势"
                    data={chartData}
                    unit="V"
                    color="#3b82f6"
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400">
              <div className="text-center">
                <AlertTriangle className="w-16 h-16 mx-auto mb-4 text-gray-600" />
                <p>请选择一个设备查看详细数据</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
