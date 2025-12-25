from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QComboBox, 
    QDoubleSpinBox, QSpinBox, QCheckBox, QGroupBox, QScrollArea, QWidget,
    QPushButton, QInputDialog, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
import pandapower as pp
class CustomPropertyEditor(QFrame):
    """自定义属性编辑器"""
    element_updated = Signal(dict)
    
    def __init__(self):
        super().__init__()
        
        self.device = None  # 当前选中的设备
        self.property_widgets = {}  # 存储属性控件
        self.custom_fields = {}  # 存储自定义字段信息：{device_type: [field_info]}
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI组件"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(10)
        
        # 标题
        title = QLabel("属性编辑器")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(title)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(line)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 属性容器
        self.properties_widget = QWidget()
        self.properties_layout = QVBoxLayout(self.properties_widget)
        self.properties_layout.setContentsMargins(0, 0, 0, 0)
        self.properties_layout.setSpacing(10)
        
        scroll_area.setWidget(self.properties_widget)
        self.layout.addWidget(scroll_area)
        
        # 默认显示提示
        self.show_no_selection()
    
    def show_no_selection(self):
        """显示未选中设备的提示"""
        self.clear_properties()
        
        self.no_selection_label = QLabel("请选择一个设备以查看其属性")
        self.no_selection_label.setAlignment(Qt.AlignCenter)
        self.no_selection_label.setStyleSheet("color: #666; font-size: 14px;")
        self.properties_layout.addWidget(self.no_selection_label)
    
    def clear_properties(self):
        """清空属性显示"""
        # 清除所有子控件和拉伸因子
        while self.properties_layout.count():
            child = self.properties_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.property_widgets.clear()
    
    def update_device_properties(self, device):
        """更新设备属性显示"""
        self.device = device
        self.clear_properties()
        
        if not self.device:
            self.show_no_selection()
            return
            
        # 设备信息组
        info_group = QGroupBox("设备信息")
        info_layout = QFormLayout(info_group)
        # 调整布局属性，实现宽度自适应
        info_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        info_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        info_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        info_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(8)
        
        # 设备类型
        type_to_name_map = {
            "bus": "母线",
            "line": "线路",
            "transformer": "变压器",
            "switch": "开关",
            "static_generator": "光伏",
            "storage": "储能",
            "load": "负载",
            "charger": "充电桩",
            "meter": "电表",
            "external_grid": "外部电网"
        }
        
        # 直接处理DeviceItem对象（图形项）
        device_type = self.device.device_type
        device_id = self.device.device_id
            
        display_name = type_to_name_map.get(device_type, device_type)+f" {device_id}"
        type_label = QLabel(device_type)
        type_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        info_layout.addRow("类型:", type_label)
        
        # 设备名称
        name_edit = QLineEdit(display_name)
        name_edit.textChanged.connect(lambda text: self.on_property_changed('name', text))
        info_layout.addRow("名称:", name_edit)
        self.property_widgets['name'] = name_edit
        
        # 设备ID
        id_label = QLabel(str(device_id))
        id_label.setStyleSheet("color: #666;")
        info_layout.addRow("ID:", id_label)
        
        self.properties_layout.addWidget(info_group)
        self.properties_layout.setAlignment(info_group, Qt.AlignTop)
        
        req_group = QGroupBox("必填参数")
        req_layout = QFormLayout(req_group)
        req_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        req_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        req_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        req_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        req_layout.setContentsMargins(10, 10, 10, 10)
        req_layout.setSpacing(8)
        opt_group = QGroupBox("可选参数")
        opt_layout = QFormLayout(opt_group)
        opt_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        opt_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        opt_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        opt_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        opt_layout.setContentsMargins(10, 10, 10, 10)
        opt_layout.setSpacing(8)
        added_req = False
        added_opt = False
        
        # 根据设备类型获取属性定义
        properties = self.get_component_properties(self.device.device_type)
        
        # 获取当前设备的属性值
        device_props = {}
        for prop_name in properties.keys():
            device_props[prop_name] = getattr(self.device, prop_name, properties[prop_name].get('default', ''))
        
        # 对于线路组件，显示所有参数，标准类型选择在第一行
        if self.device.device_type == 'line':
            # 1. 先显示标准类型选择下拉框，合并了是否使用标准类型的功能
            # 获取标准类型属性定义
            std_type_prop = properties['std_type'].copy()
            # 添加"自定义"选项到标准类型列表
            std_type_prop['choices'] = [('custom', '自定义')] + list(std_type_prop.get('choices', []))
            
            # 获取当前标准类型值
            std_type_value = device_props.get('std_type', properties['std_type'].get('default', ''))
            # 如果没有设置标准类型或使用自定义类型，设置为'custom'
            if not std_type_value or device_props.get('use_standard_type', True) is False:
                std_type_value = 'custom'
            
            # 创建并显示标准类型下拉框
            std_type_widget = self.create_property_widget('std_type', std_type_prop, std_type_value)
            if std_type_widget:
                label_text = properties['std_type'].get('label', 'std_type')
                target_layout = req_layout if properties['std_type'].get('required', False) else opt_layout
                target_layout.addRow(f"{label_text}:", std_type_widget)
                self.property_widgets['std_type'] = std_type_widget
                added_req = added_req or properties['std_type'].get('required', False)
                added_opt = added_opt or (not properties['std_type'].get('required', False))
            
            # 将use_standard_type设置为True，因为现在通过标准类型下拉框控制
            setattr(self.device, 'use_standard_type', True)
            
            # 获取并显示长度参数
            length_value = device_props.get('length_km', properties['length_km'].get('default', ''))
            length_widget = self.create_property_widget('length_km', properties['length_km'], length_value)
            if length_widget:
                label_text = properties['length_km'].get('label', 'length_km')
                target_layout = req_layout if properties['length_km'].get('required', False) else opt_layout
                target_layout.addRow(f"{label_text}:", length_widget)
                self.property_widgets['length_km'] = length_widget
                added_req = added_req or properties['length_km'].get('required', False)
                added_opt = added_opt or (not properties['length_km'].get('required', False))
            
            # 2. 然后显示所有其他参数
            for prop_name, prop_info in properties.items():
                # 跳过已经显示过的参数
                if prop_name in ['use_standard_type', 'std_type', 'length_km']:
                    continue
                    
                # 检查是否为自定义字段
                is_custom = False
                if self.device.device_type in self.custom_fields:
                    for field_info in self.custom_fields[self.device.device_type]:
                        if field_info["name"] == prop_name:
                            is_custom = True
                            break
                
                # 获取当前值
                current_value = getattr(self.device, prop_name, prop_info.get('default', ''))
                widget = self.create_property_widget(prop_name, prop_info, current_value)
                if widget:
                    label_text = prop_info.get('label', prop_name)
                    if prop_info.get('required', False):
                        label_text += "（必填）"
                        req_layout.addRow(f"{label_text}:", widget)
                        added_req = True
                    else:
                        opt_layout.addRow(f"{label_text}:", widget)
                        added_opt = True
                    self.property_widgets[prop_name] = widget
        
        # 对于变压器组件，显示所有参数，标准类型选择在第一行
        elif self.device.device_type == 'transformer':
            # 1. 先显示标准类型选择下拉框，合并了是否使用标准类型的功能
            # 获取标准类型属性定义
            std_type_prop = properties['std_type'].copy()
            # 添加"自定义"选项到标准类型列表
            std_type_prop['choices'] = [('custom', '自定义')] + list(std_type_prop.get('choices', []))
            
            # 获取当前标准类型值
            std_type_value = device_props.get('std_type', properties['std_type'].get('default', ''))
            # 如果没有设置标准类型或使用自定义类型，设置为'custom'
            if not std_type_value or device_props.get('use_standard_type', True) is False:
                std_type_value = 'custom'
            
            # 创建并显示标准类型下拉框
            std_type_widget = self.create_property_widget('std_type', std_type_prop, std_type_value)
            if std_type_widget:
                label_text = properties['std_type'].get('label', 'std_type')
                target_layout = req_layout if properties['std_type'].get('required', False) else opt_layout
                target_layout.addRow(f"{label_text}:", std_type_widget)
                self.property_widgets['std_type'] = std_type_widget
                added_req = added_req or properties['std_type'].get('required', False)
                added_opt = added_opt or (not properties['std_type'].get('required', False))
            
            # 将use_standard_type设置为True，因为现在通过标准类型下拉框控制
            setattr(self.device, 'use_standard_type', True)
            
            # 2. 然后显示所有其他参数
            for prop_name, prop_info in properties.items():
                # 跳过已经显示过的参数
                if prop_name in ['use_standard_type', 'std_type']:
                    continue
                    
                # 检查是否为自定义字段
                is_custom = False
                if self.device.device_type in self.custom_fields:
                    for field_info in self.custom_fields[self.device.device_type]:
                        if field_info["name"] == prop_name:
                            is_custom = True
                            break
                
                # 获取当前值
                current_value = getattr(self.device, prop_name, prop_info.get('default', ''))
                widget = self.create_property_widget(prop_name, prop_info, current_value)
                if widget:
                    label_text = prop_info.get('label', prop_name)
                    if prop_info.get('required', False):
                        label_text += "（必填）"
                        req_layout.addRow(f"{label_text}:", widget)
                        added_req = True
                    else:
                        opt_layout.addRow(f"{label_text}:", widget)
                        added_opt = True
                    self.property_widgets[prop_name] = widget
        
        # 对于其他设备类型，显示所有属性
        else:
            for prop_name, prop_info in properties.items():
                current_value = getattr(self.device, prop_name, prop_info.get('default', ''))
                widget = self.create_property_widget(prop_name, prop_info, current_value)
                if widget:
                    label_text = prop_info.get('label', prop_name)
                    if prop_info.get('required', False):
                        label_text += "（必填）"
                        req_layout.addRow(f"{label_text}:", widget)
                        added_req = True
                    else:
                        opt_layout.addRow(f"{label_text}:", widget)
                        added_opt = True
                    self.property_widgets[prop_name] = widget
        
        if added_req:
            self.properties_layout.addWidget(req_group)
            self.properties_layout.setAlignment(req_group, Qt.AlignTop)
        if added_opt:
            self.properties_layout.addWidget(opt_group)
            self.properties_layout.setAlignment(opt_group, Qt.AlignTop)
        
        comm_allowed = {'static_generator', 'storage', 'charger', 'meter'}
        if self.device.device_type in comm_allowed:
            comm_group = QGroupBox("通信参数")
            comm_layout = QFormLayout(comm_group)
            comm_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            comm_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
            comm_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            comm_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
            comm_layout.setContentsMargins(10, 10, 10, 10)
            comm_layout.setSpacing(8)
            comm_props = {
                'sn': {'type': 'str', 'label': '序列号', 'default': None},
                'brand': {'type': 'str', 'label': '品牌', 'default': None},
                'protocol': {'type': 'choice', 'label': '通信协议', 'choices': [('modbus_tcp', 'Modbus TCP'), ('modbus_rtu', 'Modbus RTU')], 'default': None},
                'ip_address': {'type': 'str', 'label': 'IP地址', 'default': None},
                'port': {'type': 'int', 'label': '端口', 'default': None, 'min': 1, 'max': 65535},
                'parity': {'type': 'choice', 'label': '奇偶校验', 'choices': [('none', '无'), ('even', '偶'), ('odd', '奇')], 'default': None},
                'baudrate': {'type': 'int', 'label': '波特率', 'default': None, 'min': 300, 'max': 1000000}
            }
            for prop_name, prop_info in comm_props.items():
                current_value = getattr(self.device, prop_name, prop_info.get('default', ''))
                widget = self.create_property_widget(prop_name, prop_info, current_value)
                if widget:
                    label_text = prop_info.get('label', prop_name)
                    comm_layout.addRow(f"{label_text}:", widget)
                    self.property_widgets[prop_name] = widget
            self.properties_layout.addWidget(comm_group)
            self.properties_layout.setAlignment(comm_group, Qt.AlignTop)
        
        custom_group = QGroupBox("自定义字段")
        custom_layout = QFormLayout(custom_group)
        custom_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        custom_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        custom_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        custom_layout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        custom_layout.setContentsMargins(10, 10, 10, 10)
        custom_layout.setSpacing(8)
        add_custom_field_btn = QPushButton("添加自定义字段")
        add_custom_field_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        add_custom_field_btn.clicked.connect(self._add_custom_field)
        custom_layout.addRow(add_custom_field_btn)
        if self.device.device_type in self.custom_fields:
            for field_info in self.custom_fields[self.device.device_type]:
                prop_name = field_info["name"]
                current_value = getattr(self.device, prop_name, field_info.get('default', ''))
                widget = self.create_property_widget(prop_name, field_info, current_value)
                if widget:
                    label_text = field_info.get('label', prop_name)
                    custom_layout.addRow(f"{label_text}:", widget)
                    self.property_widgets[prop_name] = widget
        self.properties_layout.addWidget(custom_group)
        self.properties_layout.setAlignment(custom_group, Qt.AlignTop)
        
        # 添加弹性空间
        self.properties_layout.addStretch()
    
    def _add_custom_field(self):
        """添加自定义字段"""
        if not self.device:
            return
        
        # 直接处理DeviceItem对象（图形项）
        device_type = self.device.device_type
        
        # 输入字段名称（用于内部存储和显示标签）
        field_name, ok = QInputDialog.getText(self, "添加自定义字段", "请输入字段名称：")
        if not ok or not field_name:
            return
        
        # 将字段名称作为内部存储名称，将其转换为更友好的显示标签
        # 将字段名称转换为显示标签：首字母大写，下划线转换为空格
        field_label = field_name.capitalize().replace('_', ' ')
        
        # 选择字段类型
        field_type, ok = QInputDialog.getItem(self, "添加自定义字段", "请选择字段类型：", 
                                             ["string", "float", "int", "bool"], 0, False)
        if not ok:
            return
        
        # 输入字段默认值
        default_value, ok = QInputDialog.getText(self, "添加自定义字段", f"请输入'{field_name}'的默认值：")
        if not ok:
            default_value = ""
        
        # 添加自定义字段信息到字典
        field_info = {
            "name": field_name,
            "label": field_label,
            "type": field_type,
            "default": default_value
        }
        
        # 初始化设备类型的自定义字段列表
        if device_type not in self.custom_fields:
            self.custom_fields[device_type] = []
        
        # 检查字段是否已存在
        for field in self.custom_fields[device_type]:
            if field["name"] == field_name:
                return
        
        # 添加字段信息
        self.custom_fields[device_type].append(field_info)
        
        # 更新属性显示
        self.update_device_properties(self.device)
    
    def create_property_widget(self, prop_name, prop_info, current_value):
        """根据属性类型创建编辑控件"""
        prop_type = prop_info.get('type', 'str')
        
        if prop_type == 'float':
            widget = QDoubleSpinBox()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.setMinimumHeight(28)
            widget.setRange(prop_info.get('min', -999999.0), prop_info.get('max', 999999.0))
            widget.setDecimals(prop_info.get('decimals', 3))
            widget.setValue(float(current_value) if current_value else 0.0)
            widget.valueChanged.connect(lambda value: self.on_property_changed(prop_name, value))
            return widget
            
        elif prop_type == 'int':
            widget = QSpinBox()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.setMinimumHeight(28)
            widget.setRange(prop_info.get('min', -999999), prop_info.get('max', 999999))
            widget.setValue(int(current_value) if current_value else 0)
            widget.valueChanged.connect(lambda value: self.on_property_changed(prop_name, value))
            return widget
            
        elif prop_type == 'bool':
            widget = QCheckBox()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.setMinimumHeight(28)
            widget.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
            widget.setChecked(bool(current_value))
            widget.toggled.connect(lambda checked: self.on_property_changed(prop_name, checked))
            return widget
            
        elif prop_type == 'choice':
            widget = QComboBox()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.setMinimumHeight(28)
            choices = prop_info.get('choices', [])
            
            for choice in choices:
                if isinstance(choice, tuple) and len(choice) == 2:
                    value, display_text = choice
                    widget.addItem(display_text, value)
                else:
                    widget.addItem(str(choice), choice)
            
            # 设置当前值
            for i in range(widget.count()):
                if widget.itemData(i) == current_value:
                    widget.setCurrentIndex(i)
                    break
            
            widget.currentIndexChanged.connect(
                lambda index: self.on_property_changed(prop_name, widget.itemData(index))
            )
            return widget
            
        elif prop_type == 'readonly':
            widget = QLabel()
            widget.setText(str(current_value) if current_value else '')
            widget.setStyleSheet("color: #666;")
            return widget
            
        else:  # 默认为字符串
            widget = QLineEdit()
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            widget.setMinimumHeight(28)
            widget.setText(str(current_value) if current_value else '')
            widget.textChanged.connect(lambda text: self.on_property_changed(prop_name, text))
            return widget
    
    def get_standard_parameters(self, device_type, std_type):
        """获取标准类型的参数值
        
        Args:
            device_type: 设备类型，如'line'或'transformer'
            std_type: 标准类型名称
            
        Returns:
            dict: 标准类型的参数值字典
        """
        # 根据设备类型返回对应的标准参数
        if device_type == 'line':
            # 线路标准参数表，包含所有标准类型参数：r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka, line_type, q_mm2, alpha
            line_std_params = {
                'NAYY 4x50 SE': {'r_ohm_per_km': 0.642, 'x_ohm_per_km': 0.083, 'c_nf_per_km': 210.0, 'max_i_ka': 0.142, 'line_type': 'cs', 'q_mm2': 50.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                'NAYY 4x120 SE': {'r_ohm_per_km': 0.225, 'x_ohm_per_km': 0.08, 'c_nf_per_km': 264.0, 'max_i_ka': 0.242, 'line_type': 'cs', 'q_mm2': 120.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                'NAYY 4x150 SE': {'r_ohm_per_km': 0.208, 'x_ohm_per_km': 0.08, 'c_nf_per_km': 261.0, 'max_i_ka': 0.27, 'line_type': 'cs', 'q_mm2': 150.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                'NA2XS2Y 1x70 RM/25 12/20 kV': {'r_ohm_per_km': 0.443, 'x_ohm_per_km': 0.132, 'c_nf_per_km': 190.0, 'max_i_ka': 0.22, 'line_type': 'cs', 'q_mm2': 70.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x95 RM/25 12/20 kV': {'r_ohm_per_km': 0.313, 'x_ohm_per_km': 0.132, 'c_nf_per_km': 216.0, 'max_i_ka': 0.252, 'line_type': 'cs', 'q_mm2': 95.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x120 RM/25 12/20 kV': {'r_ohm_per_km': 0.253, 'x_ohm_per_km': 0.119, 'c_nf_per_km': 230.0, 'max_i_ka': 0.283, 'line_type': 'cs', 'q_mm2': 120.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x150 RM/25 12/20 kV': {'r_ohm_per_km': 0.206, 'x_ohm_per_km': 0.116, 'c_nf_per_km': 250.0, 'max_i_ka': 0.319, 'line_type': 'cs', 'q_mm2': 150.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x185 RM/25 12/20 kV': {'r_ohm_per_km': 0.161, 'x_ohm_per_km': 0.117, 'c_nf_per_km': 273.0, 'max_i_ka': 0.362, 'line_type': 'cs', 'q_mm2': 185.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x240 RM/25 12/20 kV': {'r_ohm_per_km': 0.122, 'x_ohm_per_km': 0.112, 'c_nf_per_km': 304.0, 'max_i_ka': 0.421, 'line_type': 'cs', 'q_mm2': 240.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x300 RM/25 12/20 kV': {'r_ohm_per_km': 0.099, 'x_ohm_per_km': 0.149, 'c_nf_per_km': 125.0, 'max_i_ka': 0.457, 'line_type': 'cs', 'q_mm2': 300.0, 'alpha': 0.00393, 'voltage_rating': 'HV'},
                'NA2XS2Y 1x95 RM/25 6/10 kV': {'r_ohm_per_km': 0.313, 'x_ohm_per_km': 0.123, 'c_nf_per_km': 315.0, 'max_i_ka': 0.249, 'line_type': 'cs', 'q_mm2': 95.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x120 RM/25 6/10 kV': {'r_ohm_per_km': 0.253, 'x_ohm_per_km': 0.113, 'c_nf_per_km': 340.0, 'max_i_ka': 0.28, 'line_type': 'cs', 'q_mm2': 120.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x150 RM/25 6/10 kV': {'r_ohm_per_km': 0.206, 'x_ohm_per_km': 0.11, 'c_nf_per_km': 360.0, 'max_i_ka': 0.315, 'line_type': 'cs', 'q_mm2': 150.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x185 RM/25 6/10 kV': {'r_ohm_per_km': 0.161, 'x_ohm_per_km': 0.11, 'c_nf_per_km': 406.0, 'max_i_ka': 0.358, 'line_type': 'cs', 'q_mm2': 185.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'NA2XS2Y 1x240 RM/25 6/10 kV': {'r_ohm_per_km': 0.122, 'x_ohm_per_km': 0.105, 'c_nf_per_km': 456.0, 'max_i_ka': 0.416, 'line_type': 'cs', 'q_mm2': 240.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                'N2XS(FL)2Y 1x120 RM/35 64/110 kV': {'r_ohm_per_km': 0.153, 'x_ohm_per_km': 0.166, 'c_nf_per_km': 112.0, 'max_i_ka': 0.366, 'line_type': 'cs', 'q_mm2': 120.0, 'alpha': 0.00393, 'voltage_rating': 'HV'},
                'N2XS(FL)2Y 1x185 RM/35 64/110 kV': {'r_ohm_per_km': 0.099, 'x_ohm_per_km': 0.156, 'c_nf_per_km': 125.0, 'max_i_ka': 0.457, 'line_type': 'cs', 'q_mm2': 185.0, 'alpha': 0.00393, 'voltage_rating': 'HV'},
                'N2XS(FL)2Y 1x240 RM/35 64/110 kV': {'r_ohm_per_km': 0.075, 'x_ohm_per_km': 0.149, 'c_nf_per_km': 135.0, 'max_i_ka': 0.526, 'line_type': 'cs', 'q_mm2': 240.0, 'alpha': 0.00393, 'voltage_rating': 'HV'},
                'N2XS(FL)2Y 1x300 RM/35 64/110 kV': {'r_ohm_per_km': 0.06, 'x_ohm_per_km': 0.144, 'c_nf_per_km': 144.0, 'max_i_ka': 0.588, 'line_type': 'cs', 'q_mm2': 300.0, 'alpha': 0.00393, 'voltage_rating': 'HV'},
                '15-AL1/3-ST1A 0.4': {'r_ohm_per_km': 1.8769, 'x_ohm_per_km': 0.35, 'c_nf_per_km': 11.0, 'max_i_ka': 0.105, 'line_type': 'ol', 'q_mm2': 16.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '24-AL1/4-ST1A 0.4': {'r_ohm_per_km': 1.2012, 'x_ohm_per_km': 0.335, 'c_nf_per_km': 11.25, 'max_i_ka': 0.14, 'line_type': 'ol', 'q_mm2': 24.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '48-AL1/8-ST1A 0.4': {'r_ohm_per_km': 0.5939, 'x_ohm_per_km': 0.3, 'c_nf_per_km': 12.2, 'max_i_ka': 0.21, 'line_type': 'ol', 'q_mm2': 48.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '70-AL1/11-ST1A 0.4': {'r_ohm_per_km': 0.4132, 'x_ohm_per_km': 0.339, 'c_nf_per_km': 10.4, 'max_i_ka': 0.29, 'line_type': 'ol', 'q_mm2': 70.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '94-AL1/15-ST1A 0.4': {'r_ohm_per_km': 0.306, 'x_ohm_per_km': 0.29, 'c_nf_per_km': 13.2, 'max_i_ka': 0.35, 'line_type': 'ol', 'q_mm2': 94.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '122-AL1/20-ST1A 0.4': {'r_ohm_per_km': 0.2376, 'x_ohm_per_km': 0.323, 'c_nf_per_km': 11.1, 'max_i_ka': 0.41, 'line_type': 'ol', 'q_mm2': 122.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '149-AL1/24-ST1A 0.4': {'r_ohm_per_km': 0.194, 'x_ohm_per_km': 0.315, 'c_nf_per_km': 11.25, 'max_i_ka': 0.47, 'line_type': 'ol', 'q_mm2': 149.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '184-AL1/30-ST1A 0.4': {'r_ohm_per_km': 0.1571, 'x_ohm_per_km': 0.33, 'c_nf_per_km': 10.75, 'max_i_ka': 0.535, 'line_type': 'ol', 'q_mm2': 184.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '243-AL1/39-ST1A 0.4': {'r_ohm_per_km': 0.1188, 'x_ohm_per_km': 0.32, 'c_nf_per_km': 11.0, 'max_i_ka': 0.645, 'line_type': 'ol', 'q_mm2': 243.0, 'alpha': 0.00403, 'voltage_rating': 'LV'},
                '34-AL1/6-ST1A 10.0': {'r_ohm_per_km': 0.8342, 'x_ohm_per_km': 0.36, 'c_nf_per_km': 9.7, 'max_i_ka': 0.17, 'line_type': 'ol', 'q_mm2': 34.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '48-AL1/8-ST1A 10.0': {'r_ohm_per_km': 0.5939, 'x_ohm_per_km': 0.35, 'c_nf_per_km': 10.1, 'max_i_ka': 0.21, 'line_type': 'ol', 'q_mm2': 48.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '70-AL1/11-ST1A 10.0': {'r_ohm_per_km': 0.4132, 'x_ohm_per_km': 0.36, 'c_nf_per_km': 9.7, 'max_i_ka': 0.29, 'line_type': 'ol', 'q_mm2': 70.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '94-AL1/15-ST1A 10.0': {'r_ohm_per_km': 0.306, 'x_ohm_per_km': 0.33, 'c_nf_per_km': 10.75, 'max_i_ka': 0.35, 'line_type': 'ol', 'q_mm2': 94.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '122-AL1/20-ST1A 10.0': {'r_ohm_per_km': 0.2376, 'x_ohm_per_km': 0.323, 'c_nf_per_km': 11.1, 'max_i_ka': 0.41, 'line_type': 'ol', 'q_mm2': 122.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '149-AL1/24-ST1A 10.0': {'r_ohm_per_km': 0.194, 'x_ohm_per_km': 0.315, 'c_nf_per_km': 11.25, 'max_i_ka': 0.47, 'line_type': 'ol', 'q_mm2': 149.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '34-AL1/6-ST1A 20.0': {'r_ohm_per_km': 0.8342, 'x_ohm_per_km': 0.382, 'c_nf_per_km': 9.15, 'max_i_ka': 0.17, 'line_type': 'ol', 'q_mm2': 34.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '48-AL1/8-ST1A 20.0': {'r_ohm_per_km': 0.5939, 'x_ohm_per_km': 0.372, 'c_nf_per_km': 9.5, 'max_i_ka': 0.21, 'line_type': 'ol', 'q_mm2': 48.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '70-AL1/11-ST1A 20.0': {'r_ohm_per_km': 0.4132, 'x_ohm_per_km': 0.36, 'c_nf_per_km': 9.7, 'max_i_ka': 0.29, 'line_type': 'ol', 'q_mm2': 70.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '94-AL1/15-ST1A 20.0': {'r_ohm_per_km': 0.306, 'x_ohm_per_km': 0.35, 'c_nf_per_km': 10.0, 'max_i_ka': 0.35, 'line_type': 'ol', 'q_mm2': 94.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '122-AL1/20-ST1A 20.0': {'r_ohm_per_km': 0.2376, 'x_ohm_per_km': 0.344, 'c_nf_per_km': 10.3, 'max_i_ka': 0.41, 'line_type': 'ol', 'q_mm2': 122.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '149-AL1/24-ST1A 20.0': {'r_ohm_per_km': 0.194, 'x_ohm_per_km': 0.337, 'c_nf_per_km': 10.5, 'max_i_ka': 0.47, 'line_type': 'ol', 'q_mm2': 149.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '184-AL1/30-ST1A 20.0': {'r_ohm_per_km': 0.1571, 'x_ohm_per_km': 0.33, 'c_nf_per_km': 10.75, 'max_i_ka': 0.535, 'line_type': 'ol', 'q_mm2': 184.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '243-AL1/39-ST1A 20.0': {'r_ohm_per_km': 0.1188, 'x_ohm_per_km': 0.32, 'c_nf_per_km': 11.0, 'max_i_ka': 0.645, 'line_type': 'ol', 'q_mm2': 243.0, 'alpha': 0.00403, 'voltage_rating': 'MV'},
                '48-AL1/8-ST1A 110.0': {'r_ohm_per_km': 0.5939, 'x_ohm_per_km': 0.46, 'c_nf_per_km': 8.0, 'max_i_ka': 0.21, 'line_type': 'ol', 'q_mm2': 48.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '70-AL1/11-ST1A 110.0': {'r_ohm_per_km': 0.4132, 'x_ohm_per_km': 0.45, 'c_nf_per_km': 8.4, 'max_i_ka': 0.29, 'line_type': 'ol', 'q_mm2': 70.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '94-AL1/15-ST1A 110.0': {'r_ohm_per_km': 0.306, 'x_ohm_per_km': 0.44, 'c_nf_per_km': 8.65, 'max_i_ka': 0.35, 'line_type': 'ol', 'q_mm2': 94.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '122-AL1/20-ST1A 110.0': {'r_ohm_per_km': 0.2376, 'x_ohm_per_km': 0.43, 'c_nf_per_km': 8.5, 'max_i_ka': 0.41, 'line_type': 'ol', 'q_mm2': 122.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '149-AL1/24-ST1A 110.0': {'r_ohm_per_km': 0.194, 'x_ohm_per_km': 0.41, 'c_nf_per_km': 8.75, 'max_i_ka': 0.47, 'line_type': 'ol', 'q_mm2': 149.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '184-AL1/30-ST1A 110.0': {'r_ohm_per_km': 0.1571, 'x_ohm_per_km': 0.4, 'c_nf_per_km': 8.8, 'max_i_ka': 0.535, 'line_type': 'ol', 'q_mm2': 184.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '243-AL1/39-ST1A 110.0': {'r_ohm_per_km': 0.1188, 'x_ohm_per_km': 0.39, 'c_nf_per_km': 9.0, 'max_i_ka': 0.645, 'line_type': 'ol', 'q_mm2': 243.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '305-AL1/39-ST1A 110.0': {'r_ohm_per_km': 0.0949, 'x_ohm_per_km': 0.38, 'c_nf_per_km': 9.2, 'max_i_ka': 0.74, 'line_type': 'ol', 'q_mm2': 305.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '490-AL1/64-ST1A 110.0': {'r_ohm_per_km': 0.059, 'x_ohm_per_km': 0.37, 'c_nf_per_km': 9.75, 'max_i_ka': 0.96, 'line_type': 'ol', 'q_mm2': 490.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '679-AL1/86-ST1A 110.0': {'r_ohm_per_km': 0.042, 'x_ohm_per_km': 0.36, 'c_nf_per_km': 9.95, 'max_i_ka': 1.15, 'line_type': 'ol', 'q_mm2': 679.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '490-AL1/64-ST1A 220.0': {'r_ohm_per_km': 0.059, 'x_ohm_per_km': 0.285, 'c_nf_per_km': 10.0, 'max_i_ka': 0.96, 'line_type': 'ol', 'q_mm2': 490.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '679-AL1/86-ST1A 220.0': {'r_ohm_per_km': 0.042, 'x_ohm_per_km': 0.275, 'c_nf_per_km': 11.7, 'max_i_ka': 1.15, 'line_type': 'ol', 'q_mm2': 679.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '490-AL1/64-ST1A 380.0': {'r_ohm_per_km': 0.059, 'x_ohm_per_km': 0.253, 'c_nf_per_km': 11.0, 'max_i_ka': 0.96, 'line_type': 'ol', 'q_mm2': 490.0, 'alpha': 0.00403, 'voltage_rating': 'HV'},
                '679-AL1/86-ST1A 380.0': {'r_ohm_per_km': 0.042, 'x_ohm_per_km': 0.25, 'c_nf_per_km': 14.6, 'max_i_ka': 1.15, 'line_type': 'ol', 'q_mm2': 679.0, 'alpha': 0.00403, 'voltage_rating': 'HV'}
            }
            return line_std_params.get(std_type, {})
        elif device_type == 'transformer':
            # 变压器标准参数表
            transformer_std_params = {
                '160 MVA 380/110 kV': {'sn_mva': 160.0, 'vn_hv_kv': 380.0, 'vn_lv_kv': 110.0, 'vk_percent': 12.2, 'vkr_percent': 0.25, 'pfe_kw': 60.0, 'i0_percent': 0.06, 'shift_degree': 0.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '100 MVA 220/110 kV': {'sn_mva': 100.0, 'vn_hv_kv': 220.0, 'vn_lv_kv': 110.0, 'vk_percent': 12.0, 'vkr_percent': 0.26, 'pfe_kw': 55.0, 'i0_percent': 0.06, 'shift_degree': 0.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '63 MVA 110/20 kV': {'sn_mva': 63.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 20.0, 'vk_percent': 18.0, 'vkr_percent': 0.32, 'pfe_kw': 22.0, 'i0_percent': 0.04, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '40 MVA 110/20 kV': {'sn_mva': 40.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 20.0, 'vk_percent': 16.2, 'vkr_percent': 0.34, 'pfe_kw': 18.0, 'i0_percent': 0.05, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '25 MVA 110/20 kV': {'sn_mva': 25.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 20.0, 'vk_percent': 12.0, 'vkr_percent': 0.41, 'pfe_kw': 14.0, 'i0_percent': 0.07, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '63 MVA 110/10 kV': {'sn_mva': 63.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 10.0, 'vk_percent': 18.0, 'vkr_percent': 0.32, 'pfe_kw': 22.0, 'i0_percent': 0.04, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '40 MVA 110/10 kV': {'sn_mva': 40.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 10.0, 'vk_percent': 16.2, 'vkr_percent': 0.34, 'pfe_kw': 18.0, 'i0_percent': 0.05, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '25 MVA 110/10 kV': {'sn_mva': 25.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 10.0, 'vk_percent': 12.0, 'vkr_percent': 0.41, 'pfe_kw': 14.0, 'i0_percent': 0.07, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '0.25 MVA 20/0.4 kV': {'sn_mva': 0.25, 'vn_hv_kv': 20.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.44, 'pfe_kw': 0.8, 'i0_percent': 0.32, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '0.4 MVA 20/0.4 kV': {'sn_mva': 0.4, 'vn_hv_kv': 20.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.425, 'pfe_kw': 1.35, 'i0_percent': 0.3375, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '0.63 MVA 20/0.4 kV': {'sn_mva': 0.63, 'vn_hv_kv': 20.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.206, 'pfe_kw': 1.65, 'i0_percent': 0.2619, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '0.25 MVA 10/0.4 kV': {'sn_mva': 0.25, 'vn_hv_kv': 10.0, 'vn_lv_kv': 0.4, 'vk_percent': 4.0, 'vkr_percent': 1.2, 'pfe_kw': 0.6, 'i0_percent': 0.24, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '0.4 MVA 10/0.4 kV': {'sn_mva': 0.4, 'vn_hv_kv': 10.0, 'vn_lv_kv': 0.4, 'vk_percent': 4.0, 'vkr_percent': 1.325, 'pfe_kw': 0.95, 'i0_percent': 0.2375, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'},
                '0.63 MVA 10/0.4 kV': {'sn_mva': 0.63, 'vn_hv_kv': 10.0, 'vn_lv_kv': 0.4, 'vk_percent': 4.0, 'vkr_percent': 1.0794, 'pfe_kw': 1.18, 'i0_percent': 0.1873, 'shift_degree': 150.0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0.0, 'tap_changer_type': 'Ratio'}
            }
            return transformer_std_params.get(std_type, {})
        return {}
    
    def _update_parameters_from_standard(self, std_type):
        """从标准类型更新参数值
        
        Args:
            std_type: 标准类型名称
        """
        if not self.device:
            return
        
        # 如果选择了"自定义"类型，不更新参数值
        if std_type == 'custom':
            # 发送属性更新信号
            self._emit_property_updated_signal()
            return
        
        device_type = self.device.device_type
        # 获取标准参数
        std_params = self.get_standard_parameters(device_type, std_type)
        
        # 更新设备属性和界面控件
        for param_name, param_value in std_params.items():
            # 1. 更新设备属性值
            setattr(self.device, param_name, param_value)
            
            # 2. 更新界面控件值
            if param_name in self.property_widgets:
                widget = self.property_widgets[param_name]
                # 根据控件类型更新值
                if hasattr(widget, 'setValue'):  # 数值类型控件
                    widget.setValue(param_value)
                elif hasattr(widget, 'setText'):  # 文本类型控件
                    widget.setText(str(param_value))
        
        # 发送属性更新信号
        self._emit_property_updated_signal()
    
    def on_property_changed(self, prop_name, new_value):
        """属性值变化事件"""
        if not self.device:
            return
        
        # 1. 先更新设备属性值，确保数据一致性
        setattr(self.device, prop_name, new_value)
        
        # 2. 特殊处理标准类型选择变化
        if prop_name == 'std_type':
            # 从标准类型更新参数
            self._update_parameters_from_standard(new_value)
            return
        
        # 3. 发送属性更新信号，通过信号槽机制让外部处理领域层的数据更新
        self._emit_property_updated_signal()
    
    def _get_all_device_properties(self):
        """获取当前设备的所有属性"""
        all_properties = {}
        for prop in self.property_widgets.keys():
            all_properties[prop] = getattr(self.device, prop, "")
        return all_properties
    
    def _emit_property_updated_signal(self):
        """发送属性更新信号"""
        # 获取设备信息（直接处理DeviceItem对象）
        device_type = self.device.device_type
        device_id = self.device.device_id
        
        # 构建属性字典
        properties = {
            "type": device_type,
            "id": device_id,
            "name": getattr(self.device, 'name', device_type)
        }
        
        # 添加其他属性
        for prop in self.property_widgets.keys():
            if hasattr(self.device, prop):
                properties[prop] = getattr(self.device, prop)
        
        # 发送信号
        self.element_updated.emit(properties)
    
    def get_component_properties(self, component_type):
        """获取组件属性定义"""
        # 基于pandapower文档的属性定义
        properties = {
            'bus': {
                'vn_kv': {'type': 'float', 'label': '电网电压等级 (kV)', 'default': None, 'min': 0.1, 'required': True}
            },
            'line': {
                # 按照pandapower文档中net.line表格顺序排列的参数
                # 功率流计算必要参数（*）
                'std_type': {
                    'type': 'choice', 
                    'label': '标准类型', 
                    'choices': [
                        # 电缆类型
                        'NAYY 4x50 SE', 'NAYY 4x120 SE', 'NAYY 4x150 SE',
                        'NA2XS2Y 1x70 RM/25 12/20 kV', 'NA2XS2Y 1x95 RM/25 12/20 kV',
                        'NA2XS2Y 1x120 RM/25 12/20 kV', 'NA2XS2Y 1x150 RM/25 12/20 kV',
                        'NA2XS2Y 1x185 RM/25 12/20 kV', 'NA2XS2Y 1x240 RM/25 12/20 kV',
                        'NA2XS2Y 1x300 RM/25 12/20 kV',
                        'NA2XS2Y 1x95 RM/25 6/10 kV', 'NA2XS2Y 1x120 RM/25 6/10 kV',
                        'NA2XS2Y 1x150 RM/25 6/10 kV', 'NA2XS2Y 1x185 RM/25 6/10 kV',
                        'NA2XS2Y 1x240 RM/25 6/10 kV',
                        'N2XS(FL)2Y 1x120 RM/35 64/110 kV', 'N2XS(FL)2Y 1x185 RM/35 64/110 kV',
                        'N2XS(FL)2Y 1x240 RM/35 64/110 kV', 'N2XS(FL)2Y 1x300 RM/35 64/110 kV',
                        # 架空线类型 - 0.4kV
                        '15-AL1/3-ST1A 0.4', '24-AL1/4-ST1A 0.4', '48-AL1/8-ST1A 0.4',
                        '70-AL1/11-ST1A 0.4', '94-AL1/15-ST1A 0.4', '122-AL1/20-ST1A 0.4',
                        '149-AL1/24-ST1A 0.4', '184-AL1/30-ST1A 0.4', '243-AL1/39-ST1A 0.4',
                        # 架空线类型 - 10kV
                        '34-AL1/6-ST1A 10.0', '48-AL1/8-ST1A 10.0', '70-AL1/11-ST1A 10.0',
                        '94-AL1/15-ST1A 10.0', '122-AL1/20-ST1A 10.0', '149-AL1/24-ST1A 10.0',
                        # 架空线类型 - 20kV
                        '34-AL1/6-ST1A 20.0', '48-AL1/8-ST1A 20.0', '70-AL1/11-ST1A 20.0',
                        '94-AL1/15-ST1A 20.0', '122-AL1/20-ST1A 20.0', '149-AL1/24-ST1A 20.0',
                        '184-AL1/30-ST1A 20.0', '243-AL1/39-ST1A 20.0',
                        # 架空线类型 - 110kV
                        '48-AL1/8-ST1A 110.0', '70-AL1/11-ST1A 110.0', '94-AL1/15-ST1A 110.0',
                        '122-AL1/20-ST1A 110.0', '149-AL1/24-ST1A 110.0', '184-AL1/30-ST1A 110.0',
                        '243-AL1/39-ST1A 110.0', '305-AL1/39-ST1A 110.0', '490-AL1/64-ST1A 110.0',
                        '679-AL1/86-ST1A 110.0',
                        # 架空线类型 - 220kV
                        '490-AL1/64-ST1A 220.0', '679-AL1/86-ST1A 220.0',
                        # 架空线类型 - 380kV
                        '490-AL1/64-ST1A 380.0', '679-AL1/86-ST1A 380.0'
                    ], 
                    'default': None,
                    'required': True
                },
                'from_bus': {'type': 'int', 'label': '起始母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'to_bus': {'type': 'int', 'label': '终止母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'length_km': {'type': 'float', 'label': '长度 (km)', 'default': None, 'min': 0.001, 'max': 1000.0, 'decimals': 3, 'required': True},
                'r_ohm_per_km': {'type': 'float', 'label': '线路电阻 (Ω/km)', 'default': 0.642, 'min': 0.0, 'decimals': 4},
                'x_ohm_per_km': {'type': 'float', 'label': '线路电抗 (Ω/km)', 'default': 0.083, 'min': 0.0, 'decimals': 4},
                'c_nf_per_km': {'type': 'float', 'label': '线路电容 (nF/km)', 'default': 210.0, 'min': 0.0, 'decimals': 1},
                'g_us_per_km': {'type': 'float', 'label': '电导 (μS/km)', 'default': 0.0, 'min': 0.0, 'decimals': 4},
                'max_i_ka': {'type': 'float', 'label': '最大热电流 (kA)', 'default': 0.142, 'min': 0.001, 'decimals': 3},
                'parallel': {'type': 'int', 'label': '并联数量', 'default': 1, 'min': 1, 'max': 100},
                'df': {'type': 'float', 'label': '负载分配系数', 'default': 1.0, 'min': 0.0, 'max': 1.0, 'decimals': 3},
                'line_type': {'type': 'choice', 'label': '线路类型', 'choices': [('cs', '电缆'), ('ol', '架空线')], 'default': 'cs'},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                
                # 标准类型参数
                'q_mm2': {'type': 'float', 'label': '截面积 (mm²)', 'default': 50.0, 'min': 0.1, 'decimals': 1},
                'alpha': {'type': 'float', 'label': '温度系数', 'default': 0.00403, 'min': 0.0, 'decimals': 5}
            },
            'transformer': {
                # 通用参数
                'use_standard_type': {'type': 'bool', 'label': '使用标准类型', 'default': True},
                
                # 标准类型参数
                'std_type': {
                    'type': 'choice', 
                    'label': '标准类型', 
                    'choices': [
                        '160 MVA 380/110 kV', '100 MVA 220/110 kV',
                        '63 MVA 110/20 kV', '40 MVA 110/20 kV', '25 MVA 110/20 kV',
                        '63 MVA 110/10 kV', '40 MVA 110/10 kV', '25 MVA 110/10 kV',
                        '0.25 MVA 20/0.4 kV', '0.4 MVA 20/0.4 kV', '0.63 MVA 20/0.4 kV',
                        '0.25 MVA 10/0.4 kV', '0.4 MVA 10/0.4 kV', '0.63 MVA 10/0.4 kV'
                    ], 
                    'default': None,
                    'required': True
                },
                
                # 基本参数
                'hv_bus': {'type': 'int', 'label': '高压侧母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'lv_bus': {'type': 'int', 'label': '低压侧母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 25.0, 'min': 0.1, 'max': 1000.0},
                'vn_hv_kv': {'type': 'float', 'label': '高压侧额定电压 (kV)', 'default': 110.0, 'min': 0.1, 'max': 1000.0},
                'vn_lv_kv': {'type': 'float', 'label': '低压侧额定电压 (kV)', 'default': 20.0, 'min': 0.1, 'max': 1000.0},
                'vk_percent': {'type': 'float', 'label': '短路电压 (%)', 'default': 12.0, 'min': 0.1, 'max': 50.0},
                'vkr_percent': {'type': 'float', 'label': '短路电阻电压 (%)', 'default': 0.41, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'pfe_kw': {'type': 'float', 'label': '铁损 (kW)', 'default': 14.0, 'min': 0.0, 'max': 10000.0},
                'i0_percent': {'type': 'float', 'label': '空载电流 (%)', 'default': 0.07, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'shift_degree': {'type': 'float', 'label': '相位偏移 (°)', 'default': 0.0, 'min': -180.0, 'max': 180.0, 'decimals': 3},
                
                # 用户指定的额外字段
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                'max_loading_percent': {'type': 'float', 'label': '最大负载 (%)', 'default': 100.0, 'min': 0.0, 'max': 1000.0, 'decimals': 1},
                'oltc': {'type': 'bool', 'label': '有载分接开关', 'default': False},
                'power_station_unit': {'type': 'bool', 'label': '电站单元', 'default': False},
                'leakage_resistance_ratio_hv': {'type': 'float', 'label': '高压侧漏电阻比', 'default': 0.0, 'min': 0.0, 'max': 10.0, 'decimals': 4},
                'leakage_reactance_ratio_hv': {'type': 'float', 'label': '高压侧漏电抗比', 'default': 0.0, 'min': 0.0, 'max': 10.0, 'decimals': 4},
                
                # 标准类型要求的字段
                'vector_group': {
                    'type': 'choice', 
                    'label': '接线组别', 
                    'choices': ['Yy0', 'YNd5', 'Yzn5', 'Dyn5'], 
                    'default': 'YNd5'
                },
                'tap_side': {'type': 'choice', 'label': '分接开关位置', 'choices': [('hv', '高压侧'), ('lv', '低压侧')], 'default': 'hv'},
                'tap_neutral': {'type': 'int', 'label': '中性点分接位置', 'default': 0, 'min': -100, 'max': 100},
                'tap_min': {'type': 'int', 'label': '最小分接位置', 'default': -9, 'min': -100, 'max': 0},
                'tap_max': {'type': 'int', 'label': '最大分接位置', 'default': 9, 'min': 0, 'max': 100},
                'tap_step_percent': {'type': 'float', 'label': '电压分接步长 (%)', 'default': 1.5, 'min': 0.01, 'max': 10.0, 'decimals': 3},
                'tap_step_degree': {'type': 'float', 'label': '角度分接步长 (°)', 'default': 0.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'tap_changer_type': {
                    'type': 'choice', 
                    'label': '分接开关类型', 
                    'choices': [('Ratio', '变比'), ('None', '无')], 
                    'default': 'Ratio'
                },
            },
            'load': {
                'bus': {'type': 'int', 'label': '连接母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': None, 'min': -10000.0, 'max': 10000.0, 'decimals': 3, 'required': True},
                'q_mvar': {'type': 'float', 'label': '无功功率 (MVAr)', 'default': 0.0, 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'const_z_p_percent': {'type': 'float', 'label': '常阻抗有功比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'const_i_p_percent': {'type': 'float', 'label': '常电流有功比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'const_z_q_percent': {'type': 'float', 'label': '常阻抗无功比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'const_i_q_percent': {'type': 'float', 'label': '常电流无功比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': float('nan'), 'min': 0.0, 'max': 10000.0, 'decimals': 3},
                'scaling': {'type': 'float', 'label': '缩放系数', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'type': {'type': 'choice', 'label': '接线类型', 'choices': ['wye', 'delta'], 'default': 'wye'},
                'controllable': {'type': 'bool', 'label': '可控', 'default': None},
                'max_p_mw': {'type': 'float', 'label': '最大有功 (MW)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'min_p_mw': {'type': 'float', 'label': '最小有功 (MW)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'max_q_mvar': {'type': 'float', 'label': '最大无功 (MVAr)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'min_q_mvar': {'type': 'float', 'label': '最小无功 (MVAr)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'storage': {
                'bus': {'type': 'int', 'label': '连接母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': None, 'min': -10000.0, 'max': 10000.0, 'decimals': 3, 'required': True},
                'max_e_mwh': {'type': 'float', 'label': '最大储能 (MWh)', 'default': None, 'min': 0.0, 'max': 100000.0, 'decimals': 3, 'required': True},
                'q_mvar': {'type': 'float', 'label': '无功功率 (MVAr)', 'default': 0.0, 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'sn_mva': {'type': 'float', 'label': '额定功率 (MVA)', 'default': float('nan'), 'min': 0.0, 'max': 10000.0, 'decimals': 3},
                'soc_percent': {'type': 'float', 'label': '荷电状态 (%)', 'default': float('nan'), 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'min_e_mwh': {'type': 'float', 'label': '最小储能 (MWh)', 'default': 0.0, 'min': 0.0, 'max': 100000.0, 'decimals': 3},
                'scaling': {'type': 'float', 'label': '缩放系数', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'type': {'type': 'str', 'label': '类型', 'default': None},
                'max_p_mw': {'type': 'float', 'label': '最大有功 (MW)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'min_p_mw': {'type': 'float', 'label': '最小有功 (MW)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'max_q_mvar': {'type': 'float', 'label': '最大无功 (MVAr)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'min_q_mvar': {'type': 'float', 'label': '最小无功 (MVAr)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'controllable': {'type': 'bool', 'label': '可控', 'default': None},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'charger': {
                'name': {'type': 'str', 'label': '名称', 'default': None},
                'bus': {'type': 'int', 'label': '连接母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': None, 'min': -1000.0, 'max': 1000.0, 'decimals': 3, 'required': True},
                'q_mvar': {'type': 'float', 'label': '无功功率 (MVAr)', 'default': 0.0, 'min': -1000.0, 'max': 1000.0, 'decimals': 3},
                'const_z_p_percent': {'type': 'float', 'label': '常阻抗有功比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'const_i_p_percent': {'type': 'float', 'label': '常电流有功比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'const_z_q_percent': {'type': 'float', 'label': '常阻抗无功比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'const_i_q_percent': {'type': 'float', 'label': '常电流无功比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0, 'decimals': 3},
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': float('nan'), 'min': 0.0, 'max': 1000.0, 'decimals': 3},
                'scaling': {'type': 'float', 'label': '缩放系数', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'type': {'type': 'choice', 'label': '接线类型', 'choices': ['wye', 'delta'], 'default': 'wye'},
                'controllable': {'type': 'bool', 'label': '可控', 'default': None},
                'max_p_mw': {'type': 'float', 'label': '最大有功 (MW)', 'default': float('nan'), 'min': -1000.0, 'max': 1000.0, 'decimals': 3},
                'min_p_mw': {'type': 'float', 'label': '最小有功 (MW)', 'default': float('nan'), 'min': -1000.0, 'max': 1000.0, 'decimals': 3},
                'max_q_mvar': {'type': 'float', 'label': '最大无功 (MVAr)', 'default': float('nan'), 'min': -1000.0, 'max': 1000.0, 'decimals': 3},
                'min_q_mvar': {'type': 'float', 'label': '最小无功 (MVAr)', 'default': float('nan'), 'min': -1000.0, 'max': 1000.0, 'decimals': 3},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'external_grid': {
                'name': {'type': 'str', 'label': '名称', 'default': None},
                'bus': {'type': 'int', 'label': '连接母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'vm_pu': {'type': 'float', 'label': '电压设定值 (p.u.)', 'default': 1.0, 'min': 0.0, 'max': 2.0, 'decimals': 3},
                'va_degree': {'type': 'float', 'label': '角度设定值 (°)', 'default': 0.0, 'min': -180.0, 'max': 180.0, 'decimals': 3},
                's_sc_max_mva': {'type': 'float', 'label': '最大短路容量 (MVA)', 'default': float('nan'), 'min': 0.0, 'max': 1e9, 'decimals': 3},
                's_sc_min_mva': {'type': 'float', 'label': '最小短路容量 (MVA)', 'default': float('nan'), 'min': 0.0, 'max': 1e9, 'decimals': 3},
                'rx_max': {'type': 'float', 'label': '最大R/X', 'default': float('nan'), 'min': 0.0, 'max': 1e6, 'decimals': 6},
                'rx_min': {'type': 'float', 'label': '最小R/X', 'default': float('nan'), 'min': 0.0, 'max': 1e6, 'decimals': 6},
                'r0x0_max': {'type': 'float', 'label': '最大零序R/X', 'default': float('nan'), 'min': 0.0, 'max': 1e6, 'decimals': 6},
                'x0x_max': {'type': 'float', 'label': '最大零序X0/X', 'default': float('nan'), 'min': 0.0, 'max': 1e6, 'decimals': 6},
                'max_p_mw': {'type': 'float', 'label': '最大有功 (MW)', 'default': float('nan'), 'min': -1e9, 'max': 1e9, 'decimals': 3},
                'min_p_mw': {'type': 'float', 'label': '最小有功 (MW)', 'default': float('nan'), 'min': -1e9, 'max': 1e9, 'decimals': 3},
                'max_q_mvar': {'type': 'float', 'label': '最大无功 (MVAr)', 'default': float('nan'), 'min': -1e9, 'max': 1e9, 'decimals': 3},
                'min_q_mvar': {'type': 'float', 'label': '最小无功 (MVAr)', 'default': float('nan'), 'min': -1e9, 'max': 1e9, 'decimals': 3},
                'controllable': {'type': 'bool', 'label': '可控', 'default': None},
                'slack_weight': {'type': 'float', 'label': '分配平衡权重', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'static_generator': {
                'bus': {'type': 'int', 'label': '连接母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': None, 'min': 0.0, 'max': 10000.0, 'decimals': 3, 'required': True},
                'q_mvar': {'type': 'float', 'label': '无功功率 (MVAr)', 'default': 0.0, 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'sn_mva': {'type': 'float', 'label': '额定功率 (MVA)', 'default': None, 'min': 0.0, 'max': 10000.0, 'decimals': 3},
                'scaling': {'type': 'float', 'label': '缩放系数', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'type': {'type': 'choice', 'label': '类型', 'choices': ['wye', 'delta'], 'default': None},
                'max_p_mw': {'type': 'float', 'label': '最大有功 (MW)', 'default': float('nan'), 'min': 0.0, 'max': 10000.0, 'decimals': 3},
                'min_p_mw': {'type': 'float', 'label': '最小有功 (MW)', 'default': float('nan'), 'min': 0.0, 'max': 10000.0, 'decimals': 3},
                'max_q_mvar': {'type': 'float', 'label': '最大无功 (MVAr)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'min_q_mvar': {'type': 'float', 'label': '最小无功 (MVAr)', 'default': float('nan'), 'min': -10000.0, 'max': 10000.0, 'decimals': 3},
                'controllable': {'type': 'bool', 'label': '可控', 'default': None},
                'k': {'type': 'float', 'label': '短路电流比 k', 'default': float('nan'), 'min': 0.0, 'max': 1000.0, 'decimals': 3},
                'rx': {'type': 'float', 'label': '短路阻抗 R/X 比', 'default': float('nan'), 'min': 0.0, 'max': 1000.0, 'decimals': 3},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True},
                'id_q_capability_characteristic': {'type': 'int', 'label': 'Q能力曲线ID', 'default': None, 'min': 0, 'max': 999999},
                'reactive_capability_curve': {'type': 'bool', 'label': '有无Q能力曲线', 'default': False},
                'curve_style': {'type': 'choice', 'label': '曲线样式', 'choices': ['straightLineYValues', 'constantYValue'], 'default': None},
                'current_source': {'type': 'bool', 'label': '短路模型为电流源', 'default': True},
                'generator_type': {'type': 'choice', 'label': '发电机类型', 'choices': ['current_source', 'async', 'async_doubly_fed'], 'default': 'current_source'},
                'max_ik_ka': {'type': 'float', 'label': '最大瞬时短路电流 (kA)', 'default': float('nan'), 'min': 0.0, 'max': 1000.0, 'decimals': 3},
                'kappa': {'type': 'float', 'label': '峰值短路电流系数 κ', 'default': float('nan'), 'min': 0.0, 'max': 1000.0, 'decimals': 3},
                'lrc_pu': {'type': 'float', 'label': '锁定转子电流 (p.u.)', 'default': float('nan'), 'min': 0.0, 'max': 1000.0, 'decimals': 3}
            },
            'meter': {
                'type': {
                    'type': 'choice',
                    'label': '测量类型',
                    'choices': [
                        ('v', '电压 (V)'),
                        ('p', '有功功率 (P)'),
                        ('q', '无功功率 (Q)'),
                        ('i', '电流 (I)')
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
                        ('sgen', '光伏/静态发电机'),
                        ('ext_grid', '外部电网'),
                        ('storage', '储能设备'),
                        ('charger', '充电设备'),
                        ('shunt', '并联电抗器'),
                        ('ward', 'Ward等值'),
                        ('xward', '扩展Ward等值'),
                    ], 
                    'default': 'bus'
                },
                'value': {'type': 'float', 'label': '测量值', 'default': 0.0, 'min': -1e9, 'max': 1e9, 'decimals': 6},
                'std_dev': {'type': 'float', 'label': '标准差', 'default': 0.0, 'min': 0.0, 'max': 1e6, 'decimals': 6},
                'bus': {'type': 'int', 'label': '测量母线', 'default': 0, 'min': 0, 'max': 999999},
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
                'check_existing': {'type': 'bool', 'label': '检查并覆盖已有测量', 'default': True},
                'index': {'type': 'int', 'label': '测量索引', 'default': 0, 'min': 0, 'max': 999999}
            },
            'switch': {
                'bus': {'type': 'int', 'label': '连接母线', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'name': {'type': 'str', 'label': '名称', 'default': ''},
                'element': {'type': 'int', 'label': '元件索引', 'default': None, 'min': 0, 'max': 999999, 'required': True},
                'et': {'type': 'choice', 'label': '元件类型', 'choices': [('b', '母线'), ('l', '线路'), ('t', '变压器'), ('t3', '三绕组变压器')], 'default': None, 'required': True},
                'type': {'type': 'choice', 'label': '开关类型', 'choices': [('CB', '断路器'), ('LS', '负荷开关'), ('LBS', '负荷隔离开关'), ('DS', '隔离开关')], 'default': 'CB'},
                'closed': {'type': 'bool', 'label': '闭合状态', 'default': True},
                'in_ka': {'type': 'float', 'label': '额定电流 (kA)', 'default': 0.1, 'min': 0.001, 'max': 1000.0, 'decimals': 3},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            }
        }
        
        return properties.get(component_type, {})
