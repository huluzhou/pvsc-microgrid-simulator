#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 内核服务入口
提供 JSON-RPC over stdio 接口，供 Rust 调用

注意：为了与 PyInstaller 兼容，所有导入都在顶部完成
"""

import sys
import json
import os

# 确保 PyInstaller 打包后能找到模块
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    base_path = sys._MEIPASS
    sys.path.insert(0, base_path)
else:
    # 开发模式
    base_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, base_path)

# 在顶部导入所有需要的模块（PyInstaller 兼容）
from typing import Dict, Any

# 延迟导入重型模块的标志
_simulation_engine = None
_power_calculator = None


def get_simulation_engine():
    """获取仿真引擎实例（延迟初始化）"""
    global _simulation_engine
    if _simulation_engine is None:
        from simulation.engine import SimulationEngine
        _simulation_engine = SimulationEngine()
    return _simulation_engine


def get_power_calculator():
    """获取功率计算器实例（延迟初始化）"""
    global _power_calculator
    if _power_calculator is None:
        from simulation.power_calculation.factory import PowerKernelFactory
        _power_calculator = PowerKernelFactory.create("pandapower")
    return _power_calculator


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """处理 JSON-RPC 请求"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    try:
        if method == "ping":
            result = {"status": "ok"}
        elif method.startswith("simulation."):
            result = handle_simulation(method, params)
        elif method.startswith("power."):
            result = handle_power_calculation(method, params)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": str(e)
            }
        }


def handle_simulation(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """处理仿真相关请求"""
    engine = get_simulation_engine()
    
    if method == "simulation.start":
        calculation_interval_ms = params.get("calculation_interval_ms", 1000)
        try:
            engine.start(calculation_interval_ms=calculation_interval_ms)
            return {"status": "started"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.stop":
        try:
            engine.stop()
            return {"status": "stopped"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.pause":
        try:
            engine.pause()
            return {"status": "paused"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.resume":
        try:
            engine.resume()
            return {"status": "resumed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.set_topology":
        topology_data = params.get("topology_data")
        if not topology_data:
            return {"status": "error", "message": "拓扑数据未提供"}
        try:
            engine.set_topology(topology_data)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.set_device_mode":
        device_id = params.get("device_id")
        mode = params.get("mode")
        try:
            engine.set_device_mode(device_id, mode)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.set_device_random_config":
        device_id = params.get("device_id")
        min_power = params.get("min_power")
        max_power = params.get("max_power")
        try:
            engine.set_device_random_config(device_id, min_power, max_power)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.set_device_manual_setpoint":
        device_id = params.get("device_id")
        active_power = params.get("active_power")
        reactive_power = params.get("reactive_power", 0)
        try:
            engine.set_device_manual_setpoint(device_id, active_power, reactive_power)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.set_device_historical_config":
        device_id = params.get("device_id")
        config = params.get("config") or {}
        try:
            engine.set_device_historical_config(device_id, config)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.set_device_sim_params":
        device_id = params.get("device_id")
        sim_params = params.get("params") or {}
        try:
            engine.set_device_sim_params(device_id, sim_params)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.update_switch_state":
        device_id = params.get("device_id")
        is_closed = params.get("is_closed", True)
        try:
            engine.update_switch_state(device_id, is_closed)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.update_device_properties":
        device_id = params.get("device_id")
        properties = params.get("properties") or {}
        try:
            engine.update_device_properties(device_id, properties)
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.get_device_data":
        device_id = params.get("device_id")
        try:
            data = engine.get_device_data(device_id)
            return data
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.get_calculation_status":
        try:
            status = engine.get_calculation_status()
            return status
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.get_errors":
        try:
            errors = engine.get_errors()
            return {"errors": errors}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.get_last_result":
        try:
            result = engine.get_last_result()
            return {"result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif method == "simulation.perform_calculation":
        try:
            result = engine.perform_calculation()
            return {"result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        return {"status": "not_implemented"}


def handle_power_calculation(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """处理功率计算相关请求"""
    calculator = get_power_calculator()
    if not calculator:
        return {"error": "Power calculation kernel not available"}
    
    if method == "power.calculate":
        topology_data = params.get("topology_data", {})
        result = calculator.calculate_power_flow(topology_data)
        return result
    else:
        return {"status": "not_implemented"}


def main():
    """主函数"""
    # 输出启动信息到 stderr（会写入日志文件）
    print(f"Python kernel starting...", file=sys.stderr)
    print(f"Python version: {sys.version}", file=sys.stderr)
    print(f"Base path: {base_path}", file=sys.stderr)
    print(f"Frozen: {getattr(sys, 'frozen', False)}", file=sys.stderr)
    sys.stderr.flush()
    
    # 从 stdin 读取 JSON-RPC 请求
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = handle_request(request)
            # 输出响应到 stdout
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
            import traceback
            traceback.print_exc(file=sys.stderr)
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
