// Modbus 设备启停命令
use serde::Deserialize;
use tauri::State;
use std::sync::Mutex;
use crate::commands::device::{get_modbus_register_defaults, ModbusRegisterEntry};
use crate::commands::topology::device_type_to_string;
use crate::domain::metadata::DeviceMetadataStore;
use crate::services::modbus::ModbusService;

#[derive(Debug, Deserialize)]
pub struct StartModbusConfig {
    pub ip_address: String,
    pub port: u16,
    #[serde(default)]
    pub slave_id: u8,
    pub registers: Option<Vec<ModbusRegisterEntry>>,
}

#[tauri::command]
pub async fn start_device_modbus(
    device_id: String,
    device_type: String,
    config: StartModbusConfig,
    modbus_service: State<'_, ModbusService>,
) -> Result<(), String> {
    let registers = config.registers.unwrap_or_default();
    modbus_service
        .start_device_modbus(device_id, device_type, config.ip_address, config.port, registers)
        .await
}

#[tauri::command]
pub async fn stop_device_modbus(
    device_id: String,
    modbus_service: State<'_, ModbusService>,
) -> Result<(), String> {
    modbus_service.stop_device_modbus(&device_id).await
}

/// 启动拓扑中所有配置了 ip/port 的设备的 Modbus TCP 服务器（运行仿真时自动调用；寄存器使用各类型默认列表）
#[tauri::command]
pub async fn start_all_modbus_servers(
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
    modbus_service: State<'_, ModbusService>,
) -> Result<(), String> {
    let devices_to_start: Vec<(String, String, String, u16)> = {
        let store = metadata_store.lock().map_err(|e| e.to_string())?;
        store
            .get_all_devices()
            .iter()
            .filter_map(|d| {
                let ip = d.properties.get("ip").and_then(|v| v.as_str()).map(String::from)?;
                let port = d
                    .properties
                    .get("port")
                    .and_then(|v| v.as_u64().map(|n| n as u16).or_else(|| v.as_str().and_then(|s| s.parse::<u16>().ok())))?;
                if ip.is_empty() {
                    return None;
                }
                Some((d.id.clone(), device_type_to_string(&d.device_type), ip, port))
            })
            .collect()
    };
    for (id, device_type, ip, port) in devices_to_start {
        let registers = get_modbus_register_defaults(device_type.clone()).map_err(|e| e.to_string())?;
        if let Err(e) = modbus_service
            .start_device_modbus(id.clone(), device_type, ip, port, registers)
            .await
        {
            eprintln!("start_all_modbus_servers: {} 启动失败: {}", id, e);
        }
    }
    Ok(())
}

/// 返回当前正在运行的 Modbus 服务器对应的设备 id 列表（设备控制页用于显示开关状态）
#[tauri::command]
pub fn get_running_modbus_device_ids(modbus_service: State<'_, ModbusService>) -> Vec<String> {
    modbus_service.running_device_ids()
}
