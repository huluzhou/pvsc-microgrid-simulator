#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI组件管理模块
负责管理仿真窗口的UI组件创建和主题更新
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QLabel, QGroupBox, QPushButton, 
    QCheckBox, QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, 
    QLineEdit, QComboBox, QFormLayout, QDoubleSpinBox, QSlider,
    QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
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
        self.parent_window.category_combo.addItems(["全部设备", "母线", "线路", "变压器", "发电设备", "负载设备", "储能设备"])
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
        auto_group = QGroupBox("自动计算")
        auto_group.setMinimumHeight(100)  # 设置最小高度确保显示完整
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setContentsMargins(10, 10, 10, 10)  # 设置内边距
        auto_layout.setSpacing(8)  # 设置控件间距
        
        # 自动计算开关
        auto_calc_layout = QHBoxLayout()
        self.parent_window.auto_calc_checkbox = QCheckBox("启用自动潮流计算")
        self.parent_window.auto_calc_checkbox.stateChanged.connect(self.parent_window.toggle_auto_calculation)
        auto_calc_layout.addWidget(self.parent_window.auto_calc_checkbox)
        auto_calc_layout.addStretch()  # 添加弹性空间
        auto_layout.addLayout(auto_calc_layout)
        
        # 计算间隔设置
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("计算间隔:"))
        self.parent_window.calc_interval_spinbox = QSpinBox()
        self.parent_window.calc_interval_spinbox.setRange(1, 60)
        self.parent_window.calc_interval_spinbox.setValue(2)
        self.parent_window.calc_interval_spinbox.setSuffix(" 秒")
        self.parent_window.calc_interval_spinbox.setMaximumWidth(120)  # 设置最大宽度
        interval_layout.addWidget(self.parent_window.calc_interval_spinbox)
        interval_layout.addStretch()  # 添加弹性空间
        auto_layout.addLayout(interval_layout)
        
        parent_layout.addWidget(auto_group)
        
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
        self.parent_window.figure = Figure(figsize=(8, 5), dpi=100, tight_layout=True)
        self.parent_window.canvas_mpl = FigureCanvas(self.parent_window.figure)
        self.parent_window.canvas_mpl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.parent_window.ax = self.parent_window.figure.add_subplot(111)
        
        # 设置中文字体
        try:
            # 尝试设置支持中文的字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'SimSun', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        except:
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
        self.parent_window.toolbar = NavigationToolbar(self.parent_window.canvas_mpl, self.parent_window)
        
        curve_layout.addWidget(self.parent_window.toolbar)
        curve_layout.addWidget(self.parent_window.canvas_mpl, 1)  # 设置stretch因子为1，让图表区域扩展
        
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
        
        # 创建控制面板容器
        control_container = QWidget()
        control_layout = QVBoxLayout(control_container)
        
        # 功率曲线监控控制面板
        self.create_monitor_control_panel(control_layout)
        
        layout.addWidget(control_container)
        
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
        
    def update_theme_colors(self):
        """更新主题相关的所有颜色"""
        app = QApplication.instance()
        if app:
            palette = app.palette()
            bg_color = palette.color(QPalette.Window)
            is_dark_theme = bg_color.lightness() < 128
            
            # 更新自动计算控件的样式
            if hasattr(self.parent_window, 'auto_calc_checkbox'):
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
                            border: 2px solid #ccc;
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
                self.parent_window.auto_calc_checkbox.setStyleSheet(checkbox_style)
                
            # 更新SpinBox样式
            if hasattr(self.parent_window, 'calc_interval_spinbox'):
                if is_dark_theme:
                    spinbox_style = """
                        QSpinBox {
                            background-color: rgb(53, 53, 53);
                            color: rgb(255, 255, 255);
                            border: 2px solid #666;
                            border-radius: 4px;
                            padding: 2px;
                        }
                        QSpinBox::up-button, QSpinBox::down-button {
                            background-color: rgb(70, 70, 70);
                            border: 1px solid #888;
                        }
                        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                            background-color: rgb(90, 90, 90);
                        }
                    """
                else:
                    spinbox_style = """
                        QSpinBox {
                            background-color: white;
                            color: rgb(0, 0, 0);
                            border: 2px solid #ccc;
                            border-radius: 4px;
                            padding: 2px;
                        }
                        QSpinBox::up-button, QSpinBox::down-button {
                            background-color: rgb(240, 240, 240);
                            border: 1px solid #ccc;
                        }
                        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                            background-color: rgb(220, 220, 220);
                        }
                    """
                self.parent_window.calc_interval_spinbox.setStyleSheet(spinbox_style)
            
            # 更新设备树样式
            if hasattr(self.parent_window, 'device_tree'):
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
                self.parent_window.device_tree.setStyleSheet(tree_style)
            
            # 更新监控设备列表样式
            if hasattr(self.parent_window, 'monitored_devices_list'):
                self.parent_window.monitored_devices_list.setStyleSheet(tree_style if hasattr(self.parent_window, 'device_tree') else "")