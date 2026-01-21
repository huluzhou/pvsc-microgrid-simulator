// AI 相关命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::services::python_bridge::PythonBridge;
use crate::services::simulation_engine::SimulationEngine;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Serialize, Deserialize)]
pub struct PredictionRequest {
    pub device_ids: Vec<String>,
    pub prediction_horizon: u64, // 预测时间范围（秒）
    pub prediction_type: String, // "voltage", "current", "power"
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PredictionResult {
    pub device_id: String,
    pub predictions: Vec<DataPoint>,
    pub confidence: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DataPoint {
    pub timestamp: f64,
    pub value: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OptimizationRequest {
    pub objective: String, // "minimize_cost", "maximize_efficiency", etc.
    pub constraints: Vec<String>,
    pub time_horizon: u64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct OptimizationResult {
    pub strategy: serde_json::Value,
    pub expected_benefit: f64,
    pub confidence: f64,
}

#[tauri::command]
pub async fn predict_device_data(
    request: PredictionRequest,
    python_bridge: State<'_, Mutex<PythonBridge>>,
) -> Result<Vec<PredictionResult>, String> {
    let mut bridge = python_bridge.lock().await;
    let params = serde_json::to_value(&request)
        .map_err(|e| format!("Failed to serialize request: {}", e))?;
    
    let result = bridge.call("ai.predict", params).await
        .map_err(|e| format!("Failed to call AI prediction: {}", e))?;
    
    serde_json::from_value(result)
        .map_err(|e| format!("Failed to parse prediction result: {}", e))
}

#[tauri::command]
pub async fn optimize_operation(
    request: OptimizationRequest,
    python_bridge: State<'_, Mutex<PythonBridge>>,
) -> Result<OptimizationResult, String> {
    let mut bridge = python_bridge.lock().await;
    let params = serde_json::to_value(&request)
        .map_err(|e| format!("Failed to serialize request: {}", e))?;
    
    let result = bridge.call("ai.optimize", params).await
        .map_err(|e| format!("Failed to call AI optimization: {}", e))?;
    
    serde_json::from_value(result)
        .map_err(|e| format!("Failed to parse optimization result: {}", e))
}

#[tauri::command]
pub async fn get_ai_recommendations(
    device_ids: Vec<String>,
    python_bridge: State<'_, Mutex<PythonBridge>>,
) -> Result<Vec<String>, String> {
    let mut bridge = python_bridge.lock().await;
    let params = serde_json::json!({
        "device_ids": device_ids
    });
    
    let result = bridge.call("ai.get_recommendations", params).await
        .map_err(|e| format!("Failed to get AI recommendations: {}", e))?;
    
    serde_json::from_value(result.get("recommendations").cloned().unwrap_or(serde_json::json!([])))
        .map_err(|e| format!("Failed to parse recommendations: {}", e))
}
