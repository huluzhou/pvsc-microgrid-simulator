#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 内核服务入口
提供 JSON-RPC over stdio 接口，供 Rust 调用
"""

import sys
import json
from typing import Dict, Any


class PythonKernel:
    """Python 内核主类"""
    
    def __init__(self):
        from simulation.engine import SimulationEngine
        self.simulation_engine = SimulationEngine()
        self.power_calculator = None
        self.ai_kernel = None
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 JSON-RPC 请求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "ping":
                result = {"status": "ok"}
            elif method.startswith("simulation."):
                result = self.handle_simulation(method, params)
            elif method.startswith("power."):
                result = self.handle_power_calculation(method, params)
            elif method.startswith("ai."):
                result = self.handle_ai(method, params)
            elif method.startswith("analytics."):
                result = self.handle_analytics(method, params)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
    
    def handle_simulation(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理仿真相关请求"""
        action = params.get("action", "")
        
        if method == "simulation.start":
            self.simulation_engine.start()
            return {"status": "started"}
        elif method == "simulation.stop":
            self.simulation_engine.stop()
            return {"status": "stopped"}
        elif method == "simulation.pause":
            # 暂停功能将在后续实现
            return {"status": "paused"}
        elif method == "simulation.resume":
            # 恢复功能将在后续实现
            return {"status": "resumed"}
        elif method == "simulation.set_device_mode":
            device_id = params.get("device_id")
            mode = params.get("mode")
            self.simulation_engine.set_device_mode(device_id, mode)
            return {"status": "ok"}
        elif method == "simulation.get_device_data":
            device_id = params.get("device_id")
            data = self.simulation_engine.get_device_data(device_id)
            return data
        else:
            return {"status": "not_implemented"}
    
    def handle_power_calculation(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理功率计算相关请求"""
        if not self.power_calculator:
            from simulation.power_calculation.factory import PowerKernelFactory
            # 默认使用 pandapower
            self.power_calculator = PowerKernelFactory.create("pandapower")
            if not self.power_calculator:
                return {"error": "Power calculation kernel not available"}
        
        if method == "power.calculate":
            topology_data = params.get("topology_data", {})
            result = self.power_calculator.calculate_power_flow(topology_data)
            return result
        else:
            return {"status": "not_implemented"}
    
    def handle_ai(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 AI 相关请求"""
        if not self.ai_kernel:
            from ai.factory import AIKernelFactory
            # 默认使用 PyTorch（如果可用）
            self.ai_kernel = AIKernelFactory.create("pytorch")
            if not self.ai_kernel:
                return {"error": "No AI kernel available"}
        
        if method == "ai.predict":
            device_ids = params.get("device_ids", [])
            prediction_horizon = params.get("prediction_horizon", 3600)
            prediction_type = params.get("prediction_type", "power")
            result = self.ai_kernel.predict(device_ids, prediction_horizon, prediction_type)
            return result
        elif method == "ai.optimize":
            objective = params.get("objective", "minimize_cost")
            constraints = params.get("constraints", [])
            time_horizon = params.get("time_horizon", 3600)
            result = self.ai_kernel.optimize(objective, constraints, time_horizon)
            return result
        elif method == "ai.get_recommendations":
            device_ids = params.get("device_ids", [])
            recommendations = self.ai_kernel.get_recommendations(device_ids)
            return {"recommendations": recommendations}
        else:
            return {"status": "not_implemented"}
    
    def handle_analytics(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据分析相关请求"""
        from data.processor import DataProcessor
        
        processor = DataProcessor()
        analysis_type = params.get("analysis_type", "performance")
        data = params.get("data", [])
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        
        if method == "analytics.analyze":
            # 处理数据
            all_processed_data = []
            for device_id, device_data in data:
                processed = []
                for point in device_data:
                    if isinstance(point, tuple) and len(point) >= 4:
                        timestamp, voltage, current, power = point[0], point[1], point[2], point[3]
                        processed.append({
                            "timestamp": timestamp,
                            "voltage": voltage,
                            "current": current,
                            "power": power,
                        })
                    elif isinstance(point, dict):
                        processed.append(point)
                
                # 数据清洗
                cleaned = [processor.process_device_data(d) for d in processed]
                all_processed_data.append((device_id, cleaned))
            
            # 根据分析类型执行分析
            if analysis_type == "performance":
                result = self._analyze_performance(all_processed_data)
            elif analysis_type == "fault":
                result = self._analyze_fault(all_processed_data)
            elif analysis_type == "regulation":
                result = self._analyze_regulation(all_processed_data)
            elif analysis_type == "utilization":
                result = self._analyze_utilization(all_processed_data)
            elif analysis_type == "revenue":
                result = self._analyze_revenue(all_processed_data)
            else:
                result = {
                    "analysis_type": analysis_type,
                    "summary": {},
                    "details": {},
                    "charts": []
                }
            
            return result
        elif method == "analytics.generate_report":
            # 报告生成逻辑将在后续实现
            return {
                "report_path": "/tmp/report.pdf",
                "status": "generated"
            }
        else:
            return {"status": "not_implemented"}
    
    def _analyze_performance(self, data: list) -> Dict[str, Any]:
        """性能分析"""
        from data.processor import DataProcessor
        
        processor = DataProcessor()
        summary = {}
        details = {}
        charts = []
        
        for device_id, device_data in data:
            if not device_data:
                continue
            
            aggregated = processor.aggregate_data(device_data)
            
            # 计算效率（如果有功率数据）
            if "power" in aggregated:
                avg_power = aggregated["power"]["avg"]
                max_power = aggregated["power"]["max"]
                efficiency = (avg_power / max_power * 100) if max_power > 0 else 0
                
                summary[device_id] = {
                    "avg_power": avg_power,
                    "max_power": max_power,
                    "efficiency_percent": efficiency,
                }
            
            details[device_id] = aggregated
            
            # 生成图表数据
            charts.append({
                "title": f"{device_id} 功率趋势",
                "chart_type": "line",
                "data": {
                    "x": [d.get("timestamp", 0) for d in device_data],
                    "y": [d.get("power", 0) or 0 for d in device_data],
                }
            })
        
        return {
            "analysis_type": "performance",
            "summary": summary,
            "details": details,
            "charts": charts,
        }
    
    def _analyze_fault(self, data: list) -> Dict[str, Any]:
        """故障分析"""
        summary = {}
        details = {}
        charts = []
        
        for device_id, device_data in data:
            faults = []
            for point in device_data:
                # 检测异常值
                if point.get("voltage") and (point["voltage"] < 180 or point["voltage"] > 260):
                    faults.append({
                        "timestamp": point.get("timestamp"),
                        "type": "voltage_abnormal",
                        "value": point["voltage"],
                    })
                if point.get("current") and point["current"] < 0:
                    faults.append({
                        "timestamp": point.get("timestamp"),
                        "type": "current_negative",
                        "value": point["current"],
                    })
            
            summary[device_id] = {
                "fault_count": len(faults),
                "faults": faults[:10],  # 只返回前10个故障
            }
            details[device_id] = {"all_faults": faults}
        
        return {
            "analysis_type": "fault",
            "summary": summary,
            "details": details,
            "charts": charts,
        }
    
    def _analyze_regulation(self, data: list) -> Dict[str, Any]:
        """调节性能分析"""
        summary = {}
        details = {}
        charts = []
        
        for device_id, device_data in data:
            if len(device_data) < 2:
                continue
            
            # 计算响应时间（功率变化的时间）
            response_times = []
            for i in range(1, len(device_data)):
                prev_power = device_data[i-1].get("power", 0) or 0
                curr_power = device_data[i].get("power", 0) or 0
                time_diff = device_data[i].get("timestamp", 0) - device_data[i-1].get("timestamp", 0)
                
                if abs(curr_power - prev_power) > 100:  # 功率变化超过100W
                    response_times.append(time_diff)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            summary[device_id] = {
                "avg_response_time": avg_response_time,
                "response_count": len(response_times),
            }
            details[device_id] = {"response_times": response_times}
        
        return {
            "analysis_type": "regulation",
            "summary": summary,
            "details": details,
            "charts": charts,
        }
    
    def _analyze_utilization(self, data: list) -> Dict[str, Any]:
        """利用率分析"""
        from data.processor import DataProcessor
        
        processor = DataProcessor()
        summary = {}
        details = {}
        charts = []
        
        for device_id, device_data in data:
            if not device_data:
                continue
            
            aggregated = processor.aggregate_data(device_data)
            
            # 计算利用率（平均功率/最大功率）
            if "power" in aggregated:
                avg_power = aggregated["power"]["avg"]
                max_power = aggregated["power"]["max"]
                utilization = (avg_power / max_power * 100) if max_power > 0 else 0
                
                summary[device_id] = {
                    "utilization_percent": utilization,
                    "avg_power": avg_power,
                    "max_power": max_power,
                }
            
            details[device_id] = aggregated
        
        return {
            "analysis_type": "utilization",
            "summary": summary,
            "details": details,
            "charts": charts,
        }
    
    def _analyze_revenue(self, data: list) -> Dict[str, Any]:
        """收益分析"""
        summary = {}
        details = {}
        charts = []
        
        # 假设电价：0.5元/kWh
        electricity_price = 0.5
        
        for device_id, device_data in data:
            total_energy = 0.0  # kWh
            revenue = 0.0
            
            for i in range(1, len(device_data)):
                power = device_data[i].get("power", 0) or 0
                time_diff = device_data[i].get("timestamp", 0) - device_data[i-1].get("timestamp", 0)
                
                # 计算能量（功率 * 时间，转换为kWh）
                energy_kwh = (power / 1000.0) * (time_diff / 3600.0)
                total_energy += energy_kwh
            
            revenue = total_energy * electricity_price
            
            summary[device_id] = {
                "total_energy_kwh": total_energy,
                "revenue_yuan": revenue,
                "electricity_price": electricity_price,
            }
            details[device_id] = {
                "energy_breakdown": {
                    "total": total_energy,
                    "revenue": revenue,
                }
            }
        
        return {
            "analysis_type": "revenue",
            "summary": summary,
            "details": details,
            "charts": charts,
        }


def main():
    """主函数"""
    kernel = PythonKernel()
    
    # 从 stdin 读取 JSON-RPC 请求
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = kernel.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
