import { Search, Settings, HelpCircle, User, Moon, Sun } from "lucide-react";
import { useThemeStore } from "../../stores/theme";

export default function TopBar() {
  const { theme, toggleTheme } = useThemeStore();

  return (
    <header className="h-14 bg-gray-800 dark:bg-gray-900 border-b border-gray-700 dark:border-gray-800 flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold text-white">光储充微电网模拟器</h2>
      </div>
      <div className="flex items-center gap-2">
        <button 
          className="p-2 rounded-lg hover:bg-gray-700 dark:hover:bg-gray-800 transition-colors"
          onClick={toggleTheme}
          title={theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'}
        >
          {theme === 'dark' ? (
            <Sun className="w-5 h-5 text-yellow-400" />
          ) : (
            <Moon className="w-5 h-5 text-gray-300" />
          )}
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 dark:hover:bg-gray-800 transition-colors">
          <Search className="w-5 h-5 text-gray-300" />
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 dark:hover:bg-gray-800 transition-colors">
          <Settings className="w-5 h-5 text-gray-300" />
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 dark:hover:bg-gray-800 transition-colors">
          <HelpCircle className="w-5 h-5 text-gray-300" />
        </button>
        <button className="p-2 rounded-lg hover:bg-gray-700 dark:hover:bg-gray-800 transition-colors">
          <User className="w-5 h-5 text-gray-300" />
        </button>
      </div>
    </header>
  );
}
