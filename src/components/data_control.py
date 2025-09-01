"""数据生成器控制模块
提供设备数据生成的UI控制和管理功能
"""

import time
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QCheckBox, QDoubleSpinBox, QSpinBox, QSlider, QRadioButton, QPushButton,
    QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from .data_generators import DataGeneratorManager


class DataControlManager:
    """数据生成器控制管理类"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.data_generator_manager = DataGeneratorManager()
        
        
    def create_sgen_data_generation_tab(self):
        """创建光伏设备专用的数据生成控制选项卡"""
        layout = QVBoxLayout(self.parent_window.sgen_data_tab)
        
        # 当前选择设备信息
        current_device_group = QGroupBox("当前选择光伏设备")
        current_device_layout = QVBoxLayout(current_device_group)
        
        self.parent_window.sgen_current_device_label = QLabel("未选择光伏设备")
        self.parent_window.sgen_current_device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        current_device_layout.addWidget(self.parent_window.sgen_current_device_label)
        
        # 设备数据生成控制
        device_control_layout = QHBoxLayout()
        self.parent_window.sgen_enable_generation_checkbox = QCheckBox("启用设备数据生成")
        self.parent_window.sgen_enable_generation_checkbox.stateChanged.connect(self.toggle_sgen_data_generation)
        device_control_layout.addWidget(self.parent_window.sgen_enable_generation_checkbox)
        
        current_device_layout.addLayout(device_control_layout)
        layout.addWidget(current_device_group)
        
        # 光伏专用参数设置
        sgen_params_group = QGroupBox("光伏发电参数设置")
        sgen_params_layout = QFormLayout(sgen_params_group)
        
        # 变化幅度
        self.parent_window.sgen_variation_spinbox = QDoubleSpinBox()
        self.parent_window.sgen_variation_spinbox.setRange(0.0, 50.0)
        self.parent_window.sgen_variation_spinbox.setValue(15.0)
        self.parent_window.sgen_variation_spinbox.setSuffix("%")
        self.parent_window.sgen_variation_spinbox.valueChanged.connect(self.on_sgen_variation_changed)
        sgen_params_layout.addRow("功率变化幅度:", self.parent_window.sgen_variation_spinbox)
        
        layout.addWidget(sgen_params_group)
        
        # 光伏手动控制面板
        self.parent_window.sgen_manual_panel = QWidget()
        sgen_manual_layout = QFormLayout(self.parent_window.sgen_manual_panel)
        
        # 光伏功率控制
        self.parent_window.sgen_power_slider = QSlider(Qt.Horizontal)
        self.parent_window.sgen_power_slider.setRange(0, 200)  # 0-20MW
        self.parent_window.sgen_power_slider.setValue(100)
        self.parent_window.sgen_power_slider.setMinimumWidth(100)
        self.parent_window.sgen_power_slider.valueChanged.connect(self.on_sgen_power_changed)
        
        self.parent_window.sgen_power_spinbox = QDoubleSpinBox()
        self.parent_window.sgen_power_spinbox.setRange(0.0, 20.0)
        self.parent_window.sgen_power_spinbox.setValue(10.0)
        self.parent_window.sgen_power_spinbox.setSuffix(" MW")
        self.parent_window.sgen_power_spinbox.valueChanged.connect(self.on_sgen_power_spinbox_changed)
        
        sgen_power_layout = QHBoxLayout()
        sgen_power_layout.addWidget(self.parent_window.sgen_power_slider)
        sgen_power_layout.addWidget(self.parent_window.sgen_power_spinbox)
        sgen_manual_layout.addRow("发电功率:", sgen_power_layout)
        
        # 应用按钮
        sgen_apply_button = QPushButton("应用光伏设置")
        sgen_apply_button.clicked.connect(self.apply_sgen_settings)
        sgen_manual_layout.addRow("", sgen_apply_button)
        
        self.parent_window.sgen_manual_panel.setVisible(True)  # 默认显示手动控制面板
        layout.addWidget(self.parent_window.sgen_manual_panel)
        
        layout.addStretch()
        
    def create_load_data_generation_tab(self):
        """创建负载设备专用的数据生成控制选项卡"""
        layout = QVBoxLayout(self.parent_window.load_data_tab)
        
        # 当前选择设备信息
        current_device_group = QGroupBox("当前选择负载设备")
        current_device_layout = QVBoxLayout(current_device_group)
        
        self.parent_window.load_current_device_label = QLabel("未选择负载设备")
        self.parent_window.load_current_device_label.setStyleSheet("font-weight: bold; color: #F44336;")
        current_device_layout.addWidget(self.parent_window.load_current_device_label)
        
        # 设备数据生成控制
        device_control_layout = QHBoxLayout()
        self.parent_window.load_enable_generation_checkbox = QCheckBox("启用设备数据生成")
        self.parent_window.load_enable_generation_checkbox.stateChanged.connect(self.toggle_load_data_generation)
        device_control_layout.addWidget(self.parent_window.load_enable_generation_checkbox)
        
        current_device_layout.addLayout(device_control_layout)
        layout.addWidget(current_device_group)
        
        # 负载专用参数设置
        load_params_group = QGroupBox("负载用电参数设置")
        load_params_layout = QFormLayout(load_params_group)
        
        # 变化幅度
        self.parent_window.load_variation_spinbox = QDoubleSpinBox()
        self.parent_window.load_variation_spinbox.setRange(0.0, 50.0)
        self.parent_window.load_variation_spinbox.setValue(10.0)
        self.parent_window.load_variation_spinbox.setSuffix("%")
        self.parent_window.load_variation_spinbox.valueChanged.connect(self.on_load_variation_changed)
        load_params_layout.addRow("功率变化幅度:", self.parent_window.load_variation_spinbox)
        
        # 负载类型选择
        self.parent_window.load_type_combo = QComboBox()
        self.parent_window.load_type_combo.addItems(["住宅负载", "商业负载", "工业负载"])
        self.parent_window.load_type_combo.currentTextChanged.connect(self.on_load_type_changed)
        load_params_layout.addRow("负载类型:", self.parent_window.load_type_combo)
        
        layout.addWidget(load_params_group)
        
        # 负载手动控制面板
        self.parent_window.load_manual_panel = QWidget()
        load_manual_layout = QFormLayout(self.parent_window.load_manual_panel)
        
        # 负载有功功率控制
        self.parent_window.load_power_slider = QSlider(Qt.Horizontal)
        self.parent_window.load_power_slider.setRange(0, 200)  # 0-100MW
        self.parent_window.load_power_slider.setValue(100)
        self.parent_window.load_power_slider.setMinimumWidth(100)
        self.parent_window.load_power_slider.valueChanged.connect(self.on_load_power_changed)
        
        self.parent_window.load_power_spinbox = QDoubleSpinBox()
        self.parent_window.load_power_spinbox.setRange(0.0, 100.0)
        self.parent_window.load_power_spinbox.setValue(50.0)
        self.parent_window.load_power_spinbox.setSuffix(" MW")
        self.parent_window.load_power_spinbox.valueChanged.connect(self.on_load_power_spinbox_changed)
        
        load_power_layout = QHBoxLayout()
        load_power_layout.addWidget(self.parent_window.load_power_slider)
        load_power_layout.addWidget(self.parent_window.load_power_spinbox)
        load_manual_layout.addRow("有功功率:", load_power_layout)
        
        # 负载无功功率控制
        self.parent_window.load_reactive_power_slider = QSlider(Qt.Horizontal)
        self.parent_window.load_reactive_power_slider.setRange(0, 200)  # 0-50MVar
        self.parent_window.load_reactive_power_slider.setValue(50)
        self.parent_window.load_reactive_power_slider.setMinimumWidth(100)
        self.parent_window.load_reactive_power_slider.valueChanged.connect(self.on_load_reactive_power_changed)
        
        self.parent_window.load_reactive_power_spinbox = QDoubleSpinBox()
        self.parent_window.load_reactive_power_spinbox.setRange(0.0, 50.0)
        self.parent_window.load_reactive_power_spinbox.setValue(12.5)
        self.parent_window.load_reactive_power_spinbox.setSuffix(" MVar")
        self.parent_window.load_reactive_power_spinbox.valueChanged.connect(self.on_load_reactive_power_spinbox_changed)
        
        load_reactive_power_layout = QHBoxLayout()
        load_reactive_power_layout.addWidget(self.parent_window.load_reactive_power_slider)
        load_reactive_power_layout.addWidget(self.parent_window.load_reactive_power_spinbox)
        load_manual_layout.addRow("无功功率:", load_reactive_power_layout)
        
        # 应用按钮
        load_apply_button = QPushButton("应用负载设置")
        load_apply_button.clicked.connect(self.apply_load_settings)
        load_manual_layout.addRow("", load_apply_button)
        
        self.parent_window.load_manual_panel.setVisible(True)  # 默认显示手动控制面板
        layout.addWidget(self.parent_window.load_manual_panel)
        
        layout.addStretch()
        
    def create_storage_data_generation_tab(self):
        """创建储能设备专用的手动控制选项卡"""
        layout = QVBoxLayout(self.parent_window.storage_data_tab)
        
        # 当前选择设备信息
        current_device_group = QGroupBox("当前选择储能设备")
        current_device_layout = QVBoxLayout(current_device_group)
        
        self.parent_window.storage_current_device_label = QLabel("未选择储能设备")
        self.parent_window.storage_current_device_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        current_device_layout.addWidget(self.parent_window.storage_current_device_label)
        
        layout.addWidget(current_device_group)
        
        # 储能手动控制
        storage_manual_group = QGroupBox("储能手动功率控制")
        storage_manual_layout = QVBoxLayout(storage_manual_group)
        
        # 手动控制面板
        self.parent_window.storage_manual_panel = QWidget()
        storage_manual_panel_layout = QFormLayout(self.parent_window.storage_manual_panel)
        
        # 有功功率控制（正值为放电，负值为充电）
        self.parent_window.storage_power_slider = QSlider(Qt.Horizontal)
        self.parent_window.storage_power_slider.setRange(-1000, 1000)  # 滑块范围：-100.0到100.0MW（乘以10）
        self.parent_window.storage_power_slider.setValue(0)
        self.parent_window.storage_power_slider.setMinimumWidth(300)
        self.parent_window.storage_power_slider.valueChanged.connect(self.on_storage_power_changed)
        
        self.parent_window.storage_power_spinbox = QDoubleSpinBox()
        self.parent_window.storage_power_spinbox.setRange(-100.0, 100.0)
        self.parent_window.storage_power_spinbox.setValue(0.0)
        self.parent_window.storage_power_spinbox.setSuffix(" MW")
        self.parent_window.storage_power_spinbox.valueChanged.connect(self.on_storage_power_spinbox_changed)
        
        storage_power_layout = QHBoxLayout()
        storage_power_layout.addWidget(self.parent_window.storage_power_slider)
        storage_power_layout.addWidget(self.parent_window.storage_power_spinbox)
        storage_manual_panel_layout.addRow("功率控制 (正值=放电, 负值=充电):", storage_power_layout)
        
        # 功率说明标签
        power_info_label = QLabel("提示：正值表示放电（向电网供电），负值表示充电（从电网取电）")
        power_info_label.setStyleSheet("color: #666; font-size: 12px;")
        storage_manual_panel_layout.addRow("", power_info_label)
        
        # 应用按钮
        storage_apply_button = QPushButton("应用储能设置")
        storage_apply_button.clicked.connect(self.apply_storage_settings)
        storage_manual_panel_layout.addRow("", storage_apply_button)
        
        self.parent_window.storage_manual_panel.setVisible(True)  # 默认显示手动控制面板
        storage_manual_layout.addWidget(self.parent_window.storage_manual_panel)
        layout.addWidget(storage_manual_group)
        
        layout.addStretch()
        
    # 数据生成状态管理方法
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
    
    def toggle_storage_data_generation(self, state):
        """切换储能设备的数据生成状态"""
        self._toggle_device_data_generation(state, 'storage')
    
    def _toggle_device_data_generation(self, state, device_type):
        """切换指定类型设备的数据生成状态"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            return
            
        if self.parent_window.current_component_type != device_type:
            return
            
        device_key = f"{self.parent_window.current_component_type}_{self.parent_window.current_component_idx}"
        device_name = f"{self.parent_window.current_component_type}_{self.parent_window.current_component_idx}"
        
        # 设备类型映射
        device_type_map = {
            'load': '负载',
            'sgen': '光伏', 
            'storage': '储能'
        }
        device_type_name = device_type_map.get(device_type, device_type)
        
        # 面板映射
        panel_map = {
            'load': 'load_manual_panel',
            'sgen': 'sgen_manual_panel', 
            'storage': 'storage_manual_panel'
        }
        
        # 更新方法映射
        update_method_map = {
            'load': self.update_load_manual_controls_from_device,
            'sgen': self.update_sgen_manual_controls_from_device,
            'storage': self.update_storage_manual_controls_from_device
        }
        
        # 获取当前设备类型对应的面板和方法
        current_panel_name = panel_map.get(device_type)
        current_update_method = update_method_map.get(device_type)
        
        if state == 2:  # 选中状态 - 启用数据生成
            if device_key not in self.parent_window.generated_devices:
                self.parent_window.generated_devices.add(device_key)
                
                # 只隐藏当前设备类型的手动面板
                if current_panel_name and hasattr(self.parent_window, current_panel_name):
                    getattr(self.parent_window, current_panel_name).setVisible(False)
                
                self.parent_window.statusBar().showMessage(f"已启用{device_type_name}设备 {self.parent_window.current_component_idx} 的数据生成")
                print(f"启用设备 {device_name} 的数据生成")
            else:
                self.parent_window.statusBar().showMessage(f"设备 {device_name} 已在数据生成列表中")
        else:  # 未选中状态 - 禁用数据生成
            if device_key in self.parent_window.generated_devices:
                self.parent_window.generated_devices.remove(device_key)
                
                # 只显示当前设备类型的手动面板
                if current_panel_name and hasattr(self.parent_window, current_panel_name):
                    getattr(self.parent_window, current_panel_name).setVisible(True)
                
                # 只更新当前设备类型的手动控制
                if current_update_method:
                    current_update_method()
                
                self.parent_window.statusBar().showMessage(f"已禁用{device_type_name}设备 {self.parent_window.current_component_idx} 的数据生成")
                print(f"禁用设备 {device_name} 的数据生成")
            else:
                self.parent_window.statusBar().showMessage(f"设备 {device_name} 未在数据生成列表中")
    
    def toggle_device_data_generation(self, state):
        """切换当前设备的数据生成状态（保留兼容性）"""
        if hasattr(self.parent_window, 'current_component_type'):
            if self.parent_window.current_component_type == 'sgen':
                self.toggle_sgen_data_generation(state)
            elif self.parent_window.current_component_type == 'load':
                self.toggle_load_data_generation(state)
            elif self.parent_window.current_component_type == 'storage':
                self.toggle_storage_data_generation(state)
    
    # 参数变化回调方法
    def on_variation_changed(self, value):
        """变化幅度改变时的回调"""
        self.data_generator_manager.set_variation('load', value)
        self.data_generator_manager.set_variation('sgen', value)
    
    def on_interval_changed(self, value):
        """生成间隔改变时的回调"""
        self.data_generator_manager.set_interval('load', value)
        self.data_generator_manager.set_interval('sgen', value)
    
    def on_sgen_variation_changed(self, value):
        """光伏变化幅度改变时的回调"""
        self.data_generator_manager.set_variation('sgen', value)
    
    def on_sgen_interval_changed(self, value):
        """光伏生成间隔改变时的回调"""
        self.data_generator_manager.set_interval('sgen', value)
    
    def on_load_variation_changed(self, value):
        """负载变化幅度改变时的回调"""
        self.data_generator_manager.set_variation('load', value)
    
    def on_load_interval_changed(self, value):
        """负载生成间隔改变时的回调"""
        self.data_generator_manager.set_interval('load', value)
    
    def on_load_type_changed(self, load_type_text):
        """负载类型改变时的回调"""
        load_type_map = {
            "住宅负载": "residential",
            "商业负载": "commercial", 
            "工业负载": "industrial"
        }
        load_type = load_type_map.get(load_type_text, "residential")
        self.data_generator_manager.set_load_type(load_type)
    
    # 模式切换回调方法
    def on_sgen_mode_changed(self):
        """光伏设备数据生成模式改变时的回调"""
        is_manual = self.parent_window.sgen_manual_mode_radio.isChecked()
        self.parent_window.sgen_manual_panel.setVisible(is_manual)
        
        # 如果切换到手动模式，停止自动数据生成
        if is_manual and hasattr(self.parent_window, 'sgen_enable_generation_checkbox'):
            if self.parent_window.sgen_enable_generation_checkbox.isChecked():
                self.parent_window.sgen_enable_generation_checkbox.setChecked(False)
        
        # 更新当前设备的功率值到滑块和输入框
        if is_manual:
            self.update_sgen_manual_controls_from_device()
    
    def on_load_mode_changed(self):
        """负载设备数据生成模式改变时的回调"""
        is_manual = self.parent_window.load_manual_mode_radio.isChecked()
        self.parent_window.load_manual_panel.setVisible(is_manual)
        
        # 如果切换到手动模式，停止自动数据生成
        if is_manual and hasattr(self.parent_window, 'load_enable_generation_checkbox'):
            if self.parent_window.load_enable_generation_checkbox.isChecked():
                self.parent_window.load_enable_generation_checkbox.setChecked(False)
        
        # 更新当前设备的功率值到滑块和输入框
        if is_manual:
            self.update_load_manual_controls_from_device()
    
    def on_storage_mode_changed(self):
        """储能设备数据生成模式改变时的回调"""
        is_manual = self.parent_window.storage_manual_mode_radio.isChecked()
        self.parent_window.storage_manual_panel.setVisible(is_manual)
        
        # 更新当前设备的功率值到滑块和输入框
        if is_manual:
            self.update_storage_manual_controls_from_device()
    
    def on_generation_mode_changed(self):
        """数据生成模式改变时的回调（保留兼容性）"""
        is_manual = self.parent_window.manual_mode_radio.isChecked()
        self.parent_window.manual_control_panel.setVisible(is_manual)
        
        # 如果切换到手动模式，停止自动数据生成
        if is_manual and hasattr(self.parent_window, 'enable_device_generation_checkbox'):
            if self.parent_window.enable_device_generation_checkbox.isChecked():
                self.parent_window.enable_device_generation_checkbox.setChecked(False)
        
        # 更新当前设备的功率值到滑块和输入框
        if is_manual:
            self.update_manual_controls_from_device()
    
    # 手动控制更新方法
    def update_sgen_manual_controls_from_device(self):
        """从当前光伏设备更新手动控制组件的值"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            return
            
        if self.parent_window.current_component_type != 'sgen':
            return
            
        try:
            # 获取光伏设备的当前功率值
            current_power = self.parent_window.network_model.net.sgen.at[self.parent_window.current_component_idx, 'p_mw']
            
            # 更新滑块和输入框的值
            if hasattr(self.parent_window, 'sgen_power_slider'):
                self.parent_window.sgen_power_slider.setValue(int(abs(current_power) * 10))  # 转换为滑块值
            if hasattr(self.parent_window, 'sgen_power_spinbox'):
                self.parent_window.sgen_power_spinbox.setValue(abs(current_power))
        except Exception as e:
            print(f"更新光伏设备手动控制值时出错: {e}")
    
    def update_load_manual_controls_from_device(self):
        """从当前负载设备更新手动控制组件的值"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            return
            
        if self.parent_window.current_component_type != 'load':
            return
            
        try:
            # 获取负载设备的当前功率值
            current_p = self.parent_window.network_model.net.load.at[self.parent_window.current_component_idx, 'p_mw']
            current_q = self.parent_window.network_model.net.load.at[self.parent_window.current_component_idx, 'q_mvar']
            
            # 更新滑块和输入框的值
            if hasattr(self.parent_window, 'load_power_slider'):
                self.parent_window.load_power_slider.setValue(int(current_p * 2))  # 转换为滑块值
            if hasattr(self.parent_window, 'load_power_spinbox'):
                self.parent_window.load_power_spinbox.setValue(current_p)
            if hasattr(self.parent_window, 'load_reactive_power_slider'):
                self.parent_window.load_reactive_power_slider.setValue(int(current_q * 4))  # 转换为滑块值
            if hasattr(self.parent_window, 'load_reactive_power_spinbox'):
                self.parent_window.load_reactive_power_spinbox.setValue(current_q)
        except Exception as e:
            print(f"更新负载设备手动控制值时出错: {e}")
    
    def update_storage_manual_controls_from_device(self):
        """从当前储能设备更新手动控制组件的值"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            return
            
        if self.parent_window.current_component_type != 'storage':
            return
            
        try:
            # 获取储能设备的当前功率值
            current_power = self.parent_window.network_model.net.storage.at[self.parent_window.current_component_idx, 'p_mw']
            
            # 更新滑块和输入框的值
            if hasattr(self.parent_window, 'storage_power_slider'):
                self.parent_window.storage_power_slider.setValue(int(current_power * 10))  # 转换为滑块值
            if hasattr(self.parent_window, 'storage_power_spinbox'):
                self.parent_window.storage_power_spinbox.setValue(current_power)
        except Exception as e:
            print(f"更新储能设备手动控制值时出错: {e}")
    
    def update_manual_controls_from_device(self):
        """从当前设备更新手动控制组件的值（保留兼容性）"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            return
            
        component_type = self.parent_window.current_component_type
        component_idx = self.parent_window.current_component_idx
        
        try:
            if component_type == 'load':
                if component_idx < len(self.parent_window.network_model.net.load):
                    p_mw = self.parent_window.network_model.net.load.loc[component_idx, 'p_mw']
                    q_mvar = self.parent_window.network_model.net.load.loc[component_idx, 'q_mvar']
                    
                    # 获取额定功率，如果不存在则使用默认值1.0
                    if 'p_mw_rated' in self.parent_window.network_model.net.load.columns:
                        rated_power = self.parent_window.network_model.net.load.loc[component_idx, 'p_mw_rated']
                        self.parent_window.base_power_value = abs(rated_power) if rated_power != 0 else 1.0
                    else:
                        self.parent_window.base_power_value = 1.0
                    
                    if 'q_mvar_rated' in self.parent_window.network_model.net.load.columns:
                        rated_reactive = self.parent_window.network_model.net.load.loc[component_idx, 'q_mvar_rated']
                        self.parent_window.base_reactive_power_value = abs(rated_reactive) if rated_reactive != 0 else 0.5
                    else:
                        self.parent_window.base_reactive_power_value = 0.5
                    
                    # 更新滑块和输入框的值
                    if hasattr(self.parent_window, 'power_slider') and self.parent_window.base_power_value > 0:
                        percentage = int((p_mw / self.parent_window.base_power_value) * 100)
                        percentage = max(0, min(200, percentage))
                        self.parent_window.power_slider.blockSignals(True)
                        self.parent_window.power_slider.setValue(percentage)
                        self.parent_window.power_slider.blockSignals(False)
                    
                    if hasattr(self.parent_window, 'power_spinbox'):
                        self.parent_window.power_spinbox.blockSignals(True)
                        self.parent_window.power_spinbox.setValue(p_mw)
                        self.parent_window.power_spinbox.blockSignals(False)
                    
                    if hasattr(self.parent_window, 'reactive_power_slider') and self.parent_window.base_reactive_power_value > 0:
                        percentage = int((q_mvar / self.parent_window.base_reactive_power_value) * 100)
                        percentage = max(0, min(200, percentage))
                        self.parent_window.reactive_power_slider.blockSignals(True)
                        self.parent_window.reactive_power_slider.setValue(percentage)
                        self.parent_window.reactive_power_slider.blockSignals(False)
                    
                    if hasattr(self.parent_window, 'reactive_power_spinbox'):
                        self.parent_window.reactive_power_spinbox.blockSignals(True)
                        self.parent_window.reactive_power_spinbox.setValue(q_mvar)
                        self.parent_window.reactive_power_spinbox.blockSignals(False)
                        
            elif component_type == 'sgen':
                if component_idx < len(self.parent_window.network_model.net.sgen):
                    p_mw = abs(self.parent_window.network_model.net.sgen.loc[component_idx, 'p_mw'])
                    
                    # 获取额定功率，如果不存在则使用默认值10.0
                    if 'p_mw_rated' in self.parent_window.network_model.net.sgen.columns:
                        rated_power = self.parent_window.network_model.net.sgen.loc[component_idx, 'p_mw_rated']
                        self.parent_window.base_power_value = abs(rated_power) if rated_power != 0 else 10.0
                    else:
                        self.parent_window.base_power_value = 10.0
                    
                    # 更新滑块和输入框的值
                    if hasattr(self.parent_window, 'power_slider') and self.parent_window.base_power_value > 0:
                        percentage = int((p_mw / self.parent_window.base_power_value) * 100)
                        percentage = max(0, min(200, percentage))
                        self.parent_window.power_slider.blockSignals(True)
                        self.parent_window.power_slider.setValue(percentage)
                        self.parent_window.power_slider.blockSignals(False)
                    
                    if hasattr(self.parent_window, 'power_spinbox'):
                        self.parent_window.power_spinbox.blockSignals(True)
                        self.parent_window.power_spinbox.setValue(p_mw)
                        self.parent_window.power_spinbox.blockSignals(False)
                        
            elif component_type == 'storage':
                if component_idx < len(self.parent_window.network_model.net.storage):
                    p_mw = self.parent_window.network_model.net.storage.loc[component_idx, 'p_mw']
                    
                    # 获取额定功率，如果不存在则使用默认值50.0
                    if 'p_mw_rated' in self.parent_window.network_model.net.storage.columns:
                        rated_power = self.parent_window.network_model.net.storage.loc[component_idx, 'p_mw_rated']
                        self.parent_window.base_power_value = abs(rated_power) if rated_power != 0 else 50.0
                    else:
                        self.parent_window.base_power_value = 50.0
                    
                    # 更新滑块和输入框的值
                    if hasattr(self.parent_window, 'power_slider'):
                        # 储能设备的滑块范围是-200%到200%，对应-2倍到2倍额定功率
                        percentage = int((p_mw / self.parent_window.base_power_value) * 100)
                        percentage = max(-200, min(200, percentage))
                        self.parent_window.power_slider.blockSignals(True)
                        self.parent_window.power_slider.setValue(percentage)
                        self.parent_window.power_slider.blockSignals(False)
                    
                    if hasattr(self.parent_window, 'power_spinbox'):
                        self.parent_window.power_spinbox.blockSignals(True)
                        self.parent_window.power_spinbox.setValue(p_mw)
                        self.parent_window.power_spinbox.blockSignals(False)
                        
        except Exception as e:
            print(f"更新手动控制值时出错: {e}")
    
    # 滑块和输入框变化回调方法
    def on_manual_power_changed(self, value):
        """手动功率滑块改变时的回调"""
        # 将滑块值（0-200%）转换为实际功率值
        if hasattr(self.parent_window, 'power_spinbox') and hasattr(self.parent_window, 'base_power_value'):
            # 使用基准功率值计算实际功率
            new_power = self.parent_window.base_power_value * (value / 100.0)
            # 暂时断开信号连接，避免循环调用
            self.parent_window.power_spinbox.blockSignals(True)
            self.parent_window.power_spinbox.setValue(new_power)
            self.parent_window.power_spinbox.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_manual_power_spinbox_changed(self, value):
        """手动功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'power_slider') and hasattr(self.parent_window, 'base_power_value') and self.parent_window.base_power_value > 0:
            percentage = int((value / self.parent_window.base_power_value) * 100)
            percentage = max(0, min(200, percentage))  # 限制在0-200%范围内
            self.parent_window.power_slider.blockSignals(True)
            self.parent_window.power_slider.setValue(percentage)
            self.parent_window.power_slider.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_manual_reactive_power_changed(self, value):
        """手动无功功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'reactive_power_spinbox') and hasattr(self.parent_window, 'base_reactive_power_value'):
            # 使用基准无功功率值计算实际功率
            new_power = self.parent_window.base_reactive_power_value * (value / 100.0)
            self.parent_window.reactive_power_spinbox.blockSignals(True)
            self.parent_window.reactive_power_spinbox.setValue(new_power)
            self.parent_window.reactive_power_spinbox.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_manual_reactive_power_spinbox_changed(self, value):
        """手动无功功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'reactive_power_slider') and hasattr(self.parent_window, 'base_reactive_power_value') and self.parent_window.base_reactive_power_value > 0:
            percentage = int((value / self.parent_window.base_reactive_power_value) * 100)
            percentage = max(0, min(200, percentage))  # 限制在0-200%范围内
            self.parent_window.reactive_power_slider.blockSignals(True)
            self.parent_window.reactive_power_slider.setValue(percentage)
            self.parent_window.reactive_power_slider.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_sgen_power_changed(self, value):
        """光伏功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'sgen_power_spinbox'):
            # 滑块值直接对应功率值
            power_value = value / 10.0  # 滑块范围0-200对应0-20MW
            self.parent_window.sgen_power_spinbox.blockSignals(True)
            self.parent_window.sgen_power_spinbox.setValue(power_value)
            self.parent_window.sgen_power_spinbox.blockSignals(False)
    
    def on_sgen_power_spinbox_changed(self, value):
        """光伏功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'sgen_power_slider'):
            # 功率值转换为滑块值
            slider_value = int(value * 10)  # 功率值*10对应滑块值
            slider_value = max(0, min(200, slider_value))
            self.parent_window.sgen_power_slider.blockSignals(True)
            self.parent_window.sgen_power_slider.setValue(slider_value)
            self.parent_window.sgen_power_slider.blockSignals(False)
    
    def on_load_power_changed(self, value):
        """负载功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'load_power_spinbox'):
            # 滑块值直接对应功率值
            power_value = value / 2.0  # 滑块范围0-200对应0-100MW
            self.parent_window.load_power_spinbox.blockSignals(True)
            self.parent_window.load_power_spinbox.setValue(power_value)
            self.parent_window.load_power_spinbox.blockSignals(False)
    
    def on_load_power_spinbox_changed(self, value):
        """负载功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'load_power_slider'):
            # 功率值转换为滑块值
            slider_value = int(value * 2)  # 功率值*2对应滑块值
            slider_value = max(0, min(200, slider_value))
            self.parent_window.load_power_slider.blockSignals(True)
            self.parent_window.load_power_slider.setValue(slider_value)
            self.parent_window.load_power_slider.blockSignals(False)
    
    def on_load_reactive_power_changed(self, value):
        """负载无功功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'load_reactive_power_spinbox'):
            # 滑块值直接对应无功功率值
            power_value = value / 4.0  # 滑块范围0-200对应0-50MVar
            self.parent_window.load_reactive_power_spinbox.blockSignals(True)
            self.parent_window.load_reactive_power_spinbox.setValue(power_value)
            self.parent_window.load_reactive_power_spinbox.blockSignals(False)
    
    def on_load_reactive_power_spinbox_changed(self, value):
        """负载无功功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'load_reactive_power_slider'):
            # 无功功率值转换为滑块值
            slider_value = int(value * 4)  # 功率值*4对应滑块值
            slider_value = max(0, min(200, slider_value))
            self.parent_window.load_reactive_power_slider.blockSignals(True)
            self.parent_window.load_reactive_power_slider.setValue(slider_value)
            self.parent_window.load_reactive_power_slider.blockSignals(False)
    
    def on_storage_power_changed(self, value):
        """储能功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'storage_power_spinbox'):
            # 滑块值除以10得到实际功率值（MW）
            new_power = value / 10.0
            self.parent_window.storage_power_spinbox.blockSignals(True)
            self.parent_window.storage_power_spinbox.setValue(new_power)
            self.parent_window.storage_power_spinbox.blockSignals(False)
    
    def on_storage_power_spinbox_changed(self, value):
        """储能功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'storage_power_slider'):
            # 功率值乘以10得到滑块值
            slider_value = int(value * 10)
            slider_value = max(-1000, min(1000, slider_value))
            self.parent_window.storage_power_slider.blockSignals(True)
            self.parent_window.storage_power_slider.setValue(slider_value)
            self.parent_window.storage_power_slider.blockSignals(False)
    
    # 功率设置应用方法
    def apply_manual_power_settings(self):
        """应用手动功率设置到网络模型"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            QMessageBox.warning(self.parent_window, "警告", "请先选择一个设备")
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            QMessageBox.warning(self.parent_window, "警告", "网络模型未加载")
            return
            
        component_type = self.parent_window.current_component_type
        component_idx = self.parent_window.current_component_idx
        
        try:
            if component_type == 'load':
                if component_idx in self.parent_window.network_model.net.load.index:
                    p_mw = self.parent_window.power_spinbox.value()
                    q_mvar = self.parent_window.reactive_power_spinbox.value()
                    
                    self.parent_window.network_model.net.load.loc[component_idx, 'p_mw'] = p_mw
                    self.parent_window.network_model.net.load.loc[component_idx, 'q_mvar'] = q_mvar
                    
                    
                    self.parent_window.statusBar().showMessage(f"已更新负载设备 {component_idx} 的功率设置: P={p_mw:.2f}MW, Q={q_mvar:.2f}MVar")
                    print(f"应用负载设备 {component_idx} 功率设置: P={p_mw:.2f}MW, Q={q_mvar:.2f}MVar")
                else:
                    QMessageBox.warning(self.parent_window, "错误", f"负载设备 {component_idx} 不存在")
                    
            elif component_type == 'sgen':
                if component_idx in self.parent_window.network_model.net.sgen.index:
                    p_mw = self.parent_window.power_spinbox.value()
                    
                    # 光伏设备的功率为负值（发电）
                    self.parent_window.network_model.net.sgen.loc[component_idx, 'p_mw'] = -abs(p_mw)
                    
                    self.parent_window.statusBar().showMessage(f"已更新光伏设备 {component_idx} 的功率设置: P={p_mw:.2f}MW")
                    print(f"应用光伏设备 {component_idx} 功率设置: P={p_mw:.2f}MW")
                else:
                    QMessageBox.warning(self.parent_window, "错误", f"光伏设备 {component_idx} 不存在")
                    
            elif component_type == 'storage':
                if component_idx in self.parent_window.network_model.net.storage.index:
                    p_mw = self.parent_window.power_spinbox.value()
                    
                    self.parent_window.network_model.net.storage.loc[component_idx, 'p_mw'] = p_mw
                    
                    power_status = "放电" if p_mw > 0 else "充电" if p_mw < 0 else "待机"
                    self.parent_window.statusBar().showMessage(f"已更新储能设备 {component_idx} 的功率设置: P={p_mw:.2f}MW ({power_status})")
                    print(f"应用储能设备 {component_idx} 功率设置: P={p_mw:.2f}MW ({power_status})")
                else:
                    QMessageBox.warning(self.parent_window, "错误", f"储能设备 {component_idx} 不存在")
                    
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用功率设置时出错: {str(e)}")
            print(f"应用功率设置时出错: {e}")
    
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
                p_mw = self.parent_window.sgen_power_spinbox.value()
                
                # 光伏设备的功率为负值（发电）
                self.parent_window.network_model.net.sgen.loc[component_idx, 'p_mw'] = -abs(p_mw)
                
                self.parent_window.statusBar().showMessage(f"已更新光伏设备 {component_idx} 的功率设置: P={p_mw:.2f}MW")
                print(f"应用光伏设备 {component_idx} 功率设置: P={p_mw:.2f}MW")
            else:
                QMessageBox.warning(self.parent_window, "错误", f"光伏设备 {component_idx} 不存在")
                
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用光伏设置时出错: {str(e)}")
            print(f"应用光伏设置时出错: {e}")
    
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
                p_mw = self.parent_window.load_power_spinbox.value()
                q_mvar = self.parent_window.load_reactive_power_spinbox.value()
                
                self.parent_window.network_model.net.load.loc[component_idx, 'p_mw'] = p_mw
                self.parent_window.network_model.net.load.loc[component_idx, 'q_mvar'] = q_mvar
                
                self.parent_window.statusBar().showMessage(f"已更新负载设备 {component_idx} 的功率设置: P={p_mw:.2f}MW, Q={q_mvar:.2f}MVar")
                print(f"应用负载设备 {component_idx} 功率设置: P={p_mw:.2f}MW, Q={q_mvar:.2f}MVar")
            else:
                QMessageBox.warning(self.parent_window, "错误", f"负载设备 {component_idx} 不存在")
                
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用负载设置时出错: {str(e)}")
            print(f"应用负载设置时出错: {e}")
    
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
                p_mw = self.parent_window.storage_power_spinbox.value()
                
                self.parent_window.network_model.net.storage.loc[component_idx, 'p_mw'] = p_mw
                
                power_status = "放电" if p_mw > 0 else "充电" if p_mw < 0 else "待机"
                self.parent_window.statusBar().showMessage(f"已更新储能设备 {component_idx} 的功率设置: P={p_mw:.2f}MW ({power_status})")
                print(f"应用储能设备 {component_idx} 功率设置: P={p_mw:.2f}MW ({power_status})")
            else:
                QMessageBox.warning(self.parent_window, "错误", f"储能设备 {component_idx} 不存在")
                
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用储能设置时出错: {str(e)}")
            print(f"应用储能设置时出错: {e}")
    
    def remove_all_device_tabs(self):
        """移除所有设备相关的选项卡"""
        # 这个方法用于清理设备选项卡，在设备切换时调用
        pass
    
    def enable_device_data_generation(self, component_type, component_idx):
        """启用指定设备的数据生成"""
        device_key = f"{component_type}_{component_idx}"
        if device_key not in self.parent_window.generated_devices:
            self.parent_window.generated_devices.add(device_key)
            
            # 启动对应的数据生成器
            if component_type in ['load', 'sgen']:
                self.data_generator_manager.start_generation(component_type)
            
            device_type_name = {
                'load': '负载',
                'sgen': '光伏', 
                'storage': '储能'
            }.get(component_type, component_type)
            
            self.parent_window.statusBar().showMessage(f"已启用{device_type_name}设备 {component_idx} 的数据生成")
            print(f"启用设备 {device_key} 的数据生成")
    
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