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
    /// 从站 ID（Unit ID）：当前后端未使用，每设备独立端口，客户端通常用 1；默认 1
    #[serde(default = "default_slave_id")]
    pub slave_id: u8,
    pub registers: Option<Vec<ModbusRegisterEntry>>,
}

fn default_slave_id() -> u8 {
    1
}

#[tauri::command]
pub async fn start_device_modbus(
    device_id: String,
    device_type: String,
    config: StartModbusConfig,
    modbus_service: State<'_, ModbusService>,
) -> Result<(), String> {
    let registers = config.registers.unwrap_or_default();
    // 单设备启动（非加载拓扑）不写入不可变寄存器，传 None
    modbus_service
        .start_device_modbus(device_id, device_type, config.ip_address, config.port, registers, None, None)
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
    // 先停止所有旧的 Modbus 服务器（避免上一轮仿真残留导致"已在运行"错误）
    modbus_service.stop_all_device_modbus().await;
    
    // 说明：
    // - 旧版逻辑仅启动 properties 中明确配置了 ip/port 的设备
    // - 但默认拓扑（例如 topology.json）通常未配置这些字段，导致前端"运行中"但实际没有 Modbus 端口监听
    // - 这里为常用设备类型提供默认端口分配（与 working_*_client.py 保持一致），让仿真开机即具备可连的 Modbus TCP 服务
    let devices_to_start: Vec<(String, String, String, u16, Option<f64>, Option<f64>)> = {
        let store = metadata_store.lock().map_err(|e| e.to_string())?;
        let mut devices = store.get_all_devices();
        // HashMap 的 values() 顺序不稳定，这里按 id 排序，保证默认端口分配稳定
        devices.sort_by(|a, b| a.id.cmp(&b.id));

        let mut type_counters: std::collections::HashMap<String, u16> = std::collections::HashMap::new();

        devices
            .into_iter()
            .filter_map(|d| {
                let device_type = device_type_to_string(&d.device_type);

                // 1) 读取拓扑配置（若存在）
                let ip_opt = d
                    .properties
                    .get("ip")
                    .and_then(|v| v.as_str())
                    .map(|s| s.trim().to_string())
                    .filter(|s| !s.is_empty());
                let port_opt = d
                    .properties
                    .get("port")
                    .and_then(|v| v.as_u64().map(|n| n as u16).or_else(|| v.as_str().and_then(|s| s.parse::<u16>().ok())));

                // 2) 提供默认 ip/port（与 device_type_to_string 返回值一致：meter/storage/static_generator/charger）
                let default_base_port: Option<u16> = match device_type.as_str() {
                    "meter" => Some(403),
                    "storage" => Some(502),
                    "static_generator" => Some(602),
                    "charger" => Some(702),
                    _ => None,
                };

                let ip = ip_opt.unwrap_or_else(|| "127.0.0.1".to_string());
                let port = if let Some(p) = port_opt {
                    p
                } else if let Some(base) = default_base_port {
                    let c = type_counters.entry(device_type.clone()).or_insert(0);
                    let p = base.saturating_add(*c);
                    *c = c.saturating_add(1);
                    p
                } else {
                    // 其他设备类型没有默认端口分配则跳过
                    return None;
                };

                // 不可变数据：仅加载拓扑时写入，设备属性编辑时也会同步（光伏 IR 5001、储能 IR 39、充电桩 IR 4）
                // 前端设备属性面板使用 rated_power_kw，拓扑/旧数据可能为 max_power_kw 或 rated_power
                let rated_power_kw: Option<f64> = if device_type == "static_generator" || device_type == "charger" {
                    d.properties
                        .get("rated_power_kw")
                        .or_else(|| d.properties.get("max_power_kw"))
                        .or_else(|| d.properties.get("rated_power"))
                        .and_then(|v| v.as_f64().or_else(|| v.as_u64().map(|u| u as f64)))
                } else {
                    None
                };
                let rated_capacity_kwh: Option<f64> = if device_type == "storage" {
                    d.properties
                        .get("capacity_kwh")
                        .or_else(|| d.properties.get("capacity"))
                        .and_then(|v| v.as_f64().or_else(|| v.as_u64().map(|u| u as f64)))
                        .or_else(|| {
                            d.properties.get("max_e_mwh").and_then(|v| v.as_f64().map(|mwh| mwh * 1000.0))
                        })
                } else {
                    None
                };

                Some((d.id.clone(), device_type, ip, port, rated_power_kw, rated_capacity_kwh))
            })
            .collect()
    };
    for (id, device_type, ip, port, rated_power_kw, rated_capacity_kwh) in devices_to_start {
        let registers = get_modbus_register_defaults(device_type.clone()).map_err(|e| e.to_string())?;
        if let Err(e) = modbus_service
            .start_device_modbus(id.clone(), device_type, ip, port, registers, rated_power_kw, rated_capacity_kwh)
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
