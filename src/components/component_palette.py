#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
组件面板，用于显示可拖拽的电网组件
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Qt, QMimeData, QSize
from PySide6.QtGui import QDrag, QPixmap, QIcon
import os


class ComponentPalette(QListWidget):
    """组件面板类，显示可拖拽的电网组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 设置拖拽模式
        self.setDragEnabled(True)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(64, 64))
        self.setSpacing(10)
        self.setAcceptDrops(False)
        self.setDropIndicatorShown(True)

        # 添加电网组件
        self.add_components()

    def add_components(self):
        """添加电网组件到面板"""
        # 添加各种电网组件
        components = [
            {"name": "母线", "type": "bus", "icon": "bus.svg"},
            {"name": "线路", "type": "line", "icon": "line.svg"},
            {"name": "变压器", "type": "transformer", "icon": "transformer.svg"},
            {"name": "发电机", "type": "generator", "icon": "generator.svg"},
            {"name": "负载", "type": "load", "icon": "load.svg"},
            {"name": "开关", "type": "switch", "icon": "switch.svg"},
        ]

        # 使用正确的资源路径加载图标
        for component in components:
            item = QListWidgetItem(component["name"])
            item.setData(Qt.UserRole, component["type"])
            # 设置图标 - 使用资源路径函数
            try:
                from components.main_window import MainWindow
                icon_path = MainWindow.get_resource_path(f"assets/{component['icon']}")
                if os.path.exists(icon_path):
                    item.setIcon(QIcon(icon_path))
                else:
                    print(f"Warning: Icon file not found: {icon_path}")
            except Exception as e:
                print(f"Error loading icon for {component['name']}: {e}")
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

        # 设置拖拽时的图像
        component_type = item.data(Qt.UserRole)
        try:
            from components.main_window import MainWindow
            icon_path = MainWindow.get_resource_path(f"assets/{component_type}.svg")
            if os.path.exists(icon_path):
                pixmap = QIcon(icon_path).pixmap(64, 64)
            else:
                # 如果图标不存在，创建一个默认的pixmap
                pixmap = QPixmap(64, 64)
                pixmap.fill()
        except Exception as e:
            print(f"Error loading drag icon for {component_type}: {e}")
            pixmap = QPixmap(64, 64)
            pixmap.fill()

        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        # 执行拖拽
        drag.exec_(Qt.CopyAction)