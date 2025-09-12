#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI组件管理模块
负责管理仿真窗口的UI组件创建和主题更新
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QTreeWidget, QLabel, QGroupBox, QPushButton, 
    QCheckBox, QSpinBox, QTabWidget, QTableWidget, QLineEdit, QComboBox, QSizePolicy
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
        
        parent.addWidget(tree_widget)

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
        
    def create_simulation_results_panel(self, parent):
        """创建右侧仿真结果面板"""
        # 创建结果面板容器
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        
        # 标题
        results_title = QLabel("仿真结果")
        results_title.setFont(QFont("Arial", 12, QFont.Bold))
        results_layout.addWidget(results_title)
        
        # 创建选项卡
        self.parent_window.results_tabs = QTabWidget()
        
        # 组件详情选项卡
        self.parent_window.component_details_tab = QWidget()
        self.create_component_details_tab()
        self.parent_window.results_tabs.addTab(self.parent_window.component_details_tab, "组件详情")
        
        # 为不同设备类型创建独立的数据生成控制选项卡
        self.parent_window.sgen_data_tab = QWidget()  # 光伏设备选项卡
        self.parent_window.load_data_tab = QWidget()  # 负载设备选项卡
        self.parent_window.storage_data_tab = QWidget()  # 储能设备选项卡
        
        results_layout.addWidget(self.parent_window.results_tabs)
        
        parent.addWidget(results_widget)
        
    def create_component_details_tab(self):
        """创建组件详情选项卡"""
        layout = QVBoxLayout(self.parent_window.component_details_tab)
        
        # 组件参数表格
        self.parent_window.component_params_table = QTableWidget()
        self.parent_window.component_params_table.setColumnCount(2)
        self.parent_window.component_params_table.setHorizontalHeaderLabels(["参数", "值"])
        self.parent_window.component_params_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.parent_window.component_params_table)
        
        
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