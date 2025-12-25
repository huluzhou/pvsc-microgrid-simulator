import pytest
from unittest.mock import Mock, patch
from domain.aggregates.topology.value_objects.topology_id import TopologyId
from domain.aggregates.topology.value_objects.topology_status import TopologyStatusEnum
from domain.aggregates.topology.value_objects.device_type import DeviceTypeEnum
from domain.aggregates.topology.value_objects.connection_type import ConnectionTypeEnum
from domain.aggregates.topology.value_objects.position import Position
from domain.common.events.event_bus import EventBus
from application.commands.topology.topology_commands import (
    CreateTopologyCommand,
    AddDeviceCommand,
    CreateConnectionCommand,
    ValidateTopologyCommand,
    OptimizeTopologyCommand
)
from application.use_cases.topology.topology_use_cases import (
    TopologyCreationUseCase,
    TopologyDeviceManagementUseCase,
    TopologyConnectionManagementUseCase,
    TopologyValidationUseCase,
    TopologyOptimizationUseCase
)


class TestTopologyUseCases:
    """拓扑应用层用例测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.event_bus = Mock(spec=EventBus)
    
    def test_create_topology_use_case(self):
        """测试拓扑创建用例"""
        # 准备测试数据
        command = CreateTopologyCommand(
            name="测试拓扑",
            description="测试拓扑描述",
            status=TopologyStatusEnum.CREATED
        )
        
        # 创建用例实例
        use_case = TopologyCreationUseCase(event_bus=self.event_bus)
        
        # 执行用例
        result = use_case.create_topology(command)
        
        # 验证结果
        assert result.name == "测试拓扑"
        assert result.status == TopologyStatusEnum.CREATED
        assert "拓扑创建成功" in result.message
        
        # 验证事件发布
        self.event_bus.publish.assert_called_once()
    
    def test_add_device_use_case(self):
        """测试添加设备用例"""
        # 准备测试数据
        topology_id = TopologyId("test_topology_id")
        position = Position(x=10.0, y=20.0)
        
        command = AddDeviceCommand(
            topology_id=topology_id,
            device_type=DeviceTypeEnum.NODE,
            name="测试节点",
            position=position
        )
        
        # 创建用例实例
        use_case = TopologyDeviceManagementUseCase(event_bus=self.event_bus)
        
        # 执行用例
        result = use_case.add_device(command)
        
        # 验证结果
        # assert result.device_id == "device_测试节点"
        assert result.device_id is not None
        assert result.name == "测试节点"
        assert result.device_type == DeviceTypeEnum.NODE
        
        # 验证事件发布
        self.event_bus.publish.assert_called_once()
    
    def test_create_connection_use_case(self):
        """测试创建连接用例"""
        # 准备测试数据
        topology_id = TopologyId("test_topology_id")
        
        command = CreateConnectionCommand(
            topology_id=topology_id,
            source_device_id="device_1",
            target_device_id="device_2",
            connection_type=ConnectionTypeEnum.BIDIRECTIONAL
        )
        
        # 创建用例实例
        use_case = TopologyConnectionManagementUseCase(event_bus=self.event_bus)
        
        # 执行用例
        result = use_case.create_connection(command)
        
        # 验证结果
        assert result.connection_id == "conn_device_1_device_2"
        assert result.source_device_id == "device_1"
        assert result.target_device_id == "device_2"
        
        # 验证事件发布
        self.event_bus.publish.assert_called_once()
    
    def test_validate_topology_use_case(self):
        """测试拓扑验证用例"""
        # 准备测试数据
        topology_id = TopologyId("test_topology_id")
        
        command = ValidateTopologyCommand(
            topology_id=topology_id
        )
        
        # 创建用例实例
        use_case = TopologyValidationUseCase(event_bus=self.event_bus)
        
        # 执行用例
        result = use_case.validate_topology(command)
        
        # 验证结果
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        
        # 验证事件发布
        self.event_bus.publish.assert_called_once()
    
    def test_optimize_topology_use_case(self):
        """测试拓扑优化用例"""
        # 准备测试数据
        topology_id = TopologyId("test_topology_id")
        
        command = OptimizeTopologyCommand(
            topology_id=topology_id,
            optimization_goals=["minimize_loss", "maximize_reliability"]
        )
        
        # 创建用例实例
        use_case = TopologyOptimizationUseCase(event_bus=self.event_bus)
        
        # 执行用例
        result = use_case.optimize_topology(command)
        
        # 验证结果
        assert isinstance(result.optimization_result, dict)
        assert isinstance(result.recommendations, list)
        assert "拓扑优化成功" in result.message
        
        # 验证事件发布
        self.event_bus.publish.assert_called_once()
