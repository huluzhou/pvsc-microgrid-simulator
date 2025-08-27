from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QGroupBox,
    QScrollArea, QFrame, QPushButton, QFormLayout, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor


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
        self.update_theme_colors()
        
        # 移除 standard_types，直接通过标准类型创建 pandapower 组件
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
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
            
            # 对于静态发电机组件，根据use_power_factor控制显示
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
                elif prop_name in ['sn_mva', 'cos_phi']:
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
                elif prop_name in ['sn_mva', 'cos_phi']:
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
                elif prop_name in ['sn_mva', 'cos_phi']:
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
            
            # 特殊处理线路和变压器的use_standard_type属性改变
            if prop_name == 'use_standard_type' and self.current_item.component_type in ['line', 'transformer']:
                # 重新刷新属性面板显示
                self.update_properties(self.current_item)
                return  # 避免重复发出信号
            
            # 特殊处理静态发电机的use_power_factor属性改变
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
                
                # 其他参数
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                'bus': {'type': 'readonly', 'label': '连接母线', 'default': ''}
            },
            'storage': {
                'index': {'type': 'readonly', 'label': '组件索引'},
                'geodata': {'type': 'readonly', 'label': '位置'},
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
                # 通用参数
                'use_power_factor': {'type': 'bool', 'label': '使用功率因数模式', 'default': False},
                
                # 直接功率模式参数
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 0.1, 'min': 0.0, 'max': 1000.0},
                
                # 功率因数模式参数
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 0.1, 'min': 0.1, 'max': 1000.0},
                'cos_phi': {'type': 'float', 'label': '功率因数', 'default': 0.9, 'min': 0.1, 'max': 1.0, 'decimals': 3},
                
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
                        ('sgen', '静态发电机'),
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