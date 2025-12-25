#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""依赖注入容器模块，负责对象的创建和生命周期管理"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Type, Callable, Optional


class IContainer(ABC):
    """依赖注入容器接口"""
    
    @abstractmethod
    def register(self, service_type: Type, implementation: Any = None, lifetime: Any = None) -> None:
        """注册服务
        
        Args:
            service_type: 服务类型（通常是接口）
            implementation: 实现类型或实例
            lifetime: 服务生命周期
        """
        pass
    
    @abstractmethod
    def register_singleton(self, service_type: Type, implementation: Any = None) -> None:
        """注册单例服务
        
        Args:
            service_type: 服务类型
            implementation: 实现类型或实例
        """
        pass
    
    @abstractmethod
    def register_transient(self, service_type: Type, implementation: Any = None) -> None:
        """注册瞬态服务（每次请求创建新实例）
        
        Args:
            service_type: 服务类型
            implementation: 实现类型或工厂函数
        """
        pass
    
    @abstractmethod
    def register_factory(self, service_type: Type, factory: Callable) -> None:
        """注册工厂函数
        
        Args:
            service_type: 服务类型
            factory: 创建服务实例的工厂函数
        """
        pass
    
    @abstractmethod
    def resolve(self, service_type: Type) -> Any:
        """解析服务实例
        
        Args:
            service_type: 要解析的服务类型
            
        Returns:
            服务的实例
            
        Raises:
            KeyError: 服务未注册
        """
        pass
    
    @abstractmethod
    def unregister(self, service_type: Type) -> None:
        """注销服务
        
        Args:
            service_type: 要注销的服务类型
        """
        pass
    
    @abstractmethod
    def is_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册
        
        Args:
            service_type: 要检查的服务类型
            
        Returns:
            是否已注册
        """
        pass


class ServiceDescriptor:
    """服务描述符，用于描述服务的注册信息"""
    
    def __init__(self, service_type: Type, implementation: Any, lifetime: Any):
        self.service_type = service_type
        self.implementation = implementation
        self.lifetime = lifetime
        self.instance = None  # 用于单例模式


class Container(IContainer):
    """依赖注入容器的基本实现"""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
    
    def register(self, service_type: Type, implementation: Any = None, lifetime: Any = None) -> None:
        """注册服务
        
        Args:
            service_type: 服务类型（通常是接口）
            implementation: 实现类型或实例，默认为服务类型
            lifetime: 服务生命周期，默认为瞬态
        """
        from .services import ServiceLifetime
        
        if implementation is None:
            implementation = service_type
            
        if lifetime is None:
            lifetime = ServiceLifetime.TRANSIENT
            
        self._services[service_type] = ServiceDescriptor(service_type, implementation, lifetime)
    
    def register_singleton(self, service_type: Type, implementation: Any = None) -> None:
        """注册单例服务
        
        Args:
            service_type: 服务类型
            implementation: 实现类型或实例
        """
        from .services import ServiceLifetime
        self.register(service_type, implementation, ServiceLifetime.SINGLETON)
    
    def register_transient(self, service_type: Type, implementation: Any = None) -> None:
        """注册瞬态服务
        
        Args:
            service_type: 服务类型
            implementation: 实现类型或工厂函数
        """
        from .services import ServiceLifetime
        self.register(service_type, implementation, ServiceLifetime.TRANSIENT)
    
    def register_factory(self, service_type: Type, factory: Callable) -> None:
        """注册工厂函数
        
        Args:
            service_type: 服务类型
            factory: 创建服务实例的工厂函数
        """
        from .services import ServiceLifetime
        self.register(service_type, factory, ServiceLifetime.TRANSIENT)
    
    def resolve(self, service_type: Type) -> Any:
        """解析服务实例
        
        Args:
            service_type: 要解析的服务类型
            
        Returns:
            服务的实例
            
        Raises:
            KeyError: 服务未注册
        """
        if not self.is_registered(service_type):
            raise KeyError(f"Service {service_type.__name__} is not registered")
        
        descriptor = self._services[service_type]
        
        # 单例模式：如果已有实例则直接返回
        from .services import ServiceLifetime
        if descriptor.lifetime == ServiceLifetime.SINGLETON and descriptor.instance is not None:
            return descriptor.instance
        
        # 创建实例
        instance = self._create_instance(descriptor.implementation)
        
        # 单例模式：保存实例
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            descriptor.instance = instance
            
        return instance
    
    def _create_instance(self, implementation: Any) -> Any:
        """创建实例
        
        Args:
            implementation: 实现类型或实例或工厂函数
            
        Returns:
            创建的实例
        """
        # 如果已经是实例，直接返回
        if not isinstance(implementation, type) and callable(implementation):
            # 工厂函数
            try:
                # 尝试将容器自身传递给工厂函数
                return implementation(self)
            except TypeError:
                # 如果工厂函数不接受参数，则不传
                return implementation()
        
        # 如果是类型，则创建实例
        if isinstance(implementation, type):
            try:
                # 尝试无参构造函数
                return implementation()
            except TypeError:
                # 如果需要参数，尝试从容器中解析参数
                # 这里简化处理，实际应用可能需要更复杂的参数解析
                return implementation()
        
        # 已经是实例
        return implementation
    
    def unregister(self, service_type: Type) -> None:
        """注销服务
        
        Args:
            service_type: 要注销的服务类型
        """
        if service_type in self._services:
            del self._services[service_type]
    
    def is_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册
        
        Args:
            service_type: 要检查的服务类型
            
        Returns:
            是否已注册
        """
        return service_type in self._services


# 创建全局容器实例
container = Container()