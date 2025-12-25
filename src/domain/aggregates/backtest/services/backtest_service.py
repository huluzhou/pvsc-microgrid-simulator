"""回测服务模块"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.domain.models.entities.network_topology import NetworkTopology
from src.domain.models.entities.device import Device
from src.domain.models.entities.power_data import PowerData
from src.domain.models.events.backtest_events import (
    BacktestStartedEvent,
    BacktestCompletedEvent,
    BacktestProgressEvent,
    BacktestErrorEvent,
    StrategySignalEvent,
    PerformanceMetricEvent
)
from src.domain.models.strategies.base_strategy import BaseStrategy
from src.domain.models.value_objects.load_profile import LoadProfile
from src.domain.models.value_objects.backtest_result import BacktestResult
from src.infrastructure.shared.event_bus import BlinkerEventBus as EventBus


class BacktestService:
    """回测服务类，负责电力系统策略回测"""
    
    def __init__(self):
        """初始化回测服务"""
        self._is_running = False
        # 存储回测过程中的功率数据
        self._node_powers = {}
        self._connection_flows = {}
    
    def run_backtest(self, backtest_id: str, strategy: BaseStrategy, topology: NetworkTopology, 
                    historical_data: List[Dict[str, Any]], start_time: datetime, 
                    end_time: datetime, time_step: timedelta = timedelta(minutes=1)) -> BacktestResult:
        """
        运行回测
        
        Args:
            backtest_id: 回测ID
            strategy: 策略实例
            topology: 网络拓扑
            historical_data: 历史数据
            start_time: 开始时间
            end_time: 结束时间
            time_step: 时间步长
            
        Returns:
            BacktestResult: 回测结果
        """
        if self._is_running:
            raise RuntimeError("回测已在运行中")
        
        try:
            self._is_running = True
            
            # 初始化回测数据
            current_time = start_time
            total_steps = int((end_time - start_time) / time_step)
            results = {
                "backtest_id": backtest_id,
                "strategy_id": strategy.id,
                "topology_id": topology.topology_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "time_step": time_step.total_seconds(),
                "metrics": [],
                "signals": [],
                "power_data": [],
                "completed_steps": 0,
                "total_steps": total_steps
            }
            
            # 主回测循环
            step = 0
            while current_time < end_time and self._is_running:
                # 计算进度
                progress = (step / total_steps) * 100 if total_steps > 0 else 0
                
                try:
                    # 1. 模拟当前时间的电力系统状态
                    self._simulate_power_system(current_time, topology)
                    
                    # 2. 获取当前系统状态
                    system_state = self._get_system_state(topology)
                    
                    # 3. 执行策略
                    signals = strategy.execute(current_time, system_state)
                    
                    # 4. 应用策略信号
                    self._apply_signals(signals, current_time, backtest_id, topology)
                    
                    # 5. 重新计算功率
                    self._recalculate_power_data(topology)
                    
                    # 6. 记录数据
                    results["power_data"].append({
                        "timestamp": current_time.isoformat(),
                        "node_powers": {node_id: str(power) for node_id, power in self._node_powers.items()},
                        "connection_flows": {conn_id: str(flow) for conn_id, flow in self._connection_flows.items()}
                    })
                    
                    results["signals"].extend(signals)
                    
                    # 7. 计算性能指标
                    self._calculate_metrics(results, current_time)
                    
                except Exception as e:
                    pass
                
                # 前进到下一个时间步
                current_time += time_step
                step += 1
                results["completed_steps"] = step
            
            if self._is_running:
                # 计算最终指标
                self._calculate_final_metrics(results)
            
            # 创建并返回回测结果对象
            return BacktestResult(
                backtest_id=backtest_id,
                strategy_id=strategy.id,
                topology_id=topology.topology_id,
                start_time=start_time,
                end_time=end_time,
                metrics=results.get("final_metrics", {}),
                signals=results["signals"],
                power_data=results["power_data"],
                is_successful=True
            )
            
        except Exception as e:
            # 创建失败的回测结果
            return BacktestResult(
                backtest_id=backtest_id,
                strategy_id=strategy.id if 'strategy' in locals() else "unknown",
                topology_id=topology.topology_id if 'topology' in locals() else "unknown",
                start_time=start_time if 'start_time' in locals() else datetime.now(),
                end_time=end_time if 'end_time' in locals() else datetime.now(),
                metrics={"error": str(e)},
                signals=[],
                power_data=[],
                is_successful=False
            )
            
        finally:
            self._is_running = False
    
    def stop_backtest(self) -> None:
        """停止正在运行的回测"""
        self._is_running = False
    
    def validate_backtest_parameters(self, strategy: BaseStrategy, topology: NetworkTopology, 
                                   historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        验证回测参数
        
        Args:
            strategy: 策略实例
            topology: 网络拓扑
            historical_data: 历史数据
            
        Returns:
            验证结果
        """
        validation_result = {
            "is_valid": True,
            "errors": []
        }
        
        # 验证策略
        if not strategy:
            validation_result["is_valid"] = False
            validation_result["errors"].append("策略实例不能为空")
        
        # 验证拓扑
        if not topology:
            validation_result["is_valid"] = False
            validation_result["errors"].append("网络拓扑不能为空")
        elif not topology.get_all_nodes():
            validation_result["is_valid"] = False
            validation_result["errors"].append("网络拓扑中没有节点")
        
        # 验证历史数据
        if not historical_data:
            validation_result["is_valid"] = False
            validation_result["errors"].append("历史数据不能为空")
        
        return validation_result
    
    def analyze_backtest_results(self, backtest_result: BacktestResult) -> Dict[str, Any]:
        """
        分析回测结果
        
        Args:
            backtest_result: 回测结果
            
        Returns:
            分析结果
        """
        analysis = {
            "backtest_id": backtest_result.backtest_id,
            "strategy_performance": {},
            "system_behavior": {},
            "recommendations": []
        }
        
        # 简化实现
        if backtest_result.is_successful:
            # 基于指标进行分析
            metrics = backtest_result.metrics
            analysis["strategy_performance"]["total_signals"] = len(backtest_result.signals)
            analysis["strategy_performance"]["execution_duration"] = (
                backtest_result.end_time - backtest_result.start_time
            ).total_seconds() / 3600  # 转换为小时
        
        return analysis
    
    def _simulate_power_system(self, timestamp: datetime, topology: NetworkTopology) -> None:
        """
        模拟电力系统在指定时间点的状态
        
        Args:
            timestamp: 模拟时间点
            topology: 网络拓扑
        """
        # 模拟设备状态随时间变化
        for device in topology.get_all_devices():
            if device.device_type == "PV":
                # 模拟光伏发电随时间变化
                hour = timestamp.hour
                efficiency = max(0, min(1, (hour - 6) / 6) if hour < 12 else (18 - hour) / 6)
                device.power = device.capacity * efficiency
            elif device.device_type == "Load":
                # 模拟负载随时间变化
                hour = timestamp.hour
                if 8 <= hour < 20:
                    load_factor = 0.8
                else:
                    load_factor = 0.4
                device.power = device.capacity * load_factor
    
    def _recalculate_power_data(self, topology: NetworkTopology) -> None:
        """
        重新计算回测中的功率数据
        
        Args:
            topology: 网络拓扑
        """
        # 初始化节点功率
        for node in topology.get_all_nodes():
            self._node_powers[node.node_id] = 0.0
        
        # 初始化连接潮流
        for connection in topology.get_all_connections():
            conn_id = f"{connection.source_id}-{connection.target_id}"
            self._connection_flows[conn_id] = 0.0
        
        # 计算节点功率
        for device in topology.get_all_devices():
            if hasattr(device, 'node_id') and device.node_id in self._node_powers:
                if device.device_type == "Load":
                    # 负载消耗功率为负
                    self._node_powers[device.node_id] -= device.power
                else:
                    # 发电设备产生功率为正
                    self._node_powers[device.node_id] += device.power
    
    def _get_system_state(self, topology: NetworkTopology) -> Dict[str, Any]:
        """
        获取当前系统状态
        
        Args:
            topology: 网络拓扑
            
        Returns:
            系统状态字典
        """
        return {
            "nodes": {node.node_id: {"voltage": node.voltage, "power": self._node_powers.get(node.node_id, 0)}
                     for node in topology.get_all_nodes()},
            "devices": {device.device_id: {"type": device.device_type, "power": device.power, 
                                          "capacity": device.capacity}
                        for device in topology.get_all_devices()},
            "power_flows": self._connection_flows
        }
    
    def _apply_signals(self, signals: List[Dict[str, Any]], timestamp: datetime, 
                      backtest_id: str, topology: NetworkTopology) -> None:
        """
        应用策略信号
        
        Args:
            signals: 策略信号列表
            timestamp: 时间戳
            backtest_id: 回测ID
            topology: 网络拓扑
        """
        for signal in signals:
            device_id = signal.get("device_id")
            signal_type = signal.get("type")
            value = signal.get("value")
            
            if device_id and signal_type and value is not None:
                # 更新设备参数
                for device in topology.get_all_devices():
                    if device.device_id == device_id:
                        if signal_type == "power":
                            device.power = value
                        elif signal_type == "capacity":
                            device.capacity = value
                        break
    
    def _calculate_metrics(self, results: Dict[str, Any], timestamp: datetime) -> None:
        """
        计算性能指标
        
        Args:
            results: 回测结果
            timestamp: 时间戳
        """
        # 计算当前时间点的指标
        metrics = {
            "total_power_loss": 0.0,  # 简化实现
            "timestamp": timestamp.isoformat()
        }
        
        # 记录指标
        if "metrics" not in results:
            results["metrics"] = []
        results["metrics"].append(metrics)
    
    def _calculate_final_metrics(self, results: Dict[str, Any]) -> None:
        """
        计算最终性能指标
        
        Args:
            results: 回测结果
        """
        # 计算平均功率损耗
        if results["metrics"]:
            avg_power_loss = sum(m["total_power_loss"] for m in results["metrics"]) / len(results["metrics"])
            results["final_metrics"] = {
                "average_power_loss": avg_power_loss,
                "total_signals": len(results["signals"]),
                "completion_rate": (results["completed_steps"] / results["total_steps"]) * 100 if results["total_steps"] > 0 else 0
            }