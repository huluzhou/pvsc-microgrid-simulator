// 拓扑实体和规则
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum DeviceType {
    Node,        // 节点设备：母线
    Line,        // 连接设备：线路
    Transformer, // 连接设备：变压器
    Switch,      // 连接设备：开关
    Pv,          // 功率设备：光伏
    Storage,     // 功率设备：储能
    Load,        // 功率设备：负载
    Charger,     // 功率设备：充电桩
    Meter,       // 测量设备：电表
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Position {
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Location {
    pub latitude: f64,
    pub longitude: f64,
    pub altitude: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Device {
    pub id: String,
    pub name: String,
    pub device_type: DeviceType,
    pub properties: HashMap<String, serde_json::Value>,
    pub position: Option<Position>,
    pub location: Option<Location>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Connection {
    pub id: String,
    pub from_device_id: String,
    pub to_device_id: String,
    pub connection_type: String,
    pub properties: HashMap<String, serde_json::Value>,
    pub is_active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Topology {
    pub id: String,
    pub name: String,
    pub description: String,
    pub devices: HashMap<String, Device>,
    pub connections: HashMap<String, Connection>,
}

impl Topology {
    pub fn new(id: String, name: String, description: String) -> Self {
        Self {
            id,
            name,
            description,
            devices: HashMap::new(),
            connections: HashMap::new(),
        }
    }

    pub fn add_device(&mut self, device: Device) -> Result<(), String> {
        if self.devices.contains_key(&device.id) {
            return Err(format!("Device with id {} already exists", device.id));
        }
        self.devices.insert(device.id.clone(), device);
        Ok(())
    }

    pub fn remove_device(&mut self, device_id: &str) -> Result<(), String> {
        if !self.devices.contains_key(device_id) {
            return Err(format!("Device with id {} not found", device_id));
        }
        self.devices.remove(device_id);
        // 移除相关连接
        self.connections.retain(|_, conn| {
            conn.from_device_id != device_id && conn.to_device_id != device_id
        });
        Ok(())
    }

    pub fn add_connection(&mut self, connection: Connection) -> Result<(), String> {
        // 验证连接规则
        if let Err(e) = self.validate_connection(&connection) {
            return Err(e);
        }
        
        if self.connections.contains_key(&connection.id) {
            return Err(format!("Connection with id {} already exists", connection.id));
        }
        self.connections.insert(connection.id.clone(), connection);
        Ok(())
    }

    pub fn remove_connection(&mut self, connection_id: &str) -> Result<(), String> {
        if !self.connections.contains_key(connection_id) {
            return Err(format!("Connection with id {} not found", connection_id));
        }
        self.connections.remove(connection_id);
        Ok(())
    }

    fn validate_connection(&self, connection: &Connection) -> Result<(), String> {
        // 检查设备是否存在
        if !self.devices.contains_key(&connection.from_device_id) {
            return Err(format!("Source device {} not found", connection.from_device_id));
        }
        if !self.devices.contains_key(&connection.to_device_id) {
            return Err(format!("Target device {} not found", connection.to_device_id));
        }

        let from_device = &self.devices[&connection.from_device_id];
        let to_device = &self.devices[&connection.to_device_id];

        // 验证连接规则（参考 connect_rule.md）
        match (&from_device.device_type, &to_device.device_type) {
            // 不允许母线与母线直接连接
            (DeviceType::Node, DeviceType::Node) => {
                return Err("Cannot connect node to node directly".to_string());
            }
            // 其他规则验证...
            _ => {}
        }

        Ok(())
    }
}
