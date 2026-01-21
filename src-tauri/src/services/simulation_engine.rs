// 仿真引擎核心
use crate::domain::simulation::{SimulationStatus, DeviceWorkModes};
use crate::domain::topology::Topology;
use crate::services::python_bridge::PythonBridge;
use std::sync::Arc;
use tokio::sync::Mutex;
use std::collections::HashMap;
use tauri::{AppHandle, Emitter};
use tokio::time::{interval, Duration};

pub struct SimulationEngine {
    status: Arc<tokio::sync::Mutex<SimulationStatus>>,
    device_modes: Arc<tokio::sync::Mutex<DeviceWorkModes>>,
    python_bridge: Arc<Mutex<PythonBridge>>,
    topology: Arc<tokio::sync::Mutex<Option<Topology>>>,
}

impl SimulationEngine {
    pub fn new(python_bridge: Arc<Mutex<PythonBridge>>) -> Self {
        Self {
            status: Arc::new(tokio::sync::Mutex::new(SimulationStatus::new())),
            device_modes: Arc::new(tokio::sync::Mutex::new(HashMap::new())),
            python_bridge,
            topology: Arc::new(tokio::sync::Mutex::new(None)),
        }
    }

    pub async fn start(&self, app_handle: Option<AppHandle>) -> Result<(), String> {
        let mut status = self.status.lock().await;
        status.start();
        
        // 通过 Python 桥接启动仿真
        let mut bridge = self.python_bridge.lock().await;
        let params = serde_json::json!({
            "action": "start"
        });
        bridge.call("simulation.start", params).await
            .map_err(|e| format!("Failed to start simulation: {}", e))?;
        
        // 启动数据采集循环
        if let Some(app) = app_handle {
            self.start_data_collection_loop(app).await;
        }
        
        Ok(())
    }
    
    async fn start_data_collection_loop(&self, app: AppHandle) {
        let status = self.status.clone();
        let python_bridge = self.python_bridge.clone();
        let topology = self.topology.clone();
        
        tokio::spawn(async move {
            let mut interval = interval(Duration::from_secs(1)); // 每秒采集一次
            
            loop {
                interval.tick().await;
                
                // 检查仿真是否运行中
                let status_guard = status.lock().await;
                if status_guard.state != crate::domain::simulation::SimulationState::Running {
                    drop(status_guard);
                    continue;
                }
                drop(status_guard);
                
                // 获取拓扑中的所有设备
                let device_ids = {
                    let topo = topology.lock().await;
                    if let Some(ref t) = *topo {
                        t.devices.keys().cloned().collect::<Vec<_>>()
                    } else {
                        continue;
                    }
                };
                
                // 采集每个设备的数据
                for device_id in device_ids {
                    let mut bridge = python_bridge.lock().await;
                    let params = serde_json::json!({
                        "device_id": device_id
                    });
                    
                    if let Ok(data) = bridge.call("simulation.get_device_data", params).await {
                        // 发射设备数据更新事件
                        let _ = app.emit("device-data-update", serde_json::json!({
                            "device_id": device_id,
                            "data": data
                        }));
                    }
                }
            }
        });
    }

    pub async fn stop(&self) -> Result<(), String> {
        let mut status = self.status.lock().await;
        status.stop();
        
        // 通过 Python 桥接停止仿真
        let mut bridge = self.python_bridge.lock().await;
        let params = serde_json::json!({
            "action": "stop"
        });
        bridge.call("simulation.stop", params).await
            .map_err(|e| format!("Failed to stop simulation: {}", e))?;
        
        Ok(())
    }

    pub async fn pause(&self) -> Result<(), String> {
        let mut status = self.status.lock().await;
        status.pause();
        
        let mut bridge = self.python_bridge.lock().await;
        let params = serde_json::json!({
            "action": "pause"
        });
        bridge.call("simulation.pause", params).await
            .map_err(|e| format!("Failed to pause simulation: {}", e))?;
        
        Ok(())
    }

    pub async fn resume(&self) -> Result<(), String> {
        let mut status = self.status.lock().await;
        status.resume();
        
        let mut bridge = self.python_bridge.lock().await;
        let params = serde_json::json!({
            "action": "resume"
        });
        bridge.call("simulation.resume", params).await
            .map_err(|e| format!("Failed to resume simulation: {}", e))?;
        
        Ok(())
    }

    pub async fn get_status(&self) -> SimulationStatus {
        self.status.lock().await.clone()
    }

    pub async fn set_device_mode(&self, device_id: String, mode: String) -> Result<(), String> {
        // 验证模式
        let valid_modes = ["random_data", "manual", "remote", "historical_data"];
        if !valid_modes.contains(&mode.as_str()) {
            return Err(format!("Invalid mode: {}", mode));
        }

        // 更新设备模式
        self.device_modes.lock().await.insert(device_id.clone(), mode.clone().into());
        
        // 通知 Python 内核
        let mut bridge = self.python_bridge.lock().await;
        let params = serde_json::json!({
            "device_id": device_id,
            "mode": mode
        });
        bridge.call("simulation.set_device_mode", params).await
            .map_err(|e| format!("Failed to set device mode: {}", e))?;
        
        Ok(())
    }

    pub async fn get_device_modes(&self) -> DeviceWorkModes {
        self.device_modes.lock().await.clone()
    }

    pub async fn set_topology(&self, topology: Topology) {
        *self.topology.lock().await = Some(topology);
    }

    pub async fn get_topology(&self) -> Option<Topology> {
        self.topology.lock().await.clone()
    }

    pub async fn get_device_data(&self, device_id: &str) -> Result<serde_json::Value, String> {
        let mut bridge = self.python_bridge.lock().await;
        let params = serde_json::json!({
            "device_id": device_id
        });
        bridge.call("simulation.get_device_data", params).await
            .map_err(|e| format!("Failed to get device data: {}", e))
    }
}
