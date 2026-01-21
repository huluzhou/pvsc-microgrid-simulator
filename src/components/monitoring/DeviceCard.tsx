import { Zap, Battery, Sun, Plug, Gauge, Network } from "lucide-react";

interface DeviceCardProps {
  deviceId: string;
  name: string;
  deviceType: string;
  isOnline: boolean;
  voltage?: number;
  current?: number;
  power?: number;
  lastUpdate?: number;
}

const deviceIcons: Record<string, any> = {
  Node: Network,
  Pv: Sun,
  Storage: Battery,
  Load: Zap,
  Charger: Plug,
  Meter: Gauge,
};

export default function DeviceCard({
  deviceId,
  name,
  deviceType,
  isOnline,
  voltage,
  current,
  power,
  lastUpdate,
}: DeviceCardProps) {
  const Icon = deviceIcons[deviceType] || Network;
  const updateTime = lastUpdate
    ? new Date(lastUpdate * 1000).toLocaleTimeString()
    : "未知";

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-blue-500 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 text-blue-400" />
          <div>
            <div className="font-semibold text-white">{name}</div>
            <div className="text-xs text-gray-400">{deviceType}</div>
          </div>
        </div>
        <div
          className={`w-3 h-3 rounded-full ${
            isOnline ? "bg-green-500" : "bg-red-500"
          }`}
        />
      </div>
      <div className="space-y-2 text-sm">
        {voltage !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-400">电压:</span>
            <span className="text-white">{voltage.toFixed(2)} V</span>
          </div>
        )}
        {current !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-400">电流:</span>
            <span className="text-white">{current.toFixed(2)} A</span>
          </div>
        )}
        {power !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-400">功率:</span>
            <span className="text-white font-semibold">
              {power.toFixed(2)} W
            </span>
          </div>
        )}
        <div className="flex justify-between text-xs text-gray-500 pt-2 border-t border-gray-700">
          <span>最后更新:</span>
          <span>{updateTime}</span>
        </div>
      </div>
    </div>
  );
}
