/**
 * Modbus 四类寄存器与 v1.5.0 预定义寄存器（按设备类型）
 * 每类设备的寄存器设置是固定的：每个输入寄存器有更新逻辑，每个保持寄存器有命令逻辑。
 * 类型：Coils / Discrete Inputs / Input Registers / Holding Registers
 */

export type ModbusRegisterType =
  | 'coils'
  | 'discrete_inputs'
  | 'input_registers'
  | 'holding_registers';

export interface RegisterEntry {
  address: number;
  value: number; // Coils/Discrete: 0|1; Input/Holding: 16-bit
  type: ModbusRegisterType;
  name?: string;
  /** 语义键，参与仿真更新或 HR 命令的寄存器有值，用于可配置地址 */
  key?: string;
}

const REG_TYPES: ModbusRegisterType[] = [
  'coils',
  'discrete_inputs',
  'input_registers',
  'holding_registers',
];

export const MODBUS_REGISTER_TYPE_LABELS: Record<ModbusRegisterType, string> = {
  coils: '线圈 (Coils)',
  discrete_inputs: '离散输入 (Discrete Inputs)',
  input_registers: '输入寄存器 (Input Registers)',
  holding_registers: '保持寄存器 (Holding Registers)',
};

/**
 * v1.5.0 meter: Input Registers 0,1,2,3,4,5,6,7,8,9,20,10,11
 * - 有功功率(0)、无功功率(20)：int16 有符号，单位 0.5 kW，寄存器值 = 实际(kW) × 2
 * - 四象限电量(7,8,10,11)与组合有功总电能(9)：由 P/Q 积分得到，单位 kWh，寄存器单位 1 kWh；前端显示时用 0.1 kWh 单位
 * - 视在功率 S=√(P²+Q²)，总电能(9)为有功累计（上网+下网），单位 kWh
 */
function getMeterDefaults(): RegisterEntry[] {
  return [
    { address: 0, value: 0, type: 'input_registers', name: '当前有功功率(int16,0.5kW)', key: 'active_power' },
    { address: 1, value: 220, type: 'input_registers', name: 'A相电压' },
    { address: 2, value: 220, type: 'input_registers', name: 'B相电压' },
    { address: 3, value: 220, type: 'input_registers', name: 'C相电压' },
    { address: 4, value: 0, type: 'input_registers', name: 'A相电流' },
    { address: 5, value: 0, type: 'input_registers', name: 'B相电流' },
    { address: 6, value: 0, type: 'input_registers', name: 'C相电流' },
    { address: 7, value: 0, type: 'input_registers', name: '四象限-有功导出(上网,kWh)' },
    { address: 8, value: 0, type: 'input_registers', name: '四象限-有功导入(下网,kWh)' },
    { address: 9, value: 0, type: 'input_registers', name: '组合有功总电能(kWh)' },
    { address: 10, value: 0, type: 'input_registers', name: '四象限-无功导出(kVarh)' },
    { address: 11, value: 0, type: 'input_registers', name: '四象限-无功导入(kVarh)' },
    { address: 20, value: 0, type: 'input_registers', name: '无功功率(int16,0.5kW)', key: 'reactive_power' },
  ];
}

/** v1.5.0 static_generator: HR 5005,5007,5038,5040,5041; IR 5001,5003,5004,5030-5033 */
function getStaticGeneratorDefaults(): RegisterEntry[] {
  return [
    { address: 5005, value: 1, type: 'holding_registers', name: '开关机', key: 'on_off' },
    { address: 5007, value: 100, type: 'holding_registers', name: '有功功率百分比限制', key: 'power_limit_pct' },
    { address: 5038, value: 0x7fff, type: 'holding_registers', name: '有功功率限制', key: 'power_limit_raw' },
    { address: 5040, value: 0, type: 'holding_registers', name: '无功补偿百分比', key: 'reactive_comp_pct' },
    { address: 5041, value: 0, type: 'holding_registers', name: '功率因数', key: 'power_factor' },
    { address: 5001, value: 0, type: 'input_registers', name: '额定功率' },
    { address: 5003, value: 0, type: 'input_registers', name: '今日发电量' },
    { address: 5004, value: 0, type: 'input_registers', name: '总发电量' },
    { address: 5030, value: 0, type: 'input_registers', name: '当前有功功率(低)', key: 'active_power_low' },
    { address: 5031, value: 0, type: 'input_registers', name: '当前有功功率(高)', key: 'active_power_high' },
    { address: 5032, value: 0, type: 'input_registers', name: '无功功率(低)', key: 'reactive_power_low' },
    { address: 5033, value: 0, type: 'input_registers', name: '无功功率(高)', key: 'reactive_power_high' },
  ];
}

/** v1.5.0 storage: HR 4,55,5095,5033; IR 0,2,8,9,12,39-43,400,408-414,420-421,426-432,839,900+ */
function getStorageDefaults(): RegisterEntry[] {
  return [
    { address: 4, value: 0, type: 'holding_registers', name: '设置功率', key: 'set_power' },
    { address: 55, value: 243, type: 'holding_registers', name: '开关机(243默认开机)', key: 'on_off' },
    { address: 5095, value: 0, type: 'holding_registers', name: '并离网模式(0-并网,1-离网)', key: 'grid_mode' },
    { address: 5033, value: 0, type: 'holding_registers', name: 'PCS充放电状态(1-放电,2-充电)', key: 'pcs_charge_discharge_state' },
    { address: 0, value: 3, type: 'input_registers', name: 'state1' },
    { address: 2, value: 288, type: 'input_registers', name: 'SOC' },
    { address: 8, value: 10000, type: 'input_registers', name: '最大充电功率' },
    { address: 9, value: 10000, type: 'input_registers', name: '最大放电功率' },
    { address: 12, value: 862, type: 'input_registers', name: '剩余可放电容量' },
    { address: 39, value: 100, type: 'input_registers', name: '额定容量' },
    { address: 40, value: 0, type: 'input_registers', name: 'pcs_num' },
    { address: 41, value: 0, type: 'input_registers', name: 'battery_cluster_num' },
    { address: 42, value: 0, type: 'input_registers', name: 'battery_cluster_capacity' },
    { address: 43, value: 0, type: 'input_registers', name: 'battery_cluster_power' },
    { address: 400, value: 0, type: 'input_registers', name: 'state4' },
    { address: 408, value: 1, type: 'input_registers', name: 'state2' },
    { address: 409, value: 2200, type: 'input_registers', name: 'A相电压' },
    { address: 410, value: 2200, type: 'input_registers', name: 'B相电压' },
    { address: 411, value: 2200, type: 'input_registers', name: 'C相电压' },
    { address: 412, value: 0, type: 'input_registers', name: 'A相电流' },
    { address: 413, value: 0, type: 'input_registers', name: 'B相电流' },
    { address: 414, value: 0, type: 'input_registers', name: 'C相电流' },
    { address: 420, value: 0, type: 'input_registers', name: '有功功率(低)', key: 'active_power_low' },
    { address: 421, value: 0, type: 'input_registers', name: '有功功率(高)', key: 'active_power_high' },
    { address: 426, value: 0, type: 'input_registers', name: '日充电量' },
    { address: 427, value: 0, type: 'input_registers', name: '日放电量' },
    { address: 428, value: 0, type: 'input_registers', name: '累计充电总量(低)' },
    { address: 429, value: 0, type: 'input_registers', name: '累计充电总量(高)' },
    { address: 430, value: 0, type: 'input_registers', name: '累计放电总量(低)' },
    { address: 431, value: 0, type: 'input_registers', name: '累计放电总量(高)' },
    { address: 432, value: 0, type: 'input_registers', name: 'PCS工作模式(bit9-并网,bit10-离网)' },
    { address: 839, value: 240, type: 'input_registers', name: 'state3(240-停机,243/245-正常,242/246-故障)' },
    { address: 900, value: 0, type: 'input_registers', name: 'SN_900' },
  ];
}

/** v1.5.0 charger: IR 0,1,2,4,100-103; HR 0 */
function getChargerDefaults(): RegisterEntry[] {
  return [
    { address: 0, value: 0x7fff, type: 'holding_registers', name: '功率限制', key: 'power_limit_raw' },
    { address: 0, value: 0, type: 'input_registers', name: '有功功率', key: 'active_power' },
    { address: 1, value: 1, type: 'input_registers', name: '状态' },
    { address: 2, value: 0, type: 'input_registers', name: '需求功率' },
    { address: 3, value: 0, type: 'input_registers', name: '枪数量' },
    { address: 4, value: 0, type: 'input_registers', name: '额定功率' },
    { address: 100, value: 1, type: 'input_registers', name: '枪1状态' },
    { address: 101, value: 2, type: 'input_registers', name: '枪2状态' },
    { address: 102, value: 3, type: 'input_registers', name: '枪3状态' },
    { address: 103, value: 4, type: 'input_registers', name: '枪4状态' },
  ];
}

/** 按设备类型返回 v1.5.0 预定义寄存器列表（前端与后端 get_modbus_register_defaults 一致） */
export function getPredefinedRegistersForDeviceType(deviceType: string): RegisterEntry[] {
  switch (deviceType) {
    case 'meter':
      return getMeterDefaults().map((e) => ({ ...e, value: e.value }));
    case 'static_generator':
      return getStaticGeneratorDefaults().map((e) => ({ ...e, value: e.value }));
    case 'storage':
      return getStorageDefaults().map((e) => ({ ...e, value: e.value }));
    case 'charger':
      return getChargerDefaults().map((e) => ({ ...e, value: e.value }));
    default:
      return getMeterDefaults().map((e) => ({ ...e, value: e.value }));
  }
}

export function getAllRegisterTypes(): ModbusRegisterType[] {
  return [...REG_TYPES];
}
