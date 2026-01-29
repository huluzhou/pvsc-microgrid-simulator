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
            calculation_interval_ms = params.get("calculation_interval_ms", 1000)
            try:
                self.simulation_engine.start(calculation_interval_ms=calculation_interval_ms)
                return {"status": "started"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.stop":
            try:
                self.simulation_engine.stop()
                return {"status": "stopped"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.pause":
            try:
                self.simulation_engine.pause()
                return {"status": "paused"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.resume":
            try:
                self.simulation_engine.resume()
                return {"status": "resumed"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.set_topology":
            topology_data = params.get("topology_data")
            if not topology_data:
                return {"status": "error", "message": "拓扑数据未提供"}
            try:
                self.simulation_engine.set_topology(topology_data)
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.set_device_mode":
            device_id = params.get("device_id")
            mode = params.get("mode")
            try:
                self.simulation_engine.set_device_mode(device_id, mode)
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.update_device_properties":
            device_id = params.get("device_id")
            properties = params.get("properties") or {}
            try:
                self.simulation_engine.update_device_properties(device_id, properties)
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.get_device_data":
            device_id = params.get("device_id")
            try:
                data = self.simulation_engine.get_device_data(device_id)
                return data
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.get_calculation_status":
            try:
                status = self.simulation_engine.get_calculation_status()
                return status
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.get_errors":
            try:
                errors = self.simulation_engine.get_errors()
                return {"errors": errors}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.get_last_result":
            try:
                result = self.simulation_engine.get_last_result()
                return {"result": result}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        elif method == "simulation.perform_calculation":
            try:
                result = self.simulation_engine.perform_calculation()
                return {"result": result}
            except Exception as e:
                return {"status": "error", "message": str(e)}
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
        """
        处理数据分析相关请求
        
        注意：数据分析功能已移除，应在前端或Rust端实现
        """
        return {
            "status": "not_implemented",
            "message": "数据分析功能已移除，应在前端或Rust端实现"
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
