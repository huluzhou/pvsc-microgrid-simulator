/**
 * 设备节点组件
 * 使用内联SVG绘制几何图形，参考电气符号
 */
import { memo, useMemo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { DEVICE_TYPES, DeviceType, ConnectionPoint } from '../../constants/deviceTypes';

interface DeviceNodeData {
  name: string;
  deviceType: DeviceType;
  properties?: Record<string, any>;
}

// 渲染设备SVG图形（添加 shape-rendering 优化缩放清晰度）
function renderDeviceSvg(
  deviceType: DeviceType, 
  color: string, 
  width: number, 
  height: number,
  selected: boolean
): JSX.Element {
  const strokeWidth = selected ? 3 : 2;
  const strokeColor = selected ? '#3b82f6' : color;
  // SVG 通用属性，优化缩放渲染清晰度
  const svgProps = {
    shapeRendering: 'geometricPrecision' as const,
    style: { 
      overflow: 'visible' as const,
      // 防止缩放时模糊
      imageRendering: 'auto' as const,
    },
    // 使用 vectorEffect 防止线条在缩放时变形
    vectorEffect: 'non-scaling-stroke' as const,
  };
  
  switch (deviceType) {
    case 'bus':
      // 母线 - 水平粗线，单个中心连接点
      return (
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} {...svgProps}>
          <line 
            x1="0" y1={height/2} 
            x2={width} y2={height/2} 
            stroke={strokeColor} 
            strokeWidth={4} 
          />
          {/* 中心连接点标记 */}
          <circle cx={width/2} cy={height/2} r="3" fill={strokeColor} />
        </svg>
      );
    
    case 'external_grid':
      // 外部电网 - 网格矩形，底部连接点
      return (
        <svg width={width} height={height} viewBox="0 0 50 50" {...svgProps}>
          <rect x="5" y="5" width="40" height="40" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="15" y1="5" x2="15" y2="45" stroke={strokeColor} strokeWidth="1" />
          <line x1="25" y1="5" x2="25" y2="45" stroke={strokeColor} strokeWidth="1" />
          <line x1="35" y1="5" x2="35" y2="45" stroke={strokeColor} strokeWidth="1" />
          <line x1="5" y1="15" x2="45" y2="15" stroke={strokeColor} strokeWidth="1" />
          <line x1="5" y1="25" x2="45" y2="25" stroke={strokeColor} strokeWidth="1" />
          <line x1="5" y1="35" x2="45" y2="35" stroke={strokeColor} strokeWidth="1" />
          {/* 底部连接线 */}
          <line x1="25" y1="45" x2="25" y2="50" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    case 'static_generator':
      // 光伏 - 圆圈+PV，顶部连接点
      return (
        <svg width={width} height={height} viewBox="0 0 50 50" {...svgProps}>
          <circle cx="25" cy="28" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <text x="25" y="33" textAnchor="middle" fontSize="12" fontWeight="bold" fill={strokeColor}>PV</text>
          <line x1="25" y1="10" x2="25" y2="0" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    case 'storage':
      // 储能 - 电池形状，顶部连接点
      return (
        <svg width={width} height={height} viewBox="0 0 50 40" {...svgProps}>
          <rect x="8" y="12" width="30" height="20" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <rect x="38" y="18" width="4" height="8" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          {/* 电量格 */}
          <rect x="11" y="15" width="7" height="14" fill={strokeColor} opacity="0.6" />
          <rect x="20" y="15" width="7" height="14" fill={strokeColor} opacity="0.4" />
          <rect x="29" y="15" width="6" height="14" fill={strokeColor} opacity="0.2" />
          <line x1="25" y1="12" x2="25" y2="0" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    case 'load':
      // 负载 - 三角形尖朝下，顶部连接点
      return (
        <svg width={width} height={height} viewBox="0 0 40 45" {...svgProps}>
          <path d="M20,8 L5,40 L35,40 Z" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="20" y1="8" x2="20" y2="0" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    case 'charger':
      // 充电桩 - 矩形+插头，顶部连接点
      return (
        <svg width={width} height={height} viewBox="0 0 40 50" {...svgProps}>
          <rect x="8" y="15" width="24" height="30" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <rect x="14" y="8" width="12" height="7" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="20" y1="8" x2="20" y2="0" stroke={strokeColor} strokeWidth={strokeWidth} />
          {/* 闪电符号 */}
          <path d="M18,25 L22,25 L20,32 L24,32 L17,42 L19,35 L15,35 Z" fill={strokeColor} />
        </svg>
      );
    
    case 'transformer':
      // 变压器 - 两个相切圆，上下连接点
      return (
        <svg width={width} height={height} viewBox="0 0 50 70" {...svgProps}>
          <circle cx="25" cy="20" r="14" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <circle cx="25" cy="50" r="14" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="25" y1="0" x2="25" y2="6" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="25" y1="64" x2="25" y2="70" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    case 'switch':
      // 开关 - 断开触点，左右连接点
      return (
        <svg width={width} height={height} viewBox="0 0 60 30" {...svgProps}>
          <line x1="0" y1="15" x2="20" y2="15" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="40" y1="15" x2="60" y2="15" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="20" y1="15" x2="35" y2="5" stroke={strokeColor} strokeWidth={strokeWidth} />
          <circle cx="20" cy="15" r="3" fill={strokeColor} />
          <circle cx="40" cy="15" r="3" fill={strokeColor} />
        </svg>
      );
    
    case 'line':
      // 线路 - 竖向细线，上下连接点
      return (
        <svg width={width} height={height} viewBox="0 0 20 60" {...svgProps}>
          <line x1="10" y1="0" x2="10" y2="60" stroke={strokeColor} strokeWidth={strokeWidth} />
          <circle cx="10" cy="5" r="2" fill={strokeColor} />
          <circle cx="10" cy="55" r="2" fill={strokeColor} />
        </svg>
      );
    
    case 'meter':
      // 电表 - 圆圈+M，顶部连接点
      return (
        <svg width={width} height={height} viewBox="0 0 40 40" {...svgProps}>
          <circle cx="20" cy="22" r="16" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <text x="20" y="27" textAnchor="middle" fontSize="14" fontWeight="bold" fill={strokeColor}>M</text>
          <line x1="20" y1="6" x2="20" y2="0" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    default:
      return (
        <svg width={width} height={height} {...svgProps}>
          <rect x="2" y="2" width={width-4} height={height-4} fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
  }
}

// 获取Handle位置
function getHandlePosition(position: string): Position {
  switch (position) {
    case 'top': return Position.Top;
    case 'bottom': return Position.Bottom;
    case 'left': return Position.Left;
    case 'right': return Position.Right;
    case 'center': return Position.Top;  // 中心点默认使用 Top 位置
    default: return Position.Top;
  }
}

// 获取Handle样式偏移（参考 PySide 版本的连接点位置）
// 注意：Handle 的位置是相对于整个节点容器的，需要考虑标签空间
function getHandleStyle(
  point: ConnectionPoint, 
  deviceType: DeviceType,
  info: { width: number; height: number }
): React.CSSProperties {
  const style: React.CSSProperties = {};
  
  // 母线 - 中心连接点
  if (deviceType === 'bus' && point.id === 'center') {
    style.left = info.width / 2;
    style.top = info.height / 2;
  }
  
  // 开关 - 左右连接点需要精确定位到 SVG 线条端点
  if (deviceType === 'switch') {
    // SVG 线条在 y=15 (height/2)，Handle 需要在这个位置
    style.top = info.height / 2;  // 30/2 = 15
  }
  
  // 线路 - 上下连接点
  if (deviceType === 'line') {
    if (point.id === 'top') {
      style.top = 0;
    } else if (point.id === 'bottom') {
      style.top = info.height;
    }
  }
  
  return style;
}

function DeviceNode({ data, selected }: NodeProps<DeviceNodeData>) {
  const deviceType = data.deviceType as DeviceType;
  const info = DEVICE_TYPES[deviceType];
  
  // 使用 useMemo 缓存SVG渲染
  const svgElement = useMemo(() => {
    if (!info) return null;
    return renderDeviceSvg(deviceType, info.color, info.width, info.height, selected || false);
  }, [deviceType, info, selected]);

  if (!info) {
    return (
      <div className="p-2 bg-gray-200 rounded text-gray-700 text-xs border border-gray-400">
        未知设备: {deviceType}
      </div>
    );
  }

  return (
    <div 
      className="relative flex flex-col items-center select-none"
      style={{ 
        width: info.width, 
        minHeight: info.height + 24,  // 增加标签空间
        userSelect: 'none', 
        WebkitUserSelect: 'none',
        // 缩放优化
        willChange: 'transform',
        transform: 'translateZ(0)',
        backfaceVisibility: 'hidden',
      }}
    >
      {/* 选中状态外框 */}
      {selected && (
        <div 
          className="absolute inset-0 rounded pointer-events-none"
          style={{
            border: '2px solid #3b82f6',
            boxShadow: '0 0 8px 2px rgba(59, 130, 246, 0.5)',
            margin: -4,
            borderRadius: 4,
          }}
        />
      )}
      
      {/* SVG 图形 */}
      <div className="flex items-center justify-center">
        {svgElement}
      </div>
      
      {/* 设备名称标签 - 调整位置避免遮挡连接点 */}
      <div 
        className="absolute px-1.5 py-0.5 rounded text-xs font-medium text-white whitespace-nowrap"
        style={{ 
          backgroundColor: selected ? '#3b82f6' : info.color,
          top: info.height + 4,  // 固定在 SVG 下方
          left: '50%',
          transform: 'translateX(-50%)',
          WebkitFontSmoothing: 'antialiased',
          textRendering: 'optimizeLegibility',
          zIndex: 1,  // 确保标签不遮挡连接点
        }}
      >
        {data.name}
      </div>
      
      {/* 连接点 Handles - 减小尺寸，提高 z-index */}
      {info.connectionPoints.map((point) => (
        <Handle
          key={`${point.id}-target`}
          type="target"
          position={getHandlePosition(point.position)}
          id={point.id}
          className="!w-2.5 !h-2.5 !bg-red-500 !border-2 !border-white"
          style={{
            ...getHandleStyle(point, deviceType, info),
            zIndex: 10,
          }}
        />
      ))}
      {info.connectionPoints.map((point) => (
        <Handle
          key={`${point.id}-source`}
          type="source"
          position={getHandlePosition(point.position)}
          id={`${point.id}-source`}
          className="!w-2.5 !h-2.5 !bg-red-500 !border-2 !border-white !opacity-0 hover:!opacity-100"
          style={{
            ...getHandleStyle(point, deviceType, info),
            zIndex: 10,
          }}
        />
      ))}
    </div>
  );
}

// 使用 memo 进行性能优化
export default memo(DeviceNode, (prevProps, nextProps) => {
  return (
    prevProps.data.name === nextProps.data.name &&
    prevProps.data.deviceType === nextProps.data.deviceType &&
    prevProps.selected === nextProps.selected
  );
});
