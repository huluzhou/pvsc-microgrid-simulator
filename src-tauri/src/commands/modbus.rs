// Modbus 设备启停命令
use serde::Deserialize;
use tauri::State;
use crate::commands::device::ModbusRegisterEntry;
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
