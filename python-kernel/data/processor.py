"""
数据处理
"""

from typing import Dict, Any, List
import statistics
import math


class DataProcessor:
    """数据处理器"""
    
    def process_device_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理设备数据（数据清洗、转换等）"""
        processed = data.copy()
        
        # 异常值检测（使用3-sigma规则）
        if "voltage" in processed and processed["voltage"] is not None:
            # 电压应该在合理范围内（0-500V）
            if processed["voltage"] < 0 or processed["voltage"] > 500:
                processed["voltage"] = None
        
        if "current" in processed and processed["current"] is not None:
            # 电流应该在合理范围内（0-1000A）
            if processed["current"] < 0 or processed["current"] > 1000:
                processed["current"] = None
        
        if "power" in processed and processed["power"] is not None:
            # 功率应该在合理范围内（0-500kW）
            if processed["power"] < 0 or processed["power"] > 500000:
                processed["power"] = None
        
        # 如果功率缺失但电压和电流存在，计算功率
        if processed.get("power") is None and processed.get("voltage") and processed.get("current"):
            processed["power"] = processed["voltage"] * processed["current"]
        
        return processed
    
    def aggregate_data(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """聚合数据（平均值、最大值、最小值）"""
        if not data_list:
            return {}
        
        voltages = [d.get("voltage") for d in data_list if d.get("voltage") is not None]
        currents = [d.get("current") for d in data_list if d.get("current") is not None]
        powers = [d.get("power") for d in data_list if d.get("power") is not None]
        
        result = {}
        
        if voltages:
            result["voltage"] = {
                "avg": statistics.mean(voltages),
                "min": min(voltages),
                "max": max(voltages),
                "std": statistics.stdev(voltages) if len(voltages) > 1 else 0.0,
            }
        
        if currents:
            result["current"] = {
                "avg": statistics.mean(currents),
                "min": min(currents),
                "max": max(currents),
                "std": statistics.stdev(currents) if len(currents) > 1 else 0.0,
            }
        
        if powers:
            result["power"] = {
                "avg": statistics.mean(powers),
                "min": min(powers),
                "max": max(powers),
                "std": statistics.stdev(powers) if len(powers) > 1 else 0.0,
            }
        
        return result
    
    def filter_time_range(
        self, 
        data_list: List[Dict[str, Any]], 
        start_time: float, 
        end_time: float
    ) -> List[Dict[str, Any]]:
        """过滤时间范围内的数据"""
        return [
            d for d in data_list
            if d.get("timestamp") and start_time <= d.get("timestamp") <= end_time
        ]
    
    def resample_time_series(
        self,
        data_list: List[Dict[str, Any]],
        interval_seconds: float
    ) -> List[Dict[str, Any]]:
        """时间序列重采样"""
        if not data_list:
            return []
        
        sorted_data = sorted(data_list, key=lambda x: x.get("timestamp", 0))
        result = []
        current_interval_start = sorted_data[0].get("timestamp", 0)
        current_interval_data = []
        
        for data_point in sorted_data:
            timestamp = data_point.get("timestamp", 0)
            if timestamp < current_interval_start + interval_seconds:
                current_interval_data.append(data_point)
            else:
                # 聚合当前区间的数据
                if current_interval_data:
                    aggregated = self.aggregate_data(current_interval_data)
                    aggregated["timestamp"] = current_interval_start
                    result.append(aggregated)
                
                # 开始新区间
                current_interval_start = timestamp
                current_interval_data = [data_point]
        
        # 处理最后一个区间
        if current_interval_data:
            aggregated = self.aggregate_data(current_interval_data)
            aggregated["timestamp"] = current_interval_start
            result.append(aggregated)
        
        return result
