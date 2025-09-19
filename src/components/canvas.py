#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络画布组件，用于绘制和编辑电网拓扑图
"""

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QApplication, QMessageBox
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPalette

from components.network_items import BusItem, LineItem, TransformerItem, LoadItem, StorageItem, ChargerItem, ExternalGridItem, StaticGeneratorItem, MeterItem
from models.network_model import NetworkModel


class NetworkCanvas(QGraphicsView):
    """电网画布类，用于绘制和编辑电网拓扑图"""
    
    # 信号：选择变化时发出
    selection_changed = Signal(object)  # 发出当前选中的单个项目，如果多选或无选择则为None

    def __init__(self, parent=None):
        super().__init__(parent)
        # 保存父窗口引用用于更新状态栏
        self.main_window = parent
        # 初始化网络模型
        self.network_model = None
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
        
        # 设置初始滚动条样式
        self.update_scrollbar_styles()
        
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

    def create_component(self, component_type, pos):
        """创建电网组件"""
        
        # 检查是否已存在外部电网，如果尝试创建第二个则阻止
        if component_type == "external_grid":
            existing_external_grids = [item for item in self.scene.items() 
                                       if hasattr(item, 'component_type') and item.component_type == "external_grid"]
            if existing_external_grids:
                # 显示警告消息
                QMessageBox.warning(self, "创建限制", 
                                  "系统中只能存在一个外部电网设备！")
                return None
        
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
        elif component_type == "meter":
            item = MeterItem(pos)
        
        # 添加到场景
        if item:
            # 使用BaseNetworkItem的索引系统获取正确的索引
            # 组件在初始化时已经通过_get_next_index()获取了正确的索引
            
            # 生成与系统索引同步的名称
            auto_name = f"{item.component_name} {item.component_index}"
            item.component_name = auto_name
            
            # 更新组件属性中的名称
            if hasattr(item, 'properties') and 'name' in item.properties:
                item.properties['name'] = auto_name
            
            # 更新标签显示
            if hasattr(item, 'label'):
                item.label.setPlainText(auto_name)
            
            # 更新geodata属性为实际放置位置
            if hasattr(item, 'properties'):
                item.properties['geodata'] = (pos.x(), pos.y())
            
            self.scene.addItem(item)
            # 连接信号
            item.signals.itemSelected.connect(self.handle_item_selected)
            
            # 清除Modbus设备缓存，因为场景已变化
            if hasattr(self, 'modbus_manager') and self.modbus_manager:
                self.modbus_manager.clear_device_cache()
            
            return item
        
        return None

    def handle_item_selected(self, item):
        """处理组件被选中的事件"""
        print(f"组件被选中: {item.component_type}")
        # 如果已经有一个组件被选中，并且当前选中的是另一个组件，尝试连接它们
        if (
            hasattr(self, "first_selected_item")
            and self.first_selected_item
            and self.first_selected_item != item
        ):
            print(
                f"尝试连接: {self.first_selected_item.component_type} 和 {item.component_type}"
            )
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
    
    def create_network_model(self):
        """从画布上的图形组件创建pandapower网络模型"""
        try:
            # 创建新的网络模型
            self.network_model = NetworkModel()
            
            # 获取所有图形组件
            items = [item for item in self.scene.items() if hasattr(item, 'component_type')]
            
            if not items:
                print("画布上没有组件，无法创建网络模型")
                return False
            
            # 第一步：创建所有母线
            bus_items = [item for item in items if item.component_type == 'bus']
            bus_map = {}  # 存储图形项到pandapower母线索引的映射
            
            for bus_item in bus_items:
                try:
                    bus_idx = self.network_model.create_bus(
                        id(bus_item),  # 使用对象ID作为唯一标识
                        bus_item.properties if hasattr(bus_item, 'properties') else {}
                    )
                    bus_map[bus_item] = bus_idx
                    print(f"创建母线: {bus_item.component_name} -> 索引 {bus_idx}")
                except Exception as e:
                    print(f"创建母线 {bus_item.component_name} 时出错: {str(e)}")
                    return False
            
            if not bus_map:
                print("没有有效的母线组件，无法创建网络模型")
                return False
            
            # 第二步：创建连接到母线的组件（负载、发电机等，但不包括电表）
            non_meter_items = [item for item in items if item.component_type != 'bus' and item.component_type != 'meter']
            for item in non_meter_items:
                try:
                    # 查找该组件连接的母线
                    connected_buses = self.get_connected_buses(item, bus_map)
                    
                    if item.component_type == 'load':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.network_model.create_load(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建负载: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'external_grid':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.network_model.create_external_grid(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建外部电网: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'static_generator':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.network_model.create_static_generator(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建光伏: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'storage':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.network_model.create_storage(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建储能: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'charger':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.network_model.create_charger(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建充电站: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'transformer':
                        if len(connected_buses) >= 2:
                            hv_bus = connected_buses[0]
                            lv_bus = connected_buses[1]
                            self.network_model.create_transformer(
                                id(item),
                                hv_bus,
                                lv_bus,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建变压器: {item.component_name} -> 母线 {hv_bus}-{lv_bus}")
                    
                    elif item.component_type == 'line':
                        if len(connected_buses) >= 2:
                            from_bus = connected_buses[0]
                            to_bus = connected_buses[1]
                            self.network_model.create_line(
                                id(item),
                                from_bus,
                                to_bus,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建线路: {item.component_name} -> 母线 {from_bus}-{to_bus}")
                
                except Exception as e:
                    print(f"创建组件 {item.component_name} 时出错: {str(e)}")
                    # 继续处理其他组件，不中断整个过程

            # 第三步：最后创建电表设备（确保所有其他设备已创建）
            meter_items = [item for item in items if item.component_type == 'meter']
            for item in meter_items:
                try:
                    meter_idx = self.network_model.create_measurement(
                        id(item),
                        item.properties if hasattr(item, 'properties') else {}
                    )
                    print(f"创建电表: {item.component_name} -> 测量索引 {meter_idx}")
                            
                
                except Exception as e:
                    print(f"创建组件 {item.component_name} 时出错: {str(e)}")
                    # 继续处理其他组件，不中断整个过程
            
            print(f"网络模型创建完成，包含 {len(self.network_model.net.bus)} 个母线")
            import os
            from pandapower.file_io import to_json
            file_path = "network.json"
            to_json(self.network_model.net, file_path)
            # 获取完整保存路径
            full_path = os.path.abspath(file_path)
            print(f"网络模型已保存到: {full_path}")
            return True
            
        except Exception as e:
            print(f"创建网络模型时出错: {str(e)}")
            return False
    
    def get_connected_buses(self, item, bus_map):
        """获取与指定组件连接的母线列表"""
        connected_buses = []
        
        # 获取该组件的所有连接
        if hasattr(self, 'connections'):
            for conn in self.connections:
                if conn['item1'] == item:
                    # item连接到item2
                    if conn['item2'] in bus_map:
                        connected_buses.append(bus_map[conn['item2']])
                elif conn['item2'] == item:
                    # item连接到item1
                    if conn['item1'] in bus_map:
                        connected_buses.append(bus_map[conn['item1']])
        
        return connected_buses

            

    
    def _check_component_type_compatibility(self, item1, item2):
        """检查组件类型兼容性"""
        type1, type2 = item1.component_type, item2.component_type
        
        # 相同类型的组件不能相互连接
        if type1 == type2:
            return False
            
        # 母线可以连接到任何其他类型的组件
        if type1 == "bus" or type2 == "bus":
            return True
            
        # 电表可以连接到任何组件
        if type1 == "meter" or type2 == "meter":
            return True
            
        # 变压器和线路必须连接到母线或电表
        if type1 in ["transformer", "line"] or type2 in ["transformer", "line"]:
            # 如果其中一个是母线或电表，则允许连接
            if type1 in ["bus", "meter"] or type2 in ["bus", "meter"]:
                return True
            return False
            
        # 负载、存储、充电器、外部电网、光伏可以连接到母线或电表
        if type1 in ["load", "storage", "charger", "external_grid", "static_generator"] or type2 in ["load", "storage", "charger", "external_grid", "static_generator"]:
            # 如果其中一个是母线或电表，则允许连接
            if type1 in ["bus", "meter"] or type2 in ["bus", "meter"]:
                return True
            return False
            
        # 开关可以连接到母线或电表（已在上面的规则中处理）
        return False
    
    def can_connect(self, item1, item2):
        """检查两个组件是否可以连接"""
        # 检查是否已经连接
        if self.is_connected(item1, item2):
            return False
            
        # 初始化connections列表（如果不存在）
        if not hasattr(self, 'connections'):
            self.connections = []
        
        # 连接限制现在由连接点管理机制处理
        # 每个连接点最多支持2个连接，其中一个必须是电表
            
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
        
        # 电表连接后自动获取测量元件信息
        self._update_meter_properties_on_connection(item1, item2, point_index1, point_index2)
        
        # 连接关系发生改变，重置诊断标志位
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.network_is_valid = False
            print("网络连接已改变，诊断标志位已重置")
        
        return True
    
    def _update_meter_properties_on_connection(self, item1, item2, point_index1, point_index2):
        """电表连接后自动更新测量属性"""
        meter_item = None
        connected_item = None
        connected_point_index = None
        
        # 确定哪个是电表，哪个是被连接的组件
        if hasattr(item1, 'component_type') and item1.component_type == 'meter':
            meter_item = item1
            connected_item = item2
            connected_point_index = point_index2
        elif hasattr(item2, 'component_type') and item2.component_type == 'meter':
            meter_item = item2
            connected_item = item1
            connected_point_index = point_index1
        
        if not meter_item or not connected_item:
            return
        
        # 获取连接组件的类型和索引
        connected_type = getattr(connected_item, 'component_type', None)
        connected_index = getattr(connected_item, 'component_index', 0)
        
        # 获取网络模型中的实际索引
        actual_index = connected_index
        if hasattr(self, 'network_model') and self.network_model:
            # 对于不同类型的组件，获取其在网络模型中的实际索引
            if connected_type == 'static_generator':
                # 检查静态发电机是否存在
                if hasattr(self.network_model.net, 'sgen') and not self.network_model.net.sgen.empty:
                    if connected_index < len(self.network_model.net.sgen)+1:
                        actual_index = connected_index
                    else:
                        print(f"警告：静态发电机索引 {connected_index} 超出范围，使用索引 0")
                        actual_index = 0
                else:
                    print("警告：网络中没有静态发电机，无法创建电表关联")
                    return
            elif connected_type == 'load':
                # 检查负载是否存在
                if hasattr(self.network_model.net, 'load') and not self.network_model.net.load.empty:
                    if connected_index < len(self.network_model.net.load)+1:
                        actual_index = connected_index
                    else:
                        print(f"警告：负载索引 {connected_index} 超出范围，使用索引 0")
                        actual_index = 0
                else:
                    print("警告：网络中没有负载，无法创建电表关联")
                    return
            elif connected_type == 'gen':
                # 检查发电机是否存在
                if hasattr(self.network_model.net, 'gen') and not self.network_model.net.gen.empty:
                    if connected_index < len(self.network_model.net.gen)+1:
                        actual_index = connected_index
                    else:
                        print(f"警告：发电机索引 {connected_index} 超出范围，使用索引 0")
                        actual_index = 0
                else:
                    print("警告：网络中没有发电机，无法创建电表关联")
                    return
            elif connected_type == 'bus':
                # 检查母线是否存在
                if hasattr(self.network_model.net, 'bus') and not self.network_model.net.bus.empty:
                    if connected_index < len(self.network_model.net.bus)+1:
                        actual_index = connected_index
                    else:
                        print(f"警告：母线索引 {connected_index} 超出范围，使用索引 0")
                        actual_index = 0
                else:
                    print("警告：网络中没有母线，无法创建电表关联")
                    return
            elif connected_type == 'transformer':
                # 检查变压器是否存在
                if hasattr(self.network_model.net, 'trafo') and not self.network_model.net.trafo.empty:
                    if connected_index < len(self.network_model.net.trafo)+1:
                        actual_index = connected_index
                    else:
                        print(f"警告：变压器索引 {connected_index} 超出范围，使用索引 0")
                        actual_index = 0
                else:
                    print("警告：网络中没有变压器，无法创建电表关联")
                    return
            elif connected_type == 'line':
                # 检查线路是否存在
                if hasattr(self.network_model.net, 'line') and not self.network_model.net.line.empty:
                    if connected_index < len(self.network_model.net.line):
                        actual_index = connected_index
                    else:
                        print(f"警告：线路索引 {connected_index} 超出范围，使用索引 0")
                        actual_index = 0
                else:
                    print("警告：网络中没有线路，无法创建电表关联")
                    return
            elif connected_type == 'external_grid':
                # 检查外部电网是否存在
                if hasattr(self.network_model.net, 'ext_grid') and not self.network_model.net.ext_grid.empty:
                    if connected_index < len(self.network_model.net.ext_grid) + 1:
                        actual_index = connected_index
                    else:
                        print(f"警告：外部电网索引 {connected_index} 超出范围，使用索引 0")
                        actual_index = 0
                else:
                    print("警告：网络中没有外部电网，无法创建电表关联")
                    return
        else:
            actual_index = connected_index
        
        if not connected_type:
            return
        
        # 组件类型映射：将图形组件类型映射到pandapower元件类型
        type_mapping = {
            'transformer': 'trafo',
            'static_generator': 'sgen',
            'external_grid': 'ext_grid'
        }
        
        # 转换组件类型
        element_type = type_mapping.get(connected_type, connected_type)
        
        # 更新电表的测量属性
        meter_item.properties['element_type'] = element_type
        meter_item.properties['element'] = actual_index
        
        # 根据组件类型和连接点索引设置测量侧
        side = self._determine_measurement_side(connected_item, connected_point_index)
        meter_item.properties['side'] = side
        
        # 根据连接的组件类型设置合适的测量类型
        # 除非手动指定，都设置为测量有功功率
        meter_item.properties['meas_type'] = 'p'  # 默认测量有功功率
        
        print(f"电表 {meter_item.component_name} 已自动配置:")
        print(f"  测量元件类型: {meter_item.properties['element_type']}")
        print(f"  元件索引: {meter_item.properties['element']}")
        print(f"  测量侧: {meter_item.properties['side']}")
        print(f"  测量类型: {meter_item.properties['meas_type']}")
        print(f"  连接点索引: {connected_point_index}")
        
        # 强制刷新属性面板显示
        if hasattr(self, 'main_window') and self.main_window:
            properties_panel = getattr(self.main_window, 'properties_panel', None)
            if properties_panel:
                # 如果电表当前被选中，立即刷新属性面板
                if hasattr(properties_panel, 'current_item') and properties_panel.current_item == meter_item:
                    properties_panel.update_properties(meter_item)
                # 触发选择变化信号，确保属性面板能正确更新
                self.selection_changed.emit(meter_item)
        
    def _determine_measurement_side(self, connected_item, point_index):
        """根据连接的组件类型和连接点索引确定测量侧"""
        if not hasattr(connected_item, 'component_type'):
            return None
            
        component_type = connected_item.component_type
        
        # 对于变压器和线路，根据连接点索引确定测量侧
        if component_type == 'transformer':
            if point_index is not None:
                # 通常第一个连接点(索引0)是高压侧，第二个连接点(索引1)是低压侧
                if point_index == 0:
                    return 'hv'  # 高压侧
                elif point_index == 1:
                    return 'lv'  # 低压侧
                else:
                    return 'hv'  # 默认高压侧
            else:
                return 'hv'  # 默认高压侧
        elif component_type == 'line':
            if point_index is not None:
                # 通常第一个连接点(索引0)是from侧，第二个连接点(索引1)是to侧
                if point_index == 0:
                    return 'from'  # 从侧
                elif point_index == 1:
                    return 'to'  # 到侧
                else:
                    return 'from'  # 默认从侧
            else:
                return 'from'  # 默认从侧
        else:
            # 对于其他组件（bus、load、generator等），不需要侧别
            return None
        
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
                available_points = source_item.get_available_connection_points(target_item)
            
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
            # 左键点击，检查是否点击在空白区域
            scene_pos = self.mapToScene(event.pos())
            item_at_pos = self.scene.itemAt(scene_pos, self.transform())
            
            # 如果点击在空白区域（没有组件），重置选中状态
            if not item_at_pos or not hasattr(item_at_pos, 'component_type'):
                # 重置连接选中状态
                if hasattr(self, 'first_selected_item'):
                    self.first_selected_item = None
                    print("点击画布空白区域，重置选中状态")
                
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
        
        # 删除选中的项目，调用组件的delete_component方法
        for item in selected_items:
            if hasattr(item, 'delete_component'):
                item.delete_component()
            else:
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
        
        # 连接关系发生改变，重置诊断标志位
        if hasattr(self, 'main_window') and self.main_window:
            self.main_window.network_is_valid = False
            print("网络连接已改变，诊断标志位已重置")
    
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
        
        # 更新滚动条样式
        self.update_scrollbar_styles()
        
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
        
        # 更新所有组件的标签颜色和SVG图标
        for item in self.scene.items():
            if hasattr(item, 'update_label_color'):
                item.update_label_color()
            # 重新加载SVG以适应新主题
            if hasattr(item, 'reload_svg_for_theme'):
                item.reload_svg_for_theme()
    
    def update_scrollbar_styles(self):
        """更新滚动条样式以适应当前主题"""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # 检查是否为深色主题
                bg_color = palette.color(QPalette.Window)
                is_dark_theme = bg_color.lightness() < 128
                
                if is_dark_theme:
                    # 深色主题滚动条样式
                    scrollbar_style = """
                    QScrollBar:vertical {
                        background-color: rgb(53, 53, 53);
                        width: 16px;
                        border: none;
                    }
                    QScrollBar::handle:vertical {
                        background-color: rgb(80, 80, 80);
                        border-radius: 8px;
                        min-height: 20px;
                        margin: 2px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background-color: rgb(100, 100, 100);
                    }
                    QScrollBar::handle:vertical:pressed {
                        background-color: rgb(120, 120, 120);
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background: none;
                    }
                    QScrollBar:horizontal {
                        background-color: rgb(53, 53, 53);
                        height: 16px;
                        border: none;
                    }
                    QScrollBar::handle:horizontal {
                        background-color: rgb(80, 80, 80);
                        border-radius: 8px;
                        min-width: 20px;
                        margin: 2px;
                    }
                    QScrollBar::handle:horizontal:hover {
                        background-color: rgb(100, 100, 100);
                    }
                    QScrollBar::handle:horizontal:pressed {
                        background-color: rgb(120, 120, 120);
                    }
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                        border: none;
                        background: none;
                    }
                    """
                else:
                    # 浅色主题滚动条样式
                    scrollbar_style = """
                    QScrollBar:vertical {
                        background-color: rgb(240, 240, 240);
                        width: 16px;
                        border: none;
                    }
                    QScrollBar::handle:vertical {
                        background-color: rgb(200, 200, 200);
                        border-radius: 8px;
                        min-height: 20px;
                        margin: 2px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background-color: rgb(180, 180, 180);
                    }
                    QScrollBar::handle:vertical:pressed {
                        background-color: rgb(160, 160, 160);
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background: none;
                    }
                    QScrollBar:horizontal {
                        background-color: rgb(240, 240, 240);
                        height: 16px;
                        border: none;
                    }
                    QScrollBar::handle:horizontal {
                        background-color: rgb(200, 200, 200);
                        border-radius: 8px;
                        min-width: 20px;
                        margin: 2px;
                    }
                    QScrollBar::handle:horizontal:hover {
                        background-color: rgb(180, 180, 180);
                    }
                    QScrollBar::handle:horizontal:pressed {
                        background-color: rgb(160, 160, 160);
                    }
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                        border: none;
                        background: none;
                    }
                    """
                
                # 应用滚动条样式
                self.setStyleSheet(scrollbar_style)
                
        except Exception as e:
            print(f"更新滚动条样式时出错: {e}")
    
    def clear_canvas(self):
        """清空画布"""
        # 清除Modbus设备缓存，因为场景将被清空
        if hasattr(self, 'modbus_manager') and self.modbus_manager:
            self.modbus_manager.clear_device_cache()
            
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
            elif event.key() == Qt.Key_Delete:
                # DEL键删除选中的组件
                self.delete_selected_items()
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
                message = "已选中 1 个组件 | 双击修改名称 | 旋转: ←/Q键(逆时针) →/E键(顺时针) | DEL键删除 | 右键菜单"
            else:
                message = f"已选中 {count} 个组件 | 旋转: ←/Q键(逆时针) →/E键(顺时针) | DEL键删除 | 右键菜单"
        else:
            # 没有选中组件，显示默认状态和视图操作快捷键提示
            message = "就绪 | 拖拽组件到画布，点击组件进行选择和连接 | 视图: Ctrl++(放大) Ctrl+-(缩小) Ctrl+0(适应视图) 右键拖动画布"
            
        self.main_window.statusBar().showMessage(message)