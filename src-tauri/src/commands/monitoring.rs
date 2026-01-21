// 监控相关命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::services::database::Database;
use crate::domain::metadata::DeviceMetadataStore;
use std::sync::Mutex;

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceDataPoint {
    pub device_id: String,
    pub timestamp: f64,
    pub voltage: Option<f64>,
    pub current: Option<f64>,
    pub power: Option<f64>,
    pub data_json: Option<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceStatus {
    pub device_id: String,
    pub name: String,
    pub is_online: bool,
    pub last_update: Option<f64>,
    pub current_voltage: Option<f64>,
    pub current_current: Option<f64>,
    pub current_power: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
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
    db: State<'_, Mutex<Database>>,
) -> Result<(), String> {
    let json_str = data.data_json.as_ref()
        .and_then(|v| serde_json::to_string(v).ok());
    
    let db = db.lock().unwrap();
    db.insert_device_data(
        &data.device_id,
        data.timestamp,
        data.voltage,
        data.current,
        data.power,
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
    db: State<'_, Mutex<Database>>,
) -> Result<Vec<(f64, Option<f64>, Option<f64>, Option<f64>)>, String> {
    let db = db.lock().unwrap();
    db.query_device_data(&device_id, start_time, end_time)
        .map_err(|e| format!("Failed to query device data: {}", e))
}

#[tauri::command]
pub async fn get_all_devices_status(
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
    db: State<'_, Mutex<Database>>,
) -> Result<Vec<DeviceStatus>, String> {
    let devices = {
        let metadata_store = metadata_store.lock().unwrap();
        metadata_store.get_all_devices()
    };
    
    let mut statuses = Vec::new();
    for device in devices {
        // 查询最新数据
        let recent_data = {
            let db = db.lock().unwrap();
            db.query_device_data(&device.id, None, None)
                .ok()
                .and_then(|data| data.last().cloned())
        };
        
        let (voltage, current, power, last_update) = if let Some((t, v, c, p)) = recent_data {
            (v, c, p, Some(t))
        } else {
            (None, None, None, None)
        };
        
        statuses.push(DeviceStatus {
            device_id: device.id.clone(),
            name: device.name.clone(),
            is_online: recent_data.is_some(),
            last_update,
            current_voltage: voltage,
            current_current: current,
            current_power: power,
        });
    }
    
    Ok(statuses)
}

#[tauri::command]
pub async fn get_device_status(
    device_id: String,
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
    db: State<'_, Mutex<Database>>,
) -> Result<DeviceStatus, String> {
    let metadata_store = metadata_store.lock().unwrap();
    let device = metadata_store.get_device(&device_id)
        .ok_or_else(|| format!("Device {} not found", device_id))?;
    
    let recent_data = {
        let db = db.lock().unwrap();
        db.query_device_data(&device_id, None, None)
            .ok()
            .and_then(|data| data.last().cloned())
    };
    
    let (voltage, current, power, last_update) = if let Some((t, v, c, p)) = recent_data {
        (v, c, p, Some(t))
    } else {
        (None, None, None, None)
    };
    
    Ok(DeviceStatus {
        device_id: device.id.clone(),
        name: device.name.clone(),
        is_online: recent_data.is_some(),
        last_update,
        current_voltage: voltage,
        current_current: current,
        current_power: power,
    })
}
