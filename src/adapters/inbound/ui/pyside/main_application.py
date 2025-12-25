#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
光储充微电网系统主应用窗口
整合所有功能模块，提供统一的用户界面
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QTabWidget, QStatusBar, QToolBar, QMenuBar, QMenu, QMessageBox,
    QPushButton, QLabel, QFrame, QFileDialog
)
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtCore import Qt, QSize, Signal

# 使用PySide6默认样式系统

# 从组件文件导入自定义组件
from .topology import StatusPanel, TopologyCanvas, DevicePanel, PropertyEditor, TopologyToolbar

class MainApplication(QMainWindow):
    """光储充微电网系统主应用窗口"""
    
    def __init__(self, application):
        super().__init__()
        self.setWindowTitle("光储充微电网系统")
        # 设置窗口最小尺寸，确保设备列表能完整显示
        self.setMinimumSize(QSize(1920, 1080))
        # 设置窗口初始尺寸
        self.resize(QSize(1920, 1080))
        
        # 应用实例
        self.application = application
        
        # 初始化组件
        self._init_components()
        # 设置布局
        self._setup_layout()
        # 创建菜单栏
        self._create_menu_bar()
        # 创建工具栏
        self._create_tool_bar()
        # 设置状态栏
        self._setup_status_bar()
        # 连接信号槽
        self._connect_signals()
        
    def _init_components(self):
        """初始化组件"""
        # 侧边导航面板
        self.sidebar = self._create_sidebar()
        
        # 工作区标签页
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.setTabPosition(QTabWidget.North)
        self.workspace_tabs.setMovable(True)
        self.workspace_tabs.setTabsClosable(True)
        
        # 创建各个功能模块的工作区
        self._create_workspace_tabs()
        
        # 状态栏组件
        self.status_panel = StatusPanel()
        
    def _create_sidebar(self):
        """创建侧边导航面板"""
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        
        # 设置侧边栏样式
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-right: 1px solid #e9ecef;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(12)
        
        # 应用标题
        title_label = QLabel("光储充微电网系统")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 24px;
            }
        """)
        layout.addWidget(title_label)
        
        # 功能模块按钮
        self.module_buttons = {}
        
        # 拓扑设计
        self.module_buttons["topology"] = self._create_sidebar_button("拓扑设计", self._on_topology_clicked)
        # 实时监控
        self.module_buttons["monitoring"] = self._create_sidebar_button("实时监控", self._on_monitoring_clicked)
        # 设备控制
        self.module_buttons["control"] = self._create_sidebar_button("设备控制", self._on_control_clicked)
        # 数据回测
        self.module_buttons["backtest"] = self._create_sidebar_button("数据回测", self._on_backtest_clicked)
        # 数据分析
        self.module_buttons["analysis"] = self._create_sidebar_button("数据分析", self._on_analysis_clicked)
        
        # 添加按钮到布局
        for button in self.module_buttons.values():
            layout.addWidget(button)
        
        # 占位符，将按钮推到顶部
        layout.addStretch()
        
        # 版本信息
        version_label = QLabel("v1.0.0")
        version_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #6c757d;
                text-align: center;
            }
        """)
        layout.addWidget(version_label)
        
        return sidebar
    
    def _create_sidebar_button(self, text, callback):
        """创建侧边栏按钮"""
        button = QPushButton(text)
        button.setCheckable(True)
        button.clicked.connect(callback)
        
        # 设置按钮样式
        button.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
                min-height: 48px;
            }
            
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            
            QPushButton:checked {
                background-color: #343a40;
                color: #ffffff;
                border-color: #343a40;
            }
            
            QPushButton:pressed {
                background-color: #212529;
            }
        """)
        
        return button
    
    def _create_workspace_tabs(self):
        """创建工作区标签页"""
        # 拓扑设计工作区
        topology_workspace = self._create_topology_workspace()
        self.workspace_tabs.addTab(topology_workspace, "拓扑设计")
        
        # 实时监控工作区
        monitoring_workspace = self._create_monitoring_workspace()
        self.workspace_tabs.addTab(monitoring_workspace, "实时监控")
        
        # 设备控制工作区
        control_workspace = self._create_control_workspace()
        self.workspace_tabs.addTab(control_workspace, "设备控制")
        
        # 数据回测工作区
        backtest_workspace = self._create_backtest_workspace()
        self.workspace_tabs.addTab(backtest_workspace, "数据回测")
        
        # 数据分析工作区
        analysis_workspace = self._create_analysis_workspace()
        self.workspace_tabs.addTab(analysis_workspace, "数据分析")
    
    def _create_topology_workspace(self):
        """创建拓扑设计工作区"""
        workspace = QWidget()
        
        # 主布局 - 垂直布局，先放工具栏，再放内容
        main_layout = QVBoxLayout(workspace)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建拓扑设计专属工具栏
        topology_toolbar = TopologyToolbar()
        topology_toolbar.new_topology.connect(self._on_new_topology)
        topology_toolbar.open_topology.connect(self._on_open_topology)
        topology_toolbar.save_topology.connect(self._on_save_topology)
        topology_toolbar.import_topology.connect(self._on_import_topology)
        topology_toolbar.export_topology.connect(self._on_export_topology)
        topology_toolbar.undo.connect(self._on_undo)
        topology_toolbar.redo.connect(self._on_redo)
        
        # 将工具栏添加到主布局
        main_layout.addWidget(topology_toolbar)
        
        # 内容布局 - 水平布局，包含现有内容
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # 设备面板
        self.device_panel = DevicePanel()
        
        # 拓扑画布
        self.topology_canvas = TopologyCanvas(self.application)
        
        # 属性编辑器
        self.property_editor = PropertyEditor()
        
        # 左侧分割器
        left_splitter = QSplitter(Qt.Horizontal)
        left_splitter.addWidget(self.device_panel)
        left_splitter.addWidget(self.topology_canvas)
        left_splitter.setSizes([260, 1680]) # 画布宽度翻倍 (840 * 2)
        left_splitter.setOpaqueResize(True)
        left_splitter.setStretchFactor(0, 0)
        left_splitter.setStretchFactor(1, 1)
        left_splitter.setCollapsible(0, False)
        left_splitter.setCollapsible(1, True)
        
        # 主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(self.property_editor)
        main_splitter.setSizes([1940, 300]) # 左侧区域宽度相应增加 (260 + 1680)
        self.property_editor.setMinimumWidth(320)
        self.property_editor.setMaximumWidth(420)
        main_splitter.setOpaqueResize(True)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 0)
        main_splitter.setCollapsible(0, True)
        main_splitter.setCollapsible(1, True)
        
        # 将分割器添加到内容布局
        content_layout.addWidget(main_splitter)
        
        # 将内容布局添加到主布局
        main_layout.addWidget(main_splitter)
        
        return workspace
    
    def _create_monitoring_workspace(self):
        """创建实时监控工作区"""
        workspace = QWidget()
        
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)
        
        # 设备列表
        device_list = QFrame()
        device_list_layout = QHBoxLayout(device_list)
        device_list_layout.setSpacing(8)
        
        # 模拟设备标签
        devices = ["光伏逆变器1", "光伏逆变器2", "储能系统1", "负载1", "充电桩1"]
        for device in devices:
            device_tag = QPushButton(device)
            device_list_layout.addWidget(device_tag)
        
        device_list_layout.addStretch()
        layout.addWidget(device_list)
        
        # 数据曲线图
        chart_container = QFrame()
        chart_layout = QVBoxLayout(chart_container)
        
        chart_title = QLabel("实时数据曲线图")
        chart_layout.addWidget(chart_title)
        
        chart_placeholder = QLabel("数据曲线图将显示在此处")
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_layout.addWidget(chart_placeholder, 1)
        
        layout.addWidget(chart_container, 1)
        
        # 设备详细参数
        device_details = QFrame()
        device_details_layout = QGridLayout(device_details)
        device_details_layout.setSpacing(16)
        
        # 基本信息
        basic_info = QFrame()
        basic_info_layout = QVBoxLayout(basic_info)
        
        basic_info_title = QLabel("基本信息")
        basic_info_layout.addWidget(basic_info_title)
        
        basic_info_layout.addWidget(QLabel("设备名称：光伏逆变器1"))
        basic_info_layout.addWidget(QLabel("设备状态：运行正常"))
        basic_info_layout.addWidget(QLabel("通信状态：正常"))
        
        device_details_layout.addWidget(basic_info, 0, 0)
        
        # 电气参数
        electrical_params = QFrame()
        electrical_params_layout = QVBoxLayout(electrical_params)
        
        electrical_params_title = QLabel("电气参数")
        electrical_params_layout.addWidget(electrical_params_title)
        
        electrical_params_layout.addWidget(QLabel("电压：220.5 V"))
        electrical_params_layout.addWidget(QLabel("电流：10.2 A"))
        electrical_params_layout.addWidget(QLabel("有功功率：2.25 kW"))
        electrical_params_layout.addWidget(QLabel("无功功率：0.12 kVar"))
        
        device_details_layout.addWidget(electrical_params, 0, 1)
        
        # 运行参数
        operation_params = QFrame()
        operation_params_layout = QVBoxLayout(operation_params)
        
        operation_params_title = QLabel("运行参数")
        operation_params_layout.addWidget(operation_params_title)
        
        operation_params_layout.addWidget(QLabel("温度：45.2 °C"))
        operation_params_layout.addWidget(QLabel("频率：50.0 Hz"))
        operation_params_layout.addWidget(QLabel("日发电量：12.5 kWh"))
        operation_params_layout.addWidget(QLabel("总发电量：1,234.5 kWh"))
        
        device_details_layout.addWidget(operation_params, 0, 2)
        
        layout.addWidget(device_details)
        
        return workspace
    
    def _create_control_workspace(self):
        """创建设备控制工作区"""
        workspace = QWidget()
        
        layout = QHBoxLayout(workspace)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)
        
        # 设备树
        device_tree = QFrame()
        device_tree_layout = QVBoxLayout(device_tree)
        
        device_tree_title = QLabel("设备列表")
        device_tree_layout.addWidget(device_tree_title)
        
        # 模拟设备树
        device_tree_placeholder = QLabel("设备树将显示在此处")
        device_tree_placeholder.setAlignment(Qt.AlignCenter)
        device_tree_layout.addWidget(device_tree_placeholder, 1)
        
        layout.addWidget(device_tree)
        
        # 控制面板
        control_panel = QFrame()
        control_panel_layout = QVBoxLayout(control_panel)
        
        # 设备基本信息
        basic_info = QFrame()
        basic_info_layout = QVBoxLayout(basic_info)
        
        basic_info_layout.addWidget(QLabel("设备名称：光伏逆变器1"))
        basic_info_layout.addWidget(QLabel("设备状态：运行中"))
        basic_info_layout.addWidget(QLabel("通信状态：正常"))
        
        control_panel_layout.addWidget(basic_info)
        
        # 控制操作区
        control_section = QFrame()
        control_section_layout = QVBoxLayout(control_section)
        
        control_title = QLabel("控制操作")
        control_section_layout.addWidget(control_title)
        
        control_buttons_layout = QHBoxLayout()
        control_buttons_layout.setSpacing(16)
        
        start_button = QPushButton("启动")
        control_buttons_layout.addWidget(start_button)
        
        stop_button = QPushButton("停止")
        control_buttons_layout.addWidget(stop_button)
        
        emergency_button = QPushButton("紧急停止")
        control_buttons_layout.addWidget(emergency_button)
        
        control_buttons_layout.addStretch()
        control_section_layout.addLayout(control_buttons_layout)
        
        control_panel_layout.addWidget(control_section)
        
        # 功率调节区
        power_section = QFrame()
        power_section_layout = QVBoxLayout(power_section)
        
        power_title = QLabel("功率调节")
        power_section_layout.addWidget(power_title)
        
        # 有功功率
        active_power_layout = QVBoxLayout()
        active_power_layout.addWidget(QLabel("有功功率：50 kW"))
        active_power_slider = QFrame()
        active_power_layout.addWidget(active_power_slider)
        power_section_layout.addLayout(active_power_layout)
        
        # 无功功率
        reactive_power_layout = QVBoxLayout()
        reactive_power_layout.addWidget(QLabel("无功功率：0 kVar"))
        reactive_power_slider = QFrame()
        reactive_power_layout.addWidget(reactive_power_slider)
        power_section_layout.addLayout(reactive_power_layout)
        
        control_panel_layout.addWidget(power_section)
        
        # 模拟数据生成区
        simulation_section = QFrame()
        simulation_section_layout = QVBoxLayout(simulation_section)
        
        simulation_title = QLabel("模拟数据生成")
        simulation_section_layout.addWidget(simulation_title)
        
        simulation_buttons_layout = QHBoxLayout()
        simulation_buttons_layout.setSpacing(16)
        
        sine_button = QPushButton("正弦波")
        simulation_buttons_layout.addWidget(sine_button)
        
        step_button = QPushButton("阶跃变化")
        simulation_buttons_layout.addWidget(step_button)
        
        random_button = QPushButton("随机数据")
        simulation_buttons_layout.addWidget(random_button)
        
        simulation_buttons_layout.addStretch()
        simulation_section_layout.addLayout(simulation_buttons_layout)
        
        control_panel_layout.addWidget(simulation_section)
        
        layout.addWidget(control_panel)
        
        return workspace
    
    def _create_backtest_workspace(self):
        """创建数据回测工作区"""
        workspace = QWidget()
        
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)
        
        # 回测配置区
        config_section = QFrame()
        config_section_layout = QGridLayout(config_section)
        config_section_layout.setSpacing(16)
        
        # 数据源配置
        data_source = QFrame()
        data_source_layout = QVBoxLayout(data_source)
        
        data_source_title = QLabel("数据源配置")
        data_source_layout.addWidget(data_source_title)
        
        data_source_layout.addWidget(QLabel("数据库路径："))
        data_source_layout.addWidget(QFrame())
        data_source_layout.addWidget(QLabel("表名："))
        data_source_layout.addWidget(QFrame())
        
        config_section_layout.addWidget(data_source, 0, 0)
        
        # 日期范围
        date_range = QFrame()
        date_range_layout = QVBoxLayout(date_range)
        
        date_range_title = QLabel("日期范围")
        date_range_layout.addWidget(date_range_title)
        
        date_range_layout.addWidget(QLabel("开始日期："))
        date_range_layout.addWidget(QFrame())
        date_range_layout.addWidget(QLabel("结束日期："))
        date_range_layout.addWidget(QFrame())
        
        config_section_layout.addWidget(date_range, 0, 1)
        
        # 回测参数
        backtest_params = QFrame()
        backtest_params_layout = QVBoxLayout(backtest_params)
        
        backtest_params_title = QLabel("回测参数")
        backtest_params_layout.addWidget(backtest_params_title)
        
        backtest_params_layout.addWidget(QLabel("回测速率："))
        backtest_params_layout.addWidget(QFrame())
        backtest_params_layout.addWidget(QLabel("参与设备："))
        backtest_params_layout.addWidget(QFrame())
        
        config_section_layout.addWidget(backtest_params, 0, 2)
        
        layout.addWidget(config_section)
        
        # 回测监控区
        monitor_section = QFrame()
        monitor_section_layout = QVBoxLayout(monitor_section)
        
        monitor_title = QLabel("回测监控")
        monitor_section_layout.addWidget(monitor_title)
        
        # 回测状态
        status_layout = QHBoxLayout()
        status_layout.setSpacing(32)
        
        status_layout.addWidget(QLabel("回测状态：准备就绪"))
        status_layout.addWidget(QLabel("已运行时间：00:00:00"))
        status_layout.addWidget(QLabel("预计剩余时间：--:--:--"))
        
        monitor_section_layout.addLayout(status_layout)
        
        # 进度条
        progress_bar = QFrame()
        progress_bar_layout = QHBoxLayout(progress_bar)
        progress_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        progress_fill = QFrame()
        progress_bar_layout.addWidget(progress_fill)
        
        monitor_section_layout.addWidget(progress_bar)
        
        # 回测数据曲线
        chart_placeholder = QLabel("实时回测数据曲线将显示在此处")
        chart_placeholder.setAlignment(Qt.AlignCenter)
        monitor_section_layout.addWidget(chart_placeholder, 1)
        
        layout.addWidget(monitor_section, 1)
        
        # 回测结果区
        results_section = QFrame()
        results_section_layout = QHBoxLayout(results_section)
        results_section_layout.setSpacing(16)
        
        # 结果统计
        result_stats = QFrame()
        result_stats_layout = QGridLayout(result_stats)
        result_stats_layout.setSpacing(16)
        
        result_stats_layout.addWidget(QLabel("总数据量："), 0, 0)
        result_stats_layout.addWidget(QLabel("0"), 0, 1)
        result_stats_layout.addWidget(QLabel("成功记录："), 0, 2)
        result_stats_layout.addWidget(QLabel("0"), 0, 3)
        result_stats_layout.addWidget(QLabel("失败记录："), 1, 0)
        result_stats_layout.addWidget(QLabel("0"), 1, 1)
        result_stats_layout.addWidget(QLabel("成功率："), 1, 2)
        result_stats_layout.addWidget(QLabel("0%"), 1, 3)
        
        results_section_layout.addWidget(result_stats)
        
        layout.addWidget(results_section)
        
        return workspace
    
    def _create_analysis_workspace(self):
        """创建数据分析工作区"""
        workspace = QWidget()
        
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(16)
        
        # 数据选择区
        data_selection = QFrame()
        data_selection_layout = QGridLayout(data_selection)
        data_selection_layout.setSpacing(16)
        
        # 设备选择
        device_select = QFrame()
        device_select_layout = QVBoxLayout(device_select)
        
        device_select_layout.addWidget(QLabel("选择设备："))
        device_select_layout.addWidget(QFrame())
        
        data_selection_layout.addWidget(device_select, 0, 0)
        
        # 日期范围
        date_select = QFrame()
        date_select_layout = QVBoxLayout(date_select)
        
        date_select_layout.addWidget(QLabel("开始日期："))
        date_select_layout.addWidget(QFrame())
        date_select_layout.addWidget(QLabel("结束日期："))
        date_select_layout.addWidget(QFrame())
        
        data_selection_layout.addWidget(date_select, 0, 1)
        
        # 数据项选择
        data_item_select = QFrame()
        data_item_select_layout = QVBoxLayout(data_item_select)
        
        data_item_select_layout.addWidget(QLabel("选择数据项："))
        data_item_select_layout.addWidget(QFrame())
        
        data_selection_layout.addWidget(data_item_select, 0, 2)
        
        layout.addWidget(data_selection)
        
        # 数据可视化区
        visualization = QFrame()
        visualization_layout = QVBoxLayout(visualization)
        
        visualization_title = QLabel("数据可视化")
        visualization_layout.addWidget(visualization_title)
        
        # 图表类型选择
        chart_type_layout = QHBoxLayout()
        chart_type_layout.setSpacing(16)
        
        chart_type_layout.addWidget(QLabel("图表类型："))
        chart_type_layout.addWidget(QFrame())
        chart_type_layout.addStretch()
        
        visualization_layout.addLayout(chart_type_layout)
        
        # 图表区域
        chart_area = QFrame()
        chart_area_layout = QVBoxLayout(chart_area)
        
        chart_placeholder = QLabel("数据可视化图表将显示在此处")
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_area_layout.addWidget(chart_placeholder, 1)
        
        visualization_layout.addWidget(chart_area, 1)
        
        layout.addWidget(visualization, 1)
        
        # 报告生成区
        report_generation = QFrame()
        report_generation_layout = QVBoxLayout(report_generation)
        
        report_title = QLabel("报告生成")
        report_generation_layout.addWidget(report_title)
        
        # 报告类型选择
        report_types = QFrame()
        report_types_layout = QVBoxLayout(report_types)
        
        report_types_layout.addWidget(QLabel("报告类型："))
        report_types_layout.addWidget(QLabel("□ 故障分析报告"))
        report_types_layout.addWidget(QLabel("□ 调节性能分析"))
        report_types_layout.addWidget(QLabel("□ 调控效果分析"))
        report_types_layout.addWidget(QLabel("□ 设备利用率分析"))
        report_types_layout.addWidget(QLabel("□ 收益分析"))
        
        report_generation_layout.addWidget(report_types)
        
        # 报告配置
        report_config = QFrame()
        report_config_layout = QGridLayout(report_config)
        report_config_layout.setSpacing(16)
        
        report_config_layout.addWidget(QLabel("报告格式："), 0, 0)
        report_config_layout.addWidget(QFrame(), 0, 1)
        report_config_layout.addWidget(QLabel("包含图表："), 0, 2)
        report_config_layout.addWidget(QLabel("□ 是   □ 否"), 0, 3)
        
        report_generation_layout.addWidget(report_config)
        
        # 生成报告按钮
        generate_button = QPushButton("生成报告")
        report_generation_layout.addWidget(generate_button, 0, Qt.AlignRight)
        
        layout.addWidget(report_generation)
        
        return workspace
    

    
    def _setup_layout(self):
        """设置布局"""
        # 创建中央部件
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 添加侧边栏和工作区
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.workspace_tabs, 1)
        
        self.setCentralWidget(central_widget)
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        # 不创建菜单栏，根据需求删除全局菜单栏
        pass
    
    def _create_tool_bar(self):
        """创建工具栏"""
        # 不创建工具栏，根据需求删除全局工具栏
        pass
    
    def _setup_status_bar(self):
        """设置状态栏"""
        status_bar = self.statusBar()
        status_bar.addWidget(self.status_panel)
    
    def _connect_signals(self):
        """连接信号槽"""
        # 连接工作区标签页信号
        self.workspace_tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        
        # 连接拓扑画布和属性编辑器的信号
        self.topology_canvas.device_selected.connect(self.property_editor.update_device_properties)
        self.topology_canvas.selection_cleared.connect(lambda: self.property_editor.update_device_properties(None))
        # 连接属性更新信号到应用层处理
        self.property_editor.element_updated.connect(self._on_device_property_updated)
    
    def _on_device_property_updated(self, properties):
        """处理设备属性更新"""
        try:
            from application.commands.topology.topology_commands import UpdateDeviceCommand
            from domain.aggregates.topology.value_objects.topology_id import TopologyId
            from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
            
            # 获取当前拓扑ID
            topology_id_str = getattr(self.topology_canvas, "current_topology_id", "default_topology")
            
            device_id = str(properties.get("id"))
            name = properties.get("name")
            
            # 移除 id, type, name，剩下的作为 device properties
            device_props = properties.copy()
            if "id" in device_props:
                del device_props["id"]
            if "type" in device_props:
                del device_props["type"]
            if "name" in device_props:
                del device_props["name"]
            
            command = UpdateDeviceCommand(
                topology_id=TopologyId(topology_id_str),
                device_id=device_id,
                name=name,
                properties=DeviceProperties(device_props)
            )
            
            self.application.topology_device_management_use_case.update_device(command)
            
            # 记录快照用于撤销/重做
            if hasattr(self.application, "topology_undo_redo_use_case"):
                data = self.topology_canvas.get_topology_data()
                self.application.topology_undo_redo_use_case.snapshot(data)
                
        except Exception as e:
            print(f"Error updating device properties: {e}")

    def _on_topology_clicked(self):
        """拓扑设计按钮点击事件"""
        self._set_active_module("topology")
        # 检查标签页是否存在，不存在则重新创建
        self._ensure_tab_exists(0, "拓扑设计", self._create_topology_workspace)
    
    def _on_monitoring_clicked(self):
        """实时监控按钮点击事件"""
        self._set_active_module("monitoring")
        # 检查标签页是否存在，不存在则重新创建
        self._ensure_tab_exists(1, "实时监控", self._create_monitoring_workspace)
    
    def _on_control_clicked(self):
        """设备控制按钮点击事件"""
        self._set_active_module("control")
        # 检查标签页是否存在，不存在则重新创建
        self._ensure_tab_exists(2, "设备控制", self._create_control_workspace)
    
    def _on_backtest_clicked(self):
        """数据回测按钮点击事件"""
        self._set_active_module("backtest")
        # 检查标签页是否存在，不存在则重新创建
        self._ensure_tab_exists(3, "数据回测", self._create_backtest_workspace)
    
    def _on_analysis_clicked(self):
        """数据分析按钮点击事件"""
        self._set_active_module("analysis")
        # 检查标签页是否存在，不存在则重新创建
        self._ensure_tab_exists(4, "数据分析", self._create_analysis_workspace)
    
    def _ensure_tab_exists(self, index, tab_name, create_func):
        """确保指定索引的标签页存在，如果不存在则重新创建"""
        # 检查标签页数量，如果小于等于索引，或者标签页标题不匹配，则重新创建
        tab_exists = False
        tab_index = -1
        
        # 遍历现有标签页，查找是否存在同名标签页
        for i in range(self.workspace_tabs.count()):
            if self.workspace_tabs.tabText(i) == tab_name:
                tab_exists = True
                tab_index = i
                break
        
        if not tab_exists:
            # 创建新标签页
            workspace = create_func()
            tab_index = self.workspace_tabs.addTab(workspace, tab_name)
        
        # 切换到该标签页
        self.workspace_tabs.setCurrentIndex(tab_index)
    
    def _set_active_module(self, module_name):
        """设置当前活动模块"""
        for name, button in self.module_buttons.items():
            button.setChecked(name == module_name)
    
    def _on_tab_close_requested(self, index):
        """标签页关闭请求事件"""
        self.workspace_tabs.removeTab(index)
    
    def _on_about(self):
        """关于事件"""
        QMessageBox.about(self, "关于", "光储充微电网系统 v1.0\n基于DDD六边形架构设计")

    def _on_new_topology(self):
        # 通过 UI 适配器创建拓扑
        try:
            from application.commands.topology.topology_commands import CreateTopologyCommand
            self.application.topology_creation_use_case.create_topology(
                CreateTopologyCommand(name="新建拓扑", description="")
            )
        except Exception:
            pass
        # 清空画布并记录快照
        self.topology_canvas.load_topology_data({"devices": []})
        if hasattr(self.application, "topology_undo_redo_use_case"):
            self.application.topology_undo_redo_use_case.snapshot(self.topology_canvas.get_topology_data())

    def _on_open_topology(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打开拓扑", "", "JSON Files (*.json)")
        if not file_path:
            return
        
        try:
            # 使用新的加载逻辑，加载并持久化拓扑实体
            topology = self.application.topology_file_use_case.load_topology(file_path)
            
            # 更新 Canvas 当前拓扑 ID
            if hasattr(self.topology_canvas, "current_topology_id"):
                self.topology_canvas.current_topology_id = str(topology.id)
            
            # 渲染
            canvas_data = self.application.topology_file_use_case.topology_to_canvas_data(topology)
            self.topology_canvas.render_topology(canvas_data["devices"])
            
            if hasattr(self.application, "topology_undo_redo_use_case"):
                self.application.topology_undo_redo_use_case.snapshot(self.topology_canvas.get_topology_data())
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载拓扑失败: {str(e)}")

    def _on_save_topology(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存拓扑", "topology.json", "JSON Files (*.json)")
        if not file_path:
            return
            
        try:
            # 尝试保存完整的拓扑实体
            current_id = getattr(self.topology_canvas, "current_topology_id", None)
            if current_id and self.application.topology_file_use_case.save_topology_by_id(file_path, str(current_id)):
                QMessageBox.information(self, "成功", "拓扑保存成功")
            else:
                # 降级：仅保存 Canvas 数据
                data = self.topology_canvas.get_topology_data()
                self.application.topology_file_use_case.save(file_path, data)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存拓扑失败: {str(e)}")

    def _on_import_topology(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入拓扑", "", "JSON Files (*.json)")
        if not file_path:
            return
        data = self.application.topology_file_use_case.import_json(file_path)
        self.topology_canvas.load_topology_data(data)
        if hasattr(self.application, "topology_undo_redo_use_case"):
            self.application.topology_undo_redo_use_case.snapshot(self.topology_canvas.get_topology_data())

    def _on_export_topology(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "导出拓扑", "topology_export.json", "JSON Files (*.json)")
        if not file_path:
            return
        data = self.topology_canvas.get_topology_data()
        self.application.topology_file_use_case.export_json(file_path, data)

    def _on_undo(self):
        state = self.application.topology_undo_redo_use_case.undo()
        if state:
            self.topology_canvas.load_topology_data(state)

    def _on_redo(self):
        state = self.application.topology_undo_redo_use_case.redo()
        if state:
            self.topology_canvas.load_topology_data(state)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    from application.app import Application
    
    # 初始化应用程序
    app = Application()
    
    # 创建PySide应用程序
    qt_app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainApplication(app)
    window.show()
    
    # 运行应用程序
    sys.exit(qt_app.exec())
