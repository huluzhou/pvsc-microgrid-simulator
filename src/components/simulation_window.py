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
    QSizePolicy, QApplication
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
        
        # 组件详情选项卡（仅保留此选项卡）
        self.component_details_tab = QWidget()
        self.create_component_details_tab()
        self.results_tabs.addTab(self.component_details_tab, "组件详情")
        
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
        
    def create_data_generation_panel(self, parent_layout):
        """创建数据生成控制面板"""
        # 创建数据生成控制组
        data_group = QGroupBox("数据生成控制")
        data_layout = QVBoxLayout(data_group)
        
        # 负载变化幅度
        variation_layout = QHBoxLayout()
        variation_layout.addWidget(QLabel("变化幅度(%)"))
        self.variation_spinbox = QSpinBox()
        self.variation_spinbox.setRange(5, 50)
        self.variation_spinbox.setValue(20)
        data_layout.addLayout(variation_layout)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.start_generation_btn = QPushButton("开始生成")
        self.start_generation_btn.clicked.connect(self.start_load_data_generation)
        button_layout.addWidget(self.start_generation_btn)
        
        self.stop_generation_btn = QPushButton("停止生成")
        self.stop_generation_btn.clicked.connect(self.stop_load_data_generation)
        button_layout.addWidget(self.stop_generation_btn)
        
        data_layout.addLayout(button_layout)
        
        parent_layout.addWidget(data_group)
        
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
        
        # 数据生成控制面板
        self.create_data_generation_panel(control_layout)
        
        layout.addWidget(control_container)
        
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
                
        # 添加静态发电机
        if not self.network_model.net.sgen.empty:
            sgen_root = QTreeWidgetItem(self.device_tree, ["静态发电机", "分类", "-"])
            for idx, sgen in self.network_model.net.sgen.iterrows():
                sgen_name = sgen.get('name', f'SGen_{idx}')
                status = "正常" if hasattr(self.network_model.net, 'res_sgen') and not self.network_model.net.res_sgen.empty and idx in self.network_model.net.res_sgen.index else "未计算"
                sgen_item = QTreeWidgetItem(sgen_root, [f"SGen {idx}: {sgen_name}", "静态发电机", status])
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
            
        # 记录当前显示的组件信息，用于自动更新
        self.current_component_type = component_type
        self.current_component_idx = component_idx
            
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
            
            # 添加组件参数
            for param, value in component_data.items():
                all_params[f"参数_{param}"] = value
                
            # 添加仿真结果
            if result_data is not None:
                for param, value in result_data.items():
                    all_params[f"结果_{param}"] = value
            
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
        被包含在数据生成范围内。支持负载(load)和静态发电机(sgen)设备。
        
        Args:
            component_type (str): 组件类型 ('load', 'sgen')
            component_idx (int): 组件索引ID
        """
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
        
        # 只支持负载和静态发电机
        if component_type not in ['load', 'sgen']:
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
                    self.statusBar().showMessage(f"静态发电机设备 {component_idx} 不存在")
                    return

            # 检查设备是否已存在于监控列表中
            if device_key not in self.generated_devices:
                # 将设备添加到监控设备集合
                self.generated_devices.add(device_key)
                
                # 启动对应的数据生成器
                self.data_generator_manager.start_generation(component_type)
                
                # 显示成功消息
                device_name = "负载" if component_type == "load" else "光伏"
                self.statusBar().showMessage(f"已将{device_name}设备 {component_idx} 标记为数据生成设备")
                
            else:
                # 设备已存在，显示提示信息
                device_name = "负载" if component_type == "load" else "光伏"
                self.statusBar().showMessage(f"{device_name}设备 {component_idx} 已在数据生成列表中")
                
        except Exception as e:
            self.statusBar().showMessage(f"标记设备数据生成时出错: {str(e)}")
            print(f"Error in enable_device_data_generation: {str(e)}")
    
    def get_component_type_chinese(self, component_type):
        """获取组件类型的中文名称"""
        type_map = {
            'bus': '母线',
            'line': '线路', 
            'trafo': '变压器',
            'load': '负载',
            'gen': '发电机',
            'sgen': '静态发电机',
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
            "发电设备": ["发电机", "静态发电机", "外部电网"],
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
            "静态发电机": len(self.network_model.net.sgen),
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
                    '组件类型': ['母线', '线路', '变压器', '负载', '发电机', '静态发电机', '外部电网', '储能'],
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
                    
            elif device_type == "静态发电机":
                # 从静态发电机潮流计算结果中获取实际功率
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
        
    def start_load_data_generation(self):
        """开始数据生成"""
        self.data_generator_manager.start_generation()
        self.start_generation_btn.setEnabled(False)
        self.stop_generation_btn.setEnabled(True)
        
    def stop_load_data_generation(self):
        """停止数据生成"""
        self.data_generator_manager.stop_generation()
        self.start_generation_btn.setEnabled(True)
        self.stop_generation_btn.setEnabled(False)
        self.parent_window.statusBar().showMessage("已停止数据生成")
        
    def generate_and_update_load_data(self):
        """生成并更新负载数据"""
        if not self.network_model or not hasattr(self.network_model, 'net'):
            return
            
        # 生成新的负载数据
        new_load_data = self.data_generator_manager.load_generator.generate_daily_load_profile(self.network_model)
        
        if new_load_data:
            # 更新网络模型中的负载数据
            for idx, load_data in new_load_data.items():
                if idx < len(self.network_model.net.load):
                    self.network_model.net.load.loc[idx, 'p_mw'] = load_data['p_mw']
                    self.network_model.net.load.loc[idx, 'q_mvar'] = load_data['q_mvar']
            
            # 更新设备树显示
            self.update_device_tree_status()
            
            # 如果启用了自动计算，执行潮流计算
            if hasattr(self, 'auto_calc_checkbox') and self.auto_calc_checkbox.isChecked():
                self.auto_power_flow_calculation()
            
            self.parent_window.statusBar().showMessage(
                f"已更新负载数据 - 更新于 {datetime.now().strftime('%H:%M:%S')}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止自动计算定时器
        self.auto_calc_timer.stop()
        super().closeEvent(event)