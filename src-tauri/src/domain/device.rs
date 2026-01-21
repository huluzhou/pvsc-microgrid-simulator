// 设备元数据模型
use crate::domain::topology::DeviceType;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum WorkMode {
    RandomData,    // 随机数据模式
    Manual,        // 手动模式
    Remote,        // 远程模式
    HistoricalData, // 历史数据模式
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceMetadata {
    pub id: String,
    pub name: String,
    pub device_type: DeviceType,
    pub properties: HashMap<String, serde_json::Value>,
    pub work_mode: Option<WorkMode>,
    pub response_delay: Option<f64>,  // 响应延迟（秒）
    pub measurement_error: Option<f64>, // 测量误差（百分比）
    pub data_collection_frequency: Option<f64>, // 数据采集频率（秒）
}

impl DeviceMetadata {
    pub fn from_device(device: &crate::domain::topology::Device) -> Self {
        Self {
            id: device.id.clone(),
            name: device.name.clone(),
            device_type: device.device_type.clone(),
            properties: device.properties.clone(),
            work_mode: None,
            response_delay: None,
            measurement_error: None,
            data_collection_frequency: None,
        }
    }
}

impl From<String> for WorkMode {
    fn from(s: String) -> Self {
        match s.as_str() {
            "random_data" => WorkMode::RandomData,
            "manual" => WorkMode::Manual,
            "remote" => WorkMode::Remote,
            "historical_data" => WorkMode::HistoricalData,
            _ => WorkMode::RandomData,
        }
    }
}
