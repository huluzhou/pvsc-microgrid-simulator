#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
仿真界面窗口
"""


from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QTreeWidgetItem, QMessageBox, QTableWidgetItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
import pandapower as pp
import time
from datetime import datetime

from .data_generators import DataGeneratorManager

# Modbus管理器导入
from .modbus_manager import ModbusManager
# UI组件管理器导入
from .ui_components import UIComponentManager
# 功率监控模块导入
from .power_monitor import PowerMonitor



class SimulationWindow(QMainWindow):
    """仿真界面窗口"""
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        
        # 先进行内存清理，确保之前仿真不会遗留内存
        self._cleanup_previous_simulation()
        
        self.canvas = canvas
        self.parent_window = parent
        self.network_model = canvas.network_model if hasattr(canvas, 'network_model') else None
        # 从canvas获取scene引用
        self.scene = canvas.scene if hasattr(canvas, 'scene') else None
        
        # 自动潮流计算相关属性
        self.auto_calc_timer = QTimer()
        self.auto_calc_timer.timeout.connect(self.auto_power_flow_calculation)
        self.is_auto_calculating = False
        self.selected_device_id = None
        self.selected_device_type = None
        self.generated_devices = set()
        
        # 数据生成器管理
        self.data_generator_manager = DataGeneratorManager()
        self.current_load_index = 0
        
        # 当前显示的组件信息（用于自动更新组件参数表格）
        self.current_component_type = None
        self.current_component_idx = None
        
        # 光伏能量统计相关属性
        self.last_pv_update_time = None
        self.last_reset_date = datetime.now().date()
        
        # 储能能量统计相关属性
        self.last_storage_update_time = None
        
        # Modbus服务器管理器
        self.modbus_manager = ModbusManager(self.network_model, self.scene)
        
        # 初始化UI组件管理器
        self.ui_manager = UIComponentManager(self)
        
        # 初始化数据控制管理器
        from .data_control import DataControlManager
        self.data_control_manager = DataControlManager(self)
        
        # 初始化功率监控管理器
        self.power_monitor = PowerMonitor(self)
        
        self.init_ui()
        self.load_network_data()
        # 默认不启动自动计算，需要用户手动启动
        self.is_auto_calculating = False
        # 初始化新的计算控制UI状态
        if hasattr(self, 'start_calc_btn'):
            self.start_calc_btn.setChecked(False)
            self.start_calc_btn.setText("开始仿真")
        if hasattr(self, 'calc_status_label'):
            self.calc_status_label.setText("仿真状态: 已停止")
    
    def _cleanup_previous_simulation(self):
        """清理之前仿真可能遗留的内存"""
        try:
            import gc
            
            # 强制垃圾回收
            gc.collect()
            
        except Exception as e:
            print(f"定期清理失败: {e}")

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("仿真模式 - PandaPower 仿真工具")
        self.setMinimumSize(1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 创建左侧设备树面板
        self.ui_manager.create_device_tree_panel(splitter)
        
        # 创建中央功率曲线区域
        self.ui_manager.create_central_image_area(splitter)
        
        # 创建右侧仿真结果面板
        self.ui_manager.create_simulation_results_panel(splitter)
        
        # 通过数据控制管理器创建数据生成选项卡
        self.data_control_manager.create_sgen_data_generation_tab()
        self.data_control_manager.create_load_data_generation_tab()
        self.data_control_manager.create_storage_data_generation_tab()
        
        # 设置分割器比例，让中央区域有更大的权重
        splitter.setSizes([250, 800, 300])
        
        # 设置分割器拉伸策略，让中央区域可以扩展
        splitter.setStretchFactor(0, 0)   # 左侧不自动扩展
        splitter.setStretchFactor(1, 1)   # 中央区域自动扩展
        splitter.setStretchFactor(2, 0)   # 右侧不自动扩展
        
        # 创建状态栏
        self.statusBar().showMessage("仿真模式已就绪")
        
        # 初始化功率监控的UI组件引用
        self.power_monitor.initialize_ui_components()
        
    def remove_all_device_tabs(self):
        """移除所有设备专用选项卡"""
        # 移除光伏选项卡
        sgen_tab_index = self.results_tabs.indexOf(self.sgen_data_tab)
        if sgen_tab_index != -1:
            self.results_tabs.removeTab(sgen_tab_index)
            
        # 移除负载选项卡
        load_tab_index = self.results_tabs.indexOf(self.load_data_tab)
        if load_tab_index != -1:
            self.results_tabs.removeTab(load_tab_index)
            
        # 移除储能选项卡
        storage_tab_index = self.results_tabs.indexOf(self.storage_data_tab)
        if storage_tab_index != -1:
            self.results_tabs.removeTab(storage_tab_index)
    
    def update_sgen_device_info(self, component_type, component_idx):
        """更新光伏设备信息"""
        if component_type and component_idx is not None:
            device_name = f"光伏_{component_idx}"
            self.sgen_current_device_label.setText(f"当前设备: {device_name}")
            
            # 检查当前设备是否启用了数据生成
            is_enabled = self.is_device_generation_enabled(component_type, component_idx)
            self.sgen_enable_generation_checkbox.setChecked(is_enabled)
            self.sgen_enable_generation_checkbox.setEnabled(True)
        else:
            self.sgen_current_device_label.setText("未选择光伏设备")
            self.sgen_enable_generation_checkbox.setChecked(False)
            self.sgen_enable_generation_checkbox.setEnabled(False)
    
    def update_load_device_info(self, component_type, component_idx):
        """更新负载设备信息"""
        if component_type and component_idx is not None:
            device_name = f"负载_{component_idx}"
            self.load_current_device_label.setText(f"当前设备: {device_name}")
            
            # 检查当前设备是否启用了数据生成
            is_enabled = self.is_device_generation_enabled(component_type, component_idx)
            self.load_enable_generation_checkbox.setChecked(is_enabled)
            self.load_enable_generation_checkbox.setEnabled(True)
        else:
            self.load_current_device_label.setText("未选择负载设备")
            self.load_enable_generation_checkbox.setChecked(False)
            self.load_enable_generation_checkbox.setEnabled(False)
    
    def update_storage_device_info(self, component_type, component_idx):
        """更新储能设备信息"""
        if component_type and component_idx is not None:
            device_name = f"储能_{component_idx}"
            self.storage_current_device_label.setText(f"当前设备: {device_name}")
            
            # 检查当前设备是否启用了数据生成
            self.is_device_generation_enabled(component_type, component_idx)
        else:
            self.storage_current_device_label.setText("未选择储能设备")
    
    def is_device_generation_enabled(self, component_type, component_idx):
        """检查指定设备是否启用了数据生成"""
        device_key = f"{component_type}_{component_idx}"
        return device_key in self.generated_devices
    
    # 删除潮流结果和短路结果选项卡创建方法
        
    def load_network_data(self):
        """加载网络数据到设备树"""
        if not self.network_model:
            return
            
        # 清除设备缓存，因为网络模型已变化
        if hasattr(self, 'modbus_manager') and self.modbus_manager:
            self.modbus_manager.clear_device_cache()
            
        # 使电表缓存失效，因为网络模型已变化
        self.invalidate_meter_cache()
            
        self.device_tree.clear()
        
        # 添加母线
        if not self.network_model.net.bus.empty:
            bus_root = QTreeWidgetItem(self.device_tree, ["母线", "分类", "-"])
            for idx, bus in self.network_model.net.bus.iterrows():
                bus_name = bus.get('name', f'Bus_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty and idx in self.network_model.net.res_bus.index else "未计算"
                bus_item = QTreeWidgetItem(bus_root, [f"Bus {idx}: {bus_name}", "母线", status])
                bus_item.setData(0, Qt.UserRole, ('bus', idx))
                
        # 添加线路
        if not self.network_model.net.line.empty:
            line_root = QTreeWidgetItem(self.device_tree, ["线路", "分类", "-"])
            for idx, line in self.network_model.net.line.iterrows():
                line_name = line.get('name', f'Line_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_line') and not self.network_model.net.res_line.empty and idx in self.network_model.net.res_line.index else "未计算"
                line_item = QTreeWidgetItem(line_root, [f"Line {idx}: {line_name}", "线路", status])
                line_item.setData(0, Qt.UserRole, ('line', idx))
                
        # 添加变压器
        if not self.network_model.net.trafo.empty:
            trafo_root = QTreeWidgetItem(self.device_tree, ["变压器", "分类", "-"])
            for idx, trafo in self.network_model.net.trafo.iterrows():
                trafo_name = trafo.get('name', f'Trafo_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_trafo') and not self.network_model.net.res_trafo.empty and idx in self.network_model.net.res_trafo.index else "未计算"
                trafo_item = QTreeWidgetItem(trafo_root, [f"Trafo {idx}: {trafo_name}", "变压器", status])
                trafo_item.setData(0, Qt.UserRole, ('trafo', idx))
                
        # 添加负载
        if not self.network_model.net.load.empty:
            load_root = QTreeWidgetItem(self.device_tree, ["负载", "分类", "-"])
            for idx, load in self.network_model.net.load.iterrows():
                load_name = load.get('name', f'Load_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_load') and not self.network_model.net.res_load.empty and idx in self.network_model.net.res_load.index else "未计算"
                load_item = QTreeWidgetItem(load_root, [f"Load {idx}: {load_name}", "负载", status])
                load_item.setData(0, Qt.UserRole, ('load', idx))
                
        # 添加发电机
        if not self.network_model.net.gen.empty:
            gen_root = QTreeWidgetItem(self.device_tree, ["发电机", "分类", "-"])
            for idx, gen in self.network_model.net.gen.iterrows():
                gen_name = gen.get('name', f'Gen_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_gen') and not self.network_model.net.res_gen.empty and idx in self.network_model.net.res_gen.index else "未计算"
                gen_item = QTreeWidgetItem(gen_root, [f"Gen {idx}: {gen_name}", "发电机", status])
                gen_item.setData(0, Qt.UserRole, ('gen', idx))
                
        # 添加光伏
        if not self.network_model.net.sgen.empty:
            sgen_root = QTreeWidgetItem(self.device_tree, ["光伏", "分类", "-"])
            for idx, sgen in self.network_model.net.sgen.iterrows():
                sgen_name = sgen.get('name', f'SGen_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_sgen') and not self.network_model.net.res_sgen.empty and idx in self.network_model.net.res_sgen.index else "未计算"
                sgen_item = QTreeWidgetItem(sgen_root, [f"SGen {idx}: {sgen_name}", "光伏", status])
                sgen_item.setData(0, Qt.UserRole, ('sgen', idx))
                
        # 添加外部电网
        if not self.network_model.net.ext_grid.empty:
            ext_grid_root = QTreeWidgetItem(self.device_tree, ["外部电网", "分类", "-"])
            for idx, ext_grid in self.network_model.net.ext_grid.iterrows():
                ext_grid_name = ext_grid.get('name', f'ExtGrid_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_ext_grid') and not self.network_model.net.res_ext_grid.empty and idx in self.network_model.net.res_ext_grid.index else "未计算"
                ext_grid_item = QTreeWidgetItem(ext_grid_root, [f"ExtGrid {idx}: {ext_grid_name}", "外部电网", status])
                ext_grid_item.setData(0, Qt.UserRole, ('ext_grid', idx))
                
        # 添加储能
        if not self.network_model.net.storage.empty:
            storage_root = QTreeWidgetItem(self.device_tree, ["储能", "分类", "-"])
            for idx, storage in self.network_model.net.storage.iterrows():
                storage_name = storage.get('name', f'Storage_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_storage') and not self.network_model.net.res_storage.empty and idx in self.network_model.net.res_storage.index else "未计算"
                storage_item = QTreeWidgetItem(storage_root, [f"Storage {idx}: {storage_name}", "储能", status])
                storage_item.setData(0, Qt.UserRole, ('storage', idx))
                
        # 添加电表
        if hasattr(self.network_model.net, 'measurement') and not self.network_model.net.measurement.empty:
            meter_root = QTreeWidgetItem(self.device_tree, ["电表", "分类", "-"])
            for idx, meter in self.network_model.net.measurement.iterrows():
                meter_name = meter.get('name', f'Meter_{idx}')
                element_type = meter.get('element_type', '未知')
                element_idx = meter.get('element', idx)
                status = "正常" if meter.get('in_service', True) else "离线"
                meter_item = QTreeWidgetItem(meter_root, [f"Meter {idx}: {meter_name} ({element_type}_{element_idx})", "电表", status])
                meter_item.setData(0, Qt.UserRole, ('meter', idx))
        
        # 展开所有节点
        self.device_tree.expandAll()
        
        # 更新设备统计
        self.update_device_stats()
        
    def on_device_selected(self, item, column):
        """设备树中选择设备时的处理"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
            
        component_type, component_idx = data
        self.selected_device_id = str(component_idx)
        self.selected_device_type = self.get_component_type_chinese(component_type)
        
        # 更新当前设备监控复选框状态
        device_key = f"{self.selected_device_type}_{self.selected_device_id}"
        self.current_device_monitor.setChecked(device_key in self.power_monitor.monitored_devices)
        
        # 显示组件详情
        self.show_component_details(component_type, component_idx)
        
    def show_component_details(self, component_type, component_idx):
        """显示组件详细信息"""
        if not self.network_model:
            return
            
        # 检查是否需要更新选项卡（只有在设备类型改变时才重新组织选项卡）
        need_update_tabs = not hasattr(self, 'current_component_type') or self.current_component_type != component_type
        
        # 记录当前显示的组件信息，用于自动更新
        self.current_component_type = component_type
        self.current_component_idx = component_idx
        
        # 只有在设备类型改变时才重新组织选项卡
        if need_update_tabs:
            # 首先移除所有设备专用选项卡
            self.remove_all_device_tabs()
            
            # 根据设备类型添加对应的专用选项卡
            if component_type == 'sgen':
                self.results_tabs.addTab(self.sgen_data_tab, "光伏控制")
            elif component_type == 'load':
                self.results_tabs.addTab(self.load_data_tab, "负载控制")
            elif component_type == 'storage':
                self.results_tabs.addTab(self.storage_data_tab, "储能控制")
        
        # 更新设备信息（每次都需要更新，因为可能是同类型的不同设备）
        if component_type == 'sgen':
            self.update_sgen_device_info(component_type, component_idx)
        elif component_type == 'load':
            self.update_load_device_info(component_type, component_idx)
        elif component_type == 'storage':
            self.update_storage_device_info(component_type, component_idx)
            
        try:
            # 获取组件数据
            component_data = None
            result_data = None
            
            if component_type == 'bus':
                component_data = self.network_model.net.bus.loc[component_idx]
                if hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty:
                    if component_idx in self.network_model.net.res_bus.index:
                        result_data = self.network_model.net.res_bus.loc[component_idx]
            elif component_type == 'line':
                component_data = self.network_model.net.line.loc[component_idx]
                if hasattr(self.network_model.net, 'res_line') and not self.network_model.net.res_line.empty:
                    if component_idx in self.network_model.net.res_line.index:
                        result_data = self.network_model.net.res_line.loc[component_idx]
            elif component_type == 'trafo':
                component_data = self.network_model.net.trafo.loc[component_idx]
                if hasattr(self.network_model.net, 'res_trafo') and not self.network_model.net.res_trafo.empty:
                    if component_idx in self.network_model.net.res_trafo.index:
                        result_data = self.network_model.net.res_trafo.loc[component_idx]
            elif component_type == 'load':
                component_data = self.network_model.net.load.loc[component_idx]
                if hasattr(self.network_model.net, 'res_load') and not self.network_model.net.res_load.empty:
                    if component_idx in self.network_model.net.res_load.index:
                        result_data = self.network_model.net.res_load.loc[component_idx]
            elif component_type == 'gen':
                component_data = self.network_model.net.gen.loc[component_idx]
                if hasattr(self.network_model.net, 'res_gen') and not self.network_model.net.res_gen.empty:
                    if component_idx in self.network_model.net.res_gen.index:
                        result_data = self.network_model.net.res_gen.loc[component_idx]
            elif component_type == 'sgen':
                component_data = self.network_model.net.sgen.loc[component_idx]
                if hasattr(self.network_model.net, 'res_sgen') and not self.network_model.net.res_sgen.empty:
                    if component_idx in self.network_model.net.res_sgen.index:
                        result_data = self.network_model.net.res_sgen.loc[component_idx]
            elif component_type == 'ext_grid':
                component_data = self.network_model.net.ext_grid.loc[component_idx]
                if hasattr(self.network_model.net, 'res_ext_grid') and not self.network_model.net.res_ext_grid.empty:
                    if component_idx in self.network_model.net.res_ext_grid.index:
                        result_data = self.network_model.net.res_ext_grid.loc[component_idx]
            elif component_type == 'storage':
                component_data = self.network_model.net.storage.loc[component_idx]
                if hasattr(self.network_model.net, 'res_storage') and not self.network_model.net.res_storage.empty:
                    if component_idx in self.network_model.net.res_storage.index:
                        result_data = self.network_model.net.res_storage.loc[component_idx]
            elif component_type == 'meter':
                # 电表设备特殊处理 - 显示测量结果
                component_data = None
                result_data = self.show_meter_measurement_details(component_idx)
            else:
                return
                
            # 填充参数表格（组合组件参数和仿真结果）
            all_params = {}
            
            # 先添加仿真结果（显示在最上方）
            if result_data is not None:
                for param, value in result_data.items():
                    all_params[f"结果_{param}"] = value
                    
            # 再添加组件参数
            if component_data is not None:
                for param, value in component_data.items():
                    all_params[f"参数_{param}"] = value
            
            self.component_params_table.setRowCount(len(all_params))
            for i, (param, value) in enumerate(all_params.items()):
                param_item = QTableWidgetItem(str(param))
                value_item = QTableWidgetItem(f"{value:.4f}" if isinstance(value, float) else str(value))
                
                # 为仿真结果设置不同的背景色
                if param.startswith("结果_"):
                    from PySide6.QtGui import QColor
                    param_item.setBackground(QColor(211, 211, 211))  # 浅灰色
                    value_item.setBackground(QColor(211, 211, 211))  # 浅灰色
                    
                self.component_params_table.setItem(i, 0, param_item)
                self.component_params_table.setItem(i, 1, value_item)
                
        except Exception as e:
            # 显示错误信息在状态栏
            self.parent_window.statusBar().showMessage(f"显示组件详情时出错: {str(e)}")

    def update_component_params_table(self):
        """更新组件参数表格 - 在自动计算时刷新当前显示的组件详情"""
        try:
            # 检查是否有当前选中的组件
            if hasattr(self, 'current_component_type') and hasattr(self, 'current_component_idx'):
                if self.current_component_type and self.current_component_idx is not None:
                    # 重新显示当前组件的详情，这会自动更新表格内容
                    self.show_component_details(self.current_component_type, self.current_component_idx)
        except Exception as e:
            print(f"更新组件参数表格时出错: {str(e)}")

    def show_meter_measurement_details(self, meter_idx):
        """显示电表设备的测量结果详情"""
        try:
            # 获取电表图形项
            meter_item = self.get_meter_item_by_type_and_id('meter', meter_idx)
            if not meter_item:
                return {"error": f"未找到电表设备: {meter_idx}"}
            
            # 获取电表属性
            properties = meter_item.properties
            
            # 获取测量参数
            element_type = properties.get('element_type', 'bus')
            element_idx = properties.get('element', 0)
            side = properties.get('side', None)
            
            # 获取实时测量值
            measurement_value = 0.0
            para = ""
            try:
                if element_type == 'load' and hasattr(self.network_model.net, 'res_load'):
                    if element_idx in self.network_model.net.res_load.index:
                        measurement_value = self.network_model.net.res_load.loc[element_idx, 'p_mw']
                        para = "p_mw"
                elif element_type == 'sgen' and hasattr(self.network_model.net, 'res_sgen'):
                    if element_idx in self.network_model.net.res_sgen.index:
                        measurement_value = self.network_model.net.res_sgen.loc[element_idx, 'p_mw']
                        para = "p_mw"
                elif element_type == 'storage' and hasattr(self.network_model.net, 'res_storage'):
                    if element_idx in self.network_model.net.res_storage.index:
                        measurement_value = self.network_model.net.res_storage.loc[element_idx, 'p_mw']
                        para = "p_mw"
                elif element_type == 'bus' and hasattr(self.network_model.net, 'res_bus'):  
                    if element_idx in self.network_model.net.res_bus.index:
                        measurement_value = self.network_model.net.res_bus.loc[element_idx, 'p_mw']
                        para = "p_mw"
                elif element_type == 'line' and hasattr(self.network_model.net, 'res_line'):
                    if element_idx in self.network_model.net.res_line.index:
                        if side == "from":
                            measurement_value = self.network_model.net.res_line.loc[element_idx, 'p_from_mw']
                            para = "p_from_mw"
                        elif side == "to":
                            measurement_value = self.network_model.net.res_line.loc[element_idx, 'p_to_mw']
                            para = "p_to_mw"
                elif element_type == 'trafo' and hasattr(self.network_model.net, 'res_trafo'):
                    if element_idx in self.network_model.net.res_trafo.index:
                        if side == "hv":
                            measurement_value = self.network_model.net.res_trafo.loc[element_idx, 'p_hv_mw']
                            para = "p_hv_mw"
                        elif side == "lv":
                            measurement_value = self.network_model.net.res_trafo.loc[element_idx, 'p_lv_mw']
                            para = "p_lv_mw"
            except Exception as e:
                return {"error": f"获取测量值时出错: {str(e)}"}
            
            # 构建返回字典
            result = {
                para: measurement_value,
            }
            
            return result
                
        except Exception as e:
            return {"error": f"获取电表详情时出错: {str(e)}"}

    def get_component_type_chinese(self, component_type):
        """获取组件类型的中文名称"""
        type_map = {
            'bus': '母线',
            'line': '线路', 
            'trafo': '变压器',
            'load': '负载',
            'gen': '发电机',
            'sgen': '光伏',
            'ext_grid': '外部电网',
            'storage': '储能',
            'meter': '电表'
        }
        return type_map.get(component_type, component_type)
            
    def filter_device_tree(self, text):
        """根据搜索文本过滤设备树"""
        def hide_items(item, text):
            """递归隐藏/显示项目"""
            match = text.lower() in item.text(0).lower()
            
            # 检查子项目
            child_match = False
            for i in range(item.childCount()):
                child = item.child(i)
                if hide_items(child, text):
                    child_match = True
            
            # 如果有匹配的子项目或自身匹配，则显示
            should_show = match or child_match or text == ""
            item.setHidden(not should_show)
            
            return should_show
        
        # 对根项目应用过滤
        for i in range(self.device_tree.topLevelItemCount()):
            root_item = self.device_tree.topLevelItem(i)
            hide_items(root_item, text)
    
    def clear_search(self):
        """清除搜索"""
        self.search_input.clear()
    
    def filter_by_category(self, category):
        """根据分类过滤设备"""
        category_map = {
            "全部设备": [],
            "母线": ["母线"],
            "线路": ["线路"],
            "变压器": ["变压器"],
            "发电设备": ["发电机", "光伏", "外部电网"],
            "负载设备": ["负载"],
            "储能设备": ["储能"],
            "测量设备": ["电表"]
        }
        
        show_categories = category_map.get(category, [])
        
        for i in range(self.device_tree.topLevelItemCount()):
            root_item = self.device_tree.topLevelItem(i)
            category_name = root_item.text(0)
            
            if category == "全部设备":
                root_item.setHidden(False)
            else:
                root_item.setHidden(category_name not in show_categories)
    
    def refresh_device_tree(self):
        """刷新设备树"""
        # 清除设备缓存，因为网络模型可能已变化
        if hasattr(self, 'modbus_manager') and self.modbus_manager:
            self.modbus_manager.clear_device_cache()
            
        self.load_network_data()
        self.search_input.clear()
        self.category_combo.setCurrentText("全部设备")
    
    def update_device_stats(self):
        """更新设备统计信息"""
        if not self.network_model:
            self.device_stats_label.setText("设备统计: 无网络模型")
            return
        
        stats = {
            "母线": len(self.network_model.net.bus),
            "线路": len(self.network_model.net.line),
            "变压器": len(self.network_model.net.trafo),
            "负载": len(self.network_model.net.load),
            "发电机": len(self.network_model.net.gen),
            "光伏": len(self.network_model.net.sgen),
            "外部电网": len(self.network_model.net.ext_grid),
            "储能": len(self.network_model.net.storage),
            "电表":len(self.network_model.net.measurement)
        }
        
        total = sum(stats.values())
        stats_text = f"设备统计: 总计 {total} 个设备 | "
        stats_text += " | ".join([f"{k}: {v}" for k, v in stats.items() if v > 0])
        
        self.device_stats_label.setText(stats_text)
    
    
    def closeEvent(self, event):
        """窗口关闭事件 - 增强内存清理"""
        try:
            # 停止所有定时器
            self.auto_calc_timer.stop()
            
            # 停止所有Modbus服务器
            if hasattr(self, 'modbus_manager'):
                self.modbus_manager.stop_all_modbus_servers()
                self.modbus_manager.clear_device_cache()
            
            # 清理数据生成器
            if hasattr(self, 'data_generator_manager'):
                self.data_generator_manager.stop_all_generators()
            
            # 清理功率监控
            if hasattr(self, 'power_monitor'):
                self.power_monitor.cleanup()
            
            # 清理缓存
            self._clear_all_caches()
            
            # 断开信号连接
            self._disconnect_all_signals()
            
            self.parent_window.statusBar().showMessage("已退出仿真模式")
            # self.clear_all_members()
            # 强制垃圾回收
            import gc
            gc.collect()
            
            
        except Exception as e:
            print(f"关闭仿真窗口时发生错误: {e}")
        finally:
            event.accept()
    def clear_all_members(self):
        """清空类中所有成员变量"""
        # 保留基本属性，清空其他所有
        keep_attrs = ['__class__', '__dict__', '__weakref__']
        
        for attr in list(self.__dict__.keys()):
            if attr not in keep_attrs:
                delattr(self, attr)
    def _clear_all_caches(self):
        """清理所有缓存"""
        # 清理各种缓存
        cache_attrs = [
            '_energy_cache', '_meter_cache', '_pv_cache', 
            '_storage_cache', '_charger_cache', 'generated_devices',
            'current_component_type', 'current_component_idx'
        ]
        
        for attr in cache_attrs:
            if hasattr(self, attr):
                cache = getattr(self, attr)
                if isinstance(cache, dict):
                    cache.clear()
                elif isinstance(cache, set):
                    cache.clear()
                elif isinstance(cache, list):
                    cache.clear()
                else:
                    setattr(self, attr, None)
    
    def _disconnect_all_signals(self):
        """断开所有信号连接"""
        try:
            # 断开定时器信号
            self.auto_calc_timer.timeout.disconnect()
        except Exception as e:
            print(f"断开自动潮流计算定时器信号时发生错误: {e}")
            pass
    
    def update_auto_calc_timer(self):
        """更新自动潮流计算定时器间隔"""
        if not self.network_model:
            QMessageBox.warning(self, "警告", "没有可用的网络模型")
            return
        
        if self.is_auto_calculating:
            # 重新启动定时器以应用新的间隔
            self.auto_calc_timer.stop()
            interval = self.calc_interval_spinbox.value() * 1000  # 转换为毫秒
            self.auto_calc_timer.start(interval)
            self.statusBar().showMessage(f"自动潮流计算间隔已更新为 {self.calc_interval_spinbox.value()} 秒")

    def toggle_calculation(self):
        """切换计算状态"""
        if not self.network_model:
            QMessageBox.warning(self, "警告", "没有可用的网络模型")
            self.start_calc_btn.setChecked(True)  # 恢复按钮状态
            return
            
        if self.start_calc_btn.isChecked():
            # 开始计算
            interval = self.calc_interval_spinbox.value() * 1000  # 转换为毫秒
            self.auto_calc_timer.start(interval)
            self.is_auto_calculating = True
            self.start_calc_btn.setText("停止仿真")
            self.calc_status_label.setText("仿真状态: 运行中")
            self.statusBar().showMessage("仿真已启动")
        else:
            # 停止计算
            self.auto_calc_timer.stop()
            self.is_auto_calculating = False
            self.start_calc_btn.setText("开始仿真")
            self.calc_status_label.setText("仿真状态: 已停止")
            self.statusBar().showMessage("仿真已停止")
    
    def power_on_all_devices(self):
        """上电所有设备 - 启动所有Modbus服务器"""
        try:
            if not self.network_model:
                QMessageBox.warning(self, "警告", "没有可用的网络模型")
                return
            
            # 首先验证IP和端口的唯一性
            is_valid, error_msg = self.parent_window.topology_manager.validate_ip_port_uniqueness(self.scene, self)
            if not is_valid:
                return
                
            # 启动所有Modbus服务器
            self.modbus_manager.start_all_modbus_servers()
            
            # 获取运行状态
            device_count = self.modbus_manager.get_device_count()
            running_services = self.modbus_manager.get_service_count()
            
            QMessageBox.information(
                self, 
                "上电成功", 
                f"已成功启动 {running_services} 个设备的Modbus服务器\n"
                f"总设备数: {device_count['total']}"
            )
            
            self.statusBar().showMessage(f"已上电 {running_services} 个设备")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"上电失败: {str(e)}")
            self.statusBar().showMessage("上电操作失败")
    
    def power_off_all_devices(self):
        """下电所有设备 - 停止所有Modbus服务器"""
        try:
            if not self.network_model:
                QMessageBox.warning(self, "警告", "没有可用的网络模型")
                return
                
            # 获取当前运行状态
            device_count = self.modbus_manager.get_device_count()
            running_count = device_count['running_services']
            
            # 停止所有Modbus服务器
            self.modbus_manager.stop_all_modbus_servers()
            
            QMessageBox.information(
                self, 
                "下电成功", 
                f"已成功停止 {running_count} 个设备的Modbus服务器"
            )
            
            self.statusBar().showMessage("所有设备已下电")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"下电失败: {str(e)}")
            self.statusBar().showMessage("下电操作失败")
    
    def check_and_reset_daily_data(self):
        """检查并执行每日数据重置"""
        try:
            from datetime import datetime
            current_date = datetime.now().date()
            
            # 检查是否需要每日重置
            if hasattr(self, 'last_reset_date') and current_date != self.last_reset_date:
                self.reset_daily_pv_energy()
                self.reset_daily_storage_energy()
                self.last_reset_date = current_date
                print(f"已重置所有设备的每日数据 - {current_date}")
            elif not hasattr(self, 'last_reset_date'):
                self.last_reset_date = current_date
        except Exception as e:
            print(f"每日数据重置检查失败: {str(e)}")

    def auto_power_flow_calculation(self):
        """自动潮流计算主方法"""
        try:
            if not self.network_model or not hasattr(self.network_model, 'net'):
                return
                
            # 性能监控：跳过计算如果上次计算未完成
            if hasattr(self, '_is_calculating') and self._is_calculating:
                return
            self._is_calculating = True
                
            # 检查每日重置
            self.check_and_reset_daily_data()
                
            # 使用批处理更新生成的数据
            if self.generated_devices:
                self._update_generated_data_batch(self.generated_devices, self.network_model, self.data_generator_manager)
                
            # 批量更新Modbus参数
            self._update_para_from_modbus_batch()
            
            # 运行潮流计算
            try:
                pp.runpp(self.network_model.net)
                self.statusBar().showMessage("潮流计算成功")
                
                # 批量更新能量统计
                self._update_energy_stats_batch()
                
                # 智能更新策略：仅在数据变化时更新UI
                if not hasattr(self, '_ui_update_counter'):
                    self._ui_update_counter = 0
                self._ui_update_counter += 1
                
                # 每3次计算更新一次设备树（约6秒一次）
                if self._ui_update_counter % 3 == 0:
                    self.update_device_tree_status()
                
                # 每2次计算更新一次功率曲线（约4秒一次）
                if self._ui_update_counter % 2 == 0:
                    self.power_monitor.update_power_curve()
                
                # 仅在选择设备且有变化时更新参数表格
                if (hasattr(self, 'current_component_type') and 
                    self.current_component_type and 
                    self._ui_update_counter % 4 == 0):
                    self.update_component_params_table()
                
                # 批量更新Modbus数据
                self.modbus_manager.update_all_modbus_data()
                    
            except Exception as e:
                self.statusBar().showMessage(f"潮流计算失败: {str(e)}")
                return  # 潮流计算失败，跳过后续数据更新操作
                
        except Exception as e:
            print(f"自动潮流计算错误: {str(e)}")
            self.statusBar().showMessage("自动潮流计算发生错误")
        finally:
            # 重置计算状态标志
            if hasattr(self, '_is_calculating'):
                self._is_calculating = False
    


    def _update_energy_stats_batch(self):
        """批量更新能量统计信息 - 优化版本"""
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                return
                
            # 计算时间间隔（使用定时器中的实际值）
            timer_interval_ms = self.auto_calc_timer.interval()
            time_interval_hours = timer_interval_ms / (1000.0 * 3600.0)  # 毫秒转小时
            
            # 使用缓存机制避免重复遍历
            if not hasattr(self, '_energy_cache'):
                self._energy_cache = {
                    'pv_items': {},
                    'storage_items': {},
                    'last_update': 0
                }
            
            # 每5秒更新一次缓存
            current_time = time.time()
            if current_time - self._energy_cache['last_update'] > 5:
                self._energy_cache['pv_items'].clear()
                self._energy_cache['storage_items'].clear()
                
                for item in self.canvas.scene.items():
                    if hasattr(item, 'component_type'):
                        if item.component_type == 'static_generator':
                            self._energy_cache['pv_items'][item.component_index] = item
                        elif item.component_type == 'storage':
                            self._energy_cache['storage_items'][item.component_index] = item
                
                self._energy_cache['last_update'] = current_time
            
            # 批量更新光伏能量统计
            if self._energy_cache['pv_items'] and hasattr(self.network_model, 'net'):
                valid_pv_indices = [idx for idx in self._energy_cache['pv_items'].keys() 
                                  if idx in self.network_model.net.sgen.index]
                
                for device_idx in valid_pv_indices:
                    try:
                        pv_item = self._energy_cache['pv_items'][device_idx]
                        current_power_mw = abs(self.network_model.net.sgen.at[device_idx, 'p_mw'])
                        
                        # 计算本次产生的能量（kWh）
                        energy_generated_kwh = current_power_mw * time_interval_hours * 1000
                        
                        # 更新今日发电量和总发电量
                        pv_item.today_discharge_energy += energy_generated_kwh
                        pv_item.total_discharge_energy += energy_generated_kwh
                        
                    except Exception as e:
                        print(f"批量更新光伏设备 {device_idx} 能量统计时出错: {e}")
            
            # 批量更新储能能量统计
            if self._energy_cache['storage_items'] and hasattr(self.network_model, 'net'):
                valid_storage_indices = [idx for idx in self._energy_cache['storage_items'].keys() 
                                       if idx in self.network_model.net.storage.index]
                
                for device_idx in valid_storage_indices:
                    try:
                        storage_item = self._energy_cache['storage_items'][device_idx]
                        current_power_mw = self.network_model.net.storage.at[device_idx, 'p_mw']
                        
                        # 调用StorageItem的实时数据更新方法
                        storage_item.update_realtime_data(current_power_mw, time_interval_hours)
                        
                    except Exception as e:
                        print(f"批量更新储能设备 {device_idx} 能量统计时出错: {e}")
                        
        except Exception as e:
            print(f"批量更新能量统计失败: {str(e)}")
            
    def reset_daily_storage_energy(self):
        """重置储能设备的每日能量统计"""
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                return
                
            # 获取当前场景中的所有储能设备
            storage_items = []
            for item in self.canvas.scene.items():
                if hasattr(item, 'component_type') and item.component_type == 'storage':
                    storage_items.append(item)
            
            # 遍历所有储能设备，重置每日数据
            for storage_item in storage_items:
                storage_item.reset_daily_energy()
                
        except Exception as e:
            print(f"重置储能设备每日能量统计失败: {str(e)}")



    def _update_para_from_modbus_batch(self):
        """
        从Modbus寄存器读取数据并更新设备参数
        
        支持储能、充电桩和光伏系统的完整Modbus数据更新：
        - 储能设备：开关机状态、功率设定值、SOC控制
        - 充电桩：功率设定值、充电状态
        - 光伏系统：功率设定值、启停控制
        """
        try:
            if not hasattr(self, 'modbus_manager') or not self.modbus_manager:
                return
                
            if not self.network_model or not hasattr(self.network_model, 'net'):
                return
                
            # 获取所有正在运行的Modbus设备
            running_devices = list(self.modbus_manager.running_services)
            if not running_devices:
                return
            
            # 批量收集各类型设备更新数据
            storage_updates = []
            charger_updates = []
            sgen_updates = []
            
            for device_key in running_devices:
                device_type, device_idx_str = device_key.rsplit('_', 1)
                device_idx = int(device_idx_str)
                
                # 获取设备的Modbus上下文
                slave_context = self.modbus_manager.modbus_contexts.get(device_key)
                if not slave_context:
                    continue
                
                try:
                    if device_type == 'storage':
                        # 储能设备数据收集
                        update_data = self._collect_storage_modbus_data(device_idx, slave_context)
                        if update_data:
                            storage_updates.append((device_idx, update_data))
                    
                    elif device_type == 'load':
                        # 充电桩设备数据收集（负荷类型中的充电桩）
                        update_data = self._collect_charger_modbus_data(device_idx, slave_context)
                        if update_data:
                            charger_updates.append((device_idx, update_data))
                    
                    elif device_type == 'sgen':
                        # 光伏系统数据收集
                        update_data = self._collect_sgen_modbus_data(device_idx, slave_context)
                        if update_data:
                            sgen_updates.append((device_idx, update_data))
                            
                except Exception as e:
                    print(f"收集设备 {device_key} 参数失败: {e}")
            
            # 批量应用各类型设备更新
            if storage_updates:
                self._apply_storage_updates_batch(storage_updates)
            
            if charger_updates:
                self._apply_charger_updates_batch(charger_updates)
                
            if sgen_updates:
                self._apply_sgen_updates_batch(sgen_updates)
                    
        except Exception as e:
            print(f"Modbus参数批量更新失败: {str(e)}")

    def _collect_storage_modbus_data(self, device_idx, slave_context):
        """收集单个储能设备的Modbus数据
        
        储能设备保持寄存器功能：
        - 寄存器0：功率设定值 (kW)
        - 寄存器55：开关机控制 (布尔值)
        """
        try:
            # 读取功率设定值（寄存器0）
            try:
                power_setpoint = slave_context.getValues(4, 0, 1)[0]
                power_setpoint = power_setpoint / 1000.0  # kW -> MW
            except (IndexError, ValueError, AttributeError):
                power_setpoint = None
                
            # 读取开关机状态（寄存器55）
            try:
                power_on = slave_context.getValues(4, 55, 1)[0]
                power_on = bool(power_on)
            except (IndexError, ValueError, AttributeError):
                power_on = False
            
            return {
                'power_on': power_on,
                'power_setpoint': power_setpoint
            }
            
        except Exception as e:
            print(f"收集储能设备 {device_idx} 数据失败: {e}")
            return None
            
    def _collect_charger_modbus_data(self, device_idx, slave_context):
        """Collect power limit information from the holding register at address 0 for a single charging pile device"""
        try:
            # Read power limit value (register 0)
            try:
                power_limit = slave_context.getValues(4, 0, 1)[0]
                power_limit = power_limit / 1000.0  # Convert kW to MW
            except (IndexError, ValueError, AttributeError):
                power_limit = None
                
            return {
                'power_limit': power_limit
            }
            
        except Exception as e:
            print(f"Failed to collect power limit data for charging pile device {device_idx}: {e}")
            return None
            
    def _collect_sgen_modbus_data(self, device_idx, slave_context):
        """收集单个光伏系统的Modbus数据
        
        光伏系统保持寄存器功能：
        - 寄存器5005：开关机控制 (0=关机, 1=开机)
        - 寄存器5038：有功功率限制 (kW单位)
        - 寄存器5007：有功功率百分比限制 (0-100%)
        """
        try:
            # 读取开关机状态（寄存器5005）
            try:
                power_on = slave_context.getValues(4, 5005, 1)[0]
                power_on = bool(power_on)
            except (IndexError, ValueError, AttributeError):
                power_on = True  # 默认启用
                
            # 读取有功功率限制（寄存器5038）
            try:
                power_limit_kw = slave_context.getValues(4, 5038, 1)[0]
                power_limit_mw = power_limit_kw / 1000.0  # kW -> MW
            except (IndexError, ValueError, AttributeError):
                power_limit_mw = None
                
            # 读取有功功率百分比限制（寄存器5007）
            try:
                power_percent_limit = slave_context.getValues(4, 5007, 1)[0]
                power_percent_limit = min(100, max(0, power_percent_limit))  # 限制在0-100%
            except (IndexError, ValueError, AttributeError):
                power_percent_limit = None
            
            return {
                'power_on': power_on,
                'power_limit_mw': power_limit_mw,
                'power_percent_limit': power_percent_limit
            }
            
        except Exception as e:
            print(f"收集光伏系统 {device_idx} 数据失败: {e}")
            return None

    def _apply_storage_updates_batch(self, storage_updates):
        """批量应用储能设备更新"""
        try:
            # 预获取所有储能图形项，避免重复遍历
            if not hasattr(self, '_storage_items_cache'):
                self._storage_items_cache = {}
            
            # 更新缓存（如果需要）
            if not self._storage_items_cache or self._storage_items_cache.get('_last_update', 0) < time.time() - 5:
                self._storage_items_cache.clear()
                for item in self.canvas.scene.items():
                    if hasattr(item, 'component_type') and item.component_type == 'storage':
                        self._storage_items_cache[item.component_index] = item
                self._storage_items_cache['_last_update'] = time.time()
            
            # 批量应用更新
            for device_idx, update_data in storage_updates:
                storage_item = self._storage_items_cache.get(device_idx)
                if not storage_item:
                    continue
                    
                power_on = update_data['power_on']
                
                # 更新开关机状态，根据实际功率判断充放电状态
                if power_on:
                    storage_item.state = 'ready'  # 默认状态
                else:
                    storage_item.state = 'halt'
                    
                # 更新功率设定值到网络模型
                if update_data['power_setpoint'] is not None:
                    try:
                        #TODO: 数据生成模式\手动控制模式\modbus控制模式,三种模式互斥,不能同时修改网络模型中设备的功率
                        self.network_model.net.storage.loc[device_idx, 'p_mw'] = update_data['power_setpoint']
                    except (KeyError, IndexError):
                        pass
                        
        except Exception as e:
            print(f"批量应用储能更新失败: {e}")
            
    def _apply_charger_updates_batch(self, charger_updates):
        """批量应用充电桩设备功率限制更新"""
        try:
            # 预获取所有充电桩图形项
            if not hasattr(self, '_charger_items_cache'):
                self._charger_items_cache = {}
            
            # 更新缓存
            if not self._charger_items_cache or self._charger_items_cache.get('_last_update', 0) < time.time() - 5:
                self._charger_items_cache.clear()
                for item in self.canvas.scene.items():
                    if hasattr(item, 'component_type') and item.component_type == 'load':
                        # 假设负荷类型中的充电桩有特殊标识
                        self._charger_items_cache[item.component_index] = item
                self._charger_items_cache['_last_update'] = time.time()
            
            # 批量应用更新
            for device_idx, update_data in charger_updates:
                charger_item = self._charger_items_cache.get(device_idx)
                if not charger_item:
                    continue
                
                power_limit = update_data['power_limit']
                
                # 更新充电桩功率限制
                if power_limit is not None:
                    try:
                        self.network_model.net.load.loc[device_idx, 'p_mw'] = power_limit
                    except (KeyError, IndexError):
                        pass
                        
        except Exception as e:
            print(f"批量应用充电桩功率限制更新失败: {e}")
            
    def _apply_sgen_updates_batch(self, sgen_updates):
        """批量应用光伏系统更新"""
        try:
            # 预获取所有光伏图形项
            if not hasattr(self, '_sgen_items_cache'):
                self._sgen_items_cache = {}
            
            # 更新缓存
            if not self._sgen_items_cache or self._sgen_items_cache.get('_last_update', 0) < time.time() - 5:
                self._sgen_items_cache.clear()
                for item in self.canvas.scene.items():
                    if hasattr(item, 'component_type') and item.component_type == 'static_generator':
                        self._sgen_items_cache[item.component_index] = item
                self._sgen_items_cache['_last_update'] = time.time()
            
            # 批量应用更新
            for device_idx, update_data in sgen_updates:
                sgen_item = self._sgen_items_cache.get(device_idx)
                if not sgen_item:
                    continue
                
                power_on = update_data['power_on']
                power_limit_mw = update_data['power_limit_mw']
                power_percent_limit = update_data['power_percent_limit']
                
                # 获取光伏设备的额定功率
                try:
                    rated_power_mw = self.network_model.net.sgen.loc[device_idx, 'p_mw']
                except (KeyError, IndexError):
                    rated_power_mw = 0.0
                
                # 计算最终功率值
                final_power = 0.0
                
                if power_on:
                    # 根据功率限制模式计算最终功率
                    if power_limit_mw is not None:
                        # 使用绝对功率限制
                        final_power = power_limit_mw
                    elif power_percent_limit is not None:
                        # 使用百分比功率限制
                        final_power = rated_power_mw * (power_percent_limit / 100.0)
                    else:
                        # 无限制，使用额定功率
                        final_power = rated_power_mw
                
                # 更新光伏功率到网络模型
                try:
                    self.network_model.net.sgen.loc[device_idx, 'p_mw'] = final_power
                except (KeyError, IndexError):
                    pass
                    
        except Exception as e:
            print(f"批量应用光伏系统更新失败: {e}")

    def _update_generated_data_batch(self, generated_devices, network_model, data_generator_manager):
        """
        批量更新生成的设备数据 - 优化版本
        
        Args:
            generated_devices (list): 生成的设备列表，格式为['type_idx', ...]
            network_model: 网络模型对象
            data_generator_manager: 数据生成器管理器
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            if not network_model or not hasattr(network_model, 'net'):
                return False
                
            # 批量收集需要更新的设备
            load_updates = {}
            sgen_updates = {}
            
            for device in generated_devices:
                device_type, device_idx_str = device.split('_', 1)
                device_idx = int(device_idx_str)
                
                if device_type == 'load' and device_idx in network_model.net.load.index:
                    load_data = data_generator_manager.generate_device_data('load', device_idx, network_model)
                    if device_idx in load_data:
                        load_updates[device_idx] = load_data[device_idx]
                        
                elif device_type == 'sgen' and device_idx in network_model.net.sgen.index:
                    sgen_data = data_generator_manager.generate_device_data('sgen', device_idx, network_model)
                    if device_idx in sgen_data:
                        sgen_updates[device_idx] = sgen_data[device_idx]
            
            # 批量更新负载数据
            if load_updates:
                for device_idx, values in load_updates.items():
                    network_model.net.load.loc[device_idx, 'p_mw'] = values['p_mw']
                    network_model.net.load.loc[device_idx, 'q_mvar'] = values['q_mvar']
            
            # 批量更新光伏数据
            if sgen_updates:
                for device_idx, values in sgen_updates.items():
                    network_model.net.sgen.loc[device_idx, 'p_mw'] = values['p_mw']
                    network_model.net.sgen.loc[device_idx, 'q_mvar'] = values['q_mvar']
            
            return True
            
        except Exception as e:
            print(f"批量更新设备数据失败: {str(e)}")
            return False

    def get_meter_item_by_type_and_id(self, device_type, device_id):
        """根据设备类型和ID获取对应的电表项
        
        Args:
            device_type (str): 设备类型，如 'meter'
            device_id (int): 设备ID
            
        Returns:
            object: 对应的电表图形项对象，如果未找到返回None
        """
        try:
            if device_type != 'meter' or not hasattr(self, 'canvas') or not self.canvas:
                return None
                
            # 使用缓存避免重复遍历
            if not hasattr(self, '_meter_cache'):
                self._build_meter_cache()
            
            return self._meter_cache.get(device_id)
            
        except Exception as e:
            print(f"获取电表项失败: {str(e)}")
            return None
    
    def _build_meter_cache(self):
        """构建电表项缓存，避免重复遍历画布"""
        self._meter_cache = {}
        if not hasattr(self, 'canvas') or not self.canvas or not self.canvas.scene:
            return
            
        try:
            for item in self.canvas.scene.items():
                if (hasattr(item, 'component_type') and 
                    item.component_type == 'meter' and 
                    hasattr(item, 'component_index')):
                    self._meter_cache[item.component_index] = item
        except Exception as e:
            print(f"构建电表缓存失败: {str(e)}")
            self._meter_cache = {}
    
    def invalidate_meter_cache(self):
        """使电表缓存失效，当画布内容变化时调用"""
        if hasattr(self, '_meter_cache'):
            delattr(self, '_meter_cache')

    def update_device_tree_status(self):
        """更新设备树状态"""
        try:
            if not hasattr(self.network_model.net, 'res_bus') or self.network_model.net.res_bus.empty:
                return
                
            # 预加载所有结果索引，避免重复访问
            if not hasattr(self, '_device_status_cache'):
                self._device_status_cache = {}
            
            # 批量获取所有结果索引
            net = self.network_model.net
            result_indices = {
                'bus': set(net.res_bus.index) if net.res_bus is not None else set(),
                'line': set(net.res_line.index) if net.res_line is not None else set(),
                'trafo': set(net.res_trafo.index) if net.res_trafo is not None else set(),
                'load': set(net.res_load.index) if net.res_load is not None else set(),
                'gen': set(net.res_gen.index) if net.res_gen is not None else set(),
                'sgen': set(net.res_sgen.index) if net.res_sgen is not None else set(),
                'ext_grid': set(net.res_ext_grid.index) if net.res_ext_grid is not None else set(),
                'storage': set(net.res_storage.index) if net.res_storage is not None else set()
            }
            
            # 批量更新所有项目
            root = self.device_tree.invisibleRootItem()
            
            def update_item_status_optimized(item):
                """优化后的状态更新函数"""
                if not item:
                    return
                    
                data = item.data(0, Qt.UserRole)
                if data:
                    device_type, device_id = data
                    
                    # 处理电表类型
                    if device_type == 'meter':
                        meter_item = self.get_meter_item_by_type_and_id(device_type, device_id)
                        device_type = meter_item.properties['element_type']
                        device_id = meter_item.properties['element']

                    # 快速检查其他设备状态
                    if device_type in result_indices and device_id in result_indices[device_type]:
                        item.setText(2, "正常")
                        item.setForeground(2, QColor("green"))
                    else:
                        item.setText(2, "异常")
                        item.setForeground(2, QColor("red"))
                
                # 批量递归更新子项
                child_count = item.childCount()
                for i in range(child_count):
                    update_item_status_optimized(item.child(i))
            
            # 批量更新所有根项
            root_count = root.childCount()
            for i in range(root_count):
                update_item_status_optimized(root.child(i))
                
        except Exception as e:
            print(f"更新设备树状态失败: {str(e)}")

    def reset_daily_pv_energy(self):
        """重置所有光伏设备的日发电量"""
        try:
            if not hasattr(self, 'canvas') or not self.canvas:
                return
                
            # 获取当前场景中的所有光伏设备
            pv_items = []
            for item in self.canvas.scene.items():
                if hasattr(item, 'component_type') and item.component_type == 'static_generator':
                    pv_items.append(item)
            
            # 重置每个光伏设备的今日发电量
            for pv_item in pv_items:
                pv_item.today_discharge_energy = 0.0
                
            print("已重置所有光伏设备的日发电量")
            
        except Exception as e:
            print(f"重置光伏日发电量失败: {str(e)}")
