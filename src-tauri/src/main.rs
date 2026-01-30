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
use domain::metadata::DeviceMetadataStore;
use std::sync::{Arc, Mutex as StdMutex};
use tokio::sync::Mutex as TokioMutex;

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

            // 初始化数据库
            let db = Database::new(None).unwrap_or_else(|e| {
                eprintln!("Failed to initialize database: {}", e);
                panic!("Database initialization failed");
            });

            // 初始化设备元数据仓库
            let metadata_store = DeviceMetadataStore::new();

            // 初始化仿真引擎
            let db_arc = Arc::new(StdMutex::new(db));
            let simulation_engine = Arc::new(SimulationEngine::new(python_bridge_arc.clone(), db_arc.clone()));
            
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

            // 初始化 Modbus 服务
            let modbus_service = ModbusService::new();

            // 将服务存储到应用状态
            app.manage(python_bridge_arc);
            app.manage(db_arc);
            app.manage(StdMutex::new(metadata_store));
            app.manage(simulation_engine);
            app.manage(modbus_service);

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
            commands::simulation::get_device_data,
            commands::monitoring::record_device_data,
            commands::monitoring::query_device_data,
            commands::monitoring::get_all_devices_status,
            commands::monitoring::get_device_status,
            commands::device::get_all_devices,
            commands::device::get_device,
            commands::device::update_device_config,
            commands::device::batch_set_device_mode,
            commands::ai::predict_device_data,
            commands::ai::optimize_operation,
            commands::ai::get_ai_recommendations,
            commands::analytics::analyze_performance,
            commands::analytics::generate_report,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
