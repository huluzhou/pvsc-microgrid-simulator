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

/// 性能分析：数据角色到 key 的映射
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceDataMapping {
    /// 实测功率（必填）
    pub measured_power_key: String,
    /// 功率指令/参考信号
    pub reference_power_key: Option<String>,
    /// 额定功率 kW
    pub rated_power_kw: Option<f64>,
    /// 额定容量 kWh
    pub rated_capacity_kwh: Option<f64>,
    /// 对齐方式：ffill | linear | valid_only，默认 ffill
    pub alignment_method: Option<String>,
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
    /// 性能分析：待分析的功率数据项 key 列表；若有 performance_data_mapping 则从其 keys 解析
    pub data_item_keys: Vec<String>,
    /// 收益分析：关口电表有功功率数据项 key
    pub gateway_meter_active_power_key: Option<String>,
    /// 收益分析：电价配置
    pub price_config: Option<PriceConfig>,
    /// CSV 数据源时由前端传入已加载的序列，避免后端重复解析；key -> 时间序列
    pub series_data: Option<HashMap<String, Vec<TimeSeriesPoint>>>,
    /// 性能分析：按标准筛选，如 ["GB_T_36548_2024", "GB_T_36549_2018", ...]
    #[serde(default)]
    pub performance_standards: Option<Vec<String>>,
    /// 性能分析：数据角色映射
    #[serde(default)]
    pub performance_data_mapping: Option<PerformanceDataMapping>,
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
    #[serde(default)]
    pub performance_standards: Option<Vec<String>>,
    #[serde(default)]
    pub performance_data_mapping: Option<PerformanceDataMapping>,
}

/// 根据请求解析得到各 key 的时间序列（仅 [start_time, end_time] 内）
async fn resolve_series(
    request: &AnalysisRequest,
) -> Result<HashMap<String, Vec<dashboard::TimeSeriesPoint>>, String> {
    let start = request.start_time;
    let end = request.end_time;

    let keys: Vec<String> = match request.analysis_type.as_str() {
        "performance" => {
            if let Some(ref mapping) = request.performance_data_mapping {
                let mut k = vec![mapping.measured_power_key.clone()];
                if let Some(ref ref_key) = mapping.reference_power_key {
                    k.push(ref_key.clone());
                }
                k
            } else {
                request.data_item_keys.clone()
            }
        }
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

    let mut series = match &request.data_source {
        DataSourceKind::LocalFile => {
            let path = request.file_path.as_ref().ok_or("本地文件数据源需提供 file_path")?;
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

/// 空值判定
fn is_valid(v: f64) -> bool {
    v.is_finite()
}

/// 对齐方式
#[derive(Clone, Copy, PartialEq)]
enum AlignMethod {
    Ffill,
    Linear,
    ValidOnly,
}

/// 对齐实测与参考功率序列，输出 (ts, p_meas, p_ref)
fn align_series(
    measured: &[dashboard::TimeSeriesPoint],
    reference: Option<&[dashboard::TimeSeriesPoint]>,
    method: AlignMethod,
) -> Vec<(f64, f64, f64)> {
    let ref_pts = reference.unwrap_or(&[]);
    if ref_pts.is_empty() {
        return measured
            .iter()
            .filter(|p| is_valid(p.value))
            .map(|p| (p.timestamp, p.value, f64::NAN))
            .collect();
    }

    let mut all_ts: Vec<f64> = measured.iter().map(|p| p.timestamp).collect();
    for p in ref_pts {
        all_ts.push(p.timestamp);
    }
    all_ts.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    all_ts.dedup();

    let meas_map: HashMap<i64, f64> = measured
        .iter()
        .filter(|p| is_valid(p.value))
        .map(|p| ((p.timestamp * 1000.0) as i64, p.value))
        .collect();
    let ref_map: HashMap<i64, f64> = ref_pts
        .iter()
        .filter(|p| is_valid(p.value))
        .map(|p| ((p.timestamp * 1000.0) as i64, p.value))
        .collect();

    let mut result = Vec::with_capacity(all_ts.len());
    let mut last_meas = f64::NAN;
    let mut last_ref = f64::NAN;

    for &ts in &all_ts {
        let ts_i = (ts * 1000.0) as i64;
        let p_meas = if let Some(&v) = meas_map.get(&ts_i) {
            last_meas = v;
            v
        } else {
            match method {
                AlignMethod::Ffill => last_meas,
                AlignMethod::Linear => last_meas,
                AlignMethod::ValidOnly => f64::NAN,
            }
        };

        let p_ref = if let Some(&v) = ref_map.get(&ts_i) {
            last_ref = v;
            v
        } else {
            match method {
                AlignMethod::Ffill => last_ref,
                AlignMethod::Linear => last_ref,
                AlignMethod::ValidOnly => f64::NAN,
            }
        };

        if method == AlignMethod::ValidOnly && (!p_meas.is_finite() || !p_ref.is_finite()) {
            continue;
        }
        result.push((ts, p_meas, p_ref));
    }
    result
}

/// 性能分析：功率相关指标，标注国标/行标/国际标准
fn run_performance_analysis(
    series: HashMap<String, Vec<dashboard::TimeSeriesPoint>>,
    mapping: Option<&PerformanceDataMapping>,
    _standards: Option<&[String]>,
    start_time: f64,
    end_time: f64,
) -> AnalysisResult {
    let mut summary = serde_json::Map::new();
    let mut details = serde_json::Map::new();
    let mut charts: Vec<ChartData> = Vec::new();

    let (meas_key, ref_key) = mapping
        .map(|m| (m.measured_power_key.clone(), m.reference_power_key.clone()))
        .unwrap_or_else(|| {
            let k = series.keys().next().cloned().unwrap_or_default();
            (k.clone(), None)
        });

    let measured = series.get(&meas_key).cloned().unwrap_or_default();
    let reference = ref_key.as_ref().and_then(|k| series.get(k)).cloned();

    if measured.is_empty() {
        return AnalysisResult {
            analysis_type: "performance".to_string(),
            summary: serde_json::json!({ "error": "无实测功率数据" }),
            details: serde_json::json!({}),
            charts: vec![],
        };
    }

    let align_method = mapping
        .and_then(|m| m.alignment_method.as_deref())
        .unwrap_or("ffill");
    let method = match align_method {
        "linear" => AlignMethod::Linear,
        "valid_only" => AlignMethod::ValidOnly,
        _ => AlignMethod::Ffill,
    };

    let aligned = align_series(
        &measured,
        reference.as_deref(),
        method,
    );

    let rated_power = mapping.and_then(|m| m.rated_power_kw);
    let rated_capacity = mapping.and_then(|m| m.rated_capacity_kwh);
    let period_hours = (end_time - start_time) / 3600.0;

    // 过滤有效点用于单路指标
    let valid_pts: Vec<(f64, f64, f64)> = aligned
        .into_iter()
        .filter(|(_, p, _)| is_valid(*p))
        .collect();

    if valid_pts.is_empty() {
        return AnalysisResult {
            analysis_type: "performance".to_string(),
            summary: serde_json::json!({ "error": "无有效功率数据" }),
            details: serde_json::json!({}),
            charts: vec![],
        };
    }

    let values: Vec<f64> = valid_pts.iter().map(|(_, p, _)| *p).collect();
    let n = values.len() as f64;
    let mean = values.iter().sum::<f64>() / n;
    let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
    let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;
    let std = variance.sqrt();

    let mut energy_charge_kwh = 0.0;
    let mut energy_discharge_kwh = 0.0;
    for i in 1..valid_pts.len() {
        let (t0, p0, _) = valid_pts[i - 1];
        let (t1, p1, _) = valid_pts[i];
        let dt_h = (t1 - t0) / 3600.0;
        let p_avg = (p0 + p1) * 0.5;
        if p_avg < 0.0 {
            energy_charge_kwh += (-p_avg) * dt_h;
        } else if p_avg > 0.0 {
            energy_discharge_kwh += p_avg * dt_h;
        }
    }

    let round_trip_efficiency_pct = if energy_charge_kwh > 1e-6 {
        (energy_discharge_kwh / energy_charge_kwh * 100.0).min(100.0)
    } else {
        f64::NAN
    };

    let mut ramp_rate_max = 0.0;
    for i in 1..valid_pts.len() {
        let (t0, p0, _) = valid_pts[i - 1];
        let (t1, p1, _) = valid_pts[i];
        let dt = t1 - t0;
        if dt > 1e-9 {
            let dr = (p1 - p0).abs() / dt;
            if dr.is_finite() && dr > ramp_rate_max {
                ramp_rate_max = dr;
            }
        }
    }

    let performance_ratio = if max.abs() > 1e-6 {
        (mean.abs() / max.abs()).min(1.0)
    } else {
        f64::NAN
    };

    let tau = 1.0;
    let mut time_run = 0.0;
    let mut time_total = 0.0;
    for i in 1..valid_pts.len() {
        let (t0, p0, _) = valid_pts[i - 1];
        let (t1, p1, _) = valid_pts[i];
        let dt = t1 - t0;
        time_total += dt;
        if p0.abs() > tau || p1.abs() > tau {
            time_run += dt;
        }
    }
    let time_utilization_pct = if time_total > 1e-9 {
        (time_run / time_total * 100.0).min(100.0)
    } else {
        f64::NAN
    };

    let capacity_utilization_pct = if let (Some(er), true) = (rated_capacity, period_hours > 1e-6) {
        let denom = er * period_hours;
        if denom > 1e-6 {
            ((energy_charge_kwh + energy_discharge_kwh) / denom * 100.0).min(100.0)
        } else {
            f64::NAN
        }
    } else {
        f64::NAN
    };

    let (power_utilization_pct, power_utilization_max_pct) = if let Some(pr) = rated_power {
        if pr > 1e-6 {
            (
                (mean.abs() / pr * 100.0).min(100.0),
                (max.abs() / pr * 100.0).min(100.0),
            )
        } else {
            (f64::NAN, f64::NAN)
        }
    } else {
        (f64::NAN, f64::NAN)
    };

    let eta = if round_trip_efficiency_pct.is_finite() {
        round_trip_efficiency_pct / 100.0
    } else {
        0.85
    };
    let mut acc = 0.0;
    let mut demonstrated_capacity = 0.0;
    for i in 1..valid_pts.len() {
        let (t0, p0, _) = valid_pts[i - 1];
        let (t1, p1, _) = valid_pts[i];
        let dt_h = (t1 - t0) / 3600.0;
        let p_avg = (p0 + p1) * 0.5;
        if p_avg < 0.0 {
            acc += (-p_avg) * dt_h * eta.sqrt();
        } else if p_avg > 0.0 {
            acc -= p_avg * dt_h / eta.sqrt();
        }
        if acc > demonstrated_capacity {
            demonstrated_capacity = acc;
        }
    }

    let capacity_ratio = if let Some(er) = rated_capacity {
        let soc_min = 0.2;
        let denom = er * (1.0 - soc_min);
        if denom > 1e-6 {
            (demonstrated_capacity / denom).min(1.0)
        } else {
            f64::NAN
        }
    } else {
        f64::NAN
    };

    let valid_pairs: Vec<(f64, f64, f64)> = valid_pts
        .iter()
        .filter(|(_, pm, pr)| is_valid(*pm) && is_valid(*pr))
        .cloned()
        .collect();

    let (control_deviation_pct, rmse_kw, correlation, availability_pct) =
        if !valid_pairs.is_empty() && rated_power.map(|p| p > 1e-6).unwrap_or(false) {
            let m = valid_pairs.len() as f64;
            let p_rated = rated_power.unwrap();
            let dev: f64 = valid_pairs.iter().map(|(_, pm, pref)| (pm - pref).abs()).sum::<f64>() / m / p_rated * 100.0;
            let rms: f64 = (valid_pairs.iter().map(|(_, pm, pref)| (pm - pref).powi(2)).sum::<f64>() / m).sqrt();
            let pm_vec: Vec<f64> = valid_pairs.iter().map(|(_, p, _)| *p).collect();
            let pr_vec: Vec<f64> = valid_pairs.iter().map(|(_, _, p)| *p).collect();
            let pm_mean = pm_vec.iter().sum::<f64>() / m;
            let pr_mean = pr_vec.iter().sum::<f64>() / m;
            let cov: f64 = pm_vec.iter().zip(pr_vec.iter()).map(|(a, b)| (a - pm_mean) * (b - pr_mean)).sum::<f64>() / m;
            let std_pm = (pm_vec.iter().map(|x| (x - pm_mean).powi(2)).sum::<f64>() / m).sqrt();
            let std_pr = (pr_vec.iter().map(|x| (x - pr_mean).powi(2)).sum::<f64>() / m).sqrt();
            let corr = if std_pm > 1e-9 && std_pr > 1e-9 {
                (cov / (std_pm * std_pr)).min(1.0).max(-1.0)
            } else {
                f64::NAN
            };
            let tau_a = (p_rated * 0.01).max(1.0);
            let mut avail_num = 0.0;
            let mut avail_den = 0.0;
            for i in 1..valid_pairs.len() {
                let (t0, pm0, pr0) = valid_pairs[i - 1];
                let (t1, pm1, pr1) = valid_pairs[i];
                let dt = t1 - t0;
                let ref_avg = (pr0 + pr1) * 0.5;
                let meas_avg = (pm0 + pm1) * 0.5;
                if ref_avg > tau_a {
                    avail_den += dt;
                    if meas_avg > tau_a {
                        avail_num += dt;
                    }
                }
            }
            let avail = if avail_den > 1e-9 {
                (avail_num / avail_den * 100.0).min(100.0)
            } else {
                f64::NAN
            };
            (dev, rms, corr, avail)
        } else {
            (f64::NAN, f64::NAN, f64::NAN, f64::NAN)
        };

    let key_summary = serde_json::json!({
        "mean_kw": mean,
        "max_kw": max,
        "min_kw": min,
        "std_kw": std,
        "points": values.len(),
        "energy_charge_kwh": energy_charge_kwh,
        "energy_discharge_kwh": energy_discharge_kwh,
        "round_trip_efficiency_pct": round_trip_efficiency_pct,
        "ramp_rate_max_kw_per_s": ramp_rate_max,
        "performance_ratio": performance_ratio,
        "time_utilization_pct": time_utilization_pct,
        "capacity_utilization_pct": capacity_utilization_pct,
        "power_utilization_pct": power_utilization_pct,
        "power_utilization_max_pct": power_utilization_max_pct,
        "demonstrated_capacity_kwh": demonstrated_capacity,
        "capacity_ratio": capacity_ratio,
        "control_deviation_pct": control_deviation_pct,
        "rmse_kw": rmse_kw,
        "correlation": correlation,
        "availability_pct": availability_pct,
        "indicators_by_standard": {
            "GB_T_36548_2024": {
                "ramp_rate_max_kw_per_s": ramp_rate_max,
                "control_deviation_pct": control_deviation_pct,
                "note": "功率调节爬升率、控制偏差"
            },
            "GB_T_34930_2017": {
                "power_std_kw": std,
                "note": "微电网功率波动性"
            },
            "GB_T_36549_2018": {
                "capacity_utilization_pct": capacity_utilization_pct,
                "power_utilization_pct": power_utilization_pct,
                "time_utilization_pct": time_utilization_pct,
                "note": "容量、功率、时间利用率"
            },
            "IEEE_2836_2021": {
                "round_trip_efficiency_pct": round_trip_efficiency_pct,
                "ramp_rate_max_kw_per_s": ramp_rate_max,
                "rmse_kw": rmse_kw,
                "note": "光储充储能往返效率、爬升率、参考信号跟踪"
            },
            "IEEE_1679_2020": {
                "round_trip_efficiency_pct": round_trip_efficiency_pct,
                "energy_charge_kwh": energy_charge_kwh,
                "energy_discharge_kwh": energy_discharge_kwh,
                "note": "储能表征与评价"
            },
            "FEMP_BESS": {
                "round_trip_efficiency_pct": round_trip_efficiency_pct,
                "availability_pct": availability_pct,
                "performance_ratio": performance_ratio,
                "capacity_ratio": capacity_ratio,
                "demonstrated_capacity_kwh": demonstrated_capacity,
                "note": "效率η、可用率A、性能比、容量比"
            }
        }
    });
    summary.insert(meas_key.clone(), key_summary);
    let timestamps: Vec<f64> = valid_pts.iter().map(|(t, _, _)| *t).collect();
    details.insert(
        meas_key.clone(),
        serde_json::json!({ "timestamps": timestamps, "values": values }),
    );

    let mut series_vec: Vec<serde_json::Value> = Vec::new();
    let data: Vec<Vec<f64>> = measured
        .iter()
        .map(|p| vec![p.timestamp * 1000.0, p.value])
        .collect();
    series_vec.push(serde_json::json!({ "name": meas_key, "data": data }));
    charts.push(ChartData {
        title: "功率时序".to_string(),
        chart_type: "line".to_string(),
        data: serde_json::json!({ "series": series_vec }),
    });

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
        "performance" => run_performance_analysis(
            series,
            request.performance_data_mapping.as_ref(),
            request.performance_standards.as_deref(),
            request.start_time,
            request.end_time,
        ),
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
        performance_standards: request.performance_standards,
        performance_data_mapping: request.performance_data_mapping,
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
