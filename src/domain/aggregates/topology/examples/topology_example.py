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

# 创建事件总线
event_bus = InMemoryEventBus()

# 创建拓扑验证服务
validation_service = TopologyValidationService(event_bus)

# 创建拓扑连接性服务
connectivity_service = TopologyConnectivityService()

# 创建拓扑优化服务
optimization_service = TopologyOptimizationService()

# 创建拓扑
print("=== 创建拓扑 ===")
topology_id = TopologyId("topo-001")
topology = MicrogridTopology(topology_id, "测试微电网拓扑", "用于测试的微电网拓扑")
print(f"创建拓扑: {topology.name}, ID: {topology.id}")

# 创建设备属性
node_properties = DeviceProperties({"voltage_level": 400.0, "max_current": 100.0})
line_properties = DeviceProperties({"resistance": 0.1, "reactance": 0.5, "capacitance": 0.01})
transformer_properties = DeviceProperties({"primary_voltage": 10000.0, "secondary_voltage": 400.0, "power_rating": 500.0})
switch_properties = DeviceProperties({"is_closed": True, "max_current": 200.0})

# 创建位置和位置信息
location = Location(39.9042, 116.4074, 50.0)
position = Position(10.0, 20.0, 0.0)

# 创建设备
print("\n=== 添加设备 ===")
node1 = Node("node-001", node_properties, location, position)
node2 = Node("node-002", node_properties, location, Position(30.0, 40.0, 0.0))
line1 = Line("line-001", line_properties, location, position)
transformer1 = Transformer("transformer-001", transformer_properties, location, position)
switch1 = Switch("switch-001", switch_properties, location, position)

# 添加设备到拓扑
topology.add_device(node1)
topology.add_device(node2)
topology.add_device(line1)
topology.add_device(transformer1)
topology.add_device(switch1)

print(f"拓扑设备数量: {len(topology.devices)}")
for device in topology.devices:
    print(f"  - {device.id}: {device.device_type.type}")

# 创建连接
print("\n=== 添加连接 ===")
connection1 = Connection(
    "conn-001",
    "node-001",
    "line-001",
    ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
    {"current": 50.0, "voltage": 400.0}
)

connection2 = Connection(
    "conn-002",
    "line-001",
    "switch-001",
    ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
    {"current": 50.0, "voltage": 400.0}
)

connection3 = Connection(
    "conn-003",
    "switch-001",
    "transformer-001",
    ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
    {"current": 50.0, "voltage": 400.0}
)

connection4 = Connection(
    "conn-004",
    "transformer-001",
    "node-002",
    ConnectionType(ConnectionTypeEnum.BIDIRECTIONAL),
    {"current": 50.0, "voltage": 400.0}
)

# 添加连接到拓扑
topology.add_connection(connection1)
topology.add_connection(connection2)
topology.add_connection(connection3)
topology.add_connection(connection4)

print(f"拓扑连接数量: {len(topology.connections)}")
for connection in topology.connections:
    print(f"  - {connection.id}: {connection.source_device_id} -> {connection.target_device_id}")

# 验证拓扑
print("\n=== 验证拓扑 ===")
try:
    validation_result = validation_service.validate(topology)
    print(f"拓扑验证结果: {'有效' if validation_result['is_valid'] else '无效'}")
    print(f"验证分数: {validation_result}")
except Exception as e:
    print(f"拓扑验证失败: {e}")

# 检查连接性
print("\n=== 检查连接性 ===")
connectivity_result = connectivity_service.check_connectivity(topology)
print(f"拓扑连接性: {'完全连通' if connectivity_result['is_fully_connected'] else '不完全连通'}")
print(f"连通组件数量: {connectivity_result['number_of_components']}")
print(f"孤立设备: {connectivity_result['isolated_devices']}")

# 优化拓扑
print("\n=== 优化拓扑 ===")
optimization_result = optimization_service.optimize(topology)
print(f"优化分数: {optimization_result['optimization_score']:.2f}")
print("优化建议:")
for suggestion in optimization_result['suggestions']:
    print(f"  - {suggestion}")

# 更新拓扑状态
print("\n=== 更新拓扑状态 ===")
topology.update_status(TopologyStatus(TopologyStatusEnum.VALIDATED))
print(f"拓扑状态: {topology.status.status}")

# 获取拓扑事件
print("\n=== 拓扑事件 ===")
events = topology.clear_domain_events()
print(f"事件数量: {len(events)}")
for event in events:
    print(f"  - {event.event_type}: {event.timestamp}")

print("\n=== 拓扑示例完成 ===")
