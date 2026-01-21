// SSH 客户端（远程数据库访问）
use async_ssh2_tokio::client::{Client, AuthMethod, ServerCheckMethod};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use anyhow::{Result, Context};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SshConfig {
    pub host: String,
    pub port: u16,
    pub user: String,
    pub auth_method: AuthMethodConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
                AuthMethod::Pubkey {
                    key: key_content,
                    passphrase: passphrase.clone(),
                }
            }
        };

        let client = Client::connect(
            addr,
            config.user.clone(),
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

    pub async fn query_remote_database(
        &mut self,
        db_path: &str,
        query: &str,
    ) -> Result<String> {
        // 通过 SSH 执行 SQLite 查询
        // 使用 sqlite3 命令行工具执行查询并输出 CSV 格式
        let command = format!(
            "sqlite3 -csv {} \"{}\"",
            db_path,
            query.replace("\"", "\\\"")
        );
        
        self.execute_command(&command).await
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
