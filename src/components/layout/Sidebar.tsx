import { Link, useLocation } from "react-router-dom";
import { 
  Network, 
  Settings, 
  Activity, 
  Play, 
  BarChart3, 
  Brain 
} from "lucide-react";
import clsx from "clsx";

const menuItems = [
  { path: "/topology", icon: Network, label: "拓扑设计" },
  { path: "/devices", icon: Settings, label: "设备管理" },
  { path: "/monitoring", icon: Activity, label: "实时监控" },
  { path: "/simulation", icon: Play, label: "仿真控制" },
  { path: "/analytics", icon: BarChart3, label: "数据分析" },
  { path: "/ai", icon: Brain, label: "AI 智能" },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h1 className="text-lg font-bold">微电网模拟器</h1>
      </div>
      <nav className="flex-1 p-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                "flex items-center gap-3 px-4 py-3 rounded-lg mb-1 transition-colors",
                isActive
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:bg-gray-700 hover:text-white"
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
