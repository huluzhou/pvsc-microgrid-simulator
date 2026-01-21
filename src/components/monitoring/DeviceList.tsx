import { useState } from "react";
import DeviceCard from "./DeviceCard";
import { Search } from "lucide-react";

interface DeviceStatus {
  device_id: string;
  name: string;
  is_online: boolean;
  last_update?: number;
  current_voltage?: number;
  current_current?: number;
  current_power?: number;
}

interface DeviceListProps {
  devices: DeviceStatus[];
  onDeviceClick?: (deviceId: string) => void;
}

export default function DeviceList({
  devices,
  onDeviceClick,
}: DeviceListProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredDevices = devices.filter(
    (device) =>
      device.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      device.device_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="搜索设备..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDevices.map((device) => (
            <div
              key={device.device_id}
              onClick={() => onDeviceClick?.(device.device_id)}
              className="cursor-pointer"
            >
              <DeviceCard
                deviceId={device.device_id}
                name={device.name}
                deviceType="Device" // 应该从设备元数据获取
                isOnline={device.is_online}
                voltage={device.current_voltage}
                current={device.current_current}
                power={device.current_power}
                lastUpdate={device.last_update}
              />
            </div>
          ))}
        </div>
        {filteredDevices.length === 0 && (
          <div className="text-center text-gray-400 py-8">
            没有找到设备
          </div>
        )}
      </div>
    </div>
  );
}
