from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QGroupBox,
    QScrollArea, QFrame, QPushButton, QFormLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class PropertiesPanel(QWidget):
    """组件属性面板"""
    
    # 信号：属性值改变时发出
    property_changed = Signal(str, str, object)  # component_type, property_name, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_item = None
        self.property_widgets = {}
        self.init_ui()
        
        # pandapower标准类型数据 - 完整参数表
        self.standard_types = {
            'line': {
                # 电缆类型
                'NAYY 4x50 SE': {'r_ohm_per_km': 0.642, 'x_ohm_per_km': 0.083, 'c_nf_per_km': 210.0, 'max_i_ka': 0.142, 'type': 'cs', 'q_mm2': 50, 'alpha': 0.00403},
                'NAYY 4x120 SE': {'r_ohm_per_km': 0.225, 'x_ohm_per_km': 0.08, 'c_nf_per_km': 264.0, 'max_i_ka': 0.242, 'type': 'cs', 'q_mm2': 120, 'alpha': 0.00403},
                'NAYY 4x150 SE': {'r_ohm_per_km': 0.208, 'x_ohm_per_km': 0.08, 'c_nf_per_km': 261.0, 'max_i_ka': 0.27, 'type': 'cs', 'q_mm2': 150, 'alpha': 0.00403},
                'NA2XS2Y 1x95 RM/25 12/20 kV': {'r_ohm_per_km': 0.313, 'x_ohm_per_km': 0.132, 'c_nf_per_km': 216.0, 'max_i_ka': 0.252, 'type': 'cs', 'q_mm2': 95, 'alpha': 0.00403},
                'NA2XS2Y 1x185 RM/25 12/20 kV': {'r_ohm_per_km': 0.161, 'x_ohm_per_km': 0.117, 'c_nf_per_km': 273.0, 'max_i_ka': 0.362, 'type': 'cs', 'q_mm2': 185, 'alpha': 0.00403},
                'NA2XS2Y 1x240 RM/25 12/20 kV': {'r_ohm_per_km': 0.122, 'x_ohm_per_km': 0.112, 'c_nf_per_km': 304.0, 'max_i_ka': 0.421, 'type': 'cs', 'q_mm2': 240, 'alpha': 0.00403},
                'NA2XS2Y 1x95 RM/25 6/10 kV': {'r_ohm_per_km': 0.313, 'x_ohm_per_km': 0.123, 'c_nf_per_km': 315.0, 'max_i_ka': 0.249, 'type': 'cs', 'q_mm2': 95, 'alpha': 0.00403},
                'NA2XS2Y 1x185 RM/25 6/10 kV': {'r_ohm_per_km': 0.161, 'x_ohm_per_km': 0.11, 'c_nf_per_km': 406.0, 'max_i_ka': 0.358, 'type': 'cs', 'q_mm2': 185, 'alpha': 0.00403},
                'NA2XS2Y 1x240 RM/25 6/10 kV': {'r_ohm_per_km': 0.122, 'x_ohm_per_km': 0.105, 'c_nf_per_km': 456.0, 'max_i_ka': 0.416, 'type': 'cs', 'q_mm2': 240, 'alpha': 0.00403},
                'NA2XS2Y 1x150 RM/25 12/20 kV': {'r_ohm_per_km': 0.206, 'x_ohm_per_km': 0.116, 'c_nf_per_km': 250.0, 'max_i_ka': 0.319, 'type': 'cs', 'q_mm2': 150, 'alpha': 0.00403},
                'NA2XS2Y 1x120 RM/25 12/20 kV': {'r_ohm_per_km': 0.253, 'x_ohm_per_km': 0.119, 'c_nf_per_km': 230.0, 'max_i_ka': 0.283, 'type': 'cs', 'q_mm2': 120, 'alpha': 0.00403},
                'NA2XS2Y 1x70 RM/25 12/20 kV': {'r_ohm_per_km': 0.443, 'x_ohm_per_km': 0.132, 'c_nf_per_km': 190.0, 'max_i_ka': 0.22, 'type': 'cs', 'q_mm2': 70, 'alpha': 0.00403},
                'NA2XS2Y 1x150 RM/25 6/10 kV': {'r_ohm_per_km': 0.206, 'x_ohm_per_km': 0.11, 'c_nf_per_km': 360.0, 'max_i_ka': 0.315, 'type': 'cs', 'q_mm2': 150, 'alpha': 0.00403},
                'NA2XS2Y 1x120 RM/25 6/10 kV': {'r_ohm_per_km': 0.253, 'x_ohm_per_km': 0.113, 'c_nf_per_km': 340.0, 'max_i_ka': 0.28, 'type': 'cs', 'q_mm2': 120, 'alpha': 0.00403},
                'NA2XS2Y 1x70 RM/25 6/10 kV': {'r_ohm_per_km': 0.443, 'x_ohm_per_km': 0.123, 'c_nf_per_km': 280.0, 'max_i_ka': 0.217, 'type': 'cs', 'q_mm2': 70, 'alpha': 0.00403},
                'N2XS(FL)2Y 1x120 RM/35 64/110 kV': {'r_ohm_per_km': 0.153, 'x_ohm_per_km': 0.166, 'c_nf_per_km': 112.0, 'max_i_ka': 0.366, 'type': 'cs', 'q_mm2': 120, 'alpha': 0.00393},
                'N2XS(FL)2Y 1x185 RM/35 64/110 kV': {'r_ohm_per_km': 0.099, 'x_ohm_per_km': 0.156, 'c_nf_per_km': 125.0, 'max_i_ka': 0.457, 'type': 'cs', 'q_mm2': 185, 'alpha': 0.00393},
                'N2XS(FL)2Y 1x240 RM/35 64/110 kV': {'r_ohm_per_km': 0.075, 'x_ohm_per_km': 0.149, 'c_nf_per_km': 135.0, 'max_i_ka': 0.526, 'type': 'cs', 'q_mm2': 240, 'alpha': 0.00393},
                'N2XS(FL)2Y 1x300 RM/35 64/110 kV': {'r_ohm_per_km': 0.06, 'x_ohm_per_km': 0.144, 'c_nf_per_km': 144.0, 'max_i_ka': 0.588, 'type': 'cs', 'q_mm2': 300, 'alpha': 0.00393},
                # 架空线路类型
                '15-AL1/3-ST1A 0.4': {'r_ohm_per_km': 1.8769, 'x_ohm_per_km': 0.35, 'c_nf_per_km': 11.0, 'max_i_ka': 0.105, 'type': 'ol', 'q_mm2': 16, 'alpha': 0.00403},
                '24-AL1/4-ST1A 0.4': {'r_ohm_per_km': 1.2012, 'x_ohm_per_km': 0.335, 'c_nf_per_km': 11.25, 'max_i_ka': 0.14, 'type': 'ol', 'q_mm2': 24, 'alpha': 0.00403},
                '48-AL1/8-ST1A 0.4': {'r_ohm_per_km': 0.5939, 'x_ohm_per_km': 0.3, 'c_nf_per_km': 12.2, 'max_i_ka': 0.21, 'type': 'ol', 'q_mm2': 48, 'alpha': 0.00403},
                '94-AL1/15-ST1A 0.4': {'r_ohm_per_km': 0.306, 'x_ohm_per_km': 0.29, 'c_nf_per_km': 13.2, 'max_i_ka': 0.35, 'type': 'ol', 'q_mm2': 94, 'alpha': 0.00403},
                '34-AL1/6-ST1A 10.0': {'r_ohm_per_km': 0.8342, 'x_ohm_per_km': 0.36, 'c_nf_per_km': 9.7, 'max_i_ka': 0.17, 'type': 'ol', 'q_mm2': 34, 'alpha': 0.00403},
                '48-AL1/8-ST1A 10.0': {'r_ohm_per_km': 0.5939, 'x_ohm_per_km': 0.35, 'c_nf_per_km': 10.1, 'max_i_ka': 0.21, 'type': 'ol', 'q_mm2': 48, 'alpha': 0.00403},
                '70-AL1/11-ST1A 10.0': {'r_ohm_per_km': 0.4132, 'x_ohm_per_km': 0.339, 'c_nf_per_km': 10.4, 'max_i_ka': 0.29, 'type': 'ol', 'q_mm2': 70, 'alpha': 0.00403},
                '94-AL1/15-ST1A 10.0': {'r_ohm_per_km': 0.306, 'x_ohm_per_km': 0.33, 'c_nf_per_km': 10.75, 'max_i_ka': 0.35, 'type': 'ol', 'q_mm2': 94, 'alpha': 0.00403},
                '122-AL1/20-ST1A 10.0': {'r_ohm_per_km': 0.2376, 'x_ohm_per_km': 0.323, 'c_nf_per_km': 11.1, 'max_i_ka': 0.41, 'type': 'ol', 'q_mm2': 122, 'alpha': 0.00403},
                '149-AL1/24-ST1A 10.0': {'r_ohm_per_km': 0.194, 'x_ohm_per_km': 0.315, 'c_nf_per_km': 11.25, 'max_i_ka': 0.47, 'type': 'ol', 'q_mm2': 149, 'alpha': 0.00403},
                '34-AL1/6-ST1A 20.0': {'r_ohm_per_km': 0.8342, 'x_ohm_per_km': 0.382, 'c_nf_per_km': 9.15, 'max_i_ka': 0.17, 'type': 'ol', 'q_mm2': 34, 'alpha': 0.00403},
                '48-AL1/8-ST1A 20.0': {'r_ohm_per_km': 0.5939, 'x_ohm_per_km': 0.372, 'c_nf_per_km': 9.5, 'max_i_ka': 0.21, 'type': 'ol', 'q_mm2': 48, 'alpha': 0.00403},
                '70-AL1/11-ST1A 20.0': {'r_ohm_per_km': 0.4132, 'x_ohm_per_km': 0.36, 'c_nf_per_km': 9.7, 'max_i_ka': 0.29, 'type': 'ol', 'q_mm2': 70, 'alpha': 0.00403},
                '94-AL1/15-ST1A 20.0': {'r_ohm_per_km': 0.306, 'x_ohm_per_km': 0.35, 'c_nf_per_km': 10.0, 'max_i_ka': 0.35, 'type': 'ol', 'q_mm2': 94, 'alpha': 0.00403},
                '122-AL1/20-ST1A 20.0': {'r_ohm_per_km': 0.2376, 'x_ohm_per_km': 0.344, 'c_nf_per_km': 10.3, 'max_i_ka': 0.41, 'type': 'ol', 'q_mm2': 122, 'alpha': 0.00403},
                '149-AL1/24-ST1A 20.0': {'r_ohm_per_km': 0.194, 'x_ohm_per_km': 0.337, 'c_nf_per_km': 10.5, 'max_i_ka': 0.47, 'type': 'ol', 'q_mm2': 149, 'alpha': 0.00403},
                '184-AL1/30-ST1A 20.0': {'r_ohm_per_km': 0.1571, 'x_ohm_per_km': 0.33, 'c_nf_per_km': 10.75, 'max_i_ka': 0.535, 'type': 'ol', 'q_mm2': 184, 'alpha': 0.00403},
                '243-AL1/39-ST1A 20.0': {'r_ohm_per_km': 0.1188, 'x_ohm_per_km': 0.32, 'c_nf_per_km': 11.0, 'max_i_ka': 0.645, 'type': 'ol', 'q_mm2': 243, 'alpha': 0.00403},
                '48-AL1/8-ST1A 110.0': {'r_ohm_per_km': 0.5939, 'x_ohm_per_km': 0.46, 'c_nf_per_km': 8.0, 'max_i_ka': 0.21, 'type': 'ol', 'q_mm2': 48, 'alpha': 0.00403},
                '70-AL1/11-ST1A 110.0': {'r_ohm_per_km': 0.4132, 'x_ohm_per_km': 0.45, 'c_nf_per_km': 8.4, 'max_i_ka': 0.29, 'type': 'ol', 'q_mm2': 70, 'alpha': 0.00403},
                '94-AL1/15-ST1A 110.0': {'r_ohm_per_km': 0.306, 'x_ohm_per_km': 0.44, 'c_nf_per_km': 8.65, 'max_i_ka': 0.35, 'type': 'ol', 'q_mm2': 94, 'alpha': 0.00403},
                '122-AL1/20-ST1A 110.0': {'r_ohm_per_km': 0.2376, 'x_ohm_per_km': 0.43, 'c_nf_per_km': 8.5, 'max_i_ka': 0.41, 'type': 'ol', 'q_mm2': 122, 'alpha': 0.00403},
                '149-AL1/24-ST1A 110.0': {'r_ohm_per_km': 0.194, 'x_ohm_per_km': 0.41, 'c_nf_per_km': 8.75, 'max_i_ka': 0.47, 'type': 'ol', 'q_mm2': 149, 'alpha': 0.00403},
                '184-AL1/30-ST1A 110.0': {'r_ohm_per_km': 0.1571, 'x_ohm_per_km': 0.4, 'c_nf_per_km': 8.8, 'max_i_ka': 0.535, 'type': 'ol', 'q_mm2': 184, 'alpha': 0.00403},
                '243-AL1/39-ST1A 110.0': {'r_ohm_per_km': 0.1188, 'x_ohm_per_km': 0.39, 'c_nf_per_km': 9.0, 'max_i_ka': 0.645, 'type': 'ol', 'q_mm2': 243, 'alpha': 0.00403},
                '305-AL1/39-ST1A 110.0': {'r_ohm_per_km': 0.0949, 'x_ohm_per_km': 0.38, 'c_nf_per_km': 9.2, 'max_i_ka': 0.74, 'type': 'ol', 'q_mm2': 305, 'alpha': 0.00403},
                '490-AL1/64-ST1A 110.0': {'r_ohm_per_km': 0.059, 'x_ohm_per_km': 0.37, 'c_nf_per_km': 9.75, 'max_i_ka': 0.96, 'type': 'ol', 'q_mm2': 490, 'alpha': 0.00403},
                '679-AL1/86-ST1A 110.0': {'r_ohm_per_km': 0.042, 'x_ohm_per_km': 0.36, 'c_nf_per_km': 9.95, 'max_i_ka': 1.15, 'type': 'ol', 'q_mm2': 679, 'alpha': 0.00403},
                '490-AL1/64-ST1A 220.0': {'r_ohm_per_km': 0.059, 'x_ohm_per_km': 0.285, 'c_nf_per_km': 10.0, 'max_i_ka': 0.96, 'type': 'ol', 'q_mm2': 490, 'alpha': 0.00403},
                '679-AL1/86-ST1A 220.0': {'r_ohm_per_km': 0.042, 'x_ohm_per_km': 0.275, 'c_nf_per_km': 11.7, 'max_i_ka': 1.15, 'type': 'ol', 'q_mm2': 679, 'alpha': 0.00403},
                '490-AL1/64-ST1A 380.0': {'r_ohm_per_km': 0.059, 'x_ohm_per_km': 0.253, 'c_nf_per_km': 11.0, 'max_i_ka': 0.96, 'type': 'ol', 'q_mm2': 490, 'alpha': 0.00403},
                '679-AL1/86-ST1A 380.0': {'r_ohm_per_km': 0.042, 'x_ohm_per_km': 0.25, 'c_nf_per_km': 14.6, 'max_i_ka': 1.15, 'type': 'ol', 'q_mm2': 679, 'alpha': 0.00403}
            },
            'transformer': {
                '160 MVA 380/110 kV': {'sn_mva': 160.0, 'vn_hv_kv': 380.0, 'vn_lv_kv': 110.0, 'vk_percent': 12.2, 'vkr_percent': 0.25, 'pfe_kw': 60.0, 'i0_percent': 0.06, 'shift_degree': 0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '100 MVA 220/110 kV': {'sn_mva': 100.0, 'vn_hv_kv': 220.0, 'vn_lv_kv': 110.0, 'vk_percent': 12.0, 'vkr_percent': 0.26, 'pfe_kw': 55.0, 'i0_percent': 0.06, 'shift_degree': 0, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '63 MVA 110/20 kV': {'sn_mva': 63.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 20.0, 'vk_percent': 18.0, 'vkr_percent': 0.32, 'pfe_kw': 22.0, 'i0_percent': 0.04, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '40 MVA 110/20 kV': {'sn_mva': 40.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 20.0, 'vk_percent': 16.2, 'vkr_percent': 0.34, 'pfe_kw': 18.0, 'i0_percent': 0.05, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '25 MVA 110/20 kV': {'sn_mva': 25.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 20.0, 'vk_percent': 12.0, 'vkr_percent': 0.41, 'pfe_kw': 14.0, 'i0_percent': 0.07, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '63 MVA 110/10 kV': {'sn_mva': 63.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 10.0, 'vk_percent': 18.0, 'vkr_percent': 0.32, 'pfe_kw': 22.0, 'i0_percent': 0.04, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '40 MVA 110/10 kV': {'sn_mva': 40.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 10.0, 'vk_percent': 16.2, 'vkr_percent': 0.34, 'pfe_kw': 18.0, 'i0_percent': 0.05, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '25 MVA 110/10 kV': {'sn_mva': 25.0, 'vn_hv_kv': 110.0, 'vn_lv_kv': 10.0, 'vk_percent': 12.0, 'vkr_percent': 0.41, 'pfe_kw': 14.0, 'i0_percent': 0.07, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -9, 'tap_max': 9, 'tap_step_percent': 1.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '0.25 MVA 20/0.4 kV': {'sn_mva': 0.25, 'vn_hv_kv': 20.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.44, 'pfe_kw': 0.95, 'i0_percent': 0.38, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '0.4 MVA 20/0.4 kV': {'sn_mva': 0.4, 'vn_hv_kv': 20.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.325, 'pfe_kw': 1.35, 'i0_percent': 0.3375, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '0.63 MVA 20/0.4 kV': {'sn_mva': 0.63, 'vn_hv_kv': 20.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.206, 'pfe_kw': 1.65, 'i0_percent': 0.2619, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '1.0 MVA 20/0.4 kV': {'sn_mva': 1.0, 'vn_hv_kv': 20.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.08, 'pfe_kw': 2.7, 'i0_percent': 0.27, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '1.6 MVA 20/0.4 kV': {'sn_mva': 1.6, 'vn_hv_kv': 20.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 0.875, 'pfe_kw': 3.25, 'i0_percent': 0.203125, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '0.25 MVA 10/0.4 kV': {'sn_mva': 0.25, 'vn_hv_kv': 10.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.44, 'pfe_kw': 0.95, 'i0_percent': 0.38, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '0.4 MVA 10/0.4 kV': {'sn_mva': 0.4, 'vn_hv_kv': 10.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.325, 'pfe_kw': 1.35, 'i0_percent': 0.3375, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '0.63 MVA 10/0.4 kV': {'sn_mva': 0.63, 'vn_hv_kv': 10.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.206, 'pfe_kw': 1.65, 'i0_percent': 0.2619, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '1.0 MVA 10/0.4 kV': {'sn_mva': 1.0, 'vn_hv_kv': 10.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 1.08, 'pfe_kw': 2.7, 'i0_percent': 0.27, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'},
                '1.6 MVA 10/0.4 kV': {'sn_mva': 1.6, 'vn_hv_kv': 10.0, 'vn_lv_kv': 0.4, 'vk_percent': 6.0, 'vkr_percent': 0.875, 'pfe_kw': 3.25, 'i0_percent': 0.203125, 'shift_degree': 150, 'tap_side': 'hv', 'tap_neutral': 0, 'tap_min': -2, 'tap_max': 2, 'tap_step_percent': 2.5, 'tap_step_degree': 0, 'tap_changer_type': 'Ratio'}
            }
        }
        
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
        
        label = QLabel("请选择一个组件以查看其属性")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
        self.properties_layout.addWidget(label)
        
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
        
        # 标准类型选择（仅对line和transformer）
        if item.component_type in ['line', 'transformer']:
            self.add_standard_type_selector(item)
        
        # 属性组
        props_group = QGroupBox("参数")
        props_layout = QFormLayout(props_group)
        
        # 根据组件类型显示相应的属性
        properties = self.get_component_properties(item.component_type)
        
        for prop_name, prop_info in properties.items():
            current_value = item.properties.get(prop_name, prop_info.get('default', ''))
            widget = self.create_property_widget(prop_name, prop_info, current_value)
            
            if widget:
                props_layout.addRow(f"{prop_info.get('label', prop_name)}:", widget)
                self.property_widgets[prop_name] = widget
        
        self.properties_layout.addWidget(props_group)
        
        # 添加弹性空间
        self.properties_layout.addStretch()
        
    def add_standard_type_selector(self, item):
        """添加标准类型选择器"""
        std_group = QGroupBox("标准类型")
        std_layout = QVBoxLayout(std_group)
        
        # 标准类型下拉框
        type_combo = QComboBox()
        type_combo.addItem("-- 选择标准类型 --", None)
        
        if item.component_type in self.standard_types:
            for std_type in self.standard_types[item.component_type].keys():
                type_combo.addItem(std_type, std_type)
        
        type_combo.currentTextChanged.connect(lambda text: self.on_standard_type_selected(text))
        std_layout.addWidget(type_combo)
        
        self.properties_layout.addWidget(std_group)
        self.property_widgets['standard_type'] = type_combo
        
    def on_standard_type_selected(self, type_name):
        """标准类型选择事件"""
        if not self.current_item or type_name == "-- 选择标准类型 --":
            return
            
        component_type = self.current_item.component_type
        if component_type in self.standard_types and type_name in self.standard_types[component_type]:
            std_params = self.standard_types[component_type][type_name]
            
            # 更新属性值
            for param_name, param_value in std_params.items():
                if param_name in self.property_widgets:
                    widget = self.property_widgets[param_name]
                    if isinstance(widget, QDoubleSpinBox):
                        widget.setValue(param_value)
                    elif isinstance(widget, QSpinBox):
                        widget.setValue(int(param_value))
                    elif isinstance(widget, QLineEdit):
                        widget.setText(str(param_value))
                        
                # 更新组件属性
                if hasattr(self.current_item, 'properties'):
                    self.current_item.properties[param_name] = param_value
                    
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
            for choice in choices:
                widget.addItem(str(choice))
            if current_value in choices:
                widget.setCurrentText(str(current_value))
            widget.currentTextChanged.connect(lambda text: self.on_property_changed(prop_name, text))
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
            
            # 发出信号
            self.property_changed.emit(self.current_item.component_type, prop_name, new_value)
            
    def get_component_properties(self, component_type):
        """获取组件属性定义"""
        # 基于pandapower文档的属性定义
        properties = {
            'bus': {
                'vn_kv': {'type': 'float', 'label': '额定电压 (kV)', 'default': 20.0, 'min': 0.1, 'max': 1000.0},
                'type': {'type': 'choice', 'label': '母线类型', 'choices': ['b', 'n', 'm'], 'default': 'b'},
                'zone': {'type': 'str', 'label': '区域', 'default': ''},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'line': {
                'length_km': {'type': 'float', 'label': '长度 (km)', 'default': 1.0, 'min': 0.001, 'max': 1000.0},
                'r_ohm_per_km': {'type': 'float', 'label': '电阻 (Ω/km)', 'default': 0.1, 'min': 0.0, 'max': 100.0, 'decimals': 4},
                'x_ohm_per_km': {'type': 'float', 'label': '电抗 (Ω/km)', 'default': 0.1, 'min': 0.0, 'max': 100.0, 'decimals': 4},
                'c_nf_per_km': {'type': 'float', 'label': '电容 (nF/km)', 'default': 0.0, 'min': 0.0, 'max': 10000.0, 'decimals': 1},
                'max_i_ka': {'type': 'float', 'label': '最大电流 (kA)', 'default': 1.0, 'min': 0.001, 'max': 100.0, 'decimals': 3},
                'df': {'type': 'float', 'label': '损耗因子', 'default': 1.0, 'min': 0.0, 'max': 2.0, 'decimals': 3},
                'parallel': {'type': 'int', 'label': '并联数', 'default': 1, 'min': 1, 'max': 10},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'transformer': {
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 25.0, 'min': 0.1, 'max': 1000.0},
                'vn_hv_kv': {'type': 'float', 'label': '高压侧额定电压 (kV)', 'default': 110.0, 'min': 0.1, 'max': 1000.0},
                'vn_lv_kv': {'type': 'float', 'label': '低压侧额定电压 (kV)', 'default': 20.0, 'min': 0.1, 'max': 1000.0},
                'vk_percent': {'type': 'float', 'label': '短路电压 (%)', 'default': 12.0, 'min': 0.1, 'max': 50.0},
                'vkr_percent': {'type': 'float', 'label': '短路电阻电压 (%)', 'default': 0.3, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'pfe_kw': {'type': 'float', 'label': '铁损 (kW)', 'default': 14.0, 'min': 0.0, 'max': 10000.0},
                'i0_percent': {'type': 'float', 'label': '空载电流 (%)', 'default': 0.07, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'shift_degree': {'type': 'float', 'label': '相位移 (度)', 'default': 0.0, 'min': -180.0, 'max': 180.0},
                'tap_side': {'type': 'choice', 'label': '调压侧', 'choices': ['hv', 'lv'], 'default': 'hv'},
                'tap_neutral': {'type': 'int', 'label': '中性档位', 'default': 0, 'min': -50, 'max': 50},
                'tap_min': {'type': 'int', 'label': '最小档位', 'default': -9, 'min': -50, 'max': 50},
                'tap_max': {'type': 'int', 'label': '最大档位', 'default': 9, 'min': -50, 'max': 50},
                'tap_step_percent': {'type': 'float', 'label': '档位步长 (%)', 'default': 1.5, 'min': 0.1, 'max': 10.0},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'generator': {
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 10.0, 'min': 0.0, 'max': 10000.0},
                'vm_pu': {'type': 'float', 'label': '电压幅值 (p.u.)', 'default': 1.0, 'min': 0.8, 'max': 1.2, 'decimals': 3},
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 12.0, 'min': 0.1, 'max': 10000.0},
                'min_p_mw': {'type': 'float', 'label': '最小有功 (MW)', 'default': 0.0, 'min': 0.0, 'max': 10000.0},
                'max_p_mw': {'type': 'float', 'label': '最大有功 (MW)', 'default': 100.0, 'min': 0.0, 'max': 10000.0},
                'min_q_mvar': {'type': 'float', 'label': '最小无功 (Mvar)', 'default': -50.0, 'min': -10000.0, 'max': 10000.0},
                'max_q_mvar': {'type': 'float', 'label': '最大无功 (Mvar)', 'default': 50.0, 'min': -10000.0, 'max': 10000.0},
                'scaling': {'type': 'float', 'label': '缩放因子', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'slack': {'type': 'bool', 'label': '平衡节点', 'default': False},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'load': {
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 1.0, 'min': 0.0, 'max': 10000.0},
                'q_mvar': {'type': 'float', 'label': '无功功率 (Mvar)', 'default': 0.0, 'min': -10000.0, 'max': 10000.0},
                'const_z_percent': {'type': 'float', 'label': '恒阻抗比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0},
                'const_i_percent': {'type': 'float', 'label': '恒电流比例 (%)', 'default': 0.0, 'min': 0.0, 'max': 100.0},
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 1.0, 'min': 0.001, 'max': 10000.0},
                'scaling': {'type': 'float', 'label': '缩放因子', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'storage': {
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 0.0, 'min': -10000.0, 'max': 10000.0},
                'max_e_mwh': {'type': 'float', 'label': '最大储能 (MWh)', 'default': 1.0, 'min': 0.001, 'max': 100000.0},
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 1.0, 'min': 0.001, 'max': 10000.0},
                'soc_percent': {'type': 'float', 'label': '荷电状态 (%)', 'default': 50.0, 'min': 0.0, 'max': 100.0},
                'min_p_mw': {'type': 'float', 'label': '最小有功 (MW)', 'default': -100.0, 'min': -10000.0, 'max': 0.0},
                'max_p_mw': {'type': 'float', 'label': '最大有功 (MW)', 'default': 100.0, 'min': 0.0, 'max': 10000.0},
                'q_mvar': {'type': 'float', 'label': '无功功率 (Mvar)', 'default': 0.0, 'min': -10000.0, 'max': 10000.0},
                'scaling': {'type': 'float', 'label': '缩放因子', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            },
            'charger': {
                'p_mw': {'type': 'float', 'label': '有功功率 (MW)', 'default': 0.1, 'min': 0.0, 'max': 1000.0},
                'q_mvar': {'type': 'float', 'label': '无功功率 (Mvar)', 'default': 0.0, 'min': -1000.0, 'max': 1000.0},
                'sn_mva': {'type': 'float', 'label': '额定容量 (MVA)', 'default': 0.1, 'min': 0.001, 'max': 1000.0},
                'scaling': {'type': 'float', 'label': '缩放因子', 'default': 1.0, 'min': 0.0, 'max': 10.0, 'decimals': 3},
                'in_service': {'type': 'bool', 'label': '投入运行', 'default': True}
            }
        }
        
        return properties.get(component_type, {})