// Python 通信桥接
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tauri::path::BaseDirectory;
use tauri::Manager;
use tokio::sync::{Mutex, oneshot};
use tokio::process::{Command, ChildStdin};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::time::{timeout, Duration};

#[derive(Debug, Serialize, Deserialize)]
struct JsonRpcRequest {
    jsonrpc: String,
    id: u64,
    method: String,
    params: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
struct JsonRpcResponse {
    jsonrpc: String,
    id: Option<u64>,
    result: Option<serde_json::Value>,
    error: Option<JsonRpcError>,
}

#[derive(Debug, Serialize, Deserialize)]
struct JsonRpcError {
    code: i32,
    message: String,
}

pub struct PythonBridge {
    stdin: Option<Arc<Mutex<ChildStdin>>>,
    request_id: Arc<std::sync::atomic::AtomicU64>,
    pending_requests: Arc<Mutex<HashMap<u64, oneshot::Sender<Result<serde_json::Value>>>>>,
    process_handle: Option<tokio::task::JoinHandle<()>>,
}

impl PythonBridge {
    pub fn new() -> Self {
        Self {
            stdin: None,
            request_id: Arc::new(std::sync::atomic::AtomicU64::new(0)),
            pending_requests: Arc::new(Mutex::new(HashMap::new())),
            process_handle: None,
        }
    }

    pub async fn start(&mut self, app_handle: Option<&tauri::AppHandle>) -> Result<()> {
        // 优先尝试使用打包后的可执行文件
        let (executable_path, args) = if cfg!(not(debug_assertions)) {
            // 发布模式：优先从 bundle resources 加载，其次从文件系统查找
            let kernel_name = if cfg!(target_os = "windows") {
                "python-kernel/python-kernel.exe"
            } else {
                "python-kernel/python-kernel"
            };
            let resource_path: Option<std::path::PathBuf> = app_handle.and_then(|h| {
                h.path()
                    .resolve(kernel_name, BaseDirectory::Resource)
                    .ok()
                    .filter(|p: &PathBuf| p.exists())
            });
            if let Some(path) = resource_path {
                eprintln!("使用资源目录中的 Python 内核: {}", path.display());
                (path.to_string_lossy().to_string(), Vec::<String>::new())
            } else {
                match Self::find_packed_executable().await {
                    Ok(path) => {
                        eprintln!("使用打包后的Python内核: {}", path);
                        (path, Vec::<String>::new())
                    }
                    Err(e) => {
                        eprintln!("未找到打包后的可执行文件: {}, 回退到Python脚本", e);
                        let python_path = Self::find_python().await?;
                        let script_path = Self::get_python_script_path()?;
                        (python_path, vec![script_path])
                    }
                }
            }
        } else {
            // 开发模式：使用Python脚本
            let python_path = Self::find_python().await?;
            let script_path = Self::get_python_script_path()?;
            (python_path, vec![script_path])
        };
        let mut cmd = Command::new(&executable_path);
        for arg in args {
            cmd.arg(arg);
        }
        
        let mut child = cmd
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .context(format!("Failed to start Python process: {}", executable_path))?;

        let stdout = child.stdout.take()
            .ok_or_else(|| anyhow::anyhow!("Failed to get stdout"))?;
        let stdin = child.stdin.take()
            .ok_or_else(|| anyhow::anyhow!("Failed to get stdin"))?;
        let stderr = child.stderr.take()
            .ok_or_else(|| anyhow::anyhow!("Failed to get stderr"))?;

        let stdin_arc = Arc::new(Mutex::new(stdin));
        self.stdin = Some(stdin_arc.clone());

        // 启动后台任务读取 stderr 并记录日志
        tokio::spawn(async move {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();
            
            // 尝试写入日志文件
            let log_path = std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|p| p.join("python-kernel.log")))
                .unwrap_or_else(|| std::path::PathBuf::from("python-kernel.log"));
            
            let mut log_file = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&log_path)
                .ok();
            
            if let Some(ref mut f) = log_file {
                use std::io::Write;
                let _ = writeln!(f, "\n=== Python Kernel Started at {:?} ===", std::time::SystemTime::now());
            }
            
            while let Ok(Some(line)) = lines.next_line().await {
                eprintln!("[Python stderr] {}", line);
                if let Some(ref mut f) = log_file {
                    use std::io::Write;
                    let _ = writeln!(f, "{}", line);
                    let _ = f.flush();
                }
            }
        });

        // 启动后台任务读取 stdout
        let pending = self.pending_requests.clone();
        
        let handle = tokio::spawn(async move {
            let reader = BufReader::new(stdout);
            let mut lines = reader.lines();
            
            while let Ok(Some(line)) = lines.next_line().await {
                if line.trim().is_empty() {
                    continue;
                }
                
                // 解析 JSON-RPC 响应
                match serde_json::from_str::<JsonRpcResponse>(&line) {
                    Ok(response) => {
                        if let Some(id) = response.id {
                            let mut pending = pending.lock().await;
                            if let Some(sender) = pending.remove(&id) {
                                if let Some(error) = response.error {
                                    let _ = sender.send(Err(anyhow::anyhow!(
                                        "JSON-RPC error {}: {}", error.code, error.message
                                    )));
                                } else if let Some(result) = response.result {
                                    let _ = sender.send(Ok(result));
                                } else {
                                    let _ = sender.send(Err(anyhow::anyhow!("Empty response")));
                                }
                            }
                        }
                    }
                    Err(e) => {
                        eprintln!("Failed to parse JSON-RPC response: {} - {}", e, line);
                    }
                }
            }
        });

        self.process_handle = Some(handle);
        self.request_id.store(0, std::sync::atomic::Ordering::Relaxed);

        Ok(())
    }

    pub async fn stop(&mut self) -> Result<()> {
        if let Some(handle) = self.process_handle.take() {
            handle.abort();
        }
        self.stdin = None;
        Ok(())
    }

    pub async fn call(&mut self, method: &str, params: serde_json::Value) -> Result<serde_json::Value> {
        let request_id = self.request_id.fetch_add(1, std::sync::atomic::Ordering::Relaxed);

        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: request_id,
            method: method.to_string(),
            params,
        };

        let request_json = serde_json::to_string(&request)?;
        
        // 创建响应通道
        let (tx, rx) = oneshot::channel();
        {
            let mut pending = self.pending_requests.lock().await;
            pending.insert(request_id, tx);
        }

        // 发送请求
        if let Some(ref stdin) = self.stdin {
            let mut stdin = stdin.lock().await;

            stdin.write_all(request_json.as_bytes()).await?;
            stdin.write_all(b"\n").await?;
            stdin.flush().await?;
        } else {
            return Err(anyhow::anyhow!("Python process not started"));
        }

        // 等待响应（带超时）
        let timeout_duration = if method == "simulation.set_topology" {
            Duration::from_secs(60)  // 设置拓扑可能需要更长时间（首次加载库）
        } else {
            Duration::from_secs(10)  // 普通操作 10 秒超时
        };
        
        match timeout(timeout_duration, rx).await {
            Ok(Ok(result)) => result,
            Ok(Err(_)) => Err(anyhow::anyhow!("Response channel closed")),
            Err(_) => {
                // 超时，移除 pending 请求
                let mut pending = self.pending_requests.lock().await;
                pending.remove(&request_id);
                Err(anyhow::anyhow!("Request timeout after {} seconds", timeout_duration.as_secs()))
            }
        }
    }

    async fn find_python() -> Result<String> {
        // 1. 若已设置 VIRTUAL_ENV，优先使用该虚拟环境中的 Python
        if let Ok(venv) = std::env::var("VIRTUAL_ENV") {
            let venv_path = Path::new(&venv);
            let python = if cfg!(target_os = "windows") {
                venv_path.join("Scripts").join("python.exe")
            } else {
                venv_path.join("bin").join("python")
            };
            if python.exists() {
                if let Ok(out) = Command::new(&python).arg("--version").output().await {
                    if out.status.success() {
                        eprintln!("使用虚拟环境 Python: {}", python.display());
                        return Ok(python.to_string_lossy().to_string());
                    }
                }
            }
        }
        // 2. 在项目根下查找虚拟环境（venv-dev / .venv / venv），与 setup_venv.py / activate-dev 一致
        let project_roots: Vec<PathBuf> = {
            let current_dir = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
            let mut roots = vec![current_dir.clone()];
            if let Some(parent) = current_dir.parent() {
                roots.push(parent.to_path_buf());
            }
            roots
        };
        let venv_names = ["venv-dev", ".venv", "venv"];
        for root in &project_roots {
            for name in venv_names {
                let python = if cfg!(target_os = "windows") {
                    root.join(name).join("Scripts").join("python.exe")
                } else {
                    root.join(name).join("bin").join("python")
                };
                if python.exists() {
                    if let Ok(out) = Command::new(&python).arg("--version").output().await {
                        if out.status.success() {
                            eprintln!("使用项目虚拟环境 Python: {}", python.display());
                            return Ok(python.to_string_lossy().to_string());
                        }
                    }
                }
            }
        }
        // 3. 回退到 PATH 中的 python3 / python
        let candidates = ["python3", "python"];
        for cmd in candidates {
            if let Ok(out) = Command::new(cmd).arg("--version").output().await {
                if out.status.success() {
                    return Ok(cmd.to_string());
                }
            }
        }
        Err(anyhow::anyhow!("Python not found. 建议在项目根执行 python setup_venv.py 创建 venv-dev 并安装依赖"))
    }

    fn get_python_script_path() -> Result<String> {
        // 获取 Python 内核脚本路径（兼容 src-tauri 作为当前工作目录的情况）
        let current_dir = std::env::current_dir()?;

        let mut candidates: Vec<std::path::PathBuf> = Vec::new();
        // 1. 当前目录下的 python-kernel/main.py
        candidates.push(current_dir.join("python-kernel").join("main.py"));
        // 2. 父目录下的 python-kernel/main.py（开发时常见：项目根有 python-kernel，当前在 src-tauri）
        if let Some(parent) = current_dir.parent() {
            candidates.push(parent.join("python-kernel").join("main.py"));
        }

        for path in &candidates {
            if path.exists() {
                return Ok(path.to_string_lossy().to_string());
            }
        }

        Err(anyhow::anyhow!(format!(
            "Python kernel script not found. Tried paths: {:?}",
            candidates
        )))
    }

    async fn find_packed_executable() -> Result<String> {
        // 查找打包后的Python内核可执行文件
        // 优先级：
        // 1. 环境变量 PYTHON_KERNEL_PATH
        // 2. 与可执行文件同目录下的 python-kernel/python-kernel(.exe)
        // 3. 当前目录下的 dist/python-kernel/python-kernel(.exe)
        // 4. src-tauri/target/release 或 debug 目录
        
        // 检查环境变量
        if let Ok(env_path) = std::env::var("PYTHON_KERNEL_PATH") {
            let path = std::path::Path::new(&env_path);
            if path.exists() {
                return Ok(env_path);
            }
        }
        
        // 获取可执行文件所在目录
        if let Ok(exe_path) = std::env::current_exe() {
            if let Some(exe_dir) = exe_path.parent() {
                // 检查同目录下的 python-kernel 子目录
                let kernel_path = exe_dir.join("python-kernel").join(
                    if cfg!(target_os = "windows") { "python-kernel.exe" } else { "python-kernel" }
                );
                if kernel_path.exists() {
                    return Ok(kernel_path.to_string_lossy().to_string());
                }
            }
        }
        
        // 检查当前目录下的 dist/python-kernel
        let current_dir = std::env::current_dir()?;
        let dist_path = current_dir.join("dist").join("python-kernel").join(
            if cfg!(target_os = "windows") { "python-kernel.exe" } else { "python-kernel" }
        );
        if dist_path.exists() {
            return Ok(dist_path.to_string_lossy().to_string());
        }
        
        // 检查 src-tauri/target/release 或 debug 目录
        let target_dir = if cfg!(debug_assertions) {
            current_dir.join("src-tauri").join("target").join("debug")
        } else {
            current_dir.join("src-tauri").join("target").join("release")
        };
        
        let target_kernel_path = target_dir.join("python-kernel").join(
            if cfg!(target_os = "windows") { "python-kernel.exe" } else { "python-kernel" }
        );
        if target_kernel_path.exists() {
            return Ok(target_kernel_path.to_string_lossy().to_string());
        }
        
        Err(anyhow::anyhow!("Python kernel executable not found"))
    }
}

impl Drop for PythonBridge {
    fn drop(&mut self) {
        // 注意：在 Drop 中不能使用 async，所以这里只是清理资源
        // 实际的停止操作应该在外部显式调用 stop()
    }
}
