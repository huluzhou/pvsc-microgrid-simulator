// 设备管理命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::domain::metadata::DeviceMetadataStore;
use crate::domain::device::{DeviceMetadata, WorkMode};
use crate::services::simulation_engine::SimulationEngine;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceConfig {
    pub device_id: String,
    pub work_mode: Option<String>,
    pub response_delay: Option<f64>,
    pub measurement_error: Option<f64>,
    pub data_collection_frequency: Option<f64>,
}

#[tauri::command]
pub async fn get_all_devices(
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<Vec<DeviceMetadata>, String> {
    let metadata_store = metadata_store.lock().unwrap();
    Ok(metadata_store.get_all_devices().iter().map(|d| {
        DeviceMetadata {
            id: d.id.clone(),
            name: d.name.clone(),
            device_type: d.device_type.clone(),
            properties: d.properties.clone(),
            work_mode: None,
            response_delay: None,
            measurement_error: None,
            data_collection_frequency: None,
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
    // 更新设备元数据
    let mut metadata_store = metadata_store.lock().unwrap();
    let mut device = metadata_store.get_device(&config.device_id)
        .ok_or_else(|| format!("Device {} not found", config.device_id))?;
    
    // 更新配置
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
