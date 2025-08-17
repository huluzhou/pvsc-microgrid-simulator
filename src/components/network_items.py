#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
电网组件图形项，用于在画布上显示各种电网元件
"""

from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QObject, QRectF
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainterPath
from PyQt5.QtSvg import QSvgRenderer
import os


class ItemSignals(QObject):
    """用于发送图形项信号的类"""
    itemSelected = pyqtSignal(object)  # 选中信号


class BaseNetworkItem(QGraphicsItem):
    """电网组件基类"""

    def __init__(self, pos, parent=None):
        super().__init__(parent)
        self.setPos(pos)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        
        # 组件属性
        self.component_type = "base"
        self.component_name = "基础组件"
        self.properties = {}
        
        # 创建信号对象
        self.signals = ItemSignals()
        
        # SVG渲染器
        self.svg_renderer = None
        self.svg_size = 64  # SVG图标大小
        
        # 添加标签
        self.label = QGraphicsTextItem(self.component_name, self)
        self.label.setPos(-20, 35)  # 标签位置在组件下方
        self.label.setDefaultTextColor(QColor(0, 0, 0))  # 黑色
        
        # 设置Z值，确保组件在网格之上
        self.setZValue(10)
        
        # 连接点位置
        self.connection_points = []

    def load_svg(self, svg_filename):
        """加载SVG文件"""
        svg_path = os.path.join("src", "assets", svg_filename)
        if os.path.exists(svg_path):
            self.svg_renderer = QSvgRenderer(svg_path)
        else:
            print(f"SVG文件不存在: {svg_path}")

    def boundingRect(self):
        """返回边界矩形"""
        return QRectF(-32, -32, 64, 64)

    def paint(self, painter, option, widget):
        """绘制组件"""
        if self.svg_renderer and self.svg_renderer.isValid():
            # 使用SVG渲染
            rect = QRectF(-32, -32, 64, 64)
            self.svg_renderer.render(painter, rect)
            
            # 如果选中，绘制选中框
            if self.isSelected():
                pen = QPen(QColor(0, 0, 255), 2)  # 蓝色
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(rect)
        else:
            # 基类不实现具体绘制，由子类实现
            pass

    def itemChange(self, change, value):
        """项目变化事件"""
        if change == QGraphicsItem.ItemPositionChange:
            # 网格对齐
            grid_size = 50
            x = round(value.x() / grid_size) * grid_size
            y = round(value.y() / grid_size) * grid_size
            return QPointF(x, y)
        # 处理选择状态变化
        elif change == QGraphicsItem.ItemSelectedChange and value == True:
            # 发出选中信号
            self.signals.itemSelected.emit(self)
        # 处理位置已经改变
        elif change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            # 更新连接线
            self.update_connections()
        return super().itemChange(change, value)
        
    def update_connections(self):
        """更新与此组件相关的所有连接线"""
        # 获取场景
        scene = self.scene()
        if not scene:
            return
            
        # 获取画布
        views = scene.views()
        if not views:
            return
            
        canvas = views[0]
        if not hasattr(canvas, 'connections'):
            return
            
        # 更新所有与此组件相关的连接线
        for conn in canvas.connections:
            if conn['item1'] == self or conn['item2'] == self:
                # 获取连接点的场景坐标
                scene_point1 = conn['item1'].mapToScene(conn['point1'])
                scene_point2 = conn['item2'].mapToScene(conn['point2'])
                
                # 更新连接线
                conn['line'].setLine(
                    scene_point1.x(), scene_point1.y(),
                    scene_point2.x(), scene_point2.y()
                )
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        super().mousePressEvent(event)
        # 选中当前项
        self.setSelected(True)
        # 手动发出选中信号
        print(f"发出选中信号: {self.component_type}")
        self.signals.itemSelected.emit(self)


class BusItem(BaseNetworkItem):
    """母线组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "bus"
        self.component_name = "母线"
        self.properties = {
            "vn_kv": 110.0,  # 额定电压
            "name": "Bus 1",  # 名称
        }
        self.label.setPlainText(self.properties["name"])
        
        # 加载SVG图标
        self.load_svg("bus.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(-20, 0),  # 左侧
            QPointF(20, 0),   # 右侧
            QPointF(0, -10),  # 上侧
            QPointF(0, 10)    # 下侧
        ]


class LineItem(BaseNetworkItem):
    """线路组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "line"
        self.component_name = "线路"
        self.properties = {
            "length_km": 10.0,  # 线路长度
            "r_ohm_per_km": 0.1,  # 每公里电阻
            "x_ohm_per_km": 0.1,  # 每公里电抗
            "c_nf_per_km": 10,  # 每公里电容
            "name": "Line 1",  # 名称
        }
        self.label.setPlainText(self.properties["name"])
        
        # 加载SVG图标
        self.load_svg("line.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(-25, 0),  # 左侧
            QPointF(25, 0)    # 右侧
        ]


class TransformerItem(BaseNetworkItem):
    """变压器组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "transformer"
        self.component_name = "变压器"
        self.properties = {
            "sn_mva": 40.0,  # 额定容量
            "vn_hv_kv": 110.0,  # 高压侧额定电压
            "vn_lv_kv": 10.0,  # 低压侧额定电压
            "vk_percent": 10.0,  # 短路阻抗百分比
            "vkr_percent": 0.5,  # 短路损耗百分比
            "name": "Transformer 1",  # 名称
        }
        self.label.setPlainText(self.properties["name"])
        
        # 加载SVG图标
        self.load_svg("transformer.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(-20, -10),  # 左侧圆
            QPointF(20, -10)    # 右侧圆
        ]


class GeneratorItem(BaseNetworkItem):
    """发电机组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "generator"
        self.component_name = "发电机"
        self.properties = {
            "p_mw": 100.0,  # 有功功率
            "vm_pu": 1.0,  # 电压幅值标幺值
            "name": "Generator 1",  # 名称
        }
        self.label.setPlainText(self.properties["name"])
        
        # 加载SVG图标
        self.load_svg("generator.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(0, -20),  # 上侧
            QPointF(0, 20)    # 下侧
        ]


class LoadItem(BaseNetworkItem):
    """负载组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "load"
        self.component_name = "负载"
        self.properties = {
            "p_mw": 10.0,  # 有功功率
            "q_mvar": 5.0,  # 无功功率
            "name": "Load 1",  # 名称
        }
        self.label.setPlainText(self.properties["name"])
        
        # 加载SVG图标
        self.load_svg("load.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(0, -20),  # 上侧（三角形顶点）
            QPointF(-20, 20), # 左下角
            QPointF(20, 20)   # 右下角
        ]


class SwitchItem(BaseNetworkItem):
    """开关组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "switch"
        self.component_name = "开关"
        self.properties = {
            "closed": True,  # 开关状态
            "name": "Switch 1",  # 名称
        }
        self.label.setPlainText(self.properties["name"])
        
        # 加载SVG图标
        self.load_svg("switch.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(-25, 0),  # 左侧
            QPointF(25, 0)    # 右侧
        ]