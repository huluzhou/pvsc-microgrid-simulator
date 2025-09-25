"""数据生成器控制模块
提供设备数据生成的UI控制和管理功能
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel,
    QCheckBox, QDoubleSpinBox, QSlider, QPushButton,
    QMessageBox, QComboBox
)
from PySide6.QtCore import Qt
from pandas.core.frame import com
from .data_generators import DataGeneratorManager


class DataControlManager:
    """数据生成器控制管理类"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.data_generator_manager = DataGeneratorManager()
        
        # 连接储能功率变化信号
        if hasattr(parent_window, 'storage_power_changed'):
            parent_window.storage_power_changed.connect(self.on_storage_power_updated)
        
        
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
                
    def update_sgen_device_info(self, component_type, component_idx):
        """更新光伏设备信息"""
        if hasattr(self.parent_window, 'sgen_current_device_label') and hasattr(self.parent_window, 'sgen_enable_generation_checkbox'):
            if component_type and component_idx is not None:
                device_name = f"光伏_{component_idx}"
                self.parent_window.sgen_current_device_label.setText(f"当前设备: {device_name}")
                
                # 检查当前设备是否启用了数据生成
                is_enabled = self.is_device_generation_enabled(component_type, component_idx)
                self.parent_window.sgen_enable_generation_checkbox.setChecked(is_enabled)
                self.parent_window.sgen_enable_generation_checkbox.setEnabled(True)
                
                # 更新有功功率显示
                self.update_sgen_active_power(component_idx)
            else:
                self.parent_window.sgen_current_device_label.setText("未选择光伏设备")
                self.parent_window.sgen_enable_generation_checkbox.setChecked(False)
                self.parent_window.sgen_enable_generation_checkbox.setEnabled(False)
                
    def update_load_device_info(self, component_type, component_idx):
        """更新负载设备信息"""
        if hasattr(self.parent_window, 'load_current_device_label') and hasattr(self.parent_window, 'load_enable_generation_checkbox'):
            if component_type and component_idx is not None:
                device_name = f"负载_{component_idx}"
                self.parent_window.load_current_device_label.setText(f"当前设备: {device_name}")
                
                # 检查当前设备是否启用了数据生成
                is_enabled = self.is_device_generation_enabled(component_type, component_idx)
                self.parent_window.load_enable_generation_checkbox.setChecked(is_enabled)
                self.parent_window.load_enable_generation_checkbox.setEnabled(True)
            else:
                self.parent_window.load_current_device_label.setText("未选择负载设备")
                self.parent_window.load_enable_generation_checkbox.setChecked(False)
                self.parent_window.load_enable_generation_checkbox.setEnabled(False)
                
    def update_storage_device_info(self, component_type, component_idx):
        """更新储能设备信息"""
        if hasattr(self.parent_window, 'storage_current_device_label'):
            if component_type and component_idx is not None:
                device_name = f"储能_{component_idx}"
                self.parent_window.storage_current_device_label.setText(f"当前设备: {device_name}")
                
                # 检查当前设备是否启用了数据生成
                self.is_device_generation_enabled(component_type, component_idx)
            else:
                self.parent_window.storage_current_device_label.setText("未选择储能设备")
                
    def update_charger_device_info(self, component_type, component_idx):
        """更新充电桩设备信息"""
        if hasattr(self.parent_window, 'charger_current_device_label'):
            if component_type and component_idx is not None:
                device_name = f"充电桩_{component_idx}"
                self.parent_window.charger_current_device_label.setText(f"当前设备: {device_name}")
            else:
                self.parent_window.charger_current_device_label.setText("未选择充电桩设备")
                
    def is_device_generation_enabled(self, component_type, component_idx):
        """检查指定设备是否启用了数据生成"""
        device_key = f"{component_type}_{component_idx}"
        return device_key in self.parent_window.generated_devices
    
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
        # 光伏主要结果展示
        sgen_result_group = QGroupBox("光伏发电主要结果")
        sgen_result_layout = QFormLayout(sgen_result_group)
        
        # 有功功率显示
        self.parent_window.sgen_active_power_label = QLabel("-- MW")
        self.parent_window.sgen_active_power_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        sgen_result_layout.addRow("有功功率:", self.parent_window.sgen_active_power_label)
        
        # 添加到主布局
        layout.addWidget(sgen_result_group)

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
        self.parent_window.sgen_power_slider.setRange(0, 100)  # 0-1MW
        self.parent_window.sgen_power_slider.setValue(50)
        self.parent_window.sgen_power_slider.setMinimumWidth(100)
        self.parent_window.sgen_power_slider.valueChanged.connect(self.on_sgen_power_changed)
        
        self.parent_window.sgen_power_spinbox = QDoubleSpinBox()
        self.parent_window.sgen_power_spinbox.setRange(0.0, 1.0)
        self.parent_window.sgen_power_spinbox.setValue(0.5)
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
        
        # 负载主要结果展示
        load_result_group = QGroupBox("负载用电主要结果")
        load_result_layout = QFormLayout(load_result_group)
        
        # 有功功率显示
        self.parent_window.load_active_power_label = QLabel("-- MW")
        self.parent_window.load_active_power_label.setStyleSheet("font-weight: bold; color: #F44336;")
        load_result_layout.addRow("有功功率:", self.parent_window.load_active_power_label)
        
        # 添加到主布局
        layout.addWidget(load_result_group)
        
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
        self.parent_window.load_power_slider.setRange(0, 100)  # 0-10MW
        self.parent_window.load_power_slider.setValue(50)
        self.parent_window.load_power_slider.setMinimumWidth(100)
        self.parent_window.load_power_slider.valueChanged.connect(self.on_load_power_changed)
        
        self.parent_window.load_power_spinbox = QDoubleSpinBox()
        self.parent_window.load_power_spinbox.setRange(0.0, 2.0)
        self.parent_window.load_power_spinbox.setValue(1.0)
        self.parent_window.load_power_spinbox.setSuffix(" MW")
        self.parent_window.load_power_spinbox.valueChanged.connect(self.on_load_power_spinbox_changed)
        
        load_power_layout = QHBoxLayout()
        load_power_layout.addWidget(self.parent_window.load_power_slider)
        load_power_layout.addWidget(self.parent_window.load_power_spinbox)
        load_manual_layout.addRow("有功功率:", load_power_layout)
        
        # 负载无功功率控制
        self.parent_window.load_reactive_power_slider = QSlider(Qt.Horizontal)
        self.parent_window.load_reactive_power_slider.setRange(0, 100.0)  # 0-50MVar
        self.parent_window.load_reactive_power_slider.setValue(0)
        self.parent_window.load_reactive_power_slider.setMinimumWidth(100)
        self.parent_window.load_reactive_power_slider.valueChanged.connect(self.on_load_reactive_power_changed)
        
        self.parent_window.load_reactive_power_spinbox = QDoubleSpinBox()
        self.parent_window.load_reactive_power_spinbox.setRange(0.0, 2.0)
        self.parent_window.load_reactive_power_spinbox.setValue(0)
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
        
        # 储能主要结果展示
        storage_result_group = QGroupBox("储能主要结果")
        storage_result_layout = QFormLayout(storage_result_group)
        
        # 有功功率显示
        self.parent_window.storage_active_power_label = QLabel("-- MW")
        self.parent_window.storage_active_power_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        storage_result_layout.addRow("有功功率:", self.parent_window.storage_active_power_label)
        
        # 储能荷电状态显示
        self.parent_window.storage_soc_label = QLabel("-- %")
        self.parent_window.storage_soc_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        storage_result_layout.addRow("荷电状态:", self.parent_window.storage_soc_label)
        
        # 添加到主布局
        layout.addWidget(storage_result_group)
        
        # 储能手动控制
        storage_manual_group = QGroupBox("储能功率控制")
        storage_manual_layout = QVBoxLayout(storage_manual_group)
        
        # 控制模式切换（手动控制/远程控制）
        control_mode_layout = QHBoxLayout()
        control_mode_label = QLabel("控制模式：")
        
        # 使用复选框代替单选按钮，选中表示启用远程控制
        self.parent_window.storage_enable_remote = QCheckBox("启用远程控制")
        self.parent_window.storage_enable_remote.setChecked(True)  # 默认启用远程控制
        self.parent_window.storage_enable_remote.stateChanged.connect(self.on_storage_control_mode_changed)
        
        control_mode_layout.addWidget(control_mode_label)
        control_mode_layout.addWidget(self.parent_window.storage_enable_remote)
        control_mode_layout.addStretch()
        storage_manual_layout.addLayout(control_mode_layout)
        
        # 手动控制面板
        self.parent_window.storage_manual_panel = QWidget()
        storage_manual_panel_layout = QFormLayout(self.parent_window.storage_manual_panel)

        # 有功功率控制（正值为放电，负值为充电）
        self.parent_window.storage_power_slider = QSlider(Qt.Horizontal)
        self.parent_window.storage_power_slider.setRange(-100, 100)  # 滑块范围：-100.0到100.0MW（乘以10）
        self.parent_window.storage_power_slider.setValue(0)
        self.parent_window.storage_power_slider.setMinimumWidth(100)
        self.parent_window.storage_power_slider.valueChanged.connect(self.on_storage_power_changed)
        
        self.parent_window.storage_power_spinbox = QDoubleSpinBox()
        self.parent_window.storage_power_spinbox.setRange(-1.0, 1.0)
        self.parent_window.storage_power_spinbox.setValue(0.0)
        self.parent_window.storage_power_spinbox.setSuffix(" MW")
        self.parent_window.storage_power_spinbox.valueChanged.connect(self.on_storage_power_spinbox_changed)
        
        storage_power_layout = QHBoxLayout()
        storage_power_layout.addWidget(self.parent_window.storage_power_slider)
        storage_power_layout.addWidget(self.parent_window.storage_power_spinbox)
        storage_manual_panel_layout.addRow("功率控制:", storage_power_layout)
        
        # 功率说明标签
        power_info_label = QLabel("提示：正值表示充电（从电网取电），负值表示放电（向电网供电）")
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

    def create_charger_data_generation_tab(self):
        """创建充电桩设备专用的数据生成控制选项卡"""
        layout = QVBoxLayout(self.parent_window.charger_data_tab)
        
        # 当前选择设备信息
        current_device_group = QGroupBox("当前选择充电桩设备")
        current_device_layout = QVBoxLayout(current_device_group)
        
        self.parent_window.charger_current_device_label = QLabel("未选择充电桩设备")
        self.parent_window.charger_current_device_label.setStyleSheet("font-weight: bold; color: #9C27B0;")
        current_device_layout.addWidget(self.parent_window.charger_current_device_label)
        
        layout.addWidget(current_device_group)
        
        # 充电桩主要结果展示
        charger_result_group = QGroupBox("充电桩用电主要结果")
        charger_result_layout = QFormLayout(charger_result_group)
        
        # 有功功率显示
        self.parent_window.charger_active_power_label = QLabel("-- kW")
        self.parent_window.charger_active_power_label.setStyleSheet("font-weight: bold; color: #9C27B0;")
        charger_result_layout.addRow("有功功率:", self.parent_window.charger_active_power_label)
        
        # 添加到主布局
        layout.addWidget(charger_result_group)
        
        # 充电桩需求功率手动控制
        charger_manual_group = QGroupBox("充电桩需求功率控制")
        charger_manual_layout = QVBoxLayout(charger_manual_group)
        
        # 手动控制面板
        self.parent_window.charger_manual_panel = QWidget()
        charger_manual_panel_layout = QFormLayout(self.parent_window.charger_manual_panel)
        
        # 需求功率控制 - 创建时不设置固定范围，后续由update_charger_manual_controls_from_device动态设置
        self.parent_window.charger_required_power_slider = QSlider(Qt.Horizontal)
        self.parent_window.charger_required_power_slider.setRange(0, 100)  # 临时默认范围，后续会更新
        self.parent_window.charger_required_power_slider.setValue(0)
        self.parent_window.charger_required_power_slider.setMinimumWidth(100)
        self.parent_window.charger_required_power_slider.valueChanged.connect(self.on_charger_required_power_changed)
        
        self.parent_window.charger_required_power_spinbox = QDoubleSpinBox()
        self.parent_window.charger_required_power_spinbox.setRange(0.0, 100.0)  # 临时默认范围，后续会更新
        self.parent_window.charger_required_power_spinbox.setValue(0.0)
        self.parent_window.charger_required_power_spinbox.setMinimumWidth(100)
        self.parent_window.charger_required_power_spinbox.setSuffix(" kW")
        self.parent_window.charger_required_power_spinbox.valueChanged.connect(self.on_charger_required_power_spinbox_changed)
        
        charger_required_power_layout = QHBoxLayout()
        charger_required_power_layout.addWidget(self.parent_window.charger_required_power_slider)
        charger_required_power_layout.addWidget(self.parent_window.charger_required_power_spinbox)
        charger_manual_panel_layout.addRow("需求功率:", charger_required_power_layout)
        
        # 功率限制显示 - 只读标签
        self.parent_window.charger_power_limit_label = QLabel()
        self.parent_window.charger_power_limit_label.setStyleSheet("background-color: #f0f0f0; color: #333;")
        self.parent_window.charger_power_limit_label.setText("100.0 kW")  # 初始默认值
        charger_manual_panel_layout.addRow("功率限制:", self.parent_window.charger_power_limit_label)
        
        # 应用按钮
        charger_apply_button = QPushButton("应用充电桩设置")
        charger_apply_button.clicked.connect(self.apply_charger_settings)
        charger_manual_panel_layout.addRow("", charger_apply_button)
        
        self.parent_window.charger_manual_panel.setVisible(True)  # 默认显示手动控制面板
        charger_manual_layout.addWidget(self.parent_window.charger_manual_panel)
        layout.addWidget(charger_manual_group)
        
        layout.addStretch()
        
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
            'storage': self.update_storage_manual_controls_from_device,
            'charger': self.update_charger_manual_controls_from_device,  # 新增充电桩更新方法
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
    
    # 参数变化回调方法
    def on_variation_changed(self, value):
        """变化幅度改变时的回调"""
        self.data_generator_manager.set_variation('load', value)
        self.data_generator_manager.set_variation('sgen', value)
    
    def on_interval_changed(self, value):
        """生成间隔改变时的回调"""
        self.data_generator_manager.set_interval('load', value)
        self.data_generator_manager.set_interval('sgen', value)

    def update_sgen_active_power(self, component_idx):
        """更新光伏设备的有功功率显示"""
        if hasattr(self.parent_window, "sgen_active_power_label") and hasattr(
            self.parent_window, "network_model"
        ):
            net = self.parent_window.network_model.net
            if hasattr(net, "res_sgen") and component_idx in net.res_sgen.index:
                active_power = net.res_sgen.loc[component_idx, "p_mw"]
                self.parent_window.sgen_active_power_label.setText(
                    f"{active_power:.4f} MW"
                )
            else:
                self.parent_window.sgen_active_power_label.setText("未计算")

    def update_storage_active_power(self, component_idx):
        """更新储能设备的有功功率显示"""
        if hasattr(self.parent_window, "storage_active_power_label") and hasattr(
            self.parent_window, "network_model"
        ):
            net = self.parent_window.network_model.net
            if hasattr(net, "res_storage") and component_idx in net.res_storage.index:
                active_power = net.res_storage.loc[component_idx, "p_mw"]
                self.parent_window.storage_active_power_label.setText(
                    f"{active_power:.4f} MW"
                )
            else:
                self.parent_window.storage_active_power_label.setText("未计算")
    
    def update_load_active_power(self, component_idx):
        """更新负载设备的有功功率显示"""
        if hasattr(self.parent_window, "load_active_power_label") and hasattr(
            self.parent_window, "network_model"
        ):
            net = self.parent_window.network_model.net
            # 检查component_idx是否为None
            if component_idx is None:
                self.parent_window.load_active_power_label.setText("未计算")
                return
            
            if hasattr(net, "res_load") and component_idx in net.res_load.index:
                active_power = net.res_load.loc[component_idx, "p_mw"]
                self.parent_window.load_active_power_label.setText(
                    f"{active_power:.4f} MW"
                )
            else:
                self.parent_window.load_active_power_label.setText("未计算")
    
    def update_charger_active_power(self, component_idx):
        """更新充电桩设备的有功功率显示"""
        if hasattr(self.parent_window, "charger_active_power_label") and hasattr(
            self.parent_window, "network_model"
        ):
            net = self.parent_window.network_model.net
            # 检查component_idx是否为None
            if component_idx is None:
                self.parent_window.charger_active_power_label.setText("未计算")
                return
            
            # 充电桩在模型中作为负载处理，索引有+1000的偏移
            if hasattr(net, "res_load") and component_idx in net.res_load.index:
                active_power = net.res_load.loc[component_idx, "p_mw"]
                # 转换为kW显示
                active_power_kw = active_power * 1000
                self.parent_window.charger_active_power_label.setText(
                    f"{active_power_kw:.1f} kW"
                )
            else:
                self.parent_window.charger_active_power_label.setText("未计算")

    def update_storage_soc(self, component_idx):
        """更新储能设备的状态量显示"""
        if hasattr(self.parent_window, "storage_soc_label"):
            try:
                # 从scene.items()中获取SOC值
                if hasattr(self.parent_window, 'canvas') and hasattr(self.parent_window.canvas, 'scene'):
                    # 查找对应索引的储能设备
                    for item in self.parent_window.canvas.scene.items():
                        if hasattr(item, 'component_type') and item.component_type == 'storage' and item.component_index == component_idx:
                            if hasattr(item, 'properties') and 'soc_percent' in item.properties:
                                soc_percent = item.properties['soc_percent']
                                self.parent_window.storage_soc_label.setText(f"{soc_percent*100:.4f}%")
                                return
                # 如果未找到，显示默认值
                self.parent_window.storage_soc_label.setText("未计算")
            except Exception as e:
                print(f"更新储能SOC失败: {str(e)}")
                self.parent_window.storage_soc_label.setText("未计算")

    def update_realtime_data(self):
        # 根据当前设备类型只调用对应的更新方法
        component_type = getattr(self.parent_window, 'current_component_type', None)
        component_idx = getattr(self.parent_window, 'current_component_idx', None)
        
        if component_type == 'sgen':
            self.update_sgen_active_power(component_idx)
        elif component_type == 'storage':
            self.update_storage_active_power(component_idx)
            self.update_storage_soc(component_idx)
        elif component_type == 'load':
            self.update_load_active_power(component_idx)
        elif component_type == 'charger':
            self.update_charger_active_power(component_idx)

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
            
            # 获取储能设备的额定功率
            from .network_items import StorageItem
            storage_item = None
            for item in self.parent_window.canvas.scene.items():
                if isinstance(item, StorageItem) and item.component_index == self.parent_window.current_component_idx:
                    storage_item = item
                    break
            
            # 获取额定功率，默认为1.0 MW
            rated_power_mw = 1.0
            if storage_item and hasattr(storage_item, 'properties') and 'sn_mva' in storage_item.properties:
                # 从properties中获取sn_mva值
                rated_power_mw = storage_item.properties['sn_mva']
            
            # 根据额定功率动态设置滑块和输入框的范围（-150%~150%额定功率，负值表示放电）
            max_power = rated_power_mw * 1.5
            min_power = -max_power
            
            # 更新滑块范围和值
            if hasattr(self.parent_window, 'storage_power_slider'):
                self.parent_window.storage_power_slider.setRange(int(min_power * 100), int(max_power * 100))  # 精确到0.01MW
                # 确保当前值不超过新范围
                safe_value = max(int(min_power * 100), min(int(max_power * 100), int(current_power * 100)))
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
            print(f"更新储能设备手动控制值时出错: {e}")
            
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

    def update_charger_manual_controls_from_device(self):
        """从当前充电桩设备更新手动控制组件的值"""
        if not hasattr(self.parent_window, 'current_component_type') or not hasattr(self.parent_window, 'current_component_idx'):
            return
            
        if not self.parent_window.network_model or not hasattr(self.parent_window.network_model, 'net'):
            return
            
        if self.parent_window.current_component_type != 'charger':
            return
            
        try:
            # 获取充电桩设备的当前需求功率值
            current_power = self.parent_window.network_model.net.load.at[self.parent_window.current_component_idx, 'p_mw']
            current_power_kw = current_power * 1000  # 转换为kW
            
            # 获取充电桩的额定功率
            from .network_items import ChargerItem
            charger_item = None
            for item in self.parent_window.canvas.scene.items():
                if isinstance(item, ChargerItem) and item.component_index == self.parent_window.current_component_idx:
                    charger_item = item
                    break
            
            # 获取额定功率，默认为100kW
            rated_power_kw = 1000.0
            if charger_item and hasattr(charger_item, 'properties') and 'sn_mva' in charger_item.properties:
                # 从properties中获取sn_mva值并转换为kW
                sn_mva = charger_item.properties['sn_mva']
                rated_power_kw = sn_mva * 1000  # 转换为kW
            
            # 动态设置滑块和输入框的范围（0~额定功率）
            if hasattr(self.parent_window, 'charger_required_power_slider'):
                self.parent_window.charger_required_power_slider.setRange(0, int(rated_power_kw))
                # 确保当前值不超过新范围
                safe_value = max(0, min(int(rated_power_kw), int(current_power_kw)))
                self.parent_window.charger_required_power_slider.setValue(safe_value)
            
            if hasattr(self.parent_window, 'charger_required_power_spinbox'):
                self.parent_window.charger_required_power_spinbox.setRange(0.0, rated_power_kw)
                # 确保当前值不超过新范围
                safe_value = max(0.0, min(rated_power_kw, current_power_kw))
                self.parent_window.charger_required_power_spinbox.setValue(safe_value)
            
            # 更新功率限制显示
            if hasattr(self.parent_window, "charger_power_limit_label"):
                self.parent_window.charger_power_limit_label.setText(
                    f"{charger_item.power_limit * 1000:.1f} kW"
                )
                
        except Exception as e:
            print(f"更新充电桩设备手动控制值时出错: {e}")
    
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
                        self.parent_window.base_reactive_power_value = abs(rated_reactive) if rated_reactive != 0 else 1.0
                    else:
                        self.parent_window.base_reactive_power_value = 0.0
                    
                    # 根据额定功率动态设置滑块和输入框范围（0-150%额定功率）
                    max_power = self.parent_window.base_power_value * 1.5
                    max_reactive = self.parent_window.base_reactive_power_value * 1.5
                    
                    # 更新专用负载控制组件
                    if hasattr(self.parent_window, 'load_power_slider'):
                        self.parent_window.load_power_slider.setRange(0, int(max_power * 100))  # 精确到0.01MW
                        self.parent_window.load_power_slider.setValue(int(p_mw * 100))
                    
                    if hasattr(self.parent_window, 'load_power_spinbox'):
                        self.parent_window.load_power_spinbox.setRange(0.0, max_power)
                        self.parent_window.load_power_spinbox.setValue(p_mw)
                    
                    if hasattr(self.parent_window, 'load_reactive_power_slider'):
                        self.parent_window.load_reactive_power_slider.setRange(0, int(max_reactive * 100))
                        self.parent_window.load_reactive_power_slider.setValue(int(q_mvar * 100))
                    
                    if hasattr(self.parent_window, 'load_reactive_power_spinbox'):
                        self.parent_window.load_reactive_power_spinbox.setRange(0.0, max_reactive)
                        self.parent_window.load_reactive_power_spinbox.setValue(q_mvar)
                        
            elif component_type == 'sgen':
                if component_idx < len(self.parent_window.network_model.net.sgen):
                    p_mw = abs(self.parent_window.network_model.net.sgen.loc[component_idx, 'p_mw'])
                    
                    # 获取额定功率，如果不存在则使用默认值1.0
                    if 'p_mw_rated' in self.parent_window.network_model.net.sgen.columns:
                        rated_power = self.parent_window.network_model.net.sgen.loc[component_idx, 'p_mw_rated']
                        self.parent_window.base_power_value = abs(rated_power) if rated_power != 0 else 1.0
                    else:
                        self.parent_window.base_power_value = 1.0
                    
                    # 根据额定功率动态设置滑块和输入框范围（0-150%额定功率）
                    max_power = self.parent_window.base_power_value * 1.5
                    
                    # 更新专用光伏控制组件
                    if hasattr(self.parent_window, 'sgen_power_slider'):
                        self.parent_window.sgen_power_slider.setRange(0, int(max_power * 100))  # 精确到0.01MW
                        self.parent_window.sgen_power_slider.setValue(int(p_mw * 100))
                    
                    if hasattr(self.parent_window, 'sgen_power_spinbox'):
                        self.parent_window.sgen_power_spinbox.setRange(0.0, max_power)
                        self.parent_window.sgen_power_spinbox.setValue(p_mw)
                        
        except Exception as e:
            print(f"更新手动控制值时出错: {e}")
    
    # 滑块和输入框变化回调方法
    def on_manual_power_changed(self, value):
        """手动功率滑块改变时的回调"""
        # 将滑块值（百分比）转换为实际功率值
        if hasattr(self.parent_window, 'power_spinbox') and hasattr(self.parent_window, 'base_power_value'):
            # 使用基准功率值计算实际功率（精确到0.01MW）
            new_power = self.parent_window.base_power_value * (value / 100.0)
            # 暂时断开信号连接，避免循环调用
            self.parent_window.power_spinbox.blockSignals(True)
            self.parent_window.power_spinbox.setValue(new_power)
            self.parent_window.power_spinbox.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()

    
    def on_manual_reactive_power_changed(self, value):
        """手动无功功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'reactive_power_spinbox') and hasattr(self.parent_window, 'base_reactive_power_value'):
            # 使用基准无功功率值计算实际功率（精确到0.01MVar）
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
            
            # 获取当前滑块范围（动态范围）
            max_slider = self.parent_window.reactive_power_slider.maximum()
            min_slider = self.parent_window.reactive_power_slider.minimum()
            percentage = max(min_slider, min(max_slider, percentage))
            
            self.parent_window.reactive_power_slider.blockSignals(True)
            self.parent_window.reactive_power_slider.setValue(percentage)
            self.parent_window.reactive_power_slider.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_sgen_power_changed(self, value):
        """光伏功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'sgen_power_spinbox'):
            # 滑块值直接对应功率值（精确到0.01MW）
            power_value = value / 100.0
            self.parent_window.sgen_power_spinbox.blockSignals(True)
            self.parent_window.sgen_power_spinbox.setValue(power_value)
            self.parent_window.sgen_power_spinbox.blockSignals(False)

    def on_sgen_power_spinbox_changed(self, value):
        """光伏功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'sgen_power_slider'):
            # 功率值转换为滑块值（精确到0.01MW）
            slider_value = int(value * 100)
            max_slider = int(self.parent_window.sgen_power_spinbox.maximum() * 100)
            slider_value = max(0, min(max_slider, slider_value))
            self.parent_window.sgen_power_slider.blockSignals(True)
            self.parent_window.sgen_power_slider.setValue(slider_value)
            self.parent_window.sgen_power_slider.blockSignals(False)
    
    def on_load_power_changed(self, value):
        """负载功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'load_power_spinbox'):
            # 滑块值直接对应功率值（精确到0.01MW）
            power_value = value / 100.0
            self.parent_window.load_power_spinbox.blockSignals(True)
            self.parent_window.load_power_spinbox.setValue(power_value)
            self.parent_window.load_power_spinbox.blockSignals(False)
    
    def on_load_power_spinbox_changed(self, value):
        """负载功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'load_power_slider'):
            # 功率值转换为滑块值（精确到0.01MW）
            slider_value = int(value * 100)
            
            # 获取当前滑块范围
            max_slider = self.parent_window.load_power_slider.maximum()
            slider_value = max(0, min(max_slider, slider_value))
            
            self.parent_window.load_power_slider.blockSignals(True)
            self.parent_window.load_power_slider.setValue(slider_value)
            self.parent_window.load_power_slider.blockSignals(False)
    
    def on_load_reactive_power_changed(self, value):
        """负载无功功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'load_reactive_power_spinbox'):
            # 滑块值直接对应无功功率值（精确到0.01MVar）
            power_value = value / 100.0
            self.parent_window.load_reactive_power_spinbox.blockSignals(True)
            self.parent_window.load_reactive_power_spinbox.setValue(power_value)
            self.parent_window.load_reactive_power_spinbox.blockSignals(False)
    
    def on_load_reactive_power_spinbox_changed(self, value):
        """负载无功功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'load_reactive_power_slider'):
            # 无功功率值转换为滑块值（精确到0.01MVar）
            slider_value = int(value * 100)
            
            # 获取当前滑块范围
            max_slider = self.parent_window.load_reactive_power_slider.maximum()
            slider_value = max(0, min(max_slider, slider_value))
            
            self.parent_window.load_reactive_power_slider.blockSignals(True)
            self.parent_window.load_reactive_power_slider.setValue(slider_value)
            self.parent_window.load_reactive_power_slider.blockSignals(False)
    
    def on_storage_power_changed(self, value):
        """储能功率滑块改变时的回调"""
        if hasattr(self.parent_window, 'storage_power_spinbox'):
            # 滑块值直接对应功率值（精确到0.01MW）
            power_value = value / 100.0
            self.parent_window.storage_power_spinbox.blockSignals(True)
            self.parent_window.storage_power_spinbox.setValue(power_value)
            self.parent_window.storage_power_spinbox.blockSignals(False)

    def on_storage_power_spinbox_changed(self, value):
        """储能功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'storage_power_slider'):
            # 功率值转换为滑块值（精确到0.01MW）
            slider_value = int(value * 100)
            
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
            # 滑块值直接对应功率值（精确到1kW）
            power_value = float(value)
            self.parent_window.charger_required_power_spinbox.blockSignals(True)
            self.parent_window.charger_required_power_spinbox.setValue(power_value)
            self.parent_window.charger_required_power_spinbox.blockSignals(False)

    def on_charger_required_power_spinbox_changed(self, value):
        """充电桩需求功率输入框改变时的回调"""
        if hasattr(self.parent_window, 'charger_required_power_slider'):
            # 功率值转换为滑块值（精确到1kW）
            slider_value = int(value)
            # 使用滑块的当前范围限制值
            min_slider = self.parent_window.charger_required_power_slider.minimum()
            max_slider = self.parent_window.charger_required_power_slider.maximum()
            slider_value = max(min_slider, min(max_slider, slider_value))
            
            self.parent_window.charger_required_power_slider.blockSignals(True)
            self.parent_window.charger_required_power_slider.setValue(slider_value)
            self.parent_window.charger_required_power_slider.blockSignals(False)
    
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
                self.parent_window.network_model.net.load.loc[component_idx, 'p_mw'] = final_power_mw
                
                self.parent_window.statusBar().showMessage(f"已更新充电桩设备 {component_idx} 的功率设置: {final_power_kw:.1f}kW (需求功率: {demand_power_kw:.1f}kW, 功率限制: {power_limit_kw:.1f}kW)")
                print(f"应用充电桩设备 {component_idx} 功率设置: {final_power_kw:.1f}kW (max({demand_power_kw:.1f}kW, {power_limit_kw:.1f}kW))")

            else:
                QMessageBox.warning(self.parent_window, "错误", f"充电桩设备 {component_idx} 不存在")
                
        except Exception as e:
            QMessageBox.critical(self.parent_window, "错误", f"应用充电桩设置时出错: {str(e)}")
            print(f"应用充电桩设置时出错: {e}")
    
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
