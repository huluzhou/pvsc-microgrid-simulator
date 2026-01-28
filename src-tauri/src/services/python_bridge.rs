// Python 通信桥接
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};
use std::collections::HashMap;
use std::sync::Arc;
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

    pub async fn start(&mut self) -> Result<()> {
        // 优先尝试使用打包后的可执行文件
        let (executable_path, args) = if cfg!(not(debug_assertions)) {
            // 发布模式：使用打包后的可执行文件
            match Self::find_packed_executable().await {
                Ok(path) => {
                    eprintln!("使用打包后的Python内核: {}", path);
                    (path, Vec::<String>::new())
                }
                Err(e) => {
                    eprintln!("未找到打包后的可执行文件: {}, 回退到Python脚本", e);
                    // 回退到Python脚本模式
                    let python_path = Self::find_python().await?;
                    let script_path = Self::get_python_script_path()?;
                    (python_path, vec![script_path])
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

        let stdin_arc = Arc::new(Mutex::new(stdin));
        self.stdin = Some(stdin_arc.clone());

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
        match timeout(Duration::from_secs(30), rx).await {
            Ok(Ok(result)) => result,
            Ok(Err(_)) => Err(anyhow::anyhow!("Response channel closed")),
            Err(_) => {
                // 超时，移除 pending 请求
                let mut pending = self.pending_requests.lock().await;
                pending.remove(&request_id);
                Err(anyhow::anyhow!("Request timeout"))
            }
        }
    }

    async fn find_python() -> Result<String> {
        // 尝试查找 Python 3
        let candidates = ["python3", "python"];
        for cmd in candidates {
            let output = Command::new(cmd)
                .arg("--version")
                .output()
                .await;
            
            if output.is_ok() {
                return Ok(cmd.to_string());
            }
        }
        Err(anyhow::anyhow!("Python not found"))
    }

    fn get_python_script_path() -> Result<String> {
        // 获取 Python 内核脚本路径
        let current_dir = std::env::current_dir()?;
        let script_path = current_dir.join("python-kernel").join("main.py");
        Ok(script_path.to_string_lossy().to_string())
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
