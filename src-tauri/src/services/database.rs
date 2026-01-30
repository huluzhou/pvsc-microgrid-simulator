// 数据库访问
use rusqlite::{Connection, Result as SqlResult};
use anyhow::{Result, Context};

pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn new(db_path: Option<&std::path::Path>) -> Result<Self> {
        let path = db_path.map(|p| p.to_path_buf()).unwrap_or_else(|| {
            let mut path = std::env::current_dir().unwrap();
            path.push("data.db");
            path
        });

        let conn = Connection::open(&path)
            .context(format!("Failed to open database at {:?}", path))?;

        let db = Self { conn };
        db.init_schema()?;
        Ok(db)
    }

    fn init_schema(&self) -> SqlResult<()> {
        // 创建设备数据表
        // 当前只关注有功功率和无功功率，其他字段后续再加
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS device_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                p_active REAL,
                p_reactive REAL,
                data_json TEXT
            )",
            [],
        )?;

        // 创建索引
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_device_timestamp ON device_data(device_id, timestamp)",
            [],
        )?;

        // 仿真元数据（如最近一次仿真起始时间，供趋势图从 DB 获取起点）
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS simulation_meta (
                key TEXT PRIMARY KEY,
                value_real REAL
            )",
            [],
        )?;

        Ok(())
    }

    /// 持久化最近一次仿真起始时间（Unix 秒），供监控趋势图从 DB 获取起点
    pub fn set_latest_simulation_start(&self, timestamp: f64) -> SqlResult<()> {
        self.conn.execute(
            "INSERT OR REPLACE INTO simulation_meta (key, value_real) VALUES ('latest_simulation_start', ?1)",
            rusqlite::params![timestamp],
        )?;
        Ok(())
    }

    /// 获取最近一次仿真起始时间（Unix 秒）
    pub fn get_latest_simulation_start(&self) -> SqlResult<Option<f64>> {
        let mut stmt = self.conn.prepare(
            "SELECT value_real FROM simulation_meta WHERE key = 'latest_simulation_start'",
        )?;
        let mut rows = stmt.query([])?;
        if let Some(row) = rows.next()? {
            return Ok(row.get(0)?);
        }
        Ok(None)
    }

    pub fn insert_device_data(
        &self,
        device_id: &str,
        timestamp: f64,
        p_active: Option<f64>,
        p_reactive: Option<f64>,
        data_json: Option<&str>,
    ) -> SqlResult<()> {
        self.conn.execute(
            "INSERT INTO device_data (device_id, timestamp, p_active, p_reactive, data_json)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            rusqlite::params![device_id, timestamp, p_active, p_reactive, data_json],
        )?;
        Ok(())
    }

    /// 单行结果：timestamp, p_active, p_reactive, data_json。max_points 为 Some(n) 时若结果超过 n 条则按时间等分桶降采样
    pub fn query_device_data(
        &self,
        device_id: &str,
        start_time: Option<f64>,
        end_time: Option<f64>,
        max_points: Option<usize>,
    ) -> SqlResult<Vec<(f64, Option<f64>, Option<f64>, Option<String>)>> {
        let mut query = "SELECT timestamp, p_active, p_reactive, data_json FROM device_data WHERE device_id = ?1".to_string();
        let mut params: Vec<Box<dyn rusqlite::ToSql>> = vec![Box::new(device_id)];

        if let Some(start) = start_time {
            query.push_str(" AND timestamp >= ?2");
            params.push(Box::new(start));
        }
        if let Some(end) = end_time {
            query.push_str(if start_time.is_some() { " AND timestamp <= ?3" } else { " AND timestamp <= ?2" });
            params.push(Box::new(end));
        }

        query.push_str(" ORDER BY timestamp");

        let mut stmt = self.conn.prepare(&query)?;
        let rows = stmt.query_map(
            rusqlite::params_from_iter(params.iter().map(|p| p.as_ref())),
            |row| {
                Ok((
                    row.get(0)?,
                    row.get(1)?,
                    row.get(2)?,
                    row.get(3)?,
                ))
            },
        )?;

        let mut results = Vec::new();
        for row in rows {
            results.push(row?);
        }

        if let Some(n) = max_points {
            if results.len() > n && n > 0 {
                let start_ts: f64 = results.first().map(|r| r.0).unwrap_or(0.0_f64);
                let end_ts: f64 = results.last().map(|r| r.0).unwrap_or(0.0_f64);
                let span = (end_ts - start_ts).max(1e-9_f64);
                let bucket_size = span / (n as f64);
                let mut buckets: std::collections::HashMap<usize, Vec<(f64, Option<f64>, Option<f64>, Option<String>)>> =
                    std::collections::HashMap::new();
                for r in results {
                    let x: f64 = (r.0 - start_ts) / bucket_size;
                    let idx = x.floor().min((n - 1) as f64) as usize;
                    buckets.entry(idx).or_default().push(r);
                }
                results = (0..n)
                    .filter_map(|i| {
                        buckets.get(&i).and_then(|v| {
                            if v.is_empty() {
                                None
                            } else {
                                let len = v.len() as f64;
                                let ts = v.iter().map(|r| r.0).sum::<f64>() / len;
                                let p_a = v.iter().filter_map(|r| r.1).reduce(|a, b| a + b).map(|s| s / len);
                                let p_r = v.iter().filter_map(|r| r.2).reduce(|a, b| a + b).map(|s| s / len);
                                let json = v.first().and_then(|r| r.3.clone());
                                Some((ts, p_a, p_r, json))
                            }
                        })
                    })
                    .collect();
            }
        }

        Ok(results)
    }

    /// 返回该设备最新一行（含 data_json），用于状态展示，避免全表扫描
    pub fn query_device_data_latest(
        &self,
        device_id: &str,
    ) -> SqlResult<Option<(f64, Option<f64>, Option<f64>, Option<String>)>> {
        let mut stmt = self.conn.prepare(
            "SELECT timestamp, p_active, p_reactive, data_json FROM device_data WHERE device_id = ?1 ORDER BY timestamp DESC LIMIT 1",
        )?;
        let mut rows = stmt.query(rusqlite::params![device_id])?;
        if let Some(row) = rows.next()? {
            let r = (
                row.get(0)?,
                row.get(1)?,
                row.get(2)?,
                row.get(3)?,
            );
            Ok(Some(r))
        } else {
            Ok(None)
        }
    }
}
