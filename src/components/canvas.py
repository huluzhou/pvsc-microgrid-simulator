#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络画布组件，用于绘制和编辑电网拓扑图
"""

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter

from components.network_items import BusItem, LineItem, TransformerItem, GeneratorItem, LoadItem, StorageItem, ChargerItem


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
        elif component_type == "storage":
            item = StorageItem(pos)
        elif component_type == "charger":
            item = ChargerItem(pos)
        
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
        # 检查是否已经连接
        if self.is_connected(item1, item2):
            return False
            
        # 检查连接数量约束
        if not item1.can_connect() or not item2.can_connect():
            return False
            
        # 检查组件类型是否允许连接
        # 相同类型的组件不能相互连接（包括母线）
        if item1.component_type == item2.component_type:
            return False
            
        # 特定组件类型的连接规则
        # 母线可以连接到任何其他类型的组件（但不能连接到母线）
        if item1.component_type == "bus" and item2.component_type != "bus":
            return True
        if item2.component_type == "bus" and item1.component_type != "bus":
            return True
            
        # 变压器和线路必须连接到母线
        if item1.component_type in ["transformer", "line"] and item2.component_type != "bus":
            return False
        if item2.component_type in ["transformer", "line"] and item1.component_type != "bus":
            return False
            
        # 发电机和负载必须连接到母线
        if item1.component_type in ["generator", "load"] and item2.component_type != "bus":
            return False
        if item2.component_type in ["generator", "load"] and item1.component_type != "bus":
            return False
            
        # 开关可以连接到母线
        if item1.component_type == "switch" and item2.component_type == "bus":
            return True
        if item2.component_type == "switch" and item1.component_type == "bus":
            return True
        
        return False
    
    def connect_items(self, item1, item2):
        """连接两个组件"""
        # 检查对象是否有效
        try:
            if not item1 or not item2:
                return False
            # 测试访问对象属性以确保对象未被删除
            _ = item1.component_name
            _ = item2.component_name
        except (RuntimeError, AttributeError):
            print("连接失败: 组件对象已被删除")
            return False
            
        # 检查是否可以连接
        if not self.can_connect(item1, item2):
            # 显示错误信息
            valid1, msg1 = item1.validate_connections()
            valid2, msg2 = item2.validate_connections()
            if not valid1:
                print(f"连接失败: {msg1}")
            elif not valid2:
                print(f"连接失败: {msg2}")
            else:
                print(f"连接失败: {item1.component_name}和{item2.component_name}不能连接")
            return False
            
        # 找到最近的可用连接点
        connection_point1, point_index1 = self.find_nearest_connection_point(item1, item2)
        connection_point2, point_index2 = self.find_nearest_connection_point(item2, item1)
        
        # 检查是否找到了有效的连接点
        if point_index1 == -1 or point_index2 == -1:
            print("连接失败: 没有可用的连接点")
            return False
        
        # 添加连接，总线组件不标记连接点为已占用
        point_idx1 = point_index1 if item1.component_type != 'bus' else None
        point_idx2 = point_index2 if item2.component_type != 'bus' else None
        
        if not item1.add_connection(item2, point_idx1) or not item2.add_connection(item1, point_idx2):
            print("连接失败: 超出连接数限制")
            return False
        
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
            'point2': connection_point2,
            'point_index1': point_index1,
            'point_index2': point_index2
        })
        
        return True
        
    def find_nearest_connection_point(self, source_item, target_item):
        """找到最近的可用连接点"""
        # 检查对象是否有效
        try:
            if not source_item or not target_item:
                return QPointF(0, 0), -1
            
            # 获取目标项的场景位置
            target_pos = target_item.scenePos()
            
            # 如果源项没有定义连接点，使用中心点
            if not hasattr(source_item, 'connection_points') or not source_item.connection_points:
                return QPointF(0, 0), -1
            
            # 获取可用的连接点
            # 对于总线组件，允许所有连接点（不限制连接数量）
            if hasattr(source_item, 'component_type') and source_item.component_type == 'bus':
                available_points = list(range(len(source_item.connection_points)))
            else:
                available_points = source_item.get_available_connection_points()
            
            if not available_points:
                return QPointF(0, 0), -1  # 没有可用连接点
            
            # 计算每个可用连接点到目标的距离
            min_distance = float('inf')
            nearest_point = source_item.connection_points[available_points[0]]
            nearest_index = available_points[0]
            
            for point_index in available_points:
                point = source_item.connection_points[point_index]
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
                    nearest_index = point_index
            
            return nearest_point, nearest_index
        except RuntimeError:
            # 对象已被删除
            return QPointF(0, 0), -1

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
        # 检查右键点击位置是否有组件
        scene_pos = self.mapToScene(event.pos())
        item_at_pos = self.scene.itemAt(scene_pos, self.transform())
        
        # 如果点击在组件上，让组件处理右键菜单
        if item_at_pos and hasattr(item_at_pos, 'contextMenuEvent'):
            # 创建场景右键菜单事件
            from PySide6.QtWidgets import QGraphicsSceneContextMenuEvent
            scene_event = QGraphicsSceneContextMenuEvent()
            scene_event.setPos(scene_pos)
            scene_event.setScenePos(scene_pos)
            scene_event.setScreenPos(event.globalPos())
            item_at_pos.contextMenuEvent(scene_event)
            return
        
        # 创建右键菜单
        menu = QMenu(self)
        
        # 检查是否有选中的项目
        selected_items = self.scene.selectedItems()
        has_selection = len(selected_items) > 0
        
        # 添加菜单项
        disconnect_action = None
        delete_action = None
        
        if has_selection:
            # 选中项目相关操作
            disconnect_action = menu.addAction("断开所选连接")
            delete_action = menu.addAction("删除所选")
            menu.addSeparator()
        
        # 画布操作
        clear_action = menu.addAction("清空画布")
        menu.addSeparator()
        
        # 视图操作
        zoom_in_action = menu.addAction("放大")
        zoom_out_action = menu.addAction("缩小")
        zoom_fit_action = menu.addAction("适应视图")
        
        # 显示菜单并获取选择的动作
        action = menu.exec_(self.mapToGlobal(event.pos()))
        
        # 处理菜单动作
        if action == disconnect_action and has_selection:
            self.disconnect_all_from_selected()
        elif action == delete_action and has_selection:
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
        """断开选中设备的所有连接"""
        if items is None:
            items = self.scene.selectedItems()
        
        if not items or not hasattr(self, 'connections'):
            return
        
        # 找到需要删除的连接
        connections_to_remove = []
        for conn in self.connections:
            # 如果连接的任一端点在选中项目中，则删除该连接
            if conn['item1'] in items or conn['item2'] in items:
                connections_to_remove.append(conn)
        
        # 删除连接线和连接信息，并更新连接计数
        for conn in connections_to_remove:
            self.scene.removeItem(conn['line'])
            self.connections.remove(conn)
            # 更新连接计数和连接点状态
            if hasattr(conn['item1'], 'remove_connection'):
                point_index1 = conn.get('point_index1', None) if conn['item1'].component_type != 'bus' else None
                conn['item1'].remove_connection(conn['item2'], point_index1)
            if hasattr(conn['item2'], 'remove_connection'):
                point_index2 = conn.get('point_index2', None) if conn['item2'].component_type != 'bus' else None
                conn['item2'].remove_connection(conn['item1'], point_index2)
    
    def disconnect_all_from_selected(self):
        """断开选中设备的所有连接"""
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return
        
        self.disconnect_selected_items(selected_items)
    
    def disconnect_all_from_item(self, item):
        """断开指定组件的所有连接"""
        if not hasattr(self, 'connections'):
            return
        
        # 找到需要删除的连接
        connections_to_remove = []
        for conn in self.connections:
            if conn['item1'] == item or conn['item2'] == item:
                connections_to_remove.append(conn)
        
        # 删除连接线和连接信息，并更新连接计数
        for conn in connections_to_remove:
            self.scene.removeItem(conn['line'])
            self.connections.remove(conn)
            # 更新连接计数和连接点状态
            if hasattr(conn['item1'], 'remove_connection'):
                point_index1 = conn.get('point_index1', None) if conn['item1'].component_type != 'bus' else None
                conn['item1'].remove_connection(conn['item2'], point_index1)
            if hasattr(conn['item2'], 'remove_connection'):
                point_index2 = conn.get('point_index2', None) if conn['item2'].component_type != 'bus' else None
                conn['item2'].remove_connection(conn['item1'], point_index2)
        
        print(f"断开了 {len(connections_to_remove)} 个连接")
    
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
        
        # 删除找到的连接，并更新连接计数
        for conn in connections_to_remove:
            self.scene.removeItem(conn['line'])
            self.connections.remove(conn)
            # 更新连接计数
            if hasattr(conn['item1'], 'remove_connection'):
                conn['item1'].remove_connection(conn['item2'])
            if hasattr(conn['item2'], 'remove_connection'):
                conn['item2'].remove_connection(conn['item1'])
        
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