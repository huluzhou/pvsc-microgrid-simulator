// 分析相关命令
use serde::{Deserialize, Serialize};
use tauri::State;
use crate::services::database::Database;
use crate::services::python_bridge::PythonBridge;
use std::sync::Mutex as StdMutex;
use tokio::sync::Mutex as TokioMutex;

#[derive(Debug, Serialize, Deserialize)]
pub struct AnalysisRequest {
    pub device_ids: Vec<String>,
    pub start_time: f64,
    pub end_time: f64,
    pub analysis_type: String, // "performance", "fault", "regulation", "utilization", "revenue"
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AnalysisResult {
    pub analysis_type: String,
    pub summary: serde_json::Value,
    pub details: serde_json::Value,
    pub charts: Vec<ChartData>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChartData {
    pub title: String,
    pub chart_type: String, // "line", "bar", "pie"
    pub data: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ReportRequest {
    pub report_type: String, // "fault", "regulation", "control", "utilization", "revenue"
    pub device_ids: Vec<String>,
    pub start_time: f64,
    pub end_time: f64,
    pub format: String, // "pdf", "excel"
}

#[tauri::command]
pub async fn analyze_performance(
    request: AnalysisRequest,
    db: State<'_, StdMutex<Database>>,
    python_bridge: State<'_, TokioMutex<PythonBridge>>,
) -> Result<AnalysisResult, String> {
    // 从数据库查询数据
    let mut all_data = Vec::new();
    for device_id in &request.device_ids {
        let db = db.lock().unwrap();
        let data = db.query_device_data(device_id, Some(request.start_time), Some(request.end_time))
            .map_err(|e| format!("Failed to query device data: {}", e))?;
        all_data.push((device_id.clone(), data));
    }
    
    // 调用 Python 内核进行分析
    let mut bridge = python_bridge.lock().await;
    let params = serde_json::json!({
        "analysis_type": request.analysis_type,
        "data": all_data,
        "start_time": request.start_time,
        "end_time": request.end_time,
    });
    
    let result = bridge.call("analytics.analyze", params).await
        .map_err(|e| format!("Failed to analyze: {}", e))?;
    
    serde_json::from_value(result)
        .map_err(|e| format!("Failed to parse analysis result: {}", e))
}

#[tauri::command]
pub async fn generate_report(
    request: ReportRequest,
    db: State<'_, StdMutex<Database>>,
    python_bridge: State<'_, TokioMutex<PythonBridge>>,
) -> Result<String, String> {
    // 从数据库查询数据
    let mut all_data = Vec::new();
    for device_id in &request.device_ids {
        let db = db.lock().unwrap();
        let data = db.query_device_data(device_id, Some(request.start_time), Some(request.end_time))
            .map_err(|e| format!("Failed to query device data: {}", e))?;
        all_data.push((device_id.clone(), data));
    }
    
    // 调用 Python 内核生成报告
    let mut bridge = python_bridge.lock().await;
    let params = serde_json::json!({
        "report_type": request.report_type,
        "data": all_data,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "format": request.format,
    });
    
    let result = bridge.call("analytics.generate_report", params).await
        .map_err(|e| format!("Failed to generate report: {}", e))?;
    
    // 返回报告文件路径或内容
    result.get("report_path")
        .or(result.get("report_content"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| "Report generation failed".to_string())
}
