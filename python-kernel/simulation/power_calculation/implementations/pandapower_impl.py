"""
pandapower 计算内核实现
"""

from typing import Dict, Any, List, Union
from ..interface import PowerCalculationKernel


class PandapowerKernel(PowerCalculationKernel):
    """pandapower 计算内核实现"""
    
    def __init__(self):
        try:
            import pandapower as pp
            self.pp = pp
            self.net = None
        except ImportError:
            raise ImportError("pandapower is not installed. Please install it with: pip install pandapower")
    
    def calculate_power_flow(self, topology_data_or_net: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """
        执行潮流计算
        
        Args:
            topology_data_or_net: 必须是已转换的pandapower网络对象（由适配器层转换）
                                 不接受原始拓扑数据字典，请使用PandapowerTopologyAdapter进行转换
        
        Returns:
            计算结果字典，包含converged、errors、devices等字段
        """
        errors: List[Dict[str, Any]] = []
        
        try:
            # 只接受pandapower网络对象，不接受原始字典
            if hasattr(topology_data_or_net, 'bus') and hasattr(topology_data_or_net, 'line'):
                # 这是pandapower网络对象（适配器转换后的结果）
                self.net = topology_data_or_net
            elif isinstance(topology_data_or_net, dict):
                # 拒绝原始字典输入，要求使用适配器层
                raise ValueError(
                    "不接受原始拓扑数据字典。请使用PandapowerTopologyAdapter进行转换：\n"
                    "  from simulation.adapters.pandapower_adapter import PandapowerTopologyAdapter\n"
                    "  adapter = PandapowerTopologyAdapter()\n"
                    "  result = adapter.convert(topology_data)\n"
                    "  if result.success:\n"
                    "      network = result.data  # 然后传递给calculate_power_flow"
                )
            else:
                raise ValueError(f"不支持的输入类型: {type(topology_data_or_net)}。期望pandapower网络对象。")
            
            # 执行潮流计算
            calculation_failed = False
            try:
                self.pp.runpp(self.net)
            except Exception as calc_error:
                calculation_failed = True
                errors.append({
                    "type": "calculation",
                    "severity": "error",
                    "message": f"潮流计算失败: {str(calc_error)}",
                    "details": {
                        "exception": str(calc_error),
                        "exception_type": type(calc_error).__name__
                    }
                })
            
            # 检查收敛状态
            converged = getattr(self.net, 'converged', False)
            if not converged:
                calculation_failed = True
                errors.append({
                    "type": "calculation",
                    "severity": "error",
                    "message": "潮流计算不收敛",
                    "details": {}
                })
            
            # 只在计算失败或不收敛时获取诊断信息，减少正常情况下的计算开销
            if calculation_failed or not converged:
                try:
                    diagnostic = self.pp.diagnostic(self.net)
                    if diagnostic:
                        for diag_item in diagnostic:
                            errors.append({
                                "type": "calculation",
                                "severity": "warning",
                                "message": f"诊断信息: {diag_item}",
                                "details": {"diagnostic": diag_item}
                            })
                except Exception:
                    # 诊断功能可能不可用，忽略
                    pass
            
            # 检查结果表中的错误标记
            self._check_result_errors(self.net, errors)
            
            # 提取结果
            results = {
                "converged": converged,
                "errors": errors,
                "devices": {}
            }
            
            # 提取各设备的结果
            try:
                if hasattr(self.net, 'res_bus') and self.net.res_bus is not None:
                    results["devices"]["buses"] = self.net.res_bus.to_dict()
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取母线结果失败: {str(e)}",
                    "details": {}
                })
            
            try:
                if hasattr(self.net, 'res_line') and self.net.res_line is not None:
                    results["devices"]["lines"] = self.net.res_line.to_dict()
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取线路结果失败: {str(e)}",
                    "details": {}
                })
            
            try:
                if hasattr(self.net, 'res_trafo') and self.net.res_trafo is not None:
                    results["devices"]["transformers"] = self.net.res_trafo.to_dict()
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取变压器结果失败: {str(e)}",
                    "details": {}
                })
            
            try:
                if hasattr(self.net, 'res_gen') and self.net.res_gen is not None:
                    results["devices"]["generators"] = self.net.res_gen.to_dict()
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取发电机结果失败: {str(e)}",
                    "details": {}
                })
            
            try:
                if hasattr(self.net, 'res_load') and self.net.res_load is not None:
                    results["devices"]["loads"] = self.net.res_load.to_dict()
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取负载结果失败: {str(e)}",
                    "details": {}
                })
            
            try:
                if hasattr(self.net, 'res_storage') and self.net.res_storage is not None:
                    results["devices"]["storages"] = self.net.res_storage.to_dict()
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取储能结果失败: {str(e)}",
                    "details": {}
                })
            
            results["errors"] = errors
            return results
            
        except Exception as e:
            errors.append({
                "type": "runtime",
                "severity": "error",
                "message": f"计算过程异常: {str(e)}",
                "details": {
                    "exception": str(e),
                    "exception_type": type(e).__name__
                }
            })
            return {
                "converged": False,
                "errors": errors,
                "devices": {}
            }
    
    def _check_result_errors(self, net, errors: List[Dict[str, Any]]):
        """检查结果表中的错误标记"""
        try:
            # 检查线路错误
            if hasattr(net, 'res_line') and net.res_line is not None:
                # pandapower在某些情况下会在结果中标记错误
                # 这里可以检查特定的错误条件
                pass
            
            # 检查变压器错误
            if hasattr(net, 'res_trafo') and net.res_trafo is not None:
                pass
        except Exception:
            # 忽略检查错误
            pass
    
    def convert_topology(self, topology: Dict[str, Any]) -> Any:
        """
        将系统拓扑转换为 pandapower 格式
        
        ⚠️ 已弃用：此方法已被移除，请使用适配器层（PandapowerTopologyAdapter）进行转换。
        
        原因：
        - 避免重复的转换逻辑，统一使用适配器层
        - 适配器层提供更好的错误处理和验证功能
        - 确保代码维护的一致性
        
        使用方法：
        ```python
        from simulation.adapters.pandapower_adapter import PandapowerTopologyAdapter
        
        adapter = PandapowerTopologyAdapter()
        result = adapter.convert(topology_data)
        if result.success:
            network = result.data  # 然后传递给calculate_power_flow
        ```
        """
        raise NotImplementedError(
            "convert_topology方法已被移除。请使用PandapowerTopologyAdapter进行转换：\n"
            "  from simulation.adapters.pandapower_adapter import PandapowerTopologyAdapter\n"
            "  adapter = PandapowerTopologyAdapter()\n"
            "  result = adapter.convert(topology_data)\n"
            "  if result.success:\n"
            "      network = result.data"
        )
    
    def get_supported_features(self) -> List[str]:
        """获取支持的功能列表"""
        return [
            "AC power flow",
            "DC power flow",
            "OPF (Optimal Power Flow)",
            "Short circuit calculation"
        ]
