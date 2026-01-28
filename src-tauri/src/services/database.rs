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

        Ok(())
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

    pub fn query_device_data(
        &self,
        device_id: &str,
        start_time: Option<f64>,
        end_time: Option<f64>,
    ) -> SqlResult<Vec<(f64, Option<f64>, Option<f64>)>> {
        let mut query = "SELECT timestamp, p_active, p_reactive FROM device_data WHERE device_id = ?1".to_string();
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
                ))
            },
        )?;

        let mut results = Vec::new();
        for row in rows {
            results.push(row?);
        }
        Ok(results)
    }
}
