// 延迟和误差模拟
use rand::Rng;
use std::collections::HashMap;

pub struct DelaySimulator {
    device_delays: HashMap<String, f64>, // 设备ID -> 响应延迟（秒）
    measurement_errors: HashMap<String, f64>, // 设备ID -> 测量误差（百分比）
    communication_delays: HashMap<String, f64>, // 设备ID -> 通信延迟（秒）
}

impl DelaySimulator {
    pub fn new() -> Self {
        Self {
            device_delays: HashMap::new(),
            measurement_errors: HashMap::new(),
            communication_delays: HashMap::new(),
        }
    }

    pub fn set_device_response_delay(&mut self, device_id: &str, delay: f64) {
        self.device_delays.insert(device_id.to_string(), delay);
    }

    pub fn set_device_measurement_error(&mut self, device_id: &str, error_percent: f64) {
        self.measurement_errors.insert(device_id.to_string(), error_percent);
    }

    pub fn set_device_communication_delay(&mut self, device_id: &str, delay: f64) {
        self.communication_delays.insert(device_id.to_string(), delay);
    }

    pub fn apply_measurement_error(&self, device_id: &str, value: f64) -> f64 {
        if let Some(&error_percent) = self.measurement_errors.get(device_id) {
            let mut rng = rand::thread_rng();
            // 使用正态分布添加误差
            let error = rng.gen_range(-error_percent..=error_percent) / 100.0;
            value * (1.0 + error)
        } else {
            value
        }
    }

    pub fn get_response_delay(&self, device_id: &str) -> f64 {
        self.device_delays.get(device_id).copied().unwrap_or(0.0)
    }

    pub fn get_communication_delay(&self, device_id: &str) -> f64 {
        self.communication_delays.get(device_id).copied().unwrap_or(0.0)
    }
}

impl Default for DelaySimulator {
    fn default() -> Self {
        Self::new()
    }
}
