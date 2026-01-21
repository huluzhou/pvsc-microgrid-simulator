"""
历史数据模式
支持本地数据库和 SSH 远程数据库访问
"""

from typing import Dict, Any, List, Optional
import time
import sqlite3
import csv
import io


class HistoricalDataMode:
    """历史数据模式处理器"""
    
    def __init__(self, db_path: Optional[str] = None, ssh_config: Optional[Dict[str, Any]] = None):
        """
        初始化历史数据模式
        
        Args:
            db_path: 本地数据库路径（如果使用本地模式）
            ssh_config: SSH 配置（如果使用远程模式）
                {
                    "host": "example.com",
                    "port": 22,
                    "user": "username",
                    "auth_method": "password" | "keyfile",
                    "password": "password",  # 如果 auth_method 是 password
                    "key_path": "/path/to/key",  # 如果 auth_method 是 keyfile
                    "remote_db_path": "/mnt/analysis/data/device_data.db"
                }
        """
        self.db_path = db_path
        self.ssh_config = ssh_config
        self.use_remote = ssh_config is not None
        self.current_time = None
        self.time_scale = 1.0  # 时间缩放因子
        self._cache: Dict[str, List[Dict[str, Any]]] = {}  # 设备数据缓存
    
    def set_time(self, timestamp: float):
        """设置当前回放时间"""
        self.current_time = timestamp
    
    def set_time_scale(self, scale: float):
        """设置时间缩放因子"""
        self.time_scale = scale
    
    def _query_local_database(self, device_id: str, timestamp: float) -> Optional[Dict[str, Any]]:
        """从本地数据库查询数据"""
        if not self.db_path:
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询最接近指定时间的数据点
            cursor.execute("""
                SELECT timestamp, voltage, current, power, data_json
                FROM device_data
                WHERE device_id = ? AND timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (device_id, timestamp))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "voltage": row[1],
                    "current": row[2],
                    "power": row[3],
                    "timestamp": row[0],
                    "data_json": row[4],
                }
        except Exception as e:
            print(f"Error querying local database: {e}")
        
        return None
    
    def _query_remote_database(self, device_id: str, timestamp: float) -> Optional[Dict[str, Any]]:
        """通过 SSH 从远程数据库查询数据"""
        # 从缓存中查询数据
        if device_id in self._cache:
            cache_data = self._cache[device_id]
            # 查找最接近指定时间的数据点
            closest_data = None
            min_diff = float('inf')
            
            for data_point in cache_data:
                data_timestamp = data_point.get("timestamp", 0)
                diff = abs(data_timestamp - timestamp)
                if diff < min_diff and data_timestamp <= timestamp:
                    min_diff = diff
                    closest_data = data_point
            
            if closest_data:
                return closest_data
        
        return None
    
    def load_remote_data(self, device_id: str, csv_data: str):
        """从 CSV 格式的远程数据加载到缓存"""
        import csv as csv_module
        from io import StringIO
        
        try:
            reader = csv_module.DictReader(StringIO(csv_data))
            data_list = []
            for row in reader:
                data_list.append({
                    "timestamp": float(row.get("timestamp", 0)),
                    "voltage": float(row.get("voltage", 0)) if row.get("voltage") else None,
                    "current": float(row.get("current", 0)) if row.get("current") else None,
                    "power": float(row.get("power", 0)) if row.get("power") else None,
                    "data_json": row.get("data_json"),
                })
            self._cache[device_id] = sorted(data_list, key=lambda x: x["timestamp"])
        except Exception as e:
            print(f"Error loading remote data: {e}")
    
    def get_data(self, device_id: str) -> Dict[str, Any]:
        """从历史数据中获取设备数据"""
        if self.current_time is None:
            return {
                "voltage": 0.0,
                "current": 0.0,
                "power": 0.0,
                "timestamp": time.time(),
            }
        
        # 根据模式选择数据源
        if self.use_remote:
            data = self._query_remote_database(device_id, self.current_time)
        else:
            data = self._query_local_database(device_id, self.current_time)
        
        if data:
            return data
        
        # 如果没有找到数据，返回默认值
        return {
            "voltage": 220.0,
            "current": 10.0,
            "power": 2200.0,
            "timestamp": self.current_time,
        }
    
    def set_remote_data(self, device_id: str, data: List[Dict[str, Any]]):
        """设置从远程获取的数据（由 Rust 端调用）"""
        self._cache[device_id] = data
    
    def get_time_range(self, device_id: str) -> Optional[tuple]:
        """获取设备数据的时间范围"""
        if self.use_remote and device_id in self._cache:
            if not self._cache[device_id]:
                return None
            timestamps = [d.get("timestamp", 0) for d in self._cache[device_id]]
            return (min(timestamps), max(timestamps))
        
        # 本地数据库查询时间范围
        if not self.db_path:
            return None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT MIN(timestamp), MAX(timestamp)
                FROM device_data
                WHERE device_id = ?
            """, (device_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0] and row[1]:
                return (row[0], row[1])
        except Exception as e:
            print(f"Error querying time range: {e}")
        
        return None