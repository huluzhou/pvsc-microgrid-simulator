#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
仿真界面窗口
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QScrollArea, QTreeWidget, QTreeWidgetItem, QTextEdit, QLabel,
    QGroupBox, QFormLayout, QPushButton, QMessageBox, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QPainter, QFont
import pandas as pd
import pandapower as pp


class SimulationWindow(QMainWindow):
    """仿真界面窗口"""
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.parent_window = parent
        self.network_model = canvas.network_model if hasattr(canvas, 'network_model') else None
        
        self.init_ui()
        self.load_network_data()
        
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
        
        # 设备树
        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabel("设备列表")
        self.device_tree.itemClicked.connect(self.on_device_selected)
        tree_layout.addWidget(self.device_tree)
        
        # 仿真控制按钮
        control_group = QGroupBox("仿真控制")
        control_layout = QVBoxLayout(control_group)
        
        self.run_powerflow_btn = QPushButton("运行潮流计算")
        self.run_powerflow_btn.clicked.connect(self.run_power_flow)
        control_layout.addWidget(self.run_powerflow_btn)
        
        self.run_shortcircuit_btn = QPushButton("短路分析")
        self.run_shortcircuit_btn.clicked.connect(self.run_short_circuit)
        control_layout.addWidget(self.run_shortcircuit_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        tree_layout.addWidget(control_group)
        
        parent.addWidget(tree_widget)
        
    def create_central_image_area(self, parent):
        """创建中央滚动图像区域"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建图像标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: white;")
        
        # 渲染网络图像
        self.render_network_image()
        
        scroll_area.setWidget(self.image_label)
        parent.addWidget(scroll_area)
        
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
        
        # 潮流结果选项卡
        self.powerflow_results_tab = QWidget()
        self.create_powerflow_results_tab()
        self.results_tabs.addTab(self.powerflow_results_tab, "潮流结果")
        
        # 短路结果选项卡
        self.shortcircuit_results_tab = QWidget()
        self.create_shortcircuit_results_tab()
        self.results_tabs.addTab(self.shortcircuit_results_tab, "短路结果")
        
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
        
    def create_powerflow_results_tab(self):
        """创建潮流结果选项卡"""
        layout = QVBoxLayout(self.powerflow_results_tab)
        
        # 潮流结果表格
        self.powerflow_table = QTableWidget()
        layout.addWidget(self.powerflow_table)
        
    def create_shortcircuit_results_tab(self):
        """创建短路结果选项卡"""
        layout = QVBoxLayout(self.shortcircuit_results_tab)
        
        # 短路结果表格
        self.shortcircuit_table = QTableWidget()
        layout.addWidget(self.shortcircuit_table)
        
    def load_network_data(self):
        """加载网络数据到设备树"""
        if not self.network_model:
            return
            
        self.device_tree.clear()
        
        # 添加母线
        if not self.network_model.net.bus.empty:
            bus_root = QTreeWidgetItem(self.device_tree, ["母线"])
            for idx, bus in self.network_model.net.bus.iterrows():
                bus_item = QTreeWidgetItem(bus_root, [f"Bus {idx}: {bus['name']}"])
                bus_item.setData(0, Qt.UserRole, ('bus', idx))
                
        # 添加线路
        if not self.network_model.net.line.empty:
            line_root = QTreeWidgetItem(self.device_tree, ["线路"])
            for idx, line in self.network_model.net.line.iterrows():
                line_item = QTreeWidgetItem(line_root, [f"Line {idx}: {line.get('name', f'Line_{idx}')}"])
                line_item.setData(0, Qt.UserRole, ('line', idx))
                
        # 添加变压器
        if not self.network_model.net.trafo.empty:
            trafo_root = QTreeWidgetItem(self.device_tree, ["变压器"])
            for idx, trafo in self.network_model.net.trafo.iterrows():
                trafo_item = QTreeWidgetItem(trafo_root, [f"Trafo {idx}: {trafo.get('name', f'Trafo_{idx}')}"])
                trafo_item.setData(0, Qt.UserRole, ('trafo', idx))
                
        # 添加负载
        if not self.network_model.net.load.empty:
            load_root = QTreeWidgetItem(self.device_tree, ["负载"])
            for idx, load in self.network_model.net.load.iterrows():
                load_item = QTreeWidgetItem(load_root, [f"Load {idx}: {load.get('name', f'Load_{idx}')}"])
                load_item.setData(0, Qt.UserRole, ('load', idx))
                
        # 添加发电机
        if not self.network_model.net.gen.empty:
            gen_root = QTreeWidgetItem(self.device_tree, ["发电机"])
            for idx, gen in self.network_model.net.gen.iterrows():
                gen_item = QTreeWidgetItem(gen_root, [f"Gen {idx}: {gen.get('name', f'Gen_{idx}')}"])
                gen_item.setData(0, Qt.UserRole, ('gen', idx))
                
        # 添加静态发电机
        if not self.network_model.net.sgen.empty:
            sgen_root = QTreeWidgetItem(self.device_tree, ["静态发电机"])
            for idx, sgen in self.network_model.net.sgen.iterrows():
                sgen_item = QTreeWidgetItem(sgen_root, [f"SGen {idx}: {sgen.get('name', f'SGen_{idx}')}"])
                sgen_item.setData(0, Qt.UserRole, ('sgen', idx))
                
        # 添加外部电网
        if not self.network_model.net.ext_grid.empty:
            ext_grid_root = QTreeWidgetItem(self.device_tree, ["外部电网"])
            for idx, ext_grid in self.network_model.net.ext_grid.iterrows():
                ext_grid_item = QTreeWidgetItem(ext_grid_root, [f"ExtGrid {idx}: {ext_grid.get('name', f'ExtGrid_{idx}')}"])
                ext_grid_item.setData(0, Qt.UserRole, ('ext_grid', idx))
                
        # 添加储能
        if not self.network_model.net.storage.empty:
            storage_root = QTreeWidgetItem(self.device_tree, ["储能"])
            for idx, storage in self.network_model.net.storage.iterrows():
                storage_item = QTreeWidgetItem(storage_root, [f"Storage {idx}: {storage.get('name', f'Storage_{idx}')}"])
                storage_item.setData(0, Qt.UserRole, ('storage', idx))
        
        # 展开所有节点
        self.device_tree.expandAll()
        
    def render_network_image(self):
        """渲染网络图像到中央区域"""
        try:
            # 从画布获取场景内容并渲染为图像
            scene = self.canvas.scene
            scene_rect = scene.itemsBoundingRect()
            
            if scene_rect.isEmpty():
                self.image_label.setText("网络为空")
                return
                
            # 创建像素图
            pixmap = QPixmap(int(scene_rect.width() + 100), int(scene_rect.height() + 100))
            pixmap.fill(Qt.white)
            
            # 渲染场景到像素图
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            scene.render(painter, pixmap.rect(), scene_rect)
            painter.end()
            
            # 设置图像
            self.image_label.setPixmap(pixmap)
            
        except Exception as e:
            self.image_label.setText(f"渲染网络图像时出错: {str(e)}")
            
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
            if component_type == 'bus':
                component_data = self.network_model.net.bus.loc[component_idx]
            elif component_type == 'line':
                component_data = self.network_model.net.line.loc[component_idx]
            elif component_type == 'trafo':
                component_data = self.network_model.net.trafo.loc[component_idx]
            elif component_type == 'load':
                component_data = self.network_model.net.load.loc[component_idx]
            elif component_type == 'gen':
                component_data = self.network_model.net.gen.loc[component_idx]
            elif component_type == 'sgen':
                component_data = self.network_model.net.sgen.loc[component_idx]
            elif component_type == 'ext_grid':
                component_data = self.network_model.net.ext_grid.loc[component_idx]
            elif component_type == 'storage':
                component_data = self.network_model.net.storage.loc[component_idx]
            else:
                return
                
            # 显示组件信息
            info_text = f"组件类型: {component_type}\n"
            info_text += f"组件索引: {component_idx}\n"
            info_text += f"组件名称: {component_data.get('name', 'N/A')}\n"
            self.component_info.setText(info_text)
            
            # 填充参数表格
            self.component_params_table.setRowCount(len(component_data))
            for i, (param, value) in enumerate(component_data.items()):
                self.component_params_table.setItem(i, 0, QTableWidgetItem(str(param)))
                self.component_params_table.setItem(i, 1, QTableWidgetItem(str(value)))
                
        except Exception as e:
            self.component_info.setText(f"显示组件详情时出错: {str(e)}")
            
    def run_power_flow(self):
        """运行潮流计算"""
        if not self.network_model:
            QMessageBox.warning(self, "警告", "没有可用的网络模型")
            return
            
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self.run_powerflow_btn.setEnabled(False)
            
            # 运行潮流计算
            pp.runpp(self.network_model.net)
            
            # 显示结果
            self.show_powerflow_results()
            
            self.statusBar().showMessage("潮流计算完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"潮流计算失败: {str(e)}")
            
        finally:
            self.progress_bar.setVisible(False)
            self.run_powerflow_btn.setEnabled(True)
            
    def show_powerflow_results(self):
        """显示潮流计算结果"""
        if not self.network_model:
            return
            
        try:
            # 显示母线结果
            bus_results = self.network_model.net.res_bus
            if not bus_results.empty:
                self.powerflow_table.setRowCount(len(bus_results))
                self.powerflow_table.setColumnCount(len(bus_results.columns) + 1)
                
                headers = ['Index'] + list(bus_results.columns)
                self.powerflow_table.setHorizontalHeaderLabels(headers)
                
                for i, (idx, row) in enumerate(bus_results.iterrows()):
                    self.powerflow_table.setItem(i, 0, QTableWidgetItem(str(idx)))
                    for j, value in enumerate(row):
                        self.powerflow_table.setItem(i, j + 1, QTableWidgetItem(f"{value:.4f}" if isinstance(value, float) else str(value)))
                        
            # 切换到潮流结果选项卡
            self.results_tabs.setCurrentIndex(1)
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"显示潮流结果时出错: {str(e)}")
            
    def run_short_circuit(self):
        """运行短路分析"""
        QMessageBox.information(self, "信息", "短路分析功能正在开发中...")
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.parent_window.statusBar().showMessage("已退出仿真模式")
        event.accept()