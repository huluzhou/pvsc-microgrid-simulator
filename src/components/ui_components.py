#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI组件管理模块
负责管理仿真窗口的UI组件创建和主题更新
"""

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QTreeWidget,
    QLabel,
    QGroupBox,
    QPushButton,
    QCheckBox,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QLineEdit,
    QComboBox,
    QSizePolicy,
    QFormLayout,
    QDoubleSpinBox,
    QSlider,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt


class UIComponentManager:
    """UI组件管理器"""
    
    def __init__(self, parent_window):
        self.parent_window = parent_window
        
    def create_device_tree_panel(self, parent):
        """创建左侧设备树面板"""
        # 创建设备树容器
        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        
        # 标题
        tree_title = QLabel("网络设备")
        tree_title.setFont(QFont("Arial", 12, QFont.Bold))
        tree_layout.addWidget(tree_title)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.parent_window.search_input = QLineEdit()
        self.parent_window.search_input.setPlaceholderText("搜索设备...")
        self.parent_window.search_input.textChanged.connect(self.parent_window.filter_device_tree)
        
        self.parent_window.clear_search_btn = QPushButton("清除")
        self.parent_window.clear_search_btn.clicked.connect(self.parent_window.clear_search)
        self.parent_window.clear_search_btn.setMaximumWidth(60)
        
        search_layout.addWidget(self.parent_window.search_input)
        search_layout.addWidget(self.parent_window.clear_search_btn)
        tree_layout.addLayout(search_layout)
        
        # 设备分类选择
        category_layout = QHBoxLayout()
        self.parent_window.category_combo = QComboBox()
        self.parent_window.category_combo.addItems(["全部设备", "母线", "线路", "变压器", "发电设备", "负载设备", "储能设备", "测量设备"])
        self.parent_window.category_combo.currentTextChanged.connect(self.parent_window.filter_by_category)
        
        self.parent_window.refresh_tree_btn = QPushButton("刷新")
        self.parent_window.refresh_tree_btn.clicked.connect(self.parent_window.refresh_device_tree)
        self.parent_window.refresh_tree_btn.setMaximumWidth(60)
        
        category_layout.addWidget(QLabel("分类:"))
        category_layout.addWidget(self.parent_window.category_combo)
        category_layout.addWidget(self.parent_window.refresh_tree_btn)
        tree_layout.addLayout(category_layout)
        
        # 设备树
        self.parent_window.device_tree = QTreeWidget()
        self.parent_window.device_tree.setHeaderLabels(["设备名称", "类型", "状态"])
        self.parent_window.device_tree.itemClicked.connect(self.parent_window.on_device_selected)
        self.parent_window.device_tree.setAlternatingRowColors(True)
        self.parent_window.device_tree.setSortingEnabled(True)
        
        # 设置列宽
        self.parent_window.device_tree.setColumnWidth(0, 150)
        self.parent_window.device_tree.setColumnWidth(1, 80)
        self.parent_window.device_tree.setColumnWidth(2, 60)
        
        tree_layout.addWidget(self.parent_window.device_tree)
        
        # 设备统计信息
        self.parent_window.device_stats_label = QLabel("设备统计: 加载中...")
        self.parent_window.device_stats_label.setStyleSheet("font-size: 12px; color: #666; padding: 5px;")
        tree_layout.addWidget(self.parent_window.device_stats_label)
        
        # 自动计算控制面板
        self.create_auto_calculation_panel(tree_layout)
        
        parent.setWidget(tree_widget)

    def create_auto_calculation_panel(self, parent_layout):
        """创建自动计算控制面板"""
        auto_group = QGroupBox("仿真控制")
        auto_group.setMinimumHeight(150)  # 增加高度以容纳新按钮
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setContentsMargins(10, 10, 10, 10)  # 设置内边距
        auto_layout.setSpacing(8)  # 设置控件间距
        
        # 计算控制按钮
        control_layout = QHBoxLayout()
        self.parent_window.start_calc_btn = QPushButton("开始仿真")
        self.parent_window.start_calc_btn.setCheckable(True)
        self.parent_window.start_calc_btn.setChecked(False)  # 默认开始计算
        self.parent_window.start_calc_btn.clicked.connect(self.parent_window.toggle_calculation)

        control_layout.addWidget(self.parent_window.start_calc_btn)
        control_layout.addStretch()
        auto_layout.addLayout(control_layout)
        
        # Modbus服务器控制按钮
        modbus_control_layout = QHBoxLayout()
        self.parent_window.power_on_all_btn = QPushButton("上电所有设备")
        self.parent_window.power_on_all_btn.clicked.connect(self.parent_window.power_on_all_devices)
        
        self.parent_window.power_off_all_btn = QPushButton("下电所有设备")
        self.parent_window.power_off_all_btn.clicked.connect(self.parent_window.power_off_all_devices)
        
        modbus_control_layout.addWidget(self.parent_window.power_on_all_btn)
        modbus_control_layout.addWidget(self.parent_window.power_off_all_btn)
        auto_layout.addLayout(modbus_control_layout)
        
        # 计算状态标签
        self.parent_window.calc_status_label = QLabel("仿真状态: 运行中")
        auto_layout.addWidget(self.parent_window.calc_status_label)
        
        # 计算间隔设置
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("仿真间隔:"))
        self.parent_window.calc_interval_spinbox = QSpinBox()
        self.parent_window.calc_interval_spinbox.setRange(1, 60)
        self.parent_window.calc_interval_spinbox.setValue(1)
        self.parent_window.calc_interval_spinbox.setSuffix(" 秒")
        self.parent_window.calc_interval_spinbox.setMaximumWidth(120)  # 设置最大宽度
        self.parent_window.calc_interval_spinbox.valueChanged.connect(self.parent_window.update_auto_calc_timer)
        interval_layout.addWidget(self.parent_window.calc_interval_spinbox)
        interval_layout.addStretch()  # 添加弹性空间
        auto_layout.addLayout(interval_layout)

        parent_layout.addWidget(auto_group)
        
    def create_central_image_area(self, parent):
        """创建中央功率曲线显示区域"""
        # 创建主分割器（上下分隔）
        main_splitter = QSplitter(Qt.Vertical)
        
        # 创建上方图表区域
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        curve_title = QLabel("功率曲线监控")
        curve_title.setFont(QFont("Arial", 12, QFont.Bold))
        chart_layout.addWidget(curve_title)
        
        # 创建功率曲线显示区域 - 使用matplotlib交互式图表
        self.parent_window.figure = Figure(figsize=(8, 4), dpi=100, tight_layout=True)
        self.parent_window.canvas_mpl = FigureCanvas(self.parent_window.figure)
        self.parent_window.canvas_mpl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.parent_window.ax = self.parent_window.figure.add_subplot(111)
        
        # 设置中文字体
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'SimSun', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
        except (OSError, KeyError, ValueError):
            pass
        
        # 初始化图表
        self.parent_window.ax.set_xlabel('时间 (秒)', fontsize=12)
        self.parent_window.ax.set_ylabel('功率 (MW)', fontsize=12)
        self.parent_window.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
        self.parent_window.ax.grid(True, alpha=0.3)
        self.parent_window.ax.set_ylim(bottom=0)
        
        # 创建曲线对象
        self.parent_window.power_line, = self.parent_window.ax.plot([], [], 'b-', linewidth=2, label='有功功率')
        self.parent_window.power_line_q, = self.parent_window.ax.plot([], [], 'r-', linewidth=2, label='无功功率')
        self.parent_window.ax.legend()
        
        # 创建工具栏
        # self.parent_window.toolbar = NavigationToolbar(self.parent_window.canvas_mpl, self.parent_window)
        
        # chart_layout.addWidget(self.parent_window.toolbar)
        chart_layout.addWidget(self.parent_window.canvas_mpl, 1)
        
        # 创建下方监控控制面板容器
        control_container = QWidget()
        control_layout = QVBoxLayout(control_container)
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        # 添加监控控制面板
        self.create_monitor_control_panel(control_layout)
        
        # 将上下区域添加到分割器
        main_splitter.addWidget(chart_widget)
        main_splitter.addWidget(control_container)
        
        # 设置分割器比例（图表占3/4，控制面板占1/4）
        main_splitter.setStretchFactor(0, 3)  # 图表区域
        main_splitter.setStretchFactor(1, 1)  # 控制面板区域
        
        parent.addWidget(main_splitter)
        
            
    def create_sgen_data_panel(self, parent):
        """创建光伏设备数据面板"""
        # 使用data_control_manager创建设备数据生成面板
        sgen_widget = QWidget()
        sgen_layout = QVBoxLayout(sgen_widget)

        sgen_title = QLabel("光伏设备数据")
        sgen_title.setFont(QFont("Arial", 12, QFont.Bold))
        sgen_layout.addWidget(sgen_title)

        current_device_group = QGroupBox("当前设备")
        current_device_layout = QVBoxLayout(current_device_group)

        sgen_current_device_label = QLabel("未选择光伏设备")
        sgen_current_device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        current_device_layout.addWidget(sgen_current_device_label)
        self.parent_window.sgen_current_device_label = sgen_current_device_label
        # 设备数据生成控制
        device_control_layout = QHBoxLayout()
        sgen_enable_generation_checkbox = QCheckBox("启用设备数据生成")
        sgen_enable_generation_checkbox.stateChanged.connect(self.parent_window.data_control_manager.toggle_sgen_data_generation)
        device_control_layout.addWidget(sgen_enable_generation_checkbox)
        current_device_layout.addLayout(device_control_layout)
        self.parent_window.sgen_enable_generation_checkbox = sgen_enable_generation_checkbox
         # 设备上电/下电控制
        power_control_layout = QHBoxLayout()
        sgen_power_on_button = QPushButton("设备上电")
        sgen_power_on_button.clicked.connect(self.parent_window.data_control_manager.on_device_power_on)
        sgen_power_off_button = QPushButton("设备下电")
        sgen_power_off_button.clicked.connect(self.parent_window.data_control_manager.on_device_power_off)
        self.parent_window.sgen_power_on_button = sgen_power_on_button
        self.parent_window.sgen_power_off_button = sgen_power_off_button
        
        power_control_layout.addWidget(sgen_power_on_button)
        power_control_layout.addWidget(sgen_power_off_button)
        current_device_layout.addLayout(power_control_layout)

        sgen_layout.addWidget(current_device_group)

         # 光伏主要结果展示
        sgen_result_group = QGroupBox("光伏发电主要结果")
        sgen_result_layout = QFormLayout(sgen_result_group)
        
        # 有功功率显示
        sgen_active_power_label = QLabel("-- MW")
        sgen_active_power_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        sgen_result_layout.addRow("有功功率:", sgen_active_power_label)
        self.parent_window.sgen_active_power_label = sgen_active_power_label
        # 添加到主布局
        sgen_layout.addWidget(sgen_result_group)

        # 光伏专用参数设置
        sgen_params_group = QGroupBox("光伏发电参数设置")
        sgen_params_layout = QFormLayout(sgen_params_group)
        
        # 变化幅度
        sgen_variation_spinbox = QDoubleSpinBox()
        sgen_variation_spinbox.setRange(0.0, 50.0)
        sgen_variation_spinbox.setValue(0.0)
        sgen_variation_spinbox.setSuffix("%")
        sgen_variation_spinbox.valueChanged.connect(self.parent_window.data_control_manager.on_sgen_variation_changed)
        sgen_params_layout.addRow("功率变化幅度:", sgen_variation_spinbox)
        self.parent_window.sgen_variation_spinbox = sgen_variation_spinbox

        sgen_layout.addWidget(sgen_params_group)
        
        # 光伏手动控制面板
        sgen_manual_group = QGroupBox("光伏发电手动控制面板")
        sgen_manual_layout = QFormLayout(sgen_manual_group)
        self.parent_window.sgen_manual_panel = sgen_manual_group
        
        # 光伏功率控制
        sgen_power_slider = QSlider(Qt.Horizontal)
        sgen_power_slider.setRange(0, 100)  # 0-1MW
        sgen_power_slider.setValue(50)
        sgen_power_slider.setMinimumWidth(100)
        sgen_power_slider.valueChanged.connect(self.parent_window.data_control_manager.on_sgen_power_changed)
        self.parent_window.sgen_power_slider = sgen_power_slider
        
        sgen_power_spinbox = QDoubleSpinBox()
        sgen_power_spinbox.setRange(0.0, 1.0)
        sgen_power_spinbox.setValue(0.5)
        sgen_power_spinbox.setSuffix(" MW")
        sgen_power_spinbox.valueChanged.connect(self.parent_window.data_control_manager.on_sgen_power_spinbox_changed)
        self.parent_window.sgen_power_spinbox = sgen_power_spinbox
        
        sgen_power_layout = QHBoxLayout()
        sgen_power_layout.addWidget(sgen_power_slider)
        sgen_power_layout.addWidget(sgen_power_spinbox)
        sgen_manual_layout.addRow("发电功率:", sgen_power_layout)
        
        # 应用按钮
        sgen_apply_button = QPushButton("应用光伏设置")
        sgen_apply_button.clicked.connect(self.parent_window.data_control_manager.apply_sgen_settings)
        sgen_manual_layout.addRow("", sgen_apply_button)
        self.parent_window.sgen_apply_button = sgen_apply_button
        
        sgen_layout.addWidget(sgen_manual_group)
        
        sgen_layout.addStretch()


        parent.setWidget(sgen_widget)
        
    def create_load_data_panel(self, parent):
        """创建负载设备数据面板"""
        load_widget = QWidget()
        load_layout = QVBoxLayout(load_widget)

        load_title = QLabel("负载设备数据")
        load_title.setFont(QFont("Arial", 12, QFont.Bold))
        load_layout.addWidget(load_title)

        current_device_group = QGroupBox("当前设备")
        current_device_layout = QVBoxLayout(current_device_group)

        load_current_device_label = QLabel("未选择负载设备")
        load_current_device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        current_device_layout.addWidget(load_current_device_label)
        self.parent_window.load_current_device_label = load_current_device_label

        # 设备数据生成控制
        device_control_layout = QHBoxLayout()
        load_enable_generation_checkbox = QCheckBox("启用设备数据生成")
        load_enable_generation_checkbox.stateChanged.connect(self.parent_window.data_control_manager.toggle_load_data_generation)
        device_control_layout.addWidget(load_enable_generation_checkbox)
        self.parent_window.load_enable_generation_checkbox = load_enable_generation_checkbox
        current_device_layout.addLayout(device_control_layout)

        # 设备上电/下电控制
        power_control_layout = QHBoxLayout()
        load_power_on_button = QPushButton("设备上电")
        load_power_on_button.clicked.connect(self.parent_window.data_control_manager.on_device_power_on)
        load_power_off_button = QPushButton("设备下电")
        load_power_off_button.clicked.connect(self.parent_window.data_control_manager.on_device_power_off)
        self.parent_window.load_power_on_button = load_power_on_button
        self.parent_window.load_power_off_button = load_power_off_button
        
        
        power_control_layout.addWidget(load_power_on_button)
        power_control_layout.addWidget(load_power_off_button)
        current_device_layout.addLayout(power_control_layout)

        load_layout.addWidget(current_device_group)

        # 负载主要结果展示
        load_result_group = QGroupBox("负载用电主要结果")
        load_result_layout = QFormLayout(load_result_group)
        
        # 有功功率显示
        load_active_power_label = QLabel("-- MW")
        load_active_power_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        load_result_layout.addRow("有功功率:", load_active_power_label)
        self.parent_window.load_active_power_label = load_active_power_label
        
        # 添加到主布局
        load_layout.addWidget(load_result_group)

        # 负载专用参数设置
        load_params_group = QGroupBox("负载用电参数设置")
        load_params_layout = QFormLayout(load_params_group)
        
        # 变化幅度
        load_variation_spinbox = QDoubleSpinBox()
        load_variation_spinbox.setRange(0.0, 50.0)
        load_variation_spinbox.setValue(15.0)
        load_variation_spinbox.setSuffix("%")
        load_variation_spinbox.valueChanged.connect(self.parent_window.data_control_manager.on_variation_changed)
        load_params_layout.addRow("功率变化幅度:", load_variation_spinbox)
        self.parent_window.load_variation_spinbox = load_variation_spinbox
        # 负载类型选择
        load_type_combo = QComboBox()
        load_type_combo.addItems(["住宅负载", "商业负载", "工业负载"])
        load_type_combo.currentTextChanged.connect(self.parent_window.data_control_manager.on_load_type_changed)
        load_params_layout.addRow("负载类型:", load_type_combo)
        self.parent_window.load_type_combo = load_type_combo
        
        load_layout.addWidget(load_params_group)
        
        # 负载手动控制面板
        load_manual_group = QGroupBox("负载用电手动控制面板")
        load_manual_layout = QFormLayout(load_manual_group)
        self.parent_window.load_manual_panel = load_manual_group

        # 负载功率控制
        load_power_slider = QSlider(Qt.Horizontal)
        load_power_slider.setRange(0, 100)  # 0-1MW
        load_power_slider.setValue(50)
        load_power_slider.setMinimumWidth(100)
        load_power_slider.valueChanged.connect(self.parent_window.data_control_manager.on_load_power_changed)
        self.parent_window.load_power_slider = load_power_slider
        
        load_power_spinbox = QDoubleSpinBox()
        load_power_spinbox.setRange(0.0, 1.0)
        load_power_spinbox.setValue(0.5)
        load_power_spinbox.setSuffix(" MW")
        load_power_spinbox.valueChanged.connect(self.parent_window.data_control_manager.on_load_power_spinbox_changed)
        self.parent_window.load_power_spinbox = load_power_spinbox
        
        load_power_layout = QHBoxLayout()
        load_power_layout.addWidget(load_power_slider)
        load_power_layout.addWidget(load_power_spinbox)
        load_manual_layout.addRow("有功功率:", load_power_layout)
        
        # 负载无功功率控制
        load_reactive_power_slider = QSlider(Qt.Horizontal)
        load_reactive_power_slider.setRange(0, 50)  # 0-0.5MVar
        load_reactive_power_slider.setValue(25)
        load_reactive_power_slider.setMinimumWidth(100)
        load_reactive_power_slider.valueChanged.connect(self.parent_window.data_control_manager.on_load_reactive_power_changed)
        self.parent_window.load_reactive_power_slider = load_reactive_power_slider
        
        load_reactive_power_spinbox = QDoubleSpinBox()
        load_reactive_power_spinbox.setRange(0.0, 0.5)
        load_reactive_power_spinbox.setValue(0.25)
        load_reactive_power_spinbox.setSuffix(" MVar")
        self.parent_window.load_reactive_power_spinbox = load_reactive_power_spinbox
        load_reactive_power_spinbox.valueChanged.connect(self.parent_window.data_control_manager.on_load_reactive_power_spinbox_changed)
        
        load_reactive_power_layout = QHBoxLayout()
        load_reactive_power_layout.addWidget(load_reactive_power_slider)
        load_reactive_power_layout.addWidget(load_reactive_power_spinbox)
        load_manual_layout.addRow("无功功率:", load_reactive_power_layout)
        
        # 应用按钮
        load_apply_button = QPushButton("应用负载设置")
        load_apply_button.clicked.connect(self.parent_window.data_control_manager.apply_load_settings)
        load_manual_layout.addRow("", load_apply_button)
        self.parent_window.load_apply_button = load_apply_button
        
        load_layout.addWidget(load_manual_group)
        
        load_layout.addStretch()

        parent.setWidget(load_widget)
        
    def create_storage_data_panel(self, parent):
        """创建储能设备数据面板"""
        storage_widget = QWidget()
        storage_layout = QVBoxLayout(storage_widget)

        storage_title = QLabel("储能设备数据")
        storage_title.setFont(QFont("Arial", 12, QFont.Bold))
        storage_layout.addWidget(storage_title)

        current_device_group = QGroupBox("当前设备")
        current_device_layout = QVBoxLayout(current_device_group)

        storage_current_device_label = QLabel("未选择储能设备")
        storage_current_device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        current_device_layout.addWidget(storage_current_device_label)
        self.parent_window.storage_current_device_label = storage_current_device_label
        
        # 设备上电/下电控制
        power_control_layout = QHBoxLayout()
        storage_power_on_button = QPushButton("设备上电")
        storage_power_on_button.clicked.connect(self.parent_window.data_control_manager.on_device_power_on)
        storage_power_off_button = QPushButton("设备下电")
        storage_power_off_button.clicked.connect(self.parent_window.data_control_manager.on_device_power_off)
        self.parent_window.storage_power_on_button = storage_power_on_button
        self.parent_window.storage_power_off_button = storage_power_off_button
        
        # 设备并网/离网控制
        storage_grid_connection_layout = QVBoxLayout()
        storage_grid_connection_label = QLabel("并网状态：")
        storage_grid_connection_label.setStyleSheet("font-weight: bold;")
        storage_grid_connection_status = QLabel("--")
        storage_grid_connection_status.setStyleSheet("font-weight: bold; color: #FFC107;")
        
        
        storage_grid_connection_layout.addWidget(storage_grid_connection_label)
        storage_grid_connection_layout.addWidget(storage_grid_connection_status)
        
        # 存储引用到parent_window
        self.parent_window.storage_grid_connection_status = storage_grid_connection_status
        self.parent_window.storage_connection_label = storage_grid_connection_label
        
        power_control_layout.addWidget(storage_power_on_button)
        power_control_layout.addWidget(storage_power_off_button)
        current_device_layout.addLayout(power_control_layout)
        current_device_layout.addLayout(storage_grid_connection_layout)

        storage_layout.addWidget(current_device_group)

        # 储能主要结果展示
        storage_result_group = QGroupBox("储能运行主要结果")
        storage_result_layout = QFormLayout(storage_result_group)
        
        # 有功功率显示
        storage_active_power_label = QLabel("-- MW")
        storage_active_power_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        storage_result_layout.addRow("有功功率:", storage_active_power_label)
        self.parent_window.storage_active_power_label = storage_active_power_label

        # 荷电状态显示
        storage_soc_label = QLabel("--%")
        storage_soc_label.setStyleSheet("font-weight: bold; color: #9C27B0;")
        storage_result_layout.addRow("荷电状态:", storage_soc_label)
        self.parent_window.storage_soc_label = storage_soc_label
        
        # 储能工作状态显示
        storage_work_status_label = QLabel("--")
        storage_work_status_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        storage_result_layout.addRow("工作状态:", storage_work_status_label)
        self.parent_window.storage_work_status_label = storage_work_status_label
        
        # 添加到主布局
        storage_layout.addWidget(storage_result_group)

        # 储能手动控制
        storage_mode_group = QGroupBox("控制模式切换")
        storage_mode_layout = QVBoxLayout(storage_mode_group)

        # 控制模式切换
        control_mode_layout = QHBoxLayout()
        control_mode_label = QLabel("控制模式：")
        
        # 使用复选框代替单选按钮，选中表示启用远程控制
        storage_enable_remote = QCheckBox("启用远程控制")
        storage_enable_remote.setChecked(True)  # 默认启用远程控制
        storage_enable_remote.stateChanged.connect(self.parent_window.data_control_manager.on_storage_control_mode_changed)
        self.parent_window.storage_enable_remote = storage_enable_remote

        control_mode_layout.addWidget(control_mode_label)
        control_mode_layout.addWidget(storage_enable_remote)
        control_mode_layout.addStretch()
        storage_mode_layout.addLayout(control_mode_layout)
        
        storage_layout.addWidget(storage_mode_group)
        
        # 手动控制面板
        storage_manual_group = QGroupBox("储能手动控制")
        storage_manual_panel_layout = QFormLayout(storage_manual_group)
        
        # 设置storage_manual_panel属性引用，确保控制模式切换功能正常工作
        self.parent_window.storage_manual_panel = storage_manual_group
        
        # 有功功率控制（正值为放电，负值为充电）
        storage_power_slider = QSlider(Qt.Horizontal)
        storage_power_slider.setRange(-100, 100)  # 滑块范围：-100.0到100.0MW（乘以10）
        storage_power_slider.setValue(0)
        storage_power_slider.setMinimumWidth(100)
        storage_power_slider.valueChanged.connect(self.parent_window.data_control_manager.on_storage_power_changed)
        self.parent_window.storage_power_slider = storage_power_slider
        
        storage_power_spinbox = QDoubleSpinBox()
        storage_power_spinbox.setRange(-1.0, 1.0)
        storage_power_spinbox.setValue(0.0)
        storage_power_spinbox.setSuffix(" MW")
        storage_power_spinbox.valueChanged.connect(self.parent_window.data_control_manager.on_storage_power_spinbox_changed)
        self.parent_window.storage_power_spinbox = storage_power_spinbox
        
        
        storage_power_layout = QHBoxLayout()
        storage_power_layout.addWidget(storage_power_slider)
        storage_power_layout.addWidget(storage_power_spinbox)
        storage_manual_panel_layout.addRow("功率控制:", storage_power_layout)
        
        # 功率说明标签
        power_info_label = QLabel("正值充电，负值放电")
        power_info_label.setStyleSheet("color: #666; font-size: 12px;")
        storage_manual_panel_layout.addRow("", power_info_label)
        
        # 应用按钮
        storage_apply_button = QPushButton("应用储能设置")
        storage_apply_button.clicked.connect(self.parent_window.data_control_manager.apply_storage_settings)
        storage_manual_panel_layout.addRow("", storage_apply_button)
        
        storage_layout.addWidget(storage_manual_group)
        storage_layout.addStretch()
        
        parent.setWidget(storage_widget)
        
    def create_switch_data_panel(self, parent):
        """创建开关设备数据面板"""
        switch_widget = QWidget()
        switch_layout = QVBoxLayout(switch_widget)

        switch_title = QLabel("开关设备数据")
        switch_title.setFont(QFont("Arial", 12, QFont.Bold))
        switch_layout.addWidget(switch_title)

        current_device_group = QGroupBox("当前设备")
        current_device_layout = QVBoxLayout(current_device_group)

        switch_current_device_label = QLabel("未选择开关设备")
        switch_current_device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        current_device_layout.addWidget(switch_current_device_label)
        self.parent_window.switch_current_device_label = switch_current_device_label

        # 开关状态显示
        switch_status_label_layout = QHBoxLayout()
        switch_status_label = QLabel("开关状态：")
        switch_status_value = QLabel("合闸")
        switch_status_value.setStyleSheet("font-weight: bold; color: #4CAF50;")
        self.parent_window.switch_status_value = switch_status_value
        
        switch_status_label_layout.addWidget(switch_status_label)
        switch_status_label_layout.addWidget(switch_status_value)
        switch_status_label_layout.addStretch()
        current_device_layout.addLayout(switch_status_label_layout)
        
        # 合闸/分闸控制
        switch_control_layout = QHBoxLayout()
        switch_close_button = QPushButton("合闸")
        switch_close_button.clicked.connect(self.parent_window.on_switch_close)
        switch_open_button = QPushButton("分闸")
        switch_open_button.clicked.connect(self.parent_window.on_switch_open)
        self.parent_window.switch_close_button = switch_close_button
        self.parent_window.switch_open_button = switch_open_button
        
        switch_control_layout.addWidget(switch_close_button)
        switch_control_layout.addWidget(switch_open_button)
        switch_control_layout.addStretch()
        current_device_layout.addLayout(switch_control_layout)
        
        switch_layout.addWidget(current_device_group)
        
        switch_layout.addStretch()
        
        # 设置面板为parent的中央部件
        parent.setWidget(switch_widget)
    
    def create_charger_data_panel(self, parent):
        """创建充电桩设备数据面板"""
        charger_widget = QWidget()
        charger_layout = QVBoxLayout(charger_widget)

        charger_title = QLabel("充电桩设备数据")
        charger_title.setFont(QFont("Arial", 12, QFont.Bold))
        charger_layout.addWidget(charger_title)

        current_device_group = QGroupBox("当前设备")
        current_device_layout = QVBoxLayout(current_device_group)

        charger_current_device_label = QLabel("未选择充电桩设备")
        charger_current_device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        current_device_layout.addWidget(charger_current_device_label)
        self.parent_window.charger_current_device_label = charger_current_device_label

        # 设备上电/下电控制
        power_control_layout = QHBoxLayout()
        charger_power_on_button = QPushButton("设备上电")
        charger_power_on_button.clicked.connect(self.parent_window.data_control_manager.on_device_power_on)
        charger_power_off_button = QPushButton("设备下电")
        charger_power_off_button.clicked.connect(self.parent_window.data_control_manager.on_device_power_off)
        self.parent_window.charger_power_on_button = charger_power_on_button
        self.parent_window.charger_power_off_button = charger_power_off_button
        
        
        power_control_layout.addWidget(charger_power_on_button)
        power_control_layout.addWidget(charger_power_off_button)
        current_device_layout.addLayout(power_control_layout)

        charger_layout.addWidget(current_device_group)

        # 充电桩主要结果展示
        charger_result_group = QGroupBox("充电桩运行主要结果")
        charger_result_layout = QFormLayout(charger_result_group)
        
        # 有功功率显示
        charger_active_power_label = QLabel("-- kW")
        charger_active_power_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        charger_result_layout.addRow("有功功率:", charger_active_power_label)
        self.parent_window.charger_active_power_label = charger_active_power_label 
        
        
        # 添加到主布局
        charger_layout.addWidget(charger_result_group)

        # 充电桩专用参数设置
        charger_params_group = QGroupBox("充电桩运行参数设置")
        charger_params_layout = QFormLayout(charger_params_group)
        
        # 需求功率设置
        charger_required_power_slider = QSlider(Qt.Horizontal)
        charger_required_power_slider.setRange(0, 200)
        charger_required_power_slider.setValue(50)
        charger_required_power_slider.setMinimumWidth(100)
        charger_required_power_slider.valueChanged.connect(self.parent_window.data_control_manager.on_charger_required_power_changed)
        
        charger_required_power_spinbox = QDoubleSpinBox()
        charger_required_power_spinbox.setRange(0.0, 200.0)
        charger_required_power_spinbox.setValue(50.0)
        charger_required_power_spinbox.setSuffix(" kW")
        charger_required_power_spinbox.valueChanged.connect(self.parent_window.data_control_manager.on_charger_required_power_spinbox_changed)
        self.parent_window.charger_required_power_slider = charger_required_power_slider
        self.parent_window.charger_required_power_spinbox = charger_required_power_spinbox
        
        
        charger_power_layout = QHBoxLayout()
        charger_power_layout.addWidget(charger_required_power_slider)
        charger_power_layout.addWidget(charger_required_power_spinbox)
        charger_params_layout.addRow("需求功率:", charger_power_layout)
        
        # 功率限制显示
        charger_power_limit_label = QLabel("-- kW")
        charger_power_limit_label.setStyleSheet("background-color: #f0f0f0; color: #333;")
        charger_params_layout.addRow("功率限制:", charger_power_limit_label)
        self.parent_window.charger_power_limit_label = charger_power_limit_label 
        # 应用按钮
        charger_apply_button = QPushButton("应用充电桩设置")
        charger_apply_button.clicked.connect(self.parent_window.data_control_manager.apply_charger_settings)
        charger_params_layout.addRow("", charger_apply_button)
        
        charger_layout.addWidget(charger_params_group)
        
        charger_layout.addStretch()

        parent.setWidget(charger_widget)

    def create_monitor_control_panel(self, parent_layout):
        """创建监控控制面板"""
        # 创建监控控制组
        monitor_group = QGroupBox("功率曲线监控")
        monitor_layout = QVBoxLayout(monitor_group)
        
        # 当前设备监控开关
        self.parent_window.current_device_monitor = QCheckBox("监控当前设备")
        self.parent_window.current_device_monitor.stateChanged.connect(self.parent_window.power_monitor.toggle_current_device_monitor)
        monitor_layout.addWidget(self.parent_window.current_device_monitor)
        
        # 已监控设备列表
        self.parent_window.monitored_devices_list = QTreeWidget()
        self.parent_window.monitored_devices_list.setHeaderLabels(["设备", "类型", "状态"])
        self.parent_window.monitored_devices_list.setMaximumHeight(150)
        self.parent_window.monitored_devices_list.itemChanged.connect(self.parent_window.power_monitor.on_monitored_device_toggled)
        monitor_layout.addWidget(self.parent_window.monitored_devices_list)
        
        # 清除所有监控按钮
        clear_btn = QPushButton("清除所有监控")
        clear_btn.clicked.connect(self.parent_window.power_monitor.clear_all_monitors)
        monitor_layout.addWidget(clear_btn)
        
        parent_layout.addWidget(monitor_group)