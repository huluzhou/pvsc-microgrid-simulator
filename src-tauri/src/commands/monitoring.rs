// 监控相关命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::services::database::Database;
use crate::services::simulation_engine::SimulationEngine;
use crate::domain::metadata::DeviceMetadataStore;
use crate::domain::simulation::SimulationState;
use crate::domain::topology::DeviceType;
use crate::commands::topology::device_type_to_string;
use crate::services::modbus::ModbusService;
use std::sync::{Arc, Mutex as StdMutex};
use std::collections::HashMap;

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
    /// 仅电表有值：指向的设备 id，用于监控界面按目标设备类型展示数据项
    #[serde(skip_serializing_if = "Option::is_none")]
    pub target_device_id: Option<String>,
    /// 仅电表有值：从 Modbus 快照读取的电量（单位 kWh/kVarh）
    #[serde(skip_serializing_if = "Option::is_none")]
    pub energy_export_kwh: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub energy_import_kwh: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub energy_total_kwh: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub energy_reactive_export_kvarh: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub energy_reactive_import_kvarh: Option<f64>,
    /// 仅储能有值：并离网模式，从 Modbus HR 5095 读取，0=并网 1=离网
    #[serde(skip_serializing_if = "Option::is_none")]
    pub grid_mode: Option<u16>,
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
    db: State<'_, Arc<StdMutex<Option<Database>>>>,
) -> Result<(), String> {
    let guard = db.lock().unwrap();
    let db = guard.as_ref().ok_or("尚未开始仿真，无数据库")?;
    let json_str = data.data_json.as_ref()
        .and_then(|v| serde_json::to_string(v).ok());
    db.insert_device_data(
        &data.device_id,
        data.timestamp,
        data.p_active,
        data.p_reactive,
        json_str.as_deref(),
        None,
    )
    .map_err(|e| format!("Failed to insert device data: {}", e))?;
    Ok(())
}

#[tauri::command]
pub async fn get_latest_simulation_start_time(
    db: State<'_, Arc<StdMutex<Option<Database>>>>,
) -> Result<Option<f64>, String> {
    let guard = db.lock().unwrap();
    match guard.as_ref() {
        Some(db) => db.get_latest_simulation_start().map_err(|e| format!("Failed to get latest simulation start: {}", e)),
        None => Ok(None),
    }
}

/// 返回当前仿真使用的数据库文件路径（每次启动仿真会切换到新文件 data_<timestamp>.db），供数据看板「当前应用数据库」与对话框默认路径使用。
#[tauri::command]
pub fn get_app_database_path(
    current_db_path: State<'_, Arc<StdMutex<String>>>,
) -> Result<String, String> {
    let path = current_db_path.lock().map_err(|_| "路径锁异常")?;
    Ok(path.clone())
}

#[derive(serde::Serialize)]
pub struct DashboardDeviceIdsResponse {
    pub device_ids: Vec<String>,
    #[serde(rename = "deviceTypes")]
    pub device_types: std::collections::HashMap<String, String>,
}

/// 从当前应用默认数据库读取 device_data 中所有不重复的 device_id 及 device_type（供数据看板「当前应用数据库」设备列表与类型）
#[tauri::command]
pub async fn get_dashboard_device_ids(db: State<'_, Arc<StdMutex<Option<Database>>>>) -> Result<DashboardDeviceIdsResponse, String> {
    let guard = db.lock().unwrap();
    let (device_ids, device_types) = match guard.as_ref() {
        Some(db) => match db.query_device_ids_with_types() {
            Ok(rows) => {
                let ids: Vec<String> = rows.iter().map(|(id, _)| id.clone()).collect();
                let types: std::collections::HashMap<String, String> = rows
                    .into_iter()
                    .filter_map(|(id, t)| t.map(|typ| (id, typ)))
                    .collect();
                (ids, types)
            }
            Err(_) => {
                let ids = db.query_device_ids().map_err(|e| format!("查询失败: {}", e))?;
                (ids, std::collections::HashMap::new())
            }
        },
        None => (Vec::new(), std::collections::HashMap::new()),
    };
    Ok(DashboardDeviceIdsResponse {
        device_ids,
        device_types,
    })
}

#[tauri::command]
pub async fn query_device_data(
    device_id: String,
    start_time: Option<f64>,
    end_time: Option<f64>,
    max_points: Option<usize>,
    db: State<'_, Arc<StdMutex<Option<Database>>>>,
) -> Result<Vec<DeviceDataPoint>, String> {
    let guard = db.lock().unwrap();
    let rows = match guard.as_ref() {
        Some(db) => db.query_device_data(&device_id, start_time, end_time, max_points)
            .map_err(|e| format!("Failed to query device data: {}", e))?,
        None => Vec::new(),
    };
    let points: Vec<DeviceDataPoint> = rows
        .into_iter()
        .map(|(ts, p_a, p_r, json_str)| {
            let data_json = json_str
                .as_ref()
                .and_then(|s| serde_json::from_str(s).ok());
            DeviceDataPoint {
                device_id: device_id.clone(),
                timestamp: ts,
                p_active: p_a,
                p_reactive: p_r,
                data_json,
            }
        })
        .collect();
    Ok(points)
}

/// 从拓扑构建电表 -> 连接设备 id（电表仅一条连接）
fn build_meter_connections(
    topology: &crate::domain::topology::Topology,
) -> HashMap<String, String> {
    let mut meter_connections: HashMap<String, String> = HashMap::new();
    for conn in topology.connections.values() {
        let from_id = &conn.from_device_id;
        let to_id = &conn.to_device_id;
        let from_is_meter = topology.devices.get(from_id).map(|d| d.device_type == DeviceType::Meter).unwrap_or(false);
        let to_is_meter = topology.devices.get(to_id).map(|d| d.device_type == DeviceType::Meter).unwrap_or(false);
        if from_is_meter {
            meter_connections.insert(from_id.clone(), to_id.clone());
        }
        if to_is_meter {
            meter_connections.insert(to_id.clone(), from_id.clone());
        }
    }
    meter_connections
}

/// 电表 Modbus 电量寄存器单位：1 寄存器 = 1 kWh / 1 kVarh（与 modbus_server 一致；前端显示时按 0.1 单位）
const METER_ENERGY_UNIT: f64 = 1.0;

#[tauri::command]
pub async fn get_all_devices_status(
    metadata_store: State<'_, StdMutex<DeviceMetadataStore>>,
    db: State<'_, Arc<StdMutex<Option<Database>>>>,
    engine: State<'_, Arc<SimulationEngine>>,
    modbus: State<'_, ModbusService>,
) -> Result<Vec<DeviceStatus>, String> {
    let devices = {
        let metadata_store = metadata_store.lock().unwrap();
        metadata_store.get_all_devices()
    };

    let topology = {
        let metadata_store = metadata_store.lock().unwrap();
        metadata_store.get_topology()
    };
    let meter_connections = topology.as_ref().map(build_meter_connections).unwrap_or_default();

    let sim_status = engine.get_status().await;
    let device_active = engine.get_device_active_status().await;
    let is_online_from_engine = |device_id: &str| -> bool {
        matches!(sim_status.state, SimulationState::Running)
            && device_active.get(device_id).copied().unwrap_or(false)
    };

    let mut statuses = Vec::new();
    for device in devices {
        let (p_active, p_reactive, last_update) = if let Some((t, p_a, p_r)) = engine.get_last_device_power(&device.id) {
            (p_a, p_r, Some(t))
        } else if device.device_type == DeviceType::Meter {
            if let Some(target_id) = meter_connections.get(&device.id) {
                let recent = {
                    let guard = db.lock().unwrap();
                    guard.as_ref().and_then(|db| db.query_device_data_latest(target_id).ok().flatten())
                };
                if let Some((t, p_a, p_r, _)) = recent {
                    (p_a, p_r, Some(t))
                } else {
                    (None, None, None)
                }
            } else {
                (None, None, None)
            }
        } else {
            let recent = {
                let guard = db.lock().unwrap();
                guard.as_ref().and_then(|db| db.query_device_data_latest(&device.id).ok().flatten())
            };
            if let Some((t, p_a, p_r, _)) = recent {
                (p_a, p_r, Some(t))
            } else {
                (None, None, None)
            }
        };

        let target_device_id = if device.device_type == DeviceType::Meter {
            meter_connections.get(&device.id).cloned()
        } else {
            None
        };

        // 电表：从 Modbus 快照读取电量寄存器 7,8,9,10,11（单位 1 kWh / 1 kVarh）
        let (energy_export_kwh, energy_import_kwh, energy_total_kwh, energy_reactive_export_kvarh, energy_reactive_import_kvarh) =
            if device.device_type == DeviceType::Meter {
                if let Some((ir, _hr)) = modbus.get_device_register_snapshot(&device.id).await {
                    let read = |addr: u16| ir.get(&addr).copied().unwrap_or(0) as f64 * METER_ENERGY_UNIT;
                    (
                        Some(read(7)),
                        Some(read(8)),
                        Some(read(9)),
                        Some(read(10)),
                        Some(read(11)),
                    )
                } else {
                    (None, None, None, None, None)
                }
            } else {
                (None, None, None, None, None)
            };

        // 储能：从 Modbus 快照读 HR 5095 并离网模式（0=并网 1=离网）
        let grid_mode = if device.device_type == DeviceType::Storage {
            modbus.get_device_register_snapshot(&device.id).await
                .and_then(|(_, hr)| hr.get(&5095).copied())
        } else {
            None
        };

        statuses.push(DeviceStatus {
            device_id: device.id.clone(),
            name: device.name.clone(),
            device_type: device_type_to_string(&device.device_type),
            is_online: is_online_from_engine(&device.id),
            last_update,
            current_p_active: p_active,
            current_p_reactive: p_reactive,
            target_device_id,
            energy_export_kwh,
            energy_import_kwh,
            energy_total_kwh,
            energy_reactive_export_kvarh,
            energy_reactive_import_kvarh,
            grid_mode,
        });
    }

    Ok(statuses)
}

#[tauri::command]
pub async fn get_device_status(
    device_id: String,
    metadata_store: State<'_, StdMutex<DeviceMetadataStore>>,
    db: State<'_, Arc<StdMutex<Option<Database>>>>,
    engine: State<'_, Arc<SimulationEngine>>,
    modbus: State<'_, ModbusService>,
) -> Result<DeviceStatus, String> {
    let (name, device_type_str, device_type) = {
        let store = metadata_store.lock().unwrap();
        let device = store.get_device(&device_id)
            .ok_or_else(|| format!("Device {} not found", device_id))?;
        (device.name.clone(), device_type_to_string(&device.device_type), device.device_type.clone())
    };

    let (p_active, p_reactive, last_update) = if let Some((t, p_a, p_r)) = engine.get_last_device_power(&device_id) {
        (p_a, p_r, Some(t))
    } else if device_type == DeviceType::Meter {
        let topology = {
            let store = metadata_store.lock().unwrap();
            store.get_topology()
        };
        let target_id = topology.as_ref()
            .and_then(|t| build_meter_connections(t).get(&device_id).cloned());
        if let Some(tid) = target_id {
            let recent = {
                let guard = db.lock().unwrap();
                guard.as_ref().and_then(|db| db.query_device_data_latest(&tid).ok().flatten())
            };
            if let Some((t, p_a, p_r, _)) = recent {
                (p_a, p_r, Some(t))
            } else {
                (None, None, None)
            }
        } else {
            (None, None, None)
        }
    } else {
        let recent = {
            let guard = db.lock().unwrap();
            guard.as_ref().and_then(|db| db.query_device_data_latest(&device_id).ok().flatten())
        };
        if let Some((t, p_a, p_r, _)) = recent {
            (p_a, p_r, Some(t))
        } else {
            (None, None, None)
        }
    };

    let sim_status = engine.get_status().await;
    let device_active = engine.get_device_active_status().await;
    let is_online = matches!(sim_status.state, SimulationState::Running)
        && device_active.get(&device_id).copied().unwrap_or(false);

    let target_device_id = if device_type == DeviceType::Meter {
        let topo = {
            let store = metadata_store.lock().unwrap();
            store.get_topology()
        };
        topo.as_ref()
            .and_then(|t| build_meter_connections(t).get(&device_id).cloned())
    } else {
        None
    };

    let (energy_export_kwh, energy_import_kwh, energy_total_kwh, energy_reactive_export_kvarh, energy_reactive_import_kvarh) =
        if device_type == DeviceType::Meter {
            if let Some((ir, _hr)) = modbus.get_device_register_snapshot(&device_id).await {
                let read = |addr: u16| ir.get(&addr).copied().unwrap_or(0) as f64 * METER_ENERGY_UNIT;
                (
                    Some(read(7)),
                    Some(read(8)),
                    Some(read(9)),
                    Some(read(10)),
                    Some(read(11)),
                )
            } else {
                (None, None, None, None, None)
            }
        } else {
            (None, None, None, None, None)
        };

    let grid_mode = if device_type == DeviceType::Storage {
        modbus.get_device_register_snapshot(&device_id).await
            .and_then(|(_, hr)| hr.get(&5095).copied())
    } else {
        None
    };

    Ok(DeviceStatus {
        device_id,
        name,
        device_type: device_type_str,
        is_online,
        last_update,
        current_p_active: p_active,
        current_p_reactive: p_reactive,
        target_device_id,
        energy_export_kwh,
        energy_import_kwh,
        energy_total_kwh,
        energy_reactive_export_kvarh,
        energy_reactive_import_kvarh,
        grid_mode,
    })
}
