// Modbus TCP 管理
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use tokio::sync::RwLock;

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
    pub registers: HashMap<String, u16>, // register_name -> offset
}

pub struct ModbusService {
    config: Arc<RwLock<ModbusServerConfig>>,
    device_mappings: Arc<Mutex<HashMap<String, DeviceRegisterMapping>>>,
    server_running: Arc<RwLock<bool>>,
}

impl ModbusService {
    pub fn new() -> Self {
        Self {
            config: Arc::new(RwLock::new(ModbusServerConfig {
                host: "localhost".to_string(),
                port: 502,
                enabled: false,
            })),
            device_mappings: Arc::new(Mutex::new(HashMap::new())),
            server_running: Arc::new(RwLock::new(false)),
        }
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

    pub async fn is_server_running(&self) -> bool {
        *self.server_running.read().await
    }

    pub async fn start_server(&self) -> Result<(), String> {
        let config = self.config.read().await.clone();
        if !config.enabled {
            return Err("Modbus server is not enabled".to_string());
        }

        // 通知 Python 内核启动 Modbus 服务器
        // 这里需要通过 PythonBridge 调用
        *self.server_running.write().await = true;
        Ok(())
    }

    pub async fn stop_server(&self) -> Result<(), String> {
        *self.server_running.write().await = false;
        Ok(())
    }
}

impl Default for ModbusService {
    fn default() -> Self {
        Self::new()
    }
}
