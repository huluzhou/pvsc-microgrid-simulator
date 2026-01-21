// Python 通信桥接
use std::process::{Command, Stdio};
use std::io::Write;
use serde::{Deserialize, Serialize};
use anyhow::{Result, Context};

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
    process: Option<std::process::Child>,
    request_id: std::sync::atomic::AtomicU64,
}

impl PythonBridge {
    pub fn new() -> Self {
        Self {
            process: None,
            request_id: std::sync::atomic::AtomicU64::new(0),
        }
    }

    pub fn start(&mut self) -> Result<()> {
        let python_path = Self::find_python()?;
        let script_path = Self::get_python_script_path()?;

        let child = Command::new(python_path)
            .arg(script_path)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .context("Failed to start Python process")?;

        self.process = Some(child);
        self.request_id.store(0, std::sync::atomic::Ordering::Relaxed);

        Ok(())
    }

    pub fn stop(&mut self) -> Result<()> {
        if let Some(mut process) = self.process.take() {
            process.kill()?;
            process.wait()?;
        }
        Ok(())
    }

    pub fn call(&mut self, method: &str, params: serde_json::Value) -> Result<serde_json::Value> {
        let request_id = self.request_id.fetch_add(1, std::sync::atomic::Ordering::Relaxed);

        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: request_id,
            method: method.to_string(),
            params,
        };

        let request_json = serde_json::to_string(&request)?;
        
        if let Some(ref mut process) = self.process {
            if let Some(ref mut stdin) = process.stdin {
                writeln!(stdin, "{}", request_json)?;
                stdin.flush()?;
            }

            // 注意：这是一个简化的实现，实际应该使用异步或线程来处理响应
            // 这里先返回一个占位符，后续阶段会完善
            return Ok(serde_json::json!({"status": "ok"}));
        }

        Err(anyhow::anyhow!("Python process not started"))
    }

    fn find_python() -> Result<String> {
        // 尝试查找 Python 3
        let candidates = ["python3", "python"];
        for cmd in candidates {
            if Command::new(cmd)
                .arg("--version")
                .output()
                .is_ok()
            {
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
}

impl Drop for PythonBridge {
    fn drop(&mut self) {
        let _ = self.stop();
    }
}
