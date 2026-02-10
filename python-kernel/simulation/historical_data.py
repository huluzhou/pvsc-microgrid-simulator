"""
历史数据源抽象层：统一 CSV 和 SQLite 数据的加载与按时间取值。

HistoricalDataProvider (抽象基类)
  ├─ CsvDataProvider     — 解析 CSV 文件
  ├─ SqliteDataProvider  — 读取本地 SQLite 数据库（兼容仿真库和服务器库）
"""

import csv
import os
import sqlite3
import bisect
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List


class HistoricalDataProvider(ABC):
    """历史数据源抽象基类"""

    @abstractmethod
    def load(self, config: Dict[str, Any]) -> bool:
        """
        加载数据。成功返回 True。
        config 字段由子类定义，至少包含 filePath。
        """
        ...

    @abstractmethod
    def get_power_at(self, t: float) -> Tuple[float, float]:
        """
        按仿真时间 t（相对秒，从 0 开始）取功率。
        返回 (p_kw, q_kvar)。若超出范围且非循环，返回最后/首条记录。
        """
        ...

    @abstractmethod
    def get_time_range(self) -> Tuple[float, float]:
        """返回数据的 (t_min, t_max)，单位为原始时间戳（Unix 秒）。"""
        ...

    @abstractmethod
    def get_duration(self) -> float:
        """返回数据跨度（秒）。"""
        ...
    
    @abstractmethod
    def get_data_count(self) -> int:
        """返回数据点总数。"""
        ...
    
    @abstractmethod
    def get_power_at_index(self, idx: int) -> Tuple[float, float]:
        """按索引获取功率数据 (p_kw, q_kvar)。"""
        ...


# ---------------------------------------------------------------------------
# 内部数据容器：排序的时间序列
# ---------------------------------------------------------------------------

class _TimeSeries:
    """按时间戳排序的 (timestamp, p_kw, q_kvar) 序列，支持二分查找最近邻取值。"""

    def __init__(self):
        self.timestamps: List[float] = []
        self.p_values: List[float] = []
        self.q_values: List[float] = []

    def append(self, ts: float, p: float, q: float):
        self.timestamps.append(ts)
        self.p_values.append(p)
        self.q_values.append(q)

    def sort(self):
        if not self.timestamps:
            return
        combined = sorted(zip(self.timestamps, self.p_values, self.q_values))
        self.timestamps = [c[0] for c in combined]
        self.p_values = [c[1] for c in combined]
        self.q_values = [c[2] for c in combined]

    def __len__(self):
        return len(self.timestamps)

    def get_nearest(self, t: float) -> Tuple[float, float]:
        """取 t 对应的最近邻 (p_kw, q_kvar)（向左取最近的不大于 t 的点）。"""
        if not self.timestamps:
            return (0.0, 0.0)
        idx = bisect.bisect_right(self.timestamps, t) - 1
        idx = max(0, min(idx, len(self.timestamps) - 1))
        return (self.p_values[idx], self.q_values[idx])
    
    def get_at_index(self, idx: int) -> Tuple[float, float]:
        """按索引获取 (p_kw, q_kvar)。"""
        if not self.timestamps or idx < 0 or idx >= len(self.timestamps):
            return (0.0, 0.0)
        return (self.p_values[idx], self.q_values[idx])


# ---------------------------------------------------------------------------
# CSV 数据源
# ---------------------------------------------------------------------------

def _parse_timestamp(raw: str, fmt: str) -> Optional[float]:
    """解析时间戳字符串为 Unix 秒。支持纯数字（Unix 秒/毫秒）和 strptime 格式。"""
    raw = raw.strip()
    if not raw:
        return None
    # 尝试纯数字
    try:
        val = float(raw)
        if val > 1e12:
            val /= 1000.0  # 毫秒 → 秒
        return val
    except ValueError:
        pass
    # 按 fmt 解析
    import datetime
    try:
        dt = datetime.datetime.strptime(raw, fmt)
        return dt.timestamp()
    except (ValueError, OSError):
        pass
    # ISO / RFC3339
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, OSError):
        pass
    return None


def _convert_power(value: float, unit: str) -> float:
    """将功率值转为 kW。"""
    unit = (unit or "kW").strip()
    if unit == "W":
        return value / 1000.0
    elif unit == "MW":
        return value * 1000.0
    return value  # kW


class CsvDataProvider(HistoricalDataProvider):
    """
    CSV 数据源。
    config 字段：
      filePath, timeColumn, timeFormat, powerColumn({columnName, unit}),
      loadCalculation({gridMeter, pvGeneration?, storagePower?, chargerPower?}),
      startTime?, endTime?, loop?
    """

    def __init__(self):
        self._series = _TimeSeries()
        self._loop = True
        self._duration = 0.0
        self._t_min = 0.0
        self._t_max = 0.0

    def load(self, config: Dict[str, Any]) -> bool:
        file_path = config.get("filePath", "")
        if not file_path or not os.path.isfile(file_path):
            return False
        time_col = config.get("timeColumn", "timestamp")
        time_fmt = config.get("timeFormat", "%Y-%m-%d %H:%M:%S")
        power_col_cfg = config.get("powerColumn")  # {columnName, unit}
        load_calc = config.get("loadCalculation")  # {gridMeter, pvGeneration?, storagePower?, chargerPower?}
        start_time = config.get("startTime")
        end_time = config.get("endTime")
        self._loop = config.get("loop", True)

        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts = _parse_timestamp(row.get(time_col, ""), time_fmt)
                    if ts is None:
                        continue
                    if start_time is not None and ts < start_time:
                        continue
                    if end_time is not None and ts > end_time:
                        continue
                    p_kw = self._extract_power(row, power_col_cfg, load_calc)
                    self._series.append(ts, p_kw, 0.0)
        except Exception:
            return False

        if len(self._series) == 0:
            return False
        self._series.sort()
        self._t_min = self._series.timestamps[0]
        self._t_max = self._series.timestamps[-1]
        self._duration = self._t_max - self._t_min if self._t_max > self._t_min else 1.0
        return True

    def get_power_at(self, t: float) -> Tuple[float, float]:
        if self._loop and self._duration > 0:
            t_mapped = self._t_min + (t % self._duration)
        else:
            t_mapped = self._t_min + t
        return self._series.get_nearest(t_mapped)

    def get_time_range(self) -> Tuple[float, float]:
        return (self._t_min, self._t_max)

    def get_duration(self) -> float:
        return self._duration
    
    def get_data_count(self) -> int:
        return len(self._series)
    
    def get_power_at_index(self, idx: int) -> Tuple[float, float]:
        if self._loop and len(self._series) > 0:
            idx = idx % len(self._series)
        return self._series.get_at_index(idx)

    @staticmethod
    def _extract_power(row: Dict[str, str], power_col_cfg, load_calc) -> float:
        """从 CSV 行中提取有功功率（kW）。"""
        if power_col_cfg:
            col = power_col_cfg.get("columnName", "")
            unit = power_col_cfg.get("unit", "kW")
            try:
                return _convert_power(float(row.get(col, "0")), unit)
            except (ValueError, TypeError):
                return 0.0
        if load_calc:
            # 负载 = 关口下网 + 光伏发电 - 储能充电 - 充电桩充电
            def _read(cfg_key):
                cfg = load_calc.get(cfg_key)
                if not cfg:
                    return 0.0
                try:
                    return _convert_power(float(row.get(cfg["columnName"], "0")), cfg.get("unit", "kW"))
                except (ValueError, TypeError):
                    return 0.0
            grid = _read("gridMeter")
            pv = _read("pvGeneration")
            storage = _read("storagePower")
            charger = _read("chargerPower")
            return grid + pv - storage - charger
        return 0.0


# ---------------------------------------------------------------------------
# SQLite 数据源
# ---------------------------------------------------------------------------

class SqliteDataProvider(HistoricalDataProvider):
    """
    SQLite 数据源。兼容仿真生成的 device_data 表和服务器数据库。
    config 字段：
      filePath, sourceDeviceId（SQLite 中的 device_id 过滤），
      startTime?, endTime?, loop?
    自动检测列名以兼容不同版本 schema。
    """

    def __init__(self):
        self._series = _TimeSeries()
        self._loop = True
        self._duration = 0.0
        self._t_min = 0.0
        self._t_max = 0.0

    def load(self, config: Dict[str, Any]) -> bool:
        file_path = config.get("filePath", "")
        if not file_path or not os.path.isfile(file_path):
            return False
        source_device_id = config.get("sourceDeviceId", "")
        start_time = config.get("startTime")
        end_time = config.get("endTime")
        self._loop = config.get("loop", True)

        try:
            conn = sqlite3.connect(file_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 检测列名
            cursor.execute("PRAGMA table_info(device_data)")
            columns = {row["name"] for row in cursor.fetchall()}
            if "device_data" not in self._table_exists(conn):
                conn.close()
                return False

            p_col = "p_active" if "p_active" in columns else "power" if "power" in columns else None
            q_col = "p_reactive" if "p_reactive" in columns else None
            ts_col = "timestamp" if "timestamp" in columns else None

            if not p_col or not ts_col:
                conn.close()
                return False

            # 构建查询
            conditions = []
            params: list = []
            if source_device_id:
                conditions.append("device_id = ?")
                params.append(source_device_id)
            if start_time is not None:
                conditions.append(f"{ts_col} >= ?")
                params.append(float(start_time))
            if end_time is not None:
                conditions.append(f"{ts_col} <= ?")
                params.append(float(end_time))

            where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
            q_select = f"{q_col}" if q_col else "0"
            sql = f"SELECT {ts_col}, {p_col}, {q_select} FROM device_data{where} ORDER BY {ts_col}"
            cursor.execute(sql, params)

            for row in cursor:
                ts = float(row[0])
                p = float(row[1]) if row[1] is not None else 0.0
                q = float(row[2]) if row[2] is not None else 0.0
                self._series.append(ts, p, q)

            conn.close()
        except Exception:
            return False

        if len(self._series) == 0:
            return False
        self._series.sort()
        self._t_min = self._series.timestamps[0]
        self._t_max = self._series.timestamps[-1]
        self._duration = self._t_max - self._t_min if self._t_max > self._t_min else 1.0
        return True

    def get_power_at(self, t: float) -> Tuple[float, float]:
        if self._loop and self._duration > 0:
            t_mapped = self._t_min + (t % self._duration)
        else:
            t_mapped = self._t_min + t
        return self._series.get_nearest(t_mapped)

    def get_time_range(self) -> Tuple[float, float]:
        return (self._t_min, self._t_max)

    def get_duration(self) -> float:
        return self._duration
    
    def get_data_count(self) -> int:
        return len(self._series)
    
    def get_power_at_index(self, idx: int) -> Tuple[float, float]:
        if self._loop and len(self._series) > 0:
            idx = idx % len(self._series)
        return self._series.get_at_index(idx)

    @staticmethod
    def _table_exists(conn: sqlite3.Connection) -> set:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {row[0] for row in cursor}


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def create_provider(config: Dict[str, Any]) -> Optional[HistoricalDataProvider]:
    """
    根据 config 中的 sourceType 创建对应的 Provider 并加载数据。
    sourceType: 'csv'（默认）或 'sqlite'。
    返回加载成功的 Provider，失败返回 None。
    """
    source_type = config.get("sourceType", "csv")
    if source_type == "sqlite":
        provider = SqliteDataProvider()
    else:
        provider = CsvDataProvider()
    if provider.load(config):
        return provider
    return None
