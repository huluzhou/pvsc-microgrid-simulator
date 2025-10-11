from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QGroupBox,
    QScrollArea, QFrame, QFormLayout, QApplication,
    QPushButton, QHBoxLayout, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette


class PropertiesPanel(QWidget):
    """组件属性面板"""
    
    # 信号：属性值改变时发出
    property_changed = Signal(str, str, object)  # component_type, property_name, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item = None
        self.property_widgets = {}
        self.init_ui()
        
        # 初始化主题
        
        # 移除 standard_types，直接通过标准类型创建 pandapower 组件
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 设置最小宽度，确保属性面板有足够的显示空间
        self.setMinimumWidth(350)
        
        # 标题
        title_label = QLabel("组件属性")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 属性容器
        self.properties_widget = QWidget()
        self.properties_layout = QVBoxLayout(self.properties_widget)
        self.properties_layout.setContentsMargins(5, 5, 5, 5)
        
        scroll_area.setWidget(self.properties_widget)
        layout.addWidget(scroll_area)
        
        # 默认显示提示
        self.show_no_selection()
        
    def show_no_selection(self):
        """显示未选中组件的提示"""
        self.clear_properties()
        
        self.no_selection_label = QLabel("请选择一个组件以查看其属性")
        self.no_selection_label.setAlignment(Qt.AlignCenter)
        self.no_selection_label.setObjectName("noSelectionLabel")
        self.update_no_selection_style()
        self.properties_layout.addWidget(self.no_selection_label)
        
    def clear_properties(self):
        """清空属性显示"""
        # 清除所有子控件
        while self.properties_layout.count():
            child = self.properties_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.property_widgets.clear()
        
    def update_properties(self, item):
        """更新属性显示"""
        self.current_item = item
        self.clear_properties()
        
        if not item or not hasattr(item, 'properties'):
            self.show_no_selection()
            return
            
        # 初始化custom_fields字典，如果不存在的话
        if 'custom_fields' not in self.current_item.properties:
            self.current_item.properties['custom_fields'] = {}
            
        # 组件信息组
        info_group = QGroupBox("组件信息")
        info_layout = QFormLayout(info_group)
        
        # 组件类型（只读）
        type_label = QLabel(item.component_type.title())
        type_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        info_layout.addRow("类型:", type_label)
        
        # 组件名称
        name_edit = QLineEdit(getattr(item, 'component_name', ''))
        name_edit.textChanged.connect(lambda text: self.on_property_changed('name', text))
        info_layout.addRow("名称:", name_edit)
        self.property_widgets['name'] = name_edit
        
        self.properties_layout.addWidget(info_group)
        
        # 属性组
        props_group = QGroupBox("参数")
        props_layout = QFormLayout(props_group)
        
        # 根据组件类型显示相应的属性
        properties = self.get_component_properties(item.component_type)
        
        for prop_name, prop_info in properties.items():
            # 对于线路组件，根据use_standard_type控制显示
            if item.component_type == 'line':
                use_standard = item.properties.get('use_standard_type', True)
                
                # 通用参数始终显示
                if prop_name in ['length_km', 'use_standard_type']:
                    pass  # 显示
                # 自定义参数：仅在不使用标准类型时显示
                elif prop_name in ['r_ohm_per_km', 'x_ohm_per_km', 'c_nf_per_km', 'r0_ohm_per_km', 'x0_ohm_per_km', 'c0_nf_per_km', 'max_i_ka']:
                    if use_standard:
                        continue  # 跳过
            
            # 对于变压器组件，根据use_standard_type控制显示
            elif item.component_type == 'transformer':
                use_standard = item.properties.get('use_standard_type', True)
                
                # 通用参数始终显示
                if prop_name == 'use_standard_type':
                    pass  # 显示
                # 标准类型参数：仅在使用标准类型时显示
                elif prop_name == 'std_type':
                    if not use_standard:
                        continue  # 跳过
                # 自定义类型参数：仅在不使用标准类型时显示
                elif prop_name in ['sn_mva', 'vn_hv_kv', 'vn_lv_kv', 'vkr_percent', 'vk_percent', 'pfe_kw', 'i0_percent', 'vector_group']:
                    if use_standard:
                        continue  # 跳过
                # 零序参数：始终显示
                elif prop_name in ['vk0_percent', 'vkr0_percent', 'mag0_percent', 'mag0_rx', 'si0_hv_partial']:
                    pass  # 显示
            
            # 对于光伏组件，根据use_power_factor控制显示
            elif item.component_type == 'static_generator':
                use_power_factor = item.properties.get('use_power_factor', False)
                
                # 通用参数始终显示
                if prop_name in ['use_power_factor', 'scaling', 'in_service']:
                    pass  # 显示
                # 直接功率模式参数：仅在不使用功率因数模式时显示
                elif prop_name in ['p_mw']:
                    if use_power_factor:
                        continue  # 跳过
                # 功率因数模式参数：仅在使用功率因数模式时显示
                elif prop_name in ['cos_phi', 'mode']:
                    if not use_power_factor:
                        continue  # 跳过
            
            # 对于负载组件，根据use_power_factor控制显示
            elif item.component_type == 'load':
                use_power_factor = item.properties.get('use_power_factor', False)
                
                # 通用参数始终显示
                if prop_name in ['use_power_factor', 'const_z_percent', 'const_i_percent', 'scaling', 'in_service']:
                    pass  # 显示
                # 直接功率模式参数：仅在不使用功率因数模式时显示
                elif prop_name in ['p_mw']:
                    if use_power_factor:
                        continue  # 跳过
                # 功率因数模式参数：仅在使用功率因数模式时显示
                elif prop_name in ['cos_phi', 'mode']:
                    if not use_power_factor:
                        continue  # 跳过
            
            # 对于充电桩组件，根据use_power_factor控制显示
            elif item.component_type == 'charger':
                use_power_factor = item.properties.get('use_power_factor', False)
                
                # 通用参数始终显示
                if prop_name in ['use_power_factor', 'in_service']:
                    pass  # 显示
                # 直接功率模式参数：仅在不使用功率因数模式时显示
                elif prop_name in ['p_mw']:
                    if use_power_factor:
                        continue  # 跳过
                # 功率因数模式参数：仅在使用功率因数模式时显示
                elif prop_name in ['cos_phi', 'mode']:
                    if not use_power_factor:
                        continue  # 跳过
            
            # 对于所有组件，动态获取连接的bus信息
            if prop_name == 'bus':
                # 获取连接的bus名称
                connected_bus = self.get_connected_bus_name(item)
                current_value = connected_bus if connected_bus else ''
            else:
                current_value = item.properties.get(prop_name, prop_info.get('default', ''))
            widget = self.create_property_widget(prop_name, prop_info, current_value)
            
            if widget:
                props_layout.addRow(f"{prop_info.get('label', prop_name)}:", widget)
                self.property_widgets[prop_name] = widget
        
        self.properties_layout.addWidget(props_group)
        
        # 标准类型选择已集成到参数区域内，不再需要独立的选择器
        
        # 配置控件模块
        self.add_configuration_module()

        # 添加弹性空间
        self.properties_layout.addStretch()
        
    def get_connected_bus_name(self, item):
        """获取组件连接的bus索引"""
        try:
            # 检查item是否有连接的组件
            if hasattr(item, 'current_connections') and item.current_connections:
                # 查找连接的bus组件
                for connected_item in item.current_connections:
                    if hasattr(connected_item, 'component_type') and connected_item.component_type == 'bus':
                        # 返回母线的索引而不是名称
                        if hasattr(connected_item, 'component_index'):
                            return str(connected_item.component_index)
                        else:
                            return connected_item.properties.get('index', 'Unknown')
            return ''
        except Exception as e:
            print(f"获取连接bus索引时出错: {e}")
            return ''
                    
    def create_property_widget(self, prop_name, prop_info, current_value):
        """创建属性编辑控件"""
        prop_type = prop_info.get('type', 'str')
        
        if prop_type == 'float':
            widget = QDoubleSpinBox()
            widget.setRange(prop_info.get('min', -999999.0), prop_info.get('max', 999999.0))
            widget.setDecimals(prop_info.get('decimals', 3))
            widget.setValue(float(current_value) if current_value else 0.0)
            widget.valueChanged.connect(lambda value: self.on_property_changed(prop_name, value))
            return widget
            
        elif prop_type == 'int':
            widget = QSpinBox()
            widget.setRange(prop_info.get('min', -999999), prop_info.get('max', 999999))
            widget.setValue(int(current_value) if current_value else 0)
            widget.valueChanged.connect(lambda value: self.on_property_changed(prop_name, value))
            return widget
            
        elif prop_type == 'bool':
            widget = QCheckBox()
            widget.setChecked(bool(current_value))
            widget.toggled.connect(lambda checked: self.on_property_changed(prop_name, checked))
            return widget
            
        elif prop_type == 'choice':
            widget = QComboBox()
            choices = prop_info.get('choices', [])
            choice_map = {}  # 用于存储显示文本到实际值的映射
            
            for choice in choices:
                if isinstance(choice, tuple) and len(choice) == 2:
                    # 元组形式: (实际值, 显示文本)
                    value, display_text = choice
                    widget.addItem(display_text)
                    choice_map[display_text] = value
                else:
                    # 字符串形式: 直接使用
                    widget.addItem(str(choice))
                    choice_map[str(choice)] = choice
            
            # 设置当前值
            for display_text, value in choice_map.items():
                if value == current_value:
                    widget.setCurrentText(display_text)
                    break
            
            # 连接信号，传递实际值而不是显示文本
            widget.currentTextChanged.connect(
                lambda text: self.on_property_changed(prop_name, choice_map.get(text, text))
            )
            return widget
            
        elif prop_type == 'readonly':
            widget = QLineEdit()
            widget.setText(str(current_value) if current_value else '')
            widget.setReadOnly(True)
            widget.setStyleSheet("QLineEdit { background-color: #f0f0f0; color: #333333; }")
            return widget
            
        else:  # 默认为字符串
            widget = QLineEdit()
            widget.setText(str(current_value) if current_value else '')
            widget.textChanged.connect(lambda text: self.on_property_changed(prop_name, text))
            return widget
            
    def on_property_changed(self, prop_name, new_value):
        """属性值改变事件"""
        if self.current_item and hasattr(self.current_item, 'properties'):
            # IP和端口唯一性验证
            if prop_name in ['ip', 'port']:
                # 获取新的IP和端口组合
                new_ip = new_value if prop_name == 'ip' else self.current_item.properties.get('ip', '')
                new_port = new_value if prop_name == 'port' else self.current_item.properties.get('port', '')
                
                # 检查IP和端口是否有效
                if new_ip and new_port:
                    # 获取画布实例以检查冲突
                    canvas = None
                    main_window = self.parent()
                    while main_window and not hasattr(main_window, 'canvas'):
                        main_window = main_window.parent()
                    
                    if main_window and hasattr(main_window, 'canvas'):
                        canvas = main_window.canvas
                    
                    if canvas:
                        # 检查是否与现有组件冲突（排除当前组件）
                        for item in canvas.items():
                            if (hasattr(item, 'properties') and 
                                item != self.current_item and
                                item.properties.get('ip') == new_ip and
                                item.properties.get('port') == new_port):
                                
                                # 发现冲突，显示警告
                                from PySide6.QtWidgets import QMessageBox
                                QMessageBox.warning(
                                    self,
                                    "IP和端口冲突",
                                    f"IP地址 {new_ip} 和端口 {new_port} 的组合已被组件 {item.properties.get('name', '未知')} 使用。\n\n请使用不同的IP地址或端口。"
                                )
                                
                                # 恢复原来的值
                                old_value = self.current_item.properties.get(prop_name, '')
                                if prop_name in self.property_widgets:
                                    widget = self.property_widgets[prop_name]
                                    if hasattr(widget, 'setText'):
                                        widget.setText(str(old_value))
                                    elif hasattr(widget, 'setValue'):
                                        widget.setValue(float(old_value))
                                
                                return  # 不更新属性，直接返回
            
            # 更新组件属性
            self.current_item.properties[prop_name] = new_value
            
            # 特殊处理名称属性
            if prop_name == 'name':
                self.current_item.component_name = new_value
                if hasattr(self.current_item, 'label'):
                    self.current_item.label.setPlainText(new_value)
                
                # 对于电表、储能、充电桩、光伏组件，当name改变时同步更新sn
                if self.current_item.component_type in ['meter', 'storage', 'charger', 'static_generator']:
                    self.current_item.properties['sn'] = new_value
                    # 如果sn属性控件存在，也需要更新其显示值
                    if 'sn' in self.property_widgets:
                        self.property_widgets['sn'].setText(new_value)
            
            # 当额定功率改变时，更新相关功率限制和Modbus寄存器
            if prop_name == 'sn_mva':
                # 如果有update_power_limits方法则调用
                if hasattr(self.current_item, 'update_power_limits'):
                    self.current_item.update_power_limits()
                # 同步更新Modbus寄存器
                self._update_modbus_registers(prop_name, new_value)
            
            # 特殊处理线路和变压器的use_standard_type属性改变
            if prop_name == 'use_standard_type' and self.current_item.component_type in ['line', 'transformer']:
                # 重新刷新属性面板显示
                self.update_properties(self.current_item)
                return  # 避免重复发出信号
            
            # 特殊处理光伏的use_power_factor属性改变
            if prop_name == 'use_power_factor' and self.current_item.component_type == 'static_generator':
                # 重新刷新属性面板显示
                self.update_properties(self.current_item)
                return  # 避免重复发出信号
            
            # 特殊处理负载的use_power_factor属性改变
            if prop_name == 'use_power_factor' and self.current_item.component_type == 'load':
                # 重新刷新属性面板显示
                self.update_properties(self.current_item)
                return  # 避免重复发出信号
            
            # 特殊处理线路的use_standard_type属性改变
            if prop_name == 'use_standard_type' and self.current_item.component_type == 'line':
                # 重新刷新属性面板显示
                self.update_properties(self.current_item)
                return  # 避免重复发出信号
            
            # 特殊处理充电桩的use_power_factor属性改变
            if prop_name == 'use_power_factor' and self.current_item.component_type == 'charger':
                # 重新刷新属性面板显示
                self.update_properties(self.current_item)
                return  # 避免重复发出信号
            
            # 发出信号
            self.property_changed.emit(self.current_item.component_type, prop_name, new_value)
            
    def _update_modbus_registers(self, prop_name, new_value):
        """当属性改变时，同步更新对应设备的Modbus寄存器
        
        参数:
            prop_name: 属性名称
            new_value: 新的属性值
        """
        if not self.current_item or prop_name != 'sn_mva':
            return
            
        try:
            # 获取设备信息
            device_type = self.current_item.component_type
            device_index = self.current_item.properties.get('index', 0)
            device_name = self.current_item.properties.get('name', f'{device_type}_{device_index}')
            
            # 通过主窗口获取ModbusManager实例
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'modbus_manager'):
                main_window = main_window.parent()
                
            if not main_window or not hasattr(main_window, 'modbus_manager'):
                return
                
            modbus_manager = main_window.modbus_manager
            
            # 构建设备键
            device_key = f"{device_type}_{device_index}"
            
            # 检查设备是否正在运行Modbus服务
            if device_key not in modbus_manager.running_services:
                return
                
            # 获取设备上下文
            context = modbus_manager.modbus_contexts.get(device_key)
            if not context:
                return
                
            slave_context = context[1]  # 设备ID为1
            
            # 根据设备类型更新对应的寄存器
            if device_type == 'storage':
                # 储能设备：额定功率占用寄存器7-8
                rated_power_value = int(float(new_value) * 1000 * 10)  # 转换为0.1kW单位
                low_word = rated_power_value & 0xFFFF
                high_word = (rated_power_value >> 16) & 0xFFFF
                slave_context.setValues(4, 8, [low_word])   # 额定功率低位
                slave_context.setValues(4, 9, [high_word])  # 额定功率高位
                print(f"已更新储能设备 {device_name} 的额定功率寄存器: {new_value} MVA")
                
            elif device_type == 'charger':
                # 充电桩设备：额定功率占用寄存器4
                rated_power_value = int(float(new_value) * 1000)  # 转换为kW单位
                slave_context.setValues(4, 4, [rated_power_value])
                print(f"已更新充电桩设备 {device_name} 的额定功率寄存器: {new_value} MVA")
                
            elif device_type == 'static_generator':
                # 光伏设备：额定功率占用寄存器5000
                rated_power_value = int(float(new_value) * 1000 * 10)  # 转换为0.1kVA单位
                slave_context.setValues(4, 5000, [rated_power_value])
                print(f"已更新光伏设备 {device_name} 的额定功率寄存器: {new_value} MVA")
                
        except Exception as e:
            print(f"更新Modbus寄存器失败: {e}")
            
    def get_component_properties(self, component_type):
        """获取组件属性定义"""
        # 基于pandapower文档的属性定义
        properties = {
            'bus': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'vn_kv': {'type': 'float', 'label': '电网电压等级 (kV)', 'default': 20.0, 'min': 0.1},
                'geodata': {'type': 'readonly', 'label': '位置'}
            },
            'line': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                # 通用参数
                'length_km': {'type': 'float', 'label': '长度 (km)', 'default': 1.0, 'min': 0.001, 'max': 1000.0, 'decimals': 3},
                'use_standard_type': {'type': 'bool', 'label': '使用标准类型', 'default': True},
                
                # 标准类型参数
                'std_type': {
                    'type': 'choice', 
                    'label': '标准类型', 
                    'choices': [
                        'NAYY 4x50 SE', 'NAYY 4x120 SE', 'NAYY 4x150 SE',
                        'NA2XS2Y 1x95 RM/25 12/20 kV', 'NA2XS2Y 1x185 RM/25 12/20 kV',
                        'NA2XS2Y 1x240 RM/25 12/20 kV', 'NA2XS2Y 1x300 RM/25 12/20 kV',
                        '15-AL1/3-ST1A 0.4', '24-AL1/4-ST1A 0.4', '48-AL1/8-ST1A 0.4',
                        '70-AL1/11-ST1A 0.4', '94-AL1/15-ST1A 0.4', '122-AL1/20-ST1A 0.4',
                        '149-AL1/24-ST1A 0.4', '184-AL1/30-ST1A 0.4', '243-AL1/39-ST1A 0.4'
                    ], 
                    'default': 'NAYY 4x50 SE',
                    'condition': {'use_standard_type': True}
                },
                
                # 自定义参数 (用于create_line_from_parameters)
                'r_ohm_per_km': {'type': 'float', 'label': '线路电阻 (Ω/km)', 'default': 0.1, 'min': 0.0, 'decimals': 4, 'condition': {'use_standard_type': False}},
                'x_ohm_per_km': {'type': 'float', 'label': '线路电抗 (Ω/km)', 'default': 0.1, 'min': 0.0, 'decimals': 4, 'condition': {'use_standard_type': False}},
                'c_nf_per_km': {'type': 'float', 'label': '线路电容 (nF/km)', 'default': 0.0, 'min': 0.0, 'decimals': 1, 'condition': {'use_standard_type': False}},
                'r0_ohm_per_km': {'type': 'float', 'label': '零序电阻 (Ω/km)', 'default': 0.0, 'min': 0.0, 'decimals': 4, 'condition': {'use_standard_type': False}},
                'x0_ohm_per_km': {'type': 'float', 'label': '零序电抗 (Ω/km)', 'default': 0.0, 'min': 0.0, 'decimals': 4, 'condition': {'use_standard_type': False}},
                'c0_nf_per_km': {'type': 'float', 'label': '零序电容 (nF/km)', 'default': 0.0, 'min': 0.0, 'decimals': 1, 'condition': {'use_standard_type': False}},
                'max_i_ka': {'type': 'float', 'label': '最大热电流 (kA)', 'default': 1.0, 'min': 0.001, 'decimals': 3, 'condition': {'use_standard_type': False}},
                
                # 连接属性（只读显示）
                'from_bus': {'type': 'readonly', 'label': '起始母线'},
                'to_bus': {'type': 'readonly', 'label': '终止母线'},
            },
            'transformer': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                # 通用参数
                'use_standard_type': {'type': 'bool', 'label': '使用标准类型', 'default': True},
                
                # 标准类型参数
                'std_type': {
                    'type': 'choice', 
                    'label': '标准类型', 
                    'choices': [
                        '160 MVA 380/110 kV', '100 MVA 220/110 kV',
                        '63 MVA 110/20 kV', '40 MVA 110/20 kV', '25 MVA 110/20 kV',
                        '0.25 MVA 20/0.4 kV', '0.4 MVA 20/0.4 kV', '0.63 MVA 20/0.4 kV',
                        '1.0 MVA 20/0.4 kV', '1.6 MVA 20/0.4 kV'
                    ], 
                    'default': '25 MVA 110/20 kV'
                },
                
                # 自定义类型参数 (用于create_transformer_from_parameters)
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 25.0, 'min': 0.1, 'max': 1000.0},
                'vn_hv_kv': {'type': 'float', 'label': '高压侧额定电压 (kV)', 'default': 110.0, 'min': 0.1, 'max': 1000.0},
                'vn_lv_kv': {'type': 'float', 'label': '低压侧额定电压 (kV)', 'default': 20.0, 'min': 0.1, 'max': 1000.0},
                'vkr_percent': {'type': 'float', 'label': '短路电阻电压 (%)', 'default': 0.3, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'vk_percent': {'type': 'float', 'label': '短路电压 (%)', 'default': 12.0, 'min': 0.1, 'max': 50.0},
                'pfe_kw': {'type': 'float', 'label': '铁损 (kW)', 'default': 14.0, 'min': 0.0, 'max': 10000.0},
                'i0_percent': {'type': 'float', 'label': '空载电流 (%)', 'default': 0.07, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'vector_group': {
                    'type': 'choice', 
                    'label': '接线组别', 
                    'choices': ['Dyn', 'Yyn', 'Yzn', 'YNyn'], 
                    'default': 'Dyn'
                },
                
                # 零序参数 (标准类型和自定义类型都需要)
                'vk0_percent': {'type': 'float', 'label': '零序短路电压 (%)', 'default': 0.0, 'min': 0.0, 'max': 50.0},
                'vkr0_percent': {'type': 'float', 'label': '零序短路电阻电压 (%)', 'default': 0.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'mag0_percent': {'type': 'float', 'label': '零序励磁阻抗 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0},
                'mag0_rx': {'type': 'float', 'label': '零序励磁R/X比', 'default': 0.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'si0_hv_partial': {'type': 'float', 'label': '零序漏抗高压侧分配', 'default': 0.0, 'min': 0.0, 'max': 1.0, 'decimals': 3},
                
                # 连接属性（只读显示）
                'hv_bus': {'type': 'readonly', 'label': '高压侧母线'},
                'lv_bus': {'type': 'readonly', 'label': '低压侧母线'},
            },

            'load': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                # 通用参数
                'use_power_factor': {'type': 'bool', 'label': '使用功率因数模式', 'default': False},
                
                # 直接功率模式参数
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 1.0, 'min': 0.0, 'max': 10000.0},
                
                # 功率因数模式参数
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 1.0, 'min': 0.1, 'max': 10000.0},
                'cos_phi': {'type': 'float', 'label': '功率因数', 'default': 0.9, 'min': 0.1, 'max': 1.0, 'decimals': 3},
                'mode': {'type': 'choice', 'label': '模式', 'choices': ['underexcited', 'overexcited'], 'default': 'underexcited'},
                # 其他参数
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                'bus': {'type': 'readonly', 'label': '连接母线', 'default': ''}
            },
            'storage': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                'sn_mva': {'type': 'float', 'label': '额定功率 (MVA)', 'default': 1.0, 'min': 0.1, 'max': 10000.0, 'decimals': 3},
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 0.0, 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'max_e_mwh': {'type': 'float', 'label': '最大储能容量 (MWh)', 'default': 1.0, 'min': 0.001, 'max': 100000.0, 'decimals': 3},
                'sn': {'type': 'str', 'label': '序列号', 'default': ''},
                'brand': {'type': 'str', 'label': '品牌', 'default': ''},
                'ip': {'type': 'str', 'label': 'IP地址', 'default': ''},
                'port': {'type': 'str', 'label': '端口', 'default': ''},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                'bus': {'type': 'readonly', 'label': '连接母线', 'default': ''}
            },
            'charger': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 1.0, 'min': 0.1, 'max': 1000.0},
                # 通用参数
                'use_power_factor': {'type': 'bool', 'label': '使用功率因数模式', 'default': False},
                
                # 直接功率模式参数
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 0.1, 'min': 0.0, 'max': 1000.0},
                
                # 功率因数模式参数
                'cos_phi': {'type': 'float', 'label': '功率因数', 'default': 0.9, 'min': 0.1, 'max': 1.0, 'decimals': 3},
                'mode': {'type': 'choice', 'label': '模式', 'choices': ['underexcited', 'overexcited'], 'default': 'underexcited'},
                
                # 设备信息
                'sn': {'type': 'str', 'label': '序列号', 'default': ''},
                'brand': {'type': 'str', 'label': '品牌', 'default': ''},
                'ip': {'type': 'str', 'label': 'IP地址', 'default': ''},
                'port': {'type': 'str', 'label': '端口', 'default': ''},
                
                # 其他参数
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                'bus': {'type': 'readonly', 'label': '连接母线', 'default': ''}
            },
            'external_grid': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                # 显示连接的母线
                'bus': {'type': 'readonly', 'label': '连接母线', 'default': ''}
            },
            'generator': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                # 通用参数
                'use_power_factor': {'type': 'bool', 'label': '使用功率因数模式', 'default': False},
                
                # 直接功率模式参数
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 1.0, 'min': 0.0, 'max': 10000.0},
                
                # 功率因数模式参数
                'sn_mva': {'type': 'float', 'label': '额定功率 (MVA)', 'default': 1.0, 'min': 0.1, 'max': 10000.0},
                'cos_phi': {'type': 'float', 'label': '功率因数', 'default': 0.9, 'min': 0.1, 'max': 1.0, 'decimals': 3},
                
                # 设备信息
                'ip': {'type': 'str', 'label': 'IP地址', 'default': ''},
                'port': {'type': 'str', 'label': '端口', 'default': ''},
                
                # 其他参数
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                'bus': {'type': 'readonly', 'label': '连接母线', 'default': ''}
            },
            'static_generator': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                # 通用参数
                'use_power_factor': {'type': 'bool', 'label': '使用功率因数模式', 'default': False},
                
                # 直接功率模式参数
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 1.0, 'min': 0.0, 'max': 10000.0},
                
                # 功率因数模式参数
                'sn_mva': {'type': 'float', 'label': '额定功率 (MVA)', 'default': 1.0, 'min': 0.1, 'max': 10000.0},
                'cos_phi': {'type': 'float', 'label': '功率因数', 'default': 0.9, 'min': 0.1, 'max': 1.0, 'decimals': 3},
                'mode': {'type': 'choice', 'label': '模式', 'choices': ['underexcited', 'overexcited'], 'default': 'underexcited'},
                # 设备信息
                'sn': {'type': 'str', 'label': '序列号', 'default': ''},
                'brand': {'type': 'str', 'label': '品牌', 'default': ''},
                'ip': {'type': 'str', 'label': 'IP地址', 'default': ''},
                'port': {'type': 'str', 'label': '端口', 'default': ''},
                
                # 其他参数
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                'bus': {'type': 'readonly', 'label': '连接母线', 'default': ''}
            },
            'meter': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
                'meas_type': {
                    'type': 'choice', 
                    'label': '测量类型', 
                    'choices': [
                        ('v', '电压 (V)'),
                        ('p', '有功功率 (P)'),
                        ('q', '无功功率 (Q)'),
                        ('i', '电流 (I)'),
                        ('va', '电压角度 (VA)'),
                        ('ia', '电流角度 (IA)')
                    ], 
                    'default': 'p'
                },
                'element_type': {
                    'type': 'choice', 
                    'label': '测量元件类型', 
                    'choices': [
                        ('bus', '母线'),
                        ('line', '线路'),
                        ('trafo', '变压器'),
                        ('trafo3w', '三绕组变压器'),
                        ('load', '负载'),
                        ('gen', '发电机'),
                        ('sgen', '光伏'),
                        ('shunt', '并联电抗器'),
                        ('ward', 'Ward等值'),
                        ('xward', '扩展Ward等值'),
                        ('ext_grid', '外部电网')
                    ], 
                    'default': 'bus'
                },
                'element': {'type': 'int', 'label': '元件索引', 'default': 0, 'min': 0, 'max': 999999},
                'side': {
                    'type': 'choice', 
                    'label': '测量侧', 
                    'choices': [
                        (None, '无'),
                        ('from', '起始侧'),
                        ('to', '终止侧'),
                        ('hv', '高压侧'),
                        ('mv', '中压侧'),
                        ('lv', '低压侧')
                    ], 
                    'default': None
                },
                # 设备信息
                'sn': {'type': 'str', 'label': '序列号', 'default': ''},
                'brand': {'type': 'str', 'label': '品牌', 'default': ''},
                'ip': {'type': 'str', 'label': 'IP地址', 'default': ''},
                'port': {'type': 'str', 'label': '端口', 'default': ''},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
            }
        }
        
        return properties.get(component_type, {})
    
    def is_dark_theme(self):
        """检测是否为深色主题"""
        app = QApplication.instance()
        if app:
            palette = app.palette()
            window_color = palette.color(QPalette.Window)
            return window_color.lightness() < 128
        return False
    
    def add_configuration_module(self):
        """添加配置控件模块，支持用户添加任意自定义字段及其对应值"""
        # 配置模块组
        config_group = QGroupBox("配置")
        config_layout = QVBoxLayout(config_group)
        
        # 自定义字段容器 - 使用滚动区域以便于浏览
        self.custom_fields_scroll = QScrollArea()
        self.custom_fields_scroll.setWidgetResizable(True)
        self.custom_fields_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.custom_fields_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 自定义字段容器部件
        self.custom_fields_container = QWidget()
        self.custom_fields_layout = QVBoxLayout(self.custom_fields_container)
        self.custom_fields_layout.setAlignment(Qt.AlignTop)
        self.custom_fields_layout.setSpacing(0)
        
        self.custom_fields_scroll.setWidget(self.custom_fields_container)
        config_layout.addWidget(self.custom_fields_scroll)
        
        # 添加自定义字段的按钮
        add_button = QPushButton("添加字段")
        add_button.clicked.connect(self.add_custom_field)
        config_layout.addWidget(add_button)
        
        # 初始化自定义字段数据结构
        if hasattr(self.current_item, 'properties'):
            # 从组件属性中获取已有的自定义字段
            custom_fields = self.current_item.properties.get('custom_fields', {})
            for field_name, field_value in custom_fields.items():
                self._create_custom_field_entry(field_name, field_value)
        
        self.properties_layout.addWidget(config_group)
    
    def add_custom_field(self):
        """添加一个新的自定义字段"""
        # 创建默认的字段名和值
        field_index = 1
        if hasattr(self.current_item, 'properties'):
            custom_fields = self.current_item.properties.get('custom_fields', {})
            field_index = len(custom_fields) + 1
        
        default_name = f"field_{field_index}"
        default_value = ""
        
        # 创建字段输入框
        self._create_custom_field_entry(default_name, default_value)
        
        # 保存到组件属性
        self._save_custom_fields()
    
    def _create_custom_field_entry(self, field_name, field_value):
        """创建一个自定义字段的输入项"""
        # 创建水平布局来放置字段名、字段值和删除按钮
        field_layout = QHBoxLayout()
        field_layout.setSpacing(0)
        field_layout.setAlignment(Qt.AlignLeft)
        field_layout.setContentsMargins(0, 0, 0, 0)  # 设置布局内容边距为0，使纵向更紧密
        
        # 字段名输入框
        name_edit = QLineEdit(field_name)
        name_edit.setMinimumWidth(100)
        name_edit.textChanged.connect(lambda: self._save_custom_fields())
        field_layout.addWidget(name_edit)
        
        # 字段值输入框
        value_edit = QLineEdit(str(field_value))
        value_edit.setMinimumWidth(100)
        value_edit.textChanged.connect(lambda: self._save_custom_fields())
        field_layout.addWidget(value_edit, 1)  # 让值输入框占据剩余空间
        
        # 删除按钮
        delete_button = QPushButton("删除")
        delete_button.setMinimumWidth(50)  # 增加最小宽度，确保文本显示完整
        delete_button.clicked.connect(lambda: self._remove_custom_field(field_layout))
        field_layout.addWidget(delete_button)
        
        # 创建一个容器部件来容纳这个布局
        field_widget = QWidget()
        field_widget.setLayout(field_layout)
        field_widget.setStyleSheet("margin: 0px; padding: 0px;")  # 移除部件的外边距和内边距
        
        # 添加到自定义字段容器
        self.custom_fields_layout.addWidget(field_widget)
    
    def _remove_custom_field(self, field_layout):
        """删除一个自定义字段"""
        # 找到包含这个布局的部件
        field_widget = None
        for i in range(self.custom_fields_layout.count()):
            widget = self.custom_fields_layout.itemAt(i).widget()
            if widget and widget.layout() == field_layout:
                field_widget = widget
                break
        
        # 删除部件
        if field_widget:
            self.custom_fields_layout.removeWidget(field_widget)
            field_widget.deleteLater()
        
        # 保存到组件属性
        self._save_custom_fields()
    
    def _save_custom_fields(self):
        """保存自定义字段到组件属性"""
        if not hasattr(self.current_item, 'properties'):
            return
        
        custom_fields = {}
        
        # 遍历所有自定义字段输入项
        for i in range(self.custom_fields_layout.count()):
            widget = self.custom_fields_layout.itemAt(i).widget()
            if widget and widget.layout():
                field_layout = widget.layout()
                if field_layout.count() >= 2:
                    # 获取字段名和字段值
                    name_edit = field_layout.itemAt(0).widget()
                    value_edit = field_layout.itemAt(1).widget()
                    
                    if hasattr(name_edit, 'text') and hasattr(value_edit, 'text'):
                        field_name = name_edit.text().strip()
                        field_value = value_edit.text().strip()
                        
                        if field_name:  # 只有当字段名不为空时才保存
                            custom_fields[field_name] = field_value
        
        # 保存到组件属性
        self.current_item.properties['custom_fields'] = custom_fields
        
        # 发出属性改变信号
        self.property_changed.emit(
            self.current_item.component_type, 'custom_fields', custom_fields
        )
    
    def update_theme_colors(self):
        """更新主题相关的所有颜色"""
        is_dark = self.is_dark_theme()
        
        if is_dark:
            # 深色主题样式
            self.setStyleSheet("""
                QWidget {
                    background-color: rgb(53, 53, 53);
                    color: rgb(255, 255, 255);
                }
                QLabel {
                    color: rgb(255, 255, 255);
                }
                QGroupBox {
                    color: rgb(255, 255, 255);
                    border: 2px solid rgb(80, 80, 80);
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 5px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: rgb(255, 255, 255);
                }
                QLineEdit {
                    background-color: rgb(42, 42, 42);
                    border: 1px solid rgb(80, 80, 80);
                    border-radius: 3px;
                    padding: 4px;
                    color: rgb(255, 255, 255);
                }
                QLineEdit:focus {
                    border: 2px solid rgb(42, 130, 218);
                }
                QLineEdit:read-only {
                    background-color: rgb(60, 60, 60);
                    color: rgb(200, 200, 200);
                }
                QComboBox {
                    background-color: rgb(42, 42, 42);
                    border: 1px solid rgb(80, 80, 80);
                    border-radius: 3px;
                    padding: 4px;
                    color: rgb(255, 255, 255);
                }
                QComboBox:focus {
                    border: 2px solid rgb(42, 130, 218);
                }
                QComboBox::drop-down {
                    border: none;
                    width: 0px;
                }
                QComboBox::down-arrow {
                    image: none;
                    width: 0px;
                    height: 0px;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: rgb(42, 42, 42);
                    border: 1px solid rgb(80, 80, 80);
                    border-radius: 3px;
                    padding: 4px;
                    color: rgb(255, 255, 255);
                }
                QSpinBox:focus, QDoubleSpinBox:focus {
                    border: 2px solid rgb(42, 130, 218);
                }
                QSpinBox::up-button, QDoubleSpinBox::up-button {
                    width: 0px;
                    height: 0px;
                }
                QSpinBox::down-button, QDoubleSpinBox::down-button {
                    width: 0px;
                    height: 0px;
                }
                QCheckBox {
                    color: rgb(255, 255, 255);
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid rgb(80, 80, 80);
                    border-radius: 3px;
                    background-color: rgb(42, 42, 42);
                }
                QCheckBox::indicator:checked {
                    background-color: rgb(42, 130, 218);
                    border: 1px solid rgb(42, 130, 218);
                }
                QScrollArea {
                    border: none;
                    background-color: rgb(53, 53, 53);
                }
                QScrollBar:vertical {
                    background-color: rgb(53, 53, 53);
                    width: 16px;
                    border: none;
                }
                QScrollBar::handle:vertical {
                    background-color: rgb(80, 80, 80);
                    border-radius: 8px;
                    min-height: 20px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgb(100, 100, 100);
                }
                QScrollBar::handle:vertical:pressed {
                    background-color: rgb(120, 120, 120);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                }
                QScrollBar:horizontal {
                    background-color: rgb(53, 53, 53);
                    height: 16px;
                    border: none;
                }
                QScrollBar::handle:horizontal {
                    background-color: rgb(80, 80, 80);
                    border-radius: 8px;
                    min-width: 20px;
                    margin: 2px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: rgb(100, 100, 100);
                }
                QScrollBar::handle:horizontal:pressed {
                    background-color: rgb(120, 120, 120);
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    border: none;
                    background: none;
                }
                QFrame[frameShape="4"] {
                    color: rgb(80, 80, 80);
                }
            """)
        else:
            # 浅色主题样式
            self.setStyleSheet("""
                QWidget {
                    background-color: rgb(240, 240, 240);
                    color: rgb(0, 0, 0);
                }
                QLabel {
                    color: rgb(0, 0, 0);
                }
                QGroupBox {
                    color: rgb(0, 0, 0);
                    border: 2px solid rgb(200, 200, 200);
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 5px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: rgb(0, 0, 0);
                }
                QLineEdit {
                    background-color: rgb(255, 255, 255);
                    border: 1px solid rgb(200, 200, 200);
                    border-radius: 3px;
                    padding: 4px;
                    color: rgb(0, 0, 0);
                }
                QLineEdit:focus {
                    border: 2px solid rgb(0, 120, 215);
                }
                QLineEdit:read-only {
                    background-color: rgb(245, 245, 245);
                    color: rgb(100, 100, 100);
                }
                QComboBox {
                    background-color: rgb(255, 255, 255);
                    border: 1px solid rgb(200, 200, 200);
                    border-radius: 3px;
                    padding: 4px;
                    color: rgb(0, 0, 0);
                }
                QComboBox:focus {
                    border: 2px solid rgb(0, 120, 215);
                }
                QComboBox::drop-down {
                    border: none;
                    width: 0px;
                }
                QComboBox::down-arrow {
                    image: none;
                    width: 0px;
                    height: 0px;
                }
                QSpinBox, QDoubleSpinBox {
                    background-color: rgb(255, 255, 255);
                    border: 1px solid rgb(200, 200, 200);
                    border-radius: 3px;
                    padding: 4px;
                    color: rgb(0, 0, 0);
                }
                QSpinBox:focus, QDoubleSpinBox:focus {
                    border: 2px solid rgb(0, 120, 215);
                }
                QSpinBox::up-button, QDoubleSpinBox::up-button {
                    width: 0px;
                    height: 0px;
                }
                QSpinBox::down-button, QDoubleSpinBox::down-button {
                    width: 0px;
                    height: 0px;
                }
                QCheckBox {
                    color: rgb(0, 0, 0);
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 1px solid rgb(200, 200, 200);
                    border-radius: 3px;
                    background-color: rgb(255, 255, 255);
                }
                QCheckBox::indicator:checked {
                    background-color: rgb(0, 120, 215);
                    border: 1px solid rgb(0, 120, 215);
                }
                QScrollArea {
                    border: none;
                    background-color: rgb(240, 240, 240);
                }
                QScrollBar:vertical {
                    background-color: rgb(240, 240, 240);
                    width: 16px;
                    border: none;
                }
                QScrollBar::handle:vertical {
                    background-color: rgb(200, 200, 200);
                    border-radius: 8px;
                    min-height: 20px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgb(180, 180, 180);
                }
                QScrollBar::handle:vertical:pressed {
                    background-color: rgb(160, 160, 160);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    border: none;
                    background: none;
                }
                QScrollBar:horizontal {
                    background-color: rgb(240, 240, 240);
                    height: 16px;
                    border: none;
                }
                QScrollBar::handle:horizontal {
                    background-color: rgb(200, 200, 200);
                    border-radius: 8px;
                    min-width: 20px;
                    margin: 2px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: rgb(180, 180, 180);
                }
                QScrollBar::handle:horizontal:pressed {
                    background-color: rgb(160, 160, 160);
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    border: none;
                    background: none;
                }
                QFrame[frameShape="4"] {
                    color: rgb(200, 200, 200);
                }
            """)
        
        # 更新"未选中组件"提示的样式
        self.update_no_selection_style()
    
    def update_no_selection_style(self):
        """更新未选中组件提示的样式"""
        try:
            if hasattr(self, 'no_selection_label') and self.no_selection_label and not self.no_selection_label.isHidden():
                is_dark = self.is_dark_theme()
                if is_dark:
                    self.no_selection_label.setStyleSheet("""
                        QLabel#noSelectionLabel {
                            color: rgb(150, 150, 150);
                            font-style: italic;
                            padding: 20px;
                            font-size: 14px;
                        }
                    """)
                else:
                    self.no_selection_label.setStyleSheet("""
                        QLabel#noSelectionLabel {
                            color: rgb(120, 120, 120);
                            font-style: italic;
                            padding: 20px;
                            font-size: 14px;
                        }
                    """)
        except RuntimeError:
            # QLabel对象已被删除，忽略错误
            pass