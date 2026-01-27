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
