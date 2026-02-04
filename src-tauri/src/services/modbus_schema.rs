// 每类设备的寄存器设置是固定的：每个输入寄存器对应更新逻辑，每个保持寄存器对应命令逻辑。
// 本模块为各设备类型定义 IR 的 update_key 与 HR 的 command_id，作为单一事实来源。

/// 输入寄存器更新键：仿真结果写入该寄存器时使用的数据源
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IrUpdateKey {
    /// 有功功率 (0.1 kW/单位)
    ActivePower,
    /// 无功功率 (0.1 kVar/单位)
    ReactivePower,
    /// 有功功率 32 位低字
    ActivePowerLow,
    /// 有功功率 32 位高字
    ActivePowerHigh,
    /// 无功功率 32 位低字
    ReactivePowerLow,
    /// 无功功率 32 位高字
    ReactivePowerHigh,
}

/// 保持寄存器命令 id：客户端写该寄存器时触发的命令（用于远程控制）
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HrCommandId {
    /// 开关机 (e.g. 5005)
    OnOff,
    /// 有功功率百分比限制 (5007)
    PowerLimitPct,
    /// 有功功率限制 0x7FFF (5038)
    PowerLimitRaw,
    /// 无功补偿百分比 (5040)
    ReactiveCompPct,
    /// 功率因数 (5041)
    PowerFactor,
    /// 设置功率 (storage 4)
    SetPower,
    /// 并离网模式等其它 HR 暂不映射到具体命令
    Other(u16),
}

/// 按设备类型返回需要由仿真更新的输入寄存器：(地址, 更新键)
pub fn input_register_updates(device_type: &str) -> &'static [(u16, IrUpdateKey)] {
    match device_type {
        "meter" => &[
            (0, IrUpdateKey::ActivePower),
            (20, IrUpdateKey::ReactivePower),
        ],
        "static_generator" => &[
            (5030, IrUpdateKey::ActivePowerLow),
            (5031, IrUpdateKey::ActivePowerHigh),
            (5032, IrUpdateKey::ReactivePowerLow),
            (5033, IrUpdateKey::ReactivePowerHigh),
        ],
        "storage" => &[
            (420, IrUpdateKey::ActivePowerLow),
            (421, IrUpdateKey::ActivePowerHigh),
        ],
        "charger" => &[(0, IrUpdateKey::ActivePower)],
        _ => &[],
    }
}

/// 按设备类型返回具有命令逻辑的保持寄存器：(地址, 命令 id)
pub fn holding_register_commands(device_type: &str) -> &'static [(u16, HrCommandId)] {
    match device_type {
        "static_generator" => &[
            (5005, HrCommandId::OnOff),
            (5007, HrCommandId::PowerLimitPct),
            (5038, HrCommandId::PowerLimitRaw),
            (5040, HrCommandId::ReactiveCompPct),
            (5041, HrCommandId::PowerFactor),
        ],
        "storage" => &[
            (4, HrCommandId::SetPower),
            (55, HrCommandId::OnOff),
            (5095, HrCommandId::Other(5095)),
            (5033, HrCommandId::Other(5033)),
        ],
        "charger" => &[(0, HrCommandId::PowerLimitRaw)],
        _ => &[],
    }
}

/// 按设备类型返回保持寄存器默认 (地址, 语义 key)；用于从自定义地址解析命令时回退
pub fn holding_register_default_key(device_type: &str, address: u16) -> Option<&'static str> {
    let keys: &[(u16, &str)] = match device_type {
        "static_generator" => &[
            (5005, "on_off"),
            (5007, "power_limit_pct"),
            (5038, "power_limit_raw"),
            (5040, "reactive_comp_pct"),
            (5041, "power_factor"),
        ],
        "storage" => &[
            (4, "set_power"),
            (55, "on_off"),
            (5095, "grid_mode"),
            (5033, "pcs_charge_discharge_state"),
        ],
        "charger" => &[(0, "power_limit_raw")],
        _ => return None,
    };
    keys.iter().find(|(a, _)| *a == address).map(|(_, k)| *k)
}

/// 语义 key -> HrCommandId，用于按 key 应用 HR 写入（支持自定义地址）
pub fn hr_key_to_command_id(key: &str) -> Option<HrCommandId> {
    match key {
        "on_off" => Some(HrCommandId::OnOff),
        "power_limit_pct" => Some(HrCommandId::PowerLimitPct),
        "power_limit_raw" => Some(HrCommandId::PowerLimitRaw),
        "reactive_comp_pct" => Some(HrCommandId::ReactiveCompPct),
        "power_factor" => Some(HrCommandId::PowerFactor),
        "set_power" => Some(HrCommandId::SetPower),
        "grid_mode" => Some(HrCommandId::Other(5095)),
        "pcs_charge_discharge_state" => Some(HrCommandId::Other(5033)),
        _ => None,
    }
}

/// IrUpdateKey 对应的默认语义 key（用于在寄存器列表中按 key 查找自定义地址）
pub fn ir_update_key_to_default_key(k: IrUpdateKey) -> &'static str {
    match k {
        IrUpdateKey::ActivePower => "active_power",
        IrUpdateKey::ReactivePower => "reactive_power",
        IrUpdateKey::ActivePowerLow => "active_power_low",
        IrUpdateKey::ActivePowerHigh => "active_power_high",
        IrUpdateKey::ReactivePowerLow => "reactive_power_low",
        IrUpdateKey::ReactivePowerHigh => "reactive_power_high",
    }
}
