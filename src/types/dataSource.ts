/**
 * 数据源相关类型定义
 */

// 数据源类型
export type DataSourceType = 'random' | 'manual' | 'historical';

// 功率单位
export type PowerUnit = 'W' | 'kW' | 'MW';

// 手动设定值
export interface ManualSetpoint {
  activePower: number;      // 有功功率 (kW)
  reactivePower: number;    // 无功功率 (kVar)
}

// 随机数据源配置
export interface RandomConfig {
  minPower: number;         // 最小功率 (kW)
  maxPower: number;         // 最大功率 (kW)
  updateInterval: number;   // 更新间隔 (秒)
  volatility: number;       // 波动率 (0-1)
}

// 列数据源 - 定义CSV中的一列及其单位
export interface ColumnSource {
  columnName: string;       // 列名
  unit: PowerUnit;          // 单位
}

// 负载计算配置 - 用于从其他数据计算负载
// 公式: 负载 = 关口电表(下网) + 光伏发电 - 储能充电 - 充电桩充电
// 正数约定: 关口电表正=下网, 光伏正=发电, 储能正=充电, 充电桩正=充电, 负载正=用电
export interface LoadCalculation {
  gridMeter: ColumnSource;      // 关口电表功率列
  pvGeneration?: ColumnSource;  // 光伏发电功率列(可选)
  storagePower?: ColumnSource;  // 储能功率列(可选)
  chargerPower?: ColumnSource;  // 充电桩功率列(可选)
}

// 历史数据源类型
export type HistoricalSourceType = 'csv' | 'sqlite';

// 历史数据源配置
export interface HistoricalConfig {
  sourceType: HistoricalSourceType;  // 数据源类型
  filePath: string;         // 文件路径（CSV 或 SQLite）
  timeColumn: string;       // 时间列名（CSV 用）
  timeFormat: string;       // 时间格式 (如 %Y-%m-%d %H:%M:%S)（CSV 用）
  powerColumn?: ColumnSource;    // 功率数据列(直接使用，CSV 非负载设备)
  loadCalculation?: LoadCalculation;  // 负载计算配置(用于负载设备，CSV)
  sourceDeviceId?: string;  // SQLite 中的源设备 ID
  startTime?: number;       // 数据起始时间（Unix 秒）
  endTime?: number;         // 数据结束时间（Unix 秒）
  playbackSpeed: number;    // 回放速度倍率
  loop: boolean;            // 是否循环播放
}

// 设备级仿真参数
export interface DeviceSimParams {
  samplingIntervalMs: number;     // 采集频率（毫秒），0 = 每步更新
  responseDelayMs: number;        // 响应延迟（毫秒），0 = 无延迟
  measurementErrorPct: number;    // 测量误差百分比，0 = 无误差
}

// 设备控制配置
export interface DeviceControlConfig {
  deviceId: string;         // 设备ID
  dataSourceType: DataSourceType;  // 数据源类型
  manualSetpoint?: ManualSetpoint;
  randomConfig?: RandomConfig;
  historicalConfig?: HistoricalConfig;
}

// 批量设置配置
export interface BatchSetConfig {
  deviceIds: string[];      // 选中的设备ID列表
  dataSourceType: DataSourceType;
  config: ManualSetpoint | RandomConfig | HistoricalConfig;
}

// 功率单位转换
export function convertPower(value: number, fromUnit: PowerUnit, toUnit: PowerUnit): number {
  const toKw: Record<PowerUnit, number> = {
    'W': 0.001,
    'kW': 1,
    'MW': 1000,
  };
  const kwValue = value * toKw[fromUnit];
  return kwValue / toKw[toUnit];
}

// 获取单位显示文本
export function getUnitLabel(unit: PowerUnit): string {
  return unit;
}

// 数据源类型显示名称
export const DATA_SOURCE_TYPE_NAMES: Record<DataSourceType, string> = {
  random: '随机数据',
  manual: '手动设置',
  historical: '历史数据',
};
