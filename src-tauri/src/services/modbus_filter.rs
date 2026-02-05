// Modbus 过滤：原始数据经四类指令独立处理，冲突时只响应最新指令。
// 1. 开关机：关机则不应有功率  2. 功率百分比限制  3. 功率限制  4. 功率设定

use crate::services::modbus_schema::{holding_register_commands, hr_key_to_command_id, HrCommandId};
use serde_json::json;
use std::collections::HashMap;
use std::sync::Mutex;

/// 四条功率相关指令之一（百分比限制、功率限制、功率设定三者互斥，只响应最新一条）
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ModbusPowerInstruction {
    PowerLimitPct,
    PowerLimitRaw,
    PowerSetpoint,
}

/// 单设备 Modbus 控制状态：每条指令独立；pct/raw/setpoint 仅保留最新一条的序号
pub struct ModbusDeviceControlState {
    pub on_off: Option<u16>,
    pub power_limit_pct: Option<(u16, u64)>,
    pub power_limit_raw: Option<(u16, u64)>,
    pub power_setpoint_kw: Option<(f64, u64)>,
    pub seq: u64,
}

impl Default for ModbusDeviceControlState {
    fn default() -> Self {
        Self {
            on_off: None,
            power_limit_pct: None,
            power_limit_raw: None,
            power_setpoint_kw: None,
            seq: 0,
        }
    }
}

impl ModbusDeviceControlState {
    /// 根据当前状态计算有效属性：1）开关机关则 p_kw=0；2）否则只下发最新一条功率指令（pct/raw/setpoint 之一）
    fn effective_properties(&self) -> serde_json::Value {
        if self.on_off == Some(0) {
            return json!({ "on_off": 0, "p_kw": 0 });
        }
        let on_off = self.on_off.unwrap_or(1);
        let (key, _seq) = self.latest_power_instruction();
        let mut obj = serde_json::Map::new();
        obj.insert("on_off".to_string(), json!(on_off));
        match key {
            Some(ModbusPowerInstruction::PowerLimitPct) => {
                if let Some((v, _)) = self.power_limit_pct {
                    obj.insert("power_limit_pct".to_string(), json!(v));
                }
            }
            Some(ModbusPowerInstruction::PowerLimitRaw) => {
                if let Some((v, _)) = self.power_limit_raw {
                    obj.insert("power_limit_raw".to_string(), json!(v));
                }
            }
            Some(ModbusPowerInstruction::PowerSetpoint) => {
                if let Some((v, _)) = self.power_setpoint_kw {
                    obj.insert("p_kw".to_string(), json!(v));
                }
            }
            None => {}
        }
        serde_json::Value::Object(obj)
    }

    fn latest_power_instruction(&self) -> (Option<ModbusPowerInstruction>, u64) {
        let mut best: (Option<ModbusPowerInstruction>, u64) = (None, 0);
        if let Some((_, seq)) = self.power_limit_pct {
            if seq > best.1 {
                best = (Some(ModbusPowerInstruction::PowerLimitPct), seq);
            }
        }
        if let Some((_, seq)) = self.power_limit_raw {
            if seq > best.1 {
                best = (Some(ModbusPowerInstruction::PowerLimitRaw), seq);
            }
        }
        if let Some((_, seq)) = self.power_setpoint_kw {
            if seq > best.1 {
                best = (Some(ModbusPowerInstruction::PowerSetpoint), seq);
            }
        }
        best
    }
}

/// 按 (device_type, address) 解析为 HrCommandId；未定义返回 None
fn hr_address_to_command(device_type: &str, address: u16) -> Option<HrCommandId> {
    holding_register_commands(device_type)
        .iter()
        .find(|(addr, _)| *addr == address)
        .map(|(_, c)| *c)
}

/// 按 (device_type, key) 应用 HR 写入并返回有效属性（支持自定义地址时由调用方先解析 address -> key）
pub fn apply_hr_write_by_key(
    state: &mut ModbusDeviceControlState,
    device_type: &str,
    key: &str,
    value: u16,
) -> Option<serde_json::Value> {
    let cmd = hr_key_to_command_id(key)?;
    apply_hr_write_inner(state, device_type, cmd, value)
}

fn apply_hr_write_inner(
    state: &mut ModbusDeviceControlState,
    device_type: &str,
    cmd: HrCommandId,
    value: u16,
) -> Option<serde_json::Value> {
    match (device_type, cmd) {
        ("static_generator", HrCommandId::OnOff) => {
            state.on_off = Some(value);
            Some(state.effective_properties())
        }
        ("static_generator", HrCommandId::PowerLimitPct) => {
            state.seq += 1;
            state.power_limit_pct = Some((value, state.seq));
            Some(state.effective_properties())
        }
        ("static_generator", HrCommandId::PowerLimitRaw) => {
            state.seq += 1;
            state.power_limit_raw = Some((value, state.seq));
            Some(state.effective_properties())
        }
        ("static_generator", HrCommandId::ReactiveCompPct) => {
            Some(json!({ "reactive_comp_pct": value }))
        }
        ("static_generator", HrCommandId::PowerFactor) => Some(json!({ "power_factor": value })),
        ("storage", HrCommandId::SetPower) => {
            state.seq += 1;
            // 储能功率单位 0.1 kW，寄存器为有符号 16 位（负=放电）；客户端写 (-300*10)&0xFFFF 即 62536，按 i16 解析为 -3000 → -300 kW
            let raw_i16 = value as i16;
            let p_kw = (raw_i16 as f64) / 10.0;
            state.power_setpoint_kw = Some((p_kw, state.seq));
            Some(state.effective_properties())
        }
        ("storage", HrCommandId::OnOff) => {
            state.on_off = Some(value);
            Some(state.effective_properties())
        }
        ("storage", HrCommandId::Other(5095)) => Some(json!({ "grid_mode": value })),
        ("storage", HrCommandId::Other(5033)) => Some(json!({ "pcs_charge_discharge_state": value })),
        ("charger", HrCommandId::PowerLimitRaw) => {
            state.seq += 1;
            state.power_limit_raw = Some((value, state.seq));
            Some(state.effective_properties())
        }
        _ => None,
    }
}

/// 更新设备 Modbus 状态并返回应推送到 Python 的有效属性（独立指令；冲突只响应最新）
/// 优先用 address 查默认 key，再按 key 应用（兼容自定义地址时由调用方先解析 key）
pub fn apply_hr_write_and_effective_properties(
    state: &mut ModbusDeviceControlState,
    device_type: &str,
    address: u16,
    value: u16,
) -> Option<serde_json::Value> {
    let cmd = hr_address_to_command(device_type, address)?;
    apply_hr_write_inner(state, device_type, cmd, value)
}

/// 全局每设备 Modbus 控制状态，供 HR 写入时更新并计算有效属性
pub struct ModbusControlStateStore {
    pub per_device: Mutex<HashMap<String, ModbusDeviceControlState>>,
}

impl ModbusControlStateStore {
    pub fn new() -> Self {
        Self {
            per_device: Mutex::new(HashMap::new()),
        }
    }

    /// 应用一次 HR 写入并返回该设备应推送到 Python 的有效属性；若设备未开启远程控制由调用方判断
    pub fn apply_hr_write(
        &self,
        device_id: &str,
        device_type: &str,
        address: u16,
        value: u16,
    ) -> Option<serde_json::Value> {
        let mut map = self.per_device.lock().ok()?;
        let state = map.entry(device_id.to_string()).or_default();
        apply_hr_write_and_effective_properties(state, device_type, address, value)
    }
}

impl Default for ModbusControlStateStore {
    fn default() -> Self {
        Self::new()
    }
}
