#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络画布组件，用于绘制和编辑电网拓扑图
"""

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter

from components.network_items import BusItem, LineItem, TransformerItem, GeneratorItem, LoadItem, SwitchItem


class NetworkCanvas(QGraphicsView):
    """电网画布类，用于绘制和编辑电网拓扑图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        # 创建场景
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(0, 0, 5000, 5000))  # 设置场景大小
        self.setScene(self.scene)

        # 设置视图属性
        self.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)  # 框选模式
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        # 绘制网格背景
        self.draw_grid()

        # 设置接受拖放
        self.setAcceptDrops(True)

    def draw_grid(self, grid_size=50):
        """绘制网格背景"""
        # 设置网格线颜色和样式
        grid_pen = QPen(QColor(230, 230, 230))
        grid_pen.setWidth(1)

        # 绘制水平线
        for y in range(0, int(self.scene.height()), grid_size):
            self.scene.addLine(0, y, self.scene.width(), y, grid_pen)

        # 绘制垂直线
        for x in range(0, int(self.scene.width()), grid_size):
            self.scene.addLine(x, 0, x, self.scene.height(), grid_pen)

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """放置事件"""
        if event.mimeData().hasText():
            # 获取组件类型
            component_type = event.mimeData().text()
            
            # 获取放置位置
            pos = self.mapToScene(event.pos())
            
            # 创建对应的组件
            self.create_component(component_type, pos)
            
            event.acceptProposedAction()

    def create_component(self, component_type, pos):
        """创建电网组件"""
        item = None
        
        # 根据组件类型创建对应的图形项
        if component_type == "bus":
            item = BusItem(pos)
        elif component_type == "line":
            item = LineItem(pos)
        elif component_type == "transformer":
            item = TransformerItem(pos)
        elif component_type == "generator":
            item = GeneratorItem(pos)
        elif component_type == "load":
            item = LoadItem(pos)
        elif component_type == "switch":
            item = SwitchItem(pos)
        
        # 添加到场景
        if item:
            self.scene.addItem(item)
            # 连接信号
            item.signals.itemSelected.connect(self.handle_item_selected)
            
            return item
        
        return None
        
    def handle_item_selected(self, item):
        """处理组件被选中的事件"""
        print(f"组件被选中: {item.component_type}")
        # 如果已经有一个组件被选中，并且当前选中的是另一个组件，尝试连接它们
        if hasattr(self, 'first_selected_item') and self.first_selected_item and self.first_selected_item != item:
            print(f"尝试连接: {self.first_selected_item.component_type} 和 {item.component_type}")
            # 如果两个组件都是可连接的，创建连接
            if self.can_connect(self.first_selected_item, item):
                print("可以连接，创建连接线")
                self.connect_items(self.first_selected_item, item)
            else:
                print("不能连接这两个组件")
            
            # 重置选中状态
            self.first_selected_item = None
        else:
            # 记录第一个选中的组件
            print(f"记录第一个选中的组件: {item.component_type}")
            self.first_selected_item = item
            

    
    def can_connect(self, item1, item2):
        """检查两个组件是否可以连接"""
        # 检查组件类型是否允许连接
        # 相同类型的组件不能相互连接
        if item1.component_type == item2.component_type:
            return False
            
        # 特定组件类型的连接规则
        # 母线可以连接到任何其他类型的组件
        if item1.component_type == "bus" or item2.component_type == "bus":
            return True
            
        # 线路可以连接到变压器
        if (item1.component_type == "line" and item2.component_type == "transformer") or \
           (item1.component_type == "transformer" and item2.component_type == "line"):
            return True
            
        # 发电机可以连接到负载
        if (item1.component_type == "generator" and item2.component_type == "load") or \
           (item1.component_type == "load" and item2.component_type == "generator"):
            return True
            
        # 线路可以连接到负载
        if (item1.component_type == "line" and item2.component_type == "load") or \
           (item1.component_type == "load" and item2.component_type == "line"):
            return True
            
        # 变压器可以连接到负载
        if (item1.component_type == "transformer" and item2.component_type == "load") or \
           (item1.component_type == "load" and item2.component_type == "transformer"):
            return True
            
        # 开关可以连接到线路、变压器或负载
        if item1.component_type == "switch" and (item2.component_type == "line" or item2.component_type == "transformer" or item2.component_type == "load"):
            return True
        if item2.component_type == "switch" and (item1.component_type == "line" or item1.component_type == "transformer" or item1.component_type == "load"):
            return True
        
        return False
    
    def connect_items(self, item1, item2):
        """连接两个组件"""
        # 找到最近的连接点
        connection_point1 = self.find_nearest_connection_point(item1, item2)
        connection_point2 = self.find_nearest_connection_point(item2, item1)
        
        # 转换为场景坐标
        scene_point1 = item1.mapToScene(connection_point1)
        scene_point2 = item2.mapToScene(connection_point2)
        
        # 创建连接线
        line = self.scene.addLine(
            scene_point1.x(), scene_point1.y(),
            scene_point2.x(), scene_point2.y(),
            QPen(QColor(0, 0, 0), 2)
        )
        
        # 存储连接信息
        if not hasattr(self, 'connections'):
            self.connections = []
        
        self.connections.append({
            'line': line,
            'item1': item1,
            'item2': item2,
            'point1': connection_point1,
            'point2': connection_point2
        })
        
    def find_nearest_connection_point(self, source_item, target_item):
        """找到最近的连接点"""
        # 获取目标项的场景位置
        target_pos = target_item.scenePos()
        
        # 如果源项没有定义连接点，使用中心点
        if not hasattr(source_item, 'connection_points') or not source_item.connection_points:
            return QPointF(0, 0)
        
        # 计算每个连接点到目标的距离
        min_distance = float('inf')
        nearest_point = source_item.connection_points[0]
        
        for point in source_item.connection_points:
            # 转换为场景坐标
            scene_point = source_item.mapToScene(point)
            
            # 计算距离
            dx = scene_point.x() - target_pos.x()
            dy = scene_point.y() - target_pos.y()
            distance = (dx * dx + dy * dy) ** 0.5
            
            # 更新最近点
            if distance < min_distance:
                min_distance = distance
                nearest_point = point
        
        return nearest_point

    def wheelEvent(self, event):
        """鼠标滚轮事件，用于缩放"""
        # 获取缩放因子
        zoom_factor = 1.15
        
        if event.angleDelta().y() > 0:
            # 放大
            self.scale(zoom_factor, zoom_factor)
        else:
            # 缩小
            self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        # 创建右键菜单
        menu = QMenu(self)
        
        # 检查是否有选中的项目
        selected_items = self.scene.selectedItems()
        has_selection = len(selected_items) > 0
        
        # 添加菜单项
        if has_selection:
            disconnect_action = menu.addAction("断开连接")
            menu.addSeparator()
        
        delete_action = menu.addAction("删除所选")
        clear_action = menu.addAction("清空画布")
        menu.addSeparator()
        zoom_in_action = menu.addAction("放大")
        zoom_out_action = menu.addAction("缩小")
        zoom_fit_action = menu.addAction("适应视图")
        
        # 如果没有选中项目，禁用删除选项
        if not has_selection:
            delete_action.setEnabled(False)
        
        # 显示菜单并获取选择的动作
        action = menu.exec_(self.mapToGlobal(event.pos()))
        
        # 处理菜单动作
        if has_selection and action == disconnect_action:
            self.disconnect_all_from_selected()
        elif action == delete_action:
            self.delete_selected_items()
        elif action == clear_action:
            self.clear_canvas()
        elif action == zoom_in_action:
            self.scale(1.15, 1.15)
        elif action == zoom_out_action:
            self.scale(1.0 / 1.15, 1.0 / 1.15)
        elif action == zoom_fit_action:
            self.fit_in_view()

    def delete_selected_items(self):
        """删除选中的项目"""
        selected_items = self.scene.selectedItems()
        
        # 删除与选中项目相关的连接
        self.disconnect_selected_items(selected_items)
        
        # 删除选中的项目
        for item in selected_items:
            self.scene.removeItem(item)
    
    def disconnect_selected_items(self, items=None):
        """断开选中项目的连接"""
        if items is None:
            items = self.scene.selectedItems()
        
        if not hasattr(self, 'connections'):
            return
        
        # 找到需要删除的连接
        connections_to_remove = []
        for conn in self.connections:
            # 如果连接的任一端点在选中项目中，则删除该连接
            if conn['item1'] in items or conn['item2'] in items:
                connections_to_remove.append(conn)
        
        # 删除连接线和连接信息
        for conn in connections_to_remove:
            self.scene.removeItem(conn['line'])
            self.connections.remove(conn)
    
    def disconnect_all_from_selected(self):
        """断开选中设备的所有连接"""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return
        
        self.disconnect_selected_items(selected_items)
    
    def disconnect_items(self, item1, item2):
        """断开两个特定设备之间的连接"""
        if not hasattr(self, 'connections'):
            return False
        
        # 找到两个设备之间的连接
        connections_to_remove = []
        for conn in self.connections:
            if (conn['item1'] == item1 and conn['item2'] == item2) or \
               (conn['item1'] == item2 and conn['item2'] == item1):
                connections_to_remove.append(conn)
        
        # 删除找到的连接
        for conn in connections_to_remove:
            self.scene.removeItem(conn['line'])
            self.connections.remove(conn)
        
        return len(connections_to_remove) > 0
    
    def get_connections_for_item(self, item):
        """获取指定设备的所有连接"""
        if not hasattr(self, 'connections'):
            return []
        
        item_connections = []
        for conn in self.connections:
            if conn['item1'] == item or conn['item2'] == item:
                item_connections.append(conn)
        
        return item_connections
    
    def is_connected(self, item1, item2):
        """检查两个设备是否已连接"""
        if not hasattr(self, 'connections'):
            return False
        
        for conn in self.connections:
            if (conn['item1'] == item1 and conn['item2'] == item2) or \
               (conn['item1'] == item2 and conn['item2'] == item1):
                return True
        
        return False

    def clear_canvas(self):
        """清空画布"""
        self.scene.clear()
        self.draw_grid()

    def fit_in_view(self):
        """适应视图"""
        # 获取所有项目的边界矩形
        items = self.scene.items()
        if not items:
            return
        
        # 计算所有项目的边界矩形
        rect = items[0].sceneBoundingRect()
        for item in items[1:]:
            rect = rect.united(item.sceneBoundingRect())
        
        # 适应视图
        self.fitInView(rect, Qt.KeepAspectRatio)