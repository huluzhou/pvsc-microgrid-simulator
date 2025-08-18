#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
电网组件图形项，用于在画布上显示各种电网元件
"""

from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QMenu, QMessageBox
from PySide6.QtCore import Qt, QPointF, Signal, QObject, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QTransform
from PySide6.QtSvg import QSvgRenderer
import os
import math
import sys


def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持开发环境和打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，并将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境中使用当前文件的目录
        base_path = os.path.dirname(os.path.abspath(__file__))
        # 从src目录向上找到项目根目录
        while not os.path.exists(os.path.join(base_path, 'src')):
            parent = os.path.dirname(base_path)
            if parent == base_path:  # 已经到达根目录
                break
            base_path = parent
    
    return os.path.join(base_path, relative_path)


class ItemSignals(QObject):
    """用于发送图形项信号的类"""
    itemSelected = Signal(object)  # 选中信号


class BaseNetworkItem(QGraphicsItem):
    """电网组件基类"""

    def __init__(self, pos, parent=None):
        super().__init__(parent)
        self.setPos(pos)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        # 设置接受鼠标事件
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        
        # 组件属性
        self.component_type = "base"
        self.component_name = "基础组件"
        self.properties = {}
        
        # 创建信号对象
        self.signals = ItemSignals()
        
        # SVG渲染器
        self.svg_renderer = None
        self.svg_size = 64  # SVG图标大小
        
        # 旋转角度（以度为单位）
        self.rotation_angle = 0
        
        # 添加标签
        self.label = QGraphicsTextItem(self.component_name, self)
        self.label.setPos(-20, 35)  # 标签位置在组件下方
        self.label.setDefaultTextColor(QColor(0, 0, 0))  # 黑色
        
        # 设置Z值，确保组件在网格之上
        self.setZValue(10)
        
        # 连接点位置和状态
        self.connection_points = []
        self.connection_point_states = {}  # 记录每个连接点的占用状态 {point_index: connected_item}
        
        # 连接约束
        self.max_connections = -1  # -1表示无限制，其他数字表示最大连接数
        self.min_connections = 0   # 最小连接数
        self.current_connections = 0  # 当前连接数

    def load_svg(self, svg_filename):
        """加载SVG文件"""
        try:
            # 使用get_resource_path函数获取正确的资源路径
            svg_path = get_resource_path(os.path.join("assets", svg_filename))
            if os.path.exists(svg_path):
                self.svg_renderer = QSvgRenderer(svg_path)
            else:
                # 尝试开发环境路径
                dev_svg_path = get_resource_path(os.path.join("src", "assets", svg_filename))
                if os.path.exists(dev_svg_path):
                    self.svg_renderer = QSvgRenderer(dev_svg_path)
                else:
                    print(f"警告: SVG文件未找到: {svg_filename}")
                    print(f"尝试的路径: {svg_path}, {dev_svg_path}")
        except Exception as e:
            print(f"加载SVG文件时出错: {e}")
            self.svg_renderer = None

    def boundingRect(self):
        """返回边界矩形"""
        return QRectF(-32, -32, 64, 64)

    def paint(self, painter, option, widget):
        """绘制组件"""
        if self.svg_renderer and self.svg_renderer.isValid():
            # 保存画家状态
            painter.save()
            
            # 应用旋转变换
            if self.rotation_angle != 0:
                painter.rotate(self.rotation_angle)
            
            # 使用SVG渲染
            rect = QRectF(-32, -32, 64, 64)
            self.svg_renderer.render(painter, rect)
            
            # 恢复画家状态
            painter.restore()
            
            # 如果选中，绘制选中框
            if self.isSelected():
                pen = QPen(QColor(0, 0, 255), 2)  # 蓝色
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(QRectF(-32, -32, 64, 64))
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
        """更新连接线位置（当组件移动或旋转时调用）"""
        if hasattr(self, 'scene') and self.scene():
            # 获取画布对象
            canvas = None
            for view in self.scene().views():
                if hasattr(view, 'connections'):
                    canvas = view
                    break
            
            if canvas and hasattr(canvas, 'connections'):
                # 更新与此组件相关的连接线
                for conn in canvas.connections:
                    if conn['item1'] == self or conn['item2'] == self:
                        # 重新计算连接点位置
                        if conn['item1'] == self:
                            # 使用存储的连接点索引获取旋转后的连接点位置
                            point_index = conn.get('point_index1', 0)
                            if point_index < len(self.connection_points):
                                conn['point1'] = self.connection_points[point_index]
                            new_point = self.mapToScene(conn['point1'])
                            conn['line'].setLine(
                                new_point.x(), new_point.y(),
                                conn['line'].line().p2().x(), conn['line'].line().p2().y()
                            )
                        if conn['item2'] == self:
                            # 使用存储的连接点索引获取旋转后的连接点位置
                            point_index = conn.get('point_index2', 0)
                            if point_index < len(self.connection_points):
                                conn['point2'] = self.connection_points[point_index]
                            new_point = self.mapToScene(conn['point2'])
                            conn['line'].setLine(
                                conn['line'].line().p1().x(), conn['line'].line().p1().y(),
                                new_point.x(), new_point.y()
                            )
        
    def rotate_component(self, angle=90):
        """旋转组件"""
        self.rotation_angle = (self.rotation_angle + angle) % 360
        self.update_rotated_connection_points()
        self.update()
        self.update_connections()
    
    def update_rotated_connection_points(self):
        """更新旋转后的连接点位置"""
        if not hasattr(self, 'original_connection_points'):
            self.original_connection_points = self.connection_points.copy()
        
        # 将角度转换为弧度
        angle_rad = math.radians(self.rotation_angle)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        
        # 旋转每个连接点
        self.connection_points = []
        for point in self.original_connection_points:
            # 应用旋转矩阵
            new_x = point.x() * cos_angle - point.y() * sin_angle
            new_y = point.x() * sin_angle + point.y() * cos_angle
            self.connection_points.append(QPointF(new_x, new_y))
    
    def can_connect(self):
        """检查是否可以添加新连接"""
        if self.max_connections == -1:
            return True
        return self.current_connections < self.max_connections
    
    def add_connection(self, connected_item=None, connection_point_index=None):
        """添加连接"""
        if self.can_connect():
            self.current_connections += 1
            # 如果指定了连接点索引，标记该连接点为已占用
            if connection_point_index is not None:
                self.connection_point_states[connection_point_index] = connected_item
            return True
        return False
    
    def remove_connection(self, connected_item=None, connection_point_index=None):
        """移除连接"""
        if self.current_connections > 0:
            self.current_connections -= 1
            # 如果指定了连接点索引，清除该连接点的占用状态
            if connection_point_index is not None and connection_point_index in self.connection_point_states:
                del self.connection_point_states[connection_point_index]
    
    def is_connection_point_available(self, point_index):
        """检查指定连接点是否可用"""
        return point_index not in self.connection_point_states
    
    def get_available_connection_points(self):
        """获取所有可用的连接点索引"""
        available_points = []
        for i in range(len(self.connection_points)):
            if self.is_connection_point_available(i):
                available_points.append(i)
        return available_points
    
    def validate_connections(self):
        """验证连接数是否满足约束"""
        if self.current_connections < self.min_connections:
            return False, f"{self.component_name}至少需要{self.min_connections}个连接"
        if self.max_connections != -1 and self.current_connections > self.max_connections:
            return False, f"{self.component_name}最多只能有{self.max_connections}个连接"
        return True, ""
    
    def disconnect_all_connections(self):
        """断开所有连接"""
        if self.scene():
            # 获取画布对象
            canvas = None
            for view in self.scene().views():
                if hasattr(view, 'disconnect_all_from_item'):
                    canvas = view
                    break
            
            if canvas:
                canvas.disconnect_all_from_item(self)
            else:
                print(f"断开{self.component_name}的所有连接")
    
    def delete_component(self):
        """删除组件"""
        if self.scene():
            # 先断开所有连接
            self.disconnect_all_connections()
            # 从场景中移除
            self.scene().removeItem(self)
            print(f"删除组件: {self.component_name}")
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        menu = QMenu()
        
        # 添加旋转选项
        rotate_action = menu.addAction("旋转90°")
        rotate_action.triggered.connect(lambda: self.rotate_component(90))
        
        menu.addSeparator()
        
        # 添加断开连接选项
        disconnect_action = menu.addAction("断开所有连接")
        disconnect_action.triggered.connect(self.disconnect_all_connections)
        
        # 添加删除选项
        delete_action = menu.addAction("删除组件")
        delete_action.triggered.connect(self.delete_component)
        
        # 显示菜单
        menu.exec(event.screenPos())
    
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
        
        # 母线可以连接多个组件，无限制
        self.max_connections = -1
        self.min_connections = 0
        
        # 加载SVG图标
        self.load_svg("bus.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(0, 0)     # 中心点
        ]
        self.original_connection_points = self.connection_points.copy()


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
        
        # 连接约束：线路必须连接两个bus
        self.max_connections = 2
        self.min_connections = 2
        
        # 加载SVG图标
        self.load_svg("line.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(-30, 0),  # 左端
            QPointF(30, 0)    # 右端
        ]
        self.original_connection_points = self.connection_points.copy()


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
        
        # 连接约束：变压器必须连接两个bus
        self.max_connections = 2
        self.min_connections = 2
        
        # 加载SVG图标
        self.load_svg("transformer.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(-28, 0),  # 左端
            QPointF(28, 0)    # 右端
        ]
        self.original_connection_points = self.connection_points.copy()


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
        
        # 连接约束：发电机只能连接一个bus
        self.max_connections = 1
        self.min_connections = 1
        
        # 加载SVG图标
        self.load_svg("generator.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(28, 0)   # 线头端点（上侧）
        ]
        self.original_connection_points = self.connection_points.copy()


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
        
        # 连接约束：负载只能连接一个bus
        self.max_connections = 1
        self.min_connections = 1
        
        # 加载SVG图标
        self.load_svg("load.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(0, -28)   # 线头端点（上侧）
        ]
        self.original_connection_points = self.connection_points.copy()


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
        
        # 开关连接两个bus
        self.max_connections = 2
        self.min_connections = 2
        
        # 加载SVG图标
        self.load_svg("switch.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(-25, 0),  # 左侧
            QPointF(25, 0)    # 右侧
        ]
        self.original_connection_points = self.connection_points.copy()