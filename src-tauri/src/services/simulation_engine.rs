// 仿真引擎核心
use crate::domain::simulation::{SimulationStatus, DeviceWorkModes};
use crate::domain::topology::Topology;
use crate::services::python_bridge::PythonBridge;
use crate::services::database::Database;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use tokio::sync::Mutex;
use std::collections::HashMap;
use tauri::{AppHandle, Emitter};
use tokio::time::{interval, Duration};
use tokio::sync::mpsc;
use std::time::{SystemTime, UNIX_EPOCH};
use std::sync::Mutex as StdMutex;

pub struct SimulationEngine {
    status: Arc<tokio::sync::Mutex<SimulationStatus>>,
    device_modes: Arc<tokio::sync::Mutex<DeviceWorkModes>>,
    python_bridge: Arc<Mutex<PythonBridge>>,
    topology: Arc<tokio::sync::Mutex<Option<Topology>>>,
    database: Arc<StdMutex<Database>>,
    /// 全局是否允许远程控制（总闸）
    remote_control_enabled: Arc<AtomicBool>,
    /// 按设备是否允许远程控制；未配置时以全局开关为默认
    device_remote_control_allowed: Arc<tokio::sync::Mutex<HashMap<String, bool>>>,
    /// 设备在本轮仿真中的实时在线状态：仅当仿真 Running 且该设备在本轮内成功收到过数据时为 true；停止/暂停后全部视为离线
    device_active_status: Arc<tokio::sync::Mutex<HashMap<String, bool>>>,
    /// 当前功率单一数据源：device_id -> (timestamp, p_active_kw, p_reactive_kvar)，与 device-data-update 同源，供轮询使用
    last_device_power: Arc<StdMutex<HashMap<String, (f64, Option<f64>, Option<f64>)>>>,
    /// 计算循环是否已启动过（只 spawn 一次，避免暂停后再点「启动」产生多个循环导致计算次数暴增）
    calculation_loop_started: Arc<AtomicBool>,
    /// 停止时发送一次，让计算循环退出（停止时真正结束循环，避免空转）
    cancel_tx: Arc<tokio::sync::Mutex<Option<mpsc::Sender<()>>>>,
}

impl SimulationEngine {
    pub fn new(python_bridge: Arc<Mutex<PythonBridge>>, database: Arc<StdMutex<Database>>) -> Self {
        Self {
            status: Arc::new(tokio::sync::Mutex::new(SimulationStatus::new())),
            device_modes: Arc::new(tokio::sync::Mutex::new(HashMap::new())),
            python_bridge,
            topology: Arc::new(tokio::sync::Mutex::new(None)),
            database,
            remote_control_enabled: Arc::new(AtomicBool::new(true)),
            device_remote_control_allowed: Arc::new(tokio::sync::Mutex::new(HashMap::new())),
            device_active_status: Arc::new(tokio::sync::Mutex::new(HashMap::new())),
            last_device_power: Arc::new(StdMutex::new(HashMap::new())),
            calculation_loop_started: Arc::new(AtomicBool::new(false)),
            cancel_tx: Arc::new(tokio::sync::Mutex::new(None)),
        }
    }

    pub fn set_remote_control_enabled(&self, enabled: bool) {
        self.remote_control_enabled.store(enabled, Ordering::Relaxed);
    }

    pub fn remote_control_enabled(&self) -> bool {
        self.remote_control_enabled.load(Ordering::Relaxed)
    }

    /// 设置单个设备是否允许远程控制；未配置时以全局开关为默认
    pub async fn set_device_remote_control_enabled(&self, device_id: String, enabled: bool) {
        let mut m = self.device_remote_control_allowed.lock().await;
        m.insert(device_id, enabled);
    }

    /// 该设备是否允许远程控制（未配置时用全局开关）
    pub async fn device_remote_control_allowed(&self, device_id: &str) -> bool {
        if !self.remote_control_enabled() {
            return false;
        }
        let m = self.device_remote_control_allowed.lock().await;
        m.get(device_id).copied().unwrap_or(true)
    }

    pub async fn start(&self, app_handle: Option<AppHandle>, calculation_interval_ms: u64) -> Result<(), String> {
        // 检查 Python bridge 是否已就绪（应该在应用启动时已启动）
        {
            let mut bridge = self.python_bridge.lock().await;
            // 尝试 ping 确认 bridge 已就绪
            // 如果失败，说明启动时有问题，返回错误
            let mut retries = 3;
            let mut bridge_ready = false;
            
            while retries > 0 && !bridge_ready {
                match bridge.call("ping", serde_json::json!({})).await {
                    Ok(_) => {
                        bridge_ready = true;
                    }
                    Err(e) => {
                        eprintln!("Python bridge 未就绪 (剩余重试: {}): {}", retries - 1, e);
                        retries -= 1;
                        if retries > 0 {
                            tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                        }
                    }
                }
            }
            
            if !bridge_ready {
                return Err("Python 内核未就绪，请检查启动日志".to_string());
            }
        }
        
        // 获取拓扑数据
        let topology = self.topology.lock().await.clone();
        if topology.is_none() {
            return Err("拓扑数据未设置，请先加载拓扑".to_string());
        }
        
        // 将拓扑数据转换为标准格式并传递给Python内核
        let topology_data = self.convert_topology_to_standard_format(&topology.unwrap()).await?;
        
        // 新一轮仿真开始，清空设备在线状态与功率缓存，等首拍成功后再标记为在线
        self.device_active_status.lock().await.clear();
        self.last_device_power.lock().unwrap().clear();
        
        let mut bridge = self.python_bridge.lock().await;
        
        // 设置拓扑数据
        let set_topology_params = serde_json::json!({
            "topology_data": topology_data
        });
        let set_topology_result = bridge.call("simulation.set_topology", set_topology_params).await
            .map_err(|e| format!("Failed to set topology: {}", e))?;
        // Python 端 set_topology 异常时返回 result: { status: "error", message: "..." }，需检查并提前返回
        if let Some(status) = set_topology_result.get("status").and_then(|v| v.as_str()) {
            if status == "error" {
                let msg = set_topology_result.get("message")
                    .and_then(|v| v.as_str())
                    .unwrap_or("设置拓扑失败");
                return Err(format!("拓扑设置失败: {}", msg));
            }
        }
        
        // 启动仿真
        let mut status = self.status.lock().await;
        status.start();
        let start_ts = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs_f64();
        drop(status);
        if let Ok(db) = self.database.lock() {
            let _ = db.set_latest_simulation_start(start_ts);
        }
        
        let start_params = serde_json::json!({
            "calculation_interval_ms": calculation_interval_ms
        });
        bridge.call("simulation.start", start_params).await
            .map_err(|e| format!("Failed to start simulation: {}", e))?;
        drop(bridge);
        
        // 只 spawn 一次计算循环，避免「暂停后再点启动」产生多个循环导致计算次数暴增（如 1000ms 间隔却 3s 内 18 次）
        let should_spawn = !self.calculation_loop_started.swap(true, Ordering::SeqCst);
        if should_spawn {
            if let Some(app) = app_handle {
                self.start_calculation_loop(app, calculation_interval_ms).await;
            }
        }
        
        Ok(())
    }
    
    async fn convert_topology_to_standard_format(&self, topology: &Topology) -> Result<serde_json::Value, String> {
        // 转换设备
        let mut devices: serde_json::Map<String, serde_json::Value> = serde_json::Map::new();
        for (device_id, device) in &topology.devices {
            let device_type = match device.device_type {
                crate::domain::topology::DeviceType::Node => "Node",
                crate::domain::topology::DeviceType::Line => "Line",
                crate::domain::topology::DeviceType::Transformer => "Transformer",
                crate::domain::topology::DeviceType::Switch => "Switch",
                crate::domain::topology::DeviceType::Pv => "Pv",
                crate::domain::topology::DeviceType::Storage => "Storage",
                crate::domain::topology::DeviceType::Load => "Load",
                crate::domain::topology::DeviceType::Charger => "Charger",
                crate::domain::topology::DeviceType::Meter => "Meter",
                crate::domain::topology::DeviceType::ExternalGrid => "ExternalGrid",
            };
            
            let mut device_obj = serde_json::Map::new();
            device_obj.insert("device_type".to_string(), serde_json::Value::String(device_type.to_string()));
            device_obj.insert("name".to_string(), serde_json::Value::String(device.name.clone()));
            device_obj.insert("properties".to_string(), serde_json::to_value(&device.properties).unwrap_or(serde_json::Value::Object(serde_json::Map::new())));
            
            if let Some(pos) = &device.position {
                device_obj.insert("position".to_string(), serde_json::json!({
                    "x": pos.x,
                    "y": pos.y,
                    "z": pos.z
                }));
            }
            
            if let Some(loc) = &device.location {
                device_obj.insert("location".to_string(), serde_json::json!({
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "altitude": loc.altitude
                }));
            }
            
            devices.insert(device_id.clone(), serde_json::Value::Object(device_obj));
        }
        
        // 转换连接
        let mut connections = Vec::new();
        for (conn_id, conn) in &topology.connections {
            let mut conn_obj = serde_json::Map::new();
            conn_obj.insert("id".to_string(), serde_json::Value::String(conn_id.clone()));
            conn_obj.insert("from".to_string(), serde_json::Value::String(conn.from_device_id.clone()));
            conn_obj.insert("to".to_string(), serde_json::Value::String(conn.to_device_id.clone()));
            conn_obj.insert("connection_type".to_string(), serde_json::Value::String(conn.connection_type.clone()));
            
            if let Some(from_port) = &conn.from_port {
                conn_obj.insert("from_port".to_string(), serde_json::Value::String(from_port.clone()));
            }
            if let Some(to_port) = &conn.to_port {
                conn_obj.insert("to_port".to_string(), serde_json::Value::String(to_port.clone()));
            }
            if !conn.properties.is_empty() {
                conn_obj.insert("properties".to_string(), serde_json::to_value(&conn.properties).unwrap_or(serde_json::Value::Object(serde_json::Map::new())));
            }
            
            connections.push(serde_json::Value::Object(conn_obj));
        }
        
        Ok(serde_json::json!({
            "devices": devices,
            "connections": connections
        }))
    }
    
    async fn start_calculation_loop(&self, app: AppHandle, calculation_interval_ms: u64) {
        let (tx, mut rx) = mpsc::channel(1);
        {
            let mut guard = self.cancel_tx.lock().await;
            *guard = Some(tx);
        }
        let status = self.status.clone();
        let python_bridge = self.python_bridge.clone();
        let topology = self.topology.clone();
        let database = self.database.clone();
        let device_active_status = self.device_active_status.clone();
        let last_device_power = self.last_device_power.clone();
        let calculation_loop_started = self.calculation_loop_started.clone();
        
        tokio::spawn(async move {
            let mut interval = interval(Duration::from_millis(calculation_interval_ms));
            let mut calculation_times: Vec<f64> = Vec::new();
            
            loop {
                tokio::select! {
                    _ = interval.tick() => {}
                    _ = rx.recv() => {
                        calculation_loop_started.store(false, Ordering::SeqCst);
                        break;
                    }
                }
                
                // 检查仿真是否运行中
                let status_guard = status.lock().await;
                let is_running = status_guard.state == crate::domain::simulation::SimulationState::Running;
                drop(status_guard);
                
                if !is_running {
                    continue;
                }
                
                let start_time = std::time::Instant::now();
                
                // 获取计算状态和结果
                let mut bridge = python_bridge.lock().await;
                
                // 获取计算状态
                if let Ok(status_result) = bridge.call("simulation.get_calculation_status", serde_json::json!({})).await {
                    if let Some(count) = status_result.get("calculation_count").and_then(|v| v.as_u64()) {
                        let mut status_guard = status.lock().await;
                        status_guard.calculation_count = count;
                        drop(status_guard);
                    }
                }
                
                // 获取错误信息
                if let Ok(errors_result) = bridge.call("simulation.get_errors", serde_json::json!({})).await {
                    if let Some(errors_array) = errors_result.get("errors").and_then(|v| v.as_array()) {
                        // 将 Python 返回的错误数组转换为 Rust 结构
                        let new_errors: Vec<crate::domain::simulation::SimulationError> = errors_array
                            .iter()
                            .filter_map(|e| {
                                // 转换字段名和格式：Python 返回 "type"，Rust 期望 "error_type"
                                let mut error_obj = e.clone();
                                
                                // 将 "type" 字段重命名为 "error_type"
                                // 需要先检查是否是 Object 类型，然后转换为 Map 进行操作
                                if let serde_json::Value::Object(ref mut map) = error_obj {
                                    if let Some(type_value) = map.remove("type") {
                                        map.insert("error_type".to_string(), type_value);
                                    }
                                    
                                    // 转换时间戳：Python 返回 float（秒），需要转换为 u64
                                    if let Some(serde_json::Value::Number(timestamp_num)) = map.get("timestamp") {
                                        if let Some(timestamp_f64) = timestamp_num.as_f64() {
                                            map.insert("timestamp".to_string(), serde_json::json!(timestamp_f64 as u64));
                                        }
                                    }
                                }
                                
                                serde_json::from_value::<crate::domain::simulation::SimulationError>(error_obj)
                                    .map_err(|err| {
                                        eprintln!("解析错误对象失败: {} - 原始数据: {}", err, serde_json::to_string(e).unwrap_or_default());
                                    })
                                    .ok()
                            })
                            .collect();

                        let status_guard = status.lock().await;
                        let current_errors = status_guard.errors.clone();
                        drop(status_guard);

                        // 如果 Python 返回空错误列表，而当前仍有错误，则保留最后一次错误信息，
                        // 避免在仿真暂停/停止后错误面板被立即清空，便于用户查看错误原因。
                        if new_errors.is_empty() && !current_errors.is_empty() {
                            // 保留当前错误，不更新状态，也不发送事件（避免清空）
                        } else if new_errors != current_errors {
                            // 只有在错误内容实际发生变化时才更新状态并发送事件，
                            // 避免同一条错误在高频刷新时造成前端“闪烁”体验。
                            let mut status_guard = status.lock().await;
                            status_guard.errors = new_errors.clone();
                            drop(status_guard);

                            let _ = app.emit("simulation-errors-update", serde_json::json!({
                                "errors": new_errors
                            }));
                        }
                    }
                }
                
                // 主动触发计算并获取结果（避免时序问题）
                // 这样可以确保获取的是最新计算结果，而不是滞后的结果
                if let Ok(result_data) = bridge.call("simulation.perform_calculation", serde_json::json!({})).await {
                    if let Some(result) = result_data.get("result") {
                        // 检查是否因错误需要自动停止：显式 auto_paused 或（未收敛且有错误）
                        let auto_paused = result.get("auto_paused").and_then(|v| v.as_bool()).unwrap_or(false);
                        let converged = result.get("converged").and_then(|v| v.as_bool()).unwrap_or(false);
                        let has_errors = result.get("errors").and_then(|v| v.as_array()).map(|a| !a.is_empty()).unwrap_or(false);
                        let should_stop = auto_paused || (!converged && has_errors);
                        if should_stop {
                            // 先把本次 result 里的错误写入状态并通知前端，否则第一次停止时 get_errors 尚未更新，界面会看不到错误
                            if let Some(errors_array) = result.get("errors").and_then(|v| v.as_array()) {
                                let new_errors: Vec<crate::domain::simulation::SimulationError> = errors_array
                                    .iter()
                                    .filter_map(|e| {
                                        let mut error_obj = e.clone();
                                        if let serde_json::Value::Object(ref mut map) = error_obj {
                                            if let Some(type_value) = map.remove("type") {
                                                map.insert("error_type".to_string(), type_value);
                                            }
                                            if let Some(serde_json::Value::Number(timestamp_num)) = map.get("timestamp") {
                                                if let Some(timestamp_f64) = timestamp_num.as_f64() {
                                                    map.insert("timestamp".to_string(), serde_json::json!(timestamp_f64 as u64));
                                                }
                                            }
                                        }
                                        serde_json::from_value::<crate::domain::simulation::SimulationError>(error_obj).ok()
                                    })
                                    .collect();
                                if !new_errors.is_empty() {
                                    let mut status_guard = status.lock().await;
                                    status_guard.errors = new_errors.clone();
                                    drop(status_guard);
                                    let _ = app.emit("simulation-errors-update", serde_json::json!({ "errors": new_errors }));
                                }
                            }
                            // 再执行停止，与用户点击「停止」一致
                            let mut status_guard = status.lock().await;
                            status_guard.stop();
                            drop(status_guard);

                            let stop_params = serde_json::json!({ "action": "stop" });
                            if let Err(e) = bridge.call("simulation.stop", stop_params).await {
                                eprintln!("自动停止时调用 simulation.stop 失败: {}", e);
                            }
                            eprintln!("检测到严重错误，仿真已自动停止");
                            let _ = app.emit("simulation-auto-stopped", serde_json::json!({
                                "reason": "严重错误导致计算失败"
                            }));
                        }
                        
                        // 处理计算结果并存储到数据库
                        if let Some(devices) = result.get("devices") {
                            // 提取设备数据并存储
                            let topo = topology.lock().await;
                            if let Some(ref t) = topo.as_ref() {
                                // 获取当前时间戳
                                let timestamp = SystemTime::now()
                                    .duration_since(UNIX_EPOCH)
                                    .unwrap()
                                    .as_secs_f64();
                                
                                // 处理并存储计算结果（传入完整拓扑以便电表落库与连接解析；同时更新功率缓存供轮询使用）
                                Self::process_calculation_results_inline(&app, devices, t, &database, &last_device_power, timestamp);
                                // 本拍成功获取到数据，标记拓扑内设备在本轮仿真中为在线
                                let mut active = device_active_status.lock().await;
                                for id in t.devices.keys() {
                                    active.insert(id.clone(), true);
                                }
                            }
                            drop(topo);
                        }
                        
                        // 发送计算结果更新事件
                        let _ = app.emit("calculation-result-update", result);
                    }
                }
                
                drop(bridge);
                
                // 本步总耗时（含 RPC + 计算 + 处理），用于更新每步平均耗时
                let elapsed_ms = start_time.elapsed().as_millis() as f64;
                calculation_times.push(elapsed_ms);
                if calculation_times.len() > 100 {
                    calculation_times.remove(0);
                }
                
                let avg_delay = calculation_times.iter().sum::<f64>() / calculation_times.len() as f64;
                let mut status_guard = status.lock().await;
                status_guard.average_delay = avg_delay;
                
                // 更新运行时间（仅统计运行中时间，减去累计暂停时长，与 calculation_count 同步）
                if let Some(start_time) = status_guard.start_time {
                    let now = SystemTime::now()
                        .duration_since(UNIX_EPOCH)
                        .unwrap()
                        .as_secs();
                    status_guard.elapsed_time = now
                        .saturating_sub(start_time)
                        .saturating_sub(status_guard.total_paused_secs);
                }
                drop(status_guard);
            }
        });
    }
    
    /// 从拓扑构建 目标设备 id -> 指向该设备的电表 id 列表（用于落库时把目标数据也写入电表）
    fn build_target_to_meters(topology: &Topology) -> HashMap<String, Vec<String>> {
        use crate::domain::topology::DeviceType;
        let mut target_to_meters: HashMap<String, Vec<String>> = HashMap::new();
        for conn in topology.connections.values() {
            let from_id = &conn.from_device_id;
            let to_id = &conn.to_device_id;
            let from_is_meter = topology.devices.get(from_id).map(|d| d.device_type == DeviceType::Meter).unwrap_or(false);
            let to_is_meter = topology.devices.get(to_id).map(|d| d.device_type == DeviceType::Meter).unwrap_or(false);
            if from_is_meter {
                target_to_meters.entry(to_id.clone()).or_default().push(from_id.clone());
            }
            if to_is_meter {
                target_to_meters.entry(from_id.clone()).or_default().push(to_id.clone());
            }
        }
        target_to_meters
    }

    fn process_calculation_results_inline(
        app: &AppHandle,
        results: &serde_json::Value,
        topology: &Topology,
        database: &Arc<StdMutex<Database>>,
        last_device_power: &Arc<StdMutex<HashMap<String, (f64, Option<f64>, Option<f64>)>>>,
        timestamp: f64,
    ) {
        let devices = &topology.devices;
        let target_to_meters = Self::build_target_to_meters(topology);

        // 处理计算结果并存储到数据库（仅功率设备与电表；母线、线路、变压器不落库）
        // 同时发送事件通知前端
        
        // 建立设备ID到设备类型的映射，用于查找设备（保留以备将来使用）
        let _device_id_to_type: HashMap<String, &str> = devices.iter()
            .map(|(id, device)| (id.clone(), match device.device_type {
                crate::domain::topology::DeviceType::Node => "Node",
                crate::domain::topology::DeviceType::Line => "Line",
                crate::domain::topology::DeviceType::Transformer => "Transformer",
                crate::domain::topology::DeviceType::Load => "Load",
                crate::domain::topology::DeviceType::Pv => "Pv",
                crate::domain::topology::DeviceType::Storage => "Storage",
                crate::domain::topology::DeviceType::Charger => "Charger",
                crate::domain::topology::DeviceType::ExternalGrid => "ExternalGrid",
                crate::domain::topology::DeviceType::Switch => "Switch",
                crate::domain::topology::DeviceType::Meter => "Meter",
            }))
            .collect();
        
        // 处理母线结果（电压数据）
        // 注意：pandapower返回的buses是按索引组织的，需要根据拓扑中的Node设备来映射
        if let Some(buses) = results.get("buses").and_then(|v| v.as_object()) {
            for (_bus_idx_str, bus_data) in buses {
                // 尝试从拓扑中找到对应的Node设备
                // 由于pandapower索引和设备ID的映射关系复杂，这里使用设备名称匹配
                if let Some(bus_name) = bus_data.get("name").and_then(|v| v.as_str()) {
                    // 查找名称匹配的Node设备
                    for (_device_id, device) in devices {
                        if device.device_type == crate::domain::topology::DeviceType::Node 
                            && device.name == bus_name {
                            // 提取电压值（用于验证，但不存储）
                            let _voltage = bus_data.get("vm_pu")
                                .and_then(|v| v.as_f64())
                                .map(|vm_pu| {
                                    // 从设备属性中获取基准电压（vn_kv），转换为实际电压（V）
                                    let vn_kv = device.properties.get("voltage_level")
                                        .and_then(|v| v.as_f64())
                                        .unwrap_or(0.4);
                                    vm_pu * vn_kv * 1000.0 // 转换为V
                                });
                            
                            // 母线（Node）不存储功率数据，只发送事件
                            // 功率数据从连接的设备（Load、Generator等）获取
                            
                            // 发送电压数据更新事件
                            let _ = app.emit("bus-voltage-update", bus_data);
                            break;
                        }
                    }
                }
            }
        }
        
        // 处理线路结果：仅发事件，不落库（数据库只记录功率设备与电表）
        if let Some(lines) = results.get("lines").and_then(|v| v.as_object()) {
            for (_line_idx_str, line_data) in lines {
                let _ = app.emit("line-data-update", line_data);
            }
        }
        
        // 处理负载结果
        if let Some(loads) = results.get("loads").and_then(|v| v.as_object()) {
            for (_load_idx_str, load_data) in loads {
                // 提取有功功率和无功功率
                let p_active_mw = load_data.get("p_mw").and_then(|v| v.as_f64());
                let p_active_kw = p_active_mw.map(|p| p * 1000.0); // 转换为kW
                
                let p_reactive_mvar = load_data.get("q_mvar").and_then(|v| v.as_f64());
                let p_reactive_kvar = p_reactive_mvar.map(|q| q * 1000.0); // 转换为kVar
                
                // 尝试找到对应的Load设备（仅功率设备落库；电表落库其指向节点的数据）
                if let Some(load_name) = load_data.get("name").and_then(|v| v.as_str()) {
                    for (device_id, device) in devices {
                        if device.device_type == crate::domain::topology::DeviceType::Load 
                            && device.name == load_name {
                            let db = database.lock().unwrap();
                            let data_json = serde_json::to_string(load_data).ok();
                            let _ = db.insert_device_data(
                                device_id,
                                timestamp,
                                p_active_kw,
                                p_reactive_kvar,
                                data_json.as_deref(),
                            );
                            for meter_id in target_to_meters.get(device_id).unwrap_or(&vec![]) {
                                let _ = db.insert_device_data(
                                    meter_id,
                                    timestamp,
                                    p_active_kw,
                                    p_reactive_kvar,
                                    data_json.as_deref(),
                                );
                            }
                            let _ = app.emit("device-data-update", serde_json::json!({
                                "device_id": device_id,
                                "data": {
                                    "active_power": p_active_kw,
                                    "reactive_power": p_reactive_kvar,
                                    "timestamp": timestamp
                                }
                            }));
                            if let Ok(mut cache) = last_device_power.lock() {
                                cache.insert(device_id.clone(), (timestamp, p_active_kw, p_reactive_kvar));
                                for meter_id in target_to_meters.get(device_id).unwrap_or(&vec![]) {
                                    cache.insert(meter_id.clone(), (timestamp, p_active_kw, p_reactive_kvar));
                                }
                            }
                            break;
                        }
                    }
                }
                
                if let Some(p_kw) = p_active_kw {
                    let _ = app.emit("load-power-update", serde_json::json!({
                        "p_active_kw": p_kw,
                        "p_reactive_kvar": p_reactive_kvar,
                        "data": load_data
                    }));
                }
            }
        }
        
        // 处理发电机结果
        if let Some(generators) = results.get("generators").and_then(|v| v.as_object()) {
            for (_gen_idx_str, gen_data) in generators {
                // 提取有功功率和无功功率
                let p_active_mw = gen_data.get("p_mw").and_then(|v| v.as_f64());
                let p_active_kw = p_active_mw.map(|p| p * 1000.0); // 转换为kW
                
                let p_reactive_mvar = gen_data.get("q_mvar").and_then(|v| v.as_f64());
                let p_reactive_kvar = p_reactive_mvar.map(|q| q * 1000.0); // 转换为kVar
                
                // 尝试找到对应的Pv设备（功率设备落库；电表落库其指向节点的数据）
                if let Some(gen_name) = gen_data.get("name").and_then(|v| v.as_str()) {
                    for (device_id, device) in devices {
                        if device.device_type == crate::domain::topology::DeviceType::Pv 
                            && device.name == gen_name {
                            let db = database.lock().unwrap();
                            let data_json = serde_json::to_string(gen_data).ok();
                            let _ = db.insert_device_data(
                                device_id,
                                timestamp,
                                p_active_kw,
                                p_reactive_kvar,
                                data_json.as_deref(),
                            );
                            for meter_id in target_to_meters.get(device_id).unwrap_or(&vec![]) {
                                let _ = db.insert_device_data(
                                    meter_id,
                                    timestamp,
                                    p_active_kw,
                                    p_reactive_kvar,
                                    data_json.as_deref(),
                                );
                            }
                            let _ = app.emit("device-data-update", serde_json::json!({
                                "device_id": device_id,
                                "data": {
                                    "active_power": p_active_kw,
                                    "reactive_power": p_reactive_kvar,
                                    "timestamp": timestamp
                                }
                            }));
                            if let Ok(mut cache) = last_device_power.lock() {
                                cache.insert(device_id.clone(), (timestamp, p_active_kw, p_reactive_kvar));
                                for meter_id in target_to_meters.get(device_id).unwrap_or(&vec![]) {
                                    cache.insert(meter_id.clone(), (timestamp, p_active_kw, p_reactive_kvar));
                                }
                            }
                            break;
                        }
                    }
                }
                
                if let Some(p_kw) = p_active_kw {
                    let _ = app.emit("generator-power-update", serde_json::json!({
                        "p_active_kw": p_kw,
                        "p_reactive_kvar": p_reactive_kvar,
                        "data": gen_data
                    }));
                }
            }
        }
        
        // 处理储能结果
        if let Some(storages) = results.get("storages").and_then(|v| v.as_object()) {
            for (_storage_idx_str, storage_data) in storages {
                // 提取有功功率和无功功率
                let p_active_mw = storage_data.get("p_mw").and_then(|v| v.as_f64());
                let p_active_kw = p_active_mw.map(|p| p * 1000.0); // 转换为kW
                
                let p_reactive_mvar = storage_data.get("q_mvar").and_then(|v| v.as_f64());
                let p_reactive_kvar = p_reactive_mvar.map(|q| q * 1000.0); // 转换为kVar
                
                // 尝试找到对应的Storage设备（功率设备落库；电表落库其指向节点的数据）
                if let Some(storage_name) = storage_data.get("name").and_then(|v| v.as_str()) {
                    for (device_id, device) in devices {
                        if device.device_type == crate::domain::topology::DeviceType::Storage 
                            && device.name == storage_name {
                            let db = database.lock().unwrap();
                            let data_json = serde_json::to_string(storage_data).ok();
                            let _ = db.insert_device_data(
                                device_id,
                                timestamp,
                                p_active_kw,
                                p_reactive_kvar,
                                data_json.as_deref(),
                            );
                            for meter_id in target_to_meters.get(device_id).unwrap_or(&vec![]) {
                                let _ = db.insert_device_data(
                                    meter_id,
                                    timestamp,
                                    p_active_kw,
                                    p_reactive_kvar,
                                    data_json.as_deref(),
                                );
                            }
                            let _ = app.emit("device-data-update", serde_json::json!({
                                "device_id": device_id,
                                "data": {
                                    "active_power": p_active_kw,
                                    "reactive_power": p_reactive_kvar,
                                    "timestamp": timestamp
                                }
                            }));
                            if let Ok(mut cache) = last_device_power.lock() {
                                cache.insert(device_id.clone(), (timestamp, p_active_kw, p_reactive_kvar));
                                for meter_id in target_to_meters.get(device_id).unwrap_or(&vec![]) {
                                    cache.insert(meter_id.clone(), (timestamp, p_active_kw, p_reactive_kvar));
                                }
                            }
                            break;
                        }
                    }
                }
                
                let _ = app.emit("storage-data-update", storage_data);
            }
        }
        
        // 处理变压器结果
        if let Some(transformers) = results.get("transformers").and_then(|v| v.as_object()) {
            for (_trafo_idx_str, trafo_data) in transformers {
                // 发送变压器数据更新事件
                let _ = app.emit("transformer-data-update", trafo_data);
            }
        }
    }
    
    async fn process_calculation_results(
        &self,
        app: &AppHandle,
        results: &serde_json::Value,
        _devices: &std::collections::HashMap<String, crate::domain::topology::Device>
    ) {
        // 处理计算结果
        // 注意：实际的数据存储需要通过命令接口完成
        // 这里主要发送事件通知前端
        
        // 处理母线结果（电压数据）
            if let Some(buses) = results.get("buses").and_then(|v| v.as_object()) {
                for (bus_idx_str, bus_data) in buses {
                    let _ = bus_idx_str; // 保留变量名用于调试
                if let Some(_voltage_pu) = bus_data.get("vm_pu").and_then(|v| v.as_f64()) {
                    // 发送电压数据更新事件
                    let _ = app.emit("bus-voltage-update", bus_data);
                }
            }
        }
        
        // 处理线路结果（电流、功率数据）
        if let Some(lines) = results.get("lines").and_then(|v| v.as_object()) {
            for (_line_idx_str, line_data) in lines {
                // 发送线路数据更新事件
                let _ = app.emit("line-data-update", line_data);
            }
        }
        
        // 处理负载结果
        if let Some(loads) = results.get("loads").and_then(|v| v.as_object()) {
            for (_load_idx_str, load_data) in loads {
                if let Some(p_mw) = load_data.get("p_mw").and_then(|v| v.as_f64()) {
                    let power_kw = p_mw * 1000.0;
                    // 发送负载功率更新事件
                    let _ = app.emit("load-power-update", serde_json::json!({
                        "power_kw": power_kw,
                        "data": load_data
                    }));
                }
            }
        }
        
        // 处理发电机结果
        if let Some(generators) = results.get("generators").and_then(|v| v.as_object()) {
            for (_gen_idx_str, gen_data) in generators {
                if let Some(p_mw) = gen_data.get("p_mw").and_then(|v| v.as_f64()) {
                    let power_kw = p_mw * 1000.0;
                    // 发送发电机功率更新事件
                    let _ = app.emit("generator-power-update", serde_json::json!({
                        "power_kw": power_kw,
                        "data": gen_data
                    }));
                }
            }
        }
        
        // 处理储能结果
        if let Some(storages) = results.get("storages").and_then(|v| v.as_object()) {
            for (_storage_idx_str, storage_data) in storages {
                // 发送储能数据更新事件
                let _ = app.emit("storage-data-update", storage_data);
            }
        }
    }

    pub async fn stop(&self) -> Result<(), String> {
        let mut status = self.status.lock().await;
        status.stop();
        drop(status);
        // 通知计算循环退出（停止时真正结束循环）
        if let Some(tx) = self.cancel_tx.lock().await.take() {
            let _ = tx.send(()).await;
        }
        // 仿真已停止，设备数据通道关闭，全部视为离线；清空功率缓存
        self.device_active_status.lock().await.clear();
        self.last_device_power.lock().unwrap().clear();
        
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

    /// 返回当前仿真中“本轮内成功收到过数据”的设备 ID 集合，用于与引擎状态一起决定 is_online
    pub async fn get_device_active_status(&self) -> HashMap<String, bool> {
        self.device_active_status.lock().await.clone()
    }

    /// 当前功率单一数据源：返回设备最新 (timestamp, p_active_kw, p_reactive_kvar)，与 device-data-update 同源
    pub fn get_last_device_power(&self, device_id: &str) -> Option<(f64, Option<f64>, Option<f64>)> {
        let m = self.last_device_power.lock().unwrap();
        m.get(device_id).copied()
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

    /// 事件驱动远程控制：将设备属性增量立即写入仿真，下一拍计算即生效。先检查全局与按设备是否允许远程控制。
    pub async fn update_device_properties_for_simulation(
        &self,
        device_id: String,
        properties: serde_json::Value,
    ) -> Result<(), String> {
        if !self.device_remote_control_allowed(&device_id).await {
            return Ok(());
        }
        let props_map = properties
            .as_object()
            .ok_or_else(|| "properties 必须为对象".to_string())?;
        {
            let mut topo_guard = self.topology.lock().await;
            if let Some(topo) = topo_guard.as_mut() {
                if let Some(device) = topo.devices.get_mut(&device_id) {
                    for (k, v) in props_map {
                        device.properties.insert(k.clone(), v.clone());
                    }
                }
            }
        }
        let mut bridge = self.python_bridge.lock().await;
        let params = serde_json::json!({
            "device_id": device_id,
            "properties": properties
        });
        bridge
            .call("simulation.update_device_properties", params)
            .await
            .map_err(|e| format!("推送设备属性到仿真失败: {}", e))?;
        Ok(())
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
