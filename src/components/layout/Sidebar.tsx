import { Link, useLocation } from "react-router-dom";
import { 
  Network, 
  Sliders, 
  Play, 
  Radio, 
  Activity, 
  BarChart3, 
  Brain 
} from "lucide-react";
import clsx from "clsx";

const menuItems = [
  { path: "/topology", icon: Network, label: "拓扑设计" },
  { path: "/device-control", icon: Sliders, label: "设备控制" },
  { path: "/simulation", icon: Play, label: "仿真运行" },
  { path: "/modbus", icon: Radio, label: "Modbus通信" },
  { path: "/monitoring", icon: Activity, label: "实时监控" },
  { path: "/analytics", icon: BarChart3, label: "数据分析" },
  { path: "/ai", icon: Brain, label: "AI 智能" },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h1 className="text-lg font-bold text-gray-900">微电网模拟器</h1>
      </div>
      <nav className="flex-1 p-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || 
            (location.pathname === '/' && item.path === '/topology');
          return (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 transition-colors text-sm",
                isActive
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-gray-700 hover:bg-gray-100"
              )}
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
