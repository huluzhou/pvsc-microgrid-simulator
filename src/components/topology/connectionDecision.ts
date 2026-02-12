/**
 * 连接决策逻辑模块
 * 
 * 连接创建分为三个阶段：
 * - 阶段一：前置验证（任一失败则拒绝连接）
 * - 阶段二：创建连接
 * - 阶段三：联动更新
 * 
 * 参考文档：doc/TopoRule.md
 */

import { Node, Edge, Connection } from 'reactflow';
import { DeviceType, getConnectionError } from '../../constants/deviceTypes';

// ============================================================================
// 常量定义
// ============================================================================

/** 功率设备类型列表 */
export const POWER_DEVICE_TYPES: DeviceType[] = [
  'static_generator', 'storage', 'load', 'charger', 'external_grid'
];

/** 连接设备类型列表（有两个端口的设备） */
export const CONNECTION_DEVICE_TYPES: DeviceType[] = [
  'line', 'transformer', 'switch'
];

/** 设备类型到 pandapower 元件类型的映射 */
const ELEMENT_TYPE_MAP: Record<DeviceType, string> = {
  bus: 'bus',
  line: 'line',
  transformer: 'trafo',
  load: 'load',
  static_generator: 'sgen',
  storage: 'storage',
  charger: 'charger',
  external_grid: 'ext_grid',
  switch: 'switch',
  meter: 'meter'
};

// ============================================================================
// 类型定义
// ============================================================================

/** 验证结果 */
export interface ValidationResult {
  valid: boolean;
  reason?: string;
  warning?: string;
}

/** 连接上下文信息 */
interface ConnectionContext {
  connection: Connection;
  sourceNode: Node;
  targetNode: Node;
  sourceType: DeviceType;
  targetType: DeviceType;
  nodes: Node[];
  edges: Edge[];
}

// ============================================================================
// 辅助函数
// ============================================================================

/** 获取节点的现有连接中特定类型设备的数量 */
export function getConnectedDeviceCount(
  nodeId: string,
  targetType: DeviceType,
  nodes: Node[],
  edges: Edge[]
): number {
  return edges.filter(e => {
    const connectedId = e.source === nodeId ? e.target : (e.target === nodeId ? e.source : null);
    if (!connectedId) return false;
    const connectedNode = nodes.find(n => n.id === connectedId);
    return connectedNode?.data.deviceType === targetType;
  }).length;
}

/** 获取节点特定端口的连接数量 */
export function getPortConnectionCount(
  nodeId: string,
  portId: string | null | undefined,
  edges: Edge[]
): number {
  if (!portId) return 0;
  return edges.filter(e => {
    if (e.source === nodeId && e.sourceHandle === portId) return true;
    if (e.target === nodeId && e.targetHandle === portId) return true;
    return false;
  }).length;
}

/** 获取节点的总连接数 */
export function getTotalConnectionCount(nodeId: string, edges: Edge[]): number {
  return edges.filter(e => e.source === nodeId || e.target === nodeId).length;
}

/** 从设备ID中提取索引号 */
function getDeviceIndex(deviceId: string): number {
  const match = deviceId.match(/device-(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

/** 更新节点的 properties 字段 */
function updateNodeProperties(
  nodes: Node[],
  nodeId: string,
  updates: Record<string, unknown>
): Node[] {
  return nodes.map(n =>
    n.id === nodeId
      ? { ...n, data: { ...n.data, properties: { ...n.data.properties, ...updates } } }
      : n
  );
}

/** 清除节点的指定属性 */
function clearNodeProperties(
  nodes: Node[],
  nodeId: string,
  keys: string[]
): Node[] {
  return nodes.map(n => {
    if (n.id !== nodeId) return n;
    const newProperties = { ...n.data.properties };
    keys.forEach(key => delete newProperties[key]);
    return { ...n, data: { ...n.data, properties: newProperties } };
  });
}

// ============================================================================
// 阶段一：前置验证
// ============================================================================

/**
 * 1.1 检查连接是否已存在
 */
function checkDuplicateConnection(ctx: ConnectionContext): ValidationResult {
  const existingConnection = ctx.edges.find(
    (e) =>
      (e.source === ctx.connection.source && e.target === ctx.connection.target) ||
      (e.source === ctx.connection.target && e.target === ctx.connection.source)
  );
  if (existingConnection) {
    return { valid: false, reason: '连接已存在' };
  }
  return { valid: true };
}

/**
 * 1.2 检查设备类型组合是否允许
 */
function checkDeviceTypeCompatibility(ctx: ConnectionContext): ValidationResult {
  // 不允许自连接
  if (ctx.connection.source === ctx.connection.target) {
    return { valid: false, reason: '不允许自连接' };
  }

  // 使用连接规则检查
  const error = getConnectionError(ctx.sourceType, ctx.targetType);
  if (error) {
    return { valid: false, reason: error };
  }
  return { valid: true };
}

/**
 * 1.3 检查端口占用约束
 */
function checkPortConstraints(ctx: ConnectionContext): ValidationResult {
  const { connection, sourceNode, targetNode, sourceType, targetType, nodes, edges } = ctx;

  // 1.3.1 功率设备连接母线数量限制（最多1个）
  if (POWER_DEVICE_TYPES.includes(sourceType) && targetType === 'bus') {
    if (getConnectedDeviceCount(sourceNode.id, 'bus', nodes, edges) >= 1) {
      return { valid: false, reason: `${sourceNode.data.name} 已连接母线，功率设备只能连接1个母线` };
    }
  }
  if (POWER_DEVICE_TYPES.includes(targetType) && sourceType === 'bus') {
    if (getConnectedDeviceCount(targetNode.id, 'bus', nodes, edges) >= 1) {
      return { valid: false, reason: `${targetNode.data.name} 已连接母线，功率设备只能连接1个母线` };
    }
  }

  // 1.3.2 功率设备连接电表数量限制（最多1个）
  if (POWER_DEVICE_TYPES.includes(sourceType) && targetType === 'meter') {
    if (getConnectedDeviceCount(sourceNode.id, 'meter', nodes, edges) >= 1) {
      return { valid: false, reason: `${sourceNode.data.name} 已连接电表，功率设备最多连接1个电表` };
    }
  }
  if (POWER_DEVICE_TYPES.includes(targetType) && sourceType === 'meter') {
    if (getConnectedDeviceCount(targetNode.id, 'meter', nodes, edges) >= 1) {
      return { valid: false, reason: `${targetNode.data.name} 已连接电表，功率设备最多连接1个电表` };
    }
  }

  // 1.3.3 线路/变压器端口只能连接1个母线或开关
  if ((sourceType === 'line' || sourceType === 'transformer') && (targetType === 'bus' || targetType === 'switch')) {
    const portId = connection.sourceHandle;
    if (portId && getPortConnectionCount(sourceNode.id, portId, edges) >= 1) {
      return { valid: false, reason: `${sourceNode.data.name} 的该端口已有连接，每端口只能连接1个母线或开关` };
    }
  }
  if ((targetType === 'line' || targetType === 'transformer') && (sourceType === 'bus' || sourceType === 'switch')) {
    const portId = connection.targetHandle;
    if (portId && getPortConnectionCount(targetNode.id, portId, edges) >= 1) {
      return { valid: false, reason: `${targetNode.data.name} 的该端口已有连接，每端口只能连接1个母线或开关` };
    }
  }

  // 1.3.3.1 开关端口只能连接1个设备（包括母线、线路、变压器）
  // 检查开关的每个连接点是否已有连接
  if (sourceType === 'switch') {
    const portId = connection.sourceHandle;
    if (portId && getPortConnectionCount(sourceNode.id, portId, edges) >= 1) {
      return { valid: false, reason: `${sourceNode.data.name} 的该端口已有连接，开关的每个连接点只能连接1个设备` };
    }
  }
  if (targetType === 'switch') {
    const portId = connection.targetHandle;
    if (portId && getPortConnectionCount(targetNode.id, portId, edges) >= 1) {
      return { valid: false, reason: `${targetNode.data.name} 的该端口已有连接，开关的每个连接点只能连接1个设备` };
    }
  }

  // 1.3.4 电表只能有1条连接
  if (sourceType === 'meter') {
    if (getTotalConnectionCount(sourceNode.id, edges) >= 1) {
      return { valid: false, reason: `${sourceNode.data.name} 已有连接，电表只能有1条连接` };
    }
  }
  if (targetType === 'meter') {
    if (getTotalConnectionCount(targetNode.id, edges) >= 1) {
      return { valid: false, reason: `${targetNode.data.name} 已有连接，电表只能有1条连接` };
    }
  }

  return { valid: true };
}

/**
 * 1.4 检查稳态约束（警告，允许继续）
 */
function checkSteadyStateConstraints(ctx: ConnectionContext): ValidationResult {
  const { sourceNode, targetNode, sourceType, targetType, nodes, edges } = ctx;

  // 开关稳态约束：两端均非母线时警告
  const switchNode = sourceType === 'switch' ? sourceNode : (targetType === 'switch' ? targetNode : null);
  const otherType = sourceType === 'switch' ? targetType : sourceType;

  if (switchNode && otherType !== 'bus') {
    const switchEdges = edges.filter(e => e.source === switchNode.id || e.target === switchNode.id);
    const hasBusConnection = switchEdges.some(e => {
      const connectedNodeId = e.source === switchNode.id ? e.target : e.source;
      const connectedNode = nodes.find(n => n.id === connectedNodeId);
      return connectedNode?.data.deviceType === 'bus';
    });

    if (switchEdges.length >= 1 && !hasBusConnection) {
      return {
        valid: true,
        warning: `警告：开关 ${switchNode.data.name} 将形成两端都不连接母线的闭合连接，稳态运行要求至少一端连接母线`
      };
    }
  }

  return { valid: true };
}

/**
 * 阶段一：执行完整的前置验证
 */
export function validateConnectionPhase1(
  connection: Connection,
  nodes: Node[],
  edges: Edge[]
): ValidationResult {
  const sourceNode = nodes.find(n => n.id === connection.source);
  const targetNode = nodes.find(n => n.id === connection.target);

  if (!sourceNode || !targetNode) {
    return { valid: false, reason: '节点不存在' };
  }

  const ctx: ConnectionContext = {
    connection,
    sourceNode,
    targetNode,
    sourceType: sourceNode.data.deviceType as DeviceType,
    targetType: targetNode.data.deviceType as DeviceType,
    nodes,
    edges
  };

  // 依次执行各项检查
  const checks = [
    checkDuplicateConnection,
    checkDeviceTypeCompatibility,
    checkPortConstraints,
    checkSteadyStateConstraints
  ];

  for (const check of checks) {
    const result = check(ctx);
    if (!result.valid || result.warning) {
      return result;
    }
  }

  return { valid: true };
}

/**
 * 简化版验证（用于实时拖拽反馈，不返回详细信息）
 */
export function isConnectionValid(
  connection: Connection,
  nodes: Node[],
  edges: Edge[]
): boolean {
  const result = validateConnectionPhase1(connection, nodes, edges);
  // 忽略警告，只看 valid
  return result.valid;
}

// ============================================================================
// 阶段三：联动更新
// ============================================================================

/**
 * 3.1 功率设备 ↔ 母线：更新 bus 字段
 */
function linkagePowerDeviceToBus(
  updatedNodes: Node[],
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType
): Node[] {
  if (POWER_DEVICE_TYPES.includes(sourceType) && targetType === 'bus') {
    return updateNodeProperties(updatedNodes, sourceNode.id, { bus: getDeviceIndex(targetNode.id) });
  }
  if (POWER_DEVICE_TYPES.includes(targetType) && sourceType === 'bus') {
    return updateNodeProperties(updatedNodes, targetNode.id, { bus: getDeviceIndex(sourceNode.id) });
  }
  return updatedNodes;
}

/**
 * 从连接点ID中提取基础ID（去除-source后缀）
 */
function getBasePortId(portId: string | null | undefined): string | null {
  if (!portId) return null;
  // 如果包含-source后缀，去除它
  if (portId.endsWith('-source')) {
    return portId.replace('-source', '');
  }
  return portId;
}

/**
 * 3.2 线路 ↔ 母线：更新 from_bus 或 to_bus
 */
function linkageLineToBus(
  updatedNodes: Node[],
  connection: Connection,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType
): Node[] {
  if (sourceType === 'line' && targetType === 'bus') {
    const portId = getBasePortId(connection.sourceHandle);
    if (portId === 'top') {
      return updateNodeProperties(updatedNodes, sourceNode.id, { from_bus: getDeviceIndex(targetNode.id) });
    } else if (portId === 'bottom') {
      return updateNodeProperties(updatedNodes, sourceNode.id, { to_bus: getDeviceIndex(targetNode.id) });
    }
  }
  if (targetType === 'line' && sourceType === 'bus') {
    const portId = getBasePortId(connection.targetHandle);
    if (portId === 'top') {
      return updateNodeProperties(updatedNodes, targetNode.id, { from_bus: getDeviceIndex(sourceNode.id) });
    } else if (portId === 'bottom') {
      return updateNodeProperties(updatedNodes, targetNode.id, { to_bus: getDeviceIndex(sourceNode.id) });
    }
  }
  return updatedNodes;
}

/**
 * 3.3 变压器 ↔ 母线：更新 hv_bus 或 lv_bus
 */
function linkageTransformerToBus(
  updatedNodes: Node[],
  connection: Connection,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType
): Node[] {
  if (sourceType === 'transformer' && targetType === 'bus') {
    const portId = getBasePortId(connection.sourceHandle);
    if (portId === 'top') {
      return updateNodeProperties(updatedNodes, sourceNode.id, { hv_bus: getDeviceIndex(targetNode.id) });
    } else if (portId === 'bottom') {
      return updateNodeProperties(updatedNodes, sourceNode.id, { lv_bus: getDeviceIndex(targetNode.id) });
    }
  }
  if (targetType === 'transformer' && sourceType === 'bus') {
    const portId = getBasePortId(connection.targetHandle);
    if (portId === 'top') {
      return updateNodeProperties(updatedNodes, targetNode.id, { hv_bus: getDeviceIndex(sourceNode.id) });
    } else if (portId === 'bottom') {
      return updateNodeProperties(updatedNodes, targetNode.id, { lv_bus: getDeviceIndex(sourceNode.id) });
    }
  }
  return updatedNodes;
}

/**
 * 将连接点ID映射为side字段值（from_bus/to_bus/hv_bus/lv_bus等）
 */
function mapPortIdToSide(portId: string | null | undefined, deviceType: DeviceType): string | null {
  if (!portId) return null;
  const basePortId = getBasePortId(portId);
  
  // 根据设备类型和连接点映射
  if (deviceType === 'line') {
    if (basePortId === 'top') return 'from_bus';
    if (basePortId === 'bottom') return 'to_bus';
  } else if (deviceType === 'transformer') {
    if (basePortId === 'top') return 'hv_bus';
    if (basePortId === 'bottom') return 'lv_bus';
  } else if (deviceType === 'switch') {
    if (basePortId === 'left') return 'left';
    if (basePortId === 'right') return 'right';
  } else if (deviceType === 'bus') {
    if (basePortId === 'center') return 'center';
  }
  
  // 对于其他设备类型，返回原始连接点ID
  return basePortId;
}

/**
 * 3.4 电表 ↔ 任意设备：更新 element_type, element, side
 */
function linkageMeterToDevice(
  updatedNodes: Node[],
  connection: Connection,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType
): Node[] {
  if (sourceType === 'meter') {
    const side = mapPortIdToSide(connection.targetHandle, targetType);
    return updateNodeProperties(updatedNodes, sourceNode.id, {
      element_type: ELEMENT_TYPE_MAP[targetType] || targetType,
      element: getDeviceIndex(targetNode.id),
      side: side,
    });
  }
  if (targetType === 'meter') {
    const side = mapPortIdToSide(connection.sourceHandle, sourceType);
    return updateNodeProperties(updatedNodes, targetNode.id, {
      element_type: ELEMENT_TYPE_MAP[sourceType] || sourceType,
      element: getDeviceIndex(sourceNode.id),
      side: side,
    });
  }
  return updatedNodes;
}

/**
 * 3.5 开关连接母线：记录开关两端的母线索引，并检查是否需要更新线路/变压器的bus字段
 */
function linkageSwitchToBus(
  updatedNodes: Node[],
  connection: Connection,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType,
  edges: Edge[]
): Node[] {
  // 处理 开关 ↔ 母线 的情况
  if ((sourceType !== 'switch' || targetType !== 'bus') && 
      (sourceType !== 'bus' || targetType !== 'switch')) {
    return updatedNodes;
  }

  const switchNode = sourceType === 'switch' ? sourceNode : targetNode;
  const busNode = sourceType === 'switch' ? targetNode : sourceNode;

  // 获取开关的连接点ID
  const portId = getBasePortId(
    sourceType === 'switch' ? connection.sourceHandle : connection.targetHandle
  );

  // 获取当前连接的母线索引
  const busIndex = getDeviceIndex(busNode.id);

  // 获取开关的所有现有连接
  const switchEdges = edges.filter(e => 
    e.source === switchNode.id || e.target === switchNode.id
  );
  
  // 构建所有连接（包括当前新连接）
  const allConnections: Array<{ nodeId: string; portId: string }> = [];
  
  // 添加现有连接
  for (const edge of switchEdges) {
    const otherId = edge.source === switchNode.id ? edge.target : edge.source;
    const otherPortId = getBasePortId(
      edge.source === switchNode.id ? edge.sourceHandle : edge.targetHandle
    );
    allConnections.push({ nodeId: otherId, portId: otherPortId || '' });
  }
  
  // 添加当前新连接
  allConnections.push({ nodeId: busNode.id, portId: portId || '' });

  // 找出开关连接的所有设备
  const busConnections: Array<{ nodeId: string; busIndex: number }> = [];
  let lineOrTransformerConnection: { nodeId: string; type: DeviceType; index: number } | null = null;
  
  for (const conn of allConnections) {
    const otherNode = updatedNodes.find(n => n.id === conn.nodeId);
    if (!otherNode) continue;
    
    const otherType = otherNode.data.deviceType as DeviceType;
    if (otherType === 'bus') {
      busConnections.push({ nodeId: conn.nodeId, busIndex: getDeviceIndex(conn.nodeId) });
    } else if (otherType === 'line' || otherType === 'transformer') {
      lineOrTransformerConnection = {
        nodeId: conn.nodeId,
        type: otherType,
        index: getDeviceIndex(conn.nodeId)
      };
    }
  }

  // 获取开关的现有属性
  const currentSwitchProps = switchNode.data.properties || {};
  const existingBus = currentSwitchProps.bus;

  // 更新开关的属性
  const switchUpdates: Record<string, any> = {};
  
  if (lineOrTransformerConnection) {
    // 开关一端是母线，一端是线路/变压器
    // bus: 母线的索引（第一个连接的母线）
    // element_type: 'line' 或 'trafo'
    // element: 线路/变压器的索引
    if (busConnections.length > 0) {
      // 如果已有bus属性，保持；否则使用第一个母线
      switchUpdates.bus = existingBus !== undefined ? existingBus : busConnections[0].busIndex;
    } else if (existingBus !== undefined) {
      switchUpdates.bus = existingBus;
    }
    switchUpdates.element_type = lineOrTransformerConnection.type === 'line' ? 'line' : 'trafo';
    switchUpdates.element = lineOrTransformerConnection.index;
  } else if (busConnections.length >= 2) {
    // 开关两端都是母线
    // bus: 第一次连接的母线索引（如果已有bus属性则保持，否则使用第一个）
    // element_type: 'bus'
    // element: 第二次连接的母线索引（另一个母线）
    if (existingBus !== undefined) {
      // 如果已有bus属性，保持它，element设置为另一个母线
      switchUpdates.bus = existingBus;
      const otherBus = busConnections.find(b => b.busIndex !== existingBus);
      if (otherBus) {
        switchUpdates.element_type = 'bus';
        switchUpdates.element = otherBus.busIndex;
      }
    } else {
      // 如果没有bus属性，第一个连接的母线作为bus，第二个作为element
      switchUpdates.bus = busConnections[0].busIndex;
      switchUpdates.element_type = 'bus';
      switchUpdates.element = busConnections[1].busIndex;
    }
  } else if (busConnections.length === 1) {
    // 开关只连接了一个母线（当前新连接）
    // 如果已有bus属性，说明这是第二个母线，设置element_type='bus', element=当前母线索引
    // 如果没有bus属性，这是第一个母线，设置bus=当前母线索引
    if (existingBus !== undefined) {
      // 这是第二个母线
      switchUpdates.bus = existingBus;
      switchUpdates.element_type = 'bus';
      switchUpdates.element = busConnections[0].busIndex;
    } else {
      // 这是第一个母线
      switchUpdates.bus = busConnections[0].busIndex;
    }
  }

  if (Object.keys(switchUpdates).length > 0) {
    updatedNodes = updateNodeProperties(updatedNodes, switchNode.id, switchUpdates);
  }

  // 检查开关另一端是否连接了线路/变压器，如果是，更新它们空缺的bus字段
  for (const edge of switchEdges) {
    const otherId = edge.source === switchNode.id ? edge.target : edge.source;
    const otherNode = updatedNodes.find(n => n.id === otherId);
    
    if (!otherNode) continue;
    
    const otherType = otherNode.data.deviceType as DeviceType;
    
    if (otherType === 'line' || otherType === 'transformer') {
      // 获取线路/变压器的端口ID（不是开关的端口ID）
      // 如果edge.source是开关，那么edge.targetHandle是线路/变压器的端口
      // 如果edge.target是开关，那么edge.sourceHandle是线路/变压器的端口
      const otherPortId = getBasePortId(
        edge.source === switchNode.id ? edge.targetHandle : edge.sourceHandle
      );
      
      if (otherType === 'line') {
        // 只更新空缺的bus字段
        const currentProps = otherNode.data.properties || {};
        if (otherPortId === 'top' && !currentProps.from_bus) {
          updatedNodes = updateNodeProperties(updatedNodes, otherId, { from_bus: busIndex });
        } else if (otherPortId === 'bottom' && !currentProps.to_bus) {
          updatedNodes = updateNodeProperties(updatedNodes, otherId, { to_bus: busIndex });
        }
      } else if (otherType === 'transformer') {
        // 只更新空缺的bus字段
        const currentProps = otherNode.data.properties || {};
        if (otherPortId === 'top' && !currentProps.hv_bus) {
          updatedNodes = updateNodeProperties(updatedNodes, otherId, { hv_bus: busIndex });
        } else if (otherPortId === 'bottom' && !currentProps.lv_bus) {
          updatedNodes = updateNodeProperties(updatedNodes, otherId, { lv_bus: busIndex });
        }
      }
    }
  }

  return updatedNodes;
}

/**
 * 3.6 开关连接线路/变压器：记录开关的连接元件类型和索引
 * 如果开关另一端已连接母线，同时记录bus属性
 */
function linkageSwitchToLineOrTransformer(
  updatedNodes: Node[],
  _connection: Connection,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType,
  edges: Edge[]
): Node[] {
  // 处理 开关 ↔ 线路/变压器 的情况
  const switchNode = sourceType === 'switch' ? sourceNode : (targetType === 'switch' ? targetNode : null);
  const connectedNode = sourceType === 'switch' ? targetNode : sourceNode;
  const connectedType = sourceType === 'switch' ? targetType : sourceType;

  if (!switchNode || (connectedType !== 'line' && connectedType !== 'transformer')) {
    return updatedNodes;
  }

  // 获取开关的所有现有连接
  const switchEdges = edges.filter(e => 
    e.source === switchNode.id || e.target === switchNode.id
  );

  // 检查开关另一端是否连接了母线
  let connectedBusId: string | null = null;
  for (const edge of switchEdges) {
    const otherId = edge.source === switchNode.id ? edge.target : edge.source;
    const otherNode = updatedNodes.find(n => n.id === otherId);
    if (otherNode?.data.deviceType === 'bus') {
      connectedBusId = otherId;
      break;
    }
  }

  // 记录开关的连接元件类型和索引
  const elementType = connectedType === 'line' ? 'line' : 'trafo';
  const elementIndex = getDeviceIndex(connectedNode.id);
  
  // 更新开关的属性
  const switchUpdates: Record<string, any> = {
    element_type: elementType,
    element: elementIndex,
  };

  // 如果开关另一端已连接母线，记录bus属性
  if (connectedBusId) {
    switchUpdates.bus = getDeviceIndex(connectedBusId);
  }
  
  return updateNodeProperties(updatedNodes, switchNode.id, switchUpdates);
}

/**
 * 3.7 开关闭合连接联动：检查开关是否形成"母线—线路/变压器"闭合
 */
function linkageSwitchClosure(
  updatedNodes: Node[],
  connection: Connection,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType,
  edges: Edge[]
): Node[] {
  // 只处理 开关 ↔ 线路/变压器 的情况
  const switchNode = sourceType === 'switch' ? sourceNode : (targetType === 'switch' ? targetNode : null);
  const connectedNode = sourceType === 'switch' ? targetNode : sourceNode;
  const connectedType = sourceType === 'switch' ? targetType : sourceType;

  if (!switchNode || (connectedType !== 'line' && connectedType !== 'transformer')) {
    return updatedNodes;
  }

  // 找到开关的所有连接（不包括即将创建的新连接）
  const switchEdges = edges.filter(e => e.source === switchNode.id || e.target === switchNode.id);

  // 检查开关另一端是否连接了母线
  let connectedBusId: string | null = null;
  for (const edge of switchEdges) {
    const otherId = edge.source === switchNode.id ? edge.target : edge.source;
    const otherNode = updatedNodes.find(n => n.id === otherId);
    if (otherNode?.data.deviceType === 'bus') {
      connectedBusId = otherId;
      break;
    }
  }

  // 如果开关另一端连接了母线，更新线路/变压器的空缺bus字段
  if (connectedBusId) {
    const busIndex = getDeviceIndex(connectedBusId);
    const portId = getBasePortId(
      connection.source === connectedNode.id
        ? connection.sourceHandle
        : connection.targetHandle
    );

    const currentProps = connectedNode.data.properties || {};

    if (connectedType === 'line') {
      // 只更新空缺的bus字段
      if (portId === 'top' && !currentProps.from_bus) {
        return updateNodeProperties(updatedNodes, connectedNode.id, { from_bus: busIndex });
      } else if (portId === 'bottom' && !currentProps.to_bus) {
        return updateNodeProperties(updatedNodes, connectedNode.id, { to_bus: busIndex });
      }
    } else if (connectedType === 'transformer') {
      // 只更新空缺的bus字段
      if (portId === 'top' && !currentProps.hv_bus) {
        return updateNodeProperties(updatedNodes, connectedNode.id, { hv_bus: busIndex });
      } else if (portId === 'bottom' && !currentProps.lv_bus) {
        return updateNodeProperties(updatedNodes, connectedNode.id, { lv_bus: busIndex });
      }
    }
  }

  return updatedNodes;
}

/**
 * 阶段三：执行完整的联动更新
 */
export function performLinkageUpdatePhase3(
  connection: Connection,
  nodes: Node[],
  edges: Edge[]
): Node[] {
  const sourceNode = nodes.find(n => n.id === connection.source);
  const targetNode = nodes.find(n => n.id === connection.target);
  if (!sourceNode || !targetNode) return nodes;

  const sourceType = sourceNode.data.deviceType as DeviceType;
  const targetType = targetNode.data.deviceType as DeviceType;

  let updatedNodes = [...nodes];

  // 依次执行各项联动更新
  updatedNodes = linkagePowerDeviceToBus(updatedNodes, sourceNode, targetNode, sourceType, targetType);
  updatedNodes = linkageLineToBus(updatedNodes, connection, sourceNode, targetNode, sourceType, targetType);
  updatedNodes = linkageTransformerToBus(updatedNodes, connection, sourceNode, targetNode, sourceType, targetType);
  updatedNodes = linkageMeterToDevice(updatedNodes, connection, sourceNode, targetNode, sourceType, targetType);
  updatedNodes = linkageSwitchToBus(updatedNodes, connection, sourceNode, targetNode, sourceType, targetType, edges);
  updatedNodes = linkageSwitchToLineOrTransformer(updatedNodes, connection, sourceNode, targetNode, sourceType, targetType, edges);
  updatedNodes = linkageSwitchClosure(updatedNodes, connection, sourceNode, targetNode, sourceType, targetType, edges);

  return updatedNodes;
}

// ============================================================================
// 连接删除：反向联动
// ============================================================================

/**
 * 反向联动：功率设备 ↔ 母线
 */
function reverseLinkagePowerDeviceToBus(
  updatedNodes: Node[],
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType
): Node[] {
  if (POWER_DEVICE_TYPES.includes(sourceType) && targetType === 'bus') {
    return clearNodeProperties(updatedNodes, sourceNode.id, ['bus']);
  }
  if (POWER_DEVICE_TYPES.includes(targetType) && sourceType === 'bus') {
    return clearNodeProperties(updatedNodes, targetNode.id, ['bus']);
  }
  return updatedNodes;
}

/**
 * 反向联动：线路 ↔ 母线
 */
function reverseLinkageLineToBus(
  updatedNodes: Node[],
  deletedEdge: Edge,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType
): Node[] {
  if (sourceType === 'line' && targetType === 'bus') {
    const portId = getBasePortId(deletedEdge.sourceHandle);
    if (portId === 'top') {
      return clearNodeProperties(updatedNodes, sourceNode.id, ['from_bus']);
    } else if (portId === 'bottom') {
      return clearNodeProperties(updatedNodes, sourceNode.id, ['to_bus']);
    }
  }
  if (targetType === 'line' && sourceType === 'bus') {
    const portId = getBasePortId(deletedEdge.targetHandle);
    if (portId === 'top') {
      return clearNodeProperties(updatedNodes, targetNode.id, ['from_bus']);
    } else if (portId === 'bottom') {
      return clearNodeProperties(updatedNodes, targetNode.id, ['to_bus']);
    }
  }
  return updatedNodes;
}

/**
 * 反向联动：变压器 ↔ 母线
 */
function reverseLinkageTransformerToBus(
  updatedNodes: Node[],
  deletedEdge: Edge,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType
): Node[] {
  if (sourceType === 'transformer' && targetType === 'bus') {
    const portId = getBasePortId(deletedEdge.sourceHandle);
    if (portId === 'top') {
      return clearNodeProperties(updatedNodes, sourceNode.id, ['hv_bus']);
    } else if (portId === 'bottom') {
      return clearNodeProperties(updatedNodes, sourceNode.id, ['lv_bus']);
    }
  }
  if (targetType === 'transformer' && sourceType === 'bus') {
    const portId = getBasePortId(deletedEdge.targetHandle);
    if (portId === 'top') {
      return clearNodeProperties(updatedNodes, targetNode.id, ['hv_bus']);
    } else if (portId === 'bottom') {
      return clearNodeProperties(updatedNodes, targetNode.id, ['lv_bus']);
    }
  }
  return updatedNodes;
}

/**
 * 反向联动：电表
 */
function reverseLinkageMeter(
  updatedNodes: Node[],
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType
): Node[] {
  if (sourceType === 'meter') {
    return clearNodeProperties(updatedNodes, sourceNode.id, ['element_type', 'element', 'side']);
  }
  if (targetType === 'meter') {
    return clearNodeProperties(updatedNodes, targetNode.id, ['element_type', 'element', 'side']);
  }
  return updatedNodes;
}

/**
 * 反向联动：开关连接母线
 */
function reverseLinkageSwitchToBus(
  updatedNodes: Node[],
  _deletedEdge: Edge,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType,
  _edges: Edge[]
): Node[] {
  // 处理 开关 ↔ 母线 的情况
  if ((sourceType !== 'switch' || targetType !== 'bus') && 
      (sourceType !== 'bus' || targetType !== 'switch')) {
    return updatedNodes;
  }

  const switchNode = sourceType === 'switch' ? sourceNode : targetNode;
  const deletedBusIndex = getDeviceIndex(sourceType === 'switch' ? targetNode.id : sourceNode.id);

  // 获取开关的现有属性
  const currentProps = switchNode.data.properties || {};
  const currentBus = currentProps.bus;
  const currentElement = currentProps.element;
  const currentElementType = currentProps.element_type;

  // 如果删除的是bus属性对应的母线
  if (currentBus === deletedBusIndex) {
    // 如果element_type是'bus'，说明两端都是母线，将element提升为bus
    if (currentElementType === 'bus' && currentElement !== undefined) {
      return updateNodeProperties(updatedNodes, switchNode.id, {
        bus: currentElement,
        element_type: undefined,
        element: undefined,
      });
    } else {
      // 否则清除bus属性
      return clearNodeProperties(updatedNodes, switchNode.id, ['bus']);
    }
  }
  
  // 如果删除的是element对应的母线（element_type='bus'）
  if (currentElementType === 'bus' && currentElement === deletedBusIndex) {
    // 只清除element和element_type，保留bus
    return clearNodeProperties(updatedNodes, switchNode.id, ['element_type', 'element']);
  }

  return updatedNodes;
}

/**
 * 反向联动：开关连接线路/变压器
 */
function reverseLinkageSwitchToLineOrTransformer(
  updatedNodes: Node[],
  deletedEdge: Edge,
  sourceNode: Node,
  targetNode: Node,
  sourceType: DeviceType,
  targetType: DeviceType,
  edges: Edge[]
): Node[] {
  // 处理 开关 ↔ 线路/变压器 的情况
  const switchNode = sourceType === 'switch' ? sourceNode : (targetType === 'switch' ? targetNode : null);
  const connectedType = sourceType === 'switch' ? targetType : sourceType;

  if (!switchNode || (connectedType !== 'line' && connectedType !== 'transformer')) {
    return updatedNodes;
  }

  // 获取开关的剩余连接（排除被删除的连接）
  const remainingEdges = edges.filter(e => 
    (e.source === switchNode.id || e.target === switchNode.id) &&
    !(e.source === deletedEdge.source && e.target === deletedEdge.target)
  );

  // 检查开关另一端是否还有母线连接
  let hasBusConnection = false;
  let busIndex: number | null = null;
  for (const edge of remainingEdges) {
    const otherId = edge.source === switchNode.id ? edge.target : edge.source;
    const otherNode = updatedNodes.find(n => n.id === otherId);
    if (otherNode?.data.deviceType === 'bus') {
      hasBusConnection = true;
      busIndex = getDeviceIndex(otherId);
      break;
    }
  }

  // 如果还有母线连接，保留bus属性，只清除element_type和element
  // 如果没有母线连接，清除所有属性
  if (hasBusConnection && busIndex !== null) {
    return updateNodeProperties(updatedNodes, switchNode.id, {
      bus: busIndex,
      element_type: undefined,
      element: undefined,
    });
  } else {
    return clearNodeProperties(updatedNodes, switchNode.id, ['bus', 'element_type', 'element']);
  }
}

/**
 * 连接删除时执行反向联动
 */
export function performReverseLinkage(
  deletedEdge: Edge,
  nodes: Node[],
  edges: Edge[]
): Node[] {
  const sourceNode = nodes.find(n => n.id === deletedEdge.source);
  const targetNode = nodes.find(n => n.id === deletedEdge.target);
  if (!sourceNode || !targetNode) return nodes;

  const sourceType = sourceNode.data.deviceType as DeviceType;
  const targetType = targetNode.data.deviceType as DeviceType;

  let updatedNodes = [...nodes];

  // 依次执行各项反向联动
  updatedNodes = reverseLinkagePowerDeviceToBus(updatedNodes, sourceNode, targetNode, sourceType, targetType);
  updatedNodes = reverseLinkageLineToBus(updatedNodes, deletedEdge, sourceNode, targetNode, sourceType, targetType);
  updatedNodes = reverseLinkageTransformerToBus(updatedNodes, deletedEdge, sourceNode, targetNode, sourceType, targetType);
  updatedNodes = reverseLinkageMeter(updatedNodes, sourceNode, targetNode, sourceType, targetType);
  updatedNodes = reverseLinkageSwitchToBus(updatedNodes, deletedEdge, sourceNode, targetNode, sourceType, targetType, edges);
  updatedNodes = reverseLinkageSwitchToLineOrTransformer(updatedNodes, deletedEdge, sourceNode, targetNode, sourceType, targetType, edges);

  // 注意：开关闭合连接的反向联动较为复杂，暂不自动处理

  return updatedNodes;
}
