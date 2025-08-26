#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
仿真界面窗口
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QScrollArea, QTreeWidget, QTreeWidgetItem, QTextEdit, QLabel,
    QGroupBox, QFormLayout, QPushButton, QMessageBox, QProgressBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QPoint
from PySide6.QtGui import QPixmap, QPainter, QFont, QWheelEvent, QMouseEvent
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
        
        # 仿真控制按钮
        control_group = QGroupBox("仿真控制")
        control_layout = QVBoxLayout(control_group)
        
        self.run_powerflow_btn = QPushButton("运行潮流计算")
        self.run_powerflow_btn.clicked.connect(self.run_power_flow)
        self.run_powerflow_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.run_powerflow_btn)
        
        self.run_shortcircuit_btn = QPushButton("短路分析")
        self.run_shortcircuit_btn.clicked.connect(self.run_short_circuit)
        self.run_shortcircuit_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 8px; }")
        control_layout.addWidget(self.run_shortcircuit_btn)
        
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
        
        control_layout.addWidget(export_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        tree_layout.addWidget(control_group)
        
        parent.addWidget(tree_widget)
        
    def create_central_image_area(self, parent):
        """创建中央滚动图像区域"""
        # 创建增强的滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 创建图像显示容器
        self.image_container = QWidget()
        self.image_container.setMinimumSize(1200, 800)
        
        # 创建图像标签
        self.image_label = QLabel(self.image_container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("网络图像将在此显示\n\n提示：\n- 鼠标滚轮：缩放\n- 鼠标拖拽：平移\n- 双击：适应窗口")
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: white; font-size: 14px; color: #666;")
        self.image_label.setMinimumSize(1200, 800)
        
        # 设置图像标签的几何位置
        self.image_label.setGeometry(0, 0, 1200, 800)
        
        self.scroll_area.setWidget(self.image_container)
        
        # 图像显示相关属性
        self.current_pixmap = None
        self.scale_factor = 1.0
        self.min_scale = 0.1
        self.max_scale = 5.0
        self.last_pan_point = None
        
        # 为滚动区域安装事件过滤器
        self.scroll_area.installEventFilter(self)
        self.image_label.installEventFilter(self)
        
        # 渲染网络图像
        self.render_network_image()
        
        parent.addWidget(self.scroll_area)
        
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
            
            # 检查是否有潮流计算结果
            has_results = hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty
            
            # 在图像上叠加潮流计算结果
            if has_results:
                self.overlay_powerflow_results(painter, scene_rect, margin)
            
            # 添加图例和状态信息
            self.draw_image_legend(painter, pixmap.width(), pixmap.height(), has_results)
            
            painter.end()
            
            # 保存原始图像并设置显示
            self.current_pixmap = pixmap
            self.scale_factor = 1.0
            self.update_image_display()
            
        except Exception as e:
            self.image_label.setText(f"渲染网络图像时出错: {str(e)}")
    
    def overlay_powerflow_results(self, painter, scene_rect, margin):
        """在网络图上叠加潮流计算结果"""
        try:
            # 设置字体
            font = QFont("Arial", 8)
            painter.setFont(font)
            
            # 获取场景中的所有图形项
            scene = self.canvas.scene
            items = scene.items()
            
            # 为每个组件添加结果标签
            for item in items:
                if hasattr(item, 'component_type') and hasattr(item, 'component_id'):
                    component_type = item.component_type
                    component_id = item.component_id
                    
                    # 获取项目在场景中的位置
                    item_pos = item.pos()
                    item_rect = item.boundingRect()
                    
                    # 转换到图像坐标
                    x = item_pos.x() + margin
                    y = item_pos.y() + margin
                    
                    # 根据组件类型显示相应的结果
                    result_text = self.get_component_result_text(component_type, component_id)
                    if result_text:
                        # 设置结果文本的背景和颜色
                        painter.setPen(Qt.black)
                        painter.setBrush(QBrush(QColor(255, 255, 255, 200)))  # 半透明白色背景
                        
                        # 计算文本位置（在组件旁边）
                        text_x = x + item_rect.width() + 5
                        text_y = y + item_rect.height() / 2
                        
                        # 绘制背景矩形
                        text_rect = painter.fontMetrics().boundingRect(result_text)
                        bg_rect = QRectF(text_x - 2, text_y - text_rect.height() - 2, 
                                       text_rect.width() + 4, text_rect.height() + 4)
                        painter.drawRect(bg_rect)
                        
                        # 绘制文本
                        painter.drawText(text_x, text_y, result_text)
                        
        except Exception as e:
            print(f"叠加潮流结果时出错: {str(e)}")
    
    def get_component_result_text(self, component_type, component_id):
        """获取组件的结果文本"""
        try:
            result_text = ""
            
            if component_type == 'bus' and hasattr(self.network_model.net, 'res_bus'):
                if component_id in self.network_model.net.res_bus.index:
                    res = self.network_model.net.res_bus.loc[component_id]
                    voltage = res['vm_pu']
                    angle = res['va_degree']
                    result_text = f"V: {voltage:.3f}p.u.\n∠: {angle:.1f}°"
                    
            elif component_type == 'line' and hasattr(self.network_model.net, 'res_line'):
                if component_id in self.network_model.net.res_line.index:
                    res = self.network_model.net.res_line.loc[component_id]
                    p_flow = res['p_from_mw']
                    loading = res['loading_percent']
                    result_text = f"P: {p_flow:.1f}MW\nLoad: {loading:.1f}%"
                    
            elif component_type == 'trafo' and hasattr(self.network_model.net, 'res_trafo'):
                if component_id in self.network_model.net.res_trafo.index:
                    res = self.network_model.net.res_trafo.loc[component_id]
                    p_flow = res['p_hv_mw']
                    loading = res['loading_percent']
                    result_text = f"P: {p_flow:.1f}MW\nLoad: {loading:.1f}%"
                    
            elif component_type == 'load' and hasattr(self.network_model.net, 'res_load'):
                if component_id in self.network_model.net.res_load.index:
                    res = self.network_model.net.res_load.loc[component_id]
                    p_load = res['p_mw']
                    q_load = res['q_mvar']
                    result_text = f"P: {p_load:.1f}MW\nQ: {q_load:.1f}MVar"
                    
            elif component_type == 'gen' and hasattr(self.network_model.net, 'res_gen'):
                if component_id in self.network_model.net.res_gen.index:
                    res = self.network_model.net.res_gen.loc[component_id]
                    p_gen = res['p_mw']
                    q_gen = res['q_mvar']
                    result_text = f"P: {p_gen:.1f}MW\nQ: {q_gen:.1f}MVar"
                    
            elif component_type == 'sgen' and hasattr(self.network_model.net, 'res_sgen'):
                if component_id in self.network_model.net.res_sgen.index:
                    res = self.network_model.net.res_sgen.loc[component_id]
                    p_sgen = res['p_mw']
                    q_sgen = res['q_mvar']
                    result_text = f"P: {p_sgen:.1f}MW\nQ: {q_sgen:.1f}MVar"
                    
            elif component_type == 'ext_grid' and hasattr(self.network_model.net, 'res_ext_grid'):
                if component_id in self.network_model.net.res_ext_grid.index:
                    res = self.network_model.net.res_ext_grid.loc[component_id]
                    p_ext = res['p_mw']
                    q_ext = res['q_mvar']
                    result_text = f"P: {p_ext:.1f}MW\nQ: {q_ext:.1f}MVar"
                    
            elif component_type == 'storage' and hasattr(self.network_model.net, 'res_storage'):
                if component_id in self.network_model.net.res_storage.index:
                    res = self.network_model.net.res_storage.loc[component_id]
                    p_storage = res['p_mw']
                    q_storage = res['q_mvar']
                    result_text = f"P: {p_storage:.1f}MW\nQ: {q_storage:.1f}MVar"
                    
            return result_text
            
        except Exception as e:
            return ""
    
    def draw_image_legend(self, painter, width, height, has_results):
        """绘制图像图例和状态信息"""
        try:
            # 设置字体和画笔
            painter.setFont(QFont("Arial", 10, QFont.Bold))
            painter.setPen(Qt.black)
            
            # 绘制标题
            title = "电力系统网络拓扑图 - 潮流计算结果可视化" if has_results else "电力系统网络拓扑图"
            painter.drawText(10, 20, title)
            
            # 绘制状态信息
            painter.setFont(QFont("Arial", 9))
            if has_results:
                painter.setPen(Qt.darkGreen)
                painter.drawText(10, 40, "✓ 潮流计算已完成，显示实时结果")
                
                # 绘制图例
                legend_y = height - 120
                painter.setPen(Qt.black)
                painter.drawText(10, legend_y, "图例:")
                painter.drawText(10, legend_y + 20, "• V: 电压幅值 (p.u.)")
                painter.drawText(10, legend_y + 35, "• ∠: 电压角度 (度)")
                painter.drawText(10, legend_y + 50, "• P: 有功功率 (MW)")
                painter.drawText(10, legend_y + 65, "• Q: 无功功率 (MVar)")
                painter.drawText(10, legend_y + 80, "• Load: 负载率 (%)")
                
            else:
                painter.setPen(Qt.darkRed)
                painter.drawText(10, 40, "⚠ 未运行潮流计算，请先执行潮流分析")
                
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
                    param_item.setBackground(Qt.lightGray)
                    value_item.setBackground(Qt.lightGray)
                    
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
            
    def run_power_flow(self):
        """运行潮流计算"""
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self.run_powerflow_btn.setEnabled(False)
            
            # 首先从画布创建网络模型
            self.statusBar().showMessage("正在创建网络模型...")
            if not self.canvas.create_network_model():
                QMessageBox.warning(self, "警告", "无法从画布组件创建网络模型，请检查网络连接")
                return
            
            # 更新仿真窗口的网络模型引用
            self.network_model = self.canvas.network_model
            
            # 重新加载网络数据到设备树
            self.load_network_data()
            
            # 基本网络验证
            if not self.validate_network():
                return
            
            self.statusBar().showMessage("正在运行潮流计算...")
            
            # 运行潮流计算
            pp.runpp(self.network_model.net)
            
            # 显示结果
            self.show_powerflow_results()
            
            # 重新渲染网络图像以显示结果
            self.render_network_image()
            
            self.statusBar().showMessage("潮流计算完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"潮流计算失败: {str(e)}")
            
        finally:
            self.progress_bar.setVisible(False)
            self.run_powerflow_btn.setEnabled(True)
    
    def validate_network(self):
        """验证网络模型的有效性"""
        try:
            if not self.network_model or not self.network_model.net:
                QMessageBox.warning(self, "网络验证", "网络模型为空")
                return False
            
            net = self.network_model.net
            
            # 检查是否有母线
            if net.bus.empty:
                QMessageBox.warning(self, "网络验证", "网络中没有母线组件，无法进行潮流计算")
                return False
            
            # 检查是否有电源
            has_power_source = (
                not net.ext_grid.empty or 
                not net.gen.empty or 
                not net.sgen.empty
            )
            
            if not has_power_source:
                QMessageBox.warning(self, "网络验证", "网络中没有电源（外部电网、发电机或静态发电机），无法进行潮流计算")
                return False
            
            # 检查网络连通性（简单检查）
            if len(net.bus) > 1 and net.line.empty and net.trafo.empty:
                QMessageBox.warning(self, "网络验证", "网络中有多个母线但没有连接线路或变压器，可能存在孤立母线")
                return False
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "网络验证错误", f"网络验证过程中发生错误：{str(e)}")
            return False
            
    def show_powerflow_results(self):
        """显示潮流计算结果"""
        if not self.network_model:
            return
            
        try:
            # 检查是否有潮流计算结果
            if not hasattr(self.network_model.net, 'res_bus') or self.network_model.net.res_bus.empty:
                self.powerflow_table.setRowCount(1)
                self.powerflow_table.setColumnCount(1)
                self.powerflow_table.setHorizontalHeaderLabels(["状态"])
                self.powerflow_table.setItem(0, 0, QTableWidgetItem("没有潮流计算结果，请先运行潮流计算"))
                return
            
            # 创建综合结果表格
            all_results = []
            
            # 母线结果
            if hasattr(self.network_model.net, 'res_bus') and not self.network_model.net.res_bus.empty:
                for idx, row in self.network_model.net.res_bus.iterrows():
                    bus_name = self.network_model.net.bus.loc[idx, 'name'] if 'name' in self.network_model.net.bus.columns else f"Bus_{idx}"
                    voltage_status = "正常" if 0.95 <= row['vm_pu'] <= 1.05 else "异常"
                    all_results.append({
                        '类型': '母线',
                        '名称': bus_name,
                        '有功功率(MW)': '-',
                        '无功功率(MVar)': '-',
                        '电压幅值(p.u.)': f"{row['vm_pu']:.4f}",
                        '电压角度(°)': f"{row['va_degree']:.2f}",
                        '负载率(%)': '-',
                        '状态': voltage_status
                    })
            
            # 线路结果
            if hasattr(self.network_model.net, 'res_line') and not self.network_model.net.res_line.empty:
                for idx, row in self.network_model.net.res_line.iterrows():
                    line_name = self.network_model.net.line.loc[idx, 'name'] if 'name' in self.network_model.net.line.columns else f"Line_{idx}"
                    loading_status = "正常" if row['loading_percent'] <= 100 else "过载"
                    all_results.append({
                        '类型': '线路',
                        '名称': line_name,
                        '有功功率(MW)': f"{row['p_from_mw']:.3f}",
                        '无功功率(MVar)': f"{row['q_from_mvar']:.3f}",
                        '电压幅值(p.u.)': '-',
                        '电压角度(°)': '-',
                        '负载率(%)': f"{row['loading_percent']:.1f}",
                        '状态': loading_status
                    })
            
            # 变压器结果
            if hasattr(self.network_model.net, 'res_trafo') and not self.network_model.net.res_trafo.empty:
                for idx, row in self.network_model.net.res_trafo.iterrows():
                    trafo_name = self.network_model.net.trafo.loc[idx, 'name'] if 'name' in self.network_model.net.trafo.columns else f"Trafo_{idx}"
                    loading_status = "正常" if row['loading_percent'] <= 100 else "过载"
                    all_results.append({
                        '类型': '变压器',
                        '名称': trafo_name,
                        '有功功率(MW)': f"{row['p_hv_mw']:.3f}",
                        '无功功率(MVar)': f"{row['q_hv_mvar']:.3f}",
                        '电压幅值(p.u.)': '-',
                        '电压角度(°)': '-',
                        '负载率(%)': f"{row['loading_percent']:.1f}",
                        '状态': loading_status
                    })
            
            # 发电机结果
            if hasattr(self.network_model.net, 'res_gen') and not self.network_model.net.res_gen.empty:
                for idx, row in self.network_model.net.res_gen.iterrows():
                    gen_name = self.network_model.net.gen.loc[idx, 'name'] if 'name' in self.network_model.net.gen.columns else f"Gen_{idx}"
                    all_results.append({
                        '类型': '发电机',
                        '名称': gen_name,
                        '有功功率(MW)': f"{row['p_mw']:.3f}",
                        '无功功率(MVar)': f"{row['q_mvar']:.3f}",
                        '电压幅值(p.u.)': '-',
                        '电压角度(°)': '-',
                        '负载率(%)': '-',
                        '状态': '运行'
                    })
            
            # 静态发电机结果
            if hasattr(self.network_model.net, 'res_sgen') and not self.network_model.net.res_sgen.empty:
                for idx, row in self.network_model.net.res_sgen.iterrows():
                    sgen_name = self.network_model.net.sgen.loc[idx, 'name'] if 'name' in self.network_model.net.sgen.columns else f"SGen_{idx}"
                    all_results.append({
                        '类型': '静态发电机',
                        '名称': sgen_name,
                        '有功功率(MW)': f"{row['p_mw']:.3f}",
                        '无功功率(MVar)': f"{row['q_mvar']:.3f}",
                        '电压幅值(p.u.)': '-',
                        '电压角度(°)': '-',
                        '负载率(%)': '-',
                        '状态': '运行'
                    })
            
            # 负载结果
            if hasattr(self.network_model.net, 'res_load') and not self.network_model.net.res_load.empty:
                for idx, row in self.network_model.net.res_load.iterrows():
                    load_name = self.network_model.net.load.loc[idx, 'name'] if 'name' in self.network_model.net.load.columns else f"Load_{idx}"
                    all_results.append({
                        '类型': '负载',
                        '名称': load_name,
                        '有功功率(MW)': f"{row['p_mw']:.3f}",
                        '无功功率(MVar)': f"{row['q_mvar']:.3f}",
                        '电压幅值(p.u.)': '-',
                        '电压角度(°)': '-',
                        '负载率(%)': '-',
                        '状态': '运行'
                    })
            
            # 外部电网结果
            if hasattr(self.network_model.net, 'res_ext_grid') and not self.network_model.net.res_ext_grid.empty:
                for idx, row in self.network_model.net.res_ext_grid.iterrows():
                    ext_grid_name = self.network_model.net.ext_grid.loc[idx, 'name'] if 'name' in self.network_model.net.ext_grid.columns else f"ExtGrid_{idx}"
                    all_results.append({
                        '类型': '外部电网',
                        '名称': ext_grid_name,
                        '有功功率(MW)': f"{row['p_mw']:.3f}",
                        '无功功率(MVar)': f"{row['q_mvar']:.3f}",
                        '电压幅值(p.u.)': '-',
                        '电压角度(°)': '-',
                        '负载率(%)': '-',
                        '状态': '运行'
                    })
            
            # 储能结果
            if hasattr(self.network_model.net, 'res_storage') and not self.network_model.net.res_storage.empty:
                for idx, row in self.network_model.net.res_storage.iterrows():
                    storage_name = self.network_model.net.storage.loc[idx, 'name'] if 'name' in self.network_model.net.storage.columns else f"Storage_{idx}"
                    all_results.append({
                        '类型': '储能',
                        '名称': storage_name,
                        '有功功率(MW)': f"{row['p_mw']:.3f}",
                        '无功功率(MVar)': f"{row['q_mvar']:.3f}",
                        '电压幅值(p.u.)': '-',
                        '电压角度(°)': '-',
                        '负载率(%)': '-',
                        '状态': '运行'
                    })
            
            # 填充表格
            if all_results:
                self.powerflow_table.setRowCount(len(all_results))
                headers = list(all_results[0].keys())
                self.powerflow_table.setColumnCount(len(headers))
                self.powerflow_table.setHorizontalHeaderLabels(headers)
                
                for i, result in enumerate(all_results):
                    for j, (key, value) in enumerate(result.items()):
                        item = QTableWidgetItem(str(value))
                        
                        # 为不同状态设置不同颜色
                        if key == '状态':
                            if value == '异常' or value == '过载':
                                item.setBackground(Qt.red)
                            elif value == '正常' or value == '运行':
                                item.setBackground(Qt.green)
                        
                        # 为不同类型设置不同背景色
                        elif key == '类型':
                            if value == '母线':
                                item.setBackground(Qt.lightBlue)
                            elif value in ['线路', '变压器']:
                                item.setBackground(Qt.lightYellow)
                            elif value in ['发电机', '静态发电机', '外部电网', '储能']:
                                item.setBackground(Qt.lightGreen)
                            elif value == '负载':
                                item.setBackground(Qt.lightGray)
                        
                        self.powerflow_table.setItem(i, j, item)
                
                # 调整列宽
                self.powerflow_table.resizeColumnsToContents()
            
            # 切换到潮流结果选项卡
            self.results_tabs.setCurrentIndex(1)
            
        except Exception as e:
            QMessageBox.warning(self, "警告", f"显示潮流结果时出错: {str(e)}")
            
    def run_short_circuit(self):
        """运行短路分析"""
        QMessageBox.information(self, "信息", "短路分析功能正在开发中...")
        
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
            import os
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
        self.parent_window.statusBar().showMessage("已退出仿真模式")
        event.accept()