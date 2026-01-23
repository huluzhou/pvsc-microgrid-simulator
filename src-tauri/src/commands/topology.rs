// 拓扑相关命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::domain::topology::{Topology, Device, Connection, DeviceType};
use crate::domain::metadata::DeviceMetadataStore;
use std::sync::Mutex;

#[derive(Debug, Serialize, Deserialize)]
pub struct TopologyData {
    pub devices: Vec<DeviceData>,
    pub connections: Vec<ConnectionData>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceData {
    pub id: String,
    pub name: String,
    pub device_type: String,
    pub properties: serde_json::Value,
    pub position: Option<PositionData>,
    pub location: Option<LocationData>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PositionData {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct LocationData {
    pub latitude: f64,
    pub longitude: f64,
    pub altitude: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ConnectionData {
    pub id: String,
    pub from: String,
    pub to: String,
    pub connection_type: String,
    pub properties: Option<serde_json::Value>,
}

fn parse_device_type(s: &str) -> Result<DeviceType, String> {
    match s.to_lowercase().as_str() {
        // 支持前端使用的类型名称
        "bus" | "node" => Ok(DeviceType::Node),
        "line" => Ok(DeviceType::Line),
        "transformer" => Ok(DeviceType::Transformer),
        "switch" => Ok(DeviceType::Switch),
        "static_generator" | "pv" => Ok(DeviceType::Pv),
        "storage" => Ok(DeviceType::Storage),
        "load" => Ok(DeviceType::Load),
        "charger" => Ok(DeviceType::Charger),
        "meter" => Ok(DeviceType::Meter),
        "external_grid" | "externalgrid" => Ok(DeviceType::ExternalGrid),
        _ => Err(format!("Unknown device type: {}", s)),
    }
}

/// 将 DeviceType 枚举转换为前端期望的字符串格式
fn device_type_to_string(device_type: &DeviceType) -> String {
    match device_type {
        DeviceType::Node => "bus".to_string(),
        DeviceType::Line => "line".to_string(),
        DeviceType::Transformer => "transformer".to_string(),
        DeviceType::Switch => "switch".to_string(),
        DeviceType::Pv => "static_generator".to_string(),
        DeviceType::Storage => "storage".to_string(),
        DeviceType::Load => "load".to_string(),
        DeviceType::Charger => "charger".to_string(),
        DeviceType::Meter => "meter".to_string(),
        DeviceType::ExternalGrid => "external_grid".to_string(),
    }
}

fn convert_topology_data(data: TopologyData) -> Result<Topology, String> {
    let mut topology = Topology::new(
        "default".to_string(),
        "Imported Topology".to_string(),
        "".to_string(),
    );

    // 转换设备
    for device_data in data.devices {
        let device_type = parse_device_type(&device_data.device_type)?;
        let mut properties = std::collections::HashMap::new();
        if let serde_json::Value::Object(map) = device_data.properties {
            for (k, v) in map {
                properties.insert(k, v);
            }
        }

        let position = device_data.position.map(|p| crate::domain::topology::Position {
            x: p.x,
            y: p.y,
            z: p.z,
        });

        let location = device_data.location.map(|l| crate::domain::topology::Location {
            latitude: l.latitude,
            longitude: l.longitude,
            altitude: l.altitude,
        });

        let device = Device {
            id: device_data.id,
            name: device_data.name,
            device_type,
            properties,
            position,
            location,
        };

        topology.add_device(device)?;
    }

    // 转换连接
    for (idx, conn_data) in data.connections.iter().enumerate() {
        let mut properties = std::collections::HashMap::new();
        if let Some(props) = &conn_data.properties {
            if let serde_json::Value::Object(map) = props {
                for (k, v) in map {
                    properties.insert(k.clone(), v.clone());
                }
            }
        }

        let connection = Connection {
            id: if conn_data.id.is_empty() {
                format!("conn-{}", idx)
            } else {
                conn_data.id.clone()
            },
            from_device_id: conn_data.from.clone(),
            to_device_id: conn_data.to.clone(),
            connection_type: conn_data.connection_type.clone(),
            properties,
            is_active: true,
        };

        topology.add_connection(connection)?;
    }

    Ok(topology)
}

#[tauri::command]
pub async fn save_topology(
    topology_data: TopologyData,
    path: String,
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<(), String> {
    let topology = convert_topology_data(topology_data)?;
    
    // 保存到文件
    let json = serde_json::to_string_pretty(&topology)
        .map_err(|e| format!("Failed to serialize topology: {}", e))?;
    std::fs::write(&path, json)
        .map_err(|e| format!("Failed to write file: {}", e))?;

    // 更新元数据仓库
    metadata_store.lock().unwrap().set_topology(topology);

    Ok(())
}

#[tauri::command]
pub async fn load_topology(
    path: String,
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<TopologyData, String> {
    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read file: {}", e))?;
    
    let topology: Topology = serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse topology: {}", e))?;

    // 更新元数据仓库
    metadata_store.lock().unwrap().set_topology(topology.clone());

    // 转换回 TopologyData
    let devices: Vec<DeviceData> = topology.devices.values().map(|d| {
        DeviceData {
            id: d.id.clone(),
            name: d.name.clone(),
            device_type: device_type_to_string(&d.device_type),
            properties: serde_json::to_value(&d.properties).unwrap_or(serde_json::Value::Object(serde_json::Map::new())),
            position: d.position.as_ref().map(|p| PositionData {
                x: p.x,
                y: p.y,
                z: p.z,
            }),
            location: d.location.as_ref().map(|l| LocationData {
                latitude: l.latitude,
                longitude: l.longitude,
                altitude: l.altitude,
            }),
        }
    }).collect();

    let connections: Vec<ConnectionData> = topology.connections.values().map(|c| {
        ConnectionData {
            id: c.id.clone(),
            from: c.from_device_id.clone(),
            to: c.to_device_id.clone(),
            connection_type: c.connection_type.clone(),
            properties: Some(serde_json::to_value(&c.properties).unwrap_or(serde_json::Value::Object(serde_json::Map::new()))),
        }
    }).collect();

    Ok(TopologyData { devices, connections })
}

#[tauri::command]
pub async fn validate_topology(
    topology_data: TopologyData,
) -> Result<Vec<String>, String> {
    let mut errors = Vec::new();

    match convert_topology_data(topology_data) {
        Ok(_) => {}
        Err(e) => errors.push(e),
    }

    Ok(errors)
}
