// Modbus TCP 管理：每设备独立 TCP 服务，四类寄存器由 modbus_server 实现
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex as StdMutex};
use tokio::sync::{mpsc, RwLock};
use crate::commands::device::ModbusRegisterEntry;
use crate::services::modbus_filter::ModbusControlStateStore;
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

/// 每设备 Modbus TCP 服务：通过 abort JoinHandle 停止；持有共享上下文供仿真同步写入
pub struct RunningDeviceServer {
    pub join: tokio::task::JoinHandle<std::io::Result<()>>,
    pub device_type: String,
    pub context: Arc<RwLock<ModbusDeviceContext>>,
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

    /// 应用一次 HR 写入（更新控制状态），返回应推送到 Python 的有效属性；若该地址不参与功率过滤则返回 None
    pub fn apply_hr_write_and_effective_properties(
        &self,
        device_id: &str,
        device_type: &str,
        address: u16,
        value: u16,
    ) -> Option<serde_json::Value> {
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
    pub async fn start_device_modbus(
        &self,
        device_id: String,
        device_type: String,
        ip: String,
        port: u16,
        registers: Vec<ModbusRegisterEntry>,
    ) -> Result<(), String> {
        let mut running = self.running_servers.lock().map_err(|e| e.to_string())?;
        if running.contains_key(&device_id) {
            return Err("该设备 Modbus 服务已在运行".to_string());
        }
        let tx = self.hr_write_tx.clone();
        let did = device_id.clone();
        let on_holding_write: OnHoldingRegisterWrite = Arc::new(move |addr: u16, value: u16| {
            let _ = tx.try_send((did.clone(), addr, value));
        });
        let context = Arc::new(RwLock::new(ModbusDeviceContext::from_entries(&registers, Some(on_holding_write))));
        let context_for_task = context.clone();
        let join = tokio::task::spawn(async move {
            modbus_server::run_modbus_tcp_server(&ip, port, context_for_task).await
        });
        running.insert(
            device_id,
            RunningDeviceServer {
                join,
                device_type,
                context,
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

    pub fn is_device_running(&self, device_id: &str) -> bool {
        self.running_servers.lock().map(|r| r.contains_key(device_id)).unwrap_or(false)
    }

    /// 根据仿真功率缓存更新所有运行中设备的 Modbus 输入寄存器（v1.5.0 update_* 逻辑）
    pub async fn update_all_devices_from_simulation(
        &self,
        power_snapshot: &HashMap<String, (f64, Option<f64>, Option<f64>)>,
    ) {
        let to_update: Vec<(String, String, Arc<RwLock<ModbusDeviceContext>>)> = {
            let running = self.running_servers.lock().map_err(|_| ()).ok();
            let Some(r) = running else { return };
            r.iter()
                .map(|(id, s)| (id.clone(), s.device_type.clone(), s.context.clone()))
                .collect()
        };
        for (device_id, device_type, context) in to_update {
            let (_, p_active, p_reactive) = power_snapshot.get(&device_id).copied().unwrap_or((0.0, None, None));
            let p_kw = p_active.unwrap_or(0.0);
            let q_kvar = p_reactive;
            let mut ctx = context.write().await;
            modbus_server::update_context_from_simulation(&mut *ctx, &device_type, Some(p_kw), q_kvar);
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
