// 仿真引擎命令
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, State};
use crate::services::simulation_engine::SimulationEngine;
use crate::domain::simulation::{SimulationStatus, SimulationError};
use crate::domain::metadata::DeviceMetadataStore;
use std::sync::{Arc, Mutex};
use rusqlite::Connection;

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

    engine.set_remote_control_enabled(config.remote_control_enabled);
    
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
pub async fn set_device_random_config(
    device_id: String,
    min_power: f64,
    max_power: f64,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.set_device_random_config(device_id, min_power, max_power).await
}

#[tauri::command]
pub async fn set_device_manual_setpoint(
    device_id: String,
    active_power: f64,
    reactive_power: f64,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine
        .set_device_manual_setpoint(device_id, active_power, reactive_power)
        .await
}

#[tauri::command]
pub async fn set_device_historical_config(
    device_id: String,
    config: serde_json::Value,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.set_device_historical_config(device_id, config).await
}

#[tauri::command]
pub async fn set_device_sim_params(
    device_id: String,
    params: serde_json::Value,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.set_device_sim_params(device_id, params).await
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

#[tauri::command]
pub async fn set_remote_control_enabled(
    enabled: bool,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.set_remote_control_enabled(enabled);
    Ok(())
}

#[tauri::command]
pub async fn set_device_remote_control_enabled(
    device_id: String,
    enabled: bool,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.set_device_remote_control_enabled(device_id, enabled).await;
    Ok(())
}

/// 推送到计算内核前经 Modbus 指令过滤：可根据设备寄存器映射校验/合并；当前为透传。
#[tauri::command]
pub async fn update_device_properties_for_simulation(
    device_id: String,
    properties: serde_json::Value,
    engine: State<'_, Arc<SimulationEngine>>,
    modbus_service: State<'_, crate::services::modbus::ModbusService>,
) -> Result<(), String> {
    let _mapping = modbus_service.get_device_mapping(&device_id);
    engine
        .update_device_properties_for_simulation(device_id, properties)
        .await
}

/// 更新开关状态（同时更新 Python 仿真、Rust 元数据与拓扑，保证再次打开面板时显示实际状态）
#[tauri::command]
pub async fn update_switch_state(
    device_id: String,
    is_closed: bool,
    engine: State<'_, Arc<SimulationEngine>>,
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<(), String> {
    engine.update_switch_state(device_id.clone(), is_closed).await?;
    // 同步更新元数据中的 is_closed，使 get_all_devices 与再次打开开关面板时显示实际状态
    if let Some(mut device) = metadata_store.lock().unwrap().get_device(&device_id) {
        device.properties.insert("is_closed".to_string(), serde_json::json!(is_closed));
        metadata_store.lock().unwrap().update_device(device)?;
    }
    Ok(())
}

/// 读取 SQLite 数据库中的设备列表（device_data 表中的 distinct device_id）
#[tauri::command]
pub async fn list_sqlite_devices(file_path: String) -> Result<Vec<String>, String> {
    let conn = Connection::open(&file_path)
        .map_err(|e| format!("无法打开 SQLite 文件: {}", e))?;
    let mut stmt = conn
        .prepare("SELECT DISTINCT device_id FROM device_data ORDER BY device_id")
        .map_err(|e| format!("查询失败: {}", e))?;
    let devices: Vec<String> = stmt
        .query_map([], |row| row.get(0))
        .map_err(|e| format!("查询失败: {}", e))?
        .filter_map(|r| r.ok())
        .collect();
    Ok(devices)
}

/// 获取 SQLite/CSV 中指定设备的时间范围（返回 Unix 秒 [min, max]）
#[tauri::command]
pub async fn get_historical_time_range(
    file_path: String,
    source_type: String,
    source_device_id: Option<String>,
) -> Result<(f64, f64), String> {
    match source_type.as_str() {
        "sqlite" => {
            let conn = Connection::open(&file_path)
                .map_err(|e| format!("无法打开 SQLite 文件: {}", e))?;
            let sql = if let Some(ref did) = source_device_id {
                format!(
                    "SELECT MIN(timestamp), MAX(timestamp) FROM device_data WHERE device_id = '{}'",
                    did.replace('\'', "''")
                )
            } else {
                "SELECT MIN(timestamp), MAX(timestamp) FROM device_data".to_string()
            };
            let (t_min, t_max): (f64, f64) = conn
                .query_row(&sql, [], |row| Ok((row.get(0)?, row.get(1)?)))
                .map_err(|e| format!("查询时间范围失败: {}", e))?;
            Ok((t_min, t_max))
        }
        _ => {
            // CSV: 需要遍历文件读取时间列，这里暂返回占位，前端可根据文件内容做预览
            Err("CSV 时间范围查询请在前端解析".to_string())
        }
    }
}
