import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Edit, Save, X } from "lucide-react";

interface DeviceMetadata {
  id: string;
  name: string;
  device_type: string;
  properties: Record<string, any>;
  work_mode?: string;
  response_delay?: number;
  measurement_error?: number;
  data_collection_frequency?: number;
}

export default function DeviceManagement() {
  const [devices, setDevices] = useState<DeviceMetadata[]>([]);
  const [editingDevice, setEditingDevice] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<DeviceMetadata>>({});

  const loadDevices = useCallback(async () => {
    try {
      const deviceList = await invoke<DeviceMetadata[]>("get_all_devices");
      setDevices(deviceList);
    } catch (error) {
      console.error("Failed to load devices:", error);
    }
  }, []);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  const handleEdit = (device: DeviceMetadata) => {
    setEditingDevice(device.id);
    setFormData({
      work_mode: device.work_mode,
      response_delay: device.response_delay,
      measurement_error: device.measurement_error,
      data_collection_frequency: device.data_collection_frequency,
    });
  };

  const handleSave = async (deviceId: string) => {
    try {
      await invoke("update_device_config", {
        config: {
          device_id: deviceId,
          ...formData,
        },
      });
      setEditingDevice(null);
      await loadDevices();
    } catch (error) {
      console.error("Failed to update device:", error);
      alert("更新失败：" + error);
    }
  };

  const handleCancel = () => {
    setEditingDevice(null);
    setFormData({});
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6 text-white">设备管理</h1>
      <div className="bg-gray-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">设备ID</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">名称</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">类型</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">工作模式</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">响应延迟(s)</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">测量误差(%)</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">采集频率(s)</th>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {devices.map((device) => (
              <tr key={device.id} className="hover:bg-gray-750">
                <td className="px-4 py-3 text-sm text-gray-300">{device.id}</td>
                <td className="px-4 py-3 text-sm text-white">{device.name}</td>
                <td className="px-4 py-3 text-sm text-gray-300">{device.device_type}</td>
                <td className="px-4 py-3 text-sm text-white">
                  {editingDevice === device.id ? (
                    <select
                      value={formData.work_mode || ""}
                      onChange={(e) => setFormData({ ...formData, work_mode: e.target.value })}
                      className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white"
                    >
                      <option value="random_data">随机数据模式</option>
                      <option value="manual">手动模式</option>
                      <option value="remote">远程模式</option>
                      <option value="historical_data">历史数据模式</option>
                    </select>
                  ) : (
                    device.work_mode || "-"
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-white">
                  {editingDevice === device.id ? (
                    <input
                      type="number"
                      step="0.1"
                      value={formData.response_delay || ""}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          response_delay: parseFloat(e.target.value) || undefined,
                        })
                      }
                      className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white w-20"
                    />
                  ) : (
                    device.response_delay?.toFixed(2) || "-"
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-white">
                  {editingDevice === device.id ? (
                    <input
                      type="number"
                      step="0.1"
                      value={formData.measurement_error || ""}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          measurement_error: parseFloat(e.target.value) || undefined,
                        })
                      }
                      className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white w-20"
                    />
                  ) : (
                    device.measurement_error?.toFixed(2) || "-"
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-white">
                  {editingDevice === device.id ? (
                    <input
                      type="number"
                      step="0.1"
                      value={formData.data_collection_frequency || ""}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          data_collection_frequency: parseFloat(e.target.value) || undefined,
                        })
                      }
                      className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white w-20"
                    />
                  ) : (
                    device.data_collection_frequency?.toFixed(2) || "-"
                  )}
                </td>
                <td className="px-4 py-3 text-sm">
                  {editingDevice === device.id ? (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSave(device.id)}
                        className="p-1 text-green-500 hover:text-green-400"
                      >
                        <Save className="w-4 h-4" />
                      </button>
                      <button
                        onClick={handleCancel}
                        className="p-1 text-red-500 hover:text-red-400"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => handleEdit(device)}
                      className="p-1 text-blue-500 hover:text-blue-400"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
