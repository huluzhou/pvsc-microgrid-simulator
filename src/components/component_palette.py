#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
组件面板，用于显示可拖拽的电网组件
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Qt, QMimeData, QSize
from PySide6.QtGui import QDrag, QPixmap, QIcon


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

        # 暂时使用文本代替图标
        for component in components:
            item = QListWidgetItem(component["name"])
            item.setData(Qt.UserRole, component["type"])
            # 设置图标
            icon_path = f"src/assets/{component['icon']}"
            item.setIcon(QIcon(icon_path))
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
        icon_path = f"src/assets/{component_type}.svg"
        pixmap = QIcon(icon_path).pixmap(64, 64)

        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        # 执行拖拽
        drag.exec_(Qt.CopyAction)