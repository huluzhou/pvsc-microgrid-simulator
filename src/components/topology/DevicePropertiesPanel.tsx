import { useState, useEffect } from "react";
import { X } from "lucide-react";

interface DevicePropertiesPanelProps {
  device: {
    id: string;
    name: string;
    deviceType: string;
    properties: Record<string, any>;
  } | null;
  onClose: () => void;
  onUpdate: (deviceId: string, updates: any) => void;
}

export default function DevicePropertiesPanel({
  device,
  onClose,
  onUpdate,
}: DevicePropertiesPanelProps) {
  const [formData, setFormData] = useState<Record<string, any>>({});

  useEffect(() => {
    if (device) {
      setFormData({
        name: device.name,
        ...device.properties,
      });
    }
  }, [device]);

  if (!device) {
    return null;
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const { name, ...properties } = formData;
    onUpdate(device.id, { name, properties });
  };

  return (
    <div className="absolute right-0 top-0 h-full w-80 bg-gray-800 border-l border-gray-700 shadow-xl z-10">
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">设备属性</h2>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-gray-700 transition-colors"
        >
          <X className="w-5 h-5 text-gray-400" />
        </button>
      </div>
      <form onSubmit={handleSubmit} className="p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            设备名称
          </label>
          <input
            type="text"
            value={formData.name || ""}
            onChange={(e) =>
              setFormData({ ...formData, name: e.target.value })
            }
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            设备类型
          </label>
          <input
            type="text"
            value={device.deviceType}
            disabled
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-400"
          />
        </div>
        {/* 根据设备类型显示不同的属性字段 */}
        {device.deviceType === "Pv" && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                额定功率 (kW)
              </label>
              <input
                type="number"
                value={formData.rated_power || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    rated_power: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
              />
            </div>
          </>
        )}
        {device.deviceType === "Storage" && (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                容量 (kWh)
              </label>
              <input
                type="number"
                value={formData.capacity || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    capacity: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white"
              />
            </div>
          </>
        )}
        <div className="flex gap-2 pt-4">
          <button
            type="submit"
            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white transition-colors"
          >
            保存
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded text-white transition-colors"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  );
}
