"""
pandapower 计算内核实现
"""

from typing import Dict, Any, List, Union
from ..interface import PowerCalculationKernel
import pandas as pd


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
            
            # 提取结果（按行组织并带上 name，供 Rust 端按 name 匹配设备并写入监控 DB）
            results = {
                "converged": converged,
                "errors": errors,
                "devices": {}
            }

            def _res_to_row_dict(net, res_df, table_name: str) -> Dict[str, Dict[str, Any]]:
                if res_df is None or res_df.empty:
                    return {}
                table = getattr(net, table_name, None)
                name_series = table["name"] if table is not None and "name" in table.columns else None
                out = {}
                for idx in res_df.index:
                    row = res_df.loc[idx].to_dict()
                    if name_series is not None and idx in name_series.index:
                        row["name"] = name_series[idx]
                    out[str(idx)] = row
                return out

            try:
                if hasattr(self.net, 'res_bus') and self.net.res_bus is not None:
                    results["devices"]["buses"] = _res_to_row_dict(self.net, self.net.res_bus, "bus")
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取母线结果失败: {str(e)}",
                    "details": {}
                })
            try:
                if hasattr(self.net, 'res_line') and self.net.res_line is not None:
                    results["devices"]["lines"] = _res_to_row_dict(self.net, self.net.res_line, "line")
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取线路结果失败: {str(e)}",
                    "details": {}
                })
            try:
                if hasattr(self.net, 'res_switch') and self.net.res_switch is not None:
                    results["devices"]["switches"] = _res_to_row_dict(self.net, self.net.res_switch, "switch")
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取开关结果失败: {str(e)}",
                    "details": {}
                })
            try:
                if hasattr(self.net, 'res_trafo') and self.net.res_trafo is not None:
                    results["devices"]["transformers"] = _res_to_row_dict(self.net, self.net.res_trafo, "trafo")
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取变压器结果失败: {str(e)}",
                    "details": {}
                })
            try:
                # 光伏等静态发电机在 pandapower 中为 sgen 表，优先用 res_sgen；若有 res_gen 再合并
                if hasattr(self.net, 'res_sgen') and self.net.res_sgen is not None and not self.net.res_sgen.empty:
                    results["devices"]["generators"] = _res_to_row_dict(self.net, self.net.res_sgen, "sgen")
                elif hasattr(self.net, 'res_gen') and self.net.res_gen is not None:
                    results["devices"]["generators"] = _res_to_row_dict(self.net, self.net.res_gen, "gen")
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取发电机结果失败: {str(e)}",
                    "details": {}
                })
            try:
                if hasattr(self.net, 'res_load') and self.net.res_load is not None:
                    results["devices"]["loads"] = _res_to_row_dict(self.net, self.net.res_load, "load")
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取负载结果失败: {str(e)}",
                    "details": {}
                })
            try:
                if hasattr(self.net, 'res_storage') and self.net.res_storage is not None:
                    results["devices"]["storages"] = _res_to_row_dict(self.net, self.net.res_storage, "storage")
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取储能结果失败: {str(e)}",
                    "details": {}
                })
            try:
                if hasattr(self.net, 'res_ext_grid') and self.net.res_ext_grid is not None:
                    results["devices"]["ext_grids"] = _res_to_row_dict(self.net, self.net.res_ext_grid, "ext_grid")
            except Exception as e:
                errors.append({
                    "type": "calculation",
                    "severity": "warning",
                    "message": f"提取外部电网结果失败: {str(e)}",
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
                # 检查线路过载（loading > 100%）
                if 'loading_percent' in net.res_line.columns:
                    overloaded_lines = net.res_line[net.res_line['loading_percent'] > 100.0]
                    for idx, row in overloaded_lines.iterrows():
                        line_name = net.line.loc[idx, 'name'] if 'name' in net.line.columns else f"Line {idx}"
                        errors.append({
                            "type": "calculation",
                            "severity": "warning",
                            "message": f"线路 {line_name} 过载: {row['loading_percent']:.2f}%",
                            "device_id": None,
                            "details": {
                                "line_index": int(idx),
                                "loading_percent": float(row['loading_percent']),
                                "p_from_mw": float(row.get('p_from_mw', 0.0)),
                                "p_to_mw": float(row.get('p_to_mw', 0.0))
                            }
                        })
                
                # 检查线路电流超限
                if 'i_from_ka' in net.res_line.columns and 'max_i_ka' in net.line.columns:
                    for idx in net.res_line.index:
                        if idx in net.line.index:
                            i_from = net.res_line.loc[idx, 'i_from_ka']
                            max_i = net.line.loc[idx, 'max_i_ka']
                            if not pd.isna(i_from) and not pd.isna(max_i) and i_from > max_i * 1.1:  # 允许10%余量
                                line_name = net.line.loc[idx, 'name'] if 'name' in net.line.columns else f"Line {idx}"
                                errors.append({
                                    "type": "calculation",
                                    "severity": "warning",
                                    "message": f"线路 {line_name} 电流超限: {i_from:.3f} kA > {max_i:.3f} kA",
                                    "device_id": None,
                                    "details": {
                                        "line_index": int(idx),
                                        "current_ka": float(i_from),
                                        "max_current_ka": float(max_i)
                                    }
                                })
            
            # 检查变压器错误
            if hasattr(net, 'res_trafo') and net.res_trafo is not None:
                # 检查变压器过载
                if 'loading_percent' in net.res_trafo.columns:
                    overloaded_trafos = net.res_trafo[net.res_trafo['loading_percent'] > 100.0]
                    for idx, row in overloaded_trafos.iterrows():
                        trafo_name = net.trafo.loc[idx, 'name'] if 'name' in net.trafo.columns else f"Transformer {idx}"
                        errors.append({
                            "type": "calculation",
                            "severity": "warning",
                            "message": f"变压器 {trafo_name} 过载: {row['loading_percent']:.2f}%",
                            "device_id": None,
                            "details": {
                                "trafo_index": int(idx),
                                "loading_percent": float(row['loading_percent']),
                                "p_hv_mw": float(row.get('p_hv_mw', 0.0)),
                                "p_lv_mw": float(row.get('p_lv_mw', 0.0))
                            }
                        })
            
            # 检查母线电压越限
            if hasattr(net, 'res_bus') and net.res_bus is not None:
                if 'vm_pu' in net.res_bus.columns:
                    # 检查电压是否在合理范围内（0.9-1.1 pu）
                    voltage_issues = net.res_bus[
                        (net.res_bus['vm_pu'] < 0.9) | (net.res_bus['vm_pu'] > 1.1)
                    ]
                    for idx, row in voltage_issues.iterrows():
                        bus_name = net.bus.loc[idx, 'name'] if 'name' in net.bus.columns else f"Bus {idx}"
                        vm_pu = row['vm_pu']
                        severity = "error" if vm_pu < 0.85 or vm_pu > 1.15 else "warning"
                        errors.append({
                            "type": "calculation",
                            "severity": severity,
                            "message": f"母线 {bus_name} 电压异常: {vm_pu:.3f} pu",
                            "device_id": None,
                            "details": {
                                "bus_index": int(idx),
                                "voltage_pu": float(vm_pu),
                                "vn_kv": float(net.bus.loc[idx, 'vn_kv']) if 'vn_kv' in net.bus.columns else 0.0
                            }
                        })
        except Exception as e:
            # 记录检查错误但不影响主流程
            errors.append({
                "type": "runtime",
                "severity": "warning",
                "message": f"结果错误检查失败: {str(e)}",
                "device_id": None,
                "details": {"exception": str(e)}
            })
    
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
