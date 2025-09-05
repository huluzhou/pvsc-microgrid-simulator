#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
电网组件图形项，用于在画布上显示各种电网元件
"""

from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QMenu, QMessageBox, QInputDialog, QApplication
from PySide6.QtCore import Qt, QPointF, Signal, QObject, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QTransform, QPalette
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
    
    # 类级别的索引计数器，用于为每种组件类型分配唯一索引
    _component_counters = {}

    def __init__(self, pos, parent=None):
        super().__init__(parent)
        self.setPos(pos)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        # 设置接受鼠标事件
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
        
        # 双击计时器相关
        self.last_click_time = 0
        self.double_click_threshold = 500  # 双击时间阈值（毫秒）
        
        # 组件属性
        self.component_type = "base"
        self.component_name = "基础组件"
        self.properties = {}
        
        # 索引将在子类中设置component_type后分配
        self.component_index = None
        
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
        # 设置标签可拖动，防止遮挡
        self.label.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.label.setFlag(QGraphicsItem.ItemIsSelectable, True)
        
        # 根据主题设置标签颜色
        self.update_label_color()
        
        # 设置Z值，确保组件在网格之上
        self.setZValue(10)
        
        # 连接点位置和状态
        self.connection_points = []
        self.connection_point_states = {}  # 记录每个连接点的占用状态 {point_index: connected_item}
        
        # 连接约束
        self.max_connections = -1  # -1表示无限制，其他数字表示最大连接数
        self.min_connections = 0   # 最小连接数
        self.current_connections = []  # 当前连接的组件列表
        self.connection_point_states = {}  # 记录每个连接点的占用状态 {point_index: connected_item}
    
    def _get_next_index(self):
        """获取下一个可用的组件索引"""
        if self.component_type not in self._component_counters:
            self._component_counters[self.component_type] = 0
        self._component_counters[self.component_type] += 1
        return self._component_counters[self.component_type]
    
    def update_label_color(self):
        """根据当前主题更新标签颜色"""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # 检查是否为深色主题
                bg_color = palette.color(QPalette.Window)
                is_dark_theme = bg_color.lightness() < 128
                
                if is_dark_theme:
                    # 深色主题使用白色文字
                    self.label.setDefaultTextColor(QColor(255, 255, 255))
                else:
                    # 浅色主题使用黑色文字
                    self.label.setDefaultTextColor(QColor(0, 0, 0))
            else:
                # 默认黑色
                self.label.setDefaultTextColor(QColor(0, 0, 0))
        except Exception as e:
            print(f"更新标签颜色时出错: {e}")
            self.label.setDefaultTextColor(QColor(0, 0, 0))
    
    def reload_svg_for_theme(self):
        """重新加载SVG以适应当前主题"""
        if hasattr(self, 'svg_filename') and self.svg_filename:
            self.load_svg(self.svg_filename)
            # 触发重绘
            self.update()

    def load_svg(self, svg_filename):
        """加载SVG文件，支持主题适配"""
        try:
            # 保存文件名以便主题切换时重新加载
            self.svg_filename = svg_filename
            
            # 使用get_resource_path函数获取正确的资源路径
            svg_path = get_resource_path(os.path.join("assets", svg_filename))
            if not os.path.exists(svg_path):
                # 尝试开发环境路径
                svg_path = get_resource_path(os.path.join("src", "assets", svg_filename))
            
            if os.path.exists(svg_path):
                # 读取SVG内容
                with open(svg_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                # 检测当前主题
                app = QApplication.instance()
                if app:
                    palette = app.palette()
                    # 检查是否为深色主题
                    bg_color = palette.color(QPalette.Window)
                    is_dark_theme = bg_color.lightness() < 128
                    
                    if is_dark_theme:
                        # 深色主题：将黑色替换为白色
                        svg_content = svg_content.replace('#000000', '#FFFFFF')
                        svg_content = svg_content.replace('stroke="black"', 'stroke="white"')
                        svg_content = svg_content.replace('fill="black"', 'fill="white"')
                        svg_content = svg_content.replace('#333333', '#CCCCCC')
                        svg_content = svg_content.replace('stroke="#333333"', 'stroke="#cccccc"')
                        svg_content = svg_content.replace('fill="#333333"', 'fill="#cccccc"')
                    else:
                        # 浅色主题：将白色元素替换为黑色
                        svg_content = svg_content.replace('#FFFFFF', '#000000')
                        svg_content = svg_content.replace('stroke="white"', 'stroke="black"')
                        svg_content = svg_content.replace('fill="white"', 'fill="black"')
                        svg_content = svg_content.replace('#ffffff', '#000000')
                        svg_content = svg_content.replace('#fff', '#000')
                        svg_content = svg_content.replace('#CCCCCC', '#333333')
                        svg_content = svg_content.replace('stroke="#cccccc"', 'stroke="#333333"')
                        svg_content = svg_content.replace('fill="#cccccc"', 'fill="#333333"')
                
                # 使用修改后的SVG内容创建渲染器
                self.svg_renderer = QSvgRenderer()
                self.svg_renderer.load(svg_content.encode('utf-8'))
            else:
                print(f"警告: SVG文件未找到: {svg_filename}")
                print(f"尝试的路径: {svg_path}")
                self.svg_renderer = None
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
        elif change == QGraphicsItem.ItemSelectedChange and value:
            # 发出选中信号
            self.signals.itemSelected.emit(self)
        # 处理位置已经改变
        elif change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            # 更新连接线
            self.update_connections()
            # 更新geodata为当前位置的(x,y)元组
            pos = self.pos()
            self.properties["geodata"] = (pos.x(), pos.y())
            
            # 通知属性面板刷新
            try:
                scene = self.scene()
                if scene:
                    views = scene.views()
                    if views:
                        main_window = views[0].window()
                        if hasattr(main_window, 'properties_panel'):
                            # 如果当前组件被选中，刷新属性面板显示
                            if main_window.properties_panel.current_item == self:
                                main_window.properties_panel.update_properties(self)
                            # 触发属性变化信号，确保主窗口能处理这个变化
                            main_window.properties_panel.property_changed.emit(self.component_type, 'geodata', self.properties["geodata"])
            except Exception as e:
                print(f"刷新属性面板时出错: {e}")
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



        # 根据旋转角度计算新的连接点位置
        angle_rad = math.radians(self.rotation_angle)
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        
        # 更新连接点位置
        self.connection_points = []
        for original_point in self.original_connection_points:
            # 旋转变换
            x = original_point.x() * cos_angle - original_point.y() * sin_angle
            y = original_point.x() * sin_angle + original_point.y() * cos_angle
            self.connection_points.append(QPointF(x, y))
    
    def can_connect(self):
        """检查是否可以添加新连接"""
        if self.max_connections == -1:
            return True
        return len(self.current_connections) < self.max_connections
    
    def add_connection(self, connected_item=None, connection_point_index=None):
        """添加连接"""
        if self.can_connect():
            self.current_connections.append(connected_item)
            # 如果指定了连接点索引，管理该连接点的连接状态
            if connection_point_index is not None:
                if connection_point_index not in self.connection_point_states:
                    self.connection_point_states[connection_point_index] = []
                self.connection_point_states[connection_point_index].append(connected_item)
            # 更新bus参数
            self.update_bus_parameter()
            return True
        return False
    
    def remove_connection(self, connected_item=None, connection_point_index=None):
        """移除连接"""
        if len(self.current_connections) > 0:
            if connected_item and connected_item in self.current_connections:
                self.current_connections.remove(connected_item)
            elif len(self.current_connections) > 0:
                self.current_connections.pop()
            # 如果指定了连接点索引，从该连接点的连接列表中移除
            if connection_point_index is not None and connection_point_index in self.connection_point_states:
                if connected_item in self.connection_point_states[connection_point_index]:
                    self.connection_point_states[connection_point_index].remove(connected_item)
                # 如果连接点没有连接了，删除该键
                if not self.connection_point_states[connection_point_index]:
                    del self.connection_point_states[connection_point_index]
            # 更新bus参数
            self.update_bus_parameter()
            return True
        return False
    
    def update_bus_parameter(self):
        """更新bus参数"""
        # 保存旧的bus值以检测变化
        old_bus_values = {}
        
        # 处理单个bus连接的组件
        if hasattr(self, 'properties') and 'bus' in self.properties:
            old_bus_values['bus'] = self.properties.get('bus')
            
            # 查找连接的bus组件
            connected_bus = None
            for connected_item in self.current_connections:
                if hasattr(connected_item, 'component_type') and connected_item.component_type == 'bus':
                    connected_bus = connected_item
                    break
            
            # 更新bus参数
            if connected_bus:
                if hasattr(connected_bus, 'component_index'):
                    self.properties['bus'] = str(connected_bus.component_index)
                else:
                    self.properties['bus'] = str(connected_bus.properties.get('index', 'Unknown'))
            else:
                self.properties['bus'] = None
        
        # 处理变压器的hv_bus和lv_bus
        elif hasattr(self, 'component_type') and self.component_type == 'transformer':
            old_bus_values['hv_bus'] = self.properties.get('hv_bus')
            old_bus_values['lv_bus'] = self.properties.get('lv_bus')
            
            # 获取连接的bus组件
            connected_buses = []
            for connected_item in self.current_connections:
                if hasattr(connected_item, 'component_type') and connected_item.component_type == 'bus':
                    bus_index = str(connected_item.component_index) if hasattr(connected_item, 'component_index') else str(connected_item.properties.get('index', 'Unknown'))
                    connected_buses.append(bus_index)
            
            # 更新hv_bus和lv_bus
            if len(connected_buses) >= 2:
                self.properties['hv_bus'] = connected_buses[0]  # 第一个连接点为高压侧
                self.properties['lv_bus'] = connected_buses[1]  # 第二个连接点为低压侧
            elif len(connected_buses) == 1:
                self.properties['hv_bus'] = connected_buses[0]
                self.properties['lv_bus'] = None
            else:
                self.properties['hv_bus'] = None
                self.properties['lv_bus'] = None
        
        # 处理线路的from_bus和to_bus
        elif hasattr(self, 'component_type') and self.component_type == 'line':
            old_bus_values['from_bus'] = self.properties.get('from_bus')
            old_bus_values['to_bus'] = self.properties.get('to_bus')
            
            # 获取连接的bus组件
            connected_buses = []
            for connected_item in self.current_connections:
                if hasattr(connected_item, 'component_type') and connected_item.component_type == 'bus':
                    bus_index = str(connected_item.component_index) if hasattr(connected_item, 'component_index') else str(connected_item.properties.get('index', 'Unknown'))
                    connected_buses.append(bus_index)
            
            # 更新from_bus和to_bus
            if len(connected_buses) >= 2:
                self.properties['from_bus'] = connected_buses[0]  # 第一个连接点为起始母线
                self.properties['to_bus'] = connected_buses[1]    # 第二个连接点为终止母线
            elif len(connected_buses) == 1:
                self.properties['from_bus'] = connected_buses[0]
                self.properties['to_bus'] = None
            else:
                self.properties['from_bus'] = None
                self.properties['to_bus'] = None
        
        # 检查是否有变化，如果有则通知属性面板刷新
        has_changes = False
        for key, old_value in old_bus_values.items():
            if self.properties.get(key) != old_value:
                has_changes = True
                break
        
        if has_changes:
            # 通过场景查找主窗口并刷新属性面板
            try:
                from PySide6.QtCore import QTimer
                scene = self.scene()
                if scene:
                    views = scene.views()
                    if views:
                        main_window = views[0].window()
                        if hasattr(main_window, 'properties_panel'):
                            # 延迟刷新以避免递归调用
                            QTimer.singleShot(10, lambda: main_window.properties_panel.update_properties(self))
            except Exception as e:
                pass  # 忽略错误，避免影响主要功能
    
    def is_connection_point_available(self, point_index, connecting_item=None):
        """检查指定连接点是否可用"""
        if point_index not in self.connection_point_states:
            return True
        
        connections = self.connection_point_states[point_index]
        
        # 如果已经有2个连接，不能再连接
        if len(connections) >= 2:
            return False
        
        # 如果只有1个连接
        if len(connections) == 1:
            existing_item = connections[0]
            # 如果现有连接是电表，新连接可以是任何非电表组件
            if hasattr(existing_item, 'component_type') and existing_item.component_type == 'meter':
                return connecting_item is None or (hasattr(connecting_item, 'component_type') and connecting_item.component_type != 'meter')
            # 如果现有连接不是电表，新连接必须是电表
            else:
                return connecting_item is not None and hasattr(connecting_item, 'component_type') and connecting_item.component_type == 'meter'
        
        return True
    
    def get_available_connection_points(self, connecting_item=None):
        """获取所有可用的连接点索引"""
        available_points = []
        for i in range(len(self.connection_points)):
            if self.is_connection_point_available(i, connecting_item):
                available_points.append(i)
        return available_points
    
    def validate_connections(self):
        """验证连接是否满足约束"""
        if len(self.current_connections) < self.min_connections:
            return False, f"{self.component_name}至少需要{self.min_connections}个连接"
        if self.max_connections != -1 and len(self.current_connections) > self.max_connections:
            return False, f"{self.component_name}最多只能有{self.max_connections}个连接"
        return True, ""
    
    def disconnect_all_connections(self):
        """断开所有连接"""
        if hasattr(self, 'scene') and self.scene():
            # 获取画布对象
            canvas = None
            for view in self.scene().views():
                if hasattr(view, 'disconnect_all_from_item'):
                    canvas = view
                    break
            
            if canvas:
                canvas.disconnect_all_from_item(self)
    
    def delete_component(self):
        """删除组件"""
        if self.scene():
            # 先断开所有连接
            self.disconnect_all_connections()
            
            # 清除Modbus设备缓存，因为场景已变化
            scene = self.scene()
            if scene:
                views = scene.views()
                if views:
                    canvas = views[0]
                    if hasattr(canvas, 'modbus_manager') and canvas.modbus_manager:
                        canvas.modbus_manager.clear_device_cache()
            
            # 从场景中移除
            scene.removeItem(self)
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
        
        if event.button() == Qt.LeftButton:
            import time
            current_time = int(time.time() * 1000)  # 当前时间（毫秒）
            
            # 检查是否为双击
            if current_time - self.last_click_time < self.double_click_threshold:
                self.handle_double_click()
                return  # 双击时直接返回，不执行单击逻辑
            
            # 选中当前项
            self.setSelected(True)
            # 手动发出选中信号
            print(f"发出选中信号: {self.component_type}")
            self.signals.itemSelected.emit(self)
            
            self.last_click_time = current_time
    
    def handle_double_click(self):
        """处理双击事件，弹出名称编辑对话框"""
        current_name = self.properties.get('name', self.component_name)
        
        # 弹出输入对话框
        new_name, ok = QInputDialog.getText(
            None,
            '修改组件名称',
            f'请输入新的{self.component_name}名称:',
            text=current_name
        )
        
        if ok and new_name:
            # 更新所有名称相关的属性
            self.properties['name'] = new_name
            self.component_name = new_name
            self.label.setPlainText(new_name)
            
            # 通知属性面板刷新并触发信号
            try:
                scene = self.scene()
                if scene:
                    views = scene.views()
                    if views:
                        main_window = views[0].window()
                        if hasattr(main_window, 'properties_panel'):
                            # 如果当前组件被选中，刷新属性面板显示
                            if main_window.properties_panel.current_item == self:
                                main_window.properties_panel.update_properties(self)
                            # 触发属性变化信号，确保主窗口能处理这个变化
                            main_window.properties_panel.property_changed.emit(self.component_type, 'name', new_name)
            except Exception as e:
                print(f"刷新属性面板时出错: {e}")


class StorageItem(BaseNetworkItem):
    """储能组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "storage"
        self.component_name = "储能"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        # 动态生成名称
        component_name = f"Storage {self.component_index}"
        self.properties = {
            "name": component_name,  # 名称
            "index": self.component_index,  # 组件索引
            "sn_mva": 1.0,
            "geodata": (0, 0),
            "p_mw": 1.0,  # 额定功率
            "max_e_mwh": 50.0,  # 最大储能容量
            "soc_percent": 50.0,  # 荷电状态百分比
            "bus": None,  # 连接的母线
            "sn": component_name,  # 序列号
            "brand": "",  # 品牌
            "ip": "127.0.0.1",  # 使用本地回环地址作为默认IP
            "port": f"{8000 + self.component_index}",
        }
        self.label.setPlainText("母线")
        
        # 连接约束：储能可以连接一个母线和一个电表
        self.max_connections = 2
        self.min_connections = 1
        
        # 加载SVG图标
        self.load_svg("storage.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(0, -28),   # 线头端点（上侧）
        ]
        self.original_connection_points = self.connection_points.copy()
        
        # 实时数据变量初始化
        self.soc_percent = 50.0  # 荷电状态百分比
        self.today_charge_energy = 0.0  # 今日充电电量 (kWh)
        self.today_discharge_energy = 0.0  # 今日放电电量 (kWh)
        self.total_charge_energy = 0.0  # 累计充电电量 (kWh)
        self.total_discharge_energy = 0.0  # 累计放电电量 (kWh)
        self.state = 'power_off'  # 初始状态为halt
        
    def update_realtime_data(self, current_power_mw, time_delta_hours=1.0):
        """
        更新实时数据
        
        Args:
            current_power_mw: 当前功率 (MW)，正值为充电，负值为放电
            time_delta_hours: 时间间隔 (小时)
        """
        # 功率转换为 kW
        current_power_kw = current_power_mw * 1000
        
        # 计算电量变化 (kWh)
        energy_delta = abs(current_power_kw) * time_delta_hours
        
        # 更新SOC
        max_energy_kwh = self.properties.get("max_e_mwh", 50.0) * 1000
        if current_power_kw > 0:  # 充电
            self.soc_percent = min(100, self.soc_percent + (energy_delta / max_energy_kwh) * 100)
            self.today_charge_energy += energy_delta
            self.total_charge_energy += energy_delta
        elif current_power_kw < 0:  # 放电
            self.soc_percent = max(0, self.soc_percent - (energy_delta / max_energy_kwh) * 100)
            self.today_discharge_energy += energy_delta
            self.total_discharge_energy += energy_delta
            
        # 更新属性中的SOC值
        self.properties["soc_percent"] = self.soc_percent
        
    def reset_daily_energy(self):
        """重置今日电量数据"""
        self.today_charge_energy = 0.0
        self.today_discharge_energy = 0.0


        



class ChargerItem(BaseNetworkItem):
    """充电站组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "charger"
        self.component_name = "充电站"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        # 动态生成名称
        component_name = f"Charger {self.component_index}"
        self.properties = {
            "index": self.component_index,  # 组件索引
            "geodata": (0, 0),
            "sn_mva": 1.0,
            "p_mw": 1.0,  # 充电功率
            "efficiency": 0.95,  # 充电效率
            "name": component_name,  # 名称
            "bus": None,  # 连接的母线
            "sn": component_name,  # 序列号
            "brand": "",  # 品牌
            "ip": "127.0.0.1",  # 使用本地回环地址作为默认IP
            "port": f"{8000 + self.component_index}",
        }
        self.label.setPlainText("母线")
        
        # 连接约束：充电站可以连接一个母线和一个电表
        self.max_connections = 2
        self.min_connections = 1
        
        # 加载SVG图标
        self.load_svg("charger.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(0, -28)   # 线头端点（上侧）
        ]
        self.original_connection_points = self.connection_points.copy()
        



class BusItem(BaseNetworkItem):
    """母线组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "bus"
        self.component_name = "母线"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        self.properties = {
            "index": self.component_index,  # 组件索引
            "vn_kv": 20.0,  # 电网电压等级 [kV]
            "geodata": (0, 0),
        }
        self.label.setPlainText("母线")
        
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
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        self.properties = {
            "index": self.component_index,  # 组件索引
            "geodata": (0, 0),
            # 通用参数
            "length_km": 1.0,  # 线路长度 [km]
            "use_standard_type": True,  # 使用标准类型
            
            # 标准类型选择 (用于create_line)
            "std_type": "NAYY 4x50 SE",  # 标准类型
            
            # 自定义参数 (用于create_line_from_parameters)
            "r_ohm_per_km": 0.1,  # 线路电阻 [Ω/km]
            "x_ohm_per_km": 0.1,  # 线路电抗 [Ω/km]
            "c_nf_per_km": 0.0,  # 线路电容 [nF/km]
            "r0_ohm_per_km": 0.0,  # 零序电阻 [Ω/km]
            "x0_ohm_per_km": 0.0,  # 零序电抗 [Ω/km]
            "c0_nf_per_km": 0.0,  # 零序电容 [nF/km]
            "max_i_ka": 1.0,  # 最大热电流 [kA]
            
            # 连接属性
            "from_bus": None,  # 起始母线
            "to_bus": None,  # 终止母线
            "name": "线路",  # 名称
        }
        self.label.setPlainText("线路")
        
        # 连接约束：线路必须连接两个组件
        self.max_connections = 4
        self.min_connections = 2
        
        # 加载SVG图标
        self.load_svg("line.svg")
        
        # 定义连接点（相对于组件中心的位置）- 旋转90度后
        self.connection_points = [
            QPointF(0, -25),  # 上端点
            QPointF(0, 25)    # 下端点
        ]
        self.original_connection_points = self.connection_points.copy()


class TransformerItem(BaseNetworkItem):
    """变压器组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "transformer"
        self.component_name = "变压器"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        self.properties = {
            "index": self.component_index,  # 组件索引
            "geodata": (0, 0),
            "use_standard_type": True,  # 使用标准类型
            
            # 标准类型参数
            "std_type": "25 MVA 110/20 kV",  # 标准类型
            
            # 自定义类型参数
            "sn_mva": 25.0,  # 额定容量
            "vn_hv_kv": 110.0,  # 高压侧额定电压
            "vn_lv_kv": 20.0,   # 低压侧额定电压
            "vkr_percent": 0.3,  # 短路电阻电压
            "vk_percent": 12.0,  # 短路电压
            "pfe_kw": 14.0,  # 铁损
            "i0_percent": 0.07,  # 空载电流
            "vector_group": "Dyn",  # 接线组别
            
            # 零序参数 (标准类型和自定义类型都需要)
            "vk0_percent": 0.0,  # 零序短路电压
            "vkr0_percent": 0.0,  # 零序短路电阻电压
            "mag0_percent": 0.0,  # 零序励磁阻抗
            "mag0_rx": 0.0,  # 零序励磁R/X比
            "si0_hv_partial": 0.0,  # 零序漏抗高压侧分配
            
            # 连接属性
            "hv_bus": None,  # 高压侧母线
            "lv_bus": None,  # 低压侧母线
            "name": "变压器",  # 名称
        }
        self.label.setPlainText(self.properties["name"])
        
        # 连接约束：变压器必须连接两个bus
        self.max_connections = 4
        self.min_connections = 2
        
        # 加载SVG图标
        self.load_svg("transformer.svg")
        
        # 定义连接点（相对于组件中心的位置）- 旋转90度后
        self.connection_points = [
            QPointF(0, -25),  # 高压侧（上方）
            QPointF(0, 25)    # 低压侧（下方）
        ]
        self.original_connection_points = self.connection_points.copy()


class GeneratorItem(BaseNetworkItem):
    """发电机组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "generator"
        self.component_name = "发电机"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        self.properties = {
            "index": self.component_index,  # 组件索引
            "geodata": (0, 0),
            "p_mw": 50.0,  # 有功功率
            "vm_pu": 1.0,  # 电压幅值
            "name": "Generator 1",  # 名称
            "bus": None,  # 连接的母线
            "ip": "127.0.0.1",  # 使用本地回环地址作为默认IP
            "port": f"{8000 + self.component_index}",
        }
        self.label.setPlainText(self.properties["name"])
        
        # 连接约束：发电机可以连接一个母线和一个电表
        self.max_connections = 2
        self.min_connections = 1
        
        # 加载SVG图标
        self.load_svg("generator.svg")
        
        # 定义连接点（相对于组件中心的位置）- 逆时针旋转90度后
        self.connection_points = [
            QPointF(0, 28)   # 线头端点（下方）
        ]
        self.original_connection_points = self.connection_points.copy()


class LoadItem(BaseNetworkItem):
    """负荷组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "load"
        self.component_name = "负荷"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        self.properties = {
            "index": self.component_index,  # 组件索引
            "geodata": (0, 0),
            "p_mw": 1.0,  # 有功功率
            "q_mvar": 0.0,  # 无功功率
            "name": "Load 1",  # 名称
            "bus": None,  # 连接的母线
            "ip": "192.168.1.100",
            "port": f"{8000 + self.component_index}",
        }
        self.label.setPlainText(self.properties["name"])
        
        # 连接约束：负荷可以连接一个bus和一个电表
        self.max_connections = 2
        self.min_connections = 1
        
        # 加载SVG图标
        self.load_svg("load.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(0, -28)   # 线头端点（上侧）
        ]
        self.original_connection_points = self.connection_points.copy()
class ExternalGridItem(BaseNetworkItem):
    """外部电网组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "external_grid"
        self.component_name = "外部电网"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        self.properties = {
            "index": self.component_index,  # 组件索引
            "geodata": (0, 0),
            "vm_pu": 1.0,  # 电压标幺值
            "va_degree": 0.0,  # 电压角度
            "name": "External Grid 1",  # 名称
            "s_sc_max_mva": 1000.0,  # 最大短路容量
            "s_sc_min_mva": 800.0,  # 最小短路容量
            "rx_max": 0.1,  # 最大R/X比
            "rx_min": 0.1,  # 最小R/X比
            "bus": None,  # 连接的母线
        }
        self.label.setPlainText(self.properties["name"])
        
        # 连接约束：外部电网可以连接一个母线和一个电表
        self.max_connections = 2
        self.min_connections = 1
        
        # 加载SVG图标
        self.load_svg("external_grid.svg")
        
        # 定义连接点（相对于组件中心的位置）- 旋转270度后
        self.connection_points = [
            QPointF(0, 25)    # 下方连接点
        ]
        self.original_connection_points = self.connection_points.copy()


class StaticGeneratorItem(BaseNetworkItem):
    """光伏组件"""

    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "static_generator"
        self.component_name = "光伏"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        # 动态生成名称
        component_name = f"Static Generator {self.component_index}"
        self.properties = {
            "index": self.component_index,  # 组件索引
            "geodata": (0, 0),
            # 通用参数
            "use_power_factor": False,  # 使用功率因数模式
            
            # 直接功率模式参数
            "p_mw": 1.0,  # 有功功率 (MW)
            "q_mvar": 0.0,  # 无功功率 (Mvar)
            
            # 功率因数模式参数
            "sn_mva": 1.0,  # 额定功率 (MVA)
            "cos_phi": 0.9,  # 功率因数
            "mode": "overexcited",  # 运行模式
            
            # 其他参数
            "scaling": 1.0,  # 缩放因子
            "type": "wye",  # 连接类型
            "in_service": True,  # 投入运行
            "name": component_name,  # 名称
            "bus": None,  # 连接的母线
            "sn": component_name,  # 序列号
            "brand": "",  # 品牌
            "ip": "127.0.0.1",  # 使用本地回环地址作为默认IP
            "port": f"{8000 + self.component_index}",
        }
        self.today_discharge_energy = 0.0
        self.total_discharge_energy = 0.0
        self.update_power_limits()
        self.label.setPlainText(self.properties["name"])
        
        # 连接约束：光伏可以连接一个母线和一个电表
        self.max_connections = 2
        self.min_connections = 1
        
        # 加载SVG图标
        self.load_svg("static_generator.svg")
        
        # 定义连接点（相对于组件中心的位置）- 逆时针旋转90度后
        self.connection_points = [
            QPointF(0, -28)   # 线头端点（下方）
        ]
        self.original_connection_points = self.connection_points.copy()
        
    def update_power_limits(self):
        """更新功率限制值"""
        sn_mva = self.properties.get("sn_mva", 1.0)
        self.active_power_limit = sn_mva * 1000 * 1.1  # kw (110% 额定功率)
        self.active_power_limit_per = sn_mva * 1000    # kw (100% 额定功率)


class MeterItem(BaseNetworkItem):
    """电表组件"""
    
    def __init__(self, pos, parent=None):
        super().__init__(pos, parent)
        self.component_type = "meter"
        self.component_name = "Meter 1"
        # 在设置component_type后分配索引
        self.component_index = self._get_next_index()
        # 动态生成名称
        component_name = f"Meter {self.component_index}"
        
        # 初始化属性
        self.properties = {
            "index": self.component_index,  # 组件索引
            "geodata": (0, 0),
            "meas_type": "p",  # 测量类型 - 默认测量有功功率
            "element_type": "bus",  # 测量元件类型
            "value": 0.0,  # 测量值
            "std_dev": 0.01,  # 标准偏差
            "element": 0,  # 元件索引
            "side": None,  # 测量侧
            "in_service": True,  # 投入运行
            "name": component_name,  # 名称
            "bus": None,  # 连接的母线
            "sn": component_name,  # 序列号
            "brand": "",  # 品牌
            "ip": "192.168.1.100",
            "port": f"{8000 + self.component_index}",
        }
        self.label.setPlainText(self.properties["name"])
        
        # 连接约束：电表可以连接到多个组件
        self.max_connections =  1 # 允许连接多个组件
        self.min_connections = 1   # 不强制要求连接
        
        # 加载SVG图标
        self.load_svg("meter.svg")
        
        # 定义连接点（相对于组件中心的位置）
        self.connection_points = [
            QPointF(0, 32)   # 底部连接点
        ]
        self.original_connection_points = self.connection_points.copy()
        