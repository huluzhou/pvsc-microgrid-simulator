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
pub struct SimulationStatus {
    pub state: SimulationState,
    pub start_time: Option<u64>,
    pub elapsed_time: u64, // 秒
    pub calculation_count: u64,
    pub average_delay: f64, // 毫秒
}

impl SimulationStatus {
    pub fn new() -> Self {
        Self {
            state: SimulationState::Stopped,
            start_time: None,
            elapsed_time: 0,
            calculation_count: 0,
            average_delay: 0.0,
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
