#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
组件面板，用于显示可拖拽的电网组件
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QApplication, QFrame, QVBoxLayout, QLabel, QWidget, QScrollArea
from PySide6.QtCore import Qt, QMimeData, QSize, Signal
from PySide6.QtGui import QDrag, QPixmap, QIcon
import os

# 导入当前架构的日志系统
from infrastructure.logging import logger

# 获取资源文件的相对路径
def get_resource_path(icon_name):
    """获取资源文件的相对路径"""
    import os
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建资源文件的相对路径
    assets_dir = os.path.join(current_dir, "..", "assets")
    return os.path.join(assets_dir, icon_name)

class CustomDevicePanel(QFrame):
    """自定义设备面板，基于component_palette.py实现"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 设备列表标题 - 行业规范：14px，加粗
        title = QLabel("设备列表")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # 垂直滚动区域，保证在小屏幕下仍可完整显示所有设备
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        
        # 设备分类
        categories = [
            {"name": "节点设备", "devices": [
                {"name": "母线", "type": "bus", "icon": "bus.svg"}
            ]},
            {"name": "连接设备", "devices": [
                {"name": "线路", "type": "line", "icon": "line.svg"},
                {"name": "变压器", "type": "transformer", "icon": "transformer.svg"},
                {"name": "开关", "type": "switch", "icon": "switch.svg"}
            ]},
            {"name": "功率设备", "devices": [
                {"name": "光伏", "type": "static_generator", "icon": "static_generator.svg"},
                {"name": "储能", "type": "storage", "icon": "storage.svg"},
                {"name": "负载", "type": "load", "icon": "load.svg"},
                {"name": "充电桩", "type": "charger", "icon": "charger.svg"},
                {"name": "外部电网", "type": "external_grid", "icon": "external_grid.svg"}
            ]},
            {"name": "测量设备", "devices": [
                {"name": "电表", "type": "meter", "icon": "meter.svg"}
            ]}
        ]
        
        for category in categories:
            # 创建分类容器
            category_widget = QWidget()
            category_layout = QVBoxLayout(category_widget)
            category_layout.setContentsMargins(0, 0, 0, 0)
            category_layout.setSpacing(4)
            
            # 分类标题 - 添加背景色和边框，使其看起来像独立的板块
            title_label = QLabel(category["name"])
            title_label.setStyleSheet("""
                QLabel {
                    font-size: 12px; 
                    font-weight: bold; 
                    color: #333333;
                    background-color: #f0f0f0;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
            """)
            category_layout.addWidget(title_label)
            
            # 创建组件面板
            component_palette = ComponentPalette(self)
            component_palette.set_components(category["devices"])
            category_layout.addWidget(component_palette)
            if category["name"] == "功率设备":
                category_widget.setMinimumHeight(component_palette.height() + 40)
            content_layout.addWidget(category_widget)
        
        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area, 1)
    

class ComponentPalette(QListWidget):
    """组件面板类，显示可拖拽的电网组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.components = []
    
    def init_ui(self):
        """初始化UI"""
        # 设置拖拽模式
        self.setDragEnabled(True)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(40, 40))  # 稍微增大图标
        self.setSpacing(4)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)
        self.setFlow(QListWidget.LeftToRight)
        self.setWrapping(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setSelectionBehavior(QListWidget.SelectItems)
        
        # 固定网格大小
        self.setGridSize(QSize(120, 100))
        
        # 固定布局与滚动条策略
        self.setResizeMode(QListWidget.Fixed)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                padding: 0px;
            }
            QListWidget::item {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: #e6f3ff;
                border-color: #2196F3;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)

    def resizeEvent(self, event):
        """处理大小调整事件"""
        super().resizeEvent(event)

    def set_components(self, components):
        """设置组件列表"""
        self.components = components
        self.clear()  # 清空现有项
        self.add_components()
        # 固定两列网格下的宽高
        grid_w = self.gridSize().width()
        grid_h = self.gridSize().height()
        cols = 2
        count = self.count()
        rows = (count + cols - 1) // cols
        fixed_width = cols * grid_w + 8
        fixed_height = rows * grid_h + 12
        self.setFixedWidth(fixed_width)
        self.setFixedHeight(fixed_height)
    
    def add_components(self):
        """添加电网组件到面板"""
        # 使用正确的资源路径加载图标
        for component in self.components:
            item = QListWidgetItem(component["name"])
            item.setData(Qt.UserRole, component["type"])
            # 设置图标 - 直接使用QIcon，不进行主题适配
            try:
                # 使用统一的资源路径函数
                icon_path = get_resource_path(component['icon'])
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
                    item.setIcon(icon)
                else:
                    logger.warning(f"Warning: Icon file not found: {icon_path}")
            except Exception as e:
                logger.error(f"Error loading icon for {component['name']}: {e}")
            self.addItem(item)

    def startDrag(self, supportedActions):
        """开始拖拽操作"""
        item = self.currentItem()
        if not item:
            return

        # 获取组件类型
        component_type = item.data(Qt.UserRole)

        # 创建MIME数据
        mime_data = QMimeData()
        mime_data.setText(component_type)

        # 创建拖拽对象
        drag = QDrag(self)
        drag.setMimeData(mime_data)

        # 设置拖拽时的图像 - 直接使用QIcon，不进行主题适配
        component_type = item.data(Qt.UserRole)
        try:
            # 使用统一的资源路径函数
            icon_path = get_resource_path(f"{component_type}.svg")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                pixmap = icon.pixmap(64, 64)
            else:
                # 如果图标不存在，创建一个默认的pixmap
                pixmap = QPixmap(64, 64)
                pixmap.fill()
        except Exception as e:
            logger.error(f"Error loading drag icon for {component_type}: {e}")
            pixmap = QPixmap(64, 64)
            pixmap.fill()

        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        # 执行拖拽
        result = drag.exec_(Qt.CopyAction)
        
        # 拖拽完成后清除选中状态，避免设备背景一直为灰色
        self.clearSelection()
