// 仿真引擎命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::services::simulation_engine::SimulationEngine;
use crate::services::python_bridge::PythonBridge;
use crate::domain::simulation::SimulationStatus;
use std::sync::Mutex;
use std::sync::Arc;

#[derive(Debug, Serialize, Deserialize)]
pub struct SimulationControlRequest {
    pub action: String, // "start", "stop", "pause", "resume"
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DeviceModeRequest {
    pub device_id: String,
    pub mode: String,
}

#[tauri::command]
pub async fn start_simulation(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.start().await
}

#[tauri::command]
pub async fn stop_simulation(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.stop().await
}

#[tauri::command]
pub async fn pause_simulation(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.pause().await
}

#[tauri::command]
pub async fn resume_simulation(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.resume().await
}

#[tauri::command]
pub async fn get_simulation_status(
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<SimulationStatus, String> {
    Ok(engine.get_status().await)
}

#[tauri::command]
pub async fn set_device_mode(
    device_id: String,
    mode: String,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<(), String> {
    engine.set_device_mode(device_id, mode).await
}

#[tauri::command]
pub async fn get_device_data(
    device_id: String,
    engine: State<'_, Arc<SimulationEngine>>,
) -> Result<serde_json::Value, String> {
    engine.get_device_data(&device_id).await
}
