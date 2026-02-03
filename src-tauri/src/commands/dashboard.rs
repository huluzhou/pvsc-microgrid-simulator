// 数据看板命令：CSV 解析、本地 DB 按路径查询
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::File;
use std::io::BufReader;
use crate::commands::monitoring::DeviceDataPoint;

#[derive(serde::Serialize)]
pub struct DashboardListFromPathResponse {
    pub device_ids: Vec<String>,
    #[serde(rename = "deviceTypes")]
    pub device_types: std::collections::HashMap<String, String>,
}

/// 从指定路径的 SQLite 数据库读取 device_data 表中所有不重复的 device_id 及 device_type（供看板「本地数据库」设备列表）。
#[tauri::command]
pub async fn dashboard_list_devices_from_path(db_path: String) -> Result<DashboardListFromPathResponse, String> {
    let conn = rusqlite::Connection::open(&db_path).map_err(|e| format!("打开数据库失败: {}", e))?;
    let mut stmt = conn
        .prepare("SELECT DISTINCT device_id FROM device_data ORDER BY device_id")
        .map_err(|e| format!("查询失败: {}", e))?;
    let rows = stmt
        .query_map([], |row| row.get::<_, String>(0))
        .map_err(|e| format!("查询失败: {}", e))?;
    let mut ids = Vec::new();
    for row in rows {
        ids.push(row.map_err(|e| format!("读取行失败: {}", e))?);
    }
    let mut device_types = std::collections::HashMap::new();
    if let Ok(mut stmt2) = conn.prepare("SELECT device_id, device_type FROM device_data WHERE device_type IS NOT NULL") {
        if let Ok(rows2) = stmt2.query_map([], |row| Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))) {
            for row in rows2.flatten() {
                device_types.entry(row.0).or_insert(row.1);
            }
        }
    }
    Ok(DashboardListFromPathResponse {
        device_ids: ids,
        device_types,
    })
}

/// 从指定路径的 SQLite 数据库查询 device_data，与 query_device_data 同构（供看板「本地数据库」数据源使用）。
#[tauri::command]
pub async fn query_device_data_from_path(
    db_path: String,
    device_id: String,
    start_time: Option<f64>,
    end_time: Option<f64>,
    max_points: Option<usize>,
) -> Result<Vec<DeviceDataPoint>, String> {
    let conn = rusqlite::Connection::open(&db_path).map_err(|e| format!("打开数据库失败: {}", e))?;
    let mut query = "SELECT timestamp, p_active, p_reactive, data_json FROM device_data WHERE device_id = ?1".to_string();
    let mut params: Vec<Box<dyn rusqlite::ToSql>> = vec![Box::new(device_id.clone())];
    if let Some(start) = start_time {
        query.push_str(" AND timestamp >= ?2");
        params.push(Box::new(start));
    }
    if let Some(end) = end_time {
        query.push_str(if start_time.is_some() { " AND timestamp <= ?3" } else { " AND timestamp <= ?2" });
        params.push(Box::new(end));
    }
    query.push_str(" ORDER BY timestamp");

    let mut stmt = conn.prepare(&query).map_err(|e| format!("查询失败: {}", e))?;
    let rows = stmt
        .query_map(rusqlite::params_from_iter(params.iter().map(|p| p.as_ref())), |row| {
            Ok((
                row.get::<_, f64>(0)?,
                row.get::<_, Option<f64>>(1)?,
                row.get::<_, Option<f64>>(2)?,
                row.get::<_, Option<String>>(3)?,
            ))
        })
        .map_err(|e| format!("查询失败: {}", e))?;
    let mut results: Vec<(f64, Option<f64>, Option<f64>, Option<String>)> = Vec::new();
    for row in rows {
        results.push(row.map_err(|e| format!("读取行失败: {}", e))?);
    }

    if let Some(n) = max_points {
        if results.len() > n && n > 0 {
            let start_ts = results.first().map(|r| r.0).unwrap_or(0.0);
            let end_ts = results.last().map(|r| r.0).unwrap_or(0.0);
            let span = (end_ts - start_ts).max(1e-9);
            let bucket_size = span / (n as f64);
            let mut buckets: HashMap<usize, Vec<(f64, Option<f64>, Option<f64>, Option<String>)>> = HashMap::new();
            for r in &results {
                let idx = (r.0 - start_ts) / bucket_size;
                let i = idx.floor().min((n - 1) as f64).max(0.0) as usize;
                buckets.entry(i).or_default().push(r.clone());
            }
            results = (0..n)
                .filter_map(|i| {
                    buckets.get(&i).and_then(|v| {
                        if v.is_empty() {
                            None
                        } else {
                            let len = v.len() as f64;
                            let ts = v.iter().map(|r| r.0).sum::<f64>() / len;
                            let p_a = v.iter().filter_map(|r| r.1).reduce(|a, b| a + b).map(|s| s / len);
                            let p_r = v.iter().filter_map(|r| r.2).reduce(|a, b| a + b).map(|s| s / len);
                            let json = v.first().and_then(|r| r.3.clone());
                            Some((ts, p_a, p_r, json))
                        }
                    })
                })
                .collect();
        }
    }

    let points: Vec<DeviceDataPoint> = results
        .into_iter()
        .map(|(ts, p_a, p_r, json_str)| {
            let data_json = json_str.as_ref().and_then(|s| serde_json::from_str(s).ok());
            DeviceDataPoint {
                device_id: device_id.clone(),
                timestamp: ts,
                p_active: p_a,
                p_reactive: p_r,
                data_json,
            }
        })
        .collect();
    Ok(points)
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DashboardCsvData {
    pub device_ids: Vec<String>,
    pub points_by_device: HashMap<String, Vec<DeviceDataPoint>>,
}

/// 解析长表 CSV，支持列名：device_id, timestamp 或 local_timestamp, p_active 或 p_mw, p_reactive 或 q_mvar, data_json（可选）。
/// 与本地 device_data 表同构的 CSV 或 remote-tool 导出的长表格式。
#[tauri::command]
pub async fn dashboard_parse_csv(file_path: String) -> Result<DashboardCsvData, String> {
    let file = File::open(&file_path).map_err(|e| format!("打开文件失败: {}", e))?;
    let mut rdr = csv::Reader::from_reader(BufReader::new(file));
    let headers = rdr.headers().map_err(|e| format!("读取表头失败: {}", e))?;
    let headers: Vec<String> = headers.iter().map(|h| h.trim().to_string()).collect();

    let idx_device_id = headers.iter().position(|h| h.eq_ignore_ascii_case("device_id"))
        .ok_or("CSV 缺少 device_id 列")?;
    let idx_timestamp = headers.iter().position(|h| h.eq_ignore_ascii_case("timestamp") || h.eq_ignore_ascii_case("local_timestamp"))
        .ok_or("CSV 缺少 timestamp 或 local_timestamp 列")?;
    let idx_p_active = headers.iter().position(|h| h.eq_ignore_ascii_case("p_active"));
    let idx_p_mw = headers.iter().position(|h| h.eq_ignore_ascii_case("p_mw"));
    let idx_p_reactive = headers.iter().position(|h| h.eq_ignore_ascii_case("p_reactive"));
    let idx_q_mvar = headers.iter().position(|h| h.eq_ignore_ascii_case("q_mvar"));
    let idx_data_json = headers.iter().position(|h| h.eq_ignore_ascii_case("data_json"));

    let mut points_by_device: HashMap<String, Vec<DeviceDataPoint>> = HashMap::new();
    let mut device_ids_set: std::collections::HashSet<String> = std::collections::HashSet::new();

    for result in rdr.records() {
        let record = result.map_err(|e| format!("解析行失败: {}", e))?;
        if record.len() <= idx_device_id.max(idx_timestamp) {
            continue;
        }
        let device_id = record.get(idx_device_id).unwrap().trim().to_string();
        if device_id.is_empty() {
            continue;
        }
        let ts_str = record.get(idx_timestamp).unwrap().trim();
        let timestamp = parse_timestamp(ts_str).unwrap_or(0.0);
        let p_active = idx_p_active
            .and_then(|i| record.get(i))
            .and_then(|s| s.trim().parse::<f64>().ok())
            .or_else(|| {
                idx_p_mw.and_then(|i| record.get(i))
                    .and_then(|s| s.trim().parse::<f64>().ok())
                    .map(|mw| mw * 1000.0)
            });
        let p_reactive = idx_p_reactive
            .and_then(|i| record.get(i))
            .and_then(|s| s.trim().parse::<f64>().ok())
            .or_else(|| {
                idx_q_mvar.and_then(|i| record.get(i))
                    .and_then(|s| s.trim().parse::<f64>().ok())
                    .map(|mvar| mvar * 1000.0)
            });
        let data_json = idx_data_json
            .and_then(|i| record.get(i))
            .map(|s| s.trim())
            .filter(|s| !s.is_empty() && !s.eq_ignore_ascii_case("null"))
            .and_then(|s| serde_json::from_str(s).ok());

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
    Ok(DashboardCsvData {
        device_ids,
        points_by_device,
    })
}

fn parse_timestamp(s: &str) -> Option<f64> {
    let s = s.trim();
    if s.is_empty() {
        return None;
    }
    if let Ok(t) = s.parse::<f64>() {
        if t > 1e12 {
            return Some(t / 1000.0);
        }
        return Some(t);
    }
    if let Ok(t) = s.parse::<i64>() {
        let t = t as f64;
        if t > 1e12 {
            return Some(t / 1000.0);
        }
        return Some(t);
    }
    chrono::DateTime::parse_from_rfc3339(s)
        .ok()
        .map(|dt| dt.timestamp_millis() as f64 / 1000.0)
        .or_else(|| {
            chrono::NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S%.3f")
                .ok()
                .and_then(|dt| dt.and_local_timezone(chrono::Utc).single().map(|dtu| dtu.timestamp_millis() as f64 / 1000.0))
        })
        .or_else(|| {
            chrono::NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S")
                .ok()
                .and_then(|dt| dt.and_local_timezone(chrono::Utc).single().map(|dtu| dtu.timestamp_millis() as f64 / 1000.0))
        })
}
