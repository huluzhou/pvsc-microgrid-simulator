// 数据库访问
use rusqlite::{Connection, Result as SqlResult};
use anyhow::{Result, Context};

pub struct Database {
    conn: Connection,
}

impl Database {
    /// 默认数据库路径：使用 current_dir()/data.db。开发时 cwd 为 src-tauri，故为 src-tauri/data.db（仿真写入此处）。
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
        // 检查是否存在旧版本的 device_data 表（使用 voltage, current, power 列）
        let old_table_exists = self.conn.query_row(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='device_data'",
            [],
            |row| row.get::<_, i32>(0)
        )? > 0;

        if old_table_exists {
            // 检查是否有旧列名（voltage, current, power）
            let has_old_columns = self.conn.query_row(
                "SELECT COUNT(*) FROM pragma_table_info('device_data') WHERE name IN ('voltage', 'current', 'power')",
                [],
                |row| row.get::<_, i32>(0)
            ).unwrap_or(0) > 0;

            if has_old_columns {
                // 检测到旧表结构，输出警告并删除重建
                eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                eprintln!("⚠️  DATABASE SCHEMA MISMATCH DETECTED");
                eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                eprintln!("   Old table structure detected with columns:");
                eprintln!("   - voltage, current, power (old schema)");
                eprintln!("");
                eprintln!("   Expected columns:");
                eprintln!("   - p_mw, q_mvar (pandapower standard schema)");
                eprintln!("");
                eprintln!("   Action: Dropping old table and recreating with new schema.");
                eprintln!("   Note: All existing data will be lost (test data).");
                eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                
                // 删除旧表
                self.conn.execute("DROP TABLE device_data", [])?;
                eprintln!("✓ Old table dropped successfully");
            } else {
                // 检查是否有旧列名（p_active, p_reactive），需要迁移到 p_mw, q_mvar
                let has_old_power_columns = self.conn.query_row(
                    "SELECT COUNT(*) FROM pragma_table_info('device_data') WHERE name IN ('p_active', 'p_reactive')",
                    [],
                    |row| row.get::<_, i32>(0)
                ).unwrap_or(0) > 0;
                
                if has_old_power_columns {
                    eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                    eprintln!("⚠️  DATABASE SCHEMA MIGRATION");
                    eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                    eprintln!("   Migrating from p_active/p_reactive (kW) to p_mw/q_mvar (MW)");
                    eprintln!("   Converting values: MW = kW / 1000.0");
                    eprintln!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
                    
                    // 添加新列
                    let _ = self.conn.execute("ALTER TABLE device_data ADD COLUMN p_mw REAL", []);
                    let _ = self.conn.execute("ALTER TABLE device_data ADD COLUMN q_mvar REAL", []);
                    
                    // 迁移数据：将 kW 转换为 MW
                    self.conn.execute(
                        "UPDATE device_data SET p_mw = p_active / 1000.0 WHERE p_active IS NOT NULL",
                        [],
                    )?;
                    self.conn.execute(
                        "UPDATE device_data SET q_mvar = p_reactive / 1000.0 WHERE p_reactive IS NOT NULL",
                        [],
                    )?;
                    
                    // 删除旧列（SQLite 不支持直接删除列，需要重建表）
                    // 创建临时表
                    self.conn.execute(
                        "CREATE TABLE device_data_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            device_id TEXT NOT NULL,
                            timestamp REAL NOT NULL,
                            p_mw REAL,
                            q_mvar REAL,
                            data_json TEXT,
                            device_type TEXT
                        )",
                        [],
                    )?;
                    
                    // 复制数据
                    self.conn.execute(
                        "INSERT INTO device_data_new (id, device_id, timestamp, p_mw, q_mvar, data_json, device_type)
                         SELECT id, device_id, timestamp, p_mw, q_mvar, data_json, device_type FROM device_data",
                        [],
                    )?;
                    
                    // 删除旧表并重命名
                    self.conn.execute("DROP TABLE device_data", [])?;
                    self.conn.execute("ALTER TABLE device_data_new RENAME TO device_data", [])?;
                    
                    eprintln!("✓ Migration completed successfully");
                }
            }
        }

        // 创建设备数据表（使用 pandapower 标准字段名：p_mw, q_mvar）
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS device_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                p_mw REAL,
                q_mvar REAL,
                data_json TEXT,
                device_type TEXT
            )",
            [],
        )?;

        // 为已有表补充 device_type 列（忽略已存在）
        let _ = self.conn.execute("ALTER TABLE device_data ADD COLUMN device_type TEXT", []);

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

    /// 仿真开始时清空设备数据表，避免拓扑变更后旧设备数据残留；每次启动仿真视为新一轮数据。
    pub fn clear_device_data(&self) -> SqlResult<()> {
        self.conn.execute("DELETE FROM device_data", [])?;
        Ok(())
    }

    pub fn insert_device_data(
        &self,
        device_id: &str,
        timestamp: f64,
        p_mw: Option<f64>,
        q_mvar: Option<f64>,
        data_json: Option<&str>,
        device_type: Option<&str>,
    ) -> SqlResult<()> {
        self.conn.execute(
            "INSERT INTO device_data (device_id, timestamp, p_mw, q_mvar, data_json, device_type)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            rusqlite::params![device_id, timestamp, p_mw, q_mvar, data_json, device_type],
        )?;
        Ok(())
    }

    /// 单行结果：timestamp, p_mw, q_mvar, data_json。max_points 为 Some(n) 时若结果超过 n 条则按时间等分桶降采样
    pub fn query_device_data(
        &self,
        device_id: &str,
        start_time: Option<f64>,
        end_time: Option<f64>,
        max_points: Option<usize>,
    ) -> SqlResult<Vec<(f64, Option<f64>, Option<f64>, Option<String>)>> {
        let mut query = "SELECT timestamp, p_mw, q_mvar, data_json FROM device_data WHERE device_id = ?1".to_string();
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

    /// 返回 device_data 表中所有不重复的 device_id（供数据看板「当前应用数据库」设备列表）
    pub fn query_device_ids(&self) -> SqlResult<Vec<String>> {
        let mut stmt = self.conn.prepare("SELECT DISTINCT device_id FROM device_data ORDER BY device_id")?;
        let rows = stmt.query_map([], |row| row.get::<_, String>(0))?;
        let mut ids = Vec::new();
        for row in rows {
            ids.push(row?);
        }
        Ok(ids)
    }

    /// 返回 device_data 中不重复的 device_id 及其 device_type（同一设备取一条非空 device_type）
    pub fn query_device_ids_with_types(&self) -> SqlResult<Vec<(String, Option<String>)>> {
        let mut stmt = self.conn.prepare(
            "SELECT d.device_id, (SELECT d2.device_type FROM device_data d2 WHERE d2.device_id = d.device_id AND d2.device_type IS NOT NULL LIMIT 1) FROM (SELECT DISTINCT device_id FROM device_data) d ORDER BY d.device_id",
        )?;
        let rows = stmt.query_map([], |row| Ok((row.get::<_, String>(0)?, row.get::<_, Option<String>>(1)?)))?;
        let mut out = Vec::new();
        for row in rows {
            out.push(row?);
        }
        Ok(out)
    }

    /// 返回该设备最新一行（含 data_json），用于状态展示，避免全表扫描
    pub fn query_device_data_latest(
        &self,
        device_id: &str,
    ) -> SqlResult<Option<(f64, Option<f64>, Option<f64>, Option<String>)>> {
        let mut stmt = self.conn.prepare(
            "SELECT timestamp, p_mw, q_mvar, data_json FROM device_data WHERE device_id = ?1 ORDER BY timestamp DESC LIMIT 1",
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
