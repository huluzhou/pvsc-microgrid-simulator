// 设备类型定义
// 将在后续阶段完善

export type DeviceType = 
  | "node"      // 节点设备：母线
  | "line"      // 连接设备：线路
  | "transformer" // 连接设备：变压器
  | "switch"    // 连接设备：开关
  | "pv"        // 功率设备：光伏
  | "storage"   // 功率设备：储能
  | "load"      // 功率设备：负载
  | "charger"   // 功率设备：充电桩
  | "meter";    // 测量设备：电表

export type WorkMode = 
  | "random_data"    // 随机数据模式
  | "manual"         // 手动模式
  | "remote"         // 远程模式
  | "historical_data"; // 历史数据模式

export interface DeviceMetadata {
  id: string;
  name: string;
  type: DeviceType;
  properties: Record<string, any>;
  connections: string[];
  workMode?: WorkMode;
}
