/**
 * 设备类型定义
 * 定义所有支持的电力设备类型及其属性
 */

// 设备类型枚举
export type DeviceType =
  | 'bus'
  | 'line'
  | 'transformer'
  | 'switch'
  | 'static_generator'
  | 'storage'
  | 'load'
  | 'charger'
  | 'meter'
  | 'external_grid';

// 设备分类
export type DeviceCategory = 'node' | 'connection' | 'power' | 'measurement';

// 连接点位置类型
export type ConnectionPointPosition = 'top' | 'bottom' | 'left' | 'right' | 'center';

// 连接点定义
export interface ConnectionPoint {
  id: string;
  position: ConnectionPointPosition;
  offsetX?: number;  // 相对中心的X偏移
  offsetY?: number;  // 相对中心的Y偏移
}

// 设备类型信息
export interface DeviceTypeInfo {
  type: DeviceType;
  name: string;           // 中文名称
  category: DeviceCategory;
  color: string;          // 主题色
  width: number;          // 节点宽度
  height: number;         // 节点高度
  connectionPoints: ConnectionPoint[];  // 连接点
  description: string;    // 描述
}

// 设备类型配置（参考 PySide 版本的连接点定义）
export const DEVICE_TYPES: Record<DeviceType, DeviceTypeInfo> = {
  bus: {
    type: 'bus',
    name: '母线',
    category: 'node',
    color: '#1e40af',
    width: 120,
    height: 20,
    connectionPoints: [
      { id: 'center', position: 'center' },  // 母线只有1个中心连接点
    ],
    description: '电力系统中的汇流节点',
  },
  line: {
    type: 'line',
    name: '线路',
    category: 'connection',
    color: '#78716c',
    width: 20,
    height: 60,  // 竖向显示
    connectionPoints: [
      { id: 'top', position: 'top' },      // 上下两个连接点
      { id: 'bottom', position: 'bottom' },
    ],
    description: '连接两个母线的输电线路',
  },
  transformer: {
    type: 'transformer',
    name: '变压器',
    category: 'connection',
    color: '#4f46e5',
    width: 50,
    height: 70,
    connectionPoints: [
      { id: 'top', position: 'top' },
      { id: 'bottom', position: 'bottom' },
    ],
    description: '电压变换设备',
  },
  switch: {
    type: 'switch',
    name: '开关',
    category: 'connection',
    color: '#64748b',
    width: 60,
    height: 30,
    connectionPoints: [
      { id: 'left', position: 'left' },
      { id: 'right', position: 'right' },
    ],
    description: '电路控制开关',
  },
  static_generator: {
    type: 'static_generator',
    name: '光伏',
    category: 'power',
    color: '#ea580c',
    width: 50,
    height: 50,
    connectionPoints: [
      { id: 'top', position: 'top' },  // 上方1个连接点
    ],
    description: '光伏发电设备',
  },
  storage: {
    type: 'storage',
    name: '储能',
    category: 'power',
    color: '#16a34a',
    width: 50,
    height: 40,
    connectionPoints: [
      { id: 'top', position: 'top' },  // 上方1个连接点
    ],
    description: '储能系统',
  },
  load: {
    type: 'load',
    name: '负载',
    category: 'power',
    color: '#9333ea',
    width: 40,
    height: 45,
    connectionPoints: [
      { id: 'top', position: 'top' },  // 上方1个连接点
    ],
    description: '用电负载',
  },
  charger: {
    type: 'charger',
    name: '充电桩',
    category: 'power',
    color: '#0891b2',
    width: 40,
    height: 50,
    connectionPoints: [
      { id: 'top', position: 'top' },  // 上方1个连接点
    ],
    description: '电动车充电桩',
  },
  meter: {
    type: 'meter',
    name: '电表',
    category: 'measurement',
    color: '#0d9488',
    width: 40,
    height: 40,
    connectionPoints: [
      { id: 'top', position: 'top' },  // 上方1个连接点（参考 PySide）
    ],
    description: '电能计量设备',
  },
  external_grid: {
    type: 'external_grid',
    name: '外部电网',
    category: 'power',
    color: '#dc2626',
    width: 50,
    height: 50,
    connectionPoints: [
      { id: 'bottom', position: 'bottom' },  // 下方1个连接点
    ],
    description: '外部电网连接点',
  },
};

// 按分类组织的设备列表
export const DEVICE_CATEGORIES: Record<DeviceCategory, { name: string; types: DeviceType[] }> = {
  node: {
    name: '节点',
    types: ['bus'],
  },
  connection: {
    name: '连接',
    types: ['line', 'transformer', 'switch'],
  },
  power: {
    name: '功率',
    types: ['external_grid', 'static_generator', 'storage', 'load', 'charger'],
  },
  measurement: {
    name: '测量',
    types: ['meter'],
  },
};

// 设备类型到中文名称的映射
export const DEVICE_TYPE_TO_CN: Record<DeviceType, string> = Object.fromEntries(
  Object.entries(DEVICE_TYPES).map(([key, value]) => [key, value.name])
) as Record<DeviceType, string>;

// 获取设备类型信息
export function getDeviceTypeInfo(type: DeviceType): DeviceTypeInfo | undefined {
  return DEVICE_TYPES[type];
}

// 连接规则 - 定义哪些设备可以互相连接
export const CONNECTION_RULES: Record<DeviceType, DeviceType[]> = {
  // 母线可以连接的设备类型
  bus: ['line', 'transformer', 'switch', 'static_generator', 'storage', 'load', 'charger', 'meter', 'external_grid'],
  // 线路只能连接母线或开关
  line: ['bus', 'switch', 'meter'],
  // 变压器只能连接母线或开关
  transformer: ['bus', 'switch', 'meter'],
  // 开关可以连接多种设备
  switch: ['bus', 'line', 'transformer', 'meter'],
  // 功率设备只能连接母线
  static_generator: ['bus'],
  storage: ['bus'],
  load: ['bus'],
  charger: ['bus'],
  external_grid: ['bus'],
  // 电表可以串接在线路中
  meter: ['bus', 'line', 'transformer', 'switch'],
};

// 检查两个设备是否可以连接
export function canConnect(sourceType: DeviceType, targetType: DeviceType): boolean {
  const allowedTargets = CONNECTION_RULES[sourceType];
  return allowedTargets?.includes(targetType) ?? false;
}

// 获取连接失败原因
export function getConnectionError(sourceType: DeviceType, targetType: DeviceType): string | null {
  if (sourceType === targetType && sourceType === 'bus') {
    return '母线不能直接连接母线，需要通过线路或变压器';
  }
  if (!canConnect(sourceType, targetType) && !canConnect(targetType, sourceType)) {
    return `${DEVICE_TYPE_TO_CN[sourceType]}不能与${DEVICE_TYPE_TO_CN[targetType]}直接连接`;
  }
  return null;
}
