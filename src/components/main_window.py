#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主窗口组件
"""

from PySide6.QtWidgets import QMainWindow, QDockWidget, QToolBar, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QAction

from components.canvas import NetworkCanvas
from components.component_palette import ComponentPalette
from components.properties_panel import PropertiesPanel


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
        
        # 创建属性面板
        self.create_properties_panel()

        # 创建工具栏
        self.create_toolbar()

        # 创建菜单栏
        self.create_menu()

        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 初始化主题颜色
        self.update_theme_colors()

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
        
    def create_properties_panel(self):
        """创建属性面板"""
        # 创建属性面板停靠窗口
        self.properties_dock = QDockWidget("组件属性", self)
        self.properties_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # 属性面板内容
        self.properties_panel = PropertiesPanel(self)
        self.properties_dock.setWidget(self.properties_panel)
        
        # 添加到主窗口右侧
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)
        
        # 连接画布选择事件到属性面板更新
        self.canvas.selection_changed.connect(self.properties_panel.update_properties)
        
        # 连接属性面板的属性变化信号
        self.properties_panel.property_changed.connect(self.on_property_changed)

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
        
        # 断开连接动作
        disconnect_action = QAction("断开连接", self)
        disconnect_action.setShortcut("Ctrl+D")
        disconnect_action.triggered.connect(self.disconnect_selected)
        edit_menu.addAction(disconnect_action)
        
        # 删除动作
        delete_action = QAction("删除所选", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)
        
        edit_menu.addAction("全选")
        
        # 视图菜单
        view_menu = self.menuBar().addMenu("视图")
        view_menu.addAction(self.component_dock.toggleViewAction())
        view_menu.addAction(self.properties_dock.toggleViewAction())
        view_menu.addSeparator()
        
        # 缩放操作
        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        fit_view_action = QAction("适应视图", self)
        fit_view_action.setShortcut("Ctrl+0")
        fit_view_action.triggered.connect(self.fit_view)
        view_menu.addAction(fit_view_action)
        
        view_menu.addSeparator()
        
        # 主题切换
        theme_action = QAction("切换主题", self)
        theme_action.setShortcut("Ctrl+T")
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        # 仿真菜单
        sim_menu = self.menuBar().addMenu("仿真")
        sim_menu.addAction("运行潮流计算")
        sim_menu.addAction("短路分析")
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def disconnect_selected(self):
        """断开选中设备的连接"""
        self.canvas.disconnect_all_from_selected()
        self.statusBar().showMessage("已断开选中设备的连接")
    
    def delete_selected(self):
        """删除选中的项目"""
        self.canvas.delete_selected_items()
        self.statusBar().showMessage("已删除选中项目")
    
    def zoom_in(self):
        """放大视图"""
        self.canvas.scale(1.15, 1.15)
        self.statusBar().showMessage("视图已放大")
    
    def zoom_out(self):
        """缩小视图"""
        self.canvas.scale(1.0 / 1.15, 1.0 / 1.15)
        self.statusBar().showMessage("视图已缩小")
    
    def fit_view(self):
        """适应视图"""
        self.canvas.fit_in_view()
        self.statusBar().showMessage("视图已适应画布内容")
    
    def toggle_theme(self):
        """切换主题"""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPalette, QColor
        
        app = QApplication.instance()
        if app:
            palette = app.palette()
            # 检查当前是否为深色主题
            bg_color = palette.color(QPalette.Window)
            is_dark_theme = bg_color.lightness() < 128
            
            # 创建新的调色板
            new_palette = QPalette()
            
            if is_dark_theme:
                # 当前是深色主题，切换到浅色主题
                new_palette.setColor(QPalette.Window, QColor(240, 240, 240))
                new_palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
                new_palette.setColor(QPalette.Base, QColor(255, 255, 255))
                new_palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
                new_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
                new_palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
                new_palette.setColor(QPalette.Text, QColor(0, 0, 0))
                new_palette.setColor(QPalette.Button, QColor(240, 240, 240))
                new_palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
                new_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
                new_palette.setColor(QPalette.Link, QColor(0, 0, 255))
                new_palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
                new_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
                self.statusBar().showMessage("已切换到浅色主题")
            else:
                # 当前是浅色主题，切换到深色主题
                new_palette.setColor(QPalette.Window, QColor(53, 53, 53))
                new_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
                new_palette.setColor(QPalette.Base, QColor(25, 25, 25))
                new_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
                new_palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
                new_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
                new_palette.setColor(QPalette.Text, QColor(255, 255, 255))
                new_palette.setColor(QPalette.Button, QColor(53, 53, 53))
                new_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
                new_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
                new_palette.setColor(QPalette.Link, QColor(42, 130, 218))
                new_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
                new_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
                self.statusBar().showMessage("已切换到深色主题")
            
            # 应用新的调色板
            app.setPalette(new_palette)
            
            # 设置菜单栏样式表
            if is_dark_theme:
                # 浅色主题菜单样式
                menu_style = """
                QMenuBar {
                    background-color: rgb(240, 240, 240);
                    color: rgb(0, 0, 0);
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 4px 8px;
                }
                QMenuBar::item:selected {
                    background-color: rgb(0, 120, 215);
                    color: rgb(255, 255, 255);
                }
                QMenu {
                    background-color: rgb(255, 255, 255);
                    color: rgb(0, 0, 0);
                    border: 1px solid rgb(200, 200, 200);
                }
                QMenu::item {
                    padding: 4px 20px;
                }
                QMenu::item:selected {
                    background-color: rgb(0, 120, 215);
                    color: rgb(255, 255, 255);
                }
                QMenu::separator {
                    height: 1px;
                    background-color: rgb(200, 200, 200);
                    margin: 2px 0px;
                }
                """
            else:
                # 深色主题菜单样式
                menu_style = """
                QMenuBar {
                    background-color: rgb(53, 53, 53);
                    color: rgb(255, 255, 255);
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 4px 8px;
                }
                QMenuBar::item:selected {
                    background-color: rgb(42, 130, 218);
                    color: rgb(255, 255, 255);
                }
                QMenu {
                    background-color: rgb(53, 53, 53);
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(80, 80, 80);
                }
                QMenu::item {
                    padding: 4px 20px;
                }
                QMenu::item:selected {
                    background-color: rgb(42, 130, 218);
                    color: rgb(255, 255, 255);
                }
                QMenu::separator {
                    height: 1px;
                    background-color: rgb(80, 80, 80);
                    margin: 2px 0px;
                }
                """
            
            # 应用菜单样式
            self.menuBar().setStyleSheet(menu_style)
            
            # 更新所有主题相关的颜色
            self.update_theme_colors()
    
    def update_theme_colors(self):
        """更新主题相关的所有颜色"""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPalette
        
        # 获取当前主题
        app = QApplication.instance()
        if app:
            palette = app.palette()
            bg_color = palette.color(QPalette.Window)
            is_dark_theme = bg_color.lightness() < 128
            
            # 设置菜单栏样式
            if is_dark_theme:
                # 深色主题菜单样式
                menu_style = """
                QMenuBar {
                    background-color: rgb(53, 53, 53);
                    color: rgb(255, 255, 255);
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 4px 8px;
                }
                QMenuBar::item:selected {
                    background-color: rgb(42, 130, 218);
                    color: rgb(255, 255, 255);
                }
                QMenu {
                    background-color: rgb(53, 53, 53);
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(80, 80, 80);
                }
                QMenu::item {
                    padding: 4px 20px;
                }
                QMenu::item:selected {
                    background-color: rgb(42, 130, 218);
                    color: rgb(255, 255, 255);
                }
                QMenu::separator {
                    height: 1px;
                    background-color: rgb(80, 80, 80);
                    margin: 2px 0px;
                }
                """
            else:
                # 浅色主题菜单样式
                menu_style = """
                QMenuBar {
                    background-color: rgb(240, 240, 240);
                    color: rgb(0, 0, 0);
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 4px 8px;
                }
                QMenuBar::item:selected {
                    background-color: rgb(0, 120, 215);
                    color: rgb(255, 255, 255);
                }
                QMenu {
                    background-color: rgb(255, 255, 255);
                    color: rgb(0, 0, 0);
                    border: 1px solid rgb(200, 200, 200);
                }
                QMenu::item {
                    padding: 4px 20px;
                }
                QMenu::item:selected {
                    background-color: rgb(0, 120, 215);
                    color: rgb(255, 255, 255);
                }
                QMenu::separator {
                    height: 1px;
                    background-color: rgb(200, 200, 200);
                    margin: 2px 0px;
                }
                """
            
            # 应用菜单样式
            self.menuBar().setStyleSheet(menu_style)
        
        # 更新画布主题颜色
        if hasattr(self, 'canvas'):
            self.canvas.update_theme_colors()
        
        # 更新组件面板主题
        if hasattr(self, 'component_palette'):
            # 清空并重新添加组件以适应新主题
            self.component_palette.clear()
            self.component_palette.add_components()
        
        # 更新属性面板主题
        if hasattr(self, 'properties_panel'):
            self.properties_panel.update_theme_colors()
    
    def on_property_changed(self, component_type, prop_name, new_value):
        """处理组件属性变化事件"""
        try:
            # 获取当前选中的组件
            current_item = self.properties_panel.current_item
            if not current_item:
                return
            
            # 如果是名称属性变化，需要更新网络模型中的名称
            if prop_name == 'name':
                # 更新网络模型（如果存在）
                if hasattr(self.canvas, 'network_model') and self.canvas.network_model:
                    # 这里可以添加网络模型更新逻辑
                    pass
                
                # 强制刷新画布显示
                self.canvas.scene.update()
                
            print(f"属性更新: {component_type}.{prop_name} = {new_value}")
            
        except Exception as e:
            print(f"处理属性变化时出错: {e}")
    
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 PandaPower 仿真工具",
            "<h3>PandaPower 仿真工具</h3>"
            "<p>基于PySide6和pandapower的电网仿真工具</p>"
            "<p>版本: 0.1.0</p>"
        )