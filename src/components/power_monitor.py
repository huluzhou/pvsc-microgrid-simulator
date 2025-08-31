#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
功率曲线监控模块
负责管理设备功率数据的收集、存储和可视化显示
"""

import time
from collections import deque
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem


class PowerMonitor:
    """功率曲线监控管理器"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.network_model = parent_window.network_model
        
        # 功率监控相关属性
        self.power_history = {}  # 存储多个设备的功率历史数据 {device_key: deque}
        self.monitored_devices = set()  # 存储要监控的设备集合
        self.device_colors = {}  # 存储设备对应的颜色
        self.color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                             '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # 获取UI组件引用 - 延迟初始化，避免在parent_window完全初始化前访问
        self.ax = None
        self.canvas = None
        # UI组件将在parent_window初始化后设置
        self.current_device_monitor = None
        self.monitored_devices_list = None
    
    def initialize_ui_components(self):
        """初始化UI组件引用，在parent_window完全初始化后调用"""
        if hasattr(self.parent_window, 'ax'):
            self.ax = self.parent_window.ax
        if hasattr(self.parent_window, 'canvas_mpl'):
            self.canvas = self.parent_window.canvas_mpl
    
    def get_device_power(self, device_id, device_type):
        """获取设备的实际功率属性值"""
        try:
            device_id = int(device_id)  # 确保device_id是整数
            
            # 根据设备类型从潮流计算结果中获取功率值
            if device_type == "母线":
                # 母线本身不直接设置功率，但可以通过潮流计算结果获取总注入功率
                if hasattr(self.network_model.net, 'res_bus') and device_id in self.network_model.net.res_bus.index:
                    # 获取该母线的总注入功率（发电减负荷）
                    return abs(self.network_model.net.res_bus.loc[device_id, 'p_mw'])
                else:
                    return 0.0
                
            elif device_type == "线路":
                # 从线路潮流计算结果中获取功率
                if hasattr(self.network_model.net, 'res_line') and device_id in self.network_model.net.res_line.index:
                    # 获取线路的有功功率（取两端功率的平均值或较大值）
                    p_from = abs(self.network_model.net.res_line.loc[device_id, 'p_from_mw'])
                    p_to = abs(self.network_model.net.res_line.loc[device_id, 'p_to_mw'])
                    return max(p_from, p_to)  # 返回较大的功率值
                else:
                    return 0.0
                    
            elif device_type == "变压器":
                # 从变压器潮流计算结果中获取功率
                if hasattr(self.network_model.net, 'res_trafo') and device_id in self.network_model.net.res_trafo.index:
                    # 获取变压器的有功功率
                    p_hv = abs(self.network_model.net.res_trafo.loc[device_id, 'p_hv_mw'])
                    p_lv = abs(self.network_model.net.res_trafo.loc[device_id, 'p_lv_mw'])
                    return max(p_hv, p_lv)
                else:
                    return 0.0
                    
            elif device_type == "发电机":
                # 从发电机潮流计算结果中获取实际功率
                if hasattr(self.network_model.net, 'res_gen') and device_id in self.network_model.net.res_gen.index:
                    return abs(self.network_model.net.res_gen.loc[device_id, 'p_mw'])
                else:
                    # 如果潮流计算结果没有，使用设定值
                    gens = self.network_model.net.gen
                    if device_id in gens.index:
                        return abs(gens.loc[device_id, 'p_mw'])
                    return 0.0
                    
            elif device_type == "光伏":
                # 从光伏潮流计算结果中获取实际功率
                if hasattr(self.network_model.net, 'res_sgen') and device_id in self.network_model.net.res_sgen.index:
                    return abs(self.network_model.net.res_sgen.loc[device_id, 'p_mw'])
                else:
                    # 使用设定值
                    sgens = self.network_model.net.sgen
                    if device_id in sgens.index:
                        return abs(sgens.loc[device_id, 'p_mw'])
                    return 0.0
                    
            elif device_type == "负载":
                # 从负载潮流计算结果中获取实际功率
                if hasattr(self.network_model.net, 'res_load') and device_id in self.network_model.net.res_load.index:
                    return abs(self.network_model.net.res_load.loc[device_id, 'p_mw'])
                else:
                    # 使用设定值
                    loads = self.network_model.net.load
                    if device_id in loads.index:
                        return abs(loads.loc[device_id, 'p_mw'])
                    return 0.0
                    
            elif device_type == "储能":
                # 从储能潮流计算结果中获取实际功率
                if hasattr(self.network_model.net, 'res_storage') and device_id in self.network_model.net.res_storage.index:
                    return abs(self.network_model.net.res_storage.loc[device_id, 'p_mw'])
                else:
                    # 使用设定值
                    storage = self.network_model.net.storage
                    if device_id in storage.index:
                        return abs(storage.loc[device_id, 'p_mw'])
                    return 0.0
                    
            elif device_type == "外部电网":
                # 从外部电网潮流计算结果中获取功率
                if hasattr(self.network_model.net, 'res_ext_grid') and device_id in self.network_model.net.res_ext_grid.index:
                    return abs(self.network_model.net.res_ext_grid.loc[device_id, 'p_mw'])
                else:
                    return 0.0
                    
        except Exception as e:
            print(f"获取设备功率失败: {str(e)}")
        
        return 0.0
    
    def update_power_curve(self):
        """更新所有监控设备的功率曲线数据"""
        try:
            # 为每个监控的设备更新功率数据
            for device_key in self.monitored_devices:
                try:
                    device_type, device_id = device_key.split('_', 1)
                    power_value = self.get_device_power(device_id, device_type)
                    
                    if power_value is not None:
                        timestamp = time.time()
                        
                        # 如果该设备的历史数据不存在，创建新的deque
                        if device_key not in self.power_history:
                            self.power_history[device_key] = deque(maxlen=100)
                        
                        # 添加历史数据
                        self.power_history[device_key].append((timestamp, power_value))
                        
                except Exception as e:
                    print(f"更新设备 {device_key} 功率数据失败: {str(e)}")
            
            # 更新图像显示
            self.display_power_curve()
            
        except Exception as e:
            print(f"更新功率曲线失败: {str(e)}")
    
    def display_power_curve(self):
        """显示多条功率曲线 - 支持同时监控多个设备"""
        try:
            # 确保ax已初始化
            if self.ax is None:
                self.initialize_ui_components()
            if self.ax is None:
                return
                
            # 清空当前图表
            self.ax.clear()
            
            # 如果没有监控的设备，显示提示信息
            if not self.monitored_devices or not self.power_history:
                self.ax.text(0.5, 0.5, "等待数据收集...\n\n1. 在设备树中选择设备\n2. 勾选\"监控当前设备\"\n3. 启用自动计算功能\n4. 数据将实时显示", 
                             transform=self.ax.transAxes, ha='center', va='center', 
                             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7),
                             fontsize=12)
                self.ax.set_xlabel('时间 (秒)', fontsize=12)
                self.ax.set_ylabel('功率 (MW)', fontsize=12)
                self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
                if hasattr(self, 'canvas') and self.canvas:
                     self.canvas.draw()
                elif hasattr(self.parent_window, 'canvas_mpl'):
                     self.parent_window.canvas_mpl.draw()
                return
            
            all_powers = []
            
            # 获取所有设备的时间戳，找到最早的时间
            all_timestamps = []
            for device_key, history in self.power_history.items():
                if device_key in self.monitored_devices and history:
                    all_timestamps.extend([item[0] for item in history])
            
            if not all_timestamps:
                return
                
            start_time = min(all_timestamps)
            
            # 为每个监控的设备绘制曲线
            for device_key in self.monitored_devices:
                if device_key in self.power_history and self.power_history[device_key]:
                    history = self.power_history[device_key]
                    timestamps = [item[0] for item in history]
                    powers = [item[1] for item in history]
                    
                    # 转换为相对时间（秒）
                    relative_times = [t - start_time for t in timestamps]
                    
                    # 获取设备类型和ID
                    device_type, device_id = device_key.split('_', 1)
                    
                    # 使用预定义的颜色或生成新颜色
                    if device_key not in self.device_colors:
                        color_index = len(self.device_colors) % len(self.color_palette)
                        self.device_colors[device_key] = self.color_palette[color_index]
                    
                    color = self.device_colors[device_key]
                    
                    # 绘制功率曲线
                    self.ax.plot(relative_times, powers, color=color, linewidth=2,
                                label=f'{device_type} {device_id}')
                    
                    all_powers.extend(powers)
            
            # 设置图表属性
            self.ax.set_xlabel('时间 (秒)', fontsize=12)
            self.ax.set_ylabel('功率 (MW)', fontsize=12)
            self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
            self.ax.grid(True, alpha=0.3)
            
            # 自动调整Y轴范围
            if all_powers:
                min_power = min(all_powers)
                max_power = max(all_powers)
                padding = max((max_power - min_power) * 0.1, 0.1)
                self.ax.set_ylim(max(0, min_power - padding), max_power + padding)
            else:
                self.ax.set_ylim(0, 1)
            
            # 显示图例
            if len(self.monitored_devices) > 0:
                self.ax.legend()
            
            # 刷新图表
            if hasattr(self, 'canvas') and self.canvas:
                 self.canvas.draw()
            elif hasattr(self.parent_window, 'canvas_mpl'):
                 self.parent_window.canvas_mpl.draw()
            
        except Exception as e:
            self.ax.clear()
            self.ax.text(0.5, 0.5, f"显示功率曲线失败: {str(e)}", 
                         transform=self.ax.transAxes, ha='center', va='center', 
                         bbox=dict(boxstyle='round', facecolor='red', alpha=0.5))
            if hasattr(self, 'canvas') and self.canvas:
                 self.canvas.draw()
            elif hasattr(self.parent_window, 'canvas_mpl'):
                 self.parent_window.canvas_mpl.draw()
            print(f"显示功率曲线失败: {str(e)}")
    
    def toggle_current_device_monitor(self, state):
        """切换当前设备监控状态"""
        if not self.parent_window.selected_device_id or not self.parent_window.selected_device_type:
            return
            
        device_key = f"{self.parent_window.selected_device_type}_{self.parent_window.selected_device_id}"
        
        if state == 2:  # 选中状态
            if device_key not in self.monitored_devices:
                self.monitored_devices.add(device_key)
                self.update_monitored_devices_list()
        else:  # 未选中状态
            if device_key in self.monitored_devices:
                self.monitored_devices.remove(device_key)
                self.update_monitored_devices_list()
                
        # 更新图表显示
        self.display_power_curve()
    
    def on_monitored_device_toggled(self, item, column):
        """监控设备列表中的复选框状态改变"""
        if column == 0:  # 第一列是复选框
            device_key = item.data(0, Qt.UserRole)
            if item.checkState(0) == Qt.Checked:
                if device_key not in self.monitored_devices:
                    self.monitored_devices.add(device_key)
            else:
                if device_key in self.monitored_devices:
                    self.monitored_devices.remove(device_key)
            
            # 更新当前设备监控复选框状态
            current_device_key = f"{self.parent_window.selected_device_type}_{self.parent_window.selected_device_id}" if self.parent_window.selected_device_type and self.parent_window.selected_device_id else ""
            if current_device_key and hasattr(self.parent_window, 'current_device_monitor'):
                self.parent_window.current_device_monitor.setChecked(current_device_key in self.monitored_devices)
            
            # 更新图表显示
            self.display_power_curve()
    
    def update_monitored_devices_list(self):
        """更新监控设备列表"""
        if hasattr(self.parent_window, 'monitored_devices_list'):
            self.parent_window.monitored_devices_list.clear()
        
        for device_key in self.monitored_devices:
            try:
                device_type, device_id = device_key.split('_', 1)
                
                # 创建列表项
                if hasattr(self.parent_window, 'monitored_devices_list'):
                    item = QTreeWidgetItem(self.parent_window.monitored_devices_list)
                    item.setText(0, str(device_id))
                    item.setText(1, str(device_type))
                    item.setText(2, "监控中")
                    item.setData(0, Qt.UserRole, device_key)
                    item.setCheckState(0, Qt.Checked)
                
            except Exception as e:
                print(f"更新监控设备列表失败: {str(e)}")
    
    def clear_all_monitors(self):
        """清除所有监控设备"""
        self.monitored_devices.clear()
        self.device_colors.clear()
        self.update_monitored_devices_list()
        
        # 更新当前设备监控复选框状态
        if hasattr(self.parent_window, 'current_device_monitor'):
            self.parent_window.current_device_monitor.setChecked(False)
        
        # 更新图表显示
        self.display_power_curve()