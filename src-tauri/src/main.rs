// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod domain;
mod services;
mod utils;

use tauri::{Emitter, Manager};
use services::python_bridge::PythonBridge;
use services::database::Database;
use services::simulation_engine::SimulationEngine;
use services::modbus::ModbusService;
use services::ssh::SshClient;
use domain::metadata::DeviceMetadataStore;
use std::sync::{Arc, Mutex as StdMutex};
use tokio::sync::{mpsc, Mutex as TokioMutex};

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // 初始化应用设置
            #[cfg(debug_assertions)]
            {
                let window = app.get_webview_window("main").unwrap();
                window.open_devtools();
            }

            // 初始化 Python 桥接（在应用启动时立即启动）
            let python_bridge = PythonBridge::new();
            let python_bridge_arc = Arc::new(TokioMutex::new(python_bridge));

            // 数据库仅在开始仿真时创建（data_<timestamp>.db），不仿真不生成空文件
            let db_arc: Arc<StdMutex<Option<Database>>> = Arc::new(StdMutex::new(None));
            let current_db_path = Arc::new(StdMutex::new(String::new()));

            // 初始化设备元数据仓库
            let metadata_store = DeviceMetadataStore::new();

            // 初始化仿真引擎
            let simulation_engine = Arc::new(SimulationEngine::new(
                python_bridge_arc.clone(),
                db_arc.clone(),
                current_db_path.clone(),
            ));
            
            // 在应用启动时立即启动 Python bridge 并等待就绪
            let python_bridge_clone = python_bridge_arc.clone();
            let app_handle = app.handle().clone();
            
            // 使用 Tauri 的异步运行时启动 Python bridge
            tauri::async_runtime::spawn(async move {
                eprintln!("正在启动 Python 内核进程...");
                let mut bridge = python_bridge_clone.lock().await;
                
                // 启动 Python 进程
                match bridge.start().await {
                    Ok(_) => {
                        eprintln!("Python 进程已启动，等待就绪...");
                        // 等待 Python 进程初始化
                        tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;
                        
                        // 尝试 ping 确认 Python 进程已就绪
                        let mut retries = 5;
                        let mut ready = false;
                        
                        while retries > 0 && !ready {
                            match bridge.call("ping", serde_json::json!({})).await {
                                Ok(_) => {
                                    eprintln!("Python 内核已就绪");
                                    ready = true;
                                    // 发送就绪事件到前端
                                    let _ = app_handle.emit("python-kernel-ready", ());
                                }
                                Err(e) => {
                                    eprintln!("Python 内核尚未就绪 (剩余重试: {}): {}", retries - 1, e);
                                    retries -= 1;
                                    if retries > 0 {
                                        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
                                    }
                                }
                            }
                        }
                        
                        if !ready {
                            eprintln!("警告: Python 内核在多次重试后仍未就绪");
                            let _ = app_handle.emit("python-kernel-error", "Python 内核启动失败");
                        }
                    }
                    Err(e) => {
                        eprintln!("启动 Python 内核失败: {}", e);
                        let _ = app_handle.emit("python-kernel-error", format!("启动失败: {}", e));
                    }
                }
            });

            // 初始化 Modbus 服务：HR 写入通过 channel 发出事件；若设备开启远程控制则经 Modbus 过滤后推送到 Python 内核
            let (modbus_hr_tx, mut modbus_hr_rx) = mpsc::channel::<services::modbus::HoldingRegisterWriteEvent>(64);
            let modbus_service = ModbusService::new(modbus_hr_tx);
            let app_handle_modbus = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some((device_id, address, value)) = modbus_hr_rx.recv().await {
                    // Modbus 过滤：四条指令独立（开关机/功率百分比限制/功率限制/功率设定），冲突只响应最新一条；若设备允许远程控制则推送到 Python
                    if let (Some(engine), Some(modbus)) = (
                        app_handle_modbus.try_state::<Arc<SimulationEngine>>(),
                        app_handle_modbus.try_state::<ModbusService>(),
                    ) {
                        let engine = engine.inner().clone();
                        let device_type: Option<String> = engine
                            .get_topology()
                            .await
                            .and_then(|t| t.devices.get(&device_id).map(|d| d.device_type.as_str().to_string()));
                        if let Some(ref dt) = device_type {
                            if let Some(props) = modbus.apply_hr_write_and_effective_properties(&device_id, dt, address, value) {
                                let _ = engine.update_device_properties_for_simulation(device_id.clone(), props).await;
                            }
                        }
                    }
                    let _ = app_handle_modbus.emit("modbus-holding-register-write", serde_json::json!({
                        "device_id": device_id,
                        "address": address,
                        "value": value,
                    }));
                }
            });
            // SSH 客户端（数据看板远程数据源）
            let ssh_client = Arc::new(TokioMutex::new(SshClient::new()));

            // 将服务存储到应用状态
            app.manage(python_bridge_arc);
            app.manage(db_arc);
            app.manage(current_db_path);
            app.manage(StdMutex::new(metadata_store));
            app.manage(simulation_engine);
            app.manage(modbus_service);
            app.manage(ssh_client);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::topology::save_topology,
            commands::topology::save_topology_legacy,
            commands::topology::load_topology,
            commands::topology::validate_topology,
            commands::topology::load_and_validate_topology,
            commands::simulation::start_simulation,
            commands::simulation::stop_simulation,
            commands::simulation::pause_simulation,
            commands::simulation::resume_simulation,
            commands::simulation::get_simulation_status,
            commands::simulation::get_simulation_errors,
            commands::simulation::set_remote_control_enabled,
            commands::simulation::set_device_remote_control_enabled,
            commands::simulation::update_device_properties_for_simulation,
            commands::simulation::set_device_mode,
            commands::simulation::set_device_random_config,
            commands::simulation::set_device_manual_setpoint,
            commands::simulation::set_device_historical_config,
            commands::simulation::get_device_data,
            commands::monitoring::record_device_data,
            commands::monitoring::get_latest_simulation_start_time,
            commands::monitoring::get_app_database_path,
            commands::monitoring::get_dashboard_device_ids,
            commands::monitoring::query_device_data,
            commands::monitoring::get_all_devices_status,
            commands::monitoring::get_device_status,
            commands::device::get_all_devices,
            commands::device::get_modbus_devices,
            commands::device::get_modbus_register_defaults,
            commands::device::get_device,
            commands::modbus::start_device_modbus,
            commands::modbus::stop_device_modbus,
            commands::modbus::start_all_modbus_servers,
            commands::modbus::get_running_modbus_device_ids,
            commands::device::update_device_config,
            commands::device::update_device_metadata,
            commands::device::batch_set_device_mode,
            commands::ai::predict_device_data,
            commands::ai::optimize_operation,
            commands::ai::get_ai_recommendations,
            commands::analytics::analyze_performance,
            commands::analytics::generate_report,
            commands::ssh::ssh_connect,
            commands::ssh::ssh_disconnect,
            commands::ssh::ssh_is_connected,
            commands::ssh::ssh_query_remote_device_data,
            commands::dashboard::dashboard_parse_csv,
            commands::dashboard::dashboard_list_devices_from_path,
            commands::dashboard::query_device_data_from_path,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
