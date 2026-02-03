/**
 * 监控/看板共用：设备数据项配置、数据项解析、概览计算、功率格式化
 * 与 pandapower res_* 列名一致
 */

export interface DataItemDef {
  key: string;
  label: string;
  unit?: string;
}

export const DEVICE_DATA_ITEMS: Record<string, DataItemDef[]> = {
  bus: [
    { key: 'vm_pu', label: '电压 (pu)', unit: 'pu' },
    { key: 'p_mw', label: '有功功率 (MW)', unit: 'MW' },
    { key: 'q_mvar', label: '无功功率 (MVar)', unit: 'MVar' },
  ],
  line: [
    { key: 'p_from_mw', label: '首端有功 (MW)', unit: 'MW' },
    { key: 'q_from_mvar', label: '首端无功 (MVar)', unit: 'MVar' },
    { key: 'p_to_mw', label: '末端有功 (MW)', unit: 'MW' },
    { key: 'q_to_mvar', label: '末端无功 (MVar)', unit: 'MVar' },
    { key: 'pl_mw', label: '有功损耗 (MW)', unit: 'MW' },
    { key: 'ql_mvar', label: '无功损耗 (MVar)', unit: 'MVar' },
    { key: 'loading_percent', label: '负载率 (%)', unit: '%' },
  ],
  switch: [
    { key: 'p_from_mw', label: '首端有功 (MW)', unit: 'MW' },
    { key: 'q_from_mvar', label: '首端无功 (MVar)', unit: 'MVar' },
    { key: 'p_to_mw', label: '末端有功 (MW)', unit: 'MW' },
    { key: 'q_to_mvar', label: '末端无功 (MVar)', unit: 'MVar' },
    { key: 'i_ka', label: '电流 (kA)', unit: 'kA' },
    { key: 'loading_percent', label: '负载率 (%)', unit: '%' },
  ],
  load: [
    { key: 'p_mw', label: '有功功率 (MW)', unit: 'MW' },
    { key: 'q_mvar', label: '无功功率 (MVar)', unit: 'MVar' },
  ],
  charger: [
    { key: 'p_mw', label: '有功功率 (MW)', unit: 'MW' },
    { key: 'q_mvar', label: '无功功率 (MVar)', unit: 'MVar' },
  ],
  static_generator: [
    { key: 'p_mw', label: '有功功率 (MW)', unit: 'MW' },
    { key: 'q_mvar', label: '无功功率 (MVar)', unit: 'MVar' },
  ],
  external_grid: [
    { key: 'p_mw', label: '有功功率 (MW)', unit: 'MW' },
    { key: 'q_mvar', label: '无功功率 (MVar)', unit: 'MVar' },
  ],
  transformer: [
    { key: 'p_hv_mw', label: '高压侧有功 (MW)', unit: 'MW' },
    { key: 'q_hv_mvar', label: '高压侧无功 (MVar)', unit: 'MVar' },
    { key: 'p_lv_mw', label: '低压侧有功 (MW)', unit: 'MW' },
    { key: 'q_lv_mvar', label: '低压侧无功 (MVar)', unit: 'MVar' },
    { key: 'pl_mw', label: '损耗有功 (MW)', unit: 'MW' },
    { key: 'ql_mvar', label: '损耗无功 (MVar)', unit: 'MVar' },
    { key: 'i_hv_ka', label: '高压侧电流 (kA)', unit: 'kA' },
    { key: 'i_lv_ka', label: '低压侧电流 (kA)', unit: 'kA' },
    { key: 'loading_percent', label: '负载率 (%)', unit: '%' },
  ],
  storage: [
    { key: 'p_mw', label: '有功功率 (MW)', unit: 'MW' },
    { key: 'q_mvar', label: '无功功率 (MVar)', unit: 'MVar' },
  ],
};

/** 设备项（用于 getDataItemsForDevice 的 devices 参数） */
export interface DeviceItemForDataItems {
  device_id: string;
  device_type: string;
}

/** 电表数据项完全依赖其指向的设备类型 */
export function getDataItemsForDevice(
  deviceType: string,
  targetDeviceId?: string | null,
  devices?: DeviceItemForDataItems[]
): DataItemDef[] {
  const effectiveType =
    deviceType === 'meter' && targetDeviceId && devices?.length
      ? (devices.find((d) => d.device_id === targetDeviceId)?.device_type ?? 'load')
      : deviceType;
  return DEVICE_DATA_ITEMS[effectiveType] ?? DEVICE_DATA_ITEMS.load ?? [];
}

/** 安全格式化功率显示 */
export function formatPowerKw(value: number | null | undefined): string {
  if (value == null || typeof value !== 'number' || Number.isNaN(value)) return '-';
  return Number(value).toFixed(1);
}

export interface DeviceForOverview {
  device_type: string;
  active_power?: number | null;
  is_online?: boolean;
}

export interface SystemOverview {
  totalDevices: number;
  onlineDevices: number;
  totalGeneration: number;
  totalConsumption: number;
  gridExchange: number;
}

/** 总发电/总消耗/电网交换：与监控页公式一致，供监控与看板共用 */
export function computeOverview(list: DeviceForOverview[]): SystemOverview {
  const onlineDevices = list.filter((d) => d.is_online !== false).length;
  // 正为流入：储能正值=充电，储能负值=放电
  // 总发电 = 光伏正值 + 储能负值（放电部分）
  const pvSum = list
    .filter((d) => d.device_type === 'static_generator' && d.active_power != null)
    .reduce((sum, d) => sum + (Number(d.active_power) || 0), 0);
  const storageDischargeSum = list
    .filter((d) => d.device_type === 'storage' && d.active_power != null)
    .reduce((sum, d) => {
      const p = Number(d.active_power) || 0;
      return sum + (p < 0 ? -p : 0);
    }, 0);
  const totalGeneration = pvSum + storageDischargeSum;
  // 总消耗 = 负载 + 充电桩 + 储能正值（充电部分）
  const loadChargerSum = list
    .filter((d) => ['load', 'charger'].includes(d.device_type) && d.active_power != null)
    .reduce((sum, d) => sum + (Number(d.active_power) || 0), 0);
  const storageChargingSum = list
    .filter((d) => d.device_type === 'storage' && d.active_power != null)
    .reduce((sum, d) => {
      const p = Number(d.active_power) || 0;
      return sum + (p > 0 ? p : 0);
    }, 0);
  const totalConsumption = loadChargerSum + storageChargingSum;
  const gridExchange = list
    .filter((d) => d.device_type === 'external_grid' && d.active_power != null)
    .reduce((sum, d) => sum + (Number(d.active_power) || 0), 0);
  return {
    totalDevices: list.length,
    onlineDevices,
    totalGeneration,
    totalConsumption,
    gridExchange,
  };
}
