// 监控相关命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::services::database::Database;
use crate::services::simulation_engine::SimulationEngine;
use crate::domain::metadata::DeviceMetadataStore;
use crate::domain::simulation::SimulationState;
use crate::commands::topology::device_type_to_string;
use std::sync::{Arc, Mutex as StdMutex};

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceDataPoint {
    pub device_id: String,
    pub timestamp: f64,
    pub p_active: Option<f64>,    // 有功功率 (kW)
    pub p_reactive: Option<f64>,  // 无功功率 (kVar)
    pub data_json: Option<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceStatus {
    pub device_id: String,
    pub name: String,
    pub device_type: String,
    pub is_online: bool,
    pub last_update: Option<f64>,
    #[serde(rename = "active_power")]
    pub current_p_active: Option<f64>,
    #[serde(rename = "reactive_power")]
    pub current_p_reactive: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub voltage: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub current: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
#[allow(dead_code)]
pub struct Alert {
    pub id: String,
    pub device_id: String,
    pub alert_type: String,
    pub message: String,
    pub severity: String, // "info", "warning", "error"
    pub timestamp: f64,
    pub acknowledged: bool,
}

#[tauri::command]
pub async fn record_device_data(
    data: DeviceDataPoint,
    db: State<'_, Arc<StdMutex<Database>>>,
) -> Result<(), String> {
    let json_str = data.data_json.as_ref()
        .and_then(|v| serde_json::to_string(v).ok());
    
    let db = db.lock().unwrap();
    db.insert_device_data(
        &data.device_id,
        data.timestamp,
        data.p_active,
        data.p_reactive,
        json_str.as_deref(),
    )
    .map_err(|e| format!("Failed to insert device data: {}", e))?;
    Ok(())
}

#[tauri::command]
pub async fn query_device_data(
    device_id: String,
    start_time: Option<f64>,
    end_time: Option<f64>,
    db: State<'_, Arc<StdMutex<Database>>>,
    ) -> Result<Vec<(f64, Option<f64>, Option<f64>)>, String> {
    let db = db.lock().unwrap();
    db.query_device_data(&device_id, start_time, end_time)
        .map_err(|e| format!("Failed to query device data: {}", e))
}

#[tauri::command]
pub async fn get_all_devices_status(
    metadata_store: State<'_, StdMutex<DeviceMetadataStore>>,
    db: State<'_, Arc<StdMutex<Database>>>,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<Vec<DeviceStatus>, String> {
    let devices = {
        let metadata_store = metadata_store.lock().unwrap();
        metadata_store.get_all_devices()
    };
    
    let sim_status = engine.get_status().await;
    let device_active = engine.get_device_active_status().await;
    let is_online_from_engine = |device_id: &str| -> bool {
        matches!(sim_status.state, SimulationState::Running)
            && device_active.get(device_id).copied().unwrap_or(false)
    };
    
    let mut statuses = Vec::new();
    for device in devices {
        let recent_data = {
            let db = db.lock().unwrap();
            db.query_device_data(&device.id, None, None)
                .ok()
                .and_then(|data| data.last().cloned())
        };
        
        let (p_active, p_reactive, last_update) = if let Some((t, p_a, p_r)) = recent_data {
            (p_a, p_r, Some(t))
        } else {
            (None, None, None)
        };
        
        statuses.push(DeviceStatus {
            device_id: device.id.clone(),
            name: device.name.clone(),
            device_type: device_type_to_string(&device.device_type),
            is_online: is_online_from_engine(&device.id),
            last_update,
            current_p_active: p_active,
            current_p_reactive: p_reactive,
            voltage: None,
            current: None,
        });
    }
    
    Ok(statuses)
}

#[tauri::command]
pub async fn get_device_status(
    device_id: String,
    metadata_store: State<'_, StdMutex<DeviceMetadataStore>>,
    db: State<'_, Arc<StdMutex<Database>>>,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<DeviceStatus, String> {
    let (name, device_type_str) = {
        let store = metadata_store.lock().unwrap();
        let device = store.get_device(&device_id)
            .ok_or_else(|| format!("Device {} not found", device_id))?;
        (device.name.clone(), device_type_to_string(&device.device_type))
    };
    let recent_data = {
        let db = db.lock().unwrap();
        db.query_device_data(&device_id, None, None)
            .ok()
            .and_then(|data| data.last().cloned())
    };
    let (p_active, p_reactive, last_update) = if let Some((t, p_a, p_r)) = recent_data {
        (p_a, p_r, Some(t))
    } else {
        (None, None, None)
    };
    let sim_status = engine.get_status().await;
    let device_active = engine.get_device_active_status().await;
    let is_online = matches!(sim_status.state, SimulationState::Running)
        && device_active.get(&device_id).copied().unwrap_or(false);
    Ok(DeviceStatus {
        device_id,
        name,
        device_type: device_type_str,
        is_online,
        last_update,
        current_p_active: p_active,
        current_p_reactive: p_reactive,
        voltage: None,
        current: None,
    })
}
