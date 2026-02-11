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
    // 去除前后空格，以及前导单引号（宽表 CSV 中常见）
    let s = s.trim().trim_start_matches('\'').trim_start_matches('"');
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

// ====== 宽表 CSV 解析 ======

/// 宽表列元信息
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ColumnMeta {
    /// 原始列名
    pub key: String,
    /// 设备 SN（从列名解析）
    pub device_sn: String,
    /// 数据项名称（从列名解析）
    pub data_item: String,
    /// 简化的图例标签
    pub short_label: String,
}

/// 时间序列数据点
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TimeSeriesPoint {
    pub timestamp: f64,
    pub value: f64,
}

/// 宽表 CSV 解析结果
#[derive(Debug, Serialize, Deserialize)]
pub struct WideTableData {
    /// 所有数据列的元信息
    pub columns: Vec<ColumnMeta>,
    /// 每列的时间序列数据（key = 原始列名）
    pub series: HashMap<String, Vec<TimeSeriesPoint>>,
}

/// 从宽表列名中解析设备 SN 和数据项
/// 列名格式: {SN}_{dataItem}，其中 SN 为大写字母+数字
fn parse_column_name(col: &str) -> (String, String) {
    // 尝试匹配模式：SN 全为大写字母或数字，后跟 _ 和数据项
    // 例：TESAR125261GT00CN251225002_activePowerLimit → (TESAR125261GT00CN251225002, activePowerLimit)
    // 例：TMEAD35K050EI00CN251209001_active_power → (TMEAD35K050EI00CN251209001, active_power)
    let bytes = col.as_bytes();
    let mut split_pos = None;
    for i in 0..bytes.len() {
        if bytes[i] == b'_' && i > 0 {
            // 检查 _ 之前是否全部为大写字母/数字
            let prefix_valid = bytes[..i].iter().all(|b| b.is_ascii_uppercase() || b.is_ascii_digit());
            if prefix_valid && i + 1 < bytes.len() {
                split_pos = Some(i);
                break;
            }
        }
    }
    match split_pos {
        Some(pos) => (col[..pos].to_string(), col[pos + 1..].to_string()),
        None => (String::new(), col.to_string()),
    }
}

/// 生成简化的图例标签：取 SN 后 3-4 位作为短 ID
fn make_short_label(device_sn: &str, data_item: &str) -> String {
    if device_sn.is_empty() {
        return data_item.to_string();
    }
    // 取 SN 最后 3 位数字作为短 ID
    let short_id: String = device_sn.chars().rev().take(3).collect::<Vec<_>>().into_iter().rev().collect();
    format!("{}-{}", short_id, data_item)
}

/// 均匀降采样：保留首尾点，中间均匀选取
fn downsample(data: &mut Vec<TimeSeriesPoint>, max_points: usize) {
    if data.len() <= max_points || max_points < 2 {
        return;
    }
    let n = data.len();
    let step = (n - 1) as f64 / (max_points - 1) as f64;
    let mut sampled = Vec::with_capacity(max_points);
    for i in 0..max_points {
        let idx = (i as f64 * step).round() as usize;
        sampled.push(data[idx.min(n - 1)].clone());
    }
    *data = sampled;
}

/// 解析宽表 CSV 文件
/// 列格式：local_timestamp, {SN}_{dataItem}, {SN}_{dataItem}, ...
/// 数据稀疏，大部分单元格为空
/// 每列最多保留 MAX_POINTS_PER_SERIES 个点（自动降采样）
#[tauri::command]
pub async fn dashboard_parse_wide_csv(file_path: String) -> Result<WideTableData, String> {
    const MAX_POINTS_PER_SERIES: usize = 5000;

    let file = File::open(&file_path).map_err(|e| format!("打开文件失败: {}", e))?;
    let mut rdr = csv::Reader::from_reader(BufReader::new(file));
    let headers = rdr.headers().map_err(|e| format!("读取表头失败: {}", e))?;
    let headers: Vec<String> = headers.iter().map(|h| h.trim().trim_matches('"').to_string()).collect();

    // 找到时间戳列
    let ts_idx = headers.iter().position(|h| {
        h.eq_ignore_ascii_case("local_timestamp") || h.eq_ignore_ascii_case("timestamp")
    }).ok_or("CSV 缺少 local_timestamp 或 timestamp 列")?;

    // 解析其余列为数据列
    let mut columns: Vec<ColumnMeta> = Vec::new();
    let mut col_indices: Vec<usize> = Vec::new(); // 对应 headers 中的索引

    for (i, header) in headers.iter().enumerate() {
        if i == ts_idx {
            continue;
        }
        let (device_sn, data_item) = parse_column_name(header);
        let short_label = make_short_label(&device_sn, &data_item);
        columns.push(ColumnMeta {
            key: header.clone(),
            device_sn,
            data_item,
            short_label,
        });
        col_indices.push(i);
    }

    // 为每列初始化时间序列
    let mut series: HashMap<String, Vec<TimeSeriesPoint>> = HashMap::new();
    for col in &columns {
        series.insert(col.key.clone(), Vec::new());
    }

    // 逐行解析
    for result in rdr.records() {
        let record = result.map_err(|e| format!("解析行失败: {}", e))?;
        let ts_str = record.get(ts_idx).unwrap_or("").trim().to_string();
        let timestamp = match parse_timestamp(&ts_str) {
            Some(ts) => ts,
            None => continue,
        };

        for (col_meta, &col_idx) in columns.iter().zip(col_indices.iter()) {
            let cell = record.get(col_idx).unwrap_or("").trim();
            if cell.is_empty() {
                continue;
            }
            if let Ok(value) = cell.parse::<f64>() {
                if let Some(vec) = series.get_mut(&col_meta.key) {
                    vec.push(TimeSeriesPoint { timestamp, value });
                }
            }
        }
    }

    // 对每列降采样
    for (_key, data) in series.iter_mut() {
        downsample(data, MAX_POINTS_PER_SERIES);
    }

    Ok(WideTableData {
        columns,
        series,
    })
}

// ====== 本地 DB 数据列查询 ======

/// 本地 DB 可选的数据列信息
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DbColumnMeta {
    /// 列 key（格式：{device_id}:{field_name}）
    pub key: String,
    /// 设备 ID
    pub device_id: String,
    /// 字段名
    pub field_name: String,
    /// 简化标签
    pub short_label: String,
}

/// 从本地 DB 列出所有可选的数据列
/// 返回每个设备的基本字段（p_active, p_reactive）以及 data_json 中的额外字段
#[tauri::command]
pub async fn dashboard_list_db_columns(db_path: String) -> Result<Vec<DbColumnMeta>, String> {
    let conn = rusqlite::Connection::open(&db_path).map_err(|e| format!("打开数据库失败: {}", e))?;

    // 获取所有设备 ID
    let mut stmt = conn
        .prepare("SELECT DISTINCT device_id FROM device_data ORDER BY device_id")
        .map_err(|e| format!("查询失败: {}", e))?;
    let device_ids: Vec<String> = stmt
        .query_map([], |row| row.get::<_, String>(0))
        .map_err(|e| format!("查询失败: {}", e))?
        .filter_map(|r| r.ok())
        .collect();

    let mut columns: Vec<DbColumnMeta> = Vec::new();

    for device_id in &device_ids {
        let short_id = if device_id.len() > 6 {
            &device_id[device_id.len() - 3..]
        } else {
            device_id
        };

        // 基本字段
        columns.push(DbColumnMeta {
            key: format!("{}:p_active", device_id),
            device_id: device_id.clone(),
            field_name: "p_active".to_string(),
            short_label: format!("{}-p_active", short_id),
        });
        columns.push(DbColumnMeta {
            key: format!("{}:p_reactive", device_id),
            device_id: device_id.clone(),
            field_name: "p_reactive".to_string(),
            short_label: format!("{}-p_reactive", short_id),
        });

        // 尝试读取一行 data_json，解析出额外字段
        let mut stmt = conn
            .prepare("SELECT data_json FROM device_data WHERE device_id = ?1 AND data_json IS NOT NULL AND data_json != '' LIMIT 1")
            .map_err(|e| format!("查询失败: {}", e))?;
        let json_str: Option<String> = stmt
            .query_row(rusqlite::params![device_id], |row| row.get::<_, Option<String>>(0))
            .unwrap_or(None);

        if let Some(json_str) = json_str {
            if let Ok(serde_json::Value::Object(map)) = serde_json::from_str::<serde_json::Value>(&json_str) {
                for field_key in map.keys() {
                    columns.push(DbColumnMeta {
                        key: format!("{}:{}", device_id, field_key),
                        device_id: device_id.clone(),
                        field_name: field_key.clone(),
                        short_label: format!("{}-{}", short_id, field_key),
                    });
                }
            }
        }
    }

    Ok(columns)
}

/// 从本地 DB 查询指定设备指定字段的时间序列
#[tauri::command]
pub async fn dashboard_query_db_series(
    db_path: String,
    device_id: String,
    field_name: String,
    max_points: Option<usize>,
) -> Result<Vec<TimeSeriesPoint>, String> {
    let conn = rusqlite::Connection::open(&db_path).map_err(|e| format!("打开数据库失败: {}", e))?;

    let is_basic_field = field_name == "p_active" || field_name == "p_reactive";

    let mut results: Vec<TimeSeriesPoint> = Vec::new();

    if is_basic_field {
        let query = format!(
            "SELECT timestamp, {} FROM device_data WHERE device_id = ?1 AND {} IS NOT NULL ORDER BY timestamp",
            field_name, field_name
        );
        let mut stmt = conn.prepare(&query).map_err(|e| format!("查询失败: {}", e))?;
        let rows = stmt
            .query_map(rusqlite::params![device_id], |row| {
                Ok((row.get::<_, f64>(0)?, row.get::<_, f64>(1)?))
            })
            .map_err(|e| format!("查询失败: {}", e))?;
        for row in rows.flatten() {
            results.push(TimeSeriesPoint {
                timestamp: row.0,
                value: row.1,
            });
        }
    } else {
        // 从 data_json 中提取字段
        let mut stmt = conn
            .prepare("SELECT timestamp, data_json FROM device_data WHERE device_id = ?1 AND data_json IS NOT NULL ORDER BY timestamp")
            .map_err(|e| format!("查询失败: {}", e))?;
        let rows = stmt
            .query_map(rusqlite::params![device_id], |row| {
                Ok((row.get::<_, f64>(0)?, row.get::<_, String>(1)?))
            })
            .map_err(|e| format!("查询失败: {}", e))?;
        for row in rows.flatten() {
            if let Ok(serde_json::Value::Object(map)) = serde_json::from_str::<serde_json::Value>(&row.1) {
                if let Some(val) = map.get(&field_name).and_then(|v| v.as_f64()) {
                    results.push(TimeSeriesPoint {
                        timestamp: row.0,
                        value: val,
                    });
                }
            }
        }
    }

    // 降采样
    let max_pts = max_points.unwrap_or(5000);
    downsample(&mut results, max_pts);

    Ok(results)
}
