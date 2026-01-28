// 仿真引擎命令
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, State};
use crate::services::simulation_engine::SimulationEngine;
use crate::domain::simulation::{SimulationStatus, SimulationError};
use crate::domain::metadata::DeviceMetadataStore;
use std::sync::{Arc, Mutex};

#[derive(Debug, Serialize, Deserialize)]
pub struct SimulationConfig {
    pub calculation_interval_ms: u64,
    pub remote_control_enabled: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SimulationControlRequest {
    pub action: String, // "start", "stop", "pause", "resume"
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceModeRequest {
    pub device_id: String,
    pub mode: String,
}

#[tauri::command]
pub async fn start_simulation(
    app: AppHandle,
    config: SimulationConfig,
    engine: State<'_, Arc<SimulationEngine>>,
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<(), String> {
    // 从元数据存储获取拓扑数据
    let topology = {
        let store = metadata_store.lock().unwrap();
        store.get_topology()
    };
    
    if let Some(topology) = topology {
        // 设置拓扑数据到仿真引擎
        engine.set_topology(topology).await;
    } else {
        return Err("未找到拓扑数据，请先加载拓扑".to_string());
    }
    
    // 启动仿真
    engine.start(Some(app), config.calculation_interval_ms).await
}

#[tauri::command]
pub async fn stop_simulation(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.stop().await
}

#[tauri::command]
pub async fn pause_simulation(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.pause().await
}

#[tauri::command]
pub async fn resume_simulation(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.resume().await
}

#[tauri::command]
pub async fn get_simulation_status(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<SimulationStatus, String> {
    Ok(engine.get_status().await)
}

#[tauri::command]
pub async fn set_device_mode(
    device_id: String,
    mode: String,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.set_device_mode(device_id, mode).await
}

#[tauri::command]
pub async fn get_device_data(
    device_id: String,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<serde_json::Value, String> {
    engine.get_device_data(&device_id).await
}

#[tauri::command]
pub async fn get_simulation_errors(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<Vec<SimulationError>, String> {
    let status = engine.get_status().await;
    Ok(status.errors)
}
