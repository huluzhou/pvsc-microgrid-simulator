// Modbus TCP 管理：每设备独立 TCP 服务，四类寄存器由 modbus_server 实现
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use serde_json::Value as JsonValue;
use std::sync::{Arc, Mutex as StdMutex};
use tokio::sync::{mpsc, RwLock};
use crate::commands::device::ModbusRegisterEntry;
use crate::services::modbus_filter::{self, ModbusControlStateStore};
use crate::services::modbus_schema::holding_register_default_key;
use crate::services::modbus_server::{self, ModbusDeviceContext, OnHoldingRegisterWrite};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModbusServerConfig {
    pub host: String,
    pub port: u16,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceRegisterMapping {
    pub device_id: String,
    pub base_address: u16,
    pub registers: HashMap<String, u16>,
}

/// 每设备 Modbus TCP 服务：通过 abort JoinHandle 停止；持有共享上下文与寄存器列表（含 key/address）供自定义地址解析
pub struct RunningDeviceServer {
    pub join: tokio::task::JoinHandle<std::io::Result<()>>,
    pub device_type: String,
    pub context: Arc<RwLock<ModbusDeviceContext>>,
    /// 启动时传入的寄存器列表（含 key），用于 HR 写入时按地址解析 key、IR 更新时按 key 取地址
    pub registers: Vec<ModbusRegisterEntry>,
}

/// 保持寄存器写入事件：(device_id, address, value)，由接收端发出 Tauri 事件供命令逻辑使用
pub type HoldingRegisterWriteEvent = (String, u16, u16);

pub struct ModbusService {
    config: Arc<RwLock<ModbusServerConfig>>,
    device_mappings: Arc<StdMutex<HashMap<String, DeviceRegisterMapping>>>,
    /// device_id -> RunningDeviceServer
    running_servers: Arc<StdMutex<HashMap<String, RunningDeviceServer>>>,
    /// 客户端写 HR 时发送 (device_id, addr, value)，由 main 中任务接收并 emit 事件
    hr_write_tx: mpsc::Sender<HoldingRegisterWriteEvent>,
    /// 每设备 Modbus 控制状态：四条指令独立，冲突时只响应最新一条
    pub control_state: Arc<ModbusControlStateStore>,
}

impl ModbusService {
    pub fn new(hr_write_tx: mpsc::Sender<HoldingRegisterWriteEvent>) -> Self {
        Self {
            config: Arc::new(RwLock::new(ModbusServerConfig {
                host: "localhost".to_string(),
                port: 502,
                enabled: false,
            })),
            device_mappings: Arc::new(StdMutex::new(HashMap::new())),
            running_servers: Arc::new(StdMutex::new(HashMap::new())),
            hr_write_tx,
            control_state: Arc::new(ModbusControlStateStore::new()),
        }
    }

    /// 从运行中设备的寄存器列表中按地址解析 HR 的语义 key（先查条目 key，再回退到默认）
    pub fn get_key_for_holding_register(&self, device_id: &str, address: u16) -> Option<String> {
        let running = self.running_servers.lock().ok()?;
        let server = running.get(device_id)?;
        for e in &server.registers {
            if e.type_ == "holding_registers" && e.address == address {
                if let Some(ref k) = e.key {
                    return Some(k.clone());
                }
                break;
            }
        }
        holding_register_default_key(&server.device_type, address).map(String::from)
    }

    /// 应用一次 HR 写入（更新控制状态），返回应推送到 Python 的有效属性；支持自定义地址（按 key 解析）
    pub fn apply_hr_write_and_effective_properties(
        &self,
        device_id: &str,
        device_type: &str,
        address: u16,
        value: u16,
    ) -> Option<serde_json::Value> {
        let key = self.get_key_for_holding_register(device_id, address);
        if let Some(k) = key {
            let mut map = self.control_state.per_device.lock().ok()?;
            let state = map.entry(device_id.to_string()).or_default();
            return modbus_filter::apply_hr_write_by_key(state, device_type, &k, value);
        }
        self.control_state
            .apply_hr_write(device_id, device_type, address, value)
    }

    pub async fn set_config(&self, config: ModbusServerConfig) {
        *self.config.write().await = config;
    }

    pub async fn get_config(&self) -> ModbusServerConfig {
        self.config.read().await.clone()
    }

    pub fn register_device(&self, mapping: DeviceRegisterMapping) {
        let mut mappings = self.device_mappings.lock().unwrap();
        mappings.insert(mapping.device_id.clone(), mapping);
    }

    pub fn unregister_device(&self, device_id: &str) {
        let mut mappings = self.device_mappings.lock().unwrap();
        mappings.remove(device_id);
    }

    pub fn get_device_mapping(&self, device_id: &str) -> Option<DeviceRegisterMapping> {
        let mappings = self.device_mappings.lock().unwrap();
        mappings.get(device_id).cloned()
    }

    /// 启动指定设备的 Modbus TCP 服务（ip, port, 寄存器列表来自前端）；创建共享上下文供仿真同步
    /// rated_power_kw：光伏/充电桩额定功率，加载拓扑时写 IR 5001/IR 4；rated_capacity_kwh：储能额定容量，写 IR 39
    pub async fn start_device_modbus(
        &self,
        device_id: String,
        device_type: String,
        ip: String,
        port: u16,
        registers: Vec<ModbusRegisterEntry>,
        rated_power_kw: Option<f64>,
        rated_capacity_kwh: Option<f64>,
    ) -> Result<(), String> {
        {
            let running = self.running_servers.lock().map_err(|e| e.to_string())?;
            if running.contains_key(&device_id) {
                return Err("该设备 Modbus 服务已在运行".to_string());
            }
        }
        let tx = self.hr_write_tx.clone();
        let did = device_id.clone();
        let on_holding_write: OnHoldingRegisterWrite = Arc::new(move |addr: u16, value: u16| {
            let _ = tx.try_send((did.clone(), addr, value));
        });
        let context = Arc::new(RwLock::new(ModbusDeviceContext::from_entries(&registers, Some(on_holding_write))));
        // 不可变数据：仅加载拓扑或设备属性编辑时写入（在 await 前释放 MutexGuard，保证 future 为 Send）
        {
            let mut ctx = context.write().await;
            if device_type == "static_generator" {
                if let Some(kw) = rated_power_kw {
                    let v = (kw * 10.0_f64).round().clamp(0.0, 65535.0) as u16; // 0.1 kW
                    ctx.set_input_register(5001, v);
                }
            } else if device_type == "storage" {
                if let Some(kwh) = rated_capacity_kwh {
                    let v = (kwh * 10.0_f64).round().clamp(0.0, 65535.0) as u16; // 0.1 kWh
                    ctx.set_input_register(39, v);
                }
            } else if device_type == "charger" {
                if let Some(kw) = rated_power_kw {
                    let v = (kw * 10.0_f64).round().clamp(0.0, 65535.0) as u16; // 0.1 kW
                    ctx.set_input_register(4, v);
                }
            }
        }
        let context_for_task = context.clone();
        let join = tokio::task::spawn(async move {
            modbus_server::run_modbus_tcp_server(&ip, port, context_for_task).await
        });
        let mut running = self.running_servers.lock().map_err(|e| e.to_string())?;
        running.insert(
            device_id,
            RunningDeviceServer {
                join,
                device_type: device_type.clone(),
                context,
                registers,
            },
        );
        Ok(())
    }

    /// 停止指定设备的 Modbus TCP 服务（abort 任务）
    pub async fn stop_device_modbus(&self, device_id: &str) -> Result<(), String> {
        let server = {
            let mut running = self.running_servers.lock().map_err(|e| e.to_string())?;
            running.remove(device_id)
        };
        if let Some(server) = server {
            server.join.abort();
            let _ = server.join.await;
        }
        Ok(())
    }
    
    /// 停止所有运行中的 Modbus TCP 服务（仿真停止或加载新拓扑时调用）
    pub async fn stop_all_device_modbus(&self) {
        let servers: HashMap<String, RunningDeviceServer> = {
            let mut running = match self.running_servers.lock() {
                Ok(r) => r,
                Err(_) => return,
            };
            std::mem::take(&mut *running)
        };
        for (_id, server) in servers {
            server.join.abort();
            let _ = server.join.await;
        }
    }

    pub fn is_device_running(&self, device_id: &str) -> bool {
        self.running_servers.lock().map(|r| r.contains_key(device_id)).unwrap_or(false)
    }

    /// 运行中的设备 id 列表（用于仿真步后推送寄存器快照到前端）
    pub fn running_device_ids(&self) -> Vec<String> {
        self.running_servers
            .lock()
            .map(|r| r.keys().cloned().collect())
            .unwrap_or_default()
    }

    /// 获取某设备当前输入寄存器与保持寄存器的快照（地址→值），供前端显示
    pub async fn get_device_register_snapshot(
        &self,
        device_id: &str,
    ) -> Option<(HashMap<u16, u16>, HashMap<u16, u16>)> {
        let context = {
            let running = self.running_servers.lock().ok()?;
            running.get(device_id).map(|s| s.context.clone())?
        };
        let ctx = context.read().await;
        Some((ctx.input_registers.clone(), ctx.holding_registers.clone()))
    }

    /// 设备属性编辑后同步不可变寄存器：光伏 IR 5001、储能 IR 39、充电桩 IR 4（仅当该设备 Modbus 在运行且属性含对应字段时写入）
    pub async fn update_device_immutable_registers(
        &self,
        device_id: &str,
        device_type: &str,
        properties: &HashMap<String, JsonValue>,
    ) {
        let context = {
            let running = match self.running_servers.lock() {
                Ok(r) => r,
                Err(_) => return,
            };
            match running.get(device_id) {
                Some(s) => s.context.clone(),
                None => return,
            }
        };
        let (rated_power_kw, rated_capacity_kwh) = if device_type == "static_generator" || device_type == "charger" {
            let kw = properties
                .get("rated_power_kw")
                .or_else(|| properties.get("max_power_kw"))
                .or_else(|| properties.get("rated_power"))
                .and_then(|v| v.as_f64().or_else(|| v.as_u64().map(|u| u as f64)));
            (kw, None)
        } else if device_type == "storage" {
            let kwh = properties
                .get("capacity_kwh")
                .or_else(|| properties.get("capacity"))
                .and_then(|v| v.as_f64().or_else(|| v.as_u64().map(|u| u as f64)))
                .or_else(|| properties.get("max_e_mwh").and_then(|v| v.as_f64().map(|mwh| mwh * 1000.0)));
            (None, kwh)
        } else {
            (None, None)
        };
        let mut ctx = context.write().await;
        if device_type == "static_generator" {
            if let Some(kw) = rated_power_kw {
                let v = (kw * 10.0_f64).round().clamp(0.0, 65535.0) as u16;
                ctx.set_input_register(5001, v);
            }
        } else if device_type == "storage" {
            if let Some(kwh) = rated_capacity_kwh {
                let v = (kwh * 10.0_f64).round().clamp(0.0, 65535.0) as u16;
                ctx.set_input_register(39, v);
            }
        } else if device_type == "charger" {
            if let Some(kw) = rated_power_kw {
                let v = (kw * 10.0_f64).round().clamp(0.0, 65535.0) as u16;
                ctx.set_input_register(4, v);
            }
        }
    }

    /// 根据仿真功率缓存与储能状态更新所有运行中设备的 Modbus 输入寄存器（v1.5.0 update_* 逻辑）
    /// dt_seconds：本步时长（秒）；storage_states：储能 SOC/日/累计电量。额定功率等不可变数据仅在加载拓扑启动时写入。
    pub async fn update_all_devices_from_simulation(
        &self,
        power_snapshot: &HashMap<String, (f64, Option<f64>, Option<f64>)>,
        dt_seconds: f64,
        storage_states: Option<&HashMap<String, crate::domain::simulation::StorageState>>,
    ) {
        let to_update: Vec<(String, String, Arc<RwLock<ModbusDeviceContext>>, Vec<ModbusRegisterEntry>)> = {
            let running = self.running_servers.lock().map_err(|_| ()).ok();
            let Some(r) = running else { return };
            r.iter()
                .map(|(id, s)| (id.clone(), s.device_type.clone(), s.context.clone(), s.registers.clone()))
                .collect()
        };
        for (device_id, device_type, context, registers) in to_update {
            let (_, p_active, p_reactive) = power_snapshot.get(&device_id).copied().unwrap_or((0.0, None, None));
            let p_kw = p_active.unwrap_or(0.0);
            let q_kvar = p_reactive;
            let storage_state = storage_states.and_then(|m| m.get(&device_id));
            let mut ctx = context.write().await;
            modbus_server::update_context_from_simulation(
                &mut *ctx,
                &device_type,
                Some(&registers),
                Some(p_kw),
                q_kvar,
                Some(dt_seconds),
                storage_state,
            );
        }
    }
}

impl ModbusService {
    /// 用于测试或无需 HR 事件时的构造；HR 写入将被丢弃
    pub fn new_without_hr_events() -> Self {
        let (tx, _rx) = mpsc::channel(64);
        Self::new(tx)
    }
}

impl Default for ModbusService {
    fn default() -> Self {
        Self::new_without_hr_events()
    }
}
