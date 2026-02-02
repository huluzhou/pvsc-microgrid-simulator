// 仿真状态和工作模式
use crate::domain::device::WorkMode;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SimulationState {
    Stopped,
    Running,
    Paused,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationError {
    pub error_type: String,  // "adapter" | "topology" | "calculation" | "runtime"
    pub severity: String,     // "error" | "warning" | "info"
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub device_id: Option<String>,
    pub details: serde_json::Value,
    pub timestamp: u64,
}

// 手动实现 PartialEq，比较时忽略 timestamp 字段
// 这样可以避免因时间戳不同而将相同错误视为不同错误
impl PartialEq for SimulationError {
    fn eq(&self, other: &Self) -> bool {
        self.error_type == other.error_type
            && self.severity == other.severity
            && self.message == other.message
            && self.device_id == other.device_id
            && self.details == other.details
            // 不比较 timestamp
    }
}

impl Eq for SimulationError {}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationStatus {
    pub state: SimulationState,
    pub start_time: Option<u64>,
    pub elapsed_time: u64, // 秒
    pub calculation_count: u64,
    /// 每步平均耗时（毫秒）：一次仿真步（get_status + get_errors + perform_calculation + 结果处理）的耗时均值，用于判断是否跟得上计算间隔
    pub average_delay: f64,
    pub errors: Vec<SimulationError>,
}

impl SimulationStatus {
    pub fn new() -> Self {
        Self {
            state: SimulationState::Stopped,
            start_time: None,
            elapsed_time: 0,
            calculation_count: 0,
            average_delay: 0.0,
            errors: Vec::new(),
        }
    }

    pub fn start(&mut self) {
        self.state = SimulationState::Running;
        self.start_time = Some(
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        );
        self.elapsed_time = 0;
        self.calculation_count = 0;
    }

    pub fn stop(&mut self) {
        self.state = SimulationState::Stopped;
        self.start_time = None;
    }

    pub fn pause(&mut self) {
        self.state = SimulationState::Paused;
    }

    pub fn resume(&mut self) {
        self.state = SimulationState::Running;
    }
}

impl Default for SimulationStatus {
    fn default() -> Self {
        Self::new()
    }
}

// 设备工作模式映射
pub type DeviceWorkModes = HashMap<String, WorkMode>;
