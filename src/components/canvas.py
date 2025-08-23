#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络画布组件，用于绘制和编辑电网拓扑图
"""

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QApplication
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPalette

from components.network_items import BusItem, LineItem, TransformerItem, LoadItem, StorageItem, ChargerItem, ExternalGridItem, StaticGeneratorItem


class NetworkCanvas(QGraphicsView):
    """电网画布类，用于绘制和编辑电网拓扑图"""
    
    # 信号：选择变化时发出
    selection_changed = Signal(object)  # 发出当前选中的单个项目，如果多选或无选择则为None

    def __init__(self, parent=None):
        super().__init__(parent)
        # 保存父窗口引用用于更新状态栏
        self.main_window = parent
        # 初始化组件计数器
        self.component_counters = {
            'bus': 0,
            'line': 0,
            'transformer': 0,
            'load': 0,
            'storage': 0,
            'charger': 0,
            'external_grid': 0,
            'static_generator': 0
        }
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

        # 设置初始背景颜色
        self.update_background_color()
        
        # 绘制网格背景
        self.draw_grid()

        # 设置接受拖放
        self.setAcceptDrops(True)
        
        # 设置焦点策略以接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 连接场景选择变化信号
        self.scene.selectionChanged.connect(self.update_status_bar)
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        # 右键拖动相关变量
        self.right_drag_active = False
        self.last_pan_point = QPointF()
        self.right_press_point = QPointF()
        self.has_dragged = False
    
    def get_connection_line_color(self):
        """根据当前主题获取连接线颜色"""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # 检查是否为深色主题
                bg_color = palette.color(QPalette.Window)
                is_dark_theme = bg_color.lightness() < 128
                
                if is_dark_theme:
                    # 深色主题使用白色连接线
                    return QColor(255, 255, 255)
                else:
                    # 浅色主题使用黑色连接线
                    return QColor(0, 0, 0)
            else:
                # 默认黑色
                return QColor(0, 0, 0)
        except Exception as e:
            print(f"获取连接线颜色时出错: {e}")
            return QColor(0, 0, 0)

    def get_grid_color(self):
        """根据当前主题获取网格线颜色"""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # 检查是否为深色主题
                bg_color = palette.color(QPalette.Window)
                is_dark_theme = bg_color.lightness() < 128
                
                if is_dark_theme:
                    # 深色主题使用深灰色网格线
                    return QColor(80, 80, 80)
                else:
                    # 浅色主题使用浅灰色网格线
                    return QColor(230, 230, 230)
            else:
                # 默认浅灰色
                return QColor(230, 230, 230)
        except Exception as e:
            print(f"获取网格颜色时出错: {e}")
            return QColor(230, 230, 230)
    
    def draw_grid(self, grid_size=50):
        """绘制网格背景"""
        # 设置网格线颜色和样式
        grid_color = self.get_grid_color()
        grid_pen = QPen(grid_color)
        grid_pen.setWidth(1)

        # 绘制水平线
        for y in range(0, int(self.scene.height()), grid_size):
            line = self.scene.addLine(0, y, self.scene.width(), y, grid_pen)
            line.setZValue(-1)  # 设置网格线在背景层

        # 绘制垂直线
        for x in range(0, int(self.scene.width()), grid_size):
            line = self.scene.addLine(x, 0, x, self.scene.height(), grid_pen)
            line.setZValue(-1)  # 设置网格线在背景层

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

    def generate_component_name(self, component_type):
        """生成组件的自动名称"""
        # 增加计数器
        self.component_counters[component_type] += 1
        count = self.component_counters[component_type]
        
        # 根据组件类型生成名称
        name_mapping = {
            'bus': f'Bus {count}',
            'line': f'Line {count}',
            'transformer': f'Transformer {count}',
            'load': f'Load {count}',
            'storage': f'Storage {count}',
            'charger': f'Charger {count}',
            'external_grid': f'External Grid {count}',
            'static_generator': f'Static Generator {count}'
        }
        
        return name_mapping.get(component_type, f'{component_type.capitalize()} {count}')
    
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
        elif component_type == "load":
            item = LoadItem(pos)
        elif component_type == "storage":
            item = StorageItem(pos)
        elif component_type == "charger":
            item = ChargerItem(pos)
        elif component_type == "external_grid":
            item = ExternalGridItem(pos)
        elif component_type == "static_generator":
            item = StaticGeneratorItem(pos)
        
        # 添加到场景
        if item:
            # 生成自动名称
            auto_name = self.generate_component_name(component_type)
            item.component_name = auto_name
            
            # 更新组件属性中的名称
            if hasattr(item, 'properties') and 'name' in item.properties:
                item.properties['name'] = auto_name
            
            # 更新标签显示
            if hasattr(item, 'label'):
                item.label.setPlainText(auto_name)
            
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
            

    
    def _check_component_type_compatibility(self, item1, item2):
        """检查组件类型兼容性"""
        type1, type2 = item1.component_type, item2.component_type
        
        # 相同类型的组件不能相互连接
        if type1 == type2:
            return False
            
        # 母线可以连接到任何其他类型的组件
        if type1 == "bus" or type2 == "bus":
            return True
            
        # 变压器和线路必须连接到母线
        if type1 in ["transformer", "line"] or type2 in ["transformer", "line"]:
            return False
            
        # 负载和外部电网必须连接到母线
        if type1 in ["load", "storage", "charger", "external_grid", "static_generator"] or type2 in ["load", "storage", "charger", "external_grid", "static_generator"]:
            return False
            
        # 开关可以连接到母线（已在上面的母线规则中处理）
        return False
    
    def can_connect(self, item1, item2):
        """检查两个组件是否可以连接"""
        # 检查是否已经连接
        if self.is_connected(item1, item2):
            return False
            
        # 检查连接数量约束
        if not item1.can_connect() or not item2.can_connect():
            return False
            
        # 检查组件类型兼容性
        return self._check_component_type_compatibility(item1, item2)
    
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
        line_color = self.get_connection_line_color()
        line = self.scene.addLine(
            scene_point1.x(), scene_point1.y(),
            scene_point2.x(), scene_point2.y(),
            QPen(line_color, 2)
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

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.RightButton:
            # 右键按下，记录初始位置
            self.right_drag_active = True
            self.last_pan_point = event.pos()
            self.right_press_point = event.pos()
            self.has_dragged = False
            event.accept()
        else:
            # 其他按键交给父类处理
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.right_drag_active:
            # 检查是否开始拖动（移动距离超过阈值）
            drag_distance = (event.pos() - self.right_press_point).manhattanLength()
            if drag_distance > 5 and not self.has_dragged:  # 5像素阈值
                self.has_dragged = True
                self.setCursor(Qt.ClosedHandCursor)
            
            if self.has_dragged:
                # 右键拖动画布
                delta = event.pos() - self.last_pan_point
                self.last_pan_point = event.pos()
                
                # 移动视图
                self.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().value() - delta.x()
                )
                self.verticalScrollBar().setValue(
                    self.verticalScrollBar().value() - delta.y()
                )
            else:
                self.last_pan_point = event.pos()
            
            event.accept()
        else:
            # 其他情况交给父类处理
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.RightButton and self.right_drag_active:
            # 右键释放，结束拖动
            self.right_drag_active = False
            self.setCursor(Qt.ArrowCursor)
            
            # 使用QTimer延迟重置has_dragged状态，确保contextMenuEvent能检测到拖动状态
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, lambda: setattr(self, 'has_dragged', False))
            
            event.accept()
        else:
            # 其他按键交给父类处理
            super().mouseReleaseEvent(event)

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
        # 如果正在拖动或刚刚完成拖动，不显示菜单
        if self.right_drag_active or self.has_dragged:
            return
            
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
            rotate_left_action = menu.addAction("向左旋转90°")
            rotate_right_action = menu.addAction("向右旋转90°")
            menu.addSeparator()
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
        if has_selection and action == rotate_left_action:
            # 向左旋转选中的组件
            for item in selected_items:
                if hasattr(item, 'rotate_component'):
                    item.rotate_component(-90)
        elif has_selection and action == rotate_right_action:
            # 向右旋转选中的组件
            for item in selected_items:
                if hasattr(item, 'rotate_component'):
                    item.rotate_component(90)
        elif action == disconnect_action and has_selection:
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
        
        # 检查是否删除了first_selected_item
        if hasattr(self, 'first_selected_item') and self.first_selected_item in selected_items:
            self.first_selected_item = None
        
        # 删除选中的项目
        for item in selected_items:
            self.scene.removeItem(item)
    
    def _remove_connections(self, connections_to_remove):
        """移除连接的通用方法"""
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
    
    def disconnect_selected_items(self, items=None):
        """断开选中设备的所有连接"""
        if items is None:
            items = self.scene.selectedItems()
        
        if not items or not hasattr(self, 'connections'):
            return
        
        # 找到需要删除的连接
        connections_to_remove = [
            conn for conn in self.connections 
            if conn['item1'] in items or conn['item2'] in items
        ]
        
        self._remove_connections(connections_to_remove)
    
    def disconnect_all_from_selected(self):
        """断开选中设备的所有连接"""
        selected_items = self.scene.selectedItems()
        if selected_items:
            self.disconnect_selected_items(selected_items)
    
    def disconnect_all_from_item(self, item):
        """断开指定组件的所有连接"""
        if not hasattr(self, 'connections'):
            return
        
        # 检查是否需要清理first_selected_item
        if hasattr(self, 'first_selected_item') and self.first_selected_item == item:
            self.first_selected_item = None
        
        # 找到需要删除的连接
        connections_to_remove = [
            conn for conn in self.connections 
            if conn['item1'] == item or conn['item2'] == item
        ]
        
        self._remove_connections(connections_to_remove)
        print(f"断开了 {len(connections_to_remove)} 个连接")
    
    def disconnect_items(self, item1, item2):
        """断开两个特定设备之间的连接"""
        if not hasattr(self, 'connections'):
            return False
        
        # 找到两个设备之间的连接
        connections_to_remove = [
            conn for conn in self.connections 
            if (conn['item1'] == item1 and conn['item2'] == item2) or 
               (conn['item1'] == item2 and conn['item2'] == item1)
        ]
        
        self._remove_connections(connections_to_remove)
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

    def update_background_color(self):
        """更新画布背景颜色"""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # 检查是否为深色主题
                bg_color = palette.color(QPalette.Window)
                is_dark_theme = bg_color.lightness() < 128
                
                if is_dark_theme:
                    # 深色主题使用深色背景
                    self.setBackgroundBrush(QBrush(QColor(42, 42, 42)))
                    self.scene.setBackgroundBrush(QBrush(QColor(42, 42, 42)))
                else:
                    # 浅色主题使用白色背景
                    self.setBackgroundBrush(QBrush(QColor(255, 255, 255)))
                    self.scene.setBackgroundBrush(QBrush(QColor(255, 255, 255)))
        except Exception as e:
            print(f"更新背景颜色时出错: {e}")
    
    def update_connection_colors(self):
        """更新所有连接线的颜色以适应当前主题"""
        if hasattr(self, 'connections'):
            line_color = self.get_connection_line_color()
            for conn in self.connections:
                if 'line' in conn and conn['line']:
                    # 更新连接线颜色
                    pen = conn['line'].pen()
                    pen.setColor(line_color)
                    conn['line'].setPen(pen)
    
    def update_theme_colors(self):
        """更新主题相关的所有颜色"""
        # 更新画布背景颜色
        self.update_background_color()
        
        # 更新连接线颜色
        self.update_connection_colors()
        
        # 重新绘制网格
        # 先清除现有网格线（z值为-1的线条）
        items_to_remove = []
        for item in self.scene.items():
            if item.zValue() == -1:  # 网格线的z值为-1
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.scene.removeItem(item)
        
        # 重新绘制网格
        self.draw_grid()
        
        # 更新所有组件的标签颜色
        for item in self.scene.items():
            if hasattr(item, 'update_label_color'):
                item.update_label_color()
    
    def clear_canvas(self):
        """清空画布"""
        self.scene.clear()
        self.draw_grid()

    def fit_in_view(self):
        """适应视图，根据已使用的画布面积自动调整视图范围"""
        # 获取所有非背景项目（z值大于-1的项目，排除网格线等背景元素）
        network_items = [item for item in self.scene.items() if item.zValue() > -1]
        
        if not network_items:
            # 如果没有网络组件，重置到默认视图
            self.resetTransform()
            return
        
        # 计算所有网络组件的边界矩形
        rect = network_items[0].sceneBoundingRect()
        for item in network_items[1:]:
            rect = rect.united(item.sceneBoundingRect())
        
        # 添加边距以获得更好的视觉效果（边界矩形扩大20%）
        margin = max(rect.width(), rect.height()) * 0.1
        rect.adjust(-margin, -margin, margin, margin)
        
        # 适应视图，保持宽高比
        self.fitInView(rect, Qt.KeepAspectRatio)
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 获取选中的组件
        selected_items = self.scene.selectedItems()
        
        if selected_items:
            # 处理旋转快捷键
            if event.key() == Qt.Key_Left or event.key() == Qt.Key_Q:
                # 向左旋转90度（逆时针）
                for item in selected_items:
                    if hasattr(item, 'rotate_component'):
                        item.rotate_component(-90)
                event.accept()
                return
            elif event.key() == Qt.Key_Right or event.key() == Qt.Key_E:
                # 向右旋转90度（顺时针）
                for item in selected_items:
                    if hasattr(item, 'rotate_component'):
                        item.rotate_component(90)
                event.accept()
                return
        
        # 如果没有处理，传递给父类
        super().keyPressEvent(event)
    
    def on_selection_changed(self):
        """处理选择变化事件"""
        selected_items = self.scene.selectedItems()
        
        # 如果只选中一个项目，发出该项目；否则发出None
        if len(selected_items) == 1:
            self.selection_changed.emit(selected_items[0])
        else:
            self.selection_changed.emit(None)
    
    def update_status_bar(self):
        """更新状态栏显示"""
        if not self.main_window or not hasattr(self.main_window, 'statusBar'):
            return
            
        selected_items = self.scene.selectedItems()
        
        if selected_items:
            # 有组件被选中，显示操作提示
            count = len(selected_items)
            if count == 1:
                message = f"已选中 1 个组件 | 双击修改名称 | 旋转: ←/Q键(逆时针) →/E键(顺时针) | 右键菜单可选择旋转"
            else:
                message = f"已选中 {count} 个组件 | 旋转: ←/Q键(逆时针) →/E键(顺时针) | 右键菜单可选择旋转"
        else:
            # 没有选中组件，显示默认状态和视图操作快捷键提示
            message = "就绪 | 拖拽组件到画布，点击组件进行选择和连接 | 视图: Ctrl++(放大) Ctrl+-(缩小) Ctrl+0(适应视图) 右键拖动画布"
            
        self.main_window.statusBar().showMessage(message)