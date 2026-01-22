import { Search, Settings, HelpCircle } from "lucide-react";

export default function TopBar() {
  return (
    <header className="h-12 bg-white border-b border-gray-200 flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <h2 className="text-base font-semibold text-gray-800">光储充微电网模拟器</h2>
      </div>
      <div className="flex items-center gap-1">
        <button 
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          title="搜索"
        >
          <Search className="w-5 h-5 text-gray-500" />
        </button>
        <button 
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          title="设置"
        >
          <Settings className="w-5 h-5 text-gray-500" />
        </button>
        <button 
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          title="帮助"
        >
          <HelpCircle className="w-5 h-5 text-gray-500" />
        </button>
      </div>
    </header>
  );
}
