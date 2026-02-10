/**
 * 开关控制组件 - 控制开关的闭合/断开状态
 */
import { useState, useEffect } from 'react';
import { Power, PowerOff } from 'lucide-react';

interface SwitchControlProps {
  /** 初始状态：true=闭合，false=断开 */
  initialClosed?: boolean;
  /** 保存回调 */
  onSave: (isClosed: boolean) => void;
  /** 取消回调 */
  onCancel: () => void;
}

export default function SwitchControl({ initialClosed = true, onSave, onCancel }: SwitchControlProps) {
  const [isClosed, setIsClosed] = useState(initialClosed);

  useEffect(() => {
    setIsClosed(initialClosed);
  }, [initialClosed]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(isClosed);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="text-sm text-gray-600 mb-3">
        控制开关的闭合与断开状态
      </div>

      {/* 开关状态切换 */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <label className="block text-xs font-medium text-gray-600 mb-3">开关状态</label>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => setIsClosed(true)}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
              isClosed
                ? 'border-green-500 bg-green-50 text-green-700'
                : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
            }`}
          >
            <Power className="w-5 h-5" />
            <span className="font-medium">闭合</span>
          </button>
          <button
            type="button"
            onClick={() => setIsClosed(false)}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
              !isClosed
                ? 'border-red-500 bg-red-50 text-red-700'
                : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
            }`}
          >
            <PowerOff className="w-5 h-5" />
            <span className="font-medium">断开</span>
          </button>
        </div>
      </div>

      {/* 当前状态说明 */}
      <div className={`p-3 rounded-lg text-sm ${
        isClosed ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
      }`}>
        {isClosed ? (
          <>
            <strong>闭合状态：</strong>开关接通，电流可以通过，潮流计算将考虑该开关。
          </>
        ) : (
          <>
            <strong>断开状态：</strong>开关断开，无电流通过，潮流计算将忽略该开关连接。
          </>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded text-white font-medium transition-colors"
        >
          应用设置
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 font-medium transition-colors"
        >
          取消
        </button>
      </div>
    </form>
  );
}
