// 仿真引擎核心
use crate::domain::simulation::{SimulationStatus, SimulationState, DeviceWorkModes};
use crate::domain::topology::Topology;
use crate::services::python_bridge::PythonBridge;
use std::sync::{Arc, Mutex};
use std::collections::HashMap;

pub struct SimulationEngine {
    status: Arc<Mutex<SimulationStatus>>,
    device_modes: Arc<Mutex<DeviceWorkModes>>,
    python_bridge: Arc<Mutex<PythonBridge>>,
    topology: Arc<Mutex<Option<Topology>>>,
}

impl SimulationEngine {
    pub fn new(python_bridge: Arc<Mutex<PythonBridge>>) -> Self {
        Self {
            status: Arc::new(Mutex::new(SimulationStatus::new())),
            device_modes: Arc::new(Mutex::new(HashMap::new())),
            python_bridge,
            topology: Arc::new(Mutex::new(None)),
        }
    }

    pub fn start(&self) -> Result<(), String> {
        let mut status = self.status.lock().unwrap();
        status.start();
        
        // 通过 Python 桥接启动仿真
        let mut bridge = self.python_bridge.lock().unwrap();
        let params = serde_json::json!({
            "action": "start"
        });
        bridge.call("simulation.start", params)
            .map_err(|e| format!("Failed to start simulation: {}", e))?;
        
        Ok(())
    }

    pub fn stop(&self) -> Result<(), String> {
        let mut status = self.status.lock().unwrap();
        status.stop();
        
        // 通过 Python 桥接停止仿真
        let mut bridge = self.python_bridge.lock().unwrap();
        let params = serde_json::json!({
            "action": "stop"
        });
        bridge.call("simulation.stop", params)
            .map_err(|e| format!("Failed to stop simulation: {}", e))?;
        
        Ok(())
    }

    pub fn pause(&self) -> Result<(), String> {
        let mut status = self.status.lock().unwrap();
        status.pause();
        
        let mut bridge = self.python_bridge.lock().unwrap();
        let params = serde_json::json!({
            "action": "pause"
        });
        bridge.call("simulation.pause", params)
            .map_err(|e| format!("Failed to pause simulation: {}", e))?;
        
        Ok(())
    }

    pub fn resume(&self) -> Result<(), String> {
        let mut status = self.status.lock().unwrap();
        status.resume();
        
        let mut bridge = self.python_bridge.lock().unwrap();
        let params = serde_json::json!({
            "action": "resume"
        });
        bridge.call("simulation.resume", params)
            .map_err(|e| format!("Failed to resume simulation: {}", e))?;
        
        Ok(())
    }

    pub fn get_status(&self) -> SimulationStatus {
        self.status.lock().unwrap().clone()
    }

    pub fn set_device_mode(&self, device_id: String, mode: String) -> Result<(), String> {
        // 验证模式
        let valid_modes = ["random_data", "manual", "remote", "historical_data"];
        if !valid_modes.contains(&mode.as_str()) {
            return Err(format!("Invalid mode: {}", mode));
        }

        // 更新设备模式
        self.device_modes.lock().unwrap().insert(device_id.clone(), mode.clone().into());
        
        // 通知 Python 内核
        let mut bridge = self.python_bridge.lock().unwrap();
        let params = serde_json::json!({
            "device_id": device_id,
            "mode": mode
        });
        bridge.call("simulation.set_device_mode", params)
            .map_err(|e| format!("Failed to set device mode: {}", e))?;
        
        Ok(())
    }

    pub fn get_device_modes(&self) -> DeviceWorkModes {
        self.device_modes.lock().unwrap().clone()
    }

    pub fn set_topology(&self, topology: Topology) {
        *self.topology.lock().unwrap() = Some(topology);
    }

    pub fn get_topology(&self) -> Option<Topology> {
        self.topology.lock().unwrap().clone()
    }

    pub fn get_device_data(&self, device_id: &str) -> Result<serde_json::Value, String> {
        let mut bridge = self.python_bridge.lock().unwrap();
        let params = serde_json::json!({
            "device_id": device_id
        });
        bridge.call("simulation.get_device_data", params)
            .map_err(|e| format!("Failed to get device data: {}", e))
    }
}
