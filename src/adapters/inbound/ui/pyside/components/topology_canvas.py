import os
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QApplication, QMessageBox, QGraphicsTextItem, QGraphicsSimpleTextItem, QGraphicsLineItem, QGraphicsRectItem
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QTimer, QLineF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPalette, QIcon, QFont
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QStyle
from application.commands.topology.topology_commands import AddDeviceCommand, CreateConnectionCommand
from domain.aggregates.topology.value_objects.connection_type import ConnectionTypeEnum

# 导入领域层值对象和枚举
from domain.aggregates.topology.value_objects.position import Position
from domain.aggregates.topology.value_objects.device_type import DeviceTypeEnum, DeviceType
from domain.aggregates.topology.value_objects.topology_id import TopologyId
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties

# 导入AddDeviceCommand的所有依赖
from domain.aggregates.topology.value_objects.topology_status import TopologyStatusEnum
from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.entities.node import Node
from domain.aggregates.topology.entities.switch import Switch
from domain.aggregates.topology.entities.transformer import Transformer
from domain.aggregates.topology.entities.line import Line
from domain.aggregates.topology.entities.connection import Connection
from domain.aggregates.topology.entities.microgrid_topology import MicrogridTopology
from domain.aggregates.topology.services.topology_connection_rules_service import TopologyConnectionRulesService
from domain.aggregates.topology.exceptions import InvalidTopologyException

# 导入设备类型到中文名称的映射
DEVICE_TYPE_TO_NAME = {
    "bus": "母线",
    "line": "线路",
    "transformer": "变压器",
    "switch": "开关",
    "static_generator": "光伏",
    "storage": "储能",
    "load": "负载",
    "charger": "充电桩",
    "meter": "电表",
    "external_grid": "外部电网"
}

class DeviceItem(QGraphicsItem):
    """设备图形项基类"""
    
    # 类级别的资源目录路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(current_dir, "..", "assets")
    
    # 中文设备名称到英文设备类型的映射
    chinese_to_device_type = {
        "母线": "bus",
        "线路": "line",
        "变压器": "transformer",
        "开关": "switch",
        "光伏": "static_generator",
        "储能": "storage",
        "负载": "load",
        "充电桩": "charger",
        "电表": "meter",
        "外部电网": "external_grid",
        "发电机": "generator"
    }
    
    # 设备类型到SVG文件映射
    device_svg_map = {
        "bus": "bus.svg",
        "line": "line.svg",
        "transformer": "transformer.svg",
        "switch": "switch.svg",
        "static_generator": "static_generator.svg",
        "storage": "storage.svg",
        "load": "load.svg",
        "charger": "charger.svg",
        "meter": "meter.svg",
        "external_grid": "external_grid.svg",
        "generator": "generator.svg"
    }
    
    def __init__(self, device_type, pos, device_id):
        super().__init__()
        
        # 记录设备类型
        self.device_type = device_type
        
        # 设备名称为类型+id格式
        self.device_name = f"{device_type}{device_id}"
        
        self.device_id = device_id
        self.setPos(pos)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        
        # 创建SVG渲染器
        svg_file = self.device_svg_map.get(self.device_type, "default.svg")
        svg_path = os.path.join(self.assets_dir, svg_file)
        self.svg_renderer = QSvgRenderer(svg_path) if os.path.exists(svg_path) else None
        
        # 网格间距
        self.grid_spacing = 50
        
        self.info_label = QGraphicsSimpleTextItem("", self)
        font = QFont("Arial", 9)
        self.info_label.setFont(font)
        self.info_label.setPos(40, -20)
        self.info_label.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
    
    def set_device_label(self):
        """设置设备标签文本"""
        # 获取中文名称
        chinese_name = DEVICE_TYPE_TO_NAME.get(self.device_type, self.device_type)
        # 设置标签文本：名称 + ID
        self.info_label.setText(f"{chinese_name}#{self.device_id}")
    
    def boundingRect(self):
        """返回边界矩形，只包含设备图标本身，优化重绘性能"""
        return QRectF(-32, -32, 64, 64)
    
    def paint(self, painter, option, widget):
        """绘制设备图形项"""
        if self.svg_renderer and self.svg_renderer.isValid():
            # 绘制SVG图标
            rect = QRectF(-32, -32, 64, 64)
            self.svg_renderer.render(painter, rect)
            
            # 如果选中，绘制选中框
            if option.state & QStyle.State_Selected:
                pen = QPen(QColor(0, 0, 255), 2)  # 蓝色
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(QRectF(-32, -32, 64, 64))
    
    def itemChange(self, change, value):
        """处理项目属性变化"""
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # 网格吸附
            x = round(value.x() / self.grid_spacing) * self.grid_spacing
            y = round(value.y() / self.grid_spacing) * self.grid_spacing
            return QPointF(x, y)
        elif change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            views = self.scene().views()
            if views:
                view = views[0]
                if hasattr(view, "update_connections_for_device"):
                    view.update_connections_for_device(self)
        return super().itemChange(change, value)

    def get_connection_points(self):
        """获取所有连接点（场景坐标）列表"""
        points = []
        # 线路和变压器使用两个端点作为连接点
        if self.device_type in ["line", "transformer"]:
            # 上下两个点
            points.append({"index": 0, "pos": self.mapToScene(0, -28)})
            points.append({"index": 1, "pos": self.mapToScene(0, 28)})
        # 上方连接点的设备
        elif self.device_type in ["static_generator", "load"]:
             points.append({"index": 0, "pos": self.mapToScene(0, -28)})
        elif self.device_type in ["storage", "meter"]:
             points.append({"index": 0, "pos": self.mapToScene(0, -24)})
        elif self.device_type == "charger":
             points.append({"index": 0, "pos": self.mapToScene(0, -29)})
        # 下方连接点的设备
        elif self.device_type == "external_grid":
             points.append({"index": 0, "pos": self.mapToScene(0, 28)})
        # 左右连接点的设备
        elif self.device_type == "switch":
             points.append({"index": 0, "pos": self.mapToScene(-28, 0)})
             points.append({"index": 1, "pos": self.mapToScene(28, 0)})
        else:
            # 其他设备默认使用中心点
            points.append({"index": 0, "pos": self.mapToScene(0, 0)})
        return points

    def get_connection_point_by_index(self, index):
        """根据索引获取连接点（场景坐标）"""
        if self.device_type in ["line", "transformer"]:
            if index == 0:
                return self.mapToScene(0, -28)
            elif index == 1:
                return self.mapToScene(0, 28)
        
        # 左右连接点的设备
        elif self.device_type == "switch":
            if index == 0:
                return self.mapToScene(-28, 0)
            elif index == 1:
                return self.mapToScene(28, 0)
        
        # 上方连接点的设备
        elif self.device_type in ["static_generator", "load"]:
            return self.mapToScene(0, -28)
        elif self.device_type in ["storage", "meter"]:
            return self.mapToScene(0, -24)
        elif self.device_type == "charger":
            return self.mapToScene(0, -29)
        # 下方连接点的设备
        elif self.device_type == "external_grid":
            return self.mapToScene(0, 28)

        return self.mapToScene(0, 0)

    def get_connection_point(self):
        """获取默认连接点（兼容旧代码）"""
        return self.get_connection_point_by_index(0)


class CustomTopologyCanvas(QGraphicsView):
    """基于QGraphicsView的自定义拓扑画布"""
    
    # 信号：设备选中时发出
    device_selected = Signal(object)
    # 信号：取消选择时发出
    selection_cleared = Signal()
    
    def __init__(self, application):
        super().__init__()
        
        self.application = application
        
        # 初始化场景
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(0, 0, 2000, 2000))  # 设置场景大小
        self.setScene(self.scene)
        
        # 设置视图属性
        self.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)  # 智能视图更新
        self.setDragMode(QGraphicsView.RubberBandDrag)  # 框选模式
        
        # 设置背景
        self.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
        self.scene.setBackgroundBrush(QBrush(QColor(240, 240, 240)))
        
        # 启用拖拽接收
        self.setAcceptDrops(True)
        
        # 存储画布上的设备
        self.devices = []
        
        # 设备ID计数器，从1开始
        self.device_id_counter = 1
        
        # 连接选择变化信号
        self.scene.selectionChanged.connect(self._on_selection_changed)
        
        # 绘制网格
        self._draw_grid()

        self._warm_text_rendering()
        
        # 当前拓扑ID
        self.current_topology_id = "default_topology"
        
        # 初始化默认拓扑
        QTimer.singleShot(100, self._init_topology)

        # 连接功能相关状态
        self.is_connecting = False
        self.temp_connection_line = None
        self.snapped_device = None  # 当前吸附的设备
        self.start_device = None    # 连接起始设备
        
        self._init_overlay_items()

        # 启用鼠标追踪，以便在不按键时也能捕获移动事件
        self.setMouseTracking(True)
        
        # 可视化连接记录
        self.connections = []
        
        # 捕获提示已由 _init_overlay_items 初始化
        pass
    
    def _init_overlay_items(self):
        self.snap_indicator = QGraphicsRectItem(-5, -5, 10, 10)
        self.snap_indicator.setPen(QPen(QColor(255, 0, 0), 2))
        self.snap_indicator.setBrush(Qt.NoBrush)
        self.snap_indicator.setZValue(100)
        self.snap_indicator.hide()
        self.scene.addItem(self.snap_indicator)
        self.snap_hint_text = QGraphicsSimpleTextItem("")
        self.snap_hint_text.setZValue(100)
        self.snap_hint_text.hide()
        self.scene.addItem(self.snap_hint_text)
    
    def _reset_scene(self):
        self.scene.clear()
        self.devices.clear()
        self.connections.clear()
        self._draw_grid()
        self._init_overlay_items()
    
    def _draw_grid(self):
        """绘制网格背景"""
        # 设置网格线颜色和样式
        grid_color = QColor(220, 220, 220)
        grid_pen = QPen(grid_color)
        grid_pen.setWidth(1)
        
        # 绘制水平线
        for y in range(0, 2000, 50):
            line = self.scene.addLine(0, y, 2000, y, grid_pen)
            line.setZValue(-1)  # 设置网格线在背景层
        
        # 绘制垂直线
        for x in range(0, 2000, 50):
            line = self.scene.addLine(x, 0, x, 2000, grid_pen)
            line.setZValue(-1)  # 设置网格线在背景层

    def _warm_text_rendering(self):
        """预热字体与文本渲染，减少首次标签创建延迟"""
        dummy = QGraphicsSimpleTextItem("预热")
        dummy.setFont(QFont("Arial", 9))
        dummy.setOpacity(0.0)
        dummy.setPos(0, 0)
        self.scene.addItem(dummy)
        QTimer.singleShot(0, lambda: self.scene.removeItem(dummy))
    
    def _init_topology(self):
        """初始化拓扑实体"""
        from application.commands.topology.topology_commands import CreateTopologyCommand
        from domain.aggregates.topology.value_objects.topology_id import TopologyId
        from domain.aggregates.topology.value_objects.topology_status import TopologyStatusEnum
        
        # 创建拓扑命令
        create_command = CreateTopologyCommand(
            name="默认拓扑",
            description="画布默认创建的拓扑",
            status=TopologyStatusEnum.CREATED,
            topology_id=TopologyId("default_topology")
        )
        
        # 执行拓扑创建命令
        self.application.topology_creation_use_case.create_topology(create_command)
    
    def _get_closest_connection_point(self, scene_pos: QPointF, threshold: float = 20.0):
        """获取最近的连接点"""
        closest_device = None
        closest_point = None
        closest_index = -1
        min_dist = float('inf')
        
        for device in self.devices:
            # 如果正在连接，跳过起始设备
            if self.is_connecting and device == self.start_device:
                continue
                
            # 遍历设备的所有连接点
            for p_info in device.get_connection_points():
                point = p_info["pos"]
                # 计算距离
                dist = QLineF(scene_pos, point).length()
                
                if dist < threshold and dist < min_dist:
                    min_dist = dist
                    closest_device = device
                    closest_point = point
                    closest_index = p_info["index"]
                
        return closest_device, closest_point, closest_index

    def _can_connect(self, source: DeviceItem, target: DeviceItem, source_index=0, target_index=0) -> bool:
        """检查两个设备是否可以连接"""
        if not source or not target:
            return False
        try:
            return self._precheck_with_rules_service(source, target, source_index, target_index)
        except Exception:
            return False

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        scene_pos = self.mapToScene(event.pos())
        
        if self.is_connecting:
            # 更新临时连接线
            if self.temp_connection_line:
                line = self.temp_connection_line.line()
                line.setP2(scene_pos)
                self.temp_connection_line.setLine(line)
            
            # 检查吸附
            device, point, index = self._get_closest_connection_point(scene_pos)
            if device and point:
                # 吸附到连接点
                self.snap_indicator.setPos(point)
                self.snap_indicator.show()
                self.snapped_device = device
                self.snapped_device_point_index = index
                
                # 如果吸附，将线终点设为吸附点
                line = self.temp_connection_line.line()
                line.setP2(point)
                self.temp_connection_line.setLine(line)
            else:
                self.snap_indicator.hide()
                self.snapped_device = None
                self.snapped_device_point_index = 0
                
        else:
            # 正常模式下检查是否有吸附点
            device, point, index = self._get_closest_connection_point(scene_pos)
            if device and point:
                self.snap_indicator.setPos(point)
                self.snap_indicator.show()
                self.snapped_device = device
                self.snapped_device_point_index = index
                self.snap_hint_text.setText("左键点击,长按拖动开始连接")
                self.snap_hint_text.setPos(point + QPointF(-60, 24))
                self.snap_hint_text.show()
            else:
                self.snap_indicator.hide()
                self.snapped_device = None
                self.snapped_device_point_index = 0
                self.snap_hint_text.hide()
                
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            if self.snapped_device and not self.is_connecting:
                # 开始连接
                self.is_connecting = True
                self.start_device = self.snapped_device
                self.start_device_point_index = getattr(self, 'snapped_device_point_index', 0)
                start_point = self.start_device.get_connection_point_by_index(self.start_device_point_index)
                
                # 创建临时连接线
                self.temp_connection_line = QGraphicsLineItem(QLineF(start_point, start_point))
                pen = QPen(Qt.black, 2, Qt.DashLine)
                self.temp_connection_line.setPen(pen)
                self.scene.addItem(self.temp_connection_line)
                
                # 消费事件，阻止默认行为（如选择/拖拽设备）
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        if self.is_connecting and event.button() == Qt.LeftButton:
            # 结束连接
            if self.snapped_device and self.snapped_device != self.start_device:
                # 检查是否允许连接
                if self._can_connect(self.start_device, self.snapped_device, getattr(self, 'start_device_point_index', 0), getattr(self, 'snapped_device_point_index', 0)):
                    # 创建连接
                    self._create_connection(
                        self.start_device, 
                        self.snapped_device,
                        getattr(self, 'start_device_point_index', 0),
                        getattr(self, 'snapped_device_point_index', 0)
                    )
                else:
                    QMessageBox.warning(self, "无法连接", "连接不合法，已根据连接规则拒绝")
            
            # 清理状态
            self.is_connecting = False
            self.start_device = None
            self.snapped_device = None
            if self.temp_connection_line:
                self.scene.removeItem(self.temp_connection_line)
                self.temp_connection_line = None
            self.snap_indicator.hide()
            
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _create_connection(self, source: DeviceItem, target: DeviceItem, source_index=0, target_index=0):
        """创建连接"""
        try:
            # 创建连接命令
            command = CreateConnectionCommand(
                topology_id=TopologyId(self.current_topology_id),
                source_device_id=source.device_id,
                target_device_id=target.device_id,
                connection_type=ConnectionTypeEnum.BIDIRECTIONAL, # 默认为双向
                properties={"source_port": source_index, "target_port": target_index}
            )
            
            # 执行命令
            connection_id = None
            if hasattr(self.application, "topology_connection_management_use_case"):
                 result = self.application.topology_connection_management_use_case.create_connection(command)
                 try:
                     connection_id = getattr(result, "connection_id", None)
                 except Exception:
                     connection_id = None
            
            # 视觉上添加连接线 (实际应用中可能应该由领域事件触发刷新，但这里先简单处理)
            self._add_visual_connection(source, target, source_index, target_index, connection_id)
            
            if hasattr(self.application, "topology_undo_redo_use_case"):
                data = self.get_topology_data()
                self.application.topology_undo_redo_use_case.snapshot(data)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建连接失败: {str(e)}")

    def _precheck_with_rules_service(self, source: DeviceItem, target: DeviceItem, source_index=0, target_index=0) -> bool:
        topo = MicrogridTopology(TopologyId("precheck"), "Precheck")
        dev_map = {}
        for item in self.devices:
            t = item.device_type
            props = DeviceProperties({})
            if t == "bus":
                d = Node(item.device_id, props)
            elif t == "line":
                d = Line(item.device_id, props)
            elif t == "transformer":
                d = Transformer(item.device_id, props)
            elif t == "switch":
                d = Switch(item.device_id, props)
            else:
                d = Device(item.device_id, DeviceType(getattr(DeviceTypeEnum, t.upper(), DeviceTypeEnum.NODE)), props)
            dev_map[item.device_id] = d
            topo.add_device(d)
        for c in self.connections:
            conn = Connection(
                connection_id=f"pre-{c['source'].device_id}-{c['target'].device_id}-{c.get('source_index',0)}-{c.get('target_index',0)}",
                source_device_id=c["source"].device_id,
                target_device_id=c["target"].device_id,
                connection_type=ConnectionTypeEnum.BIDIRECTIONAL,
                properties={"source_port": c.get("source_index", 0), "target_port": c.get("target_index", 0)}
            )
            topo.add_connection(conn)
        src_d = dev_map.get(source.device_id)
        tgt_d = dev_map.get(target.device_id)
        candidate = Connection(
            connection_id=f"pre-{source.device_id}-{target.device_id}",
            source_device_id=source.device_id,
            target_device_id=target.device_id,
            connection_type=ConnectionTypeEnum.BIDIRECTIONAL,
            properties={"source_port": source_index, "target_port": target_index}
        )
        try:
            TopologyConnectionRulesService().enforce_and_apply(topo, candidate, src_d, tgt_d)
            return True
        except InvalidTopologyException:
            return False

    def _add_visual_connection(self, source: DeviceItem, target: DeviceItem, source_index=0, target_index=0, connection_id=None):
        """添加可视化的连接线"""
        p1 = source.get_connection_point_by_index(source_index)
        p2 = target.get_connection_point_by_index(target_index)
        line = QGraphicsLineItem(QLineF(p1, p2))
        line.setPen(QPen(Qt.black, 2))
        line.setZValue(-1) # 在设备下方
        line.setFlag(QGraphicsItem.ItemIsSelectable)
        self.scene.addItem(line)
        
        # 简单记录连接线，以便后续管理（这里只是简单实现）
        # 实际项目中应该有ConnectionItem类，并管理其生命周期
        self.connections.append({
            "line": line,
            "source": source,
            "target": target,
            "source_index": source_index,
            "target_index": target_index,
            "connection_id": connection_id
        })

    def update_connections_for_device(self, device: DeviceItem):
        """当设备移动时更新相关连接线"""
        for conn in self.connections:
            if conn["source"] == device or conn["target"] == device:
                p1 = conn["source"].get_connection_point_by_index(conn.get("source_index", 0))
                p2 = conn["target"].get_connection_point_by_index(conn.get("target_index", 0))
                conn["line"].setLine(QLineF(p1, p2))
    
    def _remove_connection_entry(self, conn):
        try:
            connection_id = conn.get("connection_id")
            if connection_id and hasattr(self.application, "topology_connection_management_use_case"):
                from application.commands.topology.topology_commands import RemoveConnectionCommand
                self.application.topology_connection_management_use_case.remove_connection(
                    RemoveConnectionCommand(
                        topology_id=TopologyId(self.current_topology_id),
                        connection_id=connection_id
                    )
                )
        except Exception:
            pass
        try:
            self.scene.removeItem(conn["line"])
        except Exception:
            pass
        try:
            self.connections.remove(conn)
        except Exception:
            pass
    
    def _remove_connection_by_line(self, line_item):
        for conn in list(self.connections):
            if conn.get("line") == line_item:
                self._remove_connection_entry(conn)
                break
    
    def _remove_connections_for_device(self, device_item):
        to_remove = [c for c in self.connections if c.get("source") == device_item or c.get("target") == device_item]
        for conn in to_remove:
            self._remove_connection_entry(conn)

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        # 检查拖拽的数据类型
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """处理拖拽移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """处理拖拽放置事件"""
        import time
        
        # 获取拖拽的设备类型
        device_type = event.mimeData().text()
        
        # 记录开始时间（释放鼠标按键的时间，此时开始处理放置事件）
        drop_start_time = time.time()
        
        # 获取拖拽位置（转换为场景坐标）
        pos = self.mapToScene(event.pos())
        
        # 处理设备放置逻辑
        self._add_device(device_type, pos)
        
        event.acceptProposedAction()
        
        # 记录总时间（从释放鼠标到处理完成的总时间）
        drop_end_time = time.time()
        total_time = drop_end_time - drop_start_time
    
    def _add_device(self, device_type: str, pos: QPointF) -> DeviceItem:
        """添加设备到画布"""
        # 网格间隔，与_draw_grid方法保持一致
        grid_spacing = 50
        
        # 自动吸附到网格线交点
        snapped_pos = QPointF(
            round(pos.x() / grid_spacing) * grid_spacing,
            round(pos.y() / grid_spacing) * grid_spacing
        )
        
        # 调用应用层创建设备
        try:
            # 转换设备类型枚举
            device_type_enum = getattr(DeviceTypeEnum, device_type.upper(), None)
            if not device_type_enum:
                 # 尝试映射中文名称
                 for name, type_str in DeviceItem.chinese_to_device_type.items():
                     if type_str == device_type:
                         device_type_enum = getattr(DeviceTypeEnum, type_str.upper(), None)
                         break
            
            if not device_type_enum:
                # 默认回退
                device_type_enum = DeviceTypeEnum.NODE
                
            # 创建添加设备命令
            command = AddDeviceCommand(
                topology_id=TopologyId(self.current_topology_id),
                device_type=device_type_enum,
                name=f"{device_type}_{len(self.devices)+1}",
                position=Position(x=snapped_pos.x(), y=snapped_pos.y()),
                properties=DeviceProperties({})
            )
            
            # 执行命令
            result = self.application.topology_device_management_use_case.add_device(command)
            
            # 使用领域层返回的ID
            device_id = result.device_id
            
        except Exception as e:
            print(f"Error adding device: {e}")
            QMessageBox.warning(self, "添加设备失败", f"无法添加设备: {str(e)}")
            # 降级处理：使用本地计数器（仅用于UI显示，防止崩溃）
            device_id = str(self.device_id_counter)
            self.device_id_counter += 1
        
        # 创建设备图形项
        device_item = DeviceItem(device_type, snapped_pos, device_id)
        
        # 先添加到场景，后设置标签（避免阻塞显示）
        self.scene.addItem(device_item)
        
        # 同步设置设备标签，避免首次拖放延迟
        device_item.set_device_label()
        
        # 存储设备
        self.devices.append(device_item)
        
        # 不再发射未使用的信号
        # self.device_added.emit(device_type, snapped_pos)
        
        if hasattr(self.application, "topology_undo_redo_use_case"):
            data = self.get_topology_data()
            self.application.topology_undo_redo_use_case.snapshot(data)
        
        return device_item
    
    def wheelEvent(self, event):
        """处理鼠标滚轮事件（缩放）"""
        # 获取缩放因子
        zoom_factor = 1.15
        
        if event.angleDelta().y() > 0:
            # 放大
            self.scale(zoom_factor, zoom_factor)
        else:
            # 缩小
            self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)
    
    def contextMenuEvent(self, event):
        """处理右键菜单事件"""
        # 创建右键菜单
        menu = QMenu(self)
        
        # 检查是否有选中的设备
        selected_items = self.scene.selectedItems()
        has_selection = len(selected_items) > 0
        
        if has_selection:
            # 选中设备相关操作
            selected_devices = [i for i in selected_items if isinstance(i, DeviceItem)]
            selected_conn_lines = [i for i in selected_items if isinstance(i, QGraphicsLineItem) and any(c["line"] == i for c in self.connections)]
            delete_action = None
            delete_conn_action = None
            if selected_devices:
                delete_action = menu.addAction("删除所选设备")
            if selected_conn_lines:
                delete_conn_action = menu.addAction("删除所选连接")
            menu.addSeparator()
        
        # 画布操作
        zoom_in_action = menu.addAction("放大")
        zoom_out_action = menu.addAction("缩小")
        zoom_fit_action = menu.addAction("适应视图")
        clear_action = menu.addAction("清空所有设备")
        
        # 显示菜单并获取选择的动作
        action = menu.exec_(self.mapToGlobal(event.pos()))
        
        # 处理菜单动作
        if has_selection and delete_action and action == delete_action:
            # 删除所选设备
            from application.commands.topology.topology_commands import RemoveDeviceCommand
            from domain.aggregates.topology.value_objects.topology_id import TopologyId
            
            for item in selected_items:
                if not isinstance(item, DeviceItem):
                    continue
                # 调用应用层的设备删除命令
                command = RemoveDeviceCommand(
                    topology_id=TopologyId(self.current_topology_id),
                    device_id=item.device_id
                )
                
                # 执行删除命令（会回收设备ID）
                try:
                    self.application.topology_device_management_use_case.remove_device(command)
                except Exception as e:
                    pass
                
                self._remove_connections_for_device(item)
                # 从图形界面移除设备项
                self.scene.removeItem(item)
                if item in self.devices:
                    self.devices.remove(item)
        elif has_selection and 'delete_conn_action' in locals() and delete_conn_action and action == delete_conn_action:
            for line_item in selected_conn_lines:
                self._remove_connection_by_line(line_item)
            if hasattr(self.application, "topology_undo_redo_use_case"):
                data = self.get_topology_data()
                self.application.topology_undo_redo_use_case.snapshot(data)
        elif action == zoom_in_action:
            self.scale(1.15, 1.15)
        elif action == zoom_out_action:
            self.scale(1.0 / 1.15, 1.0 / 1.15)
        elif action == zoom_fit_action:
            self._fit_in_view()
        elif action == clear_action:
            # 清空画布
            self._reset_scene()

            if hasattr(self.application, "topology_undo_redo_use_case"):
                data = self.get_topology_data()
                self.application.topology_undo_redo_use_case.snapshot(data)
    
    def _fit_in_view(self):
        """适应视图，根据已使用的画布面积自动调整视图范围"""
        # 获取所有设备图形项
        device_items = [item for item in self.scene.items() if isinstance(item, DeviceItem)]
        
        if not device_items:
            # 如果没有设备，重置到默认视图
            self.resetTransform()
            return
        
        # 计算所有设备的边界矩形
        rect = device_items[0].sceneBoundingRect()
        for item in device_items[1:]:
            rect = rect.united(item.sceneBoundingRect())
        
        # 添加边距以获得更好的视觉效果
        margin = max(rect.width(), rect.height()) * 0.1
        rect.adjust(-margin, -margin, margin, margin)
        
        # 适应视图，保持宽高比
        self.fitInView(rect, Qt.KeepAspectRatio)
    
    def _on_selection_changed(self):
        """处理选择变化事件"""
        selected_items = self.scene.selectedItems()
        # 过滤出DeviceItem类型的选中项
        selected_devices = [item for item in selected_items if isinstance(item, DeviceItem)]
        
        if selected_devices:
            # 只发送第一个选中的设备
            self.device_selected.emit(selected_devices[0])
        else:
            # 取消选择
            self.selection_cleared.emit()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 获取选中的设备
        selected_items = self.scene.selectedItems()
        
        if selected_items:
            # 处理删除键
            if event.key() == Qt.Key_Delete:
                # 删除所选设备
                from application.commands.topology.topology_commands import RemoveDeviceCommand
                from domain.aggregates.topology.value_objects.topology_id import TopologyId
                
                for item in list(selected_items):
                    if isinstance(item, DeviceItem):
                        command = RemoveDeviceCommand(
                            topology_id=TopologyId(self.current_topology_id),
                            device_id=item.device_id
                        )
                        try:
                            self.application.topology_device_management_use_case.remove_device(command)
                        except Exception as e:
                            pass
                        self._remove_connections_for_device(item)
                        self.scene.removeItem(item)
                        if item in self.devices:
                            self.devices.remove(item)
                    elif isinstance(item, QGraphicsLineItem):
                        if any(c["line"] == item for c in self.connections):
                            self._remove_connection_by_line(item)
            if hasattr(self.application, "topology_undo_redo_use_case"):
                data = self.get_topology_data()
                self.application.topology_undo_redo_use_case.snapshot(data)
            if hasattr(self.application, "topology_undo_redo_use_case"):
                data = self.get_topology_data()
                self.application.topology_undo_redo_use_case.snapshot(data)
        
        # 处理其他按键
        super().keyPressEvent(event)

    def get_topology_data(self) -> dict:
        devices_data = []
        for item in self.devices:
            devices_data.append({
                "type": item.device_type,
                "id": item.device_id,
                "x": item.pos().x(),
                "y": item.pos().y()
            })
        return {"devices": devices_data}

    def render_topology(self, devices_data: list) -> None:
        """根据设备数据渲染拓扑，不触发后端命令"""
        self._reset_scene()
        
        max_id_num = 0
        
        for d in devices_data:
            # 数据格式: {"type": "bus", "id": "node-1", "x": 100, "y": 200}
            device_type = d.get("type", "bus")
            device_id = d.get("id") # 这里可能是字符串或数字
            x = float(d.get("x", 0))
            y = float(d.get("y", 0))
            pos = QPointF(x, y)
            
            # 创建设备图形项
            device_item = DeviceItem(device_type, pos, device_id)
            self.scene.addItem(device_item)
            device_item.set_device_label()
            self.devices.append(device_item)
            
            # 尝试更新计数器 (如果是数字ID)
            try:
                # 如果ID是纯数字，或者以数字结尾
                if isinstance(device_id, int):
                    max_id_num = max(max_id_num, device_id)
                elif isinstance(device_id, str) and device_id.isdigit():
                    max_id_num = max(max_id_num, int(device_id))
            except:
                pass
                
        self.device_id_counter = max_id_num + 1

    def load_topology_data(self, data: dict) -> None:
        self._reset_scene()
        items = data.get("devices", [])
        max_id = 0
        for d in items:
            pos = QPointF(float(d.get("x", 0)), float(d.get("y", 0)))
            di = self._add_device(str(d.get("type", "bus")), pos)
            try:
                di.device_id = int(d.get("id", di.device_id))
            except Exception:
                pass
            di.set_device_label()
            max_id = max(max_id, di.device_id)
        self.device_id_counter = max(self.device_id_counter, max_id + 1)
