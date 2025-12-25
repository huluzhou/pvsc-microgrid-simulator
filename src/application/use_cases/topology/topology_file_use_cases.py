import json
from typing import Any, Dict, List, Optional
from domain.aggregates.topology.entities.microgrid_topology import MicrogridTopology
from domain.aggregates.topology.entities.node import Node
from domain.aggregates.topology.entities.line import Line
from domain.aggregates.topology.entities.switch import Switch
from domain.aggregates.topology.entities.transformer import Transformer
from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.entities.connection import Connection
from domain.aggregates.topology.value_objects.device_type import DeviceType, DeviceTypeEnum
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
from domain.aggregates.topology.value_objects.topology_id import TopologyId
from domain.aggregates.topology.value_objects.position import Position
from domain.aggregates.topology.value_objects.location import Location
from domain.aggregates.topology.value_objects.connection_type import ConnectionType, ConnectionTypeEnum
from domain.aggregates.topology.value_objects.device_id import DeviceId


class TopologyFileUseCase:
    def __init__(self, topology_repository=None):
        from infrastructure.third_party.di.services import InMemoryTopologyRepository
        self._topology_repository = topology_repository or InMemoryTopologyRepository()

    def open(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"devices": []}

    def save(self, file_path: str, data: Dict[str, Any]) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def import_json(self, file_path: str) -> Dict[str, Any]:
        return self.open(file_path)

    def export_json(self, file_path: str, data: Dict[str, Any]) -> bool:
        return self.save(file_path, data)

    def load_topology(self, file_path: str) -> MicrogridTopology:
        """从文件加载拓扑并转换为领域实体"""
        data = self.open(file_path)
        topology = self._parse_json_to_topology(data)
        # 保存到仓储，确保持久化，以便后续操作基于此拓扑
        self._topology_repository.save(topology)
        return topology

    def save_topology(self, file_path: str, topology: MicrogridTopology) -> bool:
        """保存拓扑实体到文件"""
        data = self._serialize_topology_to_json(topology)
        return self.save(file_path, data)

    def save_topology_by_id(self, file_path: str, topology_id: str) -> bool:
        """根据ID保存拓扑到文件"""
        topology = self._topology_repository.get(topology_id)
        if not topology:
            return False
        return self.save_topology(file_path, topology)

    def topology_to_canvas_data(self, topology: MicrogridTopology) -> Dict[str, Any]:
        """将拓扑实体转换为画布所需的数据格式"""
        devices_data = []
        for device in topology.devices:
            # 提取数字ID
            try:
                # 尝试从ID字符串中提取数字，假设格式为 "type-id" 或纯数字
                dev_id_str = str(device.id)
                if "-" in dev_id_str:
                    dev_id = int(dev_id_str.split("-")[-1])
                else:
                    dev_id = int(dev_id_str)
            except ValueError:
                # 如果无法提取，使用哈希或其他方式，或者默认0
                dev_id = 0
            
            # 获取类型字符串 (小写)
            dev_type = device.device_type.type.name.lower()
            
            devices_data.append({
                "type": dev_type,
                "id": dev_id,
                "x": device.position.x if device.position else 0.0,
                "y": device.position.y if device.position else 0.0
            })
        return {"devices": devices_data}

    def _parse_json_to_topology(self, data: Dict[str, Any]) -> MicrogridTopology:
        """解析JSON数据为拓扑实体"""
        topology_id = TopologyId("imported_topology")
        topology = MicrogridTopology(topology_id, "Imported Topology", "Imported from JSON")
        
        # 临时存储Bus名称/ID到设备ID的映射，用于建立连接
        # 格式: {bus_name_or_index: device_id}
        bus_map = {}
        
        # 1. 解析 Bus (Nodes)
        buses = data.get("Bus", [])
        for bus_data in buses:
            name = bus_data.get("name", "bus")
            index = bus_data.get("index", "0")
            vn_kv = bus_data.get("vn_kv", 0.0)
            
            # 尝试获取位置信息 (如果存在)
            geodata = bus_data.get("geodata", [0.0, 0.0])
            x, y = geodata[0], geodata[1] if len(geodata) >= 2 else (0.0, 0.0)
            
            device_id_str = f"node-{index}"
            properties = DeviceProperties({
                "vn_kv": vn_kv, 
                "name": name, 
                "index": index
            })
            
            node = Node(
                device_id=device_id_str,
                properties=properties,
                location=Location(0.0, 0.0), # 默认经纬度
                position=Position(x, y)
            )
            
            topology.add_device(node)
            
            # 记录映射
            bus_map[name] = device_id_str
            bus_map[str(index)] = device_id_str
            # 也支持通过vn_kv或其他标识查找? 暂时只用name和index
        
        # 辅助函数：创建连接
        def create_connection(source_id, target_id, conn_type=ConnectionTypeEnum.BIDIRECTIONAL):
            if not source_id or not target_id:
                return
            conn_id = f"conn-{source_id}-{target_id}"
            connection = Connection(
                connection_id=conn_id,
                source_device_id=source_id,
                target_device_id=target_id,
                connection_type=ConnectionType(conn_type)
            )
            topology.add_connection(connection)

        # 辅助函数：查找Bus ID
        def get_bus_id(bus_ref):
            return bus_map.get(str(bus_ref))

        # 2. 解析其他设备
        
        # Line
        lines = data.get("Line", [])
        for item in lines:
            index = item.get("index", "0")
            name = item.get("name", f"line-{index}")
            from_bus = item.get("from_bus")
            to_bus = item.get("to_bus")
            
            # Line位置通常在两个Bus之间，或者由geodata定义
            # 这里简单取中点或默认0
            x, y = 0.0, 0.0 
            
            device_id = f"line-{index}"
            properties = DeviceProperties(item)
            
            line = Line(
                device_id=device_id,
                properties=properties,
                location=Location(0.0, 0.0),
                position=Position(x, y)
            )
            topology.add_device(line)
            
            # 创建连接: from_bus -> line -> to_bus
            from_bus_id = get_bus_id(from_bus)
            to_bus_id = get_bus_id(to_bus)
            
            if from_bus_id:
                create_connection(from_bus_id, device_id)
            if to_bus_id:
                create_connection(device_id, to_bus_id)

        # Transformer
        trafos = data.get("Transformer", [])
        for item in trafos:
            index = item.get("index", "0")
            hv_bus = item.get("hv_bus")
            lv_bus = item.get("lv_bus")
            
            device_id = f"transformer-{index}"
            properties = DeviceProperties(item)
            
            trafo = Transformer(
                device_id=device_id,
                properties=properties,
                location=Location(0.0, 0.0),
                position=Position(0.0, 0.0)
            )
            topology.add_device(trafo)
            
            hv_bus_id = get_bus_id(hv_bus)
            lv_bus_id = get_bus_id(lv_bus)
            
            if hv_bus_id:
                create_connection(hv_bus_id, device_id)
            if lv_bus_id:
                create_connection(device_id, lv_bus_id)

        # Generic Devices (Load, Charger, Static Generator, Storage, External Grid)
        # 映射表: JSON Key -> (DeviceTypeEnum, ID Prefix)
        generic_map = {
            "Load": (DeviceTypeEnum.LOAD, "load"),
            "Charger": (DeviceTypeEnum.CHARGER, "charger"),
            "Static Generator": (DeviceTypeEnum.STATIC_GENERATOR, "static_generator"),
            "Storage": (DeviceTypeEnum.STORAGE, "storage"),
            "External Grid": (DeviceTypeEnum.EXTERNAL_GRID, "external_grid"),
            "Measurement": (DeviceTypeEnum.METER, "meter"),
            "Switch": (DeviceTypeEnum.SWITCH, "switch")
        }

        for json_key, (dtype_enum, prefix) in generic_map.items():
            items = data.get(json_key, [])
            for item in items:
                index = item.get("index", "0")
                if not index or index == "value": # 处理可能得默认值
                     import uuid
                     index = str(uuid.uuid4())[:8]
                     
                bus = item.get("bus")
                # 对于Switch, 可能是 closed 字段等
                # External Grid 也是 bus
                # Measurement 可能有 element, element_type
                
                device_id = f"{prefix}-{index}"
                properties = DeviceProperties(item)
                
                # 尝试获取位置
                geodata = item.get("geodata", [0.0, 0.0])
                x, y = geodata[0], geodata[1] if len(geodata) >= 2 else (0.0, 0.0)

                # 对于Switch，使用Switch实体
                if dtype_enum == DeviceTypeEnum.SWITCH:
                    device = Switch(
                        device_id=device_id,
                        properties=properties,
                        location=Location(0.0, 0.0),
                        position=Position(x, y)
                    )
                else:
                    device = Device(
                        device_id=device_id,
                        device_type=DeviceType(dtype_enum),
                        properties=properties,
                        location=Location(0.0, 0.0),
                        position=Position(x, y)
                    )
                
                topology.add_device(device)
                
                # 处理连接
                # 大多数单端设备连接到 'bus'
                if bus:
                    bus_id = get_bus_id(bus)
                    if bus_id:
                        create_connection(bus_id, device_id)
                
                # Measurement 特殊处理 (连接到 element)
                # 目前简单处理：如果 element 是 bus ID，则连接
                if dtype_enum == DeviceTypeEnum.METER:
                    element = item.get("element")
                    # TODO: 实现Meter连接逻辑，可能需要更复杂的查找
                    pass

        return topology

    def _serialize_topology_to_json(self, topology: MicrogridTopology) -> Dict[str, Any]:
        """将拓扑实体序列化为JSON格式"""
        data = {
            "Bus": [], "Line": [], "Load": [], "Charger": [], 
            "Static Generator": [], "External Grid": [], "Transformer": [], 
            "Measurement": [], "Storage": [], "Switch": []
        }
        
        # 辅助: 获取设备连接的Bus
        # 这需要遍历连接。为了简化，我们假设设备属性中保留了原始信息，或者通过连接反推
        # 反推比较复杂，这里先简单尝试从属性中获取 (如果导入时保留了)
        # 或者仅仅导出基本信息
        
        for device in topology.devices:
            props = device.properties.properties
            # 提取通用字段
            item = props.copy()
            item["index"] = str(device.id).split("-")[-1] if "-" in str(device.id) else str(device.id)
            if device.position:
                item["geodata"] = [device.position.x, device.position.y]
            
            dtype = device.device_type.type
            
            if dtype == DeviceTypeEnum.BUS or dtype == DeviceTypeEnum.NODE:
                data["Bus"].append(item)
            elif dtype == DeviceTypeEnum.LINE:
                data["Line"].append(item)
            elif dtype == DeviceTypeEnum.LOAD:
                data["Load"].append(item)
            elif dtype == DeviceTypeEnum.CHARGER:
                data["Charger"].append(item)
            elif dtype == DeviceTypeEnum.STATIC_GENERATOR:
                data["Static Generator"].append(item)
            elif dtype == DeviceTypeEnum.STORAGE:
                data["Storage"].append(item)
            elif dtype == DeviceTypeEnum.EXTERNAL_GRID:
                data["External Grid"].append(item)
            elif dtype == DeviceTypeEnum.TRANSFORMER:
                data["Transformer"].append(item)
            elif dtype == DeviceTypeEnum.METER:
                data["Measurement"].append(item)
            elif dtype == DeviceTypeEnum.SWITCH:
                data["Switch"].append(item)
                
        return data


class UndoRedoUseCase:
    def __init__(self) -> None:
        self._past: List[Dict[str, Any]] = []
        self._future: List[Dict[str, Any]] = []

    def snapshot(self, data: Dict[str, Any]) -> None:
        self._past.append(json.loads(json.dumps(data)))
        self._future.clear()

    def undo(self) -> Optional[Dict[str, Any]]:
        if len(self._past) <= 1:
            return self._past[-1] if self._past else None
        last = self._past.pop()
        self._future.append(last)
        return self._past[-1]

    def redo(self) -> Optional[Dict[str, Any]]:
        if not self._future:
            return self._past[-1] if self._past else None
        state = self._future.pop()
        self._past.append(state)
        return state
