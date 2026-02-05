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
    pub elapsed_time: u64, // 秒（仅统计运行中时间，不含暂停时长，与 calculation_count 同步）
    pub calculation_count: u64,
    /// 每步平均耗时（毫秒）：一次仿真步（get_status + get_errors + perform_calculation + 结果处理）的耗时均值，用于判断是否跟得上计算间隔
    pub average_delay: f64,
    pub errors: Vec<SimulationError>,
    /// 暂停开始时刻（Unix 秒），用于累计暂停时长
    #[serde(skip)]
    pub pause_started_at: Option<u64>,
    /// 累计暂停时长（秒），elapsed_time = (now - start_time) - total_paused_secs
    #[serde(skip)]
    pub total_paused_secs: u64,
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
            pause_started_at: None,
            total_paused_secs: 0,
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
        self.pause_started_at = None;
        self.total_paused_secs = 0;
    }

    pub fn stop(&mut self) {
        self.state = SimulationState::Stopped;
        self.start_time = None;
        self.pause_started_at = None;
        self.total_paused_secs = 0;
    }

    pub fn pause(&mut self) {
        self.state = SimulationState::Paused;
        self.pause_started_at = Some(
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        );
    }

    pub fn resume(&mut self) {
        self.state = SimulationState::Running;
        if let Some(ps) = self.pause_started_at.take() {
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs();
            self.total_paused_secs = self.total_paused_secs.saturating_add(now.saturating_sub(ps));
        }
    }
}

impl Default for SimulationStatus {
    fn default() -> Self {
        Self::new()
    }
}

// 设备工作模式映射
pub type DeviceWorkModes = HashMap<String, WorkMode>;

/// 储能设备独立维护的状态（pandapower 仅返回有功/无功功率）
#[derive(Debug, Clone, Default)]
pub struct StorageState {
    /// 额定容量 kWh（从拓扑 properties.capacity / max_e_mwh 解析，仅首次初始化）
    pub capacity_kwh: f64,
    /// 当前能量 kWh（积分功率得到，用于计算 SOC）
    pub energy_kwh: f64,
    /// SOC 百分比 0–100（由 energy_kwh / capacity_kwh 计算）
    pub soc_percent: f64,
    /// 日充电量 kWh（仿真步内积分，日重置可后续扩展）
    pub daily_charge_kwh: f64,
    /// 日放电量 kWh
    pub daily_discharge_kwh: f64,
    /// 累计充电总量 kWh
    pub total_charge_kwh: f64,
    /// 累计放电总量 kWh
    pub total_discharge_kwh: f64,
}
