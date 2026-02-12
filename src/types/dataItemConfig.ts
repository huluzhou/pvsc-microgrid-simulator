/**
 * 数据项显示/解析配置 - 单位换算与方向
 * 默认：功率 kW、电量 kWh，方向流入为正、流出为负（国际学术标准）
 */

/** 数据项单位类型 */
export type DataItemUnit = 'W' | 'kW' | 'MW' | 'Wh' | 'kWh' | 'MWh' | 'custom';

/** 数据项显示/解析配置 */
export interface DataItemDisplayConfig {
  /** 单位：预设或自定义。默认功率 kW、电量 kWh */
  unit?: DataItemUnit;
  /** 自定义：原始值 * scaleToStandard = 标准单位（如 kW） */
  scaleToStandard?: number;
  /** 手动取反，用于校正与默认方向相反的数据源 */
  invertDirection?: boolean;
  /** 预设约定（可选）：默认 inflow_positive（流入为正流出为负） */
  convention?: string;
}

/** 单位到标准 kW/kWh 的换算系数 */
const UNIT_TO_STANDARD: Record<DataItemUnit, number> = {
  W: 0.001,
  kW: 1,
  MW: 1000,
  Wh: 0.001,
  kWh: 1,
  MWh: 1000,
  custom: 1,
};

/** 根据配置获取换算系数，输出为标准单位（功率 kW / 电量 kWh） */
export function getScaleFactor(config?: DataItemDisplayConfig | null): number {
  if (!config) return 1;
  if (config.unit === 'custom' && config.scaleToStandard != null) {
    return config.scaleToStandard;
  }
  return config.unit ? UNIT_TO_STANDARD[config.unit] ?? 1 : 1;
}

/** 根据配置获取方向符号 */
export function getDirectionSign(config?: DataItemDisplayConfig | null): number {
  return config?.invertDirection ? -1 : 1;
}

/** 应用配置转换原始值 */
export function transformValue(value: number, config?: DataItemDisplayConfig | null): number {
  const scale = getScaleFactor(config);
  const sign = getDirectionSign(config);
  return value * scale * sign;
}
