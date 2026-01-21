import { Search, Settings, HelpCircle, User } from "lucide-react";

export default function TopBar() {
  return (
    <header className="h-14 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold">光储充微电网模拟器</h2>
      </div>
      <div className="flex items-center gap-2">
        <button className="p-2 rounded-lg hover:bg-gray-700 transition-colors">
          <Search className="w-5 h-5" />
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 transition-colors">
          <Settings className="w-5 h-5" />
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 transition-colors">
          <HelpCircle className="w-5 h-5" />
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 transition-colors">
          <User className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}
