/**
 * 开关控制组件 - 单按钮切换闭合/断开
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

  const handleToggle = () => {
    const newState = !isClosed;
    setIsClosed(newState);
    onSave(newState);
  };

  return (
    <div className="space-y-3">
      <div className="text-sm text-gray-600">
        当前状态：<span className={`font-medium ${isClosed ? 'text-green-700' : 'text-red-700'}`}>
          {isClosed ? '闭合' : '断开'}
        </span>
      </div>

      <button
        type="button"
        onClick={handleToggle}
        className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-medium transition-all ${
          isClosed
            ? 'bg-red-50 border-2 border-red-300 text-red-700 hover:bg-red-100'
            : 'bg-green-50 border-2 border-green-300 text-green-700 hover:bg-green-100'
        }`}
      >
        {isClosed ? (
          <>
            <PowerOff className="w-5 h-5" />
            <span>断开开关</span>
          </>
        ) : (
          <>
            <Power className="w-5 h-5" />
            <span>闭合开关</span>
          </>
        )}
      </button>

      <button
        type="button"
        onClick={onCancel}
        className="w-full px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 text-sm transition-colors"
      >
        关闭
      </button>
    </div>
  );
}
