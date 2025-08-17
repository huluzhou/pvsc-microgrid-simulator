#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主窗口组件
"""

from PyQt5.QtWidgets import QMainWindow, QDockWidget, QToolBar, QAction, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from components.canvas import NetworkCanvas
from components.component_palette import ComponentPalette


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowTitle("PandaPower 仿真工具")
        self.setMinimumSize(1000, 800)

        # 创建中央画布
        self.canvas = NetworkCanvas(self)
        self.setCentralWidget(self.canvas)

        # 创建组件面板
        self.create_component_palette()

        # 创建工具栏
        self.create_toolbar()

        # 创建菜单栏
        self.create_menu()

        # 状态栏
        self.statusBar().showMessage("就绪")

    def create_component_palette(self):
        """创建组件面板"""
        # 创建组件面板
        self.component_dock = QDockWidget("电网组件", self)
        self.component_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # 组件面板内容
        self.component_palette = ComponentPalette(self)
        self.component_dock.setWidget(self.component_palette)
        
        # 添加到主窗口
        self.addDockWidget(Qt.LeftDockWidgetArea, self.component_dock)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("工具栏", self)
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)

        # 添加工具栏按钮
        # 这里将来会添加保存、加载、运行仿真等按钮
        # 暂时使用占位符
        toolbar.addAction("新建")
        toolbar.addAction("打开")
        toolbar.addAction("保存")
        toolbar.addSeparator()
        toolbar.addAction("运行仿真")

    def create_menu(self):
        """创建菜单栏"""
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = self.menuBar().addMenu("编辑")
        edit_menu.addAction("撤销")
        edit_menu.addAction("重做")
        edit_menu.addSeparator()
        edit_menu.addAction("删除所选")
        edit_menu.addAction("全选")
        
        # 视图菜单
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.component_dock.toggleViewAction())
        
        # 仿真菜单
        sim_menu = self.menuBar().addMenu("仿真")
        sim_menu.addAction("运行潮流计算")
        sim_menu.addAction("短路分析")
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 PandaPower 仿真工具",
            "<h3>PandaPower 仿真工具</h3>"
            "<p>基于PyQt和pandapower的电网仿真工具</p>"
            "<p>版本: 0.1.0</p>"
        )