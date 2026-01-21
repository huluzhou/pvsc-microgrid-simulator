// 工作模式处理器
// Rust 端主要负责模式状态管理和调度
// 具体的数据生成逻辑在 Python 内核中实现

use crate::domain::device::WorkMode;
use std::collections::HashMap;

pub struct ModeHandler {
    device_modes: HashMap<String, WorkMode>,
}

impl ModeHandler {
    pub fn new() -> Self {
        Self {
            device_modes: HashMap::new(),
        }
    }

    pub fn set_device_mode(&mut self, device_id: String, mode: WorkMode) {
        self.device_modes.insert(device_id, mode);
    }

    pub fn get_device_mode(&self, device_id: &str) -> Option<&WorkMode> {
        self.device_modes.get(device_id)
    }

    pub fn get_all_modes(&self) -> &HashMap<String, WorkMode> {
        &self.device_modes
    }
}

impl Default for ModeHandler {
    fn default() -> Self {
        Self::new()
    }
}
