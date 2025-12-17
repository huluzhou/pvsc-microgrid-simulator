"""数据生成器控制模块
提供设备数据生成的UI控制和管理功能
"""

from PySide6.QtWidgets import (
    QMessageBox
)
from .data_generators import DataGeneratorManager
from utils.logger import logger


class DataControlManager:
    """数据生成器控制管理类"""
    
    def __init__(self, parent_window, data_generator_manager=None):
        self.parent_window = parent_window
        self.network_items = parent_window.network_items
        # 使用传入的数据生成器管理器实例，如果未传入则尝试从父窗口获取
        if data_generator_manager is not None:
            self.data_generator_manager = data_generator_manager
        else:
            # 作为降级方案，在没有可用实例时才创建新实例
            self.data_generator_manager = DataGeneratorManager()
        
        # 连接储能功率变化信号
        if hasattr(parent_window, 'storage_power_changed'):
            parent_window.storage_power_changed.connect(self.on_storage_power_updated)
    
    def on_device_power_on(self):
        """控制当前设备开启通信"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            QMessageBox.warning(self.parent_window, "警告", "请先选择一个设备")
            return
            
        device_type = self.parent_window.current_component_type
        device_idx = self.parent_window.current_component_idx
        
        # 获取modbus_manager
        modbus_manager = getattr(self.parent_window, 'modbus_manager', None)
        if not modbus_manager:
            QMessageBox.warning(self.parent_window, "警告", "Modbus管理器未初始化")
            return
            
        # 从全局变量network_items获取设备信息
        component_type_map = {
            'sgen': 'static_generator',
            'load': 'load',
            'storage': 'storage',
            'charger': 'charger',
            'meter': 'meter'
        }
        
        component_type_key = component_type_map.get(device_type)
        if not component_type_key:
            QMessageBox.warning(self.parent_window, "警告", f"不支持的设备类型: {device_type}")
            return
            
        # 检查设备是否存在于network_items中
        if component_type_key not in self.network_items or device_idx not in self.network_items[component_type_key]:
            QMessageBox.warning(self.parent_window, "警告", f"设备 {device_type} {device_idx} 不存在")
            return
            
        # 获取设备项
        device_item = self.network_items[component_type_key][device_idx]
        properties = getattr(device_item, 'properties', {})
        
        # 构建设备信息
        device_info = {
            'type': component_type_key,
            'index': device_idx,
            'name': properties.get('component_name', f"{device_type}_{device_idx}"),
            'sn': properties.get('sn', None),
            'ip': properties.get('ip', None),
            'port': properties.get('port', 502 + device_idx),
            'p_mw': properties.get('p_mw', 0.0),
            'q_mvar': properties.get('q_mvar', 0.0),
            'sn_mva': properties.get('sn_mva', 0.0),
            'max_e_mwh': properties.get('max_e_mwh', 1.0)  # 对储能设备有意义
        }
            
        # 检查IP是否存在
        if not device_info['ip']:
            device_type_name = {'sgen': '光伏', 'load': '负载', 'storage': '储能', 'charger': '充电桩', 'meter': '电表'}.get(device_type, device_type)
            QMessageBox.warning(self.parent_window, "失败", f"{device_type_name}设备 {device_idx} 缺少IP地址，开启通信失败")
            return
            
        # 启动Modbus服务器（开启通信）
        result = modbus_manager.start_modbus_server(device_info)
        if result:
            device_type_name = {'sgen': '光伏', 'load': '负载', 'storage': '储能', 'charger': '充电桩', 'meter': '电表'}.get(device_type, device_type)
            self.parent_window.statusBar().showMessage(f"已成功启动{device_type_name}设备 {device_idx} 的Modbus服务器")
            QMessageBox.information(self.parent_window, "成功", f"{device_type_name}设备 {device_idx} 已开启通信")
            
            # 更新通信状态指示器，基于设备的comm_status属性
            self._update_comm_status_indicator(device_type, device_idx)
            
        else:
            device_type_name = {'sgen': '光伏', 'load': '负载', 'storage': '储能', 'charger': '充电桩', 'meter': '电表'}.get(device_type, device_type)
            self.parent_window.statusBar().showMessage(f"启动{device_type_name}设备 {device_idx} 的Modbus服务器失败")
            QMessageBox.warning(self.parent_window, "失败", f"{device_type_name}设备 {device_idx} 开启通信失败")
            
            # 更新通信状态指示器，基于设备的comm_status属性
            self._update_comm_status_indicator(device_type, device_idx)
            
    def on_device_power_off(self):
        """控制当前设备关闭通信"""
        try:
            # 检查必要属性是否存在
            if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
                QMessageBox.warning(self.parent_window, "警告", "请先选择一个设备")
                return
                
            device_type = self.parent_window.current_component_type
            device_idx = self.parent_window.current_component_idx
            device_key = f"{device_type}_{device_idx}"
            component_type_map = {
            'sgen': 'static_generator',
            'load': 'load',
            'storage': 'storage',
            'charger': 'charger',
            'meter': 'meter'
            }
        
            component_type_key = component_type_map.get(device_type)
            # 映射设备类型到中文名称
            device_type_name = {'sgen': '光伏', 'load': '负载', 'storage': '储能', 'charger': '充电桩', 'meter': '电表'}.get(device_type, device_type)
            
            logger.info(f"尝试关闭{device_type_name}设备 {device_idx} 的通信")
        
            # 获取modbus_manager
            modbus_manager = getattr(self.parent_window, 'modbus_manager', None)
            if not modbus_manager:
                logger.warning("Modbus管理器未初始化")
                QMessageBox.warning(self.parent_window, "警告", "Modbus管理器未初始化")
                return
                
            # 停止Modbus服务器（关闭通信）
            result = modbus_manager.stop_modbus_server(component_type_key, device_idx)
            
            if result:
                # 显示成功信息
                success_message = f"已成功停止{device_type_name}设备 {device_idx} 的Modbus服务器"
                self.parent_window.statusBar().showMessage(success_message)
                QMessageBox.information(self.parent_window, "成功", f"{device_type_name}设备 {device_idx} 已关闭通信")
                logger.info(success_message)
                
                # 更新通信状态指示器，基于设备的comm_status属性
                self._update_comm_status_indicator(device_type, device_idx)
            else:
                # 显示失败信息
                error_message = f"停止{device_type_name}设备 {device_idx} 的Modbus服务器失败"
                self.parent_window.statusBar().showMessage(error_message)
                QMessageBox.warning(self.parent_window, "失败", f"{device_type_name}设备 {device_idx} 关闭通信失败")
                logger.warning(error_message)
                
        except Exception as e:
            # 捕获所有异常，确保方法不会崩溃
            error_info = f"关闭设备通信时发生异常: {str(e)}"
            logger.error(error_info, exc_info=True)
            QMessageBox.critical(self.parent_window, "错误", error_info)
        
        
    def get_meter_measurement_by_type(self, meter_id):
        """
        基于电表设备自身的meas_type属性获取测量值，内部调用PowerMonitor的get_meter_measurement方法
        
        参数:
            meter_id (int): 电表设备的唯一标识符
            
        返回:
            float: 测量值，如果获取失败则返回0.0
        """
        try:
            # 检查network_items中是否存在meter类型且meter_id有效
            if 'meter' not in self.network_items or meter_id not in self.network_items['meter']:
                logger.warning(f"电表设备 {meter_id} 不存在")
                return 0.0
            
            # 获取电表设备实例
            meter_item = self.network_items['meter'][meter_id]
            
            # 获取电表设备的meas_type属性
            meas_type = meter_item.properties.get('meas_type', 'p')
            
            # 根据meas_type映射到PowerMonitor支持的测量类型
            measurement_type_map = {
                'p': 'active_power',       # 有功功率
                'q': 'reactive_power',     # 无功功率
                'vm': 'voltage',           # 电压
                'i': 'current'             # 电流
            }
            
            # 获取对应的测量类型
            power_monitor_measurement_type = measurement_type_map.get(meas_type, 'active_power')
            
            # 调用PowerMonitor的get_meter_measurement方法获取测量值
            if hasattr(self.parent_window, 'power_monitor'):
                return self.parent_window.power_monitor.get_meter_measurement(meter_id, power_monitor_measurement_type)
            else:
                logger.warning("PowerMonitor实例未找到")
                # 如果无法获取测量值，返回设备的value属性值
                return meter_item.properties.get('value', 0.0)
                
        except Exception as e:
            logger.error(f"获取电表测量值时发生错误: {str(e)}", exc_info=True)
            return 0.0
    
    def on_storage_power_updated(self, device_idx, new_power):
        """响应储能功率变化信号，更新滑块和输入框的值"""
        # 检查是否当前选中的是该储能设备
        if (hasattr(self.parent_window, 'current_component_type') and 
            hasattr(self.parent_window, 'current_component_idx') and 
            self.parent_window.current_component_type == 'storage' and 
            self.parent_window.current_component_idx == device_idx):
            
            # 更新储能专用控制组件
            if hasattr(self.parent_window, 'storage_power_slider'):
                self.parent_window.storage_power_slider.blockSignals(True)
                # 将功率值转换为滑块值（精确到0.01MW）
                slider_value = int(new_power * 100)
                # 获取当前滑块范围
                min_slider = self.parent_window.storage_power_slider.minimum()
                max_slider = self.parent_window.storage_power_slider.maximum()
                slider_value = max(min_slider, min(max_slider, slider_value))
                self.parent_window.storage_power_slider.setValue(slider_value)
                self.parent_window.storage_power_slider.blockSignals(False)
            
            if hasattr(self.parent_window, 'storage_power_spinbox'):
                self.parent_window.storage_power_spinbox.blockSignals(True)
                # 获取当前输入框范围
                min_spin = self.parent_window.storage_power_spinbox.minimum()
                max_spin = self.parent_window.storage_power_spinbox.maximum()
                safe_value = max(min_spin, min(max_spin, new_power))
                self.parent_window.storage_power_spinbox.setValue(safe_value)
                self.parent_window.storage_power_spinbox.blockSignals(False)
                
    # 设备控制面板信息更新方法组
    def _update_comm_status_indicator(self, device_type, device_idx=None):
        """更新设备通信状态指示器，基于设备的comm_status属性
        
        Args:
            device_type: 设备类型 (sgen, storage, load, charger)
            device_idx: 设备索引（可选）
        """
        try:
            # 构建状态指示器标签名
            indicator_map = {
                'sgen': 'sgen_comm_status_label',
                'storage': 'storage_comm_status_label',
                'load': 'load_comm_status_label',
                'charger': 'charger_comm_status_label',
                'meter': 'meter_comm_status_label'
            }
            
            indicator_name = indicator_map.get(device_type)
            if not indicator_name:
                return
                
            # 检查状态指示器是否存在
            if not hasattr(self.parent_window, indicator_name):
                return
                
            # 获取状态指示器
            status_label = getattr(self.parent_window, indicator_name)
            
            # 确定实际的设备类型键名
            type_map = {
                'sgen': 'static_generator',
                'storage': 'storage',
                'load': 'load',
                'charger': 'charger',
                'meter': 'meter'
            }
            component_type_key = type_map.get(device_type)
            
            # 默认状态为未连接
            is_connected = False
            
            # 如果提供了设备索引且设备存在，从设备的comm_status属性获取状态
            if device_idx is not None and component_type_key in self.network_items:
                device_item = self.network_items[component_type_key].get(device_idx)
                if device_item and hasattr(device_item, 'comm_status'):
                    is_connected = device_item.comm_status
            
            # 更新状态指示器
            if is_connected:
                status_label.setText("通信状态: 已连接")
                status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                status_label.setText("通信状态: 未连接")
                status_label.setStyleSheet("color: red; font-weight: bold;")
                
        except Exception as e:
            logger.warning(f"更新通信状态指示器失败: {str(e)}")
            
    def update_storage_control_panel_info(self, component_type, component_idx):
        """更新储能控制面板信息"""
        # 更新设备标签
        if hasattr(self.parent_window, 'storage_current_device_label'):
            if component_type and component_idx is not None:
                device_name = f"储能_{component_idx}"
                self.parent_window.storage_current_device_label.setText(f"当前设备: {device_name}")
                
                # 更新手动控制组件的值和范围
                if hasattr(self.parent_window, 'network_model') and hasattr(self.parent_window.network_model, 'net'):
                    try:
                        # 获取储能设备的当前功率值，并从兆瓦(MW)转换为千瓦(kW)
                        current_power = -self.parent_window.network_model.net.storage.at[component_idx, 'p_mw'] * 1000
                        
                        # 从network_items获取储能设备的额定功率
                        storage_item = None
                        rated_power_mw = 1.0  # 默认值
                        if 'storage' in self.network_items:
                            storage_item = self.network_items['storage'].get(component_idx)
                            if storage_item and hasattr(storage_item, 'properties') and 'sn_mva' in storage_item.properties:
                                # 从properties中获取sn_mva值
                                rated_power_mw = storage_item.properties['sn_mva']
                        
                        # 更新储能设备的状态量显示
                        self.update_storage_realtime_info(component_idx)
                        
                        # 根据额定功率动态设置滑块和输入框的范围（-150%~150%额定功率，负值表示放电）
                        # 将兆瓦(MW)转换为千瓦(kW)
                        max_power = rated_power_mw * 1000
                        min_power = -max_power
                        
                        # 更新滑块范围和值
                        if hasattr(self.parent_window, 'storage_power_slider'):
                            self.parent_window.storage_power_slider.setRange(int(min_power * 10), int(max_power * 10))  # 精确到0.1kW
                            # 确保当前值不超过新范围
                            safe_value = max(int(min_power * 10), min(int(max_power * 10), int(current_power * 10)))
                            self.parent_window.storage_power_slider.setValue(safe_value)
                        
                        # 更新输入框范围和值
                        if hasattr(self.parent_window, 'storage_power_spinbox'):
                            self.parent_window.storage_power_spinbox.setRange(min_power, max_power)
                            # 确保当前值不超过新范围
                            safe_value = max(min_power, min(max_power, current_power))
                            self.parent_window.storage_power_spinbox.setValue(safe_value)
                        
                        # 根据设备的手动控制模式设置UI控件的启用/禁用状态
                        is_manual_mode = True
                        if storage_item and hasattr(storage_item, 'is_manual_control'):
                            is_manual_mode = storage_item.is_manual_control
                        
                        # 更新复选框状态
                        if hasattr(self.parent_window, 'storage_enable_remote'):
                            self.parent_window.storage_enable_remote.blockSignals(True)
                            self.parent_window.storage_enable_remote.setChecked(not is_manual_mode)
                            self.parent_window.storage_enable_remote.blockSignals(False)
                        
                        # 更新手动控制面板和控件的启用/禁用状态
                        if hasattr(self.parent_window, 'storage_manual_panel'):
                            self.parent_window.storage_manual_panel.setEnabled(is_manual_mode)
                        if hasattr(self.parent_window, 'storage_power_slider'):
                            self.parent_window.storage_power_slider.setEnabled(is_manual_mode)
                        if hasattr(self.parent_window, 'storage_power_spinbox'):
                            self.parent_window.storage_power_spinbox.setEnabled(is_manual_mode)
                    except Exception as e:
                        logger.error(f"更新储能设备信息和控制时出错: {e}")
            else:
                # 未选择设备时的处理
                self.parent_window.storage_current_device_label.setText("未选择储能设备")
                
    def update_charger_control_panel_info(self, component_type, component_idx):
        """更新充电桩控制面板信息"""
        # 更新设备标签
        if hasattr(self.parent_window, 'charger_current_device_label'):
            if component_type and component_idx is not None:
                device_name = f"充电桩_{component_idx}"
                self.parent_window.charger_current_device_label.setText(f"当前设备: {device_name}")
                
                # 更新手动控制组件的值和范围
                if hasattr(self.parent_window, 'network_model') and hasattr(self.parent_window.network_model, 'net'):
                    try:
                        # 获取充电桩设备的当前需求功率值
                        current_power = self.parent_window.network_model.net.load.at[component_idx, 'p_mw']
                        current_power_kw = current_power * 1000  # 转换为kW
                        
                        # 从network_items获取充电桩的额定功率
                        rated_power_kw = 1000.0  # 默认值
                        if 'charger' in self.network_items:
                            charger_item = self.network_items['charger'].get(component_idx)
                            if charger_item and hasattr(charger_item, 'properties'):
                                # 从properties中获取sn_mva值并转换为kW
                                sn_mva = float(charger_item.properties.get('sn_mva', 1.0))
                                rated_power_kw = sn_mva * 1000  # 转换为kW
                        
                        # 动态设置滑块和输入框的范围（0~额定功率，支持0.1kW精度）
                        if hasattr(self.parent_window, 'charger_required_power_slider'):
                            max_slider_value = int(rated_power_kw * 10)  # 乘以10以支持0.1kW精度
                            self.parent_window.charger_required_power_slider.setRange(0, max_slider_value)
                            # 确保当前值不超过新范围，并转换为滑块值（乘以10以支持0.1kW精度）
                            safe_value = max(0, min(max_slider_value, int(current_power_kw * 10)))
                            self.parent_window.charger_required_power_slider.setValue(safe_value)
                        
                        if hasattr(self.parent_window, 'charger_required_power_spinbox'):
                            self.parent_window.charger_required_power_spinbox.setRange(0.0, rated_power_kw)
                            # 确保当前值不超过新范围
                            safe_value = max(0.0, min(rated_power_kw, current_power_kw))
                            self.parent_window.charger_required_power_spinbox.setValue(safe_value)
                        
                        # 更新功率限制显示
                        if hasattr(self.parent_window, "charger_power_limit_label"):
                            # 这里可以添加功率限制显示的更新逻辑
                            pass
                    except Exception as e:
                        logger.error(f"更新充电桩设备信息和控制时出错: {e}")
            else:
                self.parent_window.charger_current_device_label.setText("未选择充电桩设备")
    
    def update_meter_control_panel_info(self, component_type, component_idx):
        """更新电表设备控制面板信息"""
        # 更新设备标签
        if hasattr(self.parent_window, 'meter_current_device_label'):
            if component_type and component_idx is not None:
                device_name = f"电表_{component_idx}"
                self.parent_window.meter_current_device_label.setText(f"当前设备: {device_name}")
            else:
                self.parent_window.meter_current_device_label.setText("未选择电表设备")
        
        # 更新测量类型信息
        if hasattr(self.parent_window, 'meter_meas_type_label'):
            if component_type and component_idx is not None and 'meter' in self.network_items and component_idx in self.network_items['meter']:
                try:
                    meter_item = self.network_items['meter'][component_idx]
                    meas_type = meter_item.properties.get('meas_type', 'p')
                    
                    # 测量类型显示映射
                    meas_type_display = {
                        'p': '有功功率',
                        'q': '无功功率',
                        'vm': '电压',
                        'i': '电流'
                    }
                    
                    display_text = meas_type_display.get(meas_type, f"未知类型({meas_type})")
                    self.parent_window.meter_meas_type_label.setText(f"{display_text}（基于设备配置）")
                except Exception as e:
                    logger.error(f"更新电表测量类型失败: {str(e)}")
                    self.parent_window.meter_meas_type_label.setText("未知（配置错误）")
            else:
                self.parent_window.meter_meas_type_label.setText("未选择设备")
        
        # 更新测量元件类型和索引信息
        if component_type and component_idx is not None and 'meter' in self.network_items and component_idx in self.network_items['meter']:
            try:
                meter_item = self.network_items['meter'][component_idx]
                element_type = meter_item.properties.get('element_type', 'bus')
                element_index = meter_item.properties.get('element', 0)
                side = meter_item.properties.get('side', '')
                
                # 更新测量元件类型
                if hasattr(self.parent_window, 'meter_element_type_label'):
                    # 基础类型文本
                    type_text = f"- 测量元件类型: {element_type}"
                    self.parent_window.meter_element_type_label.setText(type_text)
                
                # 更新测量位置信息
                if hasattr(self.parent_window, 'meter_element_side_label'):
                    side_text = ""
                    # 根据元件类型和side属性显示不同的位置描述
                    if element_type == 'trafo':
                        side_text = '高压侧' if side == 'hv' else '低压侧' if side == 'lv' else '中压侧'
                    elif element_type == 'line':
                        side_text = '起始端(from)' if side == 'from' else '末端(to)'
                    elif side:
                        side_text = side
                    
                    self.parent_window.meter_element_side_label.setText(f"- 测量位置: {side_text}")
                
                # 更新测量元件索引
                if hasattr(self.parent_window, 'meter_element_index_label'):
                    self.parent_window.meter_element_index_label.setText(f"- 测量元件索引: {element_index}")
            except Exception as e:
                logger.error(f"更新电表元件信息失败: {str(e)}")
        
        # 更新通信状态指示器
        self._update_comm_status_indicator('meter', component_idx)
        
        # 更新起始电量控件（直接显示并可写入四象限计数器）
        if (hasattr(self.parent_window, 'meter_active_export_energy_start_spin') and
            hasattr(self.parent_window, 'meter_active_import_energy_start_spin') and
            hasattr(self.parent_window, 'meter_reactive_export_energy_start_spin') and
            hasattr(self.parent_window, 'meter_reactive_import_energy_start_spin')):
            try:
                if 'meter' in self.network_items and component_idx in self.network_items['meter']:
                    meter_item = self.network_items['meter'][component_idx]
                    ae_export = float(getattr(meter_item, 'active_export_mwh', 0.0))
                    ae_import = float(getattr(meter_item, 'active_import_mwh', 0.0))
                    re_export = float(getattr(meter_item, 'reactive_export_mvarh', 0.0))
                    re_import = float(getattr(meter_item, 'reactive_import_mvarh', 0.0))
                    self.parent_window.meter_active_export_energy_start_spin.blockSignals(True)
                    self.parent_window.meter_active_import_energy_start_spin.blockSignals(True)
                    self.parent_window.meter_reactive_export_energy_start_spin.blockSignals(True)
                    self.parent_window.meter_reactive_import_energy_start_spin.blockSignals(True)
                    self.parent_window.meter_active_export_energy_start_spin.setValue(ae_export)
                    self.parent_window.meter_active_import_energy_start_spin.setValue(ae_import)
                    self.parent_window.meter_reactive_export_energy_start_spin.setValue(re_export)
                    self.parent_window.meter_reactive_import_energy_start_spin.setValue(re_import)
                    self.parent_window.meter_active_export_energy_start_spin.blockSignals(False)
                    self.parent_window.meter_active_import_energy_start_spin.blockSignals(False)
                    self.parent_window.meter_reactive_export_energy_start_spin.blockSignals(False)
                    self.parent_window.meter_reactive_import_energy_start_spin.blockSignals(False)
            except Exception as e:
                logger.error(f"更新电表起始电量控件失败: {e}")
    
    def apply_meter_start_energy(self):
        """应用电表起始电量设置到meter属性"""
        try:
            if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
                return
            if self.parent_window.current_component_type != 'meter':
                return
            idx = self.parent_window.current_component_idx
            if 'meter' in self.network_items and idx in self.network_items['meter']:
                meter_item = self.network_items['meter'][idx]
                ae_export = self.parent_window.meter_active_export_energy_start_spin.value() if hasattr(self.parent_window, 'meter_active_export_energy_start_spin') else 0.0
                ae_import = self.parent_window.meter_active_import_energy_start_spin.value() if hasattr(self.parent_window, 'meter_active_import_energy_start_spin') else 0.0
                re_export = self.parent_window.meter_reactive_export_energy_start_spin.value() if hasattr(self.parent_window, 'meter_reactive_export_energy_start_spin') else 0.0
                re_import = self.parent_window.meter_reactive_import_energy_start_spin.value() if hasattr(self.parent_window, 'meter_reactive_import_energy_start_spin') else 0.0
                meter_item.active_export_mwh = float(ae_export)
                meter_item.active_import_mwh = float(ae_import)
                meter_item.reactive_export_mvarh = float(re_export)
                meter_item.reactive_import_mvarh = float(re_import)
                self.parent_window.statusBar().showMessage(
                    f"已更新电表 {idx} 起始电量: 上网有功 {ae_export:.3f} MWh, 下网有功 {ae_import:.3f} MWh, 上网无功 {re_export:.3f} MVarh, 下网无功 {re_import:.3f} MVarh"
                )
        except Exception as e:
            logger.error(f"应用电表起始电量失败: {e}")

    def update_switch_control_panel_info(self, component_type, component_idx):
        """更新开关设备控制面板信息"""
        if hasattr(self.parent_window, 'switch_current_device_label'):
            if component_type and component_idx is not None:
                device_name = f"开关_{component_idx}"
                self.parent_window.switch_current_device_label.setText(f"当前设备: {device_name}")
            else:
                self.parent_window.switch_current_device_label.setText("未选择开关设备")
    
    def update_sgen_control_panel_info(self, component_type, component_idx):
        """更新光伏设备控制面板信息"""
        # 1. 更新手动控制组件的值
        if component_type == 'sgen' and hasattr(self.parent_window, 'network_model') and hasattr(self.parent_window.network_model, 'net'):
            try:
                # 获取光伏设备的当前功率值和额定功率
                if component_idx in self.parent_window.network_model.net.sgen.index:
                    current_power = self.parent_window.network_model.net.sgen.at[component_idx, 'p_mw']
                    current_q = self.parent_window.network_model.net.sgen.at[component_idx, 'q_mvar']
                    # 从network_items获取额定功率
                    rated_power = 1.0  # 默认值
                    if 'static_generator' in self.network_items:
                        sgen_item = self.network_items['static_generator'].get(component_idx)
                        if sgen_item and hasattr(sgen_item, 'properties'):
                            rated_power = sgen_item.properties.get('sn_mva', 1.0)
                    
                    # 将功率从MW转换为kW
                    current_power_kw = abs(current_power) * 1000
                    current_q_kvar = max(0.0, current_q * 1000)
                    rated_power_kw = rated_power * 1000
                    
                    is_remote_reactive = False
                    if hasattr(sgen_item, 'is_remote_reactive_control'):
                        is_remote_reactive = sgen_item.is_remote_reactive_control
                    if hasattr(self.parent_window, 'sgen_enable_remote_reactive'):
                        self.parent_window.sgen_enable_remote_reactive.blockSignals(True)
                        self.parent_window.sgen_enable_remote_reactive.setChecked(is_remote_reactive)
                        self.parent_window.sgen_enable_remote_reactive.blockSignals(False)
                    if hasattr(self.parent_window, 'sgen_manual_panel'):
                        self.parent_window.sgen_manual_panel.setEnabled(not is_remote_reactive)
                    if hasattr(self.parent_window, 'sgen_reactive_power_slider'):
                        self.parent_window.sgen_reactive_power_slider.setEnabled(not is_remote_reactive)
                    if hasattr(self.parent_window, 'sgen_reactive_power_spinbox'):
                        self.parent_window.sgen_reactive_power_spinbox.setEnabled(not is_remote_reactive)
                    # 更新滑块范围为0到额定功率（支持0.1kW精度）
                    if hasattr(self.parent_window, 'sgen_power_slider'):
                        max_slider_value = int(rated_power_kw * 10)  # 乘以10以支持0.1kW精度
                        self.parent_window.sgen_power_slider.setRange(0, max_slider_value)
                        self.parent_window.sgen_power_slider.setValue(int(current_power_kw * 10))  # 转换为滑块值
                    
                    # 更新输入框范围
                    if hasattr(self.parent_window, 'sgen_power_spinbox'):
                        self.parent_window.sgen_power_spinbox.setRange(0.0, rated_power_kw)
                        self.parent_window.sgen_power_spinbox.setValue(current_power_kw)
                    
                    # 更新无功功率滑块与输入框范围（单位：kvar）
                    if hasattr(self.parent_window, 'sgen_reactive_power_slider'):
                        min_q_slider = 0
                        max_q_slider = int(rated_power_kw * 10)
                        self.parent_window.sgen_reactive_power_slider.setRange(min_q_slider, max_q_slider)
                        self.parent_window.sgen_reactive_power_slider.setValue(int(current_q_kvar * 10))
                    if hasattr(self.parent_window, 'sgen_reactive_power_spinbox'):
                        self.parent_window.sgen_reactive_power_spinbox.setRange(0.0, rated_power_kw)
                        self.parent_window.sgen_reactive_power_spinbox.setSingleStep(0.1)
                        self.parent_window.sgen_reactive_power_spinbox.setValue(current_q_kvar)
                    
                    # 更新变化幅度控件
                    if hasattr(self.parent_window, 'sgen_variation_spinbox') and hasattr(self, 'data_generator_manager'):
                        # 获取当前设备的数据生成器参数
                        generator = self.data_generator_manager.device_generators.get('sgen', {}).get(
                            component_idx, self.data_generator_manager.default_pv_generator
                        )
                        if hasattr(generator, 'variation'):
                            # 避免触发信号循环
                            self.parent_window.sgen_variation_spinbox.blockSignals(True)
                            self.parent_window.sgen_variation_spinbox.setValue(generator.variation)
                            self.parent_window.sgen_variation_spinbox.blockSignals(False)
                    
                    # 更新季节选择控件
                    if hasattr(self.parent_window, 'season_combo') and hasattr(self, 'data_generator_manager'):
                        generator = self.data_generator_manager.device_generators.get('sgen', {}).get(
                            component_idx, self.data_generator_manager.default_pv_generator
                        )
                        if hasattr(generator, 'season_factor'):
                            # 季节中英文映射
                            season_map = {
                                'spring': '春季',
                                'summer': '夏季',
                                'autumn': '秋季',
                                'winter': '冬季'
                            }
                            season_text = season_map.get(generator.season_factor, '夏季')
                            # 避免触发信号循环
                            self.parent_window.season_combo.blockSignals(True)
                            self.parent_window.season_combo.setCurrentText(season_text)
                            self.parent_window.season_combo.blockSignals(False)
                    
                    # 更新天气选择控件
                    if hasattr(self.parent_window, 'weather_combo') and hasattr(self, 'data_generator_manager'):
                        generator = self.data_generator_manager.device_generators.get('sgen', {}).get(
                            component_idx, self.data_generator_manager.default_pv_generator
                        )
                        if hasattr(generator, 'weather_type'):
                            # 天气中英文映射
                            weather_map = {
                                'sunny': '晴朗',
                                'cloudy': '多云',
                                'overcast': '阴天',
                                'rainy': '雨天'
                            }
                            weather_text = weather_map.get(generator.weather_type, '晴朗')
                            # 避免触发信号循环
                            self.parent_window.weather_combo.blockSignals(True)
                            self.parent_window.weather_combo.setCurrentText(weather_text)
                            self.parent_window.weather_combo.blockSignals(False)
                    # 更新云层覆盖控件
                    if hasattr(self.parent_window, 'cloud_cover_spinbox') and hasattr(self, 'data_generator_manager'):
                        generator = self.data_generator_manager.device_generators.get('sgen', {}).get(
                            component_idx, self.data_generator_manager.default_pv_generator
                        )
                        if hasattr(generator, 'cloud_cover'):
                            # 避免触发信号循环
                            self.parent_window.cloud_cover_spinbox.blockSignals(True)
                            self.parent_window.cloud_cover_spinbox.setValue(generator.cloud_cover)
                            self.parent_window.cloud_cover_spinbox.blockSignals(False)
            except Exception as e:
                logger.error(f"更新光伏设备手动控制值时出错: {e}")
        
        # 2. 更新设备信息
        if hasattr(self.parent_window, 'sgen_current_device_label') and hasattr(self.parent_window, 'sgen_enable_generation_checkbox'):
            if component_type and component_idx is not None:
                device_name = f"光伏_{component_idx}"
                self.parent_window.sgen_current_device_label.setText(f"当前设备: {device_name}")
                
                # 检查当前设备是否启用了数据生成
                is_enabled = self.is_device_generation_enabled(component_type, component_idx)
                self.parent_window.sgen_enable_generation_checkbox.setChecked(is_enabled)
                self.parent_window.sgen_enable_generation_checkbox.setEnabled(True)
                # 根据数据生成状态控制手动控制面板可见性
                if hasattr(self.parent_window, 'sgen_manual_panel'):
                    self.parent_window.sgen_manual_panel.setVisible(not is_enabled)
                
            else:
                self.parent_window.sgen_current_device_label.setText("未选择光伏设备")
                self.parent_window.sgen_enable_generation_checkbox.setChecked(False)
                self.parent_window.sgen_enable_generation_checkbox.setEnabled(False)
    
    def update_load_control_panel_info(self, component_type, component_idx):
        """更新负载设备控制面板信息"""
        # 1. 更新手动控制组件的值
        if component_type == 'load' and hasattr(self.parent_window, 'network_model') and hasattr(self.parent_window.network_model, 'net'):
            try:
                # 获取负载设备的当前功率值
                    if component_idx in self.parent_window.network_model.net.load.index:
                        current_p = self.parent_window.network_model.net.load.at[component_idx, 'p_mw']
                        current_q = self.parent_window.network_model.net.load.at[component_idx, 'q_mvar']
                        
                        # 从network_items获取负载设备的额定功率
                        rated_power_mw = 1.0  # 默认值
                        if 'load' in self.network_items:
                            load_item = self.network_items['load'].get(component_idx)
                            if load_item and hasattr(load_item, 'properties'):
                                # 从properties中获取额定功率值
                                rated_power_mw = float(load_item.properties.get('sn_mva', 1.0))
                        
                        # 设置功率范围（单位：kW）
                        max_power = rated_power_mw * 1000  # 转换为kW
                        min_power = -max_power
                        
                        # 更新有功功率滑块和输入框的值
                        if hasattr(self.parent_window, 'load_power_slider'):
                            # 设置滑块范围（单位：kW，乘以10以实现0.1kW的精度）
                            self.parent_window.load_power_slider.setRange(int(min_power * 10), int(max_power * 10))
                            self.parent_window.load_power_slider.setValue(int(current_p * 1000 * 10))  # 转换为滑块值（MW转kW再乘以10）
                        if hasattr(self.parent_window, 'load_power_spinbox'):
                            # 设置输入框范围（单位：kW）并设置步长为0.1kW
                            self.parent_window.load_power_spinbox.setRange(min_power, max_power)
                            self.parent_window.load_power_spinbox.setSingleStep(0.1)
                            self.parent_window.load_power_spinbox.setValue(current_p * 1000)  # 转换为kW
                    
                    # 更新无功功率滑块和输入框的值（单位：kvar）
                    if hasattr(self.parent_window, 'load_reactive_power_slider'):
                        # 设置无功功率滑块范围（-150%~150%额定功率，乘以10以实现0.1kvar的精度）
                        max_q_slider = int(max_power * 10)  # 因为max_power已经是kW，直接用它作为kvar的范围
                        min_q_slider = int(min_power * 10)
                        self.parent_window.load_reactive_power_slider.setRange(min_q_slider, max_q_slider)
                        self.parent_window.load_reactive_power_slider.setValue(int(current_q * 1000 * 10))  # 转换为滑块值（MVar转kvar再乘以10）
                    if hasattr(self.parent_window, 'load_reactive_power_spinbox'):
                        # 设置无功功率输入框范围（单位：kvar）并设置步长为0.1kvar
                        self.parent_window.load_reactive_power_spinbox.setRange(min_power, max_power)
                        self.parent_window.load_reactive_power_spinbox.setSingleStep(0.1)
                        self.parent_window.load_reactive_power_spinbox.setValue(current_q * 1000)  # 转换为kvar
                    
                    # 更新变化幅度控件
                    if hasattr(self.parent_window, 'load_variation_spinbox') and hasattr(self, 'data_generator_manager'):
                        # 获取当前设备的数据生成器参数
                        generator = self.data_generator_manager.device_generators.get('load', {}).get(
                            component_idx, self.data_generator_manager.default_load_generator
                        )
                        if hasattr(generator, 'variation'):
                            # 避免触发信号循环
                            self.parent_window.load_variation_spinbox.blockSignals(True)
                            self.parent_window.load_variation_spinbox.setValue(generator.variation)
                            self.parent_window.load_variation_spinbox.blockSignals(False)
                    
                    # 更新负载类型控件
                    if hasattr(self.parent_window, 'load_type_combo') and hasattr(self, 'data_generator_manager'):
                        # 获取当前设备的数据生成器参数
                        generator = self.data_generator_manager.device_generators.get('load', {}).get(
                            component_idx, self.data_generator_manager.default_load_generator
                        )
                        if hasattr(generator, 'load_type'):
                            # 负载类型中英文映射
                            load_type_map = {
                                'residential': '住宅负载',
                                'commercial': '商业负载',
                                'industrial': '工业负载'
                            }
                            load_type_text = load_type_map.get(generator.load_type, '住宅负载')
                            # 避免触发信号循环
                            self.parent_window.load_type_combo.blockSignals(True)
                            self.parent_window.load_type_combo.setCurrentText(load_type_text)
                            self.parent_window.load_type_combo.blockSignals(False)
            except Exception as e:
                logger.error(f"更新负载设备手动控制值时出错: {e}")
        
        # 2. 更新设备信息
        if hasattr(self.parent_window, 'load_current_device_label') and hasattr(self.parent_window, 'load_enable_generation_checkbox'):
            if component_type and component_idx is not None:
                device_name = f"负载_{component_idx}"
                self.parent_window.load_current_device_label.setText(f"当前设备: {device_name}")
                
                # 检查当前设备是否启用了数据生成
                is_enabled = self.is_device_generation_enabled(component_type, component_idx)
                self.parent_window.load_enable_generation_checkbox.setChecked(is_enabled)
                self.parent_window.load_enable_generation_checkbox.setEnabled(True)
                # 根据数据生成状态控制手动控制面板可见性
                if hasattr(self.parent_window, 'load_manual_panel'):
                    self.parent_window.load_manual_panel.setVisible(not is_enabled)
                
            else:
                self.parent_window.load_current_device_label.setText("未选择负载设备")
                self.parent_window.load_enable_generation_checkbox.setChecked(False)
                self.parent_window.load_enable_generation_checkbox.setEnabled(False)
                
    def is_device_generation_enabled(self, component_type, component_idx):
        """检查指定设备是否启用了数据生成"""
        device_key = f"{component_type}_{component_idx}"
        return device_key in self.parent_window.generated_devices
    
    def toggle_sgen_data_generation(self, state):
        """切换光伏设备的数据生成状态"""
        self._toggle_device_data_generation(state, 'sgen')
    
    def toggle_load_data_generation(self, state):
        """切换负载设备的数据生成状态"""
        self._toggle_device_data_generation(state, 'load')
    
    
    def _toggle_device_data_generation(self, state, device_type):
        """切换指定类型设备的数据生成状态"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            return
            
        if self.parent_window.current_component_type != device_type:
            return
            
        # 检查是否正在回测
        if hasattr(self.parent_window, 'is_backtesting') and self.parent_window.is_backtesting:
            QMessageBox.warning(self.parent_window, "回测期间", "数据回测期间，数据生成功能无效，请先停止回测再启用数据生成")
            return
            
        device_key = f"{self.parent_window.current_component_type}_{self.parent_window.current_component_idx}"
        device_name = f"{self.parent_window.current_component_type}_{self.parent_window.current_component_idx}"
        
        # 设备类型映射
        device_type_map = {
            'load': '负载',
            'sgen': '光伏', 
        }
        device_type_name = device_type_map.get(device_type, device_type)
        
        # 面板映射
        panel_map = {
            'load': 'load_manual_panel',
            'sgen': 'sgen_manual_panel', 
        }
        
        # 获取当前设备类型对应的面板和方法
        current_panel_name = panel_map.get(device_type)
        
        if state == 2:  # 选中状态 - 启用数据生成
            if device_key not in self.parent_window.generated_devices:
                self.parent_window.generated_devices.add(device_key)
                
                # 只隐藏当前设备类型的手动面板
                if current_panel_name and hasattr(self.parent_window, current_panel_name):
                    getattr(self.parent_window, current_panel_name).setVisible(False)
                
                self.parent_window.statusBar().showMessage(f"已启用{device_type_name}设备 {self.parent_window.current_component_idx} 的数据生成")
                logger.info(f"启用设备 {device_name} 的数据生成")
            else:
                self.parent_window.statusBar().showMessage(f"设备 {device_name} 已在数据生成列表中")
        else:  # 未选中状态 - 禁用数据生成
            if device_key in self.parent_window.generated_devices:
                self.parent_window.generated_devices.remove(device_key)
                
                # 只显示当前设备类型的手动面板
                if current_panel_name and hasattr(self.parent_window, current_panel_name):
                    getattr(self.parent_window, current_panel_name).setVisible(True)
                
                self.parent_window.statusBar().showMessage(f"已禁用{device_type_name}设备 {self.parent_window.current_component_idx} 的数据生成")
                logger.info(f"禁用设备 {device_name} 的数据生成")
            else:
                self.parent_window.statusBar().showMessage(f"设备 {device_name} 未在数据生成列表中")
    
    def update_meter_realtime_info(self, component_idx):
        """更新电表设备的实时测量值信息（有功/无功功率与有功/无功电量）"""
        try:
            # 功率
            if hasattr(self.parent_window, "meter_active_power_label"):
                p_mw = self.parent_window.power_monitor.get_meter_measurement(component_idx, 'active_power') if hasattr(self.parent_window, 'power_monitor') else 0.0
                self.parent_window.meter_active_power_label.setText(f"{p_mw*1000:.1f} kW")
            if hasattr(self.parent_window, "meter_reactive_power_label"):
                q_mvar = self.parent_window.power_monitor.get_meter_measurement(component_idx, 'reactive_power') if hasattr(self.parent_window, 'power_monitor') else 0.0
                self.parent_window.meter_reactive_power_label.setText(f"{q_mvar*1000:.1f} kVar")
            # 电量（如果不存在则显示'不存在'）
            device_item = None
            if 'meter' in self.network_items and component_idx in self.network_items['meter']:
                meter_item = self.network_items['meter'][component_idx]
                element_type = meter_item.properties.get('element_type')
                element_idx = meter_item.properties.get('element')
                type_map = {'sgen': 'static_generator', 'load': 'load', 'storage': 'storage', 'ext_grid': 'external_grid'}
                device_key = type_map.get(element_type)
                device_item = self.parent_window.network_items.get(device_key, {}).get(element_idx) if device_key is not None else None
            # 删除总能量标签更新，保留四象限
            # 四象限电量
            if 'meter' in self.network_items and component_idx in self.network_items['meter']:
                meter_item = self.network_items['meter'][component_idx]
                if hasattr(self.parent_window, "meter_active_export_label"):
                    val = getattr(meter_item, 'active_export_kwh', None)
                    self.parent_window.meter_active_export_label.setText(f"{val:.1f} kWh" if val is not None else "不存在")
                if hasattr(self.parent_window, "meter_active_import_label"):
                    val = getattr(meter_item, 'active_import_kwh', None)
                    self.parent_window.meter_active_import_label.setText(f"{val:.1f} kWh" if val is not None else "不存在")
                if hasattr(self.parent_window, "meter_reactive_export_label"):
                    val = getattr(meter_item, 'reactive_export_mvarh', None)
                    self.parent_window.meter_reactive_export_label.setText(f"{val:.1f} kvarh" if val is not None else "不存在")
                if hasattr(self.parent_window, "meter_reactive_import_label"):
                    val = getattr(meter_item, 'reactive_import_mvarh', None)
                    self.parent_window.meter_reactive_import_label.setText(f"{val:.1f} kvarh" if val is not None else "不存在")
        except Exception as e:
            logger.error(f"更新电表实时信息失败: {str(e)}")
            if hasattr(self.parent_window, "meter_active_power_label"):
                self.parent_window.meter_active_power_label.setText("未计算")
            if hasattr(self.parent_window, "meter_reactive_power_label"):
                self.parent_window.meter_reactive_power_label.setText("未计算")
            # 删除总能量标签异常处理
            if hasattr(self.parent_window, "meter_active_export_label"):
                self.parent_window.meter_active_export_label.setText("不存在")
            if hasattr(self.parent_window, "meter_active_import_label"):
                self.parent_window.meter_active_import_label.setText("不存在")
            if hasattr(self.parent_window, "meter_reactive_export_label"):
                self.parent_window.meter_reactive_export_label.setText("不存在")
            if hasattr(self.parent_window, "meter_reactive_import_label"):
                self.parent_window.meter_reactive_import_label.setText("不存在")
        # 更新通信状态指示器
        self._update_comm_status_indicator('meter', component_idx)
        
    def update_sgen_realtime_info(self, component_idx):
        """更新光伏设备的实时信息（有功/无功功率）"""
        if hasattr(self.parent_window, "sgen_active_power_label") and hasattr(
            self.parent_window, "network_model"
        ):
            net = self.parent_window.network_model.net
            if hasattr(net, "res_sgen") and component_idx in net.res_sgen.index:
                active_power = net.res_sgen.at[component_idx, "p_mw"]
                self.parent_window.sgen_active_power_label.setText(
                    f"{active_power:.4f} MW"
                )
                if hasattr(self.parent_window, "sgen_reactive_power_label"):
                    reactive_power = net.res_sgen.at[component_idx, "q_mvar"]
                    self.parent_window.sgen_reactive_power_label.setText(f"{reactive_power:.4f} MVar")
            else:
                self.parent_window.sgen_active_power_label.setText("未计算")
                if hasattr(self.parent_window, "sgen_reactive_power_label"):
                    self.parent_window.sgen_reactive_power_label.setText("未计算")
        self._update_comm_status_indicator('sgen', component_idx)

    def on_sgen_reactive_control_mode_changed(self, state):
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            return
        if self.parent_window.current_component_type != 'sgen':
            return
        component_idx = self.parent_window.current_component_idx
        if 'static_generator' not in self.network_items or component_idx not in self.network_items['static_generator']:
            return
        sgen_item = self.network_items['static_generator'][component_idx]
        is_remote_enabled = False
        if hasattr(self.parent_window, 'sgen_enable_remote_reactive'):
            is_remote_enabled = self.parent_window.sgen_enable_remote_reactive.isChecked()
        sgen_item.is_remote_reactive_control = is_remote_enabled
        if hasattr(self.parent_window, 'sgen_manual_panel'):
            self.parent_window.sgen_manual_panel.setEnabled(not is_remote_enabled)
        if hasattr(self.parent_window, 'sgen_reactive_power_slider'):
            self.parent_window.sgen_reactive_power_slider.setEnabled(not is_remote_enabled)
        if hasattr(self.parent_window, 'sgen_reactive_power_spinbox'):
            self.parent_window.sgen_reactive_power_spinbox.setEnabled(not is_remote_enabled)
    
    def update_load_realtime_info(self, component_idx):
        """更新负载设备的实时信息（有功/无功功率）"""
        if hasattr(self.parent_window, "load_active_power_label") and hasattr(
            self.parent_window, "network_model"
        ):
            net = self.parent_window.network_model.net
            # 检查component_idx是否为None
            if component_idx is None:
                self.parent_window.load_active_power_label.setText("未计算")
                if hasattr(self.parent_window, "load_reactive_power_value"):
                    self.parent_window.load_reactive_power_value.setText("未计算")
                return
            
            if hasattr(net, "res_load") and component_idx in net.res_load.index:
                active_power = net.res_load.at[component_idx, "p_mw"]
                self.parent_window.load_active_power_label.setText(
                    f"{active_power:.4f} MW"
                )
                if hasattr(self.parent_window, "load_reactive_power_value"):
                    reactive_power = net.res_load.at[component_idx, "q_mvar"]
                    self.parent_window.load_reactive_power_value.setText(f"{reactive_power:.4f} MVar")
            else:
                self.parent_window.load_active_power_label.setText("未计算")
                if hasattr(self.parent_window, "load_reactive_power_value"):
                    self.parent_window.load_reactive_power_value.setText("未计算")
        self._update_comm_status_indicator('load', component_idx)
    
    def update_charger_realtime_info(self, component_idx):
        """更新充电桩设备的实时信息（有功/无功功率）"""
        if hasattr(self.parent_window, "charger_active_power_label") and hasattr(
            self.parent_window, "network_model"
        ):
            net = self.parent_window.network_model.net
            # 检查component_idx是否为None
            if component_idx is None:
                self.parent_window.charger_active_power_label.setText("未计算")
                if hasattr(self.parent_window, "charger_reactive_power_label"):
                    self.parent_window.charger_reactive_power_label.setText("未计算")
                return
            
            # 充电桩在模型中作为负载处理，索引有+1000的偏移
            if hasattr(net, "res_load") and component_idx in net.res_load.index:
                active_power = net.res_load.at[component_idx, "p_mw"]
                # 转换为kW显示
                active_power_kw = active_power * 1000
                self.parent_window.charger_active_power_label.setText(
                    f"{active_power_kw:.1f} kW"
                )
                if hasattr(self.parent_window, "charger_reactive_power_label"):
                    reactive_power_kvar = net.res_load.at[component_idx, "q_mvar"] * 1000
                    self.parent_window.charger_reactive_power_label.setText(f"{reactive_power_kvar:.1f} kVar")
            else:
                self.parent_window.charger_active_power_label.setText("未计算")
                if hasattr(self.parent_window, "charger_reactive_power_label"):
                    self.parent_window.charger_reactive_power_label.setText("未计算")
        self._update_comm_status_indicator('charger', component_idx)

    def update_storage_realtime_info(self, component_idx):
        """更新储能设备的实时信息（有功/无功功率、SOC、工作状态、并网状态）"""
        # 1. 更新有功功率显示
        if hasattr(self.parent_window, "storage_active_power_label") and hasattr(
            self.parent_window, "network_model"
        ):
            net = self.parent_window.network_model.net
            if hasattr(net, "res_storage") and component_idx in net.res_storage.index:
                active_power = -net.res_storage.at[component_idx, "p_mw"]
                self.parent_window.storage_active_power_label.setText(
                    f"{active_power:.4f} MW"
                )
                if hasattr(self.parent_window, "storage_reactive_power_label"):
                    reactive_power = net.res_storage.at[component_idx, "q_mvar"]
                    self.parent_window.storage_reactive_power_label.setText(f"{reactive_power:.4f} MVar")
            else:
                self.parent_window.storage_active_power_label.setText("未计算")
                if hasattr(self.parent_window, "storage_reactive_power_label"):
                    self.parent_window.storage_reactive_power_label.setText("未计算")
        
        # 2. 更新其他状态量显示
        # 查找储能设备
        storage_item = None
        try:
            if hasattr(self.parent_window, 'canvas') and hasattr(self.parent_window.canvas, 'scene'):
                for item in self.parent_window.canvas.scene.items():
                    if (hasattr(item, 'component_type') and 
                        item.component_type == 'storage' and 
                        item.component_index == component_idx):
                        storage_item = item
                        break
        except Exception as e:
            logger.error(f"查找储能设备失败: {str(e)}")
            
        # 更新SOC显示
        if hasattr(self.parent_window, "storage_soc_label"):
            try:
                if storage_item and hasattr(storage_item, 'properties') and 'soc_percent' in storage_item.properties:
                    soc_percent = storage_item.properties['soc_percent']
                    self.parent_window.storage_soc_label.setText(f"{soc_percent*100:.4f}%")
                else:
                    self.parent_window.storage_soc_label.setText("未计算")
            except Exception as e:
                logger.error(f"更新储能SOC失败: {str(e)}")
                self.parent_window.storage_soc_label.setText("未计算")
        
        # 更新工作状态显示
        if hasattr(self.parent_window, "storage_work_status_label"):
            try:
                if storage_item and hasattr(storage_item, 'state'):
                    work_status = storage_item.state
                    self.parent_window.storage_work_status_label.setText(work_status)
                else:
                    self.parent_window.storage_work_status_label.setText("未计算")
            except Exception as e:
                logger.error(f"更新储能工作状态失败: {str(e)}")
                self.parent_window.storage_work_status_label.setText("未计算")
        # 更新并网状态显示
        if hasattr(self.parent_window, "storage_grid_connection_status"):
            try:
                if storage_item and hasattr(storage_item, 'grid_connected'):
                    grid_connected = storage_item.grid_connected
                    if grid_connected is True:
                        self.parent_window.storage_grid_connection_status.setText("并网")
                        self.parent_window.storage_grid_connection_status.setStyleSheet("font-weight: bold; color: #4CAF50;")
                    else:
                        self.parent_window.storage_grid_connection_status.setText("离网")
                        self.parent_window.storage_grid_connection_status.setStyleSheet("font-weight: bold; color: #F44336;")
                else:
                        self.parent_window.storage_grid_connection_status.setText("离网")
                        self.parent_window.storage_grid_connection_status.setStyleSheet("font-weight: bold; color: #F44336;")
            except Exception as e:
                logger.error(f"更新储能并网状态失败: {str(e)}")
                self.parent_window.storage_grid_connection_status.setText("离网")
                self.parent_window.storage_grid_connection_status.setStyleSheet("font-weight: bold; color: #F44336;")
        # 更新通信状态指示器
        self._update_comm_status_indicator('storage', component_idx)

    def show_realtime_info(self):
        # 根据当前设备类型只调用对应的更新方法
        component_type = getattr(self.parent_window, 'current_component_type', None)
        component_idx = getattr(self.parent_window, 'current_component_idx', None)
        
        if component_type == 'sgen':
            self.update_sgen_realtime_info(component_idx)
        elif component_type == 'storage':
            self.update_storage_realtime_info(component_idx)
        elif component_type == 'load':
            self.update_load_realtime_info(component_idx)
        elif component_type == 'charger':
            self.update_charger_realtime_info(component_idx)
        elif component_type == 'meter':
            self.update_meter_realtime_info(component_idx)

    def on_sgen_variation_changed(self, value):
        """光伏变化幅度改变时的回调"""
        # 获取当前选中的设备索引
        component_idx = getattr(self.parent_window, 'current_component_idx', None)
        # 如果有选中的设备，则为该特定设备设置变化幅度
        if component_idx is not None:
            self.data_generator_manager.set_variation(value, 'sgen', component_idx)
        # 否则只设置光伏设备类型的默认变化幅度
        else:
            self.data_generator_manager.set_variation(value, 'sgen')
            
    def on_season_changed(self, season):
        """季节改变时的回调"""
        season_map = {
            "春季": "spring",
            "夏季": "summer",
            "秋季": "autumn",
            "冬季": "winter"
        }
        season = season_map.get(season, "spring")
        component_idx = getattr(self.parent_window, 'current_component_idx', None)
        if component_idx is not None:
            self.data_generator_manager.set_device_type('sgen', component_idx, season_factor=season)
        else:
            self.data_generator_manager.set_device_type('sgen', season_factor=season)
            
    def on_weather_changed(self, weather_text):
        """天气改变时的回调"""
        # 将中文天气转换为英文表示
        weather_map = {
            "晴朗": "sunny",
            "多云": "cloudy",
            "阴天": "overcast",
            "雨天": "rainy"
        }
        weather_en = weather_map.get(weather_text, "sunny")
        component_idx = getattr(self.parent_window, 'current_component_idx', None)
        if component_idx is not None:
            self.data_generator_manager.set_device_type('sgen', component_idx, weather_type=weather_en)
        else:
            self.data_generator_manager.set_device_type('sgen', weather_type=weather_en)
            # 显示状态消息
            self.parent_window.statusBar().showMessage(f"已设置天气为: {weather_text}")
            
    def on_cloud_cover_changed(self, cloud_cover):
        """云层覆盖度改变时的回调"""
        component_idx = getattr(self.parent_window, 'current_component_idx', None)
        if component_idx is not None:
            self.data_generator_manager.set_device_type('sgen', component_idx, cloud_cover=cloud_cover)
        else:
            self.data_generator_manager.set_device_type('sgen', cloud_cover=cloud_cover)
            # 显示状态消息
            self.parent_window.statusBar().showMessage(f"已设置云层覆盖度: {cloud_cover:.1f}")

    def on_load_variation_changed(self, value):
        """负载变化幅度改变时的回调"""
        # 获取当前选中的设备索引
        component_idx = getattr(self.parent_window, 'current_component_idx', None)
        # 如果有选中的设备，则为该特定设备设置变化幅度
        if component_idx is not None:
            self.data_generator_manager.set_variation(value, 'load', component_idx)
        # 否则只设置负载设备类型的默认变化幅度
        else:
            self.data_generator_manager.set_variation(value, 'load')
    
    
    def on_load_type_changed(self, load_type_text):
        """负载类型改变时的回调"""
        load_type_map = {
            "住宅负载": "residential",
            "商业负载": "commercial", 
            "工业负载": "industrial"
        }
        load_type = load_type_map.get(load_type_text, "residential")
        
        # 获取当前选中的设备索引
        component_idx = getattr(self.parent_window, 'current_component_idx', None)
        # 如果有选中的设备，则为该特定设备设置负载类型
        if component_idx is not None:
            self.data_generator_manager.set_device_type('load', component_idx, load_type=load_type)
        # 否则只设置负载设备类型的默认负载类型
        else:
            self.data_generator_manager.set_device_type('load', None, load_type=load_type)
    
    def on_storage_control_mode_changed(self, state):
        """处理储能设备控制模式切换（手动控制/远程控制）"""
        # 确保对象和属性存在
        if not hasattr(self.parent_window, 'storage_manual_panel'):
            return
            
        # 检查是否启用了远程控制
        is_remote_enabled = False
        if hasattr(self.parent_window, 'storage_enable_remote'):
            is_remote_enabled = self.parent_window.storage_enable_remote.isChecked()
            
        # 根据选择的模式启用或禁用手动控制面板
        # 如果启用了远程控制，则禁用手动控制面板；否则启用手动控制面板
        self.parent_window.storage_manual_panel.setEnabled(not is_remote_enabled)
        
        # 在远程模式下特别禁用功率控制滑块和输入框
        if hasattr(self.parent_window, 'storage_power_slider'):
            self.parent_window.storage_power_slider.setEnabled(not is_remote_enabled)
        if hasattr(self.parent_window, 'storage_power_spinbox'):
            self.parent_window.storage_power_spinbox.setEnabled(not is_remote_enabled)
        
        # 如果切换到远程控制模式，可以在这里添加远程控制的初始化逻辑
        if is_remote_enabled:
            pass  # 远程控制模式的初始化逻辑可以在这里添加
        
        # 更新StorageItem的手动控制模式状态
        if hasattr(self.parent_window, 'current_component_type') and hasattr(self.parent_window, 'current_component_idx'):
            if self.parent_window.current_component_type == 'storage' and hasattr(self.parent_window, 'canvas'):
                component_idx = self.parent_window.current_component_idx
                # 查找对应的StorageItem
                from .network_items import StorageItem
                for item in self.parent_window.canvas.scene.items():
                    if isinstance(item, StorageItem) and item.component_index == component_idx:
                        # 更新手动控制模式状态
                        item.is_manual_control = not is_remote_enabled
                        break
                        
    def on_soc_spinbox_changed(self, value):
        """处理SOC值变化的回调方法
        
        注意：此方法目前未使用。SOC值的更新在用户点击应用按钮时通过apply_storage_settings方法处理。
        保留此方法作为预留接口，以备将来可能需要实现SOC值的实时更新功能。
        """
        pass

    def on_sgen_power_changed(self, value):
        """光伏功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'sgen_power_spinbox'):
            # 滑块值转换为kW值（精确到0.1kW）
            power_value = value / 10.0
            self.parent_window.sgen_power_spinbox.blockSignals(True)
            self.parent_window.sgen_power_spinbox.setValue(power_value)
            self.parent_window.sgen_power_spinbox.blockSignals(False)

    def on_sgen_power_spinbox_changed(self, value):
        """光伏功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'sgen_power_slider'):
            # kW值转换为滑块值（精确到0.1kW）
            slider_value = int(value * 10)
            max_slider = int(self.parent_window.sgen_power_spinbox.maximum() * 10)
            slider_value = max(0, min(max_slider, slider_value))
            self.parent_window.sgen_power_slider.blockSignals(True)
            self.parent_window.sgen_power_slider.setValue(slider_value)
            self.parent_window.sgen_power_slider.blockSignals(False)
    
    def on_sgen_reactive_power_changed(self, value):
        """光伏无功功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'sgen_reactive_power_spinbox'):
            power_value = value / 10.0
            self.parent_window.sgen_reactive_power_spinbox.blockSignals(True)
            self.parent_window.sgen_reactive_power_spinbox.setValue(power_value)
            self.parent_window.sgen_reactive_power_spinbox.blockSignals(False)
    
    def on_sgen_reactive_power_spinbox_changed(self, value):
        """光伏无功功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'sgen_reactive_power_slider'):
            slider_value = int(value * 10)
            min_slider = self.parent_window.sgen_reactive_power_slider.minimum()
            max_slider = self.parent_window.sgen_reactive_power_slider.maximum()
            slider_value = max(min_slider, min(max_slider, slider_value))
            self.parent_window.sgen_reactive_power_slider.blockSignals(True)
            self.parent_window.sgen_reactive_power_slider.setValue(slider_value)
            self.parent_window.sgen_reactive_power_slider.blockSignals(False)
    
    def on_load_power_changed(self, value):
        """负载功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'load_power_spinbox'):
            # 滑块值转换为kW值（精确到0.1kW）
            power_value = value / 10.0
            self.parent_window.load_power_spinbox.blockSignals(True)
            self.parent_window.load_power_spinbox.setValue(power_value)
            self.parent_window.load_power_spinbox.blockSignals(False)
    
    def on_load_power_spinbox_changed(self, value):
        """负载功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'load_power_slider'):
            # kW值转换为滑块值（精确到0.1kW）
            slider_value = int(value * 10)
            
            # 获取当前滑块范围
            min_slider = self.parent_window.load_power_slider.minimum()
            max_slider = self.parent_window.load_power_slider.maximum()
            slider_value = max(min_slider, min(max_slider, slider_value))
            
            self.parent_window.load_power_slider.blockSignals(True)
            self.parent_window.load_power_slider.setValue(slider_value)
            self.parent_window.load_power_slider.blockSignals(False)
    
    def on_load_reactive_power_changed(self, value):
        """负载无功功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'load_reactive_power_spinbox'):
            # 滑块值转换为kvar值（精确到0.1kvar）
            power_value = value / 10.0
            self.parent_window.load_reactive_power_spinbox.blockSignals(True)
            self.parent_window.load_reactive_power_spinbox.setValue(power_value)
            self.parent_window.load_reactive_power_spinbox.blockSignals(False)
    
    def on_load_reactive_power_spinbox_changed(self, value):
        """负载无功功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'load_reactive_power_slider'):
            # kvar值转换为滑块值（精确到0.1kvar）
            slider_value = int(value * 10)
            
            # 获取当前滑块范围
            min_slider = self.parent_window.load_reactive_power_slider.minimum()
            max_slider = self.parent_window.load_reactive_power_slider.maximum()
            slider_value = max(min_slider, min(max_slider, slider_value))
            
            self.parent_window.load_reactive_power_slider.blockSignals(True)
            self.parent_window.load_reactive_power_slider.setValue(slider_value)
            self.parent_window.load_reactive_power_slider.blockSignals(False)
    
    def on_storage_power_changed(self, value):
        """储能功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'storage_power_spinbox'):
            # 滑块值转换为kW值（精确到0.1kW）
            power_value = value / 10.0
            self.parent_window.storage_power_spinbox.blockSignals(True)
            self.parent_window.storage_power_spinbox.setValue(power_value)
            self.parent_window.storage_power_spinbox.blockSignals(False)

    def on_storage_power_spinbox_changed(self, value):
        """储能功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'storage_power_slider'):
            # kW值转换为滑块值（精确到0.1kW）
            slider_value = int(value * 10)
            
            # 获取当前滑块范围
            min_slider = self.parent_window.storage_power_slider.minimum()
            max_slider = self.parent_window.storage_power_slider.maximum()
            slider_value = max(min_slider, min(max_slider, slider_value))
            
            self.parent_window.storage_power_slider.blockSignals(True)
            self.parent_window.storage_power_slider.setValue(slider_value)
            self.parent_window.storage_power_slider.blockSignals(False)

    def on_charger_required_power_changed(self, value):
        """充电桩需求功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'charger_required_power_spinbox'):
            # 滑块值转换为kW值（精确到0.1kW）
            power_value = value / 10.0
            self.parent_window.charger_required_power_spinbox.blockSignals(True)
            self.parent_window.charger_required_power_spinbox.setValue(power_value)
            self.parent_window.charger_required_power_spinbox.blockSignals(False)

    def on_charger_required_power_spinbox_changed(self, value):
        """充电桩需求功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'charger_required_power_slider'):
            # kW值转换为滑块值（精确到0.1kW）
            slider_value = int(value * 10)
            # 使用滑块的当前范围限制值
            min_slider = self.parent_window.charger_required_power_slider.minimum()
            max_slider = self.parent_window.charger_required_power_slider.maximum()
            slider_value = max(min_slider, min(max_slider, slider_value))
            
            self.parent_window.charger_required_power_slider.blockSignals(True)
            self.parent_window.charger_required_power_slider.setValue(slider_value)
            self.parent_window.charger_required_power_slider.blockSignals(False)
    
    
    def apply_sgen_settings(self):
        """应用光伏设备设置"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            QMessageBox.warning(self.parent_window, "警告", "请先选择一个光伏设备")
            return
            
        if self.parent_window.current_component_type != 'sgen':
            QMessageBox.warning(self.parent_window, "警告", "当前选择的不是光伏设备")
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            QMessageBox.warning(self.parent_window, "警告", "网络模型未加载")
            return
            
        component_idx = self.parent_window.current_component_idx
        
        try:
            if component_idx in self.parent_window.network_model.net.sgen.index:
                # 输入框的值为kW，需要转换为MW
                p_kw = self.parent_window.sgen_power_spinbox.value()
                p_mw = p_kw / 1000  # 从kW转换为MW
                q_kvar = 0.0
                if hasattr(self.parent_window, 'sgen_reactive_power_spinbox'):
                    q_kvar = self.parent_window.sgen_reactive_power_spinbox.value()
                q_mvar = max(0.0, q_kvar / 1000.0)
                
                # 光伏设备的功率为负值（发电）
                self.parent_window.network_model.net.sgen.at[component_idx, 'p_mw'] = abs(p_mw)
                self.parent_window.network_model.net.sgen.at[component_idx, 'q_mvar'] = q_mvar
                
                self.parent_window.statusBar().showMessage(f"已更新光伏设备 {component_idx} 的功率设置: P={p_mw:.2f}MW, Q={q_mvar:.2f}MVar")
                logger.debug(f"应用光伏设备 {component_idx} 功率设置: P={p_mw:.2f}MW, Q={q_mvar:.2f}MVar")
            else:
                QMessageBox.warning(self.parent_window, "错误", f"光伏设备 {component_idx} 不存在")
                
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用光伏设置时出错: {str(e)}")
            logger.error(f"应用光伏设置时出错: {e}")
    
    def apply_load_settings(self):
        """应用负载设备设置"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            QMessageBox.warning(self.parent_window, "警告", "请先选择一个负载设备")
            return
            
        if self.parent_window.current_component_type != 'load':
            QMessageBox.warning(self.parent_window, "警告", "当前选择的不是负载设备")
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            QMessageBox.warning(self.parent_window, "警告", "网络模型未加载")
            return
            
        component_idx = self.parent_window.current_component_idx
        
        try:
            if component_idx in self.parent_window.network_model.net.load.index:
                # 输入框值为kW，需要转换为MW
                p_kw = self.parent_window.load_power_spinbox.value()
                p_mw = p_kw / 1000.0  # 转换为MW
                q_kvar = self.parent_window.load_reactive_power_spinbox.value()
                q_mvar = q_kvar / 1000.0
                
                self.parent_window.network_model.net.load.at[component_idx, 'p_mw'] = p_mw
                self.parent_window.network_model.net.load.at[component_idx, 'q_mvar'] = q_mvar
                
                self.parent_window.statusBar().showMessage(f"已更新负载设备 {component_idx} 的功率设置: P={p_mw:.2f}MW, Q={q_mvar:.2f}MVar")
                logger.debug(f"应用负载设备 {component_idx} 功率设置: P={p_mw:.2f}MW, Q={q_mvar:.2f}MVar")
            else:
                QMessageBox.warning(self.parent_window, "错误", f"负载设备 {component_idx} 不存在")
                
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用负载设置时出错: {str(e)}")
            logger.error(f"应用负载设置时出错: {e}")
    
    def apply_storage_settings(self):
        """应用储能设备设置"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            QMessageBox.warning(self.parent_window, "警告", "请先选择一个储能设备")
            return
            
        if self.parent_window.current_component_type != 'storage':
            QMessageBox.warning(self.parent_window, "警告", "当前选择的不是储能设备")
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            QMessageBox.warning(self.parent_window, "警告", "网络模型未加载")
            return
            
        component_idx = self.parent_window.current_component_idx
        
        try:
            if component_idx in self.parent_window.network_model.net.storage.index:
                # 输入框的值为kW，需要转换为MW
                p_kw = self.parent_window.storage_power_spinbox.value()
                p_mw = p_kw / 1000  # 从kW转换为MW
                
                # 直接更新功率值，不受工作状态限制，支持在halt状态下手动控制
                self.parent_window.network_model.net.storage.at[component_idx, 'p_mw'] = -p_mw
                
                # SOC值将直接更新到StorageItem对象中，而不是networkmodel
                
                # 更新对应storage_item的状态
                storage_item = None
                if hasattr(self.parent_window, 'network_items') and 'storage' in self.parent_window.network_items:
                    storage_item = self.parent_window.network_items['storage'].get(component_idx)
                    
                    # 如果在手动控制模式下，更新状态和上电状态
                    if hasattr(storage_item, 'is_manual_control') and storage_item.is_manual_control:
                        # 在手动控制模式下，将设备设置为上电状态
                        storage_item.is_power_on = True
                        
                        # 根据功率值更新充放电状态
                        if p_mw > 0:
                            storage_item.state = 'discharge'  # 放电
                        elif p_mw < 0:
                            storage_item.state = 'charge'  # 充电
                        else:
                            storage_item.state = 'ready'  # 待机
                    
                    # 更新SOC状态到StorageItem的soc_percent属性
                    if hasattr(self.parent_window, 'soc_spinbox') and storage_item:
                        soc_value = self.parent_window.soc_spinbox.value()
                        # 更新对象属性（将百分比转换为0-1之间的值）
                        storage_item.soc_percent = soc_value / 100.0
                        # 同时更新properties字典中的值，保持与soc_percent属性一致（0-1之间的值）
                        if hasattr(storage_item, 'properties') and 'soc_percent' in storage_item.properties:
                            storage_item.properties['soc_percent'] = soc_value / 100.0
                    
                    # 即使在halt状态下也更新UI显示
                    self.update_storage_realtime_info(component_idx)
                
                power_status = "放电" if p_mw > 0 else "充电" if p_mw < 0 else "待机"
                soc_status = f", SOC={soc_value:.1f}%" if hasattr(self.parent_window, 'soc_spinbox') else ""
                self.parent_window.statusBar().showMessage(f"已更新储能设备 {component_idx} 的设置: P={p_mw:.2f}MW ({power_status}){soc_status}")
                logger.debug(f"应用储能设备 {component_idx} 设置: P={p_mw:.2f}MW ({power_status}){soc_status}")
            else:
                QMessageBox.warning(self.parent_window, "错误", f"储能设备 {component_idx} 不存在")
                
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用储能设置时出错: {str(e)}")
            logger.error(f"应用储能设置时出错: {e}")

    def apply_charger_settings(self):
        """应用充电桩设备设置"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            QMessageBox.warning(self.parent_window, "警告", "请先选择一个充电桩设备")
            return
            
        if self.parent_window.current_component_type != 'charger':
            QMessageBox.warning(self.parent_window, "警告", "当前选择的不是充电桩设备")
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            QMessageBox.warning(self.parent_window, "警告", "网络模型未加载")
            return
            
        component_idx = self.parent_window.current_component_idx
        
        try:
            if component_idx in self.parent_window.network_model.net.load.index:
                # 获取需求功率（从UI控件）
                demand_power_kw = self.parent_window.charger_required_power_spinbox.value()
                
                # 获取功率限制（从充电桩设备的额定功率sn_mva）
                # 需要从图形项中获取充电桩的额定功率
                from .network_items import ChargerItem
                charger_item = None
                for item in self.parent_window.canvas.scene.items():
                    if isinstance(item, ChargerItem) and item.component_index == component_idx:
                        charger_item = item
                        break
                
                power_limit_kw = 0
                if charger_item:
                    # 使用item中的power_limit成员值
                    power_limit_kw = charger_item.power_limit * 1000
                    # 存储需求功率到充电桩对象的required_power属性
                    charger_item.required_power = demand_power_kw / 1000
                else:
                    # 如果找不到图形项，使用默认值
                    power_limit_kw = 1000.0  # 默认1MW
                
                # 使用需求功率和功率限制的较小值
                final_power_kw = min(demand_power_kw, power_limit_kw)
                final_power_mw = final_power_kw / 1000.0  # 转换为MW
                
                # 设置充电桩的有功功率
                self.parent_window.network_model.net.load.at[component_idx, 'p_mw'] = final_power_mw
                
                self.parent_window.statusBar().showMessage(f"已更新充电桩设备 {component_idx} 的功率设置: {final_power_kw:.1f}kW (需求功率: {demand_power_kw:.1f}kW, 功率限制: {power_limit_kw:.1f}kW)")
                logger.debug(f"应用充电桩设备 {component_idx} 功率设置: {final_power_kw:.1f}kW (max({demand_power_kw:.1f}kW, {power_limit_kw:.1f}kW))")

            else:
                QMessageBox.warning(self.parent_window, "错误", f"充电桩设备 {component_idx} 不存在")
                
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用充电桩设置时出错: {str(e)}")
            logger.error(f"应用充电桩设置时出错: {e}")
    
    def remove_all_device_tabs(self):
        """移除所有设备相关的选项卡"""
        # 这个方法用于清理设备选项卡，在设备切换时调用
        pass
    
    def update_theme_colors(self):
        """更新主题颜色"""
        # 根据主题更新数据控制相关UI组件的样式
        if hasattr(self.parent_window, 'theme_manager'):
            theme = self.parent_window.theme_manager.current_theme
            
            # 更新复选框样式
            checkbox_style = f"""
                QCheckBox {{
                    color: {theme['text_color']};
                    background-color: {theme['background_color']};
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                }}
                QCheckBox::indicator:unchecked {{
                    border: 2px solid {theme['border_color']};
                    background-color: {theme['input_background']};
                }}
                QCheckBox::indicator:checked {{
                    border: 2px solid {theme['accent_color']};
                    background-color: {theme['accent_color']};
                }}
            """
            
            # 更新数值输入框样式
            spinbox_style = f"""
                QSpinBox, QDoubleSpinBox {{
                    color: {theme['text_color']};
                    background-color: {theme['input_background']};
                    border: 1px solid {theme['border_color']};
                    padding: 4px;
                    border-radius: 4px;
                }}
                QSpinBox:focus, QDoubleSpinBox:focus {{
                    border: 2px solid {theme['accent_color']};
                }}
            """
            
            # 应用样式到相关组件
            for attr_name in dir(self.parent_window):
                if 'checkbox' in attr_name.lower():
                    widget = getattr(self.parent_window, attr_name, None)
                    if hasattr(widget, 'setStyleSheet'):
                        widget.setStyleSheet(checkbox_style)
                elif 'spinbox' in attr_name.lower():
                    widget = getattr(self.parent_window, attr_name, None)
                    if hasattr(widget, 'setStyleSheet'):
                        widget.setStyleSheet(spinbox_style)
