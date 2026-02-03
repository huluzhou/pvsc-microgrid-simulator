// SSH 命令：连接、断开、远程 device_data 查询（供数据看板使用）
use serde::{Deserialize, Serialize};
use tauri::State;
use std::sync::Arc;
use tokio::sync::Mutex;
use crate::services::ssh::{SshClient, SshConfig};
use crate::commands::monitoring::DeviceDataPoint;
use std::io::Cursor;

#[derive(Debug, Serialize, Deserialize)]
pub struct DashboardRemoteData {
    /// 去重后的设备 id 列表，用于看板设备列表
    pub device_ids: Vec<String>,
    /// 按 device_id 分组的点数据，与 query_device_data 同构
    pub points_by_device: std::collections::HashMap<String, Vec<DeviceDataPoint>>,
}

#[tauri::command]
pub async fn ssh_connect(
    config: SshConfig,
    ssh: State<'_, Arc<Mutex<SshClient>>>,
) -> Result<(), String> {
    let mut client = ssh.lock().await;
    client.connect(config).await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn ssh_disconnect(ssh: State<'_, Arc<Mutex<SshClient>>>) -> Result<(), String> {
    let mut client = ssh.lock().await;
    client.disconnect();
    Ok(())
}

#[tauri::command]
pub async fn ssh_is_connected(ssh: State<'_, Arc<Mutex<SshClient>>>) -> Result<bool, String> {
    let client = ssh.lock().await;
    Ok(client.is_connected())
}

/// 在远端数据库执行 device_data 查询，返回与 query_device_data 同构的按设备分组的点数据。
/// 若提供 export_path，会将读取到的 CSV 写入该路径（支持导出）。
/// 远端表结构需与本地一致：device_data(device_id, timestamp, p_active, p_reactive, data_json)。
#[tauri::command]
pub async fn ssh_query_remote_device_data(
    db_path: String,
    start_time: Option<f64>,
    end_time: Option<f64>,
    max_points: Option<usize>,
    export_path: Option<String>,
    ssh: State<'_, Arc<Mutex<SshClient>>>,
) -> Result<DashboardRemoteData, String> {
    let start = start_time.unwrap_or(0.0);
    let end = end_time.unwrap_or(9999999999.0);
    let limit = max_points.unwrap_or(50_000).min(100_000);

    let mut query = "SELECT device_id, timestamp, p_active, p_reactive, data_json FROM device_data WHERE timestamp >= ".to_string();
    query.push_str(&start.to_string());
    query.push_str(" AND timestamp <= ");
    query.push_str(&end.to_string());
    query.push_str(" ORDER BY timestamp LIMIT ");
    query.push_str(&limit.to_string());

    let csv_output = {
        let mut client = ssh.lock().await;
        client
            .query_remote_database(&db_path, &query)
            .await
            .map_err(|e| e.to_string())?
    };

    // 若指定导出路径，将 CSV 写入该文件（读取到本地临时文件后支持导出）
    if let Some(ref path) = export_path {
        tokio::fs::write(path, &csv_output)
            .await
            .map_err(|e| format!("导出 CSV 失败: {}", e))?;
    }

    // 解析 CSV：sqlite3 -csv 首行为表头
    let mut rdr = csv::Reader::from_reader(Cursor::new(csv_output.as_bytes()));
    let mut points_by_device: std::collections::HashMap<String, Vec<DeviceDataPoint>> = std::collections::HashMap::new();
    let mut device_ids_set: std::collections::HashSet<String> = std::collections::HashSet::new();

    for result in rdr.records() {
        let record = result.map_err(|e| e.to_string())?;
        if record.len() < 5 {
            continue;
        }
        let device_id = record.get(0).unwrap().to_string();
        let timestamp: f64 = record.get(1).unwrap().trim().parse().unwrap_or(0.0);
        let p_active: Option<f64> = record.get(2).unwrap().trim().parse().ok();
        let p_reactive: Option<f64> = record.get(3).unwrap().trim().parse().ok();
        let data_json_str = record.get(4).unwrap().trim();
        let data_json = if data_json_str.is_empty() || data_json_str.eq_ignore_ascii_case("null") {
            None
        } else {
            serde_json::from_str(data_json_str).ok()
        };

        device_ids_set.insert(device_id.clone());
        let point = DeviceDataPoint {
            device_id: device_id.clone(),
            timestamp,
            p_active,
            p_reactive,
            data_json,
        };
        points_by_device.entry(device_id).or_default().push(point);
    }

    let device_ids: Vec<String> = device_ids_set.into_iter().collect();
    Ok(DashboardRemoteData {
        device_ids,
        points_by_device,
    })
}
