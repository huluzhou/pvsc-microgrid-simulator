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
    QTabWidget, QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QFont, QBrush, QColor
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

class LoadDataGenerator:
    """负载数据生成器"""
    
    def __init__(self):
        self.base_loads = {}
        self.load_profiles = {}
        
    def generate_load_data(self, network_model):
        """生成负载数据
        
        Args:
            network_model: 网络模型
            
        Returns:
            dict: 负载数据字典
        """
        if not network_model or not hasattr(network_model, 'net'):
            return {}
            
        load_data = {}
        
        # 获取所有负载
        if not network_model.net.load.empty:
            for idx, load in network_model.net.load.iterrows():
                # 基础负载值
                base_p = load.get('p_mw', 1.0)
                base_q = load.get('q_mvar', 0.5)
                
                # 生成随机负载变化（±20%范围内）
                variation = np.random.uniform(0.8, 1.2)
                new_p = base_p * variation
                new_q = base_q * variation
                
                load_data[idx] = {
                    'p_mw': new_p,
                    'q_mvar': new_q,
                    'name': load.get('name', f'Load_{idx}')
                }
        
        return load_data
    
    def generate_daily_load_profile(self, network_model):
        """生成日负载曲线数据
        
        Args:
            network_model: 网络模型
            
        Returns:
            dict: 日负载曲线数据
        """
        if not network_model or not hasattr(network_model, 'net'):
            return {}
            
        load_profiles = {}
        
        # 24小时负载曲线模板（基于典型日负载模式）
        daily_pattern = [
            0.6, 0.5, 0.4, 0.3, 0.3, 0.4,  # 0-5时
            0.5, 0.7, 0.8, 0.9, 0.95, 1.0,  # 6-11时
            1.0, 0.95, 0.9, 0.85, 0.9, 1.0,  # 12-17时
            1.1, 1.2, 1.1, 0.9, 0.8, 0.7   # 18-23时
        ]
        
        if not network_model.net.load.empty:
            for idx, load in network_model.net.load.iterrows():
                base_p = load.get('p_mw', 1.0)
                base_q = load.get('q_mvar', 0.5)
                
                # 根据当前时间选择负载值
                current_hour = datetime.now().hour
                pattern_index = current_hour % 24
                multiplier = daily_pattern[pattern_index] * np.random.uniform(0.9, 1.1)
                
                load_profiles[idx] = {
                    'p_mw': base_p * multiplier,
                    'q_mvar': base_q * multiplier,
                    'hour': current_hour,
                    'multiplier': multiplier
                }
        
        return load_profiles


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
        self.power_history = deque(maxlen=100)  # 存储功率历史数据
        self.selected_device_id = None
        self.selected_device_type = None
        
        # 负载数据生成相关
        self.load_data_generator = LoadDataGenerator()
        self.current_load_index = 0
        
        self.init_ui()
        self.load_network_data()
        self.update_device_combo()
        
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
        
        # 创建中央滚动图像区域
        self.create_central_image_area(splitter)
        
        # 创建右侧仿真结果面板
        self.create_simulation_results_panel(splitter)
        
        # 设置分割器比例
        splitter.setSizes([250, 600, 350])
        
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
        
        # 删除仿真控制按钮（潮流计算和短路分析功能已移除）
        
        # 导出按钮组
        export_group = QGroupBox("结果导出")
        export_layout = QHBoxLayout(export_group)
        
        self.export_csv_btn = QPushButton("导出CSV")
        self.export_csv_btn.clicked.connect(self.export_results_csv)
        self.export_csv_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 6px; }")
        export_layout.addWidget(self.export_csv_btn)
        
        self.export_excel_btn = QPushButton("导出Excel")
        self.export_excel_btn.clicked.connect(self.export_results_excel)
        self.export_excel_btn.setStyleSheet("QPushButton { background-color: #009688; color: white; font-weight: bold; padding: 6px; }")
        export_layout.addWidget(self.export_excel_btn)
        
        # 自动计算控制面板
        auto_group = QGroupBox("自动计算")
        auto_layout = QVBoxLayout(auto_group)
        
        # 自动计算开关
        auto_calc_layout = QHBoxLayout()
        auto_calc_layout.addWidget(QLabel("自动计算:"))
        self.auto_calc_checkbox = QCheckBox()
        self.auto_calc_checkbox.stateChanged.connect(self.toggle_auto_calculation)
        auto_calc_layout.addWidget(self.auto_calc_checkbox)
        auto_layout.addLayout(auto_calc_layout)
        
        # 计算间隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("间隔(秒):"))
        self.calc_interval_spinbox = QSpinBox()
        self.calc_interval_spinbox.setRange(1, 60)
        self.calc_interval_spinbox.setValue(5)
        interval_layout.addWidget(self.calc_interval_spinbox)
        auto_layout.addLayout(interval_layout)
        
        # 负载数据生成开关
        load_data_layout = QHBoxLayout()
        load_data_layout.addWidget(QLabel("生成负载数据:"))
        self.load_data_checkbox = QCheckBox()
        self.load_data_checkbox.setChecked(True)
        load_data_layout.addWidget(self.load_data_checkbox)
        auto_layout.addLayout(load_data_layout)
        
        # 功率曲线显示开关
        curve_layout = QHBoxLayout()
        curve_layout.addWidget(QLabel("显示功率曲线:"))
        self.show_curve_checkbox = QCheckBox()
        self.show_curve_checkbox.setChecked(True)
        curve_layout.addWidget(self.show_curve_checkbox)
        auto_layout.addLayout(curve_layout)
        
        # 选择设备下拉框
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("监控设备:"))
        self.device_combo = QComboBox()
        self.device_combo.currentTextChanged.connect(self.on_device_selection_changed)
        device_layout.addWidget(self.device_combo)
        auto_layout.addLayout(device_layout)
        
        tree_layout.addWidget(auto_group)
        
        parent.addWidget(tree_widget)
        
    def create_central_image_area(self, parent):
        """创建中央功率曲线显示区域"""
        # 创建功率曲线容器
        curve_widget = QWidget()
        curve_layout = QVBoxLayout(curve_widget)
        
        # 标题
        curve_title = QLabel("功率曲线监控")
        curve_title.setFont(QFont("Arial", 12, QFont.Bold))
        curve_layout.addWidget(curve_title)
        
        # 创建功率曲线显示区域 - 使用matplotlib交互式图表
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas_mpl = FigureCanvas(self.figure)
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
        curve_layout.addWidget(self.canvas_mpl)
        
        # 创建控制按钮区域
        control_layout = QHBoxLayout()
        
        self.refresh_curve_btn = QPushButton("刷新曲线")
        self.refresh_curve_btn.clicked.connect(self.refresh_power_curve)
        self.refresh_curve_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.refresh_curve_btn)
        
        self.clear_curve_btn = QPushButton("清空历史")
        self.clear_curve_btn.clicked.connect(self.clear_power_history)
        self.clear_curve_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.clear_curve_btn)
        
        self.show_topology_btn = QPushButton("显示拓扑")
        self.show_topology_btn.clicked.connect(self.show_topology_image)
        self.show_topology_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.show_topology_btn)
        
        curve_layout.addLayout(control_layout)
        
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
        
    def create_component_details_tab(self):
        """创建组件详情选项卡"""
        layout = QVBoxLayout(self.component_details_tab)
        
        # 组件信息显示
        self.component_info = QTextEdit()
        self.component_info.setReadOnly(True)
        self.component_info.setMaximumHeight(200)
        layout.addWidget(self.component_info)
        
        # 组件参数表格
        self.component_params_table = QTableWidget()
        self.component_params_table.setColumnCount(2)
        self.component_params_table.setHorizontalHeaderLabels(["参数", "值"])
        self.component_params_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.component_params_table)
        
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
        self.show_component_details(component_type, component_idx)
        
    def show_component_details(self, component_type, component_idx):
        """显示组件详细信息"""
        if not self.network_model:
            return
            
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
                
            # 显示组件基本信息
            info_text = f"组件类型: {self.get_component_type_chinese(component_type)}\n"
            info_text += f"组件索引: {component_idx}\n"
            info_text += f"组件名称: {component_data.get('name', 'N/A')}\n"
            
            # 添加工作状态信息
            if result_data is not None:
                info_text += "\n=== 仿真结果 ===\n"
                if component_type == 'bus':
                    info_text += f"电压幅值: {result_data.get('vm_pu', 'N/A'):.4f} p.u.\n"
                    info_text += f"电压角度: {result_data.get('va_degree', 'N/A'):.2f}°\n"
                elif component_type in ['line', 'trafo']:
                    info_text += f"有功功率(from): {result_data.get('p_from_mw', 'N/A'):.3f} MW\n"
                    info_text += f"无功功率(from): {result_data.get('q_from_mvar', 'N/A'):.3f} MVar\n"
                    info_text += f"有功功率(to): {result_data.get('p_to_mw', 'N/A'):.3f} MW\n"
                    info_text += f"无功功率(to): {result_data.get('q_to_mvar', 'N/A'):.3f} MVar\n"
                    if 'loading_percent' in result_data:
                        info_text += f"负载率: {result_data['loading_percent']:.1f}%\n"
                elif component_type in ['load', 'gen', 'sgen', 'ext_grid', 'storage']:
                    info_text += f"有功功率: {result_data.get('p_mw', 'N/A'):.3f} MW\n"
                    info_text += f"无功功率: {result_data.get('q_mvar', 'N/A'):.3f} MVar\n"
            else:
                info_text += "\n仿真结果: 未运行潮流计算\n"
                
            self.component_info.setText(info_text)
            
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
            self.component_info.setText(f"显示组件详情时出错: {str(e)}")
    
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
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.auto_calc_timer.stop()
        self.parent_window.statusBar().showMessage("已退出仿真模式")
        event.accept()
    
    # 删除自动潮流计算方法（潮流计算功能已移除）
    
    # 删除自动潮流计算方法
    
    def update_device_combo(self):
        """更新设备选择下拉框"""
        if not self.network_model:
            return
            
        self.device_combo.clear()
        self.device_combo.addItem("-- 选择设备 --")
        
        # 添加所有可监控的设备
        device_list = []
        
        # 母线
        if not self.network_model.net.bus.empty:
            for idx, bus in self.network_model.net.bus.iterrows():
                name = bus.get('name', f'Bus_{idx}')
                device_list.append(f"母线-{name}-{idx}")
        
        # 线路
        if not self.network_model.net.line.empty:
            for idx, line in self.network_model.net.line.iterrows():
                name = line.get('name', f'Line_{idx}')
                device_list.append(f"线路-{name}-{idx}")
        
        # 变压器
        if not self.network_model.net.trafo.empty:
            for idx, trafo in self.network_model.net.trafo.iterrows():
                name = trafo.get('name', f'Trafo_{idx}')
                device_list.append(f"变压器-{name}-{idx}")
        
        # 发电机
        if not self.network_model.net.gen.empty:
            for idx, gen in self.network_model.net.gen.iterrows():
                name = gen.get('name', f'Gen_{idx}')
                device_list.append(f"发电机-{name}-{idx}")
        
        # 负载
        if not self.network_model.net.load.empty:
            for idx, load in self.network_model.net.load.iterrows():
                name = load.get('name', f'Load_{idx}')
                device_list.append(f"负载-{name}-{idx}")
        
        # 排序并添加到下拉框
        device_list.sort()
        for device in device_list:
            self.device_combo.addItem(device)
    
    def on_device_selection_changed(self, text):
        """设备选择变更处理"""
        if not text or text == "-- 选择设备 --":
            self.selected_device_id = None
            self.selected_device_type = None
            return
        
        try:
            parts = text.split('-', 2)
            if len(parts) >= 3:
                self.selected_device_type = parts[0]
                self.selected_device_id = int(parts[2])
                
                # 清空历史数据
                self.power_history.clear()
                
                # 如果自动计算已启动，立即更新一次
                if self.is_auto_calculating:
                    self.update_power_curve()
                    
        except Exception as e:
            self.selected_device_id = None
            self.selected_device_type = None
    
    def update_power_curve(self):
        """更新功率曲线显示"""
        if self.selected_device_id is None or self.selected_device_type is None:
            return
            
        try:
            # 获取当前功率值
            power_value = self.get_device_power(self.selected_device_id, self.selected_device_type)
            
            if power_value is not None:
                # 添加历史数据
                timestamp = time.time()
                self.power_history.append((timestamp, power_value))
                
                # 更新图像显示
                self.display_power_curve()
                
        except Exception as e:
            print(f"更新功率曲线失败: {str(e)}")
    
    def get_device_power(self, device_id, device_type):
        """获取设备的实际功率属性值"""
        try:
            # 根据设备类型从实际属性中获取功率值
            if device_type == "母线":
                # 母线本身不直接设置功率，但可以通过潮流计算结果获取总注入功率
                if hasattr(self.network_model.net, 'res_bus') and device_id in self.network_model.net.res_bus.index:
                    # 获取该母线的总注入功率（发电减负荷）
                    return abs(self.network_model.net.res_bus.loc[device_id, 'p_mw'])
                else:
                    return 0.0
                
            elif device_type == "线路":
                # 从线路属性中获取功率（如果有的话）
                lines = self.network_model.net.line
                if device_id in lines.index and 'p_mw' in lines.columns:
                    return abs(lines.loc[device_id, 'p_mw'])
                else:
                    # 如果没有功率属性，返回额定容量的百分比
                    if device_id in lines.index:
                        max_power = lines.loc[device_id, 'max_i_ka'] * lines.loc[device_id, 'vn_kv'] * 1.732  # 近似最大功率
                        return max_power * 0.6  # 返回60%作为示例
                    
            elif device_type == "变压器":
                # 从变压器属性中获取功率
                trafos = self.network_model.net.trafo
                if device_id in trafos.index and 'p_mw' in trafos.columns:
                    return abs(trafos.loc[device_id, 'p_mw'])
                else:
                    # 如果没有功率属性，返回额定容量的百分比
                    if device_id in trafos.index:
                        rated_power = trafos.loc[device_id, 'sn_mva']
                        return rated_power * 0.7  # 返回70%负载作为示例
                    
            elif device_type == "发电机":
                # 从发电机属性中获取实际功率设置
                gens = self.network_model.net.gen
                if device_id in gens.index:
                    return abs(gens.loc[device_id, 'p_mw'])
                    
            elif device_type == "静态发电机":
                # 从静态发电机属性中获取实际功率设置
                sgens = self.network_model.net.sgen
                if device_id in sgens.index:
                    return abs(sgens.loc[device_id, 'p_mw'])
                    
            elif device_type == "负载":
                # 从负载属性中获取实际功率设置
                loads = self.network_model.net.load
                if device_id in loads.index:
                    return abs(loads.loc[device_id, 'p_mw'])
                    
            elif device_type == "储能":
                # 从储能属性中获取实际功率设置
                storage = self.network_model.net.storage
                if device_id in storage.index:
                    return abs(storage.loc[device_id, 'p_mw'])
                    
            elif device_type == "外部电网":
                # 从外部电网属性中获取功率
                ext_grids = self.network_model.net.ext_grid
                # 外部电网通常作为平衡节点，功率由系统决定
                # 在pandapower中，外部电网的功率通常通过潮流计算结果获取
                if hasattr(self.network_model.net, 'res_ext_grid') and device_id in self.network_model.net.res_ext_grid.index:
                    return abs(self.network_model.net.res_ext_grid.loc[device_id, 'p_mw'])
                else:
                    return 0.0
                    
        except Exception as e:
            print(f"获取设备功率失败: {str(e)}")
        
        return 0.0
    
    def display_power_curve(self):
        """显示功率曲线 - 使用交互式图表"""
        try:
            if not self.selected_device_id or not self.selected_device_type:
                return
                
            if len(self.power_history) < 2:
                # 显示初始提示
                self.ax.clear()
                self.ax.text(0.5, 0.5, "等待数据收集...\n\n1. 选择要监控的设备\n2. 启用自动计算功能\n3. 数据将实时显示", 
                             transform=self.ax.transAxes, ha='center', va='center', 
                             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7),
                             fontsize=12)
                self.ax.set_xlabel('时间 (秒)', fontsize=12)
                self.ax.set_ylabel('功率 (MW)', fontsize=12)
                self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
                self.canvas_mpl.draw()
                return
                
            # 提取时间和功率数据
            timestamps = [item[0] for item in self.power_history]
            powers = [item[1] for item in self.power_history]
            
            # 转换为相对时间（秒）
            start_time = timestamps[0]
            relative_times = [t - start_time for t in timestamps]
            
            # 清空当前图表
            self.ax.clear()
            
            # 绘制功率曲线
            self.ax.plot(relative_times, powers, 'b-', linewidth=2, 
                        label=f'{self.selected_device_type} {self.selected_device_id}')
            self.ax.set_xlabel('时间 (秒)', fontsize=12)
            self.ax.set_ylabel('功率 (MW)', fontsize=12)
            self.ax.set_title(f'{self.selected_device_type} {self.selected_device_id} 功率曲线', 
                            fontsize=14, fontweight='bold')
            self.ax.grid(True, alpha=0.3)
            
            # 自动调整Y轴范围
            if powers:
                min_power = min(powers)
                max_power = max(powers)
                padding = max((max_power - min_power) * 0.1, 0.1)
                self.ax.set_ylim(max(0, min_power - padding), max_power + padding)
            else:
                self.ax.set_ylim(0, 1)
            
            # 添加统计信息
            if powers:
                max_power = max(powers)
                min_power = min(powers)
                avg_power = sum(powers) / len(powers)
                
                stats_text = f'最大功率: {max_power:.2f} MW\n最小功率: {min_power:.2f} MW\n平均功率: {avg_power:.2f} MW\n数据点数: {len(powers)}'
                self.ax.text(0.02, 0.98, stats_text, transform=self.ax.transAxes, fontsize=10, 
                           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
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
    
    # 删除设备树状态更新方法（与潮流计算结果相关）

    def refresh_power_curve(self):
        """刷新功率曲线显示"""
        if self.selected_device_id is not None and self.selected_device_type is not None:
            self.display_power_curve()
        else:
            QMessageBox.information(self, "提示", "请先选择要监控的设备")

    def clear_power_history(self):
        """清空功率历史数据"""
        self.power_history.clear()
        
        # 清空图表并显示提示信息
        self.ax.clear()
        self.ax.text(0.5, 0.5, "功率历史数据已清空\n\n1. 选择要监控的设备\n2. 启用自动计算功能\n3. 数据将重新开始收集", 
                     transform=self.ax.transAxes, ha='center', va='center', 
                     bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7),
                     fontsize=12)
        self.ax.set_xlabel('时间 (秒)', fontsize=12)
        self.ax.set_ylabel('功率 (MW)', fontsize=12)
        self.ax.set_title('功率曲线监控', fontsize=14, fontweight='bold')
        self.canvas_mpl.draw()
        
        # 清理临时文件（如果存在）
        try:
            if os.path.exists('temp_power_curve.png'):
                os.remove('temp_power_curve.png')
        except:
            pass

    def show_topology_image(self):
        """显示网络拓扑图"""
        try:
            self.render_network_image()
            if self.current_pixmap is not None:
                # 创建拓扑图显示对话框
                dialog = QDialog(self)
                dialog.setWindowTitle("网络拓扑图")
                dialog.setModal(False)
                dialog.resize(800, 600)
                
                layout = QVBoxLayout(dialog)
                
                # 显示拓扑图
                image_label = QLabel()
                image_label.setPixmap(self.current_pixmap)
                image_label.setScaledContents(True)
                image_label.setAlignment(Qt.AlignCenter)
                
                scroll_area = QScrollArea()
                scroll_area.setWidget(image_label)
                scroll_area.setWidgetResizable(True)
                
                layout.addWidget(scroll_area)
                
                # 添加关闭按钮
                close_btn = QPushButton("关闭")
                close_btn.clicked.connect(dialog.close)
                layout.addWidget(close_btn)
                
                dialog.exec_()
            else:
                QMessageBox.warning(self, "警告", "无法生成网络拓扑图")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"显示拓扑图失败: {str(e)}")

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
                
            # 生成负载数据
            if self.load_data_checkbox.isChecked():
                load_data = self.load_data_generator.generate_load_data(self.network_model)
                
                # 更新网络中的负载值
                for load_idx, load_values in load_data.items():
                    if load_idx in self.network_model.net.load.index:
                        self.network_model.net.load.loc[load_idx, 'p_mw'] = load_values['p_mw']
                        self.network_model.net.load.loc[load_idx, 'q_mvar'] = load_values['q_mvar']
            
            # 运行潮流计算
            try:
                pp.runpp(self.network_model.net)
                self.statusBar().showMessage("潮流计算成功")
                
                # 更新设备树状态
                self.update_device_tree_status()
                
                # 更新功率曲线
                if self.selected_device_id is not None and self.selected_device_type is not None:
                    self.update_power_curve()
                    
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

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止自动计算定时器
        self.auto_calc_timer.stop()
        
        # 清理临时文件
        try:
            if os.path.exists('temp_power_curve.png'):
                os.remove('temp_power_curve.png')
        except:
            pass
            
        super().closeEvent(event)