// 拓扑相关命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::domain::topology::{Topology, Device, Connection, DeviceType};
use crate::domain::metadata::DeviceMetadataStore;
use std::sync::Mutex;
use std::collections::HashMap;

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
    /// 源设备的连接点 ID（如 "top", "bottom", "center" 等）
    #[serde(default)]
    pub from_port: Option<String>,
    /// 目标设备的连接点 ID
    #[serde(default)]
    pub to_port: Option<String>,
    pub connection_type: String,
    pub properties: Option<serde_json::Value>,
}

/// 验证结果
#[derive(Debug, Serialize, Deserialize)]
pub struct ValidationResult {
    pub valid: bool,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
}

/// 加载和验证拓扑的返回结果
#[derive(Debug, Serialize, Deserialize)]
pub struct LoadAndValidateResult {
    pub data: TopologyData,
    pub validation: ValidationResult,
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
            from_port: conn_data.from_port.clone(),
            to_port: conn_data.to_port.clone(),
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

/// 将拓扑数据转换为旧格式（pandapower 格式）
fn convert_to_legacy_format(data: &TopologyData) -> serde_json::Value {
    let mut result = serde_json::Map::new();
    
    // 建立设备类型映射
    let device_types: HashMap<String, String> = data.devices.iter()
        .map(|d| (d.id.clone(), d.device_type.clone()))
        .collect();
    
    // 按类型分组设备，并分配 index
    let mut bus_list: Vec<serde_json::Value> = Vec::new();
    let mut line_list: Vec<serde_json::Value> = Vec::new();
    let mut transformer_list: Vec<serde_json::Value> = Vec::new();
    let mut load_list: Vec<serde_json::Value> = Vec::new();
    let mut sgen_list: Vec<serde_json::Value> = Vec::new();
    let mut storage_list: Vec<serde_json::Value> = Vec::new();
    let mut charger_list: Vec<serde_json::Value> = Vec::new();
    let mut ext_grid_list: Vec<serde_json::Value> = Vec::new();
    let mut measurement_list: Vec<serde_json::Value> = Vec::new();
    let mut switch_list: Vec<serde_json::Value> = Vec::new();
    
    // 设备 ID 到 index 的映射
    let mut device_to_index: HashMap<String, (String, i64)> = HashMap::new(); // id -> (type, index)
    
    // 第一遍：分配 index 给所有设备
    for device in &data.devices {
        let (legacy_type, index) = match device.device_type.as_str() {
            "bus" => {
                let idx = bus_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Bus".to_string(), idx));
                ("Bus", idx)
            },
            "line" => {
                let idx = line_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Line".to_string(), idx));
                line_list.push(serde_json::Value::Null); // 占位
                ("Line", idx)
            },
            "transformer" => {
                let idx = transformer_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Transformer".to_string(), idx));
                transformer_list.push(serde_json::Value::Null); // 占位
                ("Transformer", idx)
            },
            "load" => {
                let idx = load_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Load".to_string(), idx));
                load_list.push(serde_json::Value::Null); // 占位
                ("Load", idx)
            },
            "static_generator" => {
                let idx = sgen_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Static_Generator".to_string(), idx));
                sgen_list.push(serde_json::Value::Null); // 占位
                ("Static_Generator", idx)
            },
            "storage" => {
                let idx = storage_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Storage".to_string(), idx));
                storage_list.push(serde_json::Value::Null); // 占位
                ("Storage", idx)
            },
            "charger" => {
                let idx = charger_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Charger".to_string(), idx));
                charger_list.push(serde_json::Value::Null); // 占位
                ("Charger", idx)
            },
            "external_grid" => {
                let idx = ext_grid_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("External_Grid".to_string(), idx));
                ext_grid_list.push(serde_json::Value::Null); // 占位
                ("External_Grid", idx)
            },
            "meter" => {
                let idx = measurement_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Measurement".to_string(), idx));
                measurement_list.push(serde_json::Value::Null); // 占位
                ("Measurement", idx)
            },
            "switch" => {
                let idx = switch_list.len() as i64;
                device_to_index.insert(device.id.clone(), ("Switch".to_string(), idx));
                switch_list.push(serde_json::Value::Null); // 占位
                ("Switch", idx)
            },
            _ => continue,
        };
        
        // 母线直接添加
        if legacy_type == "Bus" {
            let mut obj = serde_json::Map::new();
            obj.insert("name".to_string(), serde_json::Value::String(device.name.clone()));
            obj.insert("index".to_string(), serde_json::Value::Number(serde_json::Number::from(index)));
            // 添加属性
            if let serde_json::Value::Object(props) = &device.properties {
                for (k, v) in props {
                    obj.insert(k.clone(), v.clone());
                }
            }
            bus_list.push(serde_json::Value::Object(obj));
        }
    }
    
    // 分析连接关系，构建 from_bus/to_bus 等
    let mut line_connections: HashMap<String, (Option<i64>, Option<i64>)> = HashMap::new(); // line_id -> (from_bus, to_bus)
    let mut trafo_connections: HashMap<String, (Option<i64>, Option<i64>)> = HashMap::new(); // trafo_id -> (hv_bus, lv_bus)
    let mut power_device_bus: HashMap<String, i64> = HashMap::new(); // device_id -> bus_index
    let mut meter_targets: HashMap<String, (String, i64, Option<String>)> = HashMap::new(); // meter_id -> (element_type, element_index, side)
    
    for conn in &data.connections {
        let from_type = device_types.get(&conn.from).map(|s| s.as_str()).unwrap_or("unknown");
        let to_type = device_types.get(&conn.to).map(|s| s.as_str()).unwrap_or("unknown");
        
        // 线路连接
        if from_type == "line" && to_type == "bus" {
            if let Some((_, bus_idx)) = device_to_index.get(&conn.to) {
                let entry = line_connections.entry(conn.from.clone()).or_insert((None, None));
                // 根据连接属性判断是 from_bus 还是 to_bus
                let port = conn.properties.as_ref()
                    .and_then(|p| p.get("port"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("from_bus");
                if port == "to_bus" {
                    entry.1 = Some(*bus_idx);
                } else {
                    if entry.0.is_none() { entry.0 = Some(*bus_idx); }
                    else { entry.1 = Some(*bus_idx); }
                }
            }
        }
        if to_type == "line" && from_type == "bus" {
            if let Some((_, bus_idx)) = device_to_index.get(&conn.from) {
                let entry = line_connections.entry(conn.to.clone()).or_insert((None, None));
                let port = conn.properties.as_ref()
                    .and_then(|p| p.get("port"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("from_bus");
                if port == "to_bus" {
                    entry.1 = Some(*bus_idx);
                } else {
                    if entry.0.is_none() { entry.0 = Some(*bus_idx); }
                    else { entry.1 = Some(*bus_idx); }
                }
            }
        }
        
        // 变压器连接
        if from_type == "transformer" && to_type == "bus" {
            if let Some((_, bus_idx)) = device_to_index.get(&conn.to) {
                let entry = trafo_connections.entry(conn.from.clone()).or_insert((None, None));
                let port = conn.properties.as_ref()
                    .and_then(|p| p.get("port"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("hv_bus");
                if port == "lv_bus" {
                    entry.1 = Some(*bus_idx);
                } else {
                    if entry.0.is_none() { entry.0 = Some(*bus_idx); }
                    else { entry.1 = Some(*bus_idx); }
                }
            }
        }
        if to_type == "transformer" && from_type == "bus" {
            if let Some((_, bus_idx)) = device_to_index.get(&conn.from) {
                let entry = trafo_connections.entry(conn.to.clone()).or_insert((None, None));
                let port = conn.properties.as_ref()
                    .and_then(|p| p.get("port"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("hv_bus");
                if port == "lv_bus" {
                    entry.1 = Some(*bus_idx);
                } else {
                    if entry.0.is_none() { entry.0 = Some(*bus_idx); }
                    else { entry.1 = Some(*bus_idx); }
                }
            }
        }
        
        // 功率设备连接母线
        let power_types = ["load", "static_generator", "storage", "charger", "external_grid"];
        if power_types.contains(&from_type) && to_type == "bus" {
            if let Some((_, bus_idx)) = device_to_index.get(&conn.to) {
                power_device_bus.insert(conn.from.clone(), *bus_idx);
            }
        }
        if power_types.contains(&to_type) && from_type == "bus" {
            if let Some((_, bus_idx)) = device_to_index.get(&conn.from) {
                power_device_bus.insert(conn.to.clone(), *bus_idx);
            }
        }
        
        // 电表连接
        if from_type == "meter" {
            if let Some((element_type, element_idx)) = device_to_index.get(&conn.to) {
                let side = conn.properties.as_ref()
                    .and_then(|p| p.get("side"))
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string());
                let et = match element_type.as_str() {
                    "Bus" => "bus",
                    "Line" => "line",
                    "Transformer" => "trafo",
                    "Load" => "load",
                    "Static_Generator" => "sgen",
                    "Storage" => "storage",
                    "Charger" => "charger",
                    "External_Grid" => "ext_grid",
                    _ => "unknown",
                };
                meter_targets.insert(conn.from.clone(), (et.to_string(), *element_idx, side));
            }
        }
        if to_type == "meter" {
            if let Some((element_type, element_idx)) = device_to_index.get(&conn.from) {
                let side = conn.properties.as_ref()
                    .and_then(|p| p.get("side"))
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string());
                let et = match element_type.as_str() {
                    "Bus" => "bus",
                    "Line" => "line",
                    "Transformer" => "trafo",
                    "Load" => "load",
                    "Static_Generator" => "sgen",
                    "Storage" => "storage",
                    "Charger" => "charger",
                    "External_Grid" => "ext_grid",
                    _ => "unknown",
                };
                meter_targets.insert(conn.to.clone(), (et.to_string(), *element_idx, side));
            }
        }
    }
    
    // 第二遍：构建设备对象
    for device in &data.devices {
        let mut obj = serde_json::Map::new();
        obj.insert("name".to_string(), serde_json::Value::String(device.name.clone()));
        
        if let Some((_, index)) = device_to_index.get(&device.id) {
            obj.insert("index".to_string(), serde_json::Value::Number(serde_json::Number::from(*index)));
        }
        
        // 添加属性
        if let serde_json::Value::Object(props) = &device.properties {
            for (k, v) in props {
                obj.insert(k.clone(), v.clone());
            }
        }
        
        match device.device_type.as_str() {
            "line" => {
                if let Some((from_bus, to_bus)) = line_connections.get(&device.id) {
                    if let Some(fb) = from_bus {
                        obj.insert("from_bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*fb)));
                    }
                    if let Some(tb) = to_bus {
                        obj.insert("to_bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*tb)));
                    }
                }
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    line_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            "transformer" => {
                if let Some((hv_bus, lv_bus)) = trafo_connections.get(&device.id) {
                    if let Some(hb) = hv_bus {
                        obj.insert("hv_bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*hb)));
                    }
                    if let Some(lb) = lv_bus {
                        obj.insert("lv_bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*lb)));
                    }
                }
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    transformer_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            "load" => {
                if let Some(bus_idx) = power_device_bus.get(&device.id) {
                    obj.insert("bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*bus_idx)));
                }
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    load_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            "static_generator" => {
                if let Some(bus_idx) = power_device_bus.get(&device.id) {
                    obj.insert("bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*bus_idx)));
                }
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    sgen_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            "storage" => {
                if let Some(bus_idx) = power_device_bus.get(&device.id) {
                    obj.insert("bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*bus_idx)));
                }
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    storage_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            "charger" => {
                if let Some(bus_idx) = power_device_bus.get(&device.id) {
                    obj.insert("bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*bus_idx)));
                }
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    charger_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            "external_grid" => {
                if let Some(bus_idx) = power_device_bus.get(&device.id) {
                    obj.insert("bus".to_string(), serde_json::Value::Number(serde_json::Number::from(*bus_idx)));
                }
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    ext_grid_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            "meter" => {
                if let Some((element_type, element_idx, side)) = meter_targets.get(&device.id) {
                    obj.insert("element_type".to_string(), serde_json::Value::String(element_type.clone()));
                    obj.insert("element".to_string(), serde_json::Value::Number(serde_json::Number::from(*element_idx)));
                    if let Some(s) = side {
                        obj.insert("side".to_string(), serde_json::Value::String(s.clone()));
                    } else {
                        obj.insert("side".to_string(), serde_json::Value::Null);
                    }
                    if !obj.contains_key("meas_type") {
                        obj.insert("meas_type".to_string(), serde_json::Value::String("p".to_string()));
                    }
                }
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    measurement_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            "switch" => {
                // 开关暂不在旧格式中输出（pandapower 的 switch 处理较复杂）
                if let Some((_, idx)) = device_to_index.get(&device.id) {
                    switch_list[*idx as usize] = serde_json::Value::Object(obj);
                }
            },
            _ => {}
        }
    }
    
    // 构建结果
    if !bus_list.is_empty() {
        result.insert("Bus".to_string(), serde_json::Value::Array(bus_list));
    }
    // 过滤掉 null 占位符
    let line_list: Vec<_> = line_list.into_iter().filter(|v| !v.is_null()).collect();
    if !line_list.is_empty() {
        result.insert("Line".to_string(), serde_json::Value::Array(line_list));
    }
    let transformer_list: Vec<_> = transformer_list.into_iter().filter(|v| !v.is_null()).collect();
    if !transformer_list.is_empty() {
        result.insert("Transformer".to_string(), serde_json::Value::Array(transformer_list));
    }
    let load_list: Vec<_> = load_list.into_iter().filter(|v| !v.is_null()).collect();
    if !load_list.is_empty() {
        result.insert("Load".to_string(), serde_json::Value::Array(load_list));
    }
    let sgen_list: Vec<_> = sgen_list.into_iter().filter(|v| !v.is_null()).collect();
    if !sgen_list.is_empty() {
        result.insert("Static_Generator".to_string(), serde_json::Value::Array(sgen_list));
    }
    let storage_list: Vec<_> = storage_list.into_iter().filter(|v| !v.is_null()).collect();
    if !storage_list.is_empty() {
        result.insert("Storage".to_string(), serde_json::Value::Array(storage_list));
    }
    let charger_list: Vec<_> = charger_list.into_iter().filter(|v| !v.is_null()).collect();
    if !charger_list.is_empty() {
        result.insert("Charger".to_string(), serde_json::Value::Array(charger_list));
    }
    let ext_grid_list: Vec<_> = ext_grid_list.into_iter().filter(|v| !v.is_null()).collect();
    if !ext_grid_list.is_empty() {
        result.insert("External_Grid".to_string(), serde_json::Value::Array(ext_grid_list));
    }
    let measurement_list: Vec<_> = measurement_list.into_iter().filter(|v| !v.is_null()).collect();
    if !measurement_list.is_empty() {
        result.insert("Measurement".to_string(), serde_json::Value::Array(measurement_list));
    }
    
    serde_json::Value::Object(result)
}

/// 保存拓扑为旧格式（pandapower 格式）
#[tauri::command]
pub async fn save_topology_legacy(
    topology_data: TopologyData,
    path: String,
) -> Result<(), String> {
    let legacy_data = convert_to_legacy_format(&topology_data);
    
    let json = serde_json::to_string_pretty(&legacy_data)
        .map_err(|e| format!("Failed to serialize topology: {}", e))?;
    std::fs::write(&path, json)
        .map_err(|e| format!("Failed to write file: {}", e))?;

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
            from_port: c.from_port.clone(),
            to_port: c.to_port.clone(),
            connection_type: c.connection_type.clone(),
            properties: Some(serde_json::to_value(&c.properties).unwrap_or(serde_json::Value::Object(serde_json::Map::new()))),
        }
    }).collect();

    Ok(TopologyData { devices, connections })
}

/// 验证拓扑连接规则（参考 doc/TopoRule.md）
fn validate_topology_rules(data: &TopologyData) -> ValidationResult {
    let mut errors = Vec::new();
    let mut warnings = Vec::new();

    // 建立设备类型和名称映射
    let device_types: HashMap<String, String> = data.devices.iter()
        .map(|d| (d.id.clone(), d.device_type.clone()))
        .collect();
    let device_names: HashMap<String, String> = data.devices.iter()
        .map(|d| (d.id.clone(), d.name.clone()))
        .collect();

    let get_name = |id: &str| -> String {
        device_names.get(id).cloned().unwrap_or_else(|| id.to_string())
    };

    // === 全局约束 ===
    
    // 1. 外部电网设备全局仅允许 1 个
    let external_grid_count = data.devices.iter()
        .filter(|d| d.device_type == "external_grid")
        .count();
    if external_grid_count > 1 {
        errors.push(format!("外部电网设备数量超过限制：当前 {} 个，最多允许 1 个", external_grid_count));
    }

    // 2. 检查重复连接
    let mut connection_pairs: std::collections::HashSet<(String, String)> = std::collections::HashSet::new();
    for conn in &data.connections {
        let pair = if conn.from < conn.to {
            (conn.from.clone(), conn.to.clone())
        } else {
            (conn.to.clone(), conn.from.clone())
        };
        if !connection_pairs.insert(pair.clone()) {
            errors.push(format!("存在重复连接：{} <-> {}", get_name(&pair.0), get_name(&pair.1)));
        }
    }

    // === 统计各设备的连接情况 ===
    let mut device_to_bus: HashMap<String, Vec<String>> = HashMap::new();      // 设备 -> 连接的母线列表
    let mut device_to_switch: HashMap<String, Vec<String>> = HashMap::new();   // 设备 -> 连接的开关列表
    let mut device_to_meter: HashMap<String, Vec<String>> = HashMap::new();    // 设备 -> 连接的电表列表
    let mut meter_connections: HashMap<String, Vec<String>> = HashMap::new();  // 电表 -> 连接的设备列表
    let mut switch_to_bus: HashMap<String, Vec<String>> = HashMap::new();      // 开关 -> 连接的母线列表

    // 分析每个连接
    for conn in &data.connections {
        let from_type = device_types.get(&conn.from).map(|s| s.as_str()).unwrap_or("unknown");
        let to_type = device_types.get(&conn.to).map(|s| s.as_str()).unwrap_or("unknown");

        // 3. 不允许母线与母线直接连接
        if from_type == "bus" && to_type == "bus" {
            errors.push(format!("不允许母线与母线直接连接：{} <-> {}", get_name(&conn.from), get_name(&conn.to)));
        }

        // 记录设备到母线的连接
        if from_type == "bus" {
            device_to_bus.entry(conn.to.clone()).or_default().push(conn.from.clone());
        }
        if to_type == "bus" {
            device_to_bus.entry(conn.from.clone()).or_default().push(conn.to.clone());
        }

        // 记录设备到开关的连接
        if from_type == "switch" {
            device_to_switch.entry(conn.to.clone()).or_default().push(conn.from.clone());
        }
        if to_type == "switch" {
            device_to_switch.entry(conn.from.clone()).or_default().push(conn.to.clone());
        }

        // 记录开关到母线的连接
        if from_type == "switch" && to_type == "bus" {
            switch_to_bus.entry(conn.from.clone()).or_default().push(conn.to.clone());
        }
        if to_type == "switch" && from_type == "bus" {
            switch_to_bus.entry(conn.to.clone()).or_default().push(conn.from.clone());
        }

        // 记录电表连接
        if from_type == "meter" {
            meter_connections.entry(conn.from.clone()).or_default().push(conn.to.clone());
            device_to_meter.entry(conn.to.clone()).or_default().push(conn.from.clone());
        }
        if to_type == "meter" {
            meter_connections.entry(conn.to.clone()).or_default().push(conn.from.clone());
            device_to_meter.entry(conn.from.clone()).or_default().push(conn.to.clone());
        }

        // === 功率设备规则 ===
        let power_devices = ["static_generator", "storage", "load", "charger", "external_grid"];
        
        // 功率设备只能连接母线或电表，不能连接开关/线路/变压器
        if power_devices.contains(&from_type) {
            if to_type != "bus" && to_type != "meter" {
                errors.push(format!("功率设备 {} 只能连接母线或电表，不能连接 {} ({})", 
                    get_name(&conn.from), to_type, get_name(&conn.to)));
            }
        }
        if power_devices.contains(&to_type) {
            if from_type != "bus" && from_type != "meter" {
                errors.push(format!("功率设备 {} 只能连接母线或电表，不能连接 {} ({})", 
                    get_name(&conn.to), from_type, get_name(&conn.from)));
            }
        }
    }

    // === 功率设备约束 ===
    let power_devices = ["static_generator", "storage", "load", "charger", "external_grid"];
    for device in &data.devices {
        if power_devices.contains(&device.device_type.as_str()) {
            // 功率设备仅允许与 1 个母线连接
            if let Some(buses) = device_to_bus.get(&device.id) {
                if buses.len() > 1 {
                    errors.push(format!("功率设备 {} 连接了多个母线，只允许连接 1 个", device.name));
                }
            }
            // 功率设备最多连接 1 个电表
            if let Some(meters) = device_to_meter.get(&device.id) {
                if meters.len() > 1 {
                    errors.push(format!("功率设备 {} 连接了多个电表，最多允许 1 个", device.name));
                }
            }
        }
    }

    // === 线路规则 ===
    for device in &data.devices {
        if device.device_type == "line" {
            // 检查是否两端同时连接开关（禁止）
            if let Some(switches) = device_to_switch.get(&device.id) {
                if switches.len() >= 2 {
                    errors.push(format!("线路 {} 两端同时连接开关，这是不允许的", device.name));
                }
            }
            // 线路每端只能连接 1 个母线或 1 个开关
            let bus_count = device_to_bus.get(&device.id).map(|v| v.len()).unwrap_or(0);
            let switch_count = device_to_switch.get(&device.id).map(|v| v.len()).unwrap_or(0);
            if bus_count + switch_count > 2 {
                errors.push(format!("线路 {} 连接点数量超过限制（最多 2 个母线/开关组合）", device.name));
            }
        }
    }

    // === 变压器规则 ===
    for device in &data.devices {
        if device.device_type == "transformer" {
            // 检查是否两端同时连接开关（禁止）
            if let Some(switches) = device_to_switch.get(&device.id) {
                if switches.len() >= 2 {
                    errors.push(format!("变压器 {} 两端同时连接开关，这是不允许的", device.name));
                }
            }
            // 变压器每端只能连接 1 个母线或 1 个开关
            let bus_count = device_to_bus.get(&device.id).map(|v| v.len()).unwrap_or(0);
            let switch_count = device_to_switch.get(&device.id).map(|v| v.len()).unwrap_or(0);
            if bus_count + switch_count > 2 {
                errors.push(format!("变压器 {} 连接点数量超过限制（最多 2 个母线/开关组合）", device.name));
            }
        }
    }

    // === 开关规则 ===
    // 统计开关的总连接数（用于判断是否形成闭合连接）
    let mut switch_total_connections: HashMap<String, usize> = HashMap::new();
    for conn in &data.connections {
        let from_type = device_types.get(&conn.from).map(|s| s.as_str()).unwrap_or("unknown");
        let to_type = device_types.get(&conn.to).map(|s| s.as_str()).unwrap_or("unknown");
        if from_type == "switch" {
            *switch_total_connections.entry(conn.from.clone()).or_insert(0) += 1;
        }
        if to_type == "switch" {
            *switch_total_connections.entry(conn.to.clone()).or_insert(0) += 1;
        }
    }

    for device in &data.devices {
        if device.device_type == "switch" {
            let bus_count = switch_to_bus.get(&device.id).map(|v| v.len()).unwrap_or(0);
            let total_connections = switch_total_connections.get(&device.id).copied().unwrap_or(0);
            
            // 稳态约束：至少一端必须连接母线
            if bus_count == 0 {
                if total_connections >= 2 {
                    // 开关两端都已连接（形成闭合连接），但没有母线连接 -> 错误
                    errors.push(format!("开关 {} 已形成闭合连接但没有连接母线，稳态运行要求至少一端连接母线", device.name));
                } else if total_connections == 1 {
                    // 开关只有一端连接，且没有母线 -> 警告（可能还在搭建中）
                    warnings.push(format!("开关 {} 只有一端连接且未连接母线，稳态运行要求至少一端连接母线", device.name));
                }
            }
        }
    }

    // === 电表规则 ===
    for device in &data.devices {
        if device.device_type == "meter" {
            // 每个电表自身仅允许 1 条连接
            if let Some(connections) = meter_connections.get(&device.id) {
                if connections.len() > 1 {
                    errors.push(format!("电表 {} 有多条连接，每个电表只允许 1 条连接", device.name));
                }
            }
        }
    }

    // 检查目标端口的电表数量（每个目标端口仅允许 1 个电表）
    for (device_id, meters) in &device_to_meter {
        if meters.len() > 1 {
            let device_name = get_name(device_id);
            errors.push(format!("设备 {} 连接了多个电表：{}，每端口只允许 1 个", 
                device_name, meters.len()));
        }
    }

    // === 孤立设备检查（警告）===
    let connected_devices: std::collections::HashSet<String> = data.connections.iter()
        .flat_map(|c| vec![c.from.clone(), c.to.clone()])
        .collect();
    
    for device in &data.devices {
        if !connected_devices.contains(&device.id) && device.device_type != "bus" {
            warnings.push(format!("设备 {} ({}) 未连接到任何其他设备", device.name, device.device_type));
        }
    }

    ValidationResult {
        valid: errors.is_empty(),
        errors,
        warnings,
    }
}

/// 尝试从旧格式（pandapower 格式）转换拓扑数据
fn try_convert_legacy_format(content: &str) -> Option<TopologyData> {
    // 尝试解析旧格式 JSON
    let legacy: serde_json::Value = serde_json::from_str(content).ok()?;
    
    // 检查是否是旧格式（包含 Bus、Line、Load 等顶级键）
    if !legacy.is_object() {
        return None;
    }
    
    let obj = legacy.as_object()?;
    
    // 如果包含 "devices" 字段，说明是新格式
    if obj.contains_key("devices") {
        return None;
    }
    
    // 如果包含 "Bus" 或 "Line" 等字段，说明是旧格式
    if !obj.contains_key("Bus") && !obj.contains_key("Line") && !obj.contains_key("Load") {
        return None;
    }
    
    let mut devices = Vec::new();
    let mut connections = Vec::new();
    let mut device_id_counter = 1;
    let mut conn_id_counter = 1;
    
    // 类型映射：旧格式类型 -> 新格式类型
    let type_mapping: HashMap<&str, &str> = [
        ("Bus", "bus"),
        ("Line", "line"),
        ("Transformer", "transformer"),
        ("Load", "load"),
        ("Static_Generator", "static_generator"),
        ("Static Generator", "static_generator"),
        ("Storage", "storage"),
        ("Charger", "charger"),
        ("Measurement", "meter"),
        ("External_Grid", "external_grid"),
        ("External Grid", "external_grid"),
    ].into_iter().collect();
    
    // 存储 index 到 device_id 的映射
    let mut index_to_id: HashMap<(String, i64), String> = HashMap::new();
    
    // 转换各类设备
    for (legacy_type, new_type) in &type_mapping {
        if let Some(items) = obj.get(*legacy_type).and_then(|v| v.as_array()) {
            for item in items {
                let index = item.get("index").and_then(|v| v.as_i64()).unwrap_or(device_id_counter as i64);
                let default_name = format!("{}{}", new_type, index);
                let name = item.get("name").and_then(|v| v.as_str()).unwrap_or(&default_name);
                
                let device_id = format!("device-{}", device_id_counter);
                device_id_counter += 1;
                
                // 记录 index 到 device_id 的映射
                index_to_id.insert((legacy_type.to_string(), index), device_id.clone());
                
                // 构建属性
                let mut properties = serde_json::Map::new();
                for (key, value) in item.as_object().unwrap_or(&serde_json::Map::new()) {
                    if key != "name" && key != "index" {
                        properties.insert(key.clone(), value.clone());
                    }
                }
                
                devices.push(DeviceData {
                    id: device_id,
                    name: name.to_string(),
                    device_type: new_type.to_string(),
                    properties: serde_json::Value::Object(properties),
                    position: None,
                    location: None,
                });
            }
        }
    }
    
    // 第二遍：创建连接
    for (legacy_type, new_type) in &type_mapping {
        if let Some(items) = obj.get(*legacy_type).and_then(|v| v.as_array()) {
            for item in items {
                let index = item.get("index").and_then(|v| v.as_i64()).unwrap_or(0);
                let device_id = match index_to_id.get(&(legacy_type.to_string(), index)) {
                    Some(id) => id.clone(),
                    None => continue,
                };
                
                // 线路连接
                if *new_type == "line" {
                    if let Some(from_bus) = item.get("from_bus").and_then(|v| v.as_i64()) {
                        if let Some(bus_id) = index_to_id.get(&("Bus".to_string(), from_bus)) {
                            connections.push(ConnectionData {
                                id: format!("conn-{}", conn_id_counter),
                                from: device_id.clone(),
                                to: bus_id.clone(),
                                from_port: Some("top".to_string()),    // 线路起点
                                to_port: Some("center".to_string()),   // 母线中心
                                connection_type: "line".to_string(),
                                properties: Some(serde_json::json!({"port": "from_bus"})),
                            });
                            conn_id_counter += 1;
                        }
                    }
                    if let Some(to_bus) = item.get("to_bus").and_then(|v| v.as_i64()) {
                        if let Some(bus_id) = index_to_id.get(&("Bus".to_string(), to_bus)) {
                            connections.push(ConnectionData {
                                id: format!("conn-{}", conn_id_counter),
                                from: device_id.clone(),
                                to: bus_id.clone(),
                                from_port: Some("bottom".to_string()), // 线路终点
                                to_port: Some("center".to_string()),   // 母线中心
                                connection_type: "line".to_string(),
                                properties: Some(serde_json::json!({"port": "to_bus"})),
                            });
                            conn_id_counter += 1;
                        }
                    }
                }
                
                // 变压器连接
                if *new_type == "transformer" {
                    if let Some(hv_bus) = item.get("hv_bus").and_then(|v| v.as_i64()) {
                        if let Some(bus_id) = index_to_id.get(&("Bus".to_string(), hv_bus)) {
                            connections.push(ConnectionData {
                                id: format!("conn-{}", conn_id_counter),
                                from: device_id.clone(),
                                to: bus_id.clone(),
                                from_port: Some("top".to_string()),    // 变压器高压侧
                                to_port: Some("center".to_string()),   // 母线中心
                                connection_type: "transformer".to_string(),
                                properties: Some(serde_json::json!({"port": "hv_bus"})),
                            });
                            conn_id_counter += 1;
                        }
                    }
                    if let Some(lv_bus) = item.get("lv_bus").and_then(|v| v.as_i64()) {
                        if let Some(bus_id) = index_to_id.get(&("Bus".to_string(), lv_bus)) {
                            connections.push(ConnectionData {
                                id: format!("conn-{}", conn_id_counter),
                                from: device_id.clone(),
                                to: bus_id.clone(),
                                from_port: Some("bottom".to_string()), // 变压器低压侧
                                to_port: Some("center".to_string()),   // 母线中心
                                connection_type: "transformer".to_string(),
                                properties: Some(serde_json::json!({"port": "lv_bus"})),
                            });
                            conn_id_counter += 1;
                        }
                    }
                }
                
                // 功率设备连接
                if ["load", "static_generator", "storage", "charger", "external_grid"].contains(new_type) {
                    if let Some(bus) = item.get("bus").and_then(|v| v.as_i64()) {
                        if let Some(bus_id) = index_to_id.get(&("Bus".to_string(), bus)) {
                            connections.push(ConnectionData {
                                id: format!("conn-{}", conn_id_counter),
                                from: device_id.clone(),
                                to: bus_id.clone(),
                                from_port: Some("top".to_string()),    // 功率设备连接点
                                to_port: Some("center".to_string()),   // 母线中心
                                connection_type: "power".to_string(),
                                properties: None,
                            });
                            conn_id_counter += 1;
                        }
                    }
                }
            }
        }
    }
    
    Some(TopologyData { devices, connections })
}

#[tauri::command]
pub async fn validate_topology(
    topology_data: TopologyData,
) -> Result<ValidationResult, String> {
    Ok(validate_topology_rules(&topology_data))
}

/// 加载并验证拓扑文件（支持旧格式兼容）
#[tauri::command]
pub async fn load_and_validate_topology(
    path: String,
    metadata_store: State<'_, Mutex<DeviceMetadataStore>>,
) -> Result<LoadAndValidateResult, String> {
    let content = std::fs::read_to_string(&path)
        .map_err(|e| format!("Failed to read file: {}", e))?;
    
    // 尝试解析为新格式
    let topology_data: TopologyData = if let Ok(topology) = serde_json::from_str::<Topology>(&content) {
        // 新格式（内部 Topology 结构）
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
                from_port: c.from_port.clone(),
                to_port: c.to_port.clone(),
                connection_type: c.connection_type.clone(),
                properties: Some(serde_json::to_value(&c.properties).unwrap_or(serde_json::Value::Object(serde_json::Map::new()))),
            }
        }).collect();

        // 更新元数据仓库
        metadata_store.lock().unwrap().set_topology(topology);

        TopologyData { devices, connections }
    } else if let Some(data) = try_convert_legacy_format(&content) {
        // 旧格式（pandapower 格式）
        data
    } else {
        return Err("无法解析拓扑文件：既不是新格式也不是旧格式".to_string());
    };
    
    // 验证拓扑规则
    let validation = validate_topology_rules(&topology_data);
    
    Ok(LoadAndValidateResult {
        data: topology_data,
        validation,
    })
}
