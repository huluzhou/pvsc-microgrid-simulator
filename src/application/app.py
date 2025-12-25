#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用程序入口点，负责初始化依赖注入容器和启动应用程序
"""

from domain.common.events.event_bus import EventBus
from infrastructure.events.blinker_event_bus import BlinkerEventBus
from application.use_cases.topology.topology_use_cases import (
    TopologyCreationUseCase,
    TopologyDeviceManagementUseCase,
    TopologyConnectionManagementUseCase,
    TopologyValidationUseCase,
    TopologyOptimizationUseCase,
    TopologyQueryUseCase
)
from application.use_cases.topology.topology_file_use_cases import (
    TopologyFileUseCase,
    UndoRedoUseCase,
)
from domain.aggregates.topology.ports.topology_use_case_ports import (
    TopologyCreationPort,
    TopologyDeviceManagementPort,
    TopologyConnectionManagementPort,
    TopologyValidationPort,
    TopologyOptimizationPort,
    TopologyQueryPort
)
from domain.aggregates.topology.ports.topology_repository_port import TopologyRepositoryPort
from infrastructure.third_party.di.services import InMemoryTopologyRepository


class Application:
    """应用程序类，负责初始化依赖注入容器和启动应用程序"""
    
    def __init__(self):
        """初始化应用程序"""
        # 初始化事件总线
        self._event_bus = BlinkerEventBus()
        
        # 初始化拓扑存储库（应用层输出端口实现）
        self._topology_repository = InMemoryTopologyRepository()
        
        # 初始化用例实现
        self._init_use_cases()
        
    def _init_use_cases(self):
        """初始化用例实现"""
        # 拓扑用例
        self._topology_creation_use_case = TopologyCreationUseCase(self._event_bus, self._topology_repository)
        self._topology_device_management_use_case = TopologyDeviceManagementUseCase(self._event_bus, self._topology_repository)
        self._topology_connection_management_use_case = TopologyConnectionManagementUseCase(self._event_bus, self._topology_repository)
        self._topology_validation_use_case = TopologyValidationUseCase(self._event_bus, self._topology_repository)
        self._topology_optimization_use_case = TopologyOptimizationUseCase(self._event_bus, self._topology_repository)
        self._topology_query_use_case = TopologyQueryUseCase(self._topology_repository)
        self._topology_file_use_case = TopologyFileUseCase(self._topology_repository)
        self._topology_undo_redo_use_case = UndoRedoUseCase()
    
    @property
    def topology_creation_use_case(self):
        """获取拓扑创建用例"""
        return self._topology_creation_use_case
    
    @property
    def topology_device_management_use_case(self):
        """获取拓扑设备管理用例"""
        return self._topology_device_management_use_case
    
    @property
    def topology_connection_management_use_case(self):
        """获取拓扑连接管理用例"""
        return self._topology_connection_management_use_case

    @property
    def topology_file_use_case(self):
        return self._topology_file_use_case

    @property
    def topology_undo_redo_use_case(self):
        return self._topology_undo_redo_use_case
    
    @property
    def topology_query_use_case(self):
        """获取拓扑查询用例"""
        return self._topology_query_use_case
    
    def run(self):
        """运行应用程序"""
        # 这里可以添加应用程序启动逻辑
        pass
