// 数据分析命令：性能分析（功率指标+标准接轨）、收益分析（关口功率+电价）
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::commands::dashboard;
use crate::commands::dashboard::TimeSeriesPoint;

/// 数据源类型
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DataSourceKind {
    LocalFile,
    Csv,
}

/// 电价配置（收益分析）
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriceConfig {
    /// 分时电价，长度 24，单位元/kWh
    pub tou_prices: Vec<f64>,
    /// 电压等级：如 "under_1kv", "1_10kv", "35kv", "110kv", "220kv"
    pub voltage_level: String,
    /// 单一制 "single" 或两部制 "two_part"
    pub tariff_type: String,
    /// 两部制时：最大需量 元/kW·月，或 None
    pub demand_charge_per_kw_month: Option<f64>,
    /// 两部制时：变压器容量 元/kVA·月，或 None
    pub capacity_charge_per_kva_month: Option<f64>,
}

/// 分析请求（统一数据源 + 类型专用参数）
#[derive(Debug, Serialize, Deserialize)]
pub struct AnalysisRequest {
    pub data_source: DataSourceKind,
    /// 本地 DB 或 CSV 文件路径（local_file 必填；csv 可选，若提供 series_data 则可不填）
    pub file_path: Option<String>,
    pub start_time: f64,
    pub end_time: f64,
    /// "performance" | "revenue"
    pub analysis_type: String,
    /// 性能分析：待分析的功率数据项 key 列表
    pub data_item_keys: Vec<String>,
    /// 收益分析：关口电表有功功率数据项 key
    pub gateway_meter_active_power_key: Option<String>,
    /// 收益分析：电价配置
    pub price_config: Option<PriceConfig>,
    /// CSV 数据源时由前端传入已加载的序列，避免后端重复解析；key -> 时间序列
    pub series_data: Option<HashMap<String, Vec<TimeSeriesPoint>>>,
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
    pub chart_type: String,
    pub data: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ReportRequest {
    pub report_type: String,
    pub data_source: DataSourceKind,
    pub file_path: Option<String>,
    pub start_time: f64,
    pub end_time: f64,
    pub data_item_keys: Vec<String>,
    pub gateway_meter_active_power_key: Option<String>,
    pub price_config: Option<PriceConfig>,
    pub series_data: Option<HashMap<String, Vec<TimeSeriesPoint>>>,
    pub format: String,
    /// 报告保存路径（由前端从保存对话框传入）
    pub report_path: Option<String>,
}

/// 根据请求解析得到各 key 的时间序列（仅 [start_time, end_time] 内）
async fn resolve_series(
    request: &AnalysisRequest,
) -> Result<HashMap<String, Vec<dashboard::TimeSeriesPoint>>, String> {
    let start = request.start_time;
    let end = request.end_time;

    let mut series = match &request.data_source {
        DataSourceKind::LocalFile => {
            let path = request.file_path.as_ref().ok_or("本地文件数据源需提供 file_path")?;
            let keys = match request.analysis_type.as_str() {
                "performance" => request.data_item_keys.clone(),
                "revenue" => request
                    .gateway_meter_active_power_key
                    .clone()
                    .map(|k| vec![k])
                    .unwrap_or_default(),
                _ => request.data_item_keys.clone(),
            };
            if keys.is_empty() {
                return Err("未指定数据项 key".to_string());
            }
            dashboard::dashboard_fetch_series_batch(
                path.clone(),
                keys,
                Some(start),
                Some(end),
                Some(5000),
            )
            .await?
        }
        DataSourceKind::Csv => {
            let data = request
                .series_data
                .as_ref()
                .ok_or("CSV 数据源需在前端传入 series_data")?;
            let keys: Vec<String> = match request.analysis_type.as_str() {
                "performance" => request.data_item_keys.clone(),
                "revenue" => request
                    .gateway_meter_active_power_key
                    .clone()
                    .map(|k| vec![k])
                    .unwrap_or_default(),
                _ => request.data_item_keys.clone(),
            };
            if keys.is_empty() {
                return Err("未指定数据项 key".to_string());
            }
            let mut out = HashMap::new();
            for key in keys {
                if let Some(pts) = data.get(&key) {
                    let filtered: Vec<dashboard::TimeSeriesPoint> = pts
                        .iter()
                        .filter(|p| p.timestamp >= start && p.timestamp <= end)
                        .cloned()
                        .collect();
                    out.insert(key, filtered);
                }
            }
            out
        }
    };

    for (_k, v) in series.iter_mut() {
        v.sort_by(|a, b| a.timestamp.partial_cmp(&b.timestamp).unwrap_or(std::cmp::Ordering::Equal));
    }
    Ok(series)
}

/// 性能分析：功率相关指标，标注国标/行标/国际标准
fn run_performance_analysis(
    series: HashMap<String, Vec<dashboard::TimeSeriesPoint>>,
) -> AnalysisResult {
    let mut summary = serde_json::Map::new();
    let mut details = serde_json::Map::new();
    let mut charts: Vec<ChartData> = Vec::new();

    for (key, pts) in &series {
        if pts.is_empty() {
            continue;
        }
        let values: Vec<f64> = pts.iter().map(|p| p.value).collect();
        let n = values.len() as f64;
        let mean = values.iter().sum::<f64>() / n;
        let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
        let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;
        let std = variance.sqrt();

        let key_summary = serde_json::json!({
            "mean_kw": mean,
            "max_kw": max,
            "min_kw": min,
            "std_kw": std,
            "points": pts.len(),
            "standard_refs": [
                "GB/T 36548-2024 功率控制与响应",
                "GB/T 34930-2017 微电网运行控制",
                "IEEE 2836-2021 光储充储能性能测试",
                "IEEE 1679-2020 储能表征与评价",
                "FEMP BESS 效率与性能比"
            ]
        });
        summary.insert(key.clone(), key_summary);
        details.insert(
            key.clone(),
            serde_json::json!({ "timestamps": pts.iter().map(|p| p.timestamp).collect::<Vec<_>>(), "values": values }),
        );
    }

    // 可选：汇总多序列的折线图（ECharts 时间轴格式：series[].data = [[ts_ms, value], ...]）
    if series.len() <= 8 {
        let mut series_vec: Vec<serde_json::Value> = Vec::new();
        for (key, pts) in &series {
            let data: Vec<Vec<f64>> = pts
                .iter()
                .map(|p| vec![p.timestamp * 1000.0, p.value])
                .collect();
            series_vec.push(serde_json::json!({ "name": key, "data": data }));
        }
        if !series_vec.is_empty() {
            charts.push(ChartData {
                title: "功率时序".to_string(),
                chart_type: "line".to_string(),
                data: serde_json::json!({ "series": series_vec }),
            });
        }
    }

    AnalysisResult {
        analysis_type: "performance".to_string(),
        summary: serde_json::Value::Object(summary),
        details: serde_json::Value::Object(details),
        charts,
    }
}

/// 固定电度单价表（元/kWh）：电压等级 -> 单一制 | 两部制
fn fixed_unit_price(voltage: &str, tariff_type: &str) -> f64 {
    let (single, two) = match voltage {
        "under_1kv" => (0.2394, None),
        "1_10kv" => (0.2134, Some(0.1357)),
        "35kv" => (0.1884, Some(0.1107)),
        "110kv" => (0.0, Some(0.0857)),
        "220kv" => (0.0, Some(0.0597)),
        _ => (0.2134, Some(0.1357)),
    };
    if tariff_type == "two_part" {
        two.unwrap_or(single)
    } else {
        single
    }
}

/// 收益分析：关口有功积分得电量，分时+固定+两部制
fn run_revenue_analysis(
    series: HashMap<String, Vec<dashboard::TimeSeriesPoint>>,
    config: &PriceConfig,
    start_time: f64,
    end_time: f64,
) -> AnalysisResult {
    let gateway_series = series
        .values()
        .next()
        .cloned()
        .unwrap_or_default();
    if gateway_series.is_empty() {
        return AnalysisResult {
            analysis_type: "revenue".to_string(),
            summary: serde_json::json!({ "error": "无关口功率数据" }),
            details: serde_json::json!({}),
            charts: vec![],
        };
    }

    let tou = &config.tou_prices;
    let hour_prices: Vec<f64> = if tou.len() >= 24 {
        tou[..24].to_vec()
    } else {
        vec![0.5; 24]
    };

    let fixed_unit = fixed_unit_price(&config.voltage_level, &config.tariff_type);

    // 按小时聚合电量（kWh）：用梯形积分近似
    let mut hourly_energy: Vec<f64> = vec![0.0; 24];
    let mut total_energy_kwh = 0.0;
    for i in 1..gateway_series.len() {
        let t0 = gateway_series[i - 1].timestamp;
        let t1 = gateway_series[i].timestamp;
        let p0 = gateway_series[i - 1].value;
        let p1 = gateway_series[i].value;
        if t1 <= t0 {
            continue;
        }
        let dt_h = (t1 - t0) / 3600.0;
        let e = (p0 + p1) * 0.5 * dt_h;
        if e.is_finite() {
            total_energy_kwh += e;
            let hour_idx = ((t0 + t1) * 0.5 / 3600.0).floor() as i32 % 24;
            let idx = (hour_idx.rem_euclid(24)) as usize;
            if idx < 24 {
                hourly_energy[idx] += e;
            }
        }
    }

    let tou_cost: f64 = hourly_energy
        .iter()
        .enumerate()
        .map(|(i, e)| e * hour_prices.get(i).copied().unwrap_or(0.5))
        .sum();
    let fixed_cost = total_energy_kwh * fixed_unit;
    let two_part_cost = if config.tariff_type == "two_part" {
        let demand = config.demand_charge_per_kw_month.unwrap_or(0.0);
        let cap = config.capacity_charge_per_kva_month.unwrap_or(0.0);
        (demand + cap) * (end_time - start_time) / (30.0 * 24.0 * 3600.0)
    } else {
        0.0
    };
    let total_cost = tou_cost + fixed_cost + two_part_cost;

    let summary = serde_json::json!({
        "total_energy_kwh": total_energy_kwh,
        "tou_cost_yuan": tou_cost,
        "fixed_cost_yuan": fixed_cost,
        "two_part_cost_yuan": two_part_cost,
        "total_cost_yuan": total_cost,
        "voltage_level": config.voltage_level,
        "tariff_type": config.tariff_type
    });

    let charts = vec![ChartData {
        title: "分时电量与电费".to_string(),
        chart_type: "bar".to_string(),
        data: serde_json::json!({
            "x": (0..24).map(|i| format!("{}时", i)).collect::<Vec<_>>(),
            "energy": hourly_energy,
            "cost": hourly_energy.iter().enumerate().map(|(i, e)| e * hour_prices.get(i).copied().unwrap_or(0.5)).collect::<Vec<_>>()
        }),
    }];

    AnalysisResult {
        analysis_type: "revenue".to_string(),
        summary,
        details: serde_json::json!({ "hourly_energy_kwh": hourly_energy }),
        charts,
    }
}

#[tauri::command]
pub async fn analyze_performance(request: AnalysisRequest) -> Result<AnalysisResult, String> {
    let series = resolve_series(&request).await?;
    let result = match request.analysis_type.as_str() {
        "performance" => run_performance_analysis(series),
        "revenue" => {
            let config = request
                .price_config
                .as_ref()
                .ok_or("收益分析需提供 price_config")?;
            run_revenue_analysis(
                series,
                config,
                request.start_time,
                request.end_time,
            )
        }
        _ => return Err(format!("未知分析类型: {}", request.analysis_type)),
    };
    Ok(result)
}

#[tauri::command]
pub async fn generate_report(request: ReportRequest) -> Result<String, String> {
    let analysis_request = AnalysisRequest {
        data_source: request.data_source,
        file_path: request.file_path,
        start_time: request.start_time,
        end_time: request.end_time,
        analysis_type: request.report_type,
        data_item_keys: request.data_item_keys,
        gateway_meter_active_power_key: request.gateway_meter_active_power_key,
        price_config: request.price_config,
        series_data: request.series_data,
    };
    let result = analyze_performance(analysis_request).await?;
    let report_path = request.report_path.unwrap_or_else(|| {
        format!(
            "analysis_report_{}_{}.json",
            result.analysis_type,
            chrono::Utc::now().format("%Y%m%d_%H%M%S")
        )
    });
    let content = serde_json::to_string_pretty(&result).map_err(|e| e.to_string())?;
    std::fs::write(&report_path, content).map_err(|e| format!("写入报告失败: {}", e))?;
    Ok(report_path)
}
