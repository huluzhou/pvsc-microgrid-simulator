export default function StatusBar() {
  return (
    <footer className="h-8 bg-gray-800 border-t border-gray-700 flex items-center justify-between px-4 text-sm text-gray-400">
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-2">
          <span className="w-2 h-2 bg-green-500 rounded-full"></span>
          状态: 运行中
        </span>
        <span>设备数: 0</span>
        <span>模式: 未配置</span>
      </div>
      <div>
        <span>最后更新: {new Date().toLocaleTimeString()}</span>
      </div>
    </footer>
  );
}
