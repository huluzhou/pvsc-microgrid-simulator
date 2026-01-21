import { memo } from "react";
import { Handle, Position, NodeProps } from "reactflow";
import {
  Zap,
  Battery,
  Sun,
  Plug,
  Gauge,
  Network,
  Power,
  Loader,
} from "lucide-react";

const deviceIcons: Record<string, any> = {
  Node: Network,
  Line: Zap,
  Transformer: Power,
  Switch: Zap,
  Pv: Sun,
  Storage: Battery,
  Load: Loader,
  Charger: Plug,
  Meter: Gauge,
};

const deviceColors: Record<string, string> = {
  Node: "bg-blue-500",
  Line: "bg-yellow-500",
  Transformer: "bg-purple-500",
  Switch: "bg-gray-500",
  Pv: "bg-orange-500",
  Storage: "bg-green-500",
  Load: "bg-red-500",
  Charger: "bg-cyan-500",
  Meter: "bg-indigo-500",
};

function DeviceNode({ data, selected }: NodeProps) {
  const Icon = deviceIcons[data.deviceType] || Network;
  const colorClass = deviceColors[data.deviceType] || "bg-gray-500";

  return (
    <div
      className={`px-4 py-2 shadow-lg rounded-lg border-2 ${
        selected ? "border-blue-500" : "border-gray-300"
      } bg-gray-800 min-w-[150px]`}
    >
      <div className="flex items-center gap-2">
        <div className={`${colorClass} p-2 rounded`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-white text-sm">{data.name}</div>
          <div className="text-xs text-gray-400">{data.deviceType}</div>
        </div>
      </div>
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
}

export default memo(DeviceNode);
