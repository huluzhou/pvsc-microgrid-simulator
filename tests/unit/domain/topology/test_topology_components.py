import unittest
from domain.aggregates.topology.entities import (
    MicrogridTopology, Device, Node, Line, Transformer, Switch
)
from domain.aggregates.topology.value_objects import (
    TopologyId, DeviceType, DeviceTypeEnum, DeviceProperties,
    ConnectionType, ConnectionTypeEnum, Location, Position,
    TopologyStatus, TopologyStatusEnum
)
from domain.aggregates.topology.entities.connection import Connection
from domain.aggregates.topology.services import (
    TopologyValidationService, TopologyConnectivityService, TopologyOptimizationService
)
from domain.common.events.event_bus import InMemoryEventBus
from domain.aggregates.topology.exceptions import (
    InvalidTopologyException, DeviceNotFoundException, ConnectionException, TopologyValidationException
)

class TestTopologyComponents(unittest.TestCase):
    def setUp(self):
        self.event_bus = InMemoryEventBus()
        self.validation_service = TopologyValidationService(self.event_bus)
        self.connectivity_service = TopologyConnectivityService()
        self.optimization_service = TopologyOptimizationService()
        
        # 创建设备属性
        self.node_properties = DeviceProperties({"voltage_level": 400.0, "max_current": 100.0})
        self.line_properties = DeviceProperties({"resistance": 0.1, "reactance": 0.5, "capacitance": 0.01})
        self.transformer_properties = DeviceProperties({"primary_voltage": 10000.0, "secondary_voltage": 400.0, "power_rating": 500.0})
        self.switch_properties = DeviceProperties({"is_closed": True, "max_current": 200.0})
        
        # 创建位置和位置信息
        self.location = Location(39.9042, 116.4074, 50.0)
        self.position = Position(10.0, 20.0, 0.0)
    
    def test_create_topology(self):
        """测试创建拓扑"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑", "测试描述")
        
        self.assertEqual(str(topology.id), "topo-001")
        self.assertEqual(topology.name, "测试拓扑")
        self.assertEqual(topology.description, "测试描述")
        self.assertEqual(len(topology.devices), 0)
        self.assertEqual(len(topology.connections), 0)
        self.assertEqual(topology.status.status, TopologyStatusEnum.CREATED)
    
    def test_add_device(self):
        """测试添加设备"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        # 创建节点设备
        node = Node("node-001", self.node_properties, self.location, self.position)
        topology.add_device(node)
        
        self.assertEqual(len(topology.devices), 1)
        self.assertEqual(topology.devices[0].id, "node-001")
        self.assertEqual(topology.devices[0].device_type.type, DeviceTypeEnum.NODE)
    
    def test_add_duplicate_device(self):
        """测试添加重复设备"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        # 创建节点设备
        node = Node("node-001", self.node_properties, self.location, self.position)
        topology.add_device(node)
        
        # 再次添加相同ID的设备，应该抛出异常
        with self.assertRaises(InvalidTopologyException):
            topology.add_device(node)
    
    def test_remove_device(self):
        """测试删除设备"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        # 创建节点设备
        node = Node("node-001", self.node_properties, self.location, self.position)
        topology.add_device(node)
        
        # 删除设备
        topology.remove_device("node-001")
        
        self.assertEqual(len(topology.devices), 0)
    
    def test_remove_nonexistent_device(self):
        """测试删除不存在的设备"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        # 删除不存在的设备，应该抛出异常
        with self.assertRaises(DeviceNotFoundException):
            topology.remove_device("nonexistent-device")
    
    def test_add_connection(self):
        """测试添加连接"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        node1 = Node("node-001", self.node_properties, self.location, self.position)
        line1 = Line("line-001", self.line_properties, self.location, Position(30.0, 40.0, 0.0))
        topology.add_device(node1)
        topology.add_device(line1)
        connection = Connection(
            "conn-001",
            "node-001",
            "line-001",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        topology.add_connection(connection)
        self.assertEqual(len(topology.connections), 1)
        self.assertEqual(topology.connections[0].id, "conn-001")
        self.assertEqual(topology.connections[0].source_device_id, "node-001")
        self.assertEqual(topology.connections[0].target_device_id, "line-001")
    
    def test_add_invalid_connection(self):
        """测试添加无效连接"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        # 创建一个节点设备
        node = Node("node-001", self.node_properties, self.location, self.position)
        topology.add_device(node)
        
        # 创建连接到不存在的设备，应该抛出异常
        connection = Connection(
            "conn-001",
            "node-001",
            "nonexistent-device",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        
        with self.assertRaises(DeviceNotFoundException):
            topology.add_connection(connection)
    
    def test_validate_topology(self):
        """测试验证拓扑"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        node1 = Node("node-001", self.node_properties, self.location, self.position)
        node2 = Node("node-002", self.node_properties, self.location, Position(30.0, 40.0, 0.0))
        line1 = Line("line-001", self.line_properties, self.location, Position(20.0, 30.0, 0.0))
        topology.add_device(node1)
        topology.add_device(node2)
        topology.add_device(line1)
        c1 = Connection(
            "conn-001",
            "node-001",
            "line-001",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        c2 = Connection(
            "conn-002",
            "line-001",
            "node-002",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        topology.add_connection(c1)
        topology.add_connection(c2)
        
        # 验证拓扑
        validation_result = self.validation_service.validate(topology)
        
        self.assertTrue(validation_result["is_valid"])
        self.assertEqual(len(validation_result["errors"]), 0)
        self.assertTrue(validation_result["checks"]["valid_topology"])
    
    def test_check_connectivity(self):
        """测试检查连接性"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        node1 = Node("node-001", self.node_properties, self.location, self.position)
        node2 = Node("node-002", self.node_properties, self.location, Position(30.0, 40.0, 0.0))
        node3 = Node("node-003", self.node_properties, self.location, Position(50.0, 60.0, 0.0))
        line1 = Line("line-001", self.line_properties, self.location, Position(20.0, 30.0, 0.0))
        line2 = Line("line-002", self.line_properties, self.location, Position(40.0, 50.0, 0.0))
        topology.add_device(node1)
        topology.add_device(node2)
        topology.add_device(node3)
        topology.add_device(line1)
        topology.add_device(line2)
        c1 = Connection(
            "conn-001",
            "node-001",
            "line-001",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        c2 = Connection(
            "conn-002",
            "line-001",
            "node-002",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        c3 = Connection(
            "conn-003",
            "node-002",
            "line-002",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        c4 = Connection(
            "conn-004",
            "line-002",
            "node-003",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        topology.add_connection(c1)
        topology.add_connection(c2)
        topology.add_connection(c3)
        topology.add_connection(c4)
        
        # 检查连接性
        connectivity_result = self.connectivity_service.check_connectivity(topology)
        
        self.assertTrue(connectivity_result["is_fully_connected"])
        self.assertEqual(connectivity_result["number_of_components"], 1)
        self.assertEqual(len(connectivity_result["isolated_devices"]), 0)
    
    def test_optimize_topology(self):
        """测试优化拓扑"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        node1 = Node("node-001", self.node_properties, self.location, self.position)
        line1 = Line("line-001", self.line_properties, self.location, Position(30.0, 40.0, 0.0))
        topology.add_device(node1)
        topology.add_device(line1)
        connection1 = Connection(
            "conn-001",
            "node-001",
            "line-001",
            ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
            {"current": 50.0, "voltage": 400.0}
        )
        topology.add_connection(connection1)
        
        # 优化拓扑
        optimization_result = self.optimization_service.optimize(topology)
        
        self.assertEqual(optimization_result["optimization_score"], 100.0)
        self.assertEqual(len(optimization_result["suggestions"]), 0)
    
    def test_update_topology_status(self):
        """测试更新拓扑状态"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        # 更新拓扑状态
        topology.update_status(TopologyStatus(TopologyStatusEnum.VALIDATED))
        
        self.assertEqual(topology.status.status, TopologyStatusEnum.VALIDATED)
    
    def test_domain_events(self):
        """测试领域事件"""
        topology_id = TopologyId("topo-001")
        topology = MicrogridTopology(topology_id, "测试拓扑")
        
        # 创建节点设备
        node = Node("node-001", self.node_properties, self.location, self.position)
        topology.add_device(node)
        
        # 获取领域事件
        events = topology.clear_domain_events()
        
        self.assertEqual(len(events), 2)  # 拓扑创建事件和设备添加事件

if __name__ == '__main__':
    unittest.main()
