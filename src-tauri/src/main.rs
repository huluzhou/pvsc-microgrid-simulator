// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod domain;
mod services;
mod utils;

use tauri::Manager;
use services::python_bridge::PythonBridge;
use services::database::Database;
use services::simulation_engine::SimulationEngine;
use domain::metadata::DeviceMetadataStore;
use std::sync::Arc;
use tokio::sync::Mutex;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // 初始化应用设置
            #[cfg(debug_assertions)]
            {
                let window = app.get_webview_window("main").unwrap();
                window.open_devtools();
            }

            // 初始化 Python 桥接（异步）
            let mut python_bridge = PythonBridge::new();
            let rt = tokio::runtime::Runtime::new().unwrap();
            if let Err(e) = rt.block_on(python_bridge.start()) {
                eprintln!("Failed to start Python bridge: {}", e);
            }

            // 初始化数据库
            let db = Database::new(None).unwrap_or_else(|e| {
                eprintln!("Failed to initialize database: {}", e);
                panic!("Database initialization failed");
            });

            // 初始化设备元数据仓库
            let metadata_store = DeviceMetadataStore::new();

            // 初始化仿真引擎
            let python_bridge_arc = Arc::new(Mutex::new(python_bridge));
            let simulation_engine = Arc::new(SimulationEngine::new(python_bridge_arc.clone()));

            // 将服务存储到应用状态
            app.manage(python_bridge_arc);
            app.manage(Mutex::new(db));
            app.manage(Mutex::new(metadata_store));
            app.manage(simulation_engine);

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::topology::save_topology,
            commands::topology::load_topology,
            commands::topology::validate_topology,
            commands::simulation::start_simulation,
            commands::simulation::stop_simulation,
            commands::simulation::pause_simulation,
            commands::simulation::resume_simulation,
            commands::simulation::get_simulation_status,
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
