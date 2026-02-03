// SSH 客户端（远程数据库访问）
// 远程查询采用「先导出到远程临时文件，再通过 SFTP 下载到本地临时文件」避免 stdout 长度限制（参考 remote-tool）
use async_ssh2_tokio::client::{Client, AuthMethod, ServerCheckMethod};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use anyhow::{Result, Context};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SshConfig {
    pub host: String,
    pub port: u16,
    pub user: String,
    pub auth_method: AuthMethodConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum AuthMethodConfig {
    Password(String),
    KeyFile { path: String, passphrase: Option<String> },
}

pub struct SshClient {
    client: Option<Client>,
    config: Option<SshConfig>,
}

impl SshClient {
    pub fn new() -> Self {
        Self {
            client: None,
            config: None,
        }
    }

    pub async fn connect(&mut self, config: SshConfig) -> Result<()> {
        let addr: SocketAddr = format!("{}:{}", config.host, config.port)
            .parse()
            .context("Invalid host:port format")?;
        
        let auth_method = match &config.auth_method {
            AuthMethodConfig::Password(pwd) => AuthMethod::Password(pwd.clone()),
            AuthMethodConfig::KeyFile { path, passphrase } => {
                let key_content = std::fs::read_to_string(path)
                    .context("Failed to read key file")?;
                AuthMethod::PrivateKey {
                    key_data: key_content,
                    key_pass: passphrase.clone(),
                }
            }
        };

        let client = Client::connect(
            addr,
            &config.user,
            auth_method,
            ServerCheckMethod::NoCheck,
        )
        .await
        .context("Failed to connect to SSH server")?;

        self.client = Some(client);
        self.config = Some(config);
        Ok(())
    }

    pub async fn execute_command(&mut self, command: &str) -> Result<String> {
        let client = self.client.as_mut()
            .ok_or_else(|| anyhow::anyhow!("SSH client not connected"))?;
        
        let result = client.execute(command).await
            .context("Failed to execute command")?;
        
        if result.exit_status != 0 {
            return Err(anyhow::anyhow!("Command failed: {}", result.stderr));
        }
        
        Ok(result.stdout)
    }

    /// 远程执行 SQL 查询，结果先写入远程临时文件再通过 SFTP 下载到本地临时文件并读入，
    /// 避免 stdout 长度限制（参考 https://github.com/huluzhou/remote-tool）。
    /// 远程与本地临时文件在成功后均会清理。
    pub async fn query_remote_database(
        &mut self,
        db_path: &str,
        query: &str,
    ) -> Result<String> {
        let suffix: u64 = rand::random();
        let remote_tmp = format!("/tmp/dashboard_query_{}.csv", suffix);
        let local_tmp = std::env::temp_dir().join(format!("dashboard_query_{}.csv", suffix));

        // 1. 远程：sqlite3 查询结果写入临时文件（避免 stdout 限制，服务器端增量写盘）
        let write_cmd = format!(
            "sqlite3 -csv {} \"{}\" > {}",
            db_path,
            query.replace("\"", "\\\""),
            remote_tmp
        );
        self.execute_command(&write_cmd).await?;

        // 2. SFTP 下载到本地临时文件（库内部整文件缓冲；超大结果集时可考虑流式读取的 SFTP 实现）
        {
            let client = self
                .client
                .as_ref()
                .ok_or_else(|| anyhow::anyhow!("SSH client not connected"))?;
            client
                .download_file(remote_tmp.clone(), local_tmp.as_path())
                .await
                .map_err(|e| anyhow::anyhow!("Failed to download remote CSV via SFTP: {}", e))?;
        }

        // 3. 删除远程临时文件
        let _ = self.execute_command(&format!("rm -f {}", remote_tmp)).await;

        // 4. 读取本地文件并删除本地临时文件
        let content = tokio::fs::read_to_string(&local_tmp)
            .await
            .context("Failed to read downloaded CSV")?;
        let _ = std::fs::remove_file(&local_tmp);

        Ok(content)
    }

    pub fn is_connected(&self) -> bool {
        self.client.is_some()
    }

    pub fn disconnect(&mut self) {
        self.client = None;
        self.config = None;
    }
}

impl Default for SshClient {
    fn default() -> Self {
        Self::new()
    }
}
