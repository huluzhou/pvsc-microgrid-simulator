/**
 * 设备面板组件 - 浅色主题
 * 显示所有可用设备类型，支持拖拽到画布
 */
import { memo, DragEvent, useRef, useEffect } from 'react';
import { 
  DEVICE_CATEGORIES, 
  DEVICE_TYPES, 
  DeviceType,
  DeviceCategory 
} from '../../constants/deviceTypes';

interface DevicePanelProps {
  onDeviceSelect?: (deviceType: DeviceType) => void;
}

// 设备缩略图SVG
function DeviceThumbnail({ type }: { type: DeviceType }) {
  const info = DEVICE_TYPES[type];
  const color = info.color;
  const size = 32;
  
  switch (type) {
    case 'bus':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <line x1="4" y1="16" x2="28" y2="16" stroke={color} strokeWidth="3" />
        </svg>
      );
    case 'external_grid':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <rect x="4" y="4" width="24" height="24" fill="none" stroke={color} strokeWidth="2" />
          <line x1="12" y1="4" x2="12" y2="28" stroke={color} strokeWidth="1" />
          <line x1="20" y1="4" x2="20" y2="28" stroke={color} strokeWidth="1" />
          <line x1="4" y1="12" x2="28" y2="12" stroke={color} strokeWidth="1" />
          <line x1="4" y1="20" x2="28" y2="20" stroke={color} strokeWidth="1" />
        </svg>
      );
    case 'static_generator':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <circle cx="16" cy="18" r="10" fill="none" stroke={color} strokeWidth="2" />
          <text x="16" y="22" textAnchor="middle" fontSize="8" fontWeight="bold" fill={color}>PV</text>
        </svg>
      );
    case 'storage':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <rect x="4" y="10" width="20" height="14" fill="none" stroke={color} strokeWidth="2" />
          <rect x="24" y="14" width="3" height="6" fill="none" stroke={color} strokeWidth="2" />
        </svg>
      );
    case 'load':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <path d="M16,6 L6,26 L26,26 Z" fill="none" stroke={color} strokeWidth="2" />
        </svg>
      );
    case 'charger':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <rect x="6" y="10" width="20" height="18" fill="none" stroke={color} strokeWidth="2" />
          <rect x="11" y="4" width="10" height="6" fill="none" stroke={color} strokeWidth="2" />
        </svg>
      );
    case 'transformer':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <circle cx="16" cy="10" r="7" fill="none" stroke={color} strokeWidth="2" />
          <circle cx="16" cy="22" r="7" fill="none" stroke={color} strokeWidth="2" />
        </svg>
      );
    case 'switch':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <line x1="2" y1="16" x2="12" y2="16" stroke={color} strokeWidth="2" />
          <line x1="20" y1="16" x2="30" y2="16" stroke={color} strokeWidth="2" />
          <line x1="12" y1="16" x2="20" y2="8" stroke={color} strokeWidth="2" />
          <circle cx="12" cy="16" r="2" fill={color} />
          <circle cx="20" cy="16" r="2" fill={color} />
        </svg>
      );
    case 'line':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <line x1="4" y1="16" x2="28" y2="16" stroke={color} strokeWidth="2" />
        </svg>
      );
    case 'meter':
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <circle cx="16" cy="16" r="10" fill="none" stroke={color} strokeWidth="2" />
          <text x="16" y="20" textAnchor="middle" fontSize="10" fontWeight="bold" fill={color}>M</text>
        </svg>
      );
    default:
      return (
        <svg width={size} height={size} viewBox="0 0 32 32">
          <rect x="4" y="4" width="24" height="24" fill="none" stroke={color} strokeWidth="2" />
        </svg>
      );
  }
}

// 单个设备项组件
const DeviceItem = memo(function DeviceItem({ 
  type, 
  onSelect 
}: { 
  type: DeviceType; 
  onSelect?: (type: DeviceType) => void;
}) {
  const info = DEVICE_TYPES[type];
  const dragImageRef = useRef<HTMLDivElement>(null);
  
  // 预渲染拖拽预览图像
  useEffect(() => {
    if (dragImageRef.current) {
      // 确保元素已渲染
      dragImageRef.current.style.transform = 'translateX(-9999px)';
    }
  }, []);
  
  const handleDragStart = (e: DragEvent<HTMLDivElement>) => {
    e.dataTransfer.setData('application/device-type', type);
    e.dataTransfer.effectAllowed = 'copy';
    
    // 使用预渲染的元素作为拖拽预览
    if (dragImageRef.current) {
      const rect = dragImageRef.current.getBoundingClientRect();
      e.dataTransfer.setDragImage(dragImageRef.current, rect.width / 2, rect.height / 2);
    }
  };

  const handleClick = () => {
    onSelect?.(type);
  };

  return (
    <>
      <div
        draggable
        onDragStart={handleDragStart}
        onClick={handleClick}
        className="flex items-center gap-2 px-2 py-2 rounded cursor-grab hover:bg-gray-100 active:cursor-grabbing border border-transparent hover:border-gray-300 transition-colors select-none"
        title={`拖拽添加${info.name}`}
      >
        <div 
          className="w-10 h-10 rounded flex items-center justify-center bg-gray-50 border border-gray-200"
        >
          <DeviceThumbnail type={type} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-800">{info.name}</div>
          <div className="text-xs text-gray-500 truncate">{info.description}</div>
        </div>
      </div>
      
      {/* 隐藏的拖拽预览元素 - 预渲染以提高性能 */}
      <div
        ref={dragImageRef}
        className="fixed pointer-events-none bg-white rounded-lg border-2 border-blue-400 shadow-xl p-2 opacity-90"
        style={{ 
          left: '-9999px',
          top: '-9999px',
          zIndex: 9999
        }}
      >
        <div className="flex flex-col items-center gap-1">
          <div 
            className="w-12 h-12 rounded flex items-center justify-center"
            style={{ backgroundColor: info.color + '20' }}
          >
            <DeviceThumbnail type={type} />
          </div>
          <div className="text-xs font-medium text-gray-800 whitespace-nowrap">
            {info.name}
          </div>
        </div>
      </div>
    </>
  );
});

// 设备分类组件
const CategoryGroup = memo(function CategoryGroup({
  category,
  types,
  onDeviceSelect,
}: {
  category: DeviceCategory;
  types: DeviceType[];
  onDeviceSelect?: (type: DeviceType) => void;
}) {
  const categoryInfo = DEVICE_CATEGORIES[category];

  return (
    <div className="mb-3">
      <div className="px-2 py-1 text-xs font-semibold text-gray-500 uppercase tracking-wider">
        {categoryInfo.name}
      </div>
      <div className="space-y-1">
        {types.map((type) => (
          <DeviceItem 
            key={type} 
            type={type} 
            onSelect={onDeviceSelect}
          />
        ))}
      </div>
    </div>
  );
});

// 主设备面板组件
function DevicePanel({ onDeviceSelect }: DevicePanelProps) {
  return (
    <div className="w-52 bg-white border-r border-gray-200 flex flex-col h-full select-none" style={{ userSelect: 'none', WebkitUserSelect: 'none' }}>
      {/* 标题 */}
      <div className="px-3 py-2 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-800">设备</h2>
        <p className="text-xs text-gray-500">拖拽到画布添加</p>
      </div>
      
      {/* 设备列表 */}
      <div className="flex-1 overflow-y-auto p-2">
        {(Object.keys(DEVICE_CATEGORIES) as DeviceCategory[]).map((category) => (
          <CategoryGroup
            key={category}
            category={category}
            types={DEVICE_CATEGORIES[category].types}
            onDeviceSelect={onDeviceSelect}
          />
        ))}
      </div>
      
      {/* 底部提示 */}
      <div className="px-3 py-2 border-t border-gray-200 text-xs text-gray-400">
        Delete 删除 | Ctrl+S 保存
      </div>
    </div>
  );
}

export default memo(DevicePanel);
