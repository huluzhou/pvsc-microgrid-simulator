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
        """获取设备的实际功率属性值 - 优化版，减少对network_model.net的重复访问"""
        try:
            device_id = int(device_id)  # 确保device_id是整数
            
            # 缓存网络模型引用，减少重复访问
            net = self.network_model.net
            
            # 根据设备类型从潮流计算结果中获取功率值
            if device_type == "母线":
                # 母线本身不直接设置功率，但可以通过潮流计算结果获取总注入功率
                if hasattr(net, 'res_bus') and device_id in net.res_bus.index:
                    # 获取该母线的总注入功率（发电减负荷）
                    return abs(net.res_bus.at[device_id, 'p_mw'])
                return 0.0
                
            elif device_type == "线路":
                # 从线路潮流计算结果中获取功率
                if hasattr(net, 'res_line') and device_id in net.res_line.index:
                    # 获取线路的有功功率（取两端功率的平均值或较大值）
                    p_from = abs(net.res_line.at[device_id, 'p_from_mw'])
                    p_to = abs(net.res_line.at[device_id, 'p_to_mw'])
                    return max(p_from, p_to)  # 返回较大的功率值
                return 0.0
                    
            elif device_type == "变压器":
                # 从变压器潮流计算结果中获取功率
                if hasattr(net, 'res_trafo') and device_id in net.res_trafo.index:
                    # 获取变压器的有功功率
                    p_hv = abs(net.res_trafo.at[device_id, 'p_hv_mw'])
                    p_lv = abs(net.res_trafo.at[device_id, 'p_lv_mw'])
                    return max(p_hv, p_lv)
                return 0.0
                    
            elif device_type == "发电机":
                # 从发电机潮流计算结果中获取实际功率
                if hasattr(net, 'res_gen') and device_id in net.res_gen.index:
                    return abs(net.res_gen.at[device_id, 'p_mw'])
                # 如果潮流计算结果没有，使用设定值
                gens = net.gen
                if device_id in gens.index:
                    return abs(gens.at[device_id, 'p_mw'])
                return 0.0
                    
            elif device_type == "光伏":
                # 从光伏潮流计算结果中获取实际功率
                if hasattr(net, 'res_sgen') and device_id in net.res_sgen.index:
                    return abs(net.res_sgen.at[device_id, 'p_mw'])
                # 使用设定值
                sgens = net.sgen
                if device_id in sgens.index:
                    return abs(sgens.at[device_id, 'p_mw'])
                return 0.0
                    
            elif device_type == "负载":
                # 从负载潮流计算结果中获取实际功率
                if hasattr(net, 'res_load') and device_id in net.res_load.index:
                    return abs(net.res_load.at[device_id, 'p_mw'])
                # 使用设定值
                loads = net.load
                if device_id in loads.index:
                    return abs(loads.at[device_id, 'p_mw'])
                return 0.0
            elif device_type == "充电桩":
                # 从充电桩潮流计算结果中获取实际功率
                if hasattr(net, 'res_load') and device_id in net.res_load.index:
                    return net.res_load.at[device_id, 'p_mw']
                # 使用设定值
                chargers = net.load
                if device_id in chargers.index:
                    return chargers.at[device_id, 'p_mw']
                return 0.0
            elif device_type == "储能":
                # 从储能潮流计算结果中获取实际功率
                if hasattr(net, 'res_storage') and device_id in net.res_storage.index:
                    return -net.res_storage.at[device_id, 'p_mw']
                # 使用设定值
                storage = net.storage
                if device_id in storage.index:
                    return -storage.at[device_id, 'p_mw']
                return 0.0
                    
            elif device_type == "外部电网":
                # 从外部电网潮流计算结果中获取功率
                if hasattr(net, 'res_ext_grid') and device_id in net.res_ext_grid.index:
                    return abs(net.res_ext_grid.at[device_id, 'p_mw'])
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
            meter_id (int): 电表设备的唯一标识符
            
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
    # TODO:增加方法支持获取电表的测量值,可扩展,支持有功无功电压电流
    def get_meter_measurement(self, meter_id, measurement_type='active_power'):
        """
        获取指定电表的不同类型测量值
        
        参数:
            meter_id (int): 电表设备的唯一标识符
            measurement_type (str): 测量类型，支持以下值：
                - 'active_power': 有功功率（单位：MW）
                - 'reactive_power': 无功功率（单位：MVar）
                - 'voltage': 电压（单位：kV）
                - 'current': 电流（单位：kA）
                默认为'active_power'
                
        返回:
            float: 测量值，如果获取失败则返回0.0
        """
        try:
            # 仅使用父窗口的缓存方法获取电表数据
            if not hasattr(self.parent_window, 'get_meter_item_by_type_and_id'):
                print("父窗口未提供缓存方法，无法获取电表数据")
                return 0.0
                
            meter_measurement = self.parent_window.get_meter_item_by_type_and_id('meter', meter_id)
            if not meter_measurement:
                return 0.0
                
            # 提取基本测量配置
            measurement_config = self._extract_measurement_config(meter_measurement.properties)
            if not measurement_config:
                return 0.0
            
            # 根据测量类型调用相应的查询方法
            if measurement_type == 'active_power':
                # 有功功率，复用现有的查询方法
                return self._query_measurement_value(measurement_config)
            elif measurement_type == 'reactive_power':
                # 无功功率，使用修改后的配置查询
                config = measurement_config.copy()
                return self._query_measurement_value(config, value_type='reactive')
            elif measurement_type == 'voltage':
                # 电压，需要特殊处理
                return self._query_voltage_value(measurement_config)
            elif measurement_type == 'current':
                # 电流，需要特殊处理
                return self._query_current_value(measurement_config)
            else:
                print(f"不支持的测量类型: {measurement_type}")
                return 0.0
                
        except Exception as e:
            print(f"获取电表{meter_id}的{measurement_type}时出错: {str(e)}")
            return 0.0
            
    def _query_measurement_value(self, config, value_type='active'):
        """
        根据测量配置查询实时测量值 - 优化版，支持有功和无功功率
        
        参数:
            config (dict): 包含测量配置的字典
            value_type (str): 值类型，'active'表示有功功率，'reactive'表示无功功率
                
        返回:
            float: 测量到的功率值（单位：有功为MW，无功为MVar）
        """
        try:
            element_type = config['element_type']
            element_idx = config['element_idx']
            side = config['side']
            
            # 根据值类型确定键名
            active_key = 'p_mw'
            reactive_key = 'q_mvar'
            
            # 定义各元素类型的查询映射，支持有功和无功
            query_map = {
                'load': {
                    'result_attr': 'res_load',
                    'active_key': active_key,
                    'reactive_key': reactive_key
                },
                'sgen': {
                    'result_attr': 'res_sgen',
                    'active_key': active_key,
                    'reactive_key': reactive_key
                },
                'storage': {
                    'result_attr': 'res_storage',
                    'active_key': active_key,
                    'reactive_key': reactive_key
                },
                'bus': {
                    'result_attr': 'res_bus',
                    'active_key': active_key,
                    'reactive_key': reactive_key
                },
                'line': {
                    'result_attr': 'res_line',
                    'side_mapping': {
                        'from': {
                            'active': 'p_from_mw',
                            'reactive': 'q_from_mvar'
                        },
                        'to': {
                            'active': 'p_to_mw',
                            'reactive': 'q_to_mvar'
                        },
                    }
                },
                'trafo': {
                    'result_attr': 'res_trafo',
                    'side_mapping': {
                        'hv': {
                            'active': 'p_hv_mw',
                            'reactive': 'q_hv_mvar'
                        },
                        'lv': {
                            'active': 'p_lv_mw',
                            'reactive': 'q_lv_mvar'
                        },
                    }
                },
                'ext_grid': {
                    'result_attr': 'res_ext_grid',
                    'active_key': active_key,
                    'reactive_key': reactive_key
                }
            }
            
            # 检查元素类型是否支持
            if element_type not in query_map:
                print(f"不支持的元素类型: {element_type}")
                return 0.0
                
            query_info = query_map[element_type]
            result_attr = query_info['result_attr']
            
            # 缓存网络模型引用，减少重复访问
            net = self.network_model.net
            
            # 检查网络模型是否包含结果数据
            if not hasattr(net, result_attr):
                return 0.0
                
            result_df = getattr(net, result_attr)
            if element_idx not in result_df.index:
                return 0.0
                
            # 获取测量值
            if 'side_mapping' in query_info:
                # 处理有side参数的元素类型（line, trafo）
                if side in query_info['side_mapping']:
                    value_key = query_info['side_mapping'][side][value_type]
            else:
                # 处理无side参数的元素类型
                value_key = query_info['active_key'] if value_type == 'active' else query_info['reactive_key']
                
            measurement_value = result_df.at[element_idx, value_key]
            return float(measurement_value)
            
        except (KeyError, ValueError, AttributeError) as e:
            print(f"获取测量值时出错: {str(e)}")
            return 0.0
            
    def _query_voltage_value(self, config):
        """
        查询电压值
        
        参数:
            config (dict): 包含测量配置的字典
                
        返回:
            float: 电压值（单位：kV），如果获取失败则返回0.0
        """
        try:
            # 对于电压测量，我们需要获取连接到的母线电压
            element_type = config['element_type']
            element_idx = config['element_idx']
            net = self.network_model.net
            
            # 根据元素类型获取对应的母线ID
            bus_idx = None
            
            if element_type == 'bus':
                # 如果直接测量母线，使用母线ID
                bus_idx = element_idx
            elif element_type == 'line':
                # 对于线路，根据side参数确定母线
                side = config['side']
                if side == 'from':
                    bus_idx = net.line.at[element_idx, 'from_bus']
                elif side == 'to':
                    bus_idx = net.line.at[element_idx, 'to_bus']
            elif element_type == 'trafo':
                # 对于变压器，根据side参数确定母线
                side = config['side']
                if side == 'hv':
                    bus_idx = net.trafo.at[element_idx, 'hv_bus']
                elif side == 'lv':
                    bus_idx = net.trafo.at[element_idx, 'lv_bus']
            elif element_type in ['load', 'sgen', 'storage', 'ext_grid']:
                # 对于连接到母线的设备，直接获取其连接的母线
                bus_idx = net[element_type].at[element_idx, 'bus']
            
            # 如果找到母线ID，查询电压值
            if bus_idx is not None and hasattr(net, 'res_bus'):
                if bus_idx in net.res_bus.index:
                    return float(net.res_bus.at[bus_idx, 'vm_pu'] * net.bus.at[bus_idx, 'vn_kv'])
            
            return 0.0
            
        except (KeyError, ValueError, AttributeError) as e:
            print(f"获取电压值时出错: {str(e)}")
            return 0.0
            
    def _query_current_value(self, config):
        """
        查询电流值
        
        参数:
            config (dict): 包含测量配置的字典
                
        返回:
            float: 电流值（单位：kA），如果获取失败则返回0.0
        """
        try:
            element_type = config['element_type']
            element_idx = config['element_idx']
            net = self.network_model.net
            
            # 不同元素类型的电流查询方式不同
            if element_type == 'line' and hasattr(net, 'res_line'):
                # 线路电流
                if element_idx in net.res_line.index:
                    side = config['side']
                    if side == 'from':
                        return float(net.res_line.at[element_idx, 'i_from_ka'])
                    elif side == 'to':
                        return float(net.res_line.at[element_idx, 'i_to_ka'])
            elif element_type == 'trafo' and hasattr(net, 'res_trafo'):
                # 变压器电流
                if element_idx in net.res_trafo.index:
                    side = config['side']
                    if side == 'hv':
                        return float(net.res_trafo.at[element_idx, 'i_hv_ka'])
                    elif side == 'lv':
                        return float(net.res_trafo.at[element_idx, 'i_lv_ka'])
            elif element_type in ['load', 'sgen', 'storage'] and hasattr(net, f'res_{element_type}'):
                # 对于负载、静态发电机和储能设备，计算电流
                result_df = getattr(net, f'res_{element_type}')
                if element_idx in result_df.index:
                    p_mw = result_df.at[element_idx, 'p_mw']
                    q_mvar = result_df.at[element_idx, 'q_mvar']
                    # 获取连接母线的电压
                    bus_idx = net[element_type].at[element_idx, 'bus']
                    if bus_idx in net.res_bus.index:
                        vm_pu = net.res_bus.at[bus_idx, 'vm_pu']
                        vn_kv = net.bus.at[bus_idx, 'vn_kv']
                        voltage_kv = vm_pu * vn_kv
                        # 计算视在功率 (MVA)
                        s_mva = (p_mw**2 + q_mvar**2)**0.5
                        # 计算电流 (kA)
                        # 假设为三相系统，相电压 = 线电压 / √3
                        current_ka = s_mva / (3**0.5 * voltage_kv)
                        return current_ka
            
            return 0.0
            
        except (KeyError, ValueError, AttributeError) as e:
            print(f"获取电流值时出错: {str(e)}")
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
    