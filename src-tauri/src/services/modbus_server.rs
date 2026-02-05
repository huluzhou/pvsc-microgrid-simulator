// Modbus TCP 服务端：四类寄存器上下文与 Service 实现（tokio-modbus）
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::RwLock;
use tokio_modbus::server::tcp::{accept_tcp_connection, Server};
use tokio_modbus::server::Service;
use tokio_modbus::*;
use crate::commands::device::ModbusRegisterEntry;
use crate::services::modbus_schema;

/// 保持寄存器写入回调：客户端写 HR 时调用 (地址, 值)，用于命令逻辑
pub type OnHoldingRegisterWrite = Arc<dyn Fn(u16, u16) + Send + Sync>;

/// 四类寄存器存储：Coils / Discrete Inputs / Input Registers / Holding Registers
/// 每类设备寄存器设置固定，每个 IR 有更新逻辑、每个 HR 有命令逻辑（见 modbus_schema）
#[derive(Default)]
pub struct ModbusDeviceContext {
    pub coils: HashMap<u16, bool>,
    pub discrete_inputs: HashMap<u16, bool>,
    pub input_registers: HashMap<u16, u16>,
    pub holding_registers: HashMap<u16, u16>,
    /// 客户端写保持寄存器时调用，用于远程控制命令逻辑
    pub on_holding_register_write: Option<OnHoldingRegisterWrite>,
}

impl ModbusDeviceContext {
    /// 从预定义寄存器列表构建上下文；可选传入 HR 写入回调以执行命令逻辑
    pub fn from_entries(entries: &[ModbusRegisterEntry], on_holding_write: Option<OnHoldingRegisterWrite>) -> Self {
        let mut ctx = ModbusDeviceContext::default();
        ctx.on_holding_register_write = on_holding_write;
        for e in entries {
            let addr = e.address;
            let val = e.value;
            match e.type_.as_str() {
                "coils" => {
                    ctx.coils.insert(addr, val != 0);
                }
                "discrete_inputs" => {
                    ctx.discrete_inputs.insert(addr, val != 0);
                }
                "input_registers" => {
                    ctx.input_registers.insert(addr, val);
                }
                "holding_registers" => {
                    ctx.holding_registers.insert(addr, val);
                }
                _ => {}
            }
        }
        ctx
    }

    fn get_coil(&self, addr: u16) -> bool {
        self.coils.get(&addr).copied().unwrap_or(false)
    }

    fn get_discrete_input(&self, addr: u16) -> bool {
        self.discrete_inputs.get(&addr).copied().unwrap_or(false)
    }

    fn get_input_register(&self, addr: u16) -> u16 {
        self.input_registers.get(&addr).copied().unwrap_or(0)
    }

    fn get_holding_register(&self, addr: u16) -> u16 {
        self.holding_registers.get(&addr).copied().unwrap_or(0)
    }

    fn set_coil(&mut self, addr: u16, value: bool) {
        self.coils.insert(addr, value);
    }

    fn set_holding_register(&mut self, addr: u16, value: u16) {
        self.holding_registers.insert(addr, value);
        if let Some(ref cb) = self.on_holding_register_write {
            cb(addr, value);
        }
    }

    /// 供仿真同步写入：Input Registers / Discrete Inputs（只读寄存器由仿真结果更新）
    pub fn set_input_register(&mut self, addr: u16, value: u16) {
        self.input_registers.insert(addr, value);
    }

    /// 供仿真同步写入保持寄存器，不触发 on_holding_register_write（用于 state_map 写 HR 5033 等）
    pub fn set_holding_register_silent(&mut self, addr: u16, value: u16) {
        self.holding_registers.insert(addr, value);
    }

    pub fn set_discrete_input(&mut self, addr: u16, value: bool) {
        self.discrete_inputs.insert(addr, value);
    }
}

/// Service 实现：共享 ModbusDeviceContext，处理 Request 并返回 Response
pub struct ModbusContextService {
    pub context: Arc<RwLock<ModbusDeviceContext>>,
}

impl ModbusContextService {
    pub fn new(context: Arc<RwLock<ModbusDeviceContext>>) -> Self {
        Self { context }
    }
}

impl Service for ModbusContextService {
    type Request = SlaveRequest<'static>;
    type Response = Option<Response>;
    type Exception = ExceptionCode;
    type Future = std::pin::Pin<Box<dyn std::future::Future<Output = std::result::Result<Self::Response, Self::Exception>> + Send>>;

    fn call(&self, req: Self::Request) -> Self::Future {
        let context = self.context.clone();
        Box::pin(async move {
            let mut ctx = context.write().await;
            let response = match req.request {
                Request::ReadCoils(addr, qty) => {
                    let vals: Vec<bool> = (0..qty).map(|i| ctx.get_coil(addr + i)).collect();
                    Some(Response::ReadCoils(vals))
                }
                Request::ReadDiscreteInputs(addr, qty) => {
                    let vals: Vec<bool> = (0..qty).map(|i| ctx.get_discrete_input(addr + i)).collect();
                    Some(Response::ReadDiscreteInputs(vals))
                }
                Request::WriteSingleCoil(addr, value) => {
                    ctx.set_coil(addr, value);
                    Some(Response::WriteSingleCoil(addr, value))
                }
                Request::WriteMultipleCoils(addr, values) => {
                    for (i, &v) in values.iter().enumerate() {
                        ctx.set_coil(addr + i as u16, v);
                    }
                    Some(Response::WriteMultipleCoils(addr, values.len() as u16))
                }
                Request::ReadInputRegisters(addr, qty) => {
                    let vals: Vec<u16> = (0..qty).map(|i| ctx.get_input_register(addr + i)).collect();
                    Some(Response::ReadInputRegisters(vals))
                }
                Request::ReadHoldingRegisters(addr, qty) => {
                    let vals: Vec<u16> = (0..qty).map(|i| ctx.get_holding_register(addr + i)).collect();
                    Some(Response::ReadHoldingRegisters(vals))
                }
                Request::WriteSingleRegister(addr, value) => {
                    ctx.set_holding_register(addr, value);
                    Some(Response::WriteSingleRegister(addr, value))
                }
                Request::WriteMultipleRegisters(addr, values) => {
                    for (i, &v) in values.iter().enumerate() {
                        ctx.set_holding_register(addr + i as u16, v);
                    }
                    Some(Response::WriteMultipleRegisters(addr, values.len() as u16))
                }
                _ => return Err(ExceptionCode::IllegalFunction),
            };
            Ok(response)
        })
    }
}

/// 在 (ip, port) 上启动 Modbus TCP 服务，使用共享上下文；任务被 abort 时退出
/// 当 port < 1024 时，在 Linux/WSL 上无 root 会 EACCES，故改用 127.0.0.1:(10000+port) 绑定
pub async fn run_modbus_tcp_server(
    ip: &str,
    port: u16,
    context: Arc<RwLock<ModbusDeviceContext>>,
) -> std::io::Result<()> {
    let (bind_ip, bind_port) = if port < 1024 {
        let high_port = 10000u32.saturating_add(port as u32).min(65535) as u16;
        eprintln!("Modbus 端口 {} 映射到 {}（无需 root 权限）", port, high_port);
        ("127.0.0.1", high_port)
    } else {
        (ip, port)
    };
    let addr: SocketAddr = format!("{}:{}", bind_ip, bind_port).parse().map_err(|e| {
        std::io::Error::new(std::io::ErrorKind::InvalidInput, e)
    })?;
    let listener = TcpListener::bind(addr).await?;
    let server = Server::new(listener);

    let on_connected = move |stream: TcpStream, socket_addr: SocketAddr| {
        let ctx = context.clone();
        std::future::ready(accept_tcp_connection(
            stream,
            socket_addr,
            move |_| Ok(Some(ModbusContextService::new(ctx.clone()))),
        ))
    };

    let on_process_error = |err: std::io::Error| {
        eprintln!("Modbus TCP process error: {:?}", err);
    };

    server.serve(&on_connected, on_process_error).await
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
    Ok(())
}

/// 非电表有功/无功：寄存器单位 0.1 kW（寄存器值 = p_kw × 10）；储能可为负（放电）
const POWER_UNIT_KW_DEFAULT: f64 = 10.0;
/// 电表有功/无功：寄存器单位 0.5 kW，int16 有符号
const METER_POWER_UNIT_KW: f64 = 2.0; // 1/0.5
/// 电表电量：寄存器单位 1 kWh（1 寄存器 = 1 kWh；前端显示时用 0.1 kWh 单位）
const METER_ENERGY_UNIT_KWH: f64 = 1.0;

/// 将 f64 钳位到 i16 并转为 u16 存储（Modbus 寄存器为 u16，按 int16 解释）
fn clamp_i16_as_u16(v: i32) -> u16 {
    let clamped = v.clamp(i32::from(i16::MIN), i32::from(i16::MAX));
    (clamped as i16) as u16
}

/// 根据设备类型与 modbus_schema 将仿真结果写入对应输入寄存器（每个 IR 有固定更新逻辑）
/// 电表：有功/无功为 int16、单位 0.5 kW；四象限电量与组合有功总电能为 kWh（0.1 kWh/单位），由 P/Q 积分得到
/// 储能：Rust 维护的 SOC、日充电量、日放电量、累计充电/放电总量写入 IR 2/12/426-431
/// entries 可选：若提供则按 key 查找自定义地址，否则使用 schema 默认地址
/// dt_seconds：本步时长（秒），用于电表四象限电量与总电能积分；仅电表且为 Some 时累加
/// storage_state：储能状态（SOC、日/累计电量），仅 storage 且为 Some 时写 IR 2/12/426-431
pub fn update_context_from_simulation(
    ctx: &mut ModbusDeviceContext,
    device_type: &str,
    entries: Option<&[ModbusRegisterEntry]>,
    p_active_kw: Option<f64>,
    p_reactive_kvar: Option<f64>,
    dt_seconds: Option<f64>,
    storage_state: Option<&crate::domain::simulation::StorageState>,
) {
    use modbus_schema::{input_register_updates, ir_update_key_to_default_key, IrUpdateKey};
    let p_kw = p_active_kw.unwrap_or(0.0);
    let q_kvar = p_reactive_kvar.unwrap_or(0.0);

    // 电表：int16 有符号，单位 0.5 kW -> 寄存器值 = kW * 2
    let p_reg_meter = clamp_i16_as_u16((p_kw * METER_POWER_UNIT_KW).round() as i32);
    let q_reg_meter = clamp_i16_as_u16((q_kvar * METER_POWER_UNIT_KW).round() as i32);
    // 非电表：0.1 kW/单位，32 位拆高低字；储能有功可为负（放电），按有符号 i32 存
    let p_reg_other = if device_type == "storage" {
        (p_kw * POWER_UNIT_KW_DEFAULT).round() as i32 as u32
    } else {
        (p_kw * POWER_UNIT_KW_DEFAULT).round().max(0.0) as u32
    };
    let q_reg_other = if device_type == "storage" {
        (q_kvar * POWER_UNIT_KW_DEFAULT).round() as i32 as u32
    } else {
        (q_kvar * POWER_UNIT_KW_DEFAULT).round().max(0.0) as u32
    };

    for &(default_addr, ir_key) in input_register_updates(device_type) {
        let key = ir_update_key_to_default_key(ir_key);
        let addr = entries
            .and_then(|e| {
                e.iter()
                    .find(|r| r.type_ == "input_registers" && r.key.as_deref() == Some(key))
                    .map(|r| r.address)
            })
            .unwrap_or(default_addr);
        let value = match ir_key {
            IrUpdateKey::ActivePower => {
                if device_type == "meter" {
                    p_reg_meter
                } else {
                    (p_reg_other & 0xFFFF) as u16
                }
            }
            IrUpdateKey::ReactivePower => {
                if device_type == "meter" {
                    q_reg_meter
                } else {
                    (q_reg_other & 0xFFFF) as u16
                }
            }
            IrUpdateKey::ActivePowerLow => (p_reg_other & 0xFFFF) as u16,
            IrUpdateKey::ActivePowerHigh => (p_reg_other >> 16) as u16,
            IrUpdateKey::ReactivePowerLow => (q_reg_other & 0xFFFF) as u16,
            IrUpdateKey::ReactivePowerHigh => (q_reg_other >> 16) as u16,
        };
        ctx.set_input_register(addr, value);
    }

    // 电表：四象限电量与组合有功总电能（单位 kWh，寄存器 1 kWh/单位），由 P/Q 积分
    if device_type == "meter" {
        let dt_h = dt_seconds.map(|s| s / 3600.0).unwrap_or(0.0);
        let read_energy = |ctx: &ModbusDeviceContext, addr: u16| {
            ctx.input_registers.get(&addr).copied().unwrap_or(0) as f64 / METER_ENERGY_UNIT_KWH
        };
        let mut e_export_p = read_energy(ctx, 7);
        let mut e_import_p = read_energy(ctx, 8);
        let mut e_export_q = read_energy(ctx, 10);
        let mut e_import_q = read_energy(ctx, 11);
        if dt_h > 0.0 {
            if p_kw > 0.0 {
                e_export_p += p_kw * dt_h;
            } else {
                e_import_p += -p_kw * dt_h;
            }
            if let Some(q) = p_reactive_kvar {
                if q > 0.0 {
                    e_export_q += q * dt_h;
                } else {
                    e_import_q += -q * dt_h;
                }
            }
        }
        let e_total_p = e_export_p + e_import_p;
        let write_energy = |v: f64| (v * METER_ENERGY_UNIT_KWH).round().clamp(0.0, 65535.0) as u16;
        ctx.set_input_register(7, write_energy(e_export_p));
        ctx.set_input_register(8, write_energy(e_import_p));
        ctx.set_input_register(9, write_energy(e_total_p));
        ctx.set_input_register(10, write_energy(e_export_q));
        ctx.set_input_register(11, write_energy(e_import_q));
    }

    // 储能 state_map：HR 55 仅表示开关机。关机=停机；开机后按实际功率 p_kw 区分就绪/充电/放电（1=放电 2=充电 0=就绪），故障由其他异常表示。
    if device_type == "storage" {
        let reg55 = ctx.holding_registers.get(&55).copied().unwrap_or(243);
        let (reg839, reg0, reg5033) = if reg55 == 240 {
            (240u16, 1u16, 0u16)
        } else {
            if p_kw > 0.001 {
                (245, 2, 2) // 充电
            } else if p_kw < -0.001 {
                (245, 3, 1) // 放电
            } else {
                (243, 1, 0) // 就绪
            }
        };
        ctx.set_input_register(839, reg839);
        ctx.set_input_register(0, reg0);
        ctx.set_holding_register_silent(5033, reg5033);
        // 并网/离网：根据 HR 5095 同步写 IR 432，与前端/客户端约定一致（bit9=并网 0x0200，bit10=离网 0x0400）
        let grid_mode = ctx.holding_registers.get(&5095).copied().unwrap_or(0);
        let ir432 = if grid_mode == 0 { 0x0200u16 } else { 0x0400u16 };
        ctx.set_input_register(432, ir432);
    }

    // 储能：Rust 维护的 SOC、日充电量、日放电量、累计充电/放电总量 → IR 2/12/426-431（单位与 modbus_manager 一致）
    if device_type == "storage" {
        if let Some(s) = storage_state {
            let soc_reg = (s.soc_percent * 10.0).round().clamp(0.0, 1000.0) as u16;
            ctx.set_input_register(2, soc_reg);
            let remaining_kwh_x10 = (s.energy_kwh * 10.0).round().clamp(0.0, 65535.0) as u16;
            ctx.set_input_register(12, remaining_kwh_x10);
            let daily_charge = (s.daily_charge_kwh * 10.0).round().clamp(0.0, 65535.0) as u16;
            let daily_discharge = (s.daily_discharge_kwh * 10.0).round().clamp(0.0, 65535.0) as u16;
            ctx.set_input_register(426, daily_charge);
            ctx.set_input_register(427, daily_discharge);
            let total_charge_x10 = (s.total_charge_kwh * 10.0).round().clamp(0.0, u32::MAX as f64) as u32;
            ctx.set_input_register(428, (total_charge_x10 & 0xFFFF) as u16);
            ctx.set_input_register(429, (total_charge_x10 >> 16) as u16);
            let total_discharge_x10 = (s.total_discharge_kwh * 10.0).round().clamp(0.0, u32::MAX as f64) as u32;
            ctx.set_input_register(430, (total_discharge_x10 & 0xFFFF) as u16);
            ctx.set_input_register(431, (total_discharge_x10 >> 16) as u16);
        }
    }
}
