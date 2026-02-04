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

/// 功率单位：寄存器值 = 实际功率(kW) * POWER_UNIT；与 v1.5.0 协议兼容
const POWER_UNIT_KW: f64 = 10.0; // 0.1 kW per register unit

/// 根据设备类型与 modbus_schema 将仿真结果写入对应输入寄存器（每个 IR 有固定更新逻辑）
/// entries 可选：若提供则按 key 查找自定义地址，否则使用 schema 默认地址
pub fn update_context_from_simulation(
    ctx: &mut ModbusDeviceContext,
    device_type: &str,
    entries: Option<&[ModbusRegisterEntry]>,
    p_active_kw: Option<f64>,
    p_reactive_kvar: Option<f64>,
) {
    use modbus_schema::{input_register_updates, ir_update_key_to_default_key, IrUpdateKey};
    let p_kw = p_active_kw.unwrap_or(0.0);
    let q_kvar = p_reactive_kvar.unwrap_or(0.0);
    let p_reg = (p_kw * POWER_UNIT_KW).round().max(0.0) as u32;
    let q_reg = (q_kvar * POWER_UNIT_KW).round().max(0.0) as u32;

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
            IrUpdateKey::ActivePower => (p_reg & 0xFFFF) as u16,
            IrUpdateKey::ReactivePower => (q_reg & 0xFFFF) as u16,
            IrUpdateKey::ActivePowerLow => (p_reg & 0xFFFF) as u16,
            IrUpdateKey::ActivePowerHigh => (p_reg >> 16) as u16,
            IrUpdateKey::ReactivePowerLow => (q_reg & 0xFFFF) as u16,
            IrUpdateKey::ReactivePowerHigh => (q_reg >> 16) as u16,
        };
        ctx.set_input_register(addr, value);
    }
}
