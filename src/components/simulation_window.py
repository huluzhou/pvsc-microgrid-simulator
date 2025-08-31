#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
仿真界面窗口
"""

import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QScrollArea, QTreeWidget, QTreeWidgetItem, QTextEdit, QLabel,
    QGroupBox, QPushButton, QMessageBox, QProgressBar, QCheckBox, QSpinBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QDialog,
    QSizePolicy, QApplication, QFormLayout, QDoubleSpinBox, QRadioButton, QSlider
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QFont, QBrush, QColor, QPalette
from PySide6.QtCore import QRectF
import pandapower as pp
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from collections import deque
import threading
import time
from datetime import datetime
from .data_generators import DataGeneratorManager



class SimulationWindow(QMainWindow):
    """仿真界面窗口"""
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.parent_window = parent
        self.network_model = canvas.network_model if hasattr(canvas, 'network_model') else None
        
        # 自动潮流计算相关属性
        self.auto_calc_timer = QTimer()
        self.auto_calc_timer.timeout.connect(self.auto_power_flow_calculation)
        self.is_auto_calculating = False
        self.power_history = {}  # 存储多个设备的功率历史数据 {device_key: deque}
        self.selected_device_id = None
        self.selected_device_type = None
        self.monitored_devices = set()  # 存储要监控的设备集合
        self.generated_devices = set()
        self.device_colors = {}  # 存储设备对应的颜色
        self.color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                             '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        # 数据生成器管理
        self.data_generator_manager = DataGeneratorManager()
        self.current_load_index = 0
        
        # 当前显示的组件信息（用于自动更新组件参数表格）
        self.current_component_type = None
        self.current_component_idx = None
        
        self.init_ui()
        self.load_network_data()
        
        # 应用当前主题
        self.update_theme_colors()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("仿真模式 - PandaPower 仿真工具")
        self.setMinimumSize(1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 创建左侧设备树面板
        self.create_device_tree_panel(splitter)
        
        # 创建中央功率曲线区域
        self.create_central_image_area(splitter)
        
        # 创建右侧仿真结果面板
        self.create_simulation_results_panel(splitter)
        
        # 设置分割器比例，让中央区域有更大的权重
        splitter.setSizes([250, 800, 300])
        
        # 设置分割器拉伸策略，让中央区域可以扩展
        splitter.setStretchFactor(0, 0)   # 左侧不自动扩展
        splitter.setStretchFactor(1, 1)   # 中央区域自动扩展
        splitter.setStretchFactor(2, 0)   # 右侧不自动扩展
        
        # 创建状态栏
        self.statusBar().showMessage("仿真模式已就绪")
        
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
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索设备...")
        self.search_input.textChanged.connect(self.filter_device_tree)
        
        self.clear_search_btn = QPushButton("清除")
        self.clear_search_btn.clicked.connect(self.clear_search)
        self.clear_search_btn.setMaximumWidth(60)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.clear_search_btn)
        tree_layout.addLayout(search_layout)
        
        # 设备分类选择
        category_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItems(["全部设备", "母线", "线路", "变压器", "发电设备", "负载设备", "储能设备"])
        self.category_combo.currentTextChanged.connect(self.filter_by_category)
        
        self.refresh_tree_btn = QPushButton("刷新")
        self.refresh_tree_btn.clicked.connect(self.refresh_device_tree)
        self.refresh_tree_btn.setMaximumWidth(60)
        
        category_layout.addWidget(QLabel("分类:"))
        category_layout.addWidget(self.category_combo)
        category_layout.addWidget(self.refresh_tree_btn)
        tree_layout.addLayout(category_layout)
        
        # 设备树
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabels(["设备名称", "类型", "状态"])
        self.device_tree.itemClicked.connect(self.on_device_selected)
        self.device_tree.setAlternatingRowColors(True)
        self.device_tree.setSortingEnabled(True)
        
        # 设置列宽
        self.device_tree.setColumnWidth(0, 150)
        self.device_tree.setColumnWidth(1, 80)
        self.device_tree.setColumnWidth(2, 60)
        
        tree_layout.addWidget(self.device_tree)
        
        # 设备统计信息
        self.device_stats_label = QLabel("设备统计: 加载中...")
        self.device_stats_label.setStyleSheet("font-size: 12px; color: #666; padding: 5px;")
        tree_layout.addWidget(self.device_stats_label)
        
        # 自动计算控制面板
        auto_group = QGroupBox("自动计算")
        auto_group.setMinimumHeight(100)  # 设置最小高度确保显示完整
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setContentsMargins(10, 10, 10, 10)  # 设置内边距
        auto_layout.setSpacing(8)  # 设置控件间距
        
        # 自动计算开关
        auto_calc_layout = QHBoxLayout()
        auto_calc_layout.setContentsMargins(0, 0, 0, 0)
        auto_calc_label = QLabel("自动计算:")
        auto_calc_label.setMinimumWidth(60)  # 设置标签最小宽度
        auto_calc_layout.addWidget(auto_calc_label)
        self.auto_calc_checkbox = QCheckBox()
        self.auto_calc_checkbox.stateChanged.connect(self.toggle_auto_calculation)
        auto_calc_layout.addWidget(self.auto_calc_checkbox)
        auto_calc_layout.addStretch()  # 添加弹性空间
        auto_layout.addLayout(auto_calc_layout)
        
        # 计算间隔
        interval_layout = QHBoxLayout()
        interval_layout.setContentsMargins(0, 0, 0, 0)
        interval_label = QLabel("间隔(秒):")
        interval_label.setMinimumWidth(60)  # 设置标签最小宽度
        interval_layout.addWidget(interval_label)
        self.calc_interval_spinbox = QSpinBox()
        self.calc_interval_spinbox.setRange(1, 60)
        self.calc_interval_spinbox.setValue(5)
        self.calc_interval_spinbox.setMinimumWidth(80)  # 增加宽度确保箭头显示
        self.calc_interval_spinbox.setMaximumWidth(120)  # 设置最大宽度
        interval_layout.addWidget(self.calc_interval_spinbox)
        interval_layout.addStretch()  # 添加弹性空间
        auto_layout.addLayout(interval_layout)
        
        tree_layout.addWidget(auto_group)
        
        parent.addWidget(tree_widget)
        
    def create_central_image_area(self, parent):
        """创建中央功率曲线显示区域"""
        # 创建功率曲线容器
        curve_widget = QWidget()
        curve_layout = QVBoxLayout(curve_widget)
        curve_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        curve_title = QLabel("功率曲线监控")
        curve_title.setFont(QFont("Arial", 12, QFont.Bold))
        curve_layout.addWidget(curve_title)
        
        # 创建功率曲线显示区域 - 使用matplotlib交互式图表
        # 使用更灵活的尺寸设置，让Figure自适应容器大小
        self.figure = Figure(figsize=(8, 5), dpi=100, tight_layout=True)
        self.canvas_mpl = FigureCanvas(self.figure)
        self.canvas_mpl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = self.figure.add_subplot(111)
        
        # 设置中文字体
        try:
            # 尝试设置支持中文的字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'SimSun', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        except:
            pass
        
        # 初始化图表
        self.ax.set_xlabel('时间 (秒)', fontsize=12)
        self.ax.set_ylabel('功率 (MW)', fontsize=12)
        self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_ylim(bottom=0)
        
        # 创建曲线对象
        self.power_line, = self.ax.plot([], [], 'b-', linewidth=2, label='有功功率')
        self.power_line_q, = self.ax.plot([], [], 'r-', linewidth=2, label='无功功率')
        self.ax.legend()
        
        # 创建工具栏
        from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
        self.toolbar = NavigationToolbar(self.canvas_mpl, self)
        
        curve_layout.addWidget(self.toolbar)
        curve_layout.addWidget(self.canvas_mpl, 1)  # 设置stretch因子为1，让图表区域扩展
        
        parent.addWidget(curve_widget)
        
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
        self.results_tabs = QTabWidget()
        
        # 组件详情选项卡
        self.component_details_tab = QWidget()
        self.create_component_details_tab()
        self.results_tabs.addTab(self.component_details_tab, "组件详情")
        
        # 为不同设备类型创建独立的数据生成控制选项卡
        self.sgen_data_tab = QWidget()  # 光伏设备选项卡
        self.load_data_tab = QWidget()  # 负载设备选项卡
        self.storage_data_tab = QWidget()  # 储能设备选项卡
        
        # 创建各设备类型的选项卡内容
        self.create_sgen_data_generation_tab()
        self.create_load_data_generation_tab()
        self.create_storage_data_generation_tab()
        
        # 注意：不在这里添加选项卡，而是在show_component_details中根据设备类型动态添加
        
        results_layout.addWidget(self.results_tabs)
        
        parent.addWidget(results_widget)
        
    def create_monitor_control_panel(self, parent_layout):
        """创建监控控制面板"""
        # 创建监控控制组
        monitor_group = QGroupBox("功率曲线监控")
        monitor_layout = QVBoxLayout(monitor_group)
        
        # 当前设备监控开关
        self.current_device_monitor = QCheckBox("监控当前设备")
        self.current_device_monitor.stateChanged.connect(self.toggle_current_device_monitor)
        monitor_layout.addWidget(self.current_device_monitor)
        
        # 已监控设备列表
        self.monitored_devices_list = QTreeWidget()
        self.monitored_devices_list.setHeaderLabels(["设备", "类型", "状态"])
        self.monitored_devices_list.setMaximumHeight(150)
        self.monitored_devices_list.itemChanged.connect(self.on_monitored_device_toggled)
        monitor_layout.addWidget(self.monitored_devices_list)
        
        # 清除所有监控按钮
        clear_btn = QPushButton("清除所有监控")
        clear_btn.clicked.connect(self.clear_all_monitors)
        monitor_layout.addWidget(clear_btn)
        
        parent_layout.addWidget(monitor_group)
        

        
    def create_component_details_tab(self):
        """创建组件详情选项卡"""
        layout = QVBoxLayout(self.component_details_tab)
        
        # 组件参数表格
        self.component_params_table = QTableWidget()
        self.component_params_table.setColumnCount(2)
        self.component_params_table.setHorizontalHeaderLabels(["参数", "值"])
        self.component_params_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.component_params_table)
        
        # 创建控制面板容器
        control_container = QWidget()
        control_layout = QVBoxLayout(control_container)
        
        # 功率曲线监控控制面板
        self.create_monitor_control_panel(control_layout)
        
        layout.addWidget(control_container)
        
    def create_data_generation_tab(self):
        """创建数据生成控制选项卡"""
        layout = QVBoxLayout(self.data_generation_tab)
        
        # 当前选择设备信息
        current_device_group = QGroupBox("当前选择设备")
        current_device_layout = QVBoxLayout(current_device_group)
        
        self.current_device_label = QLabel("未选择设备")
        self.current_device_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        current_device_layout.addWidget(self.current_device_label)
        
        # 设备数据生成控制
        device_control_layout = QHBoxLayout()
        self.enable_device_generation_checkbox = QCheckBox("启用当前设备数据生成")
        self.enable_device_generation_checkbox.stateChanged.connect(self.toggle_device_data_generation)
        device_control_layout.addWidget(self.enable_device_generation_checkbox)
        
        current_device_layout.addLayout(device_control_layout)
        layout.addWidget(current_device_group)
        
        # 数据生成参数设置
        params_group = QGroupBox("生成参数设置")
        params_layout = QFormLayout(params_group)
        
        # 变化幅度
        self.variation_spinbox = QDoubleSpinBox()
        self.variation_spinbox.setRange(0.0, 50.0)
        self.variation_spinbox.setValue(10.0)
        self.variation_spinbox.setSuffix("%")
        params_layout.addRow("变化幅度:", self.variation_spinbox)
        
        # 季节因子
        self.season_combo = QComboBox()
        self.season_combo.addItems(["春季", "夏季", "秋季", "冬季"])
        self.season_combo.setCurrentText("夏季")
        params_layout.addRow("季节因子:", self.season_combo)
        
        # 天气类型（仅对光伏有效）
        self.weather_combo = QComboBox()
        self.weather_combo.addItems(["晴天", "多云", "阴天"])
        self.weather_combo.setCurrentText("晴天")
        params_layout.addRow("天气类型:", self.weather_combo)
        
        layout.addWidget(params_group)
        
        # 手动数据生成控制
        manual_control_group = QGroupBox("手动数据生成控制")
        manual_control_layout = QVBoxLayout(manual_control_group)
        
        # 数据生成模式选择
        mode_layout = QHBoxLayout()
        self.auto_mode_radio = QRadioButton("自动生成")
        self.manual_mode_radio = QRadioButton("手动控制")
        self.auto_mode_radio.setChecked(True)
        self.auto_mode_radio.toggled.connect(self.on_generation_mode_changed)
        self.manual_mode_radio.toggled.connect(self.on_generation_mode_changed)
        mode_layout.addWidget(self.auto_mode_radio)
        mode_layout.addWidget(self.manual_mode_radio)
        manual_control_layout.addLayout(mode_layout)
        
        # 手动控制面板（初始隐藏）
        self.manual_control_panel = QWidget()
        manual_panel_layout = QFormLayout(self.manual_control_panel)
        
        # 有功功率控制
        self.power_slider = QSlider(Qt.Horizontal)
        self.power_slider.setRange(0, 200)  # 0-200% 范围
        self.power_slider.setValue(100)
        self.power_slider.setMinimumWidth(300)  # 设置最小宽度
        self.power_slider.valueChanged.connect(self.on_manual_power_changed)
        
        self.power_spinbox = QDoubleSpinBox()
        self.power_spinbox.setRange(0.0, 100.0)  # 增加范围
        self.power_spinbox.setValue(1.0)
        self.power_spinbox.setSuffix(" MW")
        self.power_spinbox.setDecimals(3)  # 增加精度
        self.power_spinbox.valueChanged.connect(self.on_manual_power_spinbox_changed)
        
        power_control_layout = QHBoxLayout()
        power_control_layout.addWidget(self.power_slider)
        power_control_layout.addWidget(self.power_spinbox)
        manual_panel_layout.addRow("有功功率:", power_control_layout)
        
        # 无功功率控制（仅对负载有效）
        self.reactive_power_slider = QSlider(Qt.Horizontal)
        self.reactive_power_slider.setRange(0, 200)
        self.reactive_power_slider.setValue(100)
        self.reactive_power_slider.setMinimumWidth(300)  # 设置最小宽度
        self.reactive_power_slider.valueChanged.connect(self.on_manual_reactive_power_changed)
        
        self.reactive_power_spinbox = QDoubleSpinBox()
        self.reactive_power_spinbox.setRange(0.0, 50.0)  # 增加范围
        self.reactive_power_spinbox.setValue(0.5)
        self.reactive_power_spinbox.setSuffix(" MVar")
        self.reactive_power_spinbox.setDecimals(3)  # 增加精度
        self.reactive_power_spinbox.valueChanged.connect(self.on_manual_reactive_power_spinbox_changed)
        
        reactive_power_control_layout = QHBoxLayout()
        reactive_power_control_layout.addWidget(self.reactive_power_slider)
        reactive_power_control_layout.addWidget(self.reactive_power_spinbox)
        manual_panel_layout.addRow("无功功率:", reactive_power_control_layout)
        
        # 应用按钮
        self.apply_manual_btn = QPushButton("应用手动设置")
        self.apply_manual_btn.clicked.connect(self.apply_manual_power_settings)
        manual_panel_layout.addRow("", self.apply_manual_btn)
        
        self.manual_control_panel.setVisible(False)
        manual_control_layout.addWidget(self.manual_control_panel)
        
        layout.addWidget(manual_control_group)
        
        # 添加弹性空间
        layout.addStretch()
        
    def create_sgen_data_generation_tab(self):
        """创建光伏设备专用的数据生成控制选项卡"""
        layout = QVBoxLayout(self.sgen_data_tab)
        
        # 当前选择设备信息
        current_device_group = QGroupBox("当前选择光伏设备")
        current_device_layout = QVBoxLayout(current_device_group)
        
        self.sgen_current_device_label = QLabel("未选择光伏设备")
        self.sgen_current_device_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        current_device_layout.addWidget(self.sgen_current_device_label)
        
        # 设备数据生成控制
        device_control_layout = QHBoxLayout()
        self.sgen_enable_generation_checkbox = QCheckBox("启用光伏设备数据生成")
        self.sgen_enable_generation_checkbox.stateChanged.connect(self.toggle_sgen_data_generation)
        device_control_layout.addWidget(self.sgen_enable_generation_checkbox)
        
        current_device_layout.addLayout(device_control_layout)
        layout.addWidget(current_device_group)
        
        # 光伏专用参数设置
        sgen_params_group = QGroupBox("光伏发电参数设置")
        sgen_params_layout = QFormLayout(sgen_params_group)
        
        # 变化幅度
        self.sgen_variation_spinbox = QDoubleSpinBox()
        self.sgen_variation_spinbox.setRange(0.0, 50.0)
        self.sgen_variation_spinbox.setValue(15.0)
        self.sgen_variation_spinbox.setSuffix("%")
        sgen_params_layout.addRow("功率变化幅度:", self.sgen_variation_spinbox)
        
        # 季节因子
        self.sgen_season_combo = QComboBox()
        self.sgen_season_combo.addItems(["春季", "夏季", "秋季", "冬季"])
        self.sgen_season_combo.setCurrentText("夏季")
        sgen_params_layout.addRow("季节因子:", self.sgen_season_combo)
        
        # 天气类型（光伏专用）
        self.sgen_weather_combo = QComboBox()
        self.sgen_weather_combo.addItems(["晴天", "多云", "阴天", "雨天"])
        self.sgen_weather_combo.setCurrentText("晴天")
        sgen_params_layout.addRow("天气类型:", self.sgen_weather_combo)
        
        # 光照强度系数
        self.sgen_irradiance_spinbox = QDoubleSpinBox()
        self.sgen_irradiance_spinbox.setRange(0.1, 1.5)
        self.sgen_irradiance_spinbox.setValue(1.0)
        self.sgen_irradiance_spinbox.setDecimals(2)
        sgen_params_layout.addRow("光照强度系数:", self.sgen_irradiance_spinbox)
        
        layout.addWidget(sgen_params_group)
        
        # 光伏手动控制
        sgen_manual_group = QGroupBox("光伏手动功率控制")
        sgen_manual_layout = QVBoxLayout(sgen_manual_group)
        
        # 控制模式选择
        sgen_mode_layout = QHBoxLayout()
        self.sgen_auto_mode_radio = QRadioButton("自动发电")
        self.sgen_manual_mode_radio = QRadioButton("手动控制")
        self.sgen_auto_mode_radio.setChecked(True)
        self.sgen_auto_mode_radio.toggled.connect(self.on_sgen_mode_changed)
        self.sgen_manual_mode_radio.toggled.connect(self.on_sgen_mode_changed)
        sgen_mode_layout.addWidget(self.sgen_auto_mode_radio)
        sgen_mode_layout.addWidget(self.sgen_manual_mode_radio)
        sgen_manual_layout.addLayout(sgen_mode_layout)
        
        # 手动控制面板
        self.sgen_manual_panel = QWidget()
        sgen_manual_panel_layout = QFormLayout(self.sgen_manual_panel)
        
        # 有功功率控制
        self.sgen_power_slider = QSlider(Qt.Horizontal)
        self.sgen_power_slider.setRange(0, 200)
        self.sgen_power_slider.setValue(100)
        self.sgen_power_slider.setMinimumWidth(300)
        self.sgen_power_slider.valueChanged.connect(self.on_sgen_power_changed)
        
        self.sgen_power_spinbox = QDoubleSpinBox()
        self.sgen_power_spinbox.setRange(0.0, 20.0)
        self.sgen_power_spinbox.setValue(10.0)
        self.sgen_power_spinbox.setSuffix(" MW")
        self.sgen_power_spinbox.setDecimals(1)
        self.sgen_power_spinbox.valueChanged.connect(self.on_sgen_power_spinbox_changed)
        
        sgen_power_layout = QHBoxLayout()
        sgen_power_layout.addWidget(self.sgen_power_slider)
        sgen_power_layout.addWidget(self.sgen_power_spinbox)
        sgen_manual_panel_layout.addRow("发电功率:", sgen_power_layout)
        
        # 应用按钮
        self.sgen_apply_btn = QPushButton("应用光伏设置")
        self.sgen_apply_btn.clicked.connect(self.apply_sgen_settings)
        sgen_manual_panel_layout.addRow("", self.sgen_apply_btn)
        
        self.sgen_manual_panel.setVisible(False)
        sgen_manual_layout.addWidget(self.sgen_manual_panel)
        
        layout.addWidget(sgen_manual_group)
        layout.addStretch()
        
    def create_load_data_generation_tab(self):
        """创建负载设备专用的数据生成控制选项卡"""
        layout = QVBoxLayout(self.load_data_tab)
        
        # 当前选择设备信息
        current_device_group = QGroupBox("当前选择负载设备")
        current_device_layout = QVBoxLayout(current_device_group)
        
        self.load_current_device_label = QLabel("未选择负载设备")
        self.load_current_device_label.setStyleSheet("font-weight: bold; color: #F44336;")
        current_device_layout.addWidget(self.load_current_device_label)
        
        # 设备数据生成控制
        device_control_layout = QHBoxLayout()
        self.load_enable_generation_checkbox = QCheckBox("启用负载设备数据生成")
        self.load_enable_generation_checkbox.stateChanged.connect(self.toggle_load_data_generation)
        device_control_layout.addWidget(self.load_enable_generation_checkbox)
        
        current_device_layout.addLayout(device_control_layout)
        layout.addWidget(current_device_group)
        
        # 负载专用参数设置
        load_params_group = QGroupBox("负载用电参数设置")
        load_params_layout = QFormLayout(load_params_group)
        
        # 变化幅度
        self.load_variation_spinbox = QDoubleSpinBox()
        self.load_variation_spinbox.setRange(0.0, 50.0)
        self.load_variation_spinbox.setValue(10.0)
        self.load_variation_spinbox.setSuffix("%")
        load_params_layout.addRow("功率变化幅度:", self.load_variation_spinbox)
        
        # 季节因子
        self.load_season_combo = QComboBox()
        self.load_season_combo.addItems(["春季", "夏季", "秋季", "冬季"])
        self.load_season_combo.setCurrentText("夏季")
        load_params_layout.addRow("季节因子:", self.load_season_combo)
        
        # 负载类型（负载专用）
        self.load_type_combo = QComboBox()
        self.load_type_combo.addItems(["居民负载", "工业负载", "商业负载", "农业负载"])
        self.load_type_combo.setCurrentText("居民负载")
        load_params_layout.addRow("负载类型:", self.load_type_combo)
        
        # 功率因数
        self.load_power_factor_spinbox = QDoubleSpinBox()
        self.load_power_factor_spinbox.setRange(0.7, 1.0)
        self.load_power_factor_spinbox.setValue(0.9)
        self.load_power_factor_spinbox.setDecimals(2)
        load_params_layout.addRow("功率因数:", self.load_power_factor_spinbox)
        
        layout.addWidget(load_params_group)
        
        # 负载手动控制
        load_manual_group = QGroupBox("负载手动功率控制")
        load_manual_layout = QVBoxLayout(load_manual_group)
        
        # 控制模式选择
        load_mode_layout = QHBoxLayout()
        self.load_auto_mode_radio = QRadioButton("自动用电")
        self.load_manual_mode_radio = QRadioButton("手动控制")
        self.load_auto_mode_radio.setChecked(True)
        self.load_auto_mode_radio.toggled.connect(self.on_load_mode_changed)
        self.load_manual_mode_radio.toggled.connect(self.on_load_mode_changed)
        load_mode_layout.addWidget(self.load_auto_mode_radio)
        load_mode_layout.addWidget(self.load_manual_mode_radio)
        load_manual_layout.addLayout(load_mode_layout)
        
        # 手动控制面板
        self.load_manual_panel = QWidget()
        load_manual_panel_layout = QFormLayout(self.load_manual_panel)
        
        # 有功功率控制
        self.load_power_slider = QSlider(Qt.Horizontal)
        self.load_power_slider.setRange(0, 200)
        self.load_power_slider.setValue(100)
        self.load_power_slider.setMinimumWidth(300)
        self.load_power_slider.valueChanged.connect(self.on_load_power_changed)
        
        self.load_power_spinbox = QDoubleSpinBox()
        self.load_power_spinbox.setRange(0.0, 100.0)
        self.load_power_spinbox.setValue(1.0)
        self.load_power_spinbox.setSuffix(" MW")
        self.load_power_spinbox.setDecimals(3)
        self.load_power_spinbox.valueChanged.connect(self.on_load_power_spinbox_changed)
        
        load_power_layout = QHBoxLayout()
        load_power_layout.addWidget(self.load_power_slider)
        load_power_layout.addWidget(self.load_power_spinbox)
        load_manual_panel_layout.addRow("有功功率:", load_power_layout)
        
        # 无功功率控制（负载专用）
        self.load_reactive_power_slider = QSlider(Qt.Horizontal)
        self.load_reactive_power_slider.setRange(0, 200)
        self.load_reactive_power_slider.setValue(100)
        self.load_reactive_power_slider.setMinimumWidth(300)
        self.load_reactive_power_slider.valueChanged.connect(self.on_load_reactive_power_changed)
        
        self.load_reactive_power_spinbox = QDoubleSpinBox()
        self.load_reactive_power_spinbox.setRange(0.0, 50.0)
        self.load_reactive_power_spinbox.setValue(0.5)
        self.load_reactive_power_spinbox.setSuffix(" MVar")
        self.load_reactive_power_spinbox.setDecimals(3)
        self.load_reactive_power_spinbox.valueChanged.connect(self.on_load_reactive_power_spinbox_changed)
        
        load_reactive_power_layout = QHBoxLayout()
        load_reactive_power_layout.addWidget(self.load_reactive_power_slider)
        load_reactive_power_layout.addWidget(self.load_reactive_power_spinbox)
        load_manual_panel_layout.addRow("无功功率:", load_reactive_power_layout)
        
        # 应用按钮
        self.load_apply_btn = QPushButton("应用负载设置")
        self.load_apply_btn.clicked.connect(self.apply_load_settings)
        load_manual_panel_layout.addRow("", self.load_apply_btn)
        
        self.load_manual_panel.setVisible(False)
        load_manual_layout.addWidget(self.load_manual_panel)
        
        layout.addWidget(load_manual_group)
        layout.addStretch()
        
    def create_storage_data_generation_tab(self):
        """创建储能设备专用的手动控制选项卡"""
        layout = QVBoxLayout(self.storage_data_tab)
        
        # 当前选择设备信息
        current_device_group = QGroupBox("当前选择储能设备")
        current_device_layout = QVBoxLayout(current_device_group)
        
        self.storage_current_device_label = QLabel("未选择储能设备")
        self.storage_current_device_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        current_device_layout.addWidget(self.storage_current_device_label)
        
        layout.addWidget(current_device_group)
        
        # 储能手动控制
        storage_manual_group = QGroupBox("储能手动功率控制")
        storage_manual_layout = QVBoxLayout(storage_manual_group)
        
        # 手动控制面板
        self.storage_manual_panel = QWidget()
        storage_manual_panel_layout = QFormLayout(self.storage_manual_panel)
        
        # 有功功率控制（正值为放电，负值为充电）
        self.storage_power_slider = QSlider(Qt.Horizontal)
        self.storage_power_slider.setRange(-1000, 1000)  # 滑块范围：-100.0到100.0MW（乘以10）
        self.storage_power_slider.setValue(0)
        self.storage_power_slider.setMinimumWidth(300)
        self.storage_power_slider.valueChanged.connect(self.on_storage_power_changed)
        
        self.storage_power_spinbox = QDoubleSpinBox()
        self.storage_power_spinbox.setRange(-100.0, 100.0)  # 支持充电和放电
        self.storage_power_spinbox.setValue(0.0)
        self.storage_power_spinbox.setSuffix(" MW")
        self.storage_power_spinbox.setDecimals(1)
        self.storage_power_spinbox.valueChanged.connect(self.on_storage_power_spinbox_changed)
        
        storage_power_layout = QHBoxLayout()
        storage_power_layout.addWidget(self.storage_power_slider)
        storage_power_layout.addWidget(self.storage_power_spinbox)
        storage_manual_panel_layout.addRow("充放电功率:", storage_power_layout)
        
        # 功率说明标签
        power_info_label = QLabel("正值为放电，负值为充电")
        power_info_label.setStyleSheet("color: #666; font-size: 10px;")
        storage_manual_panel_layout.addRow("", power_info_label)
        
        # 应用按钮
        self.storage_apply_btn = QPushButton("应用储能设置")
        self.storage_apply_btn.clicked.connect(self.apply_storage_settings)
        storage_manual_panel_layout.addRow("", self.storage_apply_btn)
        
        # 储能设备默认显示手动控制面板
        self.storage_manual_panel.setVisible(True)
        storage_manual_layout.addWidget(self.storage_manual_panel)
        
        layout.addWidget(storage_manual_group)
        layout.addStretch()
        
    def remove_all_device_tabs(self):
        """移除所有设备专用选项卡"""
        # 移除光伏选项卡
        sgen_tab_index = self.results_tabs.indexOf(self.sgen_data_tab)
        if sgen_tab_index != -1:
            self.results_tabs.removeTab(sgen_tab_index)
            
        # 移除负载选项卡
        load_tab_index = self.results_tabs.indexOf(self.load_data_tab)
        if load_tab_index != -1:
            self.results_tabs.removeTab(load_tab_index)
            
        # 移除储能选项卡
        storage_tab_index = self.results_tabs.indexOf(self.storage_data_tab)
        if storage_tab_index != -1:
            self.results_tabs.removeTab(storage_tab_index)
    
    def update_sgen_device_info(self, component_type, component_idx):
        """更新光伏设备信息"""
        if component_type and component_idx is not None:
            device_name = f"光伏_{component_idx}"
            self.sgen_current_device_label.setText(f"当前设备: {device_name}")
            
            # 检查当前设备是否启用了数据生成
            is_enabled = self.is_device_generation_enabled(component_type, component_idx)
            self.sgen_enable_generation_checkbox.setChecked(is_enabled)
            self.sgen_enable_generation_checkbox.setEnabled(True)
        else:
            self.sgen_current_device_label.setText("未选择光伏设备")
            self.sgen_enable_generation_checkbox.setChecked(False)
            self.sgen_enable_generation_checkbox.setEnabled(False)
    
    def update_load_device_info(self, component_type, component_idx):
        """更新负载设备信息"""
        if component_type and component_idx is not None:
            device_name = f"负载_{component_idx}"
            self.load_current_device_label.setText(f"当前设备: {device_name}")
            
            # 检查当前设备是否启用了数据生成
            is_enabled = self.is_device_generation_enabled(component_type, component_idx)
            self.load_enable_generation_checkbox.setChecked(is_enabled)
            self.load_enable_generation_checkbox.setEnabled(True)
        else:
            self.load_current_device_label.setText("未选择负载设备")
            self.load_enable_generation_checkbox.setChecked(False)
            self.load_enable_generation_checkbox.setEnabled(False)
    
    def update_storage_device_info(self, component_type, component_idx):
        """更新储能设备信息"""
        if component_type and component_idx is not None:
            device_name = f"储能_{component_idx}"
            self.storage_current_device_label.setText(f"当前设备: {device_name}")
            
            # 检查当前设备是否启用了数据生成
            is_enabled = self.is_device_generation_enabled(component_type, component_idx)
        else:
            self.storage_current_device_label.setText("未选择储能设备")
    
    def update_current_device_info(self, component_type, component_idx):
        """更新当前选择设备信息（保留原方法以兼容性）"""
        if component_type and component_idx is not None:
            device_name = f"{component_type}_{component_idx}"
            # 这个方法现在主要用于兼容性，实际更新由各设备专用方法处理
        else:
            pass
    
    def is_device_generation_enabled(self, component_type, component_idx):
        """检查指定设备是否启用了数据生成"""
        device_key = f"{component_type}_{component_idx}"
        return device_key in self.generated_devices
    
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
        """通用的设备数据生成切换方法"""
        if hasattr(self, 'current_component_type') and hasattr(self, 'current_component_idx'):
            if self.current_component_type == device_type and self.current_component_idx is not None:
                device_key = f"{self.current_component_type}_{self.current_component_idx}"
                device_name = f"{self.current_component_type}_{self.current_component_idx}"
                
                if state == 2:  # Qt.Checked
                    # 启用设备数据生成时，确保切换到自动模式
                    if device_type == 'sgen' and hasattr(self, 'sgen_manual_mode_radio') and self.sgen_manual_mode_radio.isChecked():
                        self.sgen_auto_mode_radio.setChecked(True)
                        self.sgen_manual_panel.setVisible(False)
                    elif device_type == 'load' and hasattr(self, 'load_manual_mode_radio') and self.load_manual_mode_radio.isChecked():
                        self.load_auto_mode_radio.setChecked(True)
                        self.load_manual_panel.setVisible(False)
                    elif device_type == 'storage' and hasattr(self, 'storage_manual_mode_radio') and self.storage_manual_mode_radio.isChecked():
                        self.storage_auto_mode_radio.setChecked(True)
                        self.storage_manual_panel.setVisible(False)
                    
                    # 启用设备数据生成
                    if device_key not in self.generated_devices:
                        self.generated_devices.add(device_key)
                        # 启动对应的数据生成器（储能设备暂时不启动生成器，因为还没有实现）
                        if self.current_component_type in ['load', 'sgen']:
                            self.data_generator_manager.start_generation(self.current_component_type)
                        
                        # 获取设备类型的中文名称
                        device_type_name = {
                            'load': '负载',
                            'sgen': '光伏', 
                            'storage': '储能'
                        }.get(self.current_component_type, self.current_component_type)
                        
                        self.statusBar().showMessage(f"已启用{device_type_name}设备 {self.current_component_idx} 的数据生成")
                        print(f"启用设备 {device_name} 的数据生成")
                    else:
                        self.statusBar().showMessage(f"设备 {device_name} 已在数据生成列表中")
                else:
                    # 禁用设备数据生成
                    if device_key in self.generated_devices:
                        self.generated_devices.remove(device_key)
                        
                        # 获取设备类型的中文名称
                        device_type_name = {
                            'load': '负载',
                            'sgen': '光伏', 
                            'storage': '储能'
                        }.get(self.current_component_type, self.current_component_type)
                        
                        self.statusBar().showMessage(f"已禁用{device_type_name}设备 {self.current_component_idx} 的数据生成")
                        print(f"禁用设备 {device_name} 的数据生成")
                        
                        # 如果该类型的设备都被禁用了，停止对应的数据生成器
                        type_devices = [key for key in self.generated_devices if key.startswith(f"{self.current_component_type}_")]
                        if not type_devices and self.current_component_type in ['load', 'sgen']:
                            self.data_generator_manager.stop_generation(self.current_component_type)
                    else:
                        self.statusBar().showMessage(f"设备 {device_name} 未在数据生成列表中")
    
    def toggle_device_data_generation(self, state):
        """切换当前设备的数据生成状态（保留兼容性）"""
        if hasattr(self, 'current_component_type'):
            if self.current_component_type == 'sgen':
                self.toggle_sgen_data_generation(state)
            elif self.current_component_type == 'load':
                self.toggle_load_data_generation(state)
            elif self.current_component_type == 'storage':
                self.toggle_storage_data_generation(state)
        
    # 删除潮流结果和短路结果选项卡创建方法
        
    def load_network_data(self):
        """加载网络数据到设备树"""
        if not self.network_model:
            return
            
        self.device_tree.clear()
        
        # 添加母线
        if not self.network_model.net.bus.empty:
            bus_root = QTreeWidgetItem(self.device_tree, ["母线", "分类", "-"])
            for idx, bus in self.network_model.net.bus.iterrows():
                bus_name = bus.get('name', f'Bus_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty and idx in self.network_model.net.res_bus.index else "未计算"
                bus_item = QTreeWidgetItem(bus_root, [f"Bus {idx}: {bus_name}", "母线", status])
                bus_item.setData(0, Qt.UserRole, ('bus', idx))
                
        # 添加线路
        if not self.network_model.net.line.empty:
            line_root = QTreeWidgetItem(self.device_tree, ["线路", "分类", "-"])
            for idx, line in self.network_model.net.line.iterrows():
                line_name = line.get('name', f'Line_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_line') and not self.network_model.net.res_line.empty and idx in self.network_model.net.res_line.index else "未计算"
                line_item = QTreeWidgetItem(line_root, [f"Line {idx}: {line_name}", "线路", status])
                line_item.setData(0, Qt.UserRole, ('line', idx))
                
        # 添加变压器
        if not self.network_model.net.trafo.empty:
            trafo_root = QTreeWidgetItem(self.device_tree, ["变压器", "分类", "-"])
            for idx, trafo in self.network_model.net.trafo.iterrows():
                trafo_name = trafo.get('name', f'Trafo_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_trafo') and not self.network_model.net.res_trafo.empty and idx in self.network_model.net.res_trafo.index else "未计算"
                trafo_item = QTreeWidgetItem(trafo_root, [f"Trafo {idx}: {trafo_name}", "变压器", status])
                trafo_item.setData(0, Qt.UserRole, ('trafo', idx))
                
        # 添加负载
        if not self.network_model.net.load.empty:
            load_root = QTreeWidgetItem(self.device_tree, ["负载", "分类", "-"])
            for idx, load in self.network_model.net.load.iterrows():
                load_name = load.get('name', f'Load_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_load') and not self.network_model.net.res_load.empty and idx in self.network_model.net.res_load.index else "未计算"
                load_item = QTreeWidgetItem(load_root, [f"Load {idx}: {load_name}", "负载", status])
                load_item.setData(0, Qt.UserRole, ('load', idx))
                
        # 添加发电机
        if not self.network_model.net.gen.empty:
            gen_root = QTreeWidgetItem(self.device_tree, ["发电机", "分类", "-"])
            for idx, gen in self.network_model.net.gen.iterrows():
                gen_name = gen.get('name', f'Gen_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_gen') and not self.network_model.net.res_gen.empty and idx in self.network_model.net.res_gen.index else "未计算"
                gen_item = QTreeWidgetItem(gen_root, [f"Gen {idx}: {gen_name}", "发电机", status])
                gen_item.setData(0, Qt.UserRole, ('gen', idx))
                
        # 添加光伏
        if not self.network_model.net.sgen.empty:
            sgen_root = QTreeWidgetItem(self.device_tree, ["光伏", "分类", "-"])
            for idx, sgen in self.network_model.net.sgen.iterrows():
                sgen_name = sgen.get('name', f'SGen_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_sgen') and not self.network_model.net.res_sgen.empty and idx in self.network_model.net.res_sgen.index else "未计算"
                sgen_item = QTreeWidgetItem(sgen_root, [f"SGen {idx}: {sgen_name}", "光伏", status])
                sgen_item.setData(0, Qt.UserRole, ('sgen', idx))
                
        # 添加外部电网
        if not self.network_model.net.ext_grid.empty:
            ext_grid_root = QTreeWidgetItem(self.device_tree, ["外部电网", "分类", "-"])
            for idx, ext_grid in self.network_model.net.ext_grid.iterrows():
                ext_grid_name = ext_grid.get('name', f'ExtGrid_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_ext_grid') and not self.network_model.net.res_ext_grid.empty and idx in self.network_model.net.res_ext_grid.index else "未计算"
                ext_grid_item = QTreeWidgetItem(ext_grid_root, [f"ExtGrid {idx}: {ext_grid_name}", "外部电网", status])
                ext_grid_item.setData(0, Qt.UserRole, ('ext_grid', idx))
                
        # 添加储能
        if not self.network_model.net.storage.empty:
            storage_root = QTreeWidgetItem(self.device_tree, ["储能", "分类", "-"])
            for idx, storage in self.network_model.net.storage.iterrows():
                storage_name = storage.get('name', f'Storage_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_storage') and not self.network_model.net.res_storage.empty and idx in self.network_model.net.res_storage.index else "未计算"
                storage_item = QTreeWidgetItem(storage_root, [f"Storage {idx}: {storage_name}", "储能", status])
                storage_item.setData(0, Qt.UserRole, ('storage', idx))
        
        # 展开所有节点
        self.device_tree.expandAll()
        
        # 更新设备统计
        self.update_device_stats()
        
    def render_network_image(self):
        """渲染网络图像到中央区域"""
        try:
            # 从画布获取场景内容并渲染为图像
            scene = self.canvas.scene
            scene_rect = scene.itemsBoundingRect()
            
            if scene_rect.isEmpty():
                self.image_label.setText("网络为空")
                return
                
            # 创建更大的像素图以容纳额外的信息显示
            margin = 150
            pixmap = QPixmap(int(scene_rect.width() + margin * 2), int(scene_rect.height() + margin * 2))
            pixmap.fill(Qt.white)
            
            # 渲染场景到像素图
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 先渲染原始场景
            target_rect = QRectF(margin, margin, scene_rect.width(), scene_rect.height())
            scene.render(painter, target_rect, scene_rect)
            
            # 简化网络图像渲染，移除潮流计算结果
            has_results = False
            
            # 添加基础图例和状态信息
            self.draw_image_legend(painter, pixmap.width(), pixmap.height(), has_results)
            
            painter.end()
            
            # 保存原始图像并设置显示
            self.current_pixmap = pixmap
            self.scale_factor = 1.0
            self.update_image_display()
            
        except Exception as e:
            self.image_label.setText(f"渲染网络图像时出错: {str(e)}")
    
    # 删除潮流结果叠加和组件结果文本获取方法
    
    def draw_image_legend(self, painter, width, height, has_results):
        """绘制图像图例和状态信息"""
        try:
            # 设置字体和画笔
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.setPen(Qt.black)
            
            # 绘制标题
            title = "电力系统网络拓扑图"
            painter.drawText(10, 20, title)
            
            # 绘制状态信息
            painter.setFont(QFont("Arial", 9))
            painter.setPen(Qt.darkGreen)
            painter.drawText(10, 40, "✓ 网络拓扑图已生成")
                
            # 绘制网络统计信息
            stats_x = width - 200
            stats_y = 20
            painter.setPen(Qt.black)
            painter.drawText(stats_x, stats_y, "网络统计:")
            
            if self.network_model:
                net = self.network_model.net
                painter.drawText(stats_x, stats_y + 20, f"母线: {len(net.bus)}")
                painter.drawText(stats_x, stats_y + 35, f"线路: {len(net.line)}")
                painter.drawText(stats_x, stats_y + 50, f"变压器: {len(net.trafo)}")
                painter.drawText(stats_x, stats_y + 65, f"负载: {len(net.load)}")
                painter.drawText(stats_x, stats_y + 80, f"发电机: {len(net.gen)}")
                
        except Exception as e:
            print(f"绘制图例时出错: {str(e)}")
            
    def on_device_selected(self, item, column):
        """设备树中选择设备时的处理"""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
            
        component_type, component_idx = data
        self.selected_device_id = str(component_idx)
        self.selected_device_type = self.get_component_type_chinese(component_type)
        
        # 更新当前设备监控复选框状态
        device_key = f"{self.selected_device_type}_{self.selected_device_id}"
        self.current_device_monitor.setChecked(device_key in self.monitored_devices)
        
        # 显示组件详情
        self.show_component_details(component_type, component_idx)
        
        self.enable_device_data_generation(component_type, component_idx)

        
    def show_component_details(self, component_type, component_idx):
        """显示组件详细信息"""
        if not self.network_model:
            return
            
        # 检查是否需要更新选项卡（只有在设备类型改变时才重新组织选项卡）
        need_update_tabs = not hasattr(self, 'current_component_type') or self.current_component_type != component_type
        
        # 记录当前显示的组件信息，用于自动更新
        self.current_component_type = component_type
        self.current_component_idx = component_idx
        
        # 只有在设备类型改变时才重新组织选项卡
        if need_update_tabs:
            # 首先移除所有设备专用选项卡
            self.remove_all_device_tabs()
            
            # 根据设备类型添加对应的专用选项卡
            if component_type == 'sgen':
                self.results_tabs.addTab(self.sgen_data_tab, "光伏控制")
            elif component_type == 'load':
                self.results_tabs.addTab(self.load_data_tab, "负载控制")
            elif component_type == 'storage':
                self.results_tabs.addTab(self.storage_data_tab, "储能控制")
        
        # 更新设备信息（每次都需要更新，因为可能是同类型的不同设备）
        if component_type == 'sgen':
            self.update_sgen_device_info(component_type, component_idx)
        elif component_type == 'load':
            self.update_load_device_info(component_type, component_idx)
        elif component_type == 'storage':
            self.update_storage_device_info(component_type, component_idx)
            
        try:
            # 获取组件数据
            component_data = None
            result_data = None
            
            if component_type == 'bus':
                component_data = self.network_model.net.bus.loc[component_idx]
                if hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty:
                    if component_idx in self.network_model.net.res_bus.index:
                        result_data = self.network_model.net.res_bus.loc[component_idx]
            elif component_type == 'line':
                component_data = self.network_model.net.line.loc[component_idx]
                if hasattr(self.network_model.net, 'res_line') and not self.network_model.net.res_line.empty:
                    if component_idx in self.network_model.net.res_line.index:
                        result_data = self.network_model.net.res_line.loc[component_idx]
            elif component_type == 'trafo':
                component_data = self.network_model.net.trafo.loc[component_idx]
                if hasattr(self.network_model.net, 'res_trafo') and not self.network_model.net.res_trafo.empty:
                    if component_idx in self.network_model.net.res_trafo.index:
                        result_data = self.network_model.net.res_trafo.loc[component_idx]
            elif component_type == 'load':
                component_data = self.network_model.net.load.loc[component_idx]
                if hasattr(self.network_model.net, 'res_load') and not self.network_model.net.res_load.empty:
                    if component_idx in self.network_model.net.res_load.index:
                        result_data = self.network_model.net.res_load.loc[component_idx]
            elif component_type == 'gen':
                component_data = self.network_model.net.gen.loc[component_idx]
                if hasattr(self.network_model.net, 'res_gen') and not self.network_model.net.res_gen.empty:
                    if component_idx in self.network_model.net.res_gen.index:
                        result_data = self.network_model.net.res_gen.loc[component_idx]
            elif component_type == 'sgen':
                component_data = self.network_model.net.sgen.loc[component_idx]
                if hasattr(self.network_model.net, 'res_sgen') and not self.network_model.net.res_sgen.empty:
                    if component_idx in self.network_model.net.res_sgen.index:
                        result_data = self.network_model.net.res_sgen.loc[component_idx]
            elif component_type == 'ext_grid':
                component_data = self.network_model.net.ext_grid.loc[component_idx]
                if hasattr(self.network_model.net, 'res_ext_grid') and not self.network_model.net.res_ext_grid.empty:
                    if component_idx in self.network_model.net.res_ext_grid.index:
                        result_data = self.network_model.net.res_ext_grid.loc[component_idx]
            elif component_type == 'storage':
                component_data = self.network_model.net.storage.loc[component_idx]
                if hasattr(self.network_model.net, 'res_storage') and not self.network_model.net.res_storage.empty:
                    if component_idx in self.network_model.net.res_storage.index:
                        result_data = self.network_model.net.res_storage.loc[component_idx]
            else:
                return
                
            # 填充参数表格（组合组件参数和仿真结果）
            all_params = {}
            
            # 先添加仿真结果（显示在最上方）
            if result_data is not None:
                for param, value in result_data.items():
                    all_params[f"结果_{param}"] = value
                    
            # 再添加组件参数
            for param, value in component_data.items():
                all_params[f"参数_{param}"] = value
            
            self.component_params_table.setRowCount(len(all_params))
            for i, (param, value) in enumerate(all_params.items()):
                param_item = QTableWidgetItem(str(param))
                value_item = QTableWidgetItem(f"{value:.4f}" if isinstance(value, float) else str(value))
                
                # 为仿真结果设置不同的背景色
                if param.startswith("结果_"):
                    from PySide6.QtGui import QColor
                    param_item.setBackground(QColor(211, 211, 211))  # 浅灰色
                    value_item.setBackground(QColor(211, 211, 211))  # 浅灰色
                    
                self.component_params_table.setItem(i, 0, param_item)
                self.component_params_table.setItem(i, 1, value_item)
                
        except Exception as e:
            # 显示错误信息在状态栏
            self.parent_window.statusBar().showMessage(f"显示组件详情时出错: {str(e)}")

    def update_component_params_table(self):
        """更新组件参数表格 - 在自动计算时刷新当前显示的组件详情"""
        try:
            # 检查是否有当前选中的组件
            if hasattr(self, 'current_component_type') and hasattr(self, 'current_component_idx'):
                if self.current_component_type and self.current_component_idx is not None:
                    # 重新显示当前组件的详情，这会自动更新表格内容
                    self.show_component_details(self.current_component_type, self.current_component_idx)
        except Exception as e:
            print(f"更新组件参数表格时出错: {str(e)}")

    def enable_device_data_generation(self, component_type, component_idx):
        """标记需要生成数据的设备
        
        该函数用于标记指定设备为需要生成数据的设备，使其在数据生成过程中
        被包含在数据生成范围内。支持负载(load)、光伏(sgen)和储能(storage)设备。
        
        Args:
            component_type (str): 组件类型 ('load', 'sgen', 'storage')
            component_idx (int): 组件索引ID
        """
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
        
        # 支持负载、光伏和储能
        if component_type not in ['load', 'sgen', 'storage']:
            return

        try:
            # 创建设备唯一标识符
            device_key = f"{component_type}_{component_idx}"
            
            # 检查设备是否存在于网络模型中
            if component_type == 'load':
                if component_idx not in self.network_model.net.load.index:
                    self.statusBar().showMessage(f"负载设备 {component_idx} 不存在")
                    return
            elif component_type == 'sgen':
                if component_idx not in self.network_model.net.sgen.index:
                    self.statusBar().showMessage(f"光伏设备 {component_idx} 不存在")
                    return
            elif component_type == 'storage':
                if component_idx not in self.network_model.net.storage.index:
                    self.statusBar().showMessage(f"储能设备 {component_idx} 不存在")
                    return

            # 检查设备是否已存在于监控列表中
            if device_key not in self.generated_devices:
                # 将设备添加到监控设备集合
                self.generated_devices.add(device_key)
                
                # 启动对应的数据生成器（储能设备暂时不启动生成器）
                if component_type in ['load', 'sgen']:
                    self.data_generator_manager.start_generation(component_type)
                
                # 显示成功消息
                device_type_names = {
                    'load': '负载',
                    'sgen': '光伏',
                    'storage': '储能'
                }
                device_name = device_type_names.get(component_type, component_type)
                self.statusBar().showMessage(f"已将{device_name}设备 {component_idx} 标记为数据生成设备")
                
            else:
                # 设备已存在，显示提示信息
                device_type_names = {
                    'load': '负载',
                    'sgen': '光伏',
                    'storage': '储能'
                }
                device_name = device_type_names.get(component_type, component_type)
                self.statusBar().showMessage(f"{device_name}设备 {component_idx} 已在数据生成列表中")
                
        except Exception as e:
            self.statusBar().showMessage(f"标记设备数据生成时出错: {str(e)}")
            print(f"Error in enable_device_data_generation: {str(e)}")
    
    def disable_device_data_generation(self, component_type, component_idx):
        """禁用指定设备的数据生成
        
        Args:
            component_type (str): 组件类型 ('load', 'sgen', 'storage')
            component_idx (int): 组件索引ID
        """
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
        
        # 支持负载、光伏和储能
        if component_type not in ['load', 'sgen', 'storage']:
            return

        try:
            # 创建设备唯一标识符
            device_key = f"{component_type}_{component_idx}"
            
            # 检查设备是否在生成列表中
            if device_key in self.generated_devices:
                # 从生成设备集合中移除
                self.generated_devices.remove(device_key)
                
                # 显示成功消息
                device_type_names = {
                    'load': '负载',
                    'sgen': '光伏',
                    'storage': '储能'
                }
                device_name = device_type_names.get(component_type, component_type)
                self.statusBar().showMessage(f"已禁用{device_name}设备 {component_idx} 的数据生成")
                
                # 如果该类型的设备都被禁用了，停止对应的数据生成器（储能设备暂时不需要停止生成器）
                type_devices = [key for key in self.generated_devices if key.startswith(f"{component_type}_")]
                if not type_devices and component_type in ['load', 'sgen']:
                    self.data_generator_manager.stop_generation(component_type)
                    
            else:
                # 设备不在生成列表中，显示提示信息
                device_type_names = {
                    'load': '负载',
                    'sgen': '光伏',
                    'storage': '储能'
                }
                device_name = device_type_names.get(component_type, component_type)
                self.statusBar().showMessage(f"{device_name}设备 {component_idx} 未在数据生成列表中")
                
        except Exception as e:
            self.statusBar().showMessage(f"禁用设备数据生成时出错: {str(e)}")
            print(f"Error in disable_device_data_generation: {str(e)}")
    
    def get_component_type_chinese(self, component_type):
        """获取组件类型的中文名称"""
        type_map = {
            'bus': '母线',
            'line': '线路', 
            'trafo': '变压器',
            'load': '负载',
            'gen': '发电机',
            'sgen': '光伏',
            'ext_grid': '外部电网',
            'storage': '储能'
        }
        return type_map.get(component_type, component_type)
            
        
    def eventFilter(self, obj, event):
        """事件过滤器，处理图像缩放和平移"""
        if obj == self.scroll_area.viewport() or obj == self.image_label:
            if event.type() == event.Type.Wheel:
                return self.handle_wheel_event(event)
            elif event.type() == event.Type.MouseButtonPress:
                return self.handle_mouse_press_event(event)
            elif event.type() == event.Type.MouseMove:
                return self.handle_mouse_move_event(event)
            elif event.type() == event.Type.MouseButtonRelease:
                return self.handle_mouse_release_event(event)
            elif event.type() == event.Type.MouseButtonDblClick:
                return self.handle_double_click_event(event)
        
        return super().eventFilter(obj, event)
    
    def handle_wheel_event(self, event):
        """处理鼠标滚轮事件进行缩放"""
        if self.current_pixmap is None:
            return False
            
        # 计算缩放因子
        delta = event.angleDelta().y()
        scale_change = 1.15 if delta > 0 else 1.0 / 1.15
        
        new_scale = self.scale_factor * scale_change
        new_scale = max(self.min_scale, min(self.max_scale, new_scale))
        
        if new_scale != self.scale_factor:
            self.scale_factor = new_scale
            self.update_image_display()
            
        return True
    
    def handle_mouse_press_event(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.last_pan_point = event.pos()
            self.scroll_area.setCursor(Qt.ClosedHandCursor)
            return True
        return False
    
    def handle_mouse_move_event(self, event):
        """处理鼠标移动事件进行平移"""
        if self.last_pan_point is not None and (event.buttons() & Qt.LeftButton):
            delta = event.pos() - self.last_pan_point
            
            # 获取滚动条
            h_scroll = self.scroll_area.horizontalScrollBar()
            v_scroll = self.scroll_area.verticalScrollBar()
            
            # 更新滚动条位置
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
            
            self.last_pan_point = event.pos()
            return True
        return False
    
    def handle_mouse_release_event(self, event):
        """处理鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.last_pan_point = None
            self.scroll_area.setCursor(Qt.ArrowCursor)
            return True
        return False
    
    def handle_double_click_event(self, event):
        """处理双击事件，适应窗口大小"""
        if self.current_pixmap is None:
            return False
            
        # 计算适应窗口的缩放因子
        scroll_size = self.scroll_area.size()
        pixmap_size = self.current_pixmap.size()
        
        scale_x = (scroll_size.width() - 20) / pixmap_size.width()
        scale_y = (scroll_size.height() - 20) / pixmap_size.height()
        
        self.scale_factor = min(scale_x, scale_y, 1.0)  # 不放大，只缩小
        self.update_image_display()
        
        return True
    
    def update_image_display(self):
        """更新图像显示"""
        if self.current_pixmap is None:
            return
            
        # 缩放图像
        scaled_pixmap = self.current_pixmap.scaled(
            self.current_pixmap.size() * self.scale_factor,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # 更新图像标签
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.resize(scaled_pixmap.size())
        
        # 更新容器大小
        container_size = scaled_pixmap.size()
        container_size.setWidth(max(container_size.width(), self.scroll_area.width()))
        container_size.setHeight(max(container_size.height(), self.scroll_area.height()))
        self.image_container.resize(container_size)
        
        # 居中显示图像
        x = max(0, (container_size.width() - scaled_pixmap.width()) // 2)
        y = max(0, (container_size.height() - scaled_pixmap.height()) // 2)
        self.image_label.move(x, y)
        
        # 更新状态栏
        self.statusBar().showMessage(f"缩放: {self.scale_factor:.1%}")
    
    def filter_device_tree(self, text):
        """根据搜索文本过滤设备树"""
        def hide_items(item, text):
            """递归隐藏/显示项目"""
            match = text.lower() in item.text(0).lower()
            
            # 检查子项目
            child_match = False
            for i in range(item.childCount()):
                child = item.child(i)
                if hide_items(child, text):
                    child_match = True
            
            # 如果有匹配的子项目或自身匹配，则显示
            should_show = match or child_match or text == ""
            item.setHidden(not should_show)
            
            return should_show
        
        # 对根项目应用过滤
        for i in range(self.device_tree.topLevelItemCount()):
            root_item = self.device_tree.topLevelItem(i)
            hide_items(root_item, text)
    
    def clear_search(self):
        """清除搜索"""
        self.search_input.clear()
    
    def filter_by_category(self, category):
        """根据分类过滤设备"""
        category_map = {
            "全部设备": [],
            "母线": ["母线"],
            "线路": ["线路"],
            "变压器": ["变压器"],
            "发电设备": ["发电机", "光伏", "外部电网"],
            "负载设备": ["负载"],
            "储能设备": ["储能"]
        }
        
        show_categories = category_map.get(category, [])
        
        for i in range(self.device_tree.topLevelItemCount()):
            root_item = self.device_tree.topLevelItem(i)
            category_name = root_item.text(0)
            
            if category == "全部设备":
                root_item.setHidden(False)
            else:
                root_item.setHidden(category_name not in show_categories)
    
    def refresh_device_tree(self):
        """刷新设备树"""
        self.load_network_data()
        self.search_input.clear()
        self.category_combo.setCurrentText("全部设备")
    
    def update_device_stats(self):
        """更新设备统计信息"""
        if not self.network_model:
            self.device_stats_label.setText("设备统计: 无网络模型")
            return
        
        stats = {
            "母线": len(self.network_model.net.bus),
            "线路": len(self.network_model.net.line),
            "变压器": len(self.network_model.net.trafo),
            "负载": len(self.network_model.net.load),
            "发电机": len(self.network_model.net.gen),
            "光伏": len(self.network_model.net.sgen),
            "外部电网": len(self.network_model.net.ext_grid),
            "储能": len(self.network_model.net.storage)
        }
        
        total = sum(stats.values())
        stats_text = f"设备统计: 总计 {total} 个设备 | "
        stats_text += " | ".join([f"{k}: {v}" for k, v in stats.items() if v > 0])
        
        self.device_stats_label.setText(stats_text)
    
    def export_results_csv(self):
        """导出仿真结果为CSV格式"""
        if not self.network_model:
            QMessageBox.warning(self, "警告", "没有可用的网络模型")
            return
            
        # 检查是否有潮流计算结果
        has_results = hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty
        if not has_results:
            QMessageBox.warning(self, "警告", "请先运行潮流计算")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            import pandas as pd
            from datetime import datetime
            
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出CSV文件", 
                f"powerflow_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV文件 (*.csv)"
            )
            
            if not file_path:
                return
                
            # 收集所有结果数据
            all_results = []
            
            # 母线结果
            if hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty:
                for idx, res in self.network_model.net.res_bus.iterrows():
                    bus_data = self.network_model.net.bus.loc[idx]
                    all_results.append({
                        '组件类型': '母线',
                        '组件ID': idx,
                        '组件名称': bus_data.get('name', f'Bus_{idx}'),
                        '电压幅值(p.u.)': res['vm_pu'],
                        '电压角度(度)': res['va_degree'],
                        '有功功率(MW)': res.get('p_mw', 0),
                        '无功功率(MVar)': res.get('q_mvar', 0),
                        '负载率(%)': '',
                        '状态': '正常' if 0.95 <= res['vm_pu'] <= 1.05 else '异常'
                    })
            
            # 线路结果
            if hasattr(self.network_model.net, 'res_line') and not self.network_model.net.res_line.empty:
                for idx, res in self.network_model.net.res_line.iterrows():
                    line_data = self.network_model.net.line.loc[idx]
                    all_results.append({
                        '组件类型': '线路',
                        '组件ID': idx,
                        '组件名称': line_data.get('name', f'Line_{idx}'),
                        '电压幅值(p.u.)': '',
                        '电压角度(度)': '',
                        '有功功率(MW)': res['p_from_mw'],
                        '无功功率(MVar)': res['q_from_mvar'],
                        '负载率(%)': res['loading_percent'],
                        '状态': '正常' if res['loading_percent'] <= 80 else ('过载' if res['loading_percent'] > 100 else '警告')
                    })
            
            # 变压器结果
            if hasattr(self.network_model.net, 'res_trafo') and not self.network_model.net.res_trafo.empty:
                for idx, res in self.network_model.net.res_trafo.iterrows():
                    trafo_data = self.network_model.net.trafo.loc[idx]
                    all_results.append({
                        '组件类型': '变压器',
                        '组件ID': idx,
                        '组件名称': trafo_data.get('name', f'Trafo_{idx}'),
                        '电压幅值(p.u.)': '',
                        '电压角度(度)': '',
                        '有功功率(MW)': res['p_hv_mw'],
                        '无功功率(MVar)': res['q_hv_mvar'],
                        '负载率(%)': res['loading_percent'],
                        '状态': '正常' if res['loading_percent'] <= 80 else ('过载' if res['loading_percent'] > 100 else '警告')
                    })
            
            # 负载结果
            if hasattr(self.network_model.net, 'res_load') and not self.network_model.net.res_load.empty:
                for idx, res in self.network_model.net.res_load.iterrows():
                    load_data = self.network_model.net.load.loc[idx]
                    all_results.append({
                        '组件类型': '负载',
                        '组件ID': idx,
                        '组件名称': load_data.get('name', f'Load_{idx}'),
                        '电压幅值(p.u.)': '',
                        '电压角度(度)': '',
                        '有功功率(MW)': res['p_mw'],
                        '无功功率(MVar)': res['q_mvar'],
                        '负载率(%)': '',
                        '状态': '运行'
                    })
            
            # 发电机结果
            if hasattr(self.network_model.net, 'res_gen') and not self.network_model.net.res_gen.empty:
                for idx, res in self.network_model.net.res_gen.iterrows():
                    gen_data = self.network_model.net.gen.loc[idx]
                    all_results.append({
                        '组件类型': '发电机',
                        '组件ID': idx,
                        '组件名称': gen_data.get('name', f'Gen_{idx}'),
                        '电压幅值(p.u.)': '',
                        '电压角度(度)': '',
                        '有功功率(MW)': res['p_mw'],
                        '无功功率(MVar)': res['q_mvar'],
                        '负载率(%)': '',
                        '状态': '运行'
                    })
            
            # 创建DataFrame并保存
            df = pd.DataFrame(all_results)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            QMessageBox.information(self, "成功", f"仿真结果已导出到:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出CSV文件失败:\n{str(e)}")
    
    def export_results_excel(self):
        """导出仿真结果为Excel格式"""
        if not self.network_model:
            QMessageBox.warning(self, "警告", "没有可用的网络模型")
            return
            
        # 检查是否有潮流计算结果
        has_results = hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty
        if not has_results:
            QMessageBox.warning(self, "警告", "请先运行潮流计算")
            return
            
        try:
            from PyQt5.QtWidgets import QFileDialog
            import pandas as pd
            from datetime import datetime
            
            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出Excel文件", 
                f"powerflow_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "Excel文件 (*.xlsx)"
            )
            
            if not file_path:
                return
                
            # 创建Excel写入器
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                
                # 母线结果工作表
                if hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty:
                    bus_results = []
                    for idx, res in self.network_model.net.res_bus.iterrows():
                        bus_data = self.network_model.net.bus.loc[idx]
                        bus_results.append({
                            'ID': idx,
                            '名称': bus_data.get('name', f'Bus_{idx}'),
                            '电压幅值(p.u.)': res['vm_pu'],
                            '电压角度(度)': res['va_degree'],
                            '状态': '正常' if 0.95 <= res['vm_pu'] <= 1.05 else '异常'
                        })
                    pd.DataFrame(bus_results).to_excel(writer, sheet_name='母线结果', index=False)
                
                # 线路结果工作表
                if hasattr(self.network_model.net, 'res_line') and not self.network_model.net.res_line.empty:
                    line_results = []
                    for idx, res in self.network_model.net.res_line.iterrows():
                        line_data = self.network_model.net.line.loc[idx]
                        line_results.append({
                            'ID': idx,
                            '名称': line_data.get('name', f'Line_{idx}'),
                            '有功功率(MW)': res['p_from_mw'],
                            '无功功率(MVar)': res['q_from_mvar'],
                            '负载率(%)': res['loading_percent'],
                            '状态': '正常' if res['loading_percent'] <= 80 else ('过载' if res['loading_percent'] > 100 else '警告')
                        })
                    pd.DataFrame(line_results).to_excel(writer, sheet_name='线路结果', index=False)
                
                # 变压器结果工作表
                if hasattr(self.network_model.net, 'res_trafo') and not self.network_model.net.res_trafo.empty:
                    trafo_results = []
                    for idx, res in self.network_model.net.res_trafo.iterrows():
                        trafo_data = self.network_model.net.trafo.loc[idx]
                        trafo_results.append({
                            'ID': idx,
                            '名称': trafo_data.get('name', f'Trafo_{idx}'),
                            '有功功率(MW)': res['p_hv_mw'],
                            '无功功率(MVar)': res['q_hv_mvar'],
                            '负载率(%)': res['loading_percent'],
                            '状态': '正常' if res['loading_percent'] <= 80 else ('过载' if res['loading_percent'] > 100 else '警告')
                        })
                    pd.DataFrame(trafo_results).to_excel(writer, sheet_name='变压器结果', index=False)
                
                # 负载结果工作表
                if hasattr(self.network_model.net, 'res_load') and not self.network_model.net.res_load.empty:
                    load_results = []
                    for idx, res in self.network_model.net.res_load.iterrows():
                        load_data = self.network_model.net.load.loc[idx]
                        load_results.append({
                            'ID': idx,
                            '名称': load_data.get('name', f'Load_{idx}'),
                            '有功功率(MW)': res['p_mw'],
                            '无功功率(MVar)': res['q_mvar']
                        })
                    pd.DataFrame(load_results).to_excel(writer, sheet_name='负载结果', index=False)
                
                # 发电机结果工作表
                if hasattr(self.network_model.net, 'res_gen') and not self.network_model.net.res_gen.empty:
                    gen_results = []
                    for idx, res in self.network_model.net.res_gen.iterrows():
                        gen_data = self.network_model.net.gen.loc[idx]
                        gen_results.append({
                            'ID': idx,
                            '名称': gen_data.get('name', f'Gen_{idx}'),
                            '有功功率(MW)': res['p_mw'],
                            '无功功率(MVar)': res['q_mvar']
                        })
                    pd.DataFrame(gen_results).to_excel(writer, sheet_name='发电机结果', index=False)
                
                # 网络统计工作表
                network_stats = {
                    '组件类型': ['母线', '线路', '变压器', '负载', '发电机', '光伏', '外部电网', '储能'],
                    '数量': [
                        len(self.network_model.net.bus),
                        len(self.network_model.net.line),
                        len(self.network_model.net.trafo),
                        len(self.network_model.net.load),
                        len(self.network_model.net.gen),
                        len(self.network_model.net.sgen),
                        len(self.network_model.net.ext_grid),
                        len(self.network_model.net.storage)
                    ]
                }
                pd.DataFrame(network_stats).to_excel(writer, sheet_name='网络统计', index=False)
            
            QMessageBox.information(self, "成功", f"仿真结果已导出到:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出Excel文件失败:\n{str(e)}")
    
    def update_theme_colors(self):
        """更新主题相关的所有颜色"""
        app = QApplication.instance()
        if app:
            palette = app.palette()
            bg_color = palette.color(QPalette.Window)
            is_dark_theme = bg_color.lightness() < 128
            
            # 更新自动计算控件的样式
            if hasattr(self, 'auto_calc_checkbox'):
                if is_dark_theme:
                    # 深色主题样式
                    checkbox_style = """
                        QCheckBox {
                            spacing: 5px;
                            color: rgb(255, 255, 255);
                        }
                        QCheckBox::indicator {
                            width: 18px;
                            height: 18px;
                            border: 2px solid #888;
                            border-radius: 3px;
                            background-color: rgb(53, 53, 53);
                        }
                        QCheckBox::indicator:checked {
                            background-color: #4CAF50;
                            border-color: #4CAF50;
                        }
                        QCheckBox::indicator:checked:pressed {
                            background-color: #45a049;
                        }
                    """
                else:
                    # 浅色主题样式
                    checkbox_style = """
                        QCheckBox {
                            spacing: 5px;
                            color: rgb(0, 0, 0);
                        }
                        QCheckBox::indicator {
                            width: 18px;
                            height: 18px;
                            border: 2px solid #555;
                            border-radius: 3px;
                            background-color: white;
                        }
                        QCheckBox::indicator:checked {
                            background-color: #4CAF50;
                            border-color: #4CAF50;
                        }
                        QCheckBox::indicator:checked:pressed {
                            background-color: #45a049;
                        }
                    """
                self.auto_calc_checkbox.setStyleSheet(checkbox_style)
            
            # 更新SpinBox样式
            if hasattr(self, 'calc_interval_spinbox'):
                if is_dark_theme:
                    # 深色主题样式
                    spinbox_style = """
                        QSpinBox {
                            padding-right: 15px;
                            border: 1px solid #666;
                            border-radius: 3px;
                            background-color: rgb(53, 53, 53);
                            color: rgb(255, 255, 255);
                        }
                        QSpinBox::up-button {
                            subcontrol-origin: border;
                            subcontrol-position: top right;
                            width: 16px;
                            border-left-width: 1px;
                            border-left-color: #666;
                            border-left-style: solid;
                            border-top-right-radius: 3px;
                            background-color: #666;
                        }
                        QSpinBox::down-button {
                            subcontrol-origin: border;
                            subcontrol-position: bottom right;
                            width: 16px;
                            border-left-width: 1px;
                            border-left-color: #666;
                            border-left-style: solid;
                            border-bottom-right-radius: 3px;
                            background-color: #666;
                        }
                        QSpinBox::up-arrow {
                            image: none;
                            border-left: 4px solid transparent;
                            border-right: 4px solid transparent;
                            border-bottom: 4px solid #ccc;
                            width: 0px;
                            height: 0px;
                        }
                        QSpinBox::down-arrow {
                            image: none;
                            border-left: 4px solid transparent;
                            border-right: 4px solid transparent;
                            border-top: 4px solid #ccc;
                            width: 0px;
                            height: 0px;
                        }
                    """
                else:
                    # 浅色主题样式
                    spinbox_style = """
                        QSpinBox {
                            padding-right: 15px;
                            border: 1px solid #ccc;
                            border-radius: 3px;
                            background-color: white;
                            color: rgb(0, 0, 0);
                        }
                        QSpinBox::up-button {
                            subcontrol-origin: border;
                            subcontrol-position: top right;
                            width: 16px;
                            border-left-width: 1px;
                            border-left-color: #ccc;
                            border-left-style: solid;
                            border-top-right-radius: 3px;
                            background-color: #f0f0f0;
                        }
                        QSpinBox::down-button {
                            subcontrol-origin: border;
                            subcontrol-position: bottom right;
                            width: 16px;
                            border-left-width: 1px;
                            border-left-color: #ccc;
                            border-left-style: solid;
                            border-bottom-right-radius: 3px;
                            background-color: #f0f0f0;
                        }
                        QSpinBox::up-arrow {
                            image: none;
                            border-left: 4px solid transparent;
                            border-right: 4px solid transparent;
                            border-bottom: 4px solid #666;
                            width: 0px;
                            height: 0px;
                        }
                        QSpinBox::down-arrow {
                            image: none;
                            border-left: 4px solid transparent;
                            border-right: 4px solid transparent;
                            border-top: 4px solid #666;
                            width: 0px;
                            height: 0px;
                        }
                    """
                self.calc_interval_spinbox.setStyleSheet(spinbox_style)
            
            # 更新设备树样式
            if hasattr(self, 'device_tree'):
                if is_dark_theme:
                    # 深色主题样式
                    tree_style = """
                        QTreeWidget {
                            background-color: rgb(53, 53, 53);
                            color: rgb(255, 255, 255);
                            border: 1px solid #666;
                            alternate-background-color: rgb(60, 60, 60);
                            selection-background-color: rgb(42, 130, 218);
                            selection-color: rgb(255, 255, 255);
                        }
                        QTreeWidget::item {
                            padding: 2px;
                            border: none;
                        }
                        QTreeWidget::item:selected {
                            background-color: rgb(42, 130, 218);
                            color: rgb(255, 255, 255);
                        }
                        QTreeWidget::item:hover {
                            background-color: rgb(70, 70, 70);
                        }


                        QTreeWidget {
                            color: rgb(255, 255, 255);
                        }
                        QHeaderView::section {
                            background-color: rgb(60, 60, 60);
                            color: rgb(255, 255, 255);
                            border: 1px solid #666;
                            padding: 4px;
                        }
                    """
                else:
                    # 浅色主题样式
                    tree_style = """
                        QTreeWidget {
                            background-color: white;
                            color: rgb(0, 0, 0);
                            border: 1px solid #ccc;
                            alternate-background-color: rgb(245, 245, 245);
                            selection-background-color: rgb(0, 120, 215);
                            selection-color: rgb(255, 255, 255);
                        }
                        QTreeWidget::item {
                            padding: 2px;
                            border: none;
                        }
                        QTreeWidget::item:selected {
                            background-color: rgb(0, 120, 215);
                            color: rgb(255, 255, 255);
                        }
                        QTreeWidget::item:hover {
                            background-color: rgb(230, 230, 230);
                        }


                        QHeaderView::section {
                            background-color: rgb(240, 240, 240);
                            color: rgb(0, 0, 0);
                            border: 1px solid #ccc;
                            padding: 4px;
                        }
                    """
                self.device_tree.setStyleSheet(tree_style)
            
            # 更新监控设备列表样式
            if hasattr(self, 'monitored_devices_list'):
                self.monitored_devices_list.setStyleSheet(tree_style if hasattr(self, 'device_tree') else "")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.auto_calc_timer.stop()
        self.parent_window.statusBar().showMessage("已退出仿真模式")
        event.accept()
    
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
    
    def get_device_power(self, device_id, device_type):
        """获取设备的实际功率属性值"""
        try:
            device_id = int(device_id)  # 确保device_id是整数
            
            # 根据设备类型从潮流计算结果中获取功率值
            if device_type == "母线":
                # 母线本身不直接设置功率，但可以通过潮流计算结果获取总注入功率
                if hasattr(self.network_model.net, 'res_bus') and device_id in self.network_model.net.res_bus.index:
                    # 获取该母线的总注入功率（发电减负荷）
                    return abs(self.network_model.net.res_bus.loc[device_id, 'p_mw'])
                else:
                    return 0.0
                
            elif device_type == "线路":
                # 从线路潮流计算结果中获取功率
                if hasattr(self.network_model.net, 'res_line') and device_id in self.network_model.net.res_line.index:
                    # 获取线路的有功功率（取两端功率的平均值或较大值）
                    p_from = abs(self.network_model.net.res_line.loc[device_id, 'p_from_mw'])
                    p_to = abs(self.network_model.net.res_line.loc[device_id, 'p_to_mw'])
                    return max(p_from, p_to)  # 返回较大的功率值
                else:
                    return 0.0
                    
            elif device_type == "变压器":
                # 从变压器潮流计算结果中获取功率
                if hasattr(self.network_model.net, 'res_trafo') and device_id in self.network_model.net.res_trafo.index:
                    # 获取变压器的有功功率
                    p_hv = abs(self.network_model.net.res_trafo.loc[device_id, 'p_hv_mw'])
                    p_lv = abs(self.network_model.net.res_trafo.loc[device_id, 'p_lv_mw'])
                    return max(p_hv, p_lv)
                else:
                    return 0.0
                    
            elif device_type == "发电机":
                # 从发电机潮流计算结果中获取实际功率
                if hasattr(self.network_model.net, 'res_gen') and device_id in self.network_model.net.res_gen.index:
                    return abs(self.network_model.net.res_gen.loc[device_id, 'p_mw'])
                else:
                    # 如果潮流计算结果没有，使用设定值
                    gens = self.network_model.net.gen
                    if device_id in gens.index:
                        return abs(gens.loc[device_id, 'p_mw'])
                    return 0.0
                    
            elif device_type == "光伏":
                # 从光伏潮流计算结果中获取实际功率
                if hasattr(self.network_model.net, 'res_sgen') and device_id in self.network_model.net.res_sgen.index:
                    return abs(self.network_model.net.res_sgen.loc[device_id, 'p_mw'])
                else:
                    # 使用设定值
                    sgens = self.network_model.net.sgen
                    if device_id in sgens.index:
                        return abs(sgens.loc[device_id, 'p_mw'])
                    return 0.0
                    
            elif device_type == "负载":
                # 从负载潮流计算结果中获取实际功率
                if hasattr(self.network_model.net, 'res_load') and device_id in self.network_model.net.res_load.index:
                    return abs(self.network_model.net.res_load.loc[device_id, 'p_mw'])
                else:
                    # 使用设定值
                    loads = self.network_model.net.load
                    if device_id in loads.index:
                        return abs(loads.loc[device_id, 'p_mw'])
                    return 0.0
                    
            elif device_type == "储能":
                # 从储能潮流计算结果中获取实际功率
                if hasattr(self.network_model.net, 'res_storage') and device_id in self.network_model.net.res_storage.index:
                    return abs(self.network_model.net.res_storage.loc[device_id, 'p_mw'])
                else:
                    # 使用设定值
                    storage = self.network_model.net.storage
                    if device_id in storage.index:
                        return abs(storage.loc[device_id, 'p_mw'])
                    return 0.0
                    
            elif device_type == "外部电网":
                # 从外部电网潮流计算结果中获取功率
                if hasattr(self.network_model.net, 'res_ext_grid') and device_id in self.network_model.net.res_ext_grid.index:
                    return abs(self.network_model.net.res_ext_grid.loc[device_id, 'p_mw'])
                else:
                    return 0.0
                    
        except Exception as e:
            print(f"获取设备功率失败: {str(e)}")
        
        return 0.0
    
    def display_power_curve(self):
        """显示多条功率曲线 - 支持同时监控多个设备"""
        try:
            # 清空当前图表
            self.ax.clear()
            
            # 如果没有监控的设备，显示提示信息
            if not self.monitored_devices or not self.power_history:
                self.ax.text(0.5, 0.5, "等待数据收集...\n\n1. 在设备树中选择设备\n2. 勾选\"监控当前设备\"\n3. 启用自动计算功能\n4. 数据将实时显示", 
                             transform=self.ax.transAxes, ha='center', va='center', 
                             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7),
                             fontsize=12)
                self.ax.set_xlabel('时间 (秒)', fontsize=12)
                self.ax.set_ylabel('功率 (MW)', fontsize=12)
                self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
                self.canvas_mpl.draw()
                return
            
            all_powers = []
            
            # 获取所有设备的时间戳，找到最早的时间
            all_timestamps = []
            for device_key, history in self.power_history.items():
                if device_key in self.monitored_devices and history:
                    all_timestamps.extend([item[0] for item in history])
            
            if not all_timestamps:
                return
                
            start_time = min(all_timestamps)
            
            # 为每个监控的设备绘制曲线
            for device_key in self.monitored_devices:
                if device_key in self.power_history and self.power_history[device_key]:
                    history = self.power_history[device_key]
                    timestamps = [item[0] for item in history]
                    powers = [item[1] for item in history]
                    
                    # 转换为相对时间（秒）
                    relative_times = [t - start_time for t in timestamps]
                    
                    # 获取设备类型和ID
                    device_type, device_id = device_key.split('_', 1)
                    
                    # 使用预定义的颜色或生成新颜色
                    if device_key not in self.device_colors:
                        color_index = len(self.device_colors) % len(self.color_palette)
                        self.device_colors[device_key] = self.color_palette[color_index]
                    
                    color = self.device_colors[device_key]
                    
                    # 绘制功率曲线
                    self.ax.plot(relative_times, powers, color=color, linewidth=2,
                                label=f'{device_type} {device_id}')
                    
                    all_powers.extend(powers)
            
            # 设置图表属性
            self.ax.set_xlabel('时间 (秒)', fontsize=12)
            self.ax.set_ylabel('功率 (MW)', fontsize=12)
            self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
            self.ax.grid(True, alpha=0.3)
            
            # 自动调整Y轴范围
            if all_powers:
                min_power = min(all_powers)
                max_power = max(all_powers)
                padding = max((max_power - min_power) * 0.1, 0.1)
                self.ax.set_ylim(max(0, min_power - padding), max_power + padding)
            else:
                self.ax.set_ylim(0, 1)
            
            # 显示图例
            if len(self.monitored_devices) > 0:
                self.ax.legend()
            
            # 刷新图表
            self.canvas_mpl.draw()
            
        except Exception as e:
            self.ax.clear()
            self.ax.text(0.5, 0.5, f"显示功率曲线失败: {str(e)}", 
                         transform=self.ax.transAxes, ha='center', va='center', 
                         bbox=dict(boxstyle='round', facecolor='red', alpha=0.5))
            self.canvas_mpl.draw()
            print(f"显示功率曲线失败: {str(e)}")
    


    def toggle_auto_calculation(self, state):
        """切换自动潮流计算状态"""
        if state == 2: 
            if not self.network_model:
                QMessageBox.warning(self, "警告", "没有可用的网络模型")
                self.auto_calc_checkbox.setChecked(False)
                return
                
            interval = self.calc_interval_spinbox.value() * 1000  # 转换为毫秒
            self.auto_calc_timer.start(interval)
            self.is_auto_calculating = True
            self.statusBar().showMessage("自动潮流计算已启动")
        else:
            self.auto_calc_timer.stop()
            self.is_auto_calculating = False
            self.statusBar().showMessage("自动潮流计算已停止")
    
    def auto_power_flow_calculation(self):
        """自动潮流计算主方法"""
        try:
            if not self.network_model or not hasattr(self.network_model, 'net'):
                return
                
            for device in self.generated_devices:
                device_type, device_idx = device.split('_', 1)
                device_idx = int(device_idx)
                
                if device_type == 'load':
                    if device_idx in self.network_model.net.load.index:
                        load_data = self.data_generator_manager.generate_device_data('load', device_idx, self.network_model)
                        if device_idx in load_data:
                            load_values = load_data[device_idx]
                            self.network_model.net.load.loc[device_idx, 'p_mw'] = load_values['p_mw']
                            self.network_model.net.load.loc[device_idx, 'q_mvar'] = load_values['q_mvar']
                            
                elif device_type == 'sgen':
                    if device_idx in self.network_model.net.sgen.index:
                        sgen_data = self.data_generator_manager.generate_device_data('sgen', device_idx, self.network_model)
                        if device_idx in sgen_data:
                            sgen_values = sgen_data[device_idx]
                            self.network_model.net.sgen.loc[device_idx, 'p_mw'] = sgen_values['p_mw']
                            self.network_model.net.sgen.loc[device_idx, 'q_mvar'] = sgen_values['q_mvar']
            # 运行潮流计算
            try:
                pp.runpp(self.network_model.net)
                self.statusBar().showMessage("潮流计算成功")
                
                # 更新设备树状态
                self.update_device_tree_status()
                
                # 更新功率曲线（仅更新监控设备的数据，不再自动显示）
                self.update_power_curve()
                
                # 更新组件参数表格
                self.update_component_params_table()
                    
            except Exception as e:
                self.statusBar().showMessage(f"潮流计算失败: {str(e)}")
                
        except Exception as e:
            print(f"自动潮流计算错误: {str(e)}")
            self.statusBar().showMessage("自动潮流计算发生错误")
    
    def update_device_tree_status(self):
        """更新设备树状态"""
        try:
            if not hasattr(self.network_model.net, 'res_bus') or self.network_model.net.res_bus.empty:
                return
                
            # 遍历设备树并更新状态
            root = self.device_tree.invisibleRootItem()
            
            def update_item_status(item):
                data = item.data(0, Qt.UserRole)
                if data:
                    device_type, device_id = data
                    
                    try:
                        if device_type == 'bus' and hasattr(self.network_model.net, 'res_bus'):
                            if device_id in self.network_model.net.res_bus.index:
                                item.setText(2, "正常")
                        elif device_type == 'line' and hasattr(self.network_model.net, 'res_line'):
                            if device_id in self.network_model.net.res_line.index:
                                item.setText(2, "正常")
                        elif device_type == 'trafo' and hasattr(self.network_model.net, 'res_trafo'):
                            if device_id in self.network_model.net.res_trafo.index:
                                item.setText(2, "正常")
                        elif device_type == 'load' and hasattr(self.network_model.net, 'res_load'):
                            if device_id in self.network_model.net.res_load.index:
                                item.setText(2, "正常")
                        elif device_type == 'gen' and hasattr(self.network_model.net, 'res_gen'):
                            if device_id in self.network_model.net.res_gen.index:
                                item.setText(2, "正常")
                        elif device_type == 'sgen' and hasattr(self.network_model.net, 'res_sgen'):
                            if device_id in self.network_model.net.res_sgen.index:
                                item.setText(2, "正常")
                        elif device_type == 'ext_grid' and hasattr(self.network_model.net, 'res_ext_grid'):
                            if device_id in self.network_model.net.res_ext_grid.index:
                                item.setText(2, "正常")
                        elif device_type == 'storage' and hasattr(self.network_model.net, 'res_storage'):
                            if device_id in self.network_model.net.res_storage.index:
                                item.setText(2, "正常")
                    except:
                        item.setText(2, "异常")
                
                # 递归更新子项
                for i in range(item.childCount()):
                    update_item_status(item.child(i))
            
            # 更新所有根项
            for i in range(root.childCount()):
                update_item_status(root.child(i))
                
        except Exception as e:
            print(f"更新设备树状态失败: {str(e)}")

    def toggle_current_device_monitor(self, state):
        """切换当前设备监控状态"""
        if not self.selected_device_id or not self.selected_device_type:
            return
            
        device_key = f"{self.selected_device_type}_{self.selected_device_id}"
        
        if state == 2:  # 选中状态
            if device_key not in self.monitored_devices:
                self.monitored_devices.add(device_key)
                self.update_monitored_devices_list()
        else:  # 未选中状态
            if device_key in self.monitored_devices:
                self.monitored_devices.remove(device_key)
                self.update_monitored_devices_list()
                
        # 更新图表显示
        self.display_power_curve()
    
    def on_monitored_device_toggled(self, item, column):
        """监控设备列表中的复选框状态改变"""
        if column == 0:  # 第一列是复选框
            device_key = item.data(0, Qt.UserRole)
            if item.checkState(0) == Qt.Checked:
                if device_key not in self.monitored_devices:
                    self.monitored_devices.add(device_key)
            else:
                if device_key in self.monitored_devices:
                    self.monitored_devices.remove(device_key)
            
            # 更新当前设备监控复选框状态
            current_device_key = f"{self.selected_device_type}_{self.selected_device_id}" if self.selected_device_type and self.selected_device_id else ""
            if current_device_key:
                self.current_device_monitor.setChecked(current_device_key in self.monitored_devices)
            
            # 更新图表显示
            self.display_power_curve()
    
    def update_monitored_devices_list(self):
        """更新监控设备列表"""
        self.monitored_devices_list.clear()
        
        for device_key in self.monitored_devices:
            try:
                device_type, device_id = device_key.split('_', 1)
                
                # 创建列表项
                item = QTreeWidgetItem(self.monitored_devices_list)
                item.setText(0, str(device_id))
                item.setText(1, str(device_type))
                item.setText(2, "监控中")
                item.setData(0, Qt.UserRole, device_key)
                item.setCheckState(0, Qt.Checked)
                
            except Exception as e:
                print(f"更新监控设备列表失败: {str(e)}")
    
    def clear_all_monitors(self):
        """清除所有监控设备"""
        self.monitored_devices.clear()
        self.device_colors.clear()
        self.update_monitored_devices_list()
        
        # 更新当前设备监控复选框状态
        self.current_device_monitor.setChecked(False)
        
        # 更新图表显示
        self.display_power_curve()
        
    def on_sgen_mode_changed(self):
        """光伏设备数据生成模式改变时的回调"""
        is_manual = self.sgen_manual_mode_radio.isChecked()
        self.sgen_manual_panel.setVisible(is_manual)
        
        # 如果切换到手动模式，停止自动数据生成
        if is_manual and hasattr(self, 'sgen_enable_generation_checkbox'):
            if self.sgen_enable_generation_checkbox.isChecked():
                self.sgen_enable_generation_checkbox.setChecked(False)
        
        # 更新当前设备的功率值到滑块和输入框
        if is_manual:
            self.update_sgen_manual_controls_from_device()
    
    def on_load_mode_changed(self):
        """负载设备数据生成模式改变时的回调"""
        is_manual = self.load_manual_mode_radio.isChecked()
        self.load_manual_panel.setVisible(is_manual)
        
        # 如果切换到手动模式，停止自动数据生成
        if is_manual and hasattr(self, 'load_enable_generation_checkbox'):
            if self.load_enable_generation_checkbox.isChecked():
                self.load_enable_generation_checkbox.setChecked(False)
        
        # 更新当前设备的功率值到滑块和输入框
        if is_manual:
            self.update_load_manual_controls_from_device()
    
    def on_storage_mode_changed(self):
        """储能设备数据生成模式改变时的回调"""
        is_manual = self.storage_manual_mode_radio.isChecked()
        self.storage_manual_panel.setVisible(is_manual)
        
        # 更新当前设备的功率值到滑块和输入框
        if is_manual:
            self.update_storage_manual_controls_from_device()
    
    def on_generation_mode_changed(self):
        """数据生成模式改变时的回调（保留兼容性）"""
        is_manual = self.manual_mode_radio.isChecked()
        self.manual_control_panel.setVisible(is_manual)
        
        # 如果切换到手动模式，停止自动数据生成
        if is_manual and hasattr(self, 'enable_device_generation_checkbox'):
            if self.enable_device_generation_checkbox.isChecked():
                self.enable_device_generation_checkbox.setChecked(False)
        
        # 更新当前设备的功率值到滑块和输入框
        if is_manual:
            self.update_manual_controls_from_device()
    
    def update_sgen_manual_controls_from_device(self):
        """从当前光伏设备更新手动控制组件的值"""
        if not hasattr(self, 'current_component_type') or not hasattr(self, 'current_component_idx'):
            return
            
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
            
        if self.current_component_type != 'sgen':
            return
            
        try:
            # 获取光伏设备的当前功率值
            current_power = self.network_model.net.sgen.at[self.current_component_idx, 'p_mw']
            
            # 更新滑块和输入框的值
            if hasattr(self, 'sgen_manual_power_slider'):
                self.sgen_manual_power_slider.setValue(int(current_power * 1000))  # 转换为kW
            if hasattr(self, 'sgen_manual_power_spinbox'):
                self.sgen_manual_power_spinbox.setValue(current_power)
        except Exception as e:
            print(f"更新光伏设备手动控制值时出错: {e}")
    
    def update_load_manual_controls_from_device(self):
        """从当前负载设备更新手动控制组件的值"""
        if not hasattr(self, 'current_component_type') or not hasattr(self, 'current_component_idx'):
            return
            
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
            
        if self.current_component_type != 'load':
            return
            
        try:
            # 获取负载设备的当前功率值
            current_p = self.network_model.net.load.at[self.current_component_idx, 'p_mw']
            current_q = self.network_model.net.load.at[self.current_component_idx, 'q_mvar']
            
            # 更新滑块和输入框的值
            if hasattr(self, 'load_manual_power_slider'):
                self.load_manual_power_slider.setValue(int(current_p * 1000))  # 转换为kW
            if hasattr(self, 'load_manual_power_spinbox'):
                self.load_manual_power_spinbox.setValue(current_p)
            if hasattr(self, 'load_manual_reactive_power_slider'):
                self.load_manual_reactive_power_slider.setValue(int(current_q * 1000))  # 转换为kVar
            if hasattr(self, 'load_manual_reactive_power_spinbox'):
                self.load_manual_reactive_power_spinbox.setValue(current_q)
        except Exception as e:
            print(f"更新负载设备手动控制值时出错: {e}")
    
    def update_storage_manual_controls_from_device(self):
        """从当前储能设备更新手动控制组件的值"""
        if not hasattr(self, 'current_component_type') or not hasattr(self, 'current_component_idx'):
            return
            
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
            
        if self.current_component_type != 'storage':
            return
            
        try:
            # 获取储能设备的当前功率值
            current_power = self.network_model.net.storage.at[self.current_component_idx, 'p_mw']
            
            # 更新滑块和输入框的值
            if hasattr(self, 'storage_manual_power_slider'):
                self.storage_manual_power_slider.setValue(int(current_power * 1000))  # 转换为kW
            if hasattr(self, 'storage_manual_power_spinbox'):
                self.storage_manual_power_spinbox.setValue(current_power)
        except Exception as e:
            print(f"更新储能设备手动控制值时出错: {e}")
    
    def update_manual_controls_from_device(self):
        """从当前设备更新手动控制组件的值（保留兼容性）"""
        if not hasattr(self, 'current_component_type') or not hasattr(self, 'current_component_idx'):
            return
            
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
            
        component_type = self.current_component_type
        component_idx = self.current_component_idx
        
        try:
            if component_type == 'load':
                if component_idx < len(self.network_model.net.load):
                    p_mw = self.network_model.net.load.loc[component_idx, 'p_mw']
                    q_mvar = self.network_model.net.load.loc[component_idx, 'q_mvar']
                    
                    # 获取额定功率，如果不存在则使用默认值1.0
                    if 'p_mw_rated' in self.network_model.net.load.columns:
                        rated_power = self.network_model.net.load.loc[component_idx, 'p_mw_rated']
                        self.base_power_value = abs(rated_power) if rated_power != 0 else 1.0
                    else:
                        self.base_power_value = 1.0
                    
                    if 'q_mvar_rated' in self.network_model.net.load.columns:
                        rated_reactive = self.network_model.net.load.loc[component_idx, 'q_mvar_rated']
                        self.base_reactive_power_value = abs(rated_reactive) if rated_reactive != 0 else 0.5
                    else:
                        self.base_reactive_power_value = 0.5
                    
                    self.power_spinbox.setValue(abs(p_mw))
                    self.reactive_power_spinbox.setValue(abs(q_mvar))
                    
                    # 根据当前功率与额定功率的比例设置滑块值
                    power_percentage = int((abs(p_mw) / self.base_power_value) * 100) if self.base_power_value > 0 else 100
                    reactive_percentage = int((abs(q_mvar) / self.base_reactive_power_value) * 100) if self.base_reactive_power_value > 0 else 100
                    self.power_slider.setValue(max(0, min(200, power_percentage)))
                    self.reactive_power_slider.setValue(max(0, min(200, reactive_percentage)))
                    
                    # 显示无功功率控制
                    self.reactive_power_slider.setVisible(True)
                    self.reactive_power_spinbox.setVisible(True)
                    
            elif component_type == 'sgen':
                if component_idx < len(self.network_model.net.sgen):
                    p_mw = self.network_model.net.sgen.loc[component_idx, 'p_mw']
                    
                    # 获取额定功率，如果不存在则使用默认值1.0
                    if 'p_mw_rated' in self.network_model.net.sgen.columns:
                        rated_power = self.network_model.net.sgen.loc[component_idx, 'p_mw_rated']
                        self.base_power_value = abs(rated_power) if rated_power != 0 else 1.0
                    elif 'sn_mva' in self.network_model.net.sgen.columns:
                        # 如果有视在功率，使用它作为基准
                        sn_mva = self.network_model.net.sgen.loc[component_idx, 'sn_mva']
                        self.base_power_value = abs(sn_mva) if sn_mva != 0 else 1.0
                    else:
                        self.base_power_value = 1.0
                    
                    self.power_spinbox.setValue(abs(p_mw))  # 光伏功率通常为负值
                    
                    # 根据当前功率与额定功率的比例设置滑块值
                    power_percentage = int((abs(p_mw) / self.base_power_value) * 100) if self.base_power_value > 0 else 100
                    self.power_slider.setValue(max(0, min(200, power_percentage)))
                    
                    # 光伏设备隐藏无功功率控制
                    self.reactive_power_slider.setVisible(False)
                    self.reactive_power_spinbox.setVisible(False)
                    
            elif component_type == 'storage':
                if component_idx < len(self.network_model.net.storage):
                    p_mw = self.network_model.net.storage.loc[component_idx, 'p_mw']
                    
                    # 获取额定功率，如果不存在则使用默认值1.0
                    if 'max_p_mw' in self.network_model.net.storage.columns:
                        max_power = self.network_model.net.storage.loc[component_idx, 'max_p_mw']
                        self.base_power_value = abs(max_power) if max_power != 0 else 1.0
                    elif 'sn_mva' in self.network_model.net.storage.columns:
                        # 如果有视在功率，使用它作为基准
                        sn_mva = self.network_model.net.storage.loc[component_idx, 'sn_mva']
                        self.base_power_value = abs(sn_mva) if sn_mva != 0 else 1.0
                    else:
                        self.base_power_value = 1.0
                    
                    self.power_spinbox.setValue(abs(p_mw))  # 储能功率可正可负
                    
                    # 根据当前功率与额定功率的比例设置滑块值
                    power_percentage = int((abs(p_mw) / self.base_power_value) * 100) if self.base_power_value > 0 else 100
                    self.power_slider.setValue(max(0, min(200, power_percentage)))
                    
                    # 储能设备隐藏无功功率控制
                    self.reactive_power_slider.setVisible(False)
                    self.reactive_power_spinbox.setVisible(False)
            else:
                # 其他设备类型隐藏手动控制
                self.manual_control_panel.setVisible(False)
                return
                
        except Exception as e:
            print(f"更新手动控制值时出错: {e}")
    
    def on_manual_power_changed(self, value):
        """手动功率滑块改变时的回调"""
        # 将滑块值（0-200%）转换为实际功率值
        if hasattr(self, 'power_spinbox') and hasattr(self, 'base_power_value'):
            # 使用基准功率值计算实际功率
            new_power = self.base_power_value * (value / 100.0)
            # 暂时断开信号连接，避免循环调用
            self.power_spinbox.blockSignals(True)
            self.power_spinbox.setValue(new_power)
            self.power_spinbox.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_manual_power_spinbox_changed(self, value):
        """手动功率输入框改变时的回调"""
        # 根据输入框值更新滑块百分比
        if hasattr(self, 'power_slider') and hasattr(self, 'base_power_value') and self.base_power_value > 0:
            percentage = int((value / self.base_power_value) * 100)
            percentage = max(0, min(200, percentage))  # 限制在0-200%范围内
            self.power_slider.blockSignals(True)
            self.power_slider.setValue(percentage)
            self.power_slider.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_manual_reactive_power_changed(self, value):
        """手动无功功率滑块改变时的回调"""
        if hasattr(self, 'reactive_power_spinbox') and hasattr(self, 'base_reactive_power_value'):
            # 使用基准无功功率值计算实际功率
            new_power = self.base_reactive_power_value * (value / 100.0)
            self.reactive_power_spinbox.blockSignals(True)
            self.reactive_power_spinbox.setValue(new_power)
            self.reactive_power_spinbox.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_manual_reactive_power_spinbox_changed(self, value):
        """手动无功功率输入框改变时的回调"""
        if hasattr(self, 'reactive_power_slider') and hasattr(self, 'base_reactive_power_value') and self.base_reactive_power_value > 0:
            percentage = int((value / self.base_reactive_power_value) * 100)
            percentage = max(0, min(200, percentage))  # 限制在0-200%范围内
            self.reactive_power_slider.blockSignals(True)
            self.reactive_power_slider.setValue(percentage)
            self.reactive_power_slider.blockSignals(False)
            
            # 自动应用功率设置到设备
            self.apply_manual_power_settings()
    
    def on_sgen_power_changed(self, value):
        """光伏功率滑块改变时的回调"""
        if hasattr(self, 'sgen_power_spinbox'):
            # 滑块值直接对应功率值
            power_value = value / 10.0  # 滑块范围0-200对应0-20MW
            self.sgen_power_spinbox.blockSignals(True)
            self.sgen_power_spinbox.setValue(power_value)
            self.sgen_power_spinbox.blockSignals(False)
    
    def on_sgen_power_spinbox_changed(self, value):
        """光伏功率输入框改变时的回调"""
        if hasattr(self, 'sgen_power_slider'):
            # 功率值转换为滑块值
            slider_value = int(value * 10)  # 功率值*10对应滑块值
            slider_value = max(0, min(200, slider_value))
            self.sgen_power_slider.blockSignals(True)
            self.sgen_power_slider.setValue(slider_value)
            self.sgen_power_slider.blockSignals(False)
    
    def on_load_power_changed(self, value):
        """负载功率滑块改变时的回调"""
        if hasattr(self, 'load_power_spinbox'):
            # 滑块值直接对应功率值
            power_value = value / 2.0  # 滑块范围0-200对应0-100MW
            self.load_power_spinbox.blockSignals(True)
            self.load_power_spinbox.setValue(power_value)
            self.load_power_spinbox.blockSignals(False)
    
    def on_load_power_spinbox_changed(self, value):
        """负载功率输入框改变时的回调"""
        if hasattr(self, 'load_power_slider'):
            # 功率值转换为滑块值
            slider_value = int(value * 2)  # 功率值*2对应滑块值
            slider_value = max(0, min(200, slider_value))
            self.load_power_slider.blockSignals(True)
            self.load_power_slider.setValue(slider_value)
            self.load_power_slider.blockSignals(False)
    
    def on_load_reactive_power_changed(self, value):
        """负载无功功率滑块改变时的回调"""
        if hasattr(self, 'load_reactive_power_spinbox'):
            # 滑块值直接对应无功功率值
            power_value = value / 4.0  # 滑块范围0-200对应0-50MVar
            self.load_reactive_power_spinbox.blockSignals(True)
            self.load_reactive_power_spinbox.setValue(power_value)
            self.load_reactive_power_spinbox.blockSignals(False)
    
    def on_load_reactive_power_spinbox_changed(self, value):
        """负载无功功率输入框改变时的回调"""
        if hasattr(self, 'load_reactive_power_slider'):
            # 无功功率值转换为滑块值
            slider_value = int(value * 4)  # 功率值*4对应滑块值
            slider_value = max(0, min(200, slider_value))
            self.load_reactive_power_slider.blockSignals(True)
            self.load_reactive_power_slider.setValue(slider_value)
            self.load_reactive_power_slider.blockSignals(False)
    
    def on_storage_power_changed(self, value):
        """储能功率滑块改变时的回调"""
        if hasattr(self, 'storage_power_spinbox'):
            # 滑块值除以10得到实际功率值（MW）
            new_power = value / 10.0
            self.storage_power_spinbox.blockSignals(True)
            self.storage_power_spinbox.setValue(new_power)
            self.storage_power_spinbox.blockSignals(False)
    
    def on_storage_power_spinbox_changed(self, value):
        """储能功率输入框改变时的回调"""
        if hasattr(self, 'storage_power_slider'):
            # 功率值乘以10得到滑块值
            slider_value = int(value * 10)
            slider_value = max(-1000, min(1000, slider_value))
            self.storage_power_slider.blockSignals(True)
            self.storage_power_slider.setValue(slider_value)
            self.storage_power_slider.blockSignals(False)

    def apply_manual_power_settings(self):
        """应用手动功率设置到网络模型"""
        if not hasattr(self, 'current_component_type') or not hasattr(self, 'current_component_idx'):
            QMessageBox.warning(self, "警告", "请先选择一个设备")
            return
            
        if not self.network_model or not hasattr(self.network_model, 'net'):
            QMessageBox.warning(self, "警告", "网络模型未加载")
            return
            
        component_type = self.current_component_type
        component_idx = self.current_component_idx
        
        try:
            if component_type == 'load':
                if component_idx in self.network_model.net.load.index:
                    p_mw = self.power_spinbox.value()
                    q_mvar = self.reactive_power_spinbox.value()
                    
                    self.network_model.net.load.loc[component_idx, 'p_mw'] = p_mw
                    self.network_model.net.load.loc[component_idx, 'q_mvar'] = q_mvar
                    
                    # 更新设备树显示
                    self.update_device_tree_status()
                    
                    # 如果启用了自动计算，执行潮流计算
                    if hasattr(self, 'auto_calc_checkbox') and self.auto_calc_checkbox.isChecked():
                        self.auto_power_flow_calculation()
                    
                    self.statusBar().showMessage(f"已更新负载 {component_idx} 的功率设置")
                    
            elif component_type == 'sgen':
                if component_idx in self.network_model.net.sgen.index:
                    p_mw = -abs(self.power_spinbox.value())  # 光伏功率为负值
                    
                    self.network_model.net.sgen.loc[component_idx, 'p_mw'] = p_mw
                    
                    # 更新设备树显示
                    self.update_device_tree_status()
                    
                    # 如果启用了自动计算，执行潮流计算
                    if hasattr(self, 'auto_calc_checkbox') and self.auto_calc_checkbox.isChecked():
                        self.auto_power_flow_calculation()
                    
                    self.statusBar().showMessage(f"已更新光伏 {component_idx} 的功率设置")
                    
            elif component_type == 'storage':
                if component_idx in self.network_model.net.storage.index:
                    p_mw = self.power_spinbox.value()  # 储能功率可正可负
                    
                    self.network_model.net.storage.loc[component_idx, 'p_mw'] = p_mw
                    
                    # 更新设备树显示
                    self.update_device_tree_status()
                    
                    # 如果启用了自动计算，执行潮流计算
                    if hasattr(self, 'auto_calc_checkbox') and self.auto_calc_checkbox.isChecked():
                        self.auto_power_flow_calculation()
                    
                    self.statusBar().showMessage(f"已更新储能 {component_idx} 的功率设置")
            else:
                QMessageBox.warning(self, "警告", "当前设备不支持手动功率控制")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用手动设置时出错: {e}")

    def apply_sgen_settings(self):
        """应用光伏设备的手动功率设置"""
        if not hasattr(self, 'current_component_type') or not hasattr(self, 'current_component_idx'):
            QMessageBox.warning(self, "警告", "请先选择一个光伏设备")
            return
            
        if not self.network_model or not hasattr(self.network_model, 'net'):
            QMessageBox.warning(self, "警告", "网络模型未加载")
            return
            
        component_idx = self.current_component_idx
        
        try:
            if component_idx in self.network_model.net.sgen.index:
                p_mw = -abs(self.sgen_power_spinbox.value())  # 光伏功率为负值
                
                self.network_model.net.sgen.loc[component_idx, 'p_mw'] = p_mw
                
                # 更新设备树显示
                self.update_device_tree_status()
                
                # 如果启用了自动计算，执行潮流计算
                if hasattr(self, 'auto_calc_checkbox') and self.auto_calc_checkbox.isChecked():
                    self.auto_power_flow_calculation()
                
                self.statusBar().showMessage(f"已更新光伏 {component_idx} 的功率设置")
            else:
                QMessageBox.warning(self, "警告", "光伏设备不存在")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用光伏设置时出错: {e}")
    
    def apply_load_settings(self):
        """应用负载设备的手动功率设置"""
        if not hasattr(self, 'current_component_type') or not hasattr(self, 'current_component_idx'):
            QMessageBox.warning(self, "警告", "请先选择一个负载设备")
            return
            
        if not self.network_model or not hasattr(self.network_model, 'net'):
            QMessageBox.warning(self, "警告", "网络模型未加载")
            return
            
        component_idx = self.current_component_idx
        
        try:
            if component_idx in self.network_model.net.load.index:
                p_mw = self.load_power_spinbox.value()
                q_mvar = self.load_reactive_power_spinbox.value()
                
                self.network_model.net.load.loc[component_idx, 'p_mw'] = p_mw
                self.network_model.net.load.loc[component_idx, 'q_mvar'] = q_mvar
                
                # 更新设备树显示
                self.update_device_tree_status()
                
                # 如果启用了自动计算，执行潮流计算
                if hasattr(self, 'auto_calc_checkbox') and self.auto_calc_checkbox.isChecked():
                    self.auto_power_flow_calculation()
                
                self.statusBar().showMessage(f"已更新负载 {component_idx} 的功率设置")
            else:
                QMessageBox.warning(self, "警告", "负载设备不存在")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用负载设置时出错: {e}")
    
    def apply_storage_settings(self):
        """应用储能设备的手动功率设置"""
        if not hasattr(self, 'current_component_type') or not hasattr(self, 'current_component_idx'):
            QMessageBox.warning(self, "警告", "请先选择一个储能设备")
            return
            
        if not self.network_model or not hasattr(self.network_model, 'net'):
            QMessageBox.warning(self, "警告", "网络模型未加载")
            return
            
        component_idx = self.current_component_idx
        
        try:
            if component_idx in self.network_model.net.storage.index:
                p_mw = self.storage_power_spinbox.value()  # 储能功率可正可负
                
                self.network_model.net.storage.loc[component_idx, 'p_mw'] = p_mw
                
                # 更新设备树显示
                self.update_device_tree_status()
                
                # 如果启用了自动计算，执行潮流计算
                if hasattr(self, 'auto_calc_checkbox') and self.auto_calc_checkbox.isChecked():
                    self.auto_power_flow_calculation()
                
                self.statusBar().showMessage(f"已更新储能 {component_idx} 的功率设置")
            else:
                QMessageBox.warning(self, "警告", "储能设备不存在")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用储能设置时出错: {e}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止自动计算定时器
        self.auto_calc_timer.stop()
        super().closeEvent(event)