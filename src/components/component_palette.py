#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
组件面板，用于显示可拖拽的电网组件
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QApplication
from PySide6.QtCore import Qt, QMimeData, QSize
from PySide6.QtGui import QDrag, QPixmap, QIcon, QPalette
from PySide6.QtSvg import QSvgRenderer
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

    def is_dark_theme(self):
        """检测是否为深色主题"""
        app = QApplication.instance()
        if app:
            palette = app.palette()
            window_color = palette.color(QPalette.Window)
            return window_color.lightness() < 128
        return False

    def adapt_svg_for_theme(self, svg_path):
        """根据主题适配SVG颜色"""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            if self.is_dark_theme():
                # 深色主题：将黑色元素替换为白色
                svg_content = svg_content.replace('stroke="black"', 'stroke="white"')
                svg_content = svg_content.replace('fill="black"', 'fill="white"')
                svg_content = svg_content.replace('stroke="#000000"', 'stroke="#ffffff"')
                svg_content = svg_content.replace('fill="#000000"', 'fill="#ffffff"')
                svg_content = svg_content.replace('stroke="#000"', 'stroke="#fff"')
                svg_content = svg_content.replace('fill="#000"', 'fill="#fff"')
                svg_content = svg_content.replace('stroke="#333333"', 'stroke="#cccccc"')
                svg_content = svg_content.replace('fill="#333333"', 'fill="#cccccc"')
            else:
                # 浅色主题：将白色元素替换为黑色
                svg_content = svg_content.replace('stroke="white"', 'stroke="black"')
                svg_content = svg_content.replace('fill="white"', 'fill="black"')
                svg_content = svg_content.replace('stroke="#ffffff"', 'stroke="#000000"')
                svg_content = svg_content.replace('fill="#ffffff"', 'fill="#000000"')
                svg_content = svg_content.replace('stroke="#fff"', 'stroke="#000"')
                svg_content = svg_content.replace('fill="#fff"', 'fill="#000"')
                svg_content = svg_content.replace('stroke="#cccccc"', 'stroke="#333333"')
                svg_content = svg_content.replace('fill="#cccccc"', 'fill="#333333"')
            
            return svg_content
        except Exception as e:
            print(f"Error adapting SVG for theme: {e}")
            return None

    def create_themed_icon(self, svg_path, size=64):
        """创建适配主题的图标"""
        svg_content = self.adapt_svg_for_theme(svg_path)
        if svg_content:
            renderer = QSvgRenderer()
            renderer.load(svg_content.encode('utf-8'))
            
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            
            from PySide6.QtGui import QPainter
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            return QIcon(pixmap)
        return QIcon()

    def add_components(self):
        """添加电网组件到面板"""
        # 添加各种电网组件
        components = [
            {"name": "母线", "type": "bus", "icon": "bus.svg"},
            {"name": "线路", "type": "line", "icon": "line.svg"},
            {"name": "变压器", "type": "transformer", "icon": "transformer.svg"},
            {"name": "光伏", "type": "static_generator", "icon": "static_generator.svg"},
            {"name": "负载", "type": "load", "icon": "load.svg"},
            {"name": "储能", "type": "storage", "icon": "storage.svg"},
            {"name": "充电站", "type": "charger", "icon": "charger.svg"},
            {"name": "外部电网", "type": "external_grid", "icon": "external_grid.svg"},
            {"name": "电表", "type": "meter", "icon": "meter.svg"},
        ]

        # 使用正确的资源路径加载图标
        for component in components:
            item = QListWidgetItem(component["name"])
            item.setData(Qt.UserRole, component["type"])
            # 设置图标 - 使用主题适配的图标
            try:
                # 使用统一的资源路径函数
                from config import get_resource_path
                icon_path = get_resource_path(component['icon'])
                if os.path.exists(icon_path):
                    themed_icon = self.create_themed_icon(icon_path, 64)
                    item.setIcon(themed_icon)
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
            # 使用统一的资源路径函数
            from config import get_resource_path
            icon_path = get_resource_path(f"{component_type}.svg")
            if os.path.exists(icon_path):
                themed_icon = self.create_themed_icon(icon_path, 64)
                pixmap = themed_icon.pixmap(64, 64)
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