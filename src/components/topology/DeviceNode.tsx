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

// 渲染设备SVG图形
function renderDeviceSvg(
  deviceType: DeviceType, 
  color: string, 
  width: number, 
  height: number,
  selected: boolean
): JSX.Element {
  const strokeWidth = selected ? 3 : 2;
  const strokeColor = selected ? '#3b82f6' : color;
  
  switch (deviceType) {
    case 'bus':
      // 母线 - 水平粗线
      return (
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
          <line 
            x1="0" y1={height/2} 
            x2={width} y2={height/2} 
            stroke={strokeColor} 
            strokeWidth={4} 
          />
          {/* 连接点标记 */}
          <circle cx="10" cy={height/2} r="3" fill={strokeColor} />
          <circle cx={width/2} cy={height/2} r="3" fill={strokeColor} />
          <circle cx={width-10} cy={height/2} r="3" fill={strokeColor} />
        </svg>
      );
    
    case 'external_grid':
      // 外部电网 - 网格矩形
      return (
        <svg width={width} height={height} viewBox="0 0 50 50">
          <rect x="5" y="5" width="40" height="40" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="15" y1="5" x2="15" y2="45" stroke={strokeColor} strokeWidth="1" />
          <line x1="25" y1="5" x2="25" y2="45" stroke={strokeColor} strokeWidth="1" />
          <line x1="35" y1="5" x2="35" y2="45" stroke={strokeColor} strokeWidth="1" />
          <line x1="5" y1="15" x2="45" y2="15" stroke={strokeColor} strokeWidth="1" />
          <line x1="5" y1="25" x2="45" y2="25" stroke={strokeColor} strokeWidth="1" />
          <line x1="5" y1="35" x2="45" y2="35" stroke={strokeColor} strokeWidth="1" />
        </svg>
      );
    
    case 'static_generator':
      // 光伏 - 圆圈+PV
      return (
        <svg width={width} height={height} viewBox="0 0 50 50">
          <circle cx="25" cy="28" r="18" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <text x="25" y="33" textAnchor="middle" fontSize="12" fontWeight="bold" fill={strokeColor}>PV</text>
          <line x1="25" y1="10" x2="25" y2="0" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    case 'storage':
      // 储能 - 电池形状
      return (
        <svg width={width} height={height} viewBox="0 0 50 40">
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
      // 负载 - 三角形尖朝下
      return (
        <svg width={width} height={height} viewBox="0 0 40 45">
          <path d="M20,8 L5,40 L35,40 Z" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="20" y1="8" x2="20" y2="0" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    case 'charger':
      // 充电桩 - 矩形+插头
      return (
        <svg width={width} height={height} viewBox="0 0 40 50">
          <rect x="8" y="15" width="24" height="30" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <rect x="14" y="8" width="12" height="7" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="20" y1="8" x2="20" y2="0" stroke={strokeColor} strokeWidth={strokeWidth} />
          {/* 闪电符号 */}
          <path d="M18,25 L22,25 L20,32 L24,32 L17,42 L19,35 L15,35 Z" fill={strokeColor} />
        </svg>
      );
    
    case 'transformer':
      // 变压器 - 两个相切圆
      return (
        <svg width={width} height={height} viewBox="0 0 50 70">
          <circle cx="25" cy="20" r="14" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <circle cx="25" cy="50" r="14" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="25" y1="0" x2="25" y2="6" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="25" y1="64" x2="25" y2="70" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    case 'switch':
      // 开关 - 断开触点
      return (
        <svg width={width} height={height} viewBox="0 0 60 30">
          <line x1="0" y1="15" x2="20" y2="15" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="40" y1="15" x2="60" y2="15" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="20" y1="15" x2="35" y2="5" stroke={strokeColor} strokeWidth={strokeWidth} />
          <circle cx="20" cy="15" r="3" fill={strokeColor} />
          <circle cx="40" cy="15" r="3" fill={strokeColor} />
        </svg>
      );
    
    case 'line':
      // 线路 - 细线
      return (
        <svg width={width} height={height} viewBox="0 0 60 20">
          <line x1="0" y1="10" x2="60" y2="10" stroke={strokeColor} strokeWidth={strokeWidth} />
          <circle cx="5" cy="10" r="2" fill={strokeColor} />
          <circle cx="55" cy="10" r="2" fill={strokeColor} />
        </svg>
      );
    
    case 'meter':
      // 电表 - 圆圈+M
      return (
        <svg width={width} height={height} viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="16" fill="none" stroke={strokeColor} strokeWidth={strokeWidth} />
          <text x="20" y="25" textAnchor="middle" fontSize="14" fontWeight="bold" fill={strokeColor}>M</text>
          <line x1="0" y1="20" x2="4" y2="20" stroke={strokeColor} strokeWidth={strokeWidth} />
          <line x1="36" y1="20" x2="40" y2="20" stroke={strokeColor} strokeWidth={strokeWidth} />
        </svg>
      );
    
    default:
      return (
        <svg width={width} height={height}>
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
    default: return Position.Top;
  }
}

// 获取Handle样式偏移
function getHandleStyle(
  point: ConnectionPoint, 
  deviceType: DeviceType,
  info: { width: number; height: number }
): React.CSSProperties {
  const style: React.CSSProperties = {};
  
  if (deviceType === 'bus') {
    // 母线特殊处理 - 三个连接点
    if (point.id === 'left') {
      style.left = 10;
    } else if (point.id === 'right') {
      style.left = info.width - 10;
    } else {
      style.left = info.width / 2;
    }
    style.top = info.height / 2;
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
      style={{ width: info.width, minHeight: info.height + 20, userSelect: 'none', WebkitUserSelect: 'none' }}
    >
      {/* SVG 图形 */}
      <div className="flex items-center justify-center">
        {svgElement}
      </div>
      
      {/* 设备名称标签 */}
      <div 
        className="mt-1 px-1.5 py-0.5 rounded text-xs font-medium text-white whitespace-nowrap"
        style={{ backgroundColor: selected ? '#3b82f6' : info.color }}
      >
        {data.name}
      </div>
      
      {/* 连接点 Handles */}
      {info.connectionPoints.map((point) => (
        <Handle
          key={`${point.id}-target`}
          type="target"
          position={getHandlePosition(point.position)}
          id={point.id}
          className="!w-3 !h-3 !bg-red-500 !border-2 !border-white"
          style={getHandleStyle(point, deviceType, info)}
        />
      ))}
      {info.connectionPoints.map((point) => (
        <Handle
          key={`${point.id}-source`}
          type="source"
          position={getHandlePosition(point.position)}
          id={`${point.id}-source`}
          className="!w-3 !h-3 !bg-red-500 !border-2 !border-white !opacity-0 hover:!opacity-100"
          style={getHandleStyle(point, deviceType, info)}
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
