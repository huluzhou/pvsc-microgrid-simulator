// 设备管理命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::domain::metadata::DeviceMetadataStore;
use crate::domain::device::DeviceMetadata;
use crate::services::simulation_engine::SimulationEngine;
use crate::commands::topology::device_type_to_string;
use std::sync::{Arc, Mutex};
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceConfig {
    pub device_id: String,
    pub work_mode: Option<String>,
    pub response_delay: Option<f64>,
    pub measurement_error: Option<f64>,
    pub data_collection_frequency: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub id: String,
    pub name: String,
    pub device_type: String,  // 使用字符串类型，方便前端使用
    pub properties: HashMap<String, serde_json::Value>,
}

/// Modbus 设备信息：仅包含拓扑中配置了 ip 和 port 的设备（旧版/新版拓扑均从 properties 读取）
#[derive(Debug, Serialize, Deserialize)]
pub struct ModbusDeviceInfo {
    pub id: String,
    pub name: String,
    pub device_type: String,
    pub ip: String,
    pub port: u16,
}

/// 单条寄存器配置（四类：coils / discrete_inputs / input_registers / holding_registers）
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModbusRegisterEntry {
    pub address: u16,
    pub value: u16,
    /// coils | discrete_inputs | input_registers | holding_registers
    #[serde(rename = "type")]
    pub type_: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
}

fn modbus_register_defaults_meter() -> Vec<ModbusRegisterEntry> {
    vec![
        ModbusRegisterEntry { address: 0, value: 0, type_: "input_registers".into(), name: Some("当前有功功率".into()) },
        ModbusRegisterEntry { address: 1, value: 220, type_: "input_registers".into(), name: Some("A相电压".into()) },
        ModbusRegisterEntry { address: 2, value: 220, type_: "input_registers".into(), name: Some("B相电压".into()) },
        ModbusRegisterEntry { address: 3, value: 220, type_: "input_registers".into(), name: Some("C相电压".into()) },
        ModbusRegisterEntry { address: 4, value: 0, type_: "input_registers".into(), name: Some("A相电流".into()) },
        ModbusRegisterEntry { address: 5, value: 0, type_: "input_registers".into(), name: Some("B相电流".into()) },
        ModbusRegisterEntry { address: 6, value: 0, type_: "input_registers".into(), name: Some("C相电流".into()) },
        ModbusRegisterEntry { address: 7, value: 0, type_: "input_registers".into(), name: Some("四象限-有功导出(上网)".into()) },
        ModbusRegisterEntry { address: 8, value: 0, type_: "input_registers".into(), name: Some("四象限-有功导入(下网)".into()) },
        ModbusRegisterEntry { address: 9, value: 0, type_: "input_registers".into(), name: Some("组合有功总电能".into()) },
        ModbusRegisterEntry { address: 10, value: 0, type_: "input_registers".into(), name: Some("四象限-无功导出".into()) },
        ModbusRegisterEntry { address: 11, value: 0, type_: "input_registers".into(), name: Some("四象限-无功导入".into()) },
        ModbusRegisterEntry { address: 20, value: 0, type_: "input_registers".into(), name: Some("无功功率".into()) },
    ]
}

fn modbus_register_defaults_static_generator() -> Vec<ModbusRegisterEntry> {
    vec![
        ModbusRegisterEntry { address: 5005, value: 1, type_: "holding_registers".into(), name: Some("开关机".into()) },
        ModbusRegisterEntry { address: 5007, value: 100, type_: "holding_registers".into(), name: Some("有功功率百分比限制".into()) },
        ModbusRegisterEntry { address: 5038, value: 0x7FFF, type_: "holding_registers".into(), name: Some("有功功率限制".into()) },
        ModbusRegisterEntry { address: 5040, value: 0, type_: "holding_registers".into(), name: Some("无功补偿百分比".into()) },
        ModbusRegisterEntry { address: 5041, value: 0, type_: "holding_registers".into(), name: Some("功率因数".into()) },
        ModbusRegisterEntry { address: 5001, value: 0, type_: "input_registers".into(), name: Some("额定功率".into()) },
        ModbusRegisterEntry { address: 5003, value: 0, type_: "input_registers".into(), name: Some("今日发电量".into()) },
        ModbusRegisterEntry { address: 5004, value: 0, type_: "input_registers".into(), name: Some("总发电量".into()) },
        ModbusRegisterEntry { address: 5030, value: 0, type_: "input_registers".into(), name: Some("当前有功功率(低)".into()) },
        ModbusRegisterEntry { address: 5031, value: 0, type_: "input_registers".into(), name: Some("当前有功功率(高)".into()) },
        ModbusRegisterEntry { address: 5032, value: 0, type_: "input_registers".into(), name: Some("无功功率(低)".into()) },
        ModbusRegisterEntry { address: 5033, value: 0, type_: "input_registers".into(), name: Some("无功功率(高)".into()) },
    ]
}

fn modbus_register_defaults_storage() -> Vec<ModbusRegisterEntry> {
    vec![
        ModbusRegisterEntry { address: 4, value: 0, type_: "holding_registers".into(), name: Some("设置功率".into()) },
        ModbusRegisterEntry { address: 55, value: 243, type_: "holding_registers".into(), name: Some("开关机(243默认开机)".into()) },
        ModbusRegisterEntry { address: 5095, value: 0, type_: "holding_registers".into(), name: Some("并离网模式(0-并网,1-离网)".into()) },
        ModbusRegisterEntry { address: 5033, value: 0, type_: "holding_registers".into(), name: Some("PCS充放电状态(1-放电,2-充电)".into()) },
        ModbusRegisterEntry { address: 0, value: 3, type_: "input_registers".into(), name: Some("state1".into()) },
        ModbusRegisterEntry { address: 2, value: 288, type_: "input_registers".into(), name: Some("SOC".into()) },
        ModbusRegisterEntry { address: 8, value: 10000, type_: "input_registers".into(), name: Some("最大充电功率".into()) },
        ModbusRegisterEntry { address: 9, value: 10000, type_: "input_registers".into(), name: Some("最大放电功率".into()) },
        ModbusRegisterEntry { address: 12, value: 862, type_: "input_registers".into(), name: Some("剩余可放电容量".into()) },
        ModbusRegisterEntry { address: 39, value: 100, type_: "input_registers".into(), name: Some("额定容量".into()) },
        ModbusRegisterEntry { address: 40, value: 0, type_: "input_registers".into(), name: Some("pcs_num".into()) },
        ModbusRegisterEntry { address: 41, value: 0, type_: "input_registers".into(), name: Some("battery_cluster_num".into()) },
        ModbusRegisterEntry { address: 42, value: 0, type_: "input_registers".into(), name: Some("battery_cluster_capacity".into()) },
        ModbusRegisterEntry { address: 43, value: 0, type_: "input_registers".into(), name: Some("battery_cluster_power".into()) },
        ModbusRegisterEntry { address: 400, value: 0, type_: "input_registers".into(), name: Some("state4".into()) },
        ModbusRegisterEntry { address: 408, value: 1, type_: "input_registers".into(), name: Some("state2".into()) },
        ModbusRegisterEntry { address: 409, value: 2200, type_: "input_registers".into(), name: Some("A相电压".into()) },
        ModbusRegisterEntry { address: 410, value: 2200, type_: "input_registers".into(), name: Some("B相电压".into()) },
        ModbusRegisterEntry { address: 411, value: 2200, type_: "input_registers".into(), name: Some("C相电压".into()) },
        ModbusRegisterEntry { address: 412, value: 0, type_: "input_registers".into(), name: Some("A相电流".into()) },
        ModbusRegisterEntry { address: 413, value: 0, type_: "input_registers".into(), name: Some("B相电流".into()) },
        ModbusRegisterEntry { address: 414, value: 0, type_: "input_registers".into(), name: Some("C相电流".into()) },
        ModbusRegisterEntry { address: 420, value: 0, type_: "input_registers".into(), name: Some("有功功率(低)".into()) },
        ModbusRegisterEntry { address: 421, value: 0, type_: "input_registers".into(), name: Some("有功功率(高)".into()) },
        ModbusRegisterEntry { address: 426, value: 0, type_: "input_registers".into(), name: Some("日充电量".into()) },
        ModbusRegisterEntry { address: 427, value: 0, type_: "input_registers".into(), name: Some("日放电量".into()) },
        ModbusRegisterEntry { address: 428, value: 0, type_: "input_registers".into(), name: Some("累计充电总量(低)".into()) },
        ModbusRegisterEntry { address: 429, value: 0, type_: "input_registers".into(), name: Some("累计充电总量(高)".into()) },
        ModbusRegisterEntry { address: 430, value: 0, type_: "input_registers".into(), name: Some("累计放电总量(低)".into()) },
        ModbusRegisterEntry { address: 431, value: 0, type_: "input_registers".into(), name: Some("累计放电总量(高)".into()) },
        ModbusRegisterEntry { address: 432, value: 0, type_: "input_registers".into(), name: Some("PCS工作模式(bit9-并网,bit10-离网)".into()) },
        ModbusRegisterEntry { address: 839, value: 240, type_: "input_registers".into(), name: Some("state3(240-停机,243/245-正常,242/246-故障)".into()) },
        ModbusRegisterEntry { address: 900, value: 0, type_: "input_registers".into(), name: Some("SN_900".into()) },
    ]
}

fn modbus_register_defaults_charger() -> Vec<ModbusRegisterEntry> {
    vec![
        ModbusRegisterEntry { address: 0, value: 0x7FFF, type_: "holding_registers".into(), name: Some("功率限制".into()) },
        ModbusRegisterEntry { address: 0, value: 0, type_: "input_registers".into(), name: Some("有功功率".into()) },
        ModbusRegisterEntry { address: 1, value: 1, type_: "input_registers".into(), name: Some("状态".into()) },
        ModbusRegisterEntry { address: 2, value: 0, type_: "input_registers".into(), name: Some("需求功率".into()) },
        ModbusRegisterEntry { address: 3, value: 0, type_: "input_registers".into(), name: Some("枪数量".into()) },
        ModbusRegisterEntry { address: 4, value: 0, type_: "input_registers".into(), name: Some("额定功率".into()) },
        ModbusRegisterEntry { address: 100, value: 1, type_: "input_registers".into(), name: Some("枪1状态".into()) },
        ModbusRegisterEntry { address: 101, value: 2, type_: "input_registers".into(), name: Some("枪2状态".into()) },
        ModbusRegisterEntry { address: 102, value: 3, type_: "input_registers".into(), name: Some("枪3状态".into()) },
        ModbusRegisterEntry { address: 103, value: 4, type_: "input_registers".into(), name: Some("枪4状态".into()) },
    ]
}

/// 返回指定设备类型的 v1.5.0 预定义寄存器列表（与前端 modbusRegisters 一致）
#[tauri::command]
pub fn get_modbus_register_defaults(device_type: String) -> Result<Vec<ModbusRegisterEntry>, String> {
    let list = match device_type.as_str() {
        "meter" => modbus_register_defaults_meter(),
        "static_generator" => modbus_register_defaults_static_generator(),
        "storage" => modbus_register_defaults_storage(),
        "charger" => modbus_register_defaults_charger(),
        _ => modbus_register_defaults_meter(),
    };
    Ok(list)
}

#[tauri::command]
pub async fn get_all_devices(
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<Vec<DeviceInfo>, String> {
    let metadata_store = metadata_store.lock().unwrap();
    Ok(metadata_store.get_all_devices().iter().map(|d| {
        DeviceInfo {
            id: d.id.clone(),
            name: d.name.clone(),
            device_type: device_type_to_string(&d.device_type),  // 转换为字符串
            properties: d.properties.clone(),
        }
    }).collect())
}

/// 返回拓扑中定义了 ip 和 port 的设备列表（供 Modbus 通信面板使用；兼容旧版拓扑 Measurement/Storage 的 ip/port 与新版 properties）
#[tauri::command]
pub async fn get_modbus_devices(
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<Vec<ModbusDeviceInfo>, String> {
    let metadata_store = metadata_store.lock().unwrap();
    let mut out = Vec::new();
    for d in metadata_store.get_all_devices().iter() {
        let ip = d.properties.get("ip")
            .and_then(|v| v.as_str())
            .map(String::from);
        let port = d.properties.get("port")
            .and_then(|v| {
                v.as_u64().map(|n| n as u16)
                    .or_else(|| v.as_str().and_then(|s| s.parse::<u16>().ok()))
            });
        if let (Some(ip), Some(port)) = (ip, port) {
            if !ip.is_empty() {
                out.push(ModbusDeviceInfo {
                    id: d.id.clone(),
                    name: d.name.clone(),
                    device_type: device_type_to_string(&d.device_type),
                    ip,
                    port,
                });
            }
        }
    }
    Ok(out)
}

#[tauri::command]
pub async fn get_device(
    device_id: String,
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<DeviceMetadata, String> {
    let metadata_store = metadata_store.lock().unwrap();
    let device = metadata_store.get_device(&device_id)
        .ok_or_else(|| format!("Device {} not found", device_id))?;
    
    Ok(DeviceMetadata::from_device(&device))
}

#[tauri::command]
pub async fn update_device_config(
    config: DeviceConfig,
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    // 验证设备存在
    {
        let metadata_store = metadata_store.lock().unwrap();
        metadata_store.get_device(&config.device_id)
            .ok_or_else(|| format!("Device {} not found", config.device_id))?;
    }
    
    // 更新配置（先释放锁，再调用异步函数）
    if let Some(work_mode_str) = &config.work_mode {
        // 设置工作模式
        engine.set_device_mode(config.device_id.clone(), work_mode_str.clone()).await?;
    }
    
    // 更新设备元数据（响应延迟、测量误差等）
    // 这些配置将存储在设备元数据中，供 Python 内核使用
    
    Ok(())
}

#[tauri::command]
pub async fn batch_set_device_mode(
    device_ids: Vec<String>,
    mode: String,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    for device_id in device_ids {
        engine.set_device_mode(device_id, mode.clone()).await?;
    }
    Ok(())
}
