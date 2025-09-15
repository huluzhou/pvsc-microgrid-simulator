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
        """初始化功率监控器"""
        self.parent_window = parent_window
        self.network_model = parent_window.network_model
        self.power_history = {}  # 存储功率历史数据
        self.monitored_devices = set()  # 存储需要监控的设备
        self.device_colors = {}  # 存储设备对应的颜色
        self.ax = None
        self.canvas = None
        
        # 性能优化：添加更新计时器
        self._update_timer = None
        self._batch_update_pending = False
        
        # 颜色配置
        self.color_palette = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
            '#FECA57', '#FF9FF3', '#54A0FF', '#5F27CD'
        ]
    
    def schedule_curve_update(self):
        """延迟更新图表，避免频繁重绘"""
        if self._update_timer is None:
            from PySide6.QtCore import QTimer
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._perform_batch_update)
        
        # 重置计时器，延迟100ms后更新
        self._update_timer.stop()
        self._update_timer.start(100)
        self._batch_update_pending = True
    
    def _perform_batch_update(self):
        """执行批量更新"""
        if self._batch_update_pending:
            self.display_power_curve()
            self._batch_update_pending = False
    
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
                    return self.network_model.net.res_storage.loc[device_id, 'p_mw']
                else:
                    # 使用设定值
                    storage = self.network_model.net.storage
                    if device_id in storage.index:
                        return storage.loc[device_id, 'p_mw']
                    return 0.0
                    
            elif device_type == "外部电网":
                # 从外部电网潮流计算结果中获取功率
                if hasattr(self.network_model.net, 'res_ext_grid') and device_id in self.network_model.net.res_ext_grid.index:
                    return abs(self.network_model.net.res_ext_grid.loc[device_id, 'p_mw'])
                else:
                    return 0.0
            elif device_type == "电表":
                return self._get_meter_power(device_id)
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
        """显示多条功率曲线 - 确保时间基准和窗口完全一致"""
        try:
            # 确保ax已初始化
            if self.ax is None:
                self.initialize_ui_components()
            if self.ax is None:
                return
                
            # 快速检查：如果没有监控的设备，直接显示提示
            if not self.monitored_devices:
                self._show_empty_message()
                return
            
            # 清空当前图表
            self.ax.clear()
            
            # 收集所有有效数据
            all_data = []
            all_powers = []
            all_times = []
            
            for device_key in list(self.monitored_devices):
                if device_key in self.power_history and self.power_history[device_key]:
                    history = list(self.power_history[device_key])  # 转换为列表以便操作
                    
                    if history:
                        # 数据采样：限制数据点数量
                        max_points = 1000
                        if len(history) > max_points:
                            step = max(1, len(history) // max_points)
                            sampled_history = history[::step]
                            # 确保包含最新数据
                            if history and history[-1] not in sampled_history:
                                sampled_history.append(history[-1])
                            history = sampled_history
                        
                        if history:
                            timestamps = [item[0] for item in history]
                            powers = [item[1] for item in history]
                            
                            all_data.append({
                                'device_key': device_key,
                                'timestamps': timestamps,
                                'powers': powers
                            })
                            all_powers.extend(powers)
                            all_times.extend(timestamps)
            
            if not all_data:
                self._show_empty_message()
                return
            
            # 使用全局统一的时间基准和窗口
            global_start_time = min(all_times)
            current_time = max(all_times) if all_times else time.time()
            max_display_time = max(300, current_time - global_start_time)  # 至少显示5分钟
            
            # 绘制所有曲线
            for data in all_data:
                device_key = data['device_key']
                timestamps = data['timestamps']
                powers = data['powers']
                
                # 使用统一的相对时间
                relative_times = [t - global_start_time for t in timestamps]
                
                # 缓存颜色
                if device_key not in self.device_colors:
                    color_index = len(self.device_colors) % len(self.color_palette)
                    self.device_colors[device_key] = self.color_palette[color_index]
                
                device_type, device_id = device_key.split('_', 1)
                self.ax.plot(relative_times, powers, 
                           color=self.device_colors[device_key], linewidth=1.5,
                           label=f'{device_type} {device_id}')
            
            # 设置统一的时间轴范围
            self._setup_time_axis(global_start_time, current_time)
            self._setup_chart_layout(all_powers)
            
            # 高效刷新图表
            self._refresh_canvas()
            
        except Exception as e:
            self._handle_display_error(str(e))
    
    def _setup_time_axis(self, global_start_time, current_time):
        """设置统一的时间轴，确保最新数据点位置一致"""
        time_range = current_time - global_start_time
        
        # 设置合理的显示窗口
        if time_range <= 60:  # 1分钟内
            display_range = 60  # 显示1分钟
            self.ax.set_xlim(0, display_range)
        elif time_range <= 300:  # 5分钟内
            display_range = 300  # 显示5分钟
            self.ax.set_xlim(0, display_range)
        elif time_range <= 600:  # 10分钟内
            display_range = 600  # 显示10分钟
            self.ax.set_xlim(0, display_range)
        else:  # 超过10分钟，显示最近10分钟
            display_range = 600
            self.ax.set_xlim(time_range - display_range, time_range)
        
        # 设置时间轴标签
        self.ax.set_xlabel('时间 (秒)', fontsize=12)
        
        # 添加网格线，便于观察时间点
        self.ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    def _show_empty_message(self):
        """显示空数据提示"""
        self.ax.clear()
        self.ax.text(0.5, 0.5, "等待数据收集...\n\n1. 在设备树中选择设备\n2. 勾选\"监控当前设备\"\n3. 启用自动计算功能\n4. 数据将实时显示", 
                     transform=self.ax.transAxes, ha='center', va='center', 
                     bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7),
                     fontsize=12)
        self.ax.set_xlabel('时间 (秒)', fontsize=12)
        self.ax.set_ylabel('功率 (MW)', fontsize=12)
        self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
        self._refresh_canvas()
    
    def _setup_chart_layout(self, all_powers):
        """设置图表布局"""
        self.ax.set_xlabel('时间 (秒)', fontsize=12)
        self.ax.set_ylabel('功率 (MW)', fontsize=12)
        self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        
        # 智能调整Y轴范围
        if all_powers:
            min_power = min(all_powers)
            max_power = max(all_powers)
            
            # 添加合理的边距
            range_size = max_power - min_power
            if range_size < 0.1:  # 数据范围太小
                padding = 0.1
            else:
                padding = range_size * 0.1
            
            self.ax.set_ylim(min_power - padding, max_power + padding)
        else:
            self.ax.set_ylim(-1, 1)
        
        # 显示图例（如果有数据）
        if self.ax.get_legend_handles_labels()[0]:
            self.ax.legend()
    
    def _refresh_canvas(self):
        """高效刷新画布"""
        try:
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.draw_idle()  # 使用draw_idle代替draw，提高性能
            elif hasattr(self.parent_window, 'canvas_mpl'):
                self.parent_window.canvas_mpl.draw_idle()
        except Exception as e:
            print(f"刷新画布失败: {str(e)}")
    
    def _handle_display_error(self, error_msg):
        """处理显示错误"""
        self.ax.clear()
        self.ax.text(0.5, 0.5, f"显示功率曲线失败: {error_msg}", 
                     transform=self.ax.transAxes, ha='center', va='center', 
                     bbox=dict(boxstyle='round', facecolor='red', alpha=0.5))
        self._refresh_canvas()
        print(f"显示功率曲线失败: {error_msg}")
    
    def toggle_current_device_monitor(self, state):
        """切换当前设备监控状态 - 优化延迟更新"""
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
                
        # 使用延迟更新机制，避免频繁重绘
        self.schedule_curve_update()
    
    def on_monitored_device_toggled(self, item, column):
        """监控设备列表中的复选框状态改变 - 优化延迟更新"""
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
            
            # 使用延迟更新机制
            self.schedule_curve_update()
    
    def schedule_curve_update(self):
        """延迟更新图表，避免频繁重绘"""
        if self._update_timer is None:
            from PySide6.QtCore import QTimer
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._perform_batch_update)
        
        # 重置计时器，延迟100ms后更新
        self._update_timer.stop()
        self._update_timer.start(100)
        self._batch_update_pending = True
    
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
        """清除所有监控设备 - 优化性能"""
        self.monitored_devices.clear()
        self.device_colors.clear()
        self.update_monitored_devices_list()
        
        # 更新当前设备监控复选框状态
        if hasattr(self.parent_window, 'current_device_monitor'):
            self.parent_window.current_device_monitor.setChecked(False)
        
        # 使用延迟更新机制
        self.schedule_curve_update()
    
    def cleanup(self):
        """完整清理功率监控资源 - 防止内存泄漏"""
        try:
            # 清理所有监控数据
            self.clear_all_monitors()
            
            # 清理历史数据
            if hasattr(self, 'power_history'):
                self.power_history.clear()
            
            # 清理设备颜色映射
            if hasattr(self, 'device_colors'):
                self.device_colors.clear()
            
            # 清理监控设备集合
            if hasattr(self, 'monitored_devices'):
                self.monitored_devices.clear()
            
            # 断开UI组件引用
            self.ax = None
            self.canvas = None
            self.current_device_monitor = None
            self.monitored_devices_list = None
            
            # 清理网络模型引用
            self.network_model = None
            # self.clear_all_members()
            # 强制垃圾回收
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"清理功率监控资源时发生错误: {e}")

    def clear_all_members(self):
        """清空类中所有成员变量"""
        # 保留基本属性，清空其他所有
        keep_attrs = ['__class__', '__dict__', '__weakref__']
        
        for attr in list(self.__dict__.keys()):
            if attr not in keep_attrs:
                delattr(self, attr)  

    def _get_meter_power(self, meter_id):
        """
        获取指定电表的功率测量值
        
        参数:
            meter_id (str): 电表设备的唯一标识符
            
        返回:
            float: 电表测量的功率值（单位：MW），如果获取失败则返回0.0
        """
        try:
            # 仅使用父窗口的缓存方法
            if not hasattr(self.parent_window, 'get_meter_item_by_type_and_id'):
                print("父窗口未提供缓存方法，无法获取电表数据")
                return 0.0
                
            meter_measurement = self.parent_window.get_meter_item_by_type_and_id('meter', meter_id)
            if not meter_measurement:
                return 0.0
                
            # 直接提取配置并查询测量值
            measurement_config = self._extract_measurement_config(meter_measurement.properties)
            return self._query_measurement_value(measurement_config) if measurement_config else 0.0
            
        except Exception as e:
            print(f"获取电表{meter_id}功率时出错: {str(e)}")
            return 0.0
    
    def _extract_measurement_config(self, measurement_row):
        """
        从测量行数据中提取测量配置信息
        
        参数:
            measurement_row (pd.Series): 测量配置数据行
            
        返回:
            dict: 包含测量配置的词典，如果提取失败返回None
        """
        try:
            return {
                'measurement_type': measurement_row['meas_type'],
                'element_type': measurement_row['element_type'],
                'element_idx': measurement_row['element'],
                'side': measurement_row.get('side', None)
            }
        except (KeyError, IndexError) as e:
            print(f"提取测量配置时出错: {str(e)}")
            return None
    
    def _query_measurement_value(self, config):
        """
        根据测量配置查询实时测量值
        
        参数:
            config (dict): 包含测量配置的字典
            
        返回:
            float: 测量到的功率值（单位：MW）
        """
        element_type = config['element_type']
        element_idx = config['element_idx']
        side = config['side']
        
        # 定义各元素类型的查询映射
        query_map = {
            'load': {
                'result_attr': 'res_load',
                'value_key': 'p_mw'
            },
            'sgen': {
                'result_attr': 'res_sgen',
                'value_key': 'p_mw'
            },
            'storage': {
                'result_attr': 'res_storage',
                'value_key': 'p_mw'
            },
            'bus': {
                'result_attr': 'res_bus',
                'value_key': 'p_mw'
            },
            'line': {
                'result_attr': 'res_line',
                'side_mapping': {
                    'from': 'p_from_mw',
                    'to': 'p_to_mw',
                }
            },
            'trafo': {
                'result_attr': 'res_trafo',
                'side_mapping': {
                    'hv': 'p_hv_mw',
                    'lv': 'p_lv_mw',
                }
            },
            'ext_grid': {
                'result_attr': 'res_ext_grid',
                'value_key': 'p_mw'
            }
        }
        
        # 检查元素类型是否支持
        if element_type not in query_map:
            print(f"不支持的元素类型: {element_type}")
            return 0.0
            
        query_info = query_map[element_type]
        result_attr = query_info['result_attr']
        
        # 检查网络模型是否包含结果数据
        if not hasattr(self.network_model.net, result_attr):
            return 0.0
            
        result_df = getattr(self.network_model.net, result_attr)
        if element_idx not in result_df.index:
            return 0.0
            
        # 获取测量值
        try:
            if 'side_mapping' in query_info:
                # 处理有side参数的元素类型（line, trafo）
                value_key = query_info['side_mapping'].get(side, query_info['side_mapping'][None])
            else:
                # 处理无side参数的元素类型
                value_key = query_info['value_key']
                
            measurement_value = result_df.loc[element_idx, value_key]
            return abs(float(measurement_value))
            
        except (KeyError, ValueError) as e:
            print(f"获取测量值时出错: {str(e)}")
            return 0.0