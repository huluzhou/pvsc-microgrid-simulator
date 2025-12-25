# 导入Blinker库和必要组件
from blinker import Namespace
import logging
import asyncio
import threading
from typing import Dict, Callable, Any, List, Optional

# 创建命名空间用于隔离不同域的事件
_event_bus = Namespace()

# 定义标准领域事件
# 拓扑变更事件
TOPOLOGY_CHANGED = 'topology_changed'
# 设备更新事件
DEVICE_UPDATED = 'device_updated'
# 功率计算完成事件
POWER_CALCULATED = 'power_calculated'
# 控制命令执行事件
CONTROL_COMMAND_EXECUTED = 'control_command_executed'
# 设备命令执行事件
DEVICE_COMMAND_EXECUTED = 'device_command_executed'
# 设备状态变更事件
DEVICE_STATE_CHANGED = 'device_state_changed'
# 设备参数更新事件
DEVICE_PARAMETER_UPDATED = 'device_parameter_updated'
# 回测完成事件
BACKTEST_COMPLETED = 'backtest_completed'

# 事件处理器接口
class IEventHandler:
    """事件处理器接口，用于处理领域事件"""
    
    def handle(self, event_data: Dict[str, Any], **kwargs) -> None:
        """处理事件的方法，需要由具体实现类重写"""
        pass

# 事件总线接口
class IEventBus:
    """事件总线接口，定义了事件发布订阅的标准操作"""
    
    def subscribe(self, event_name: str, handler: Callable) -> None:
        """订阅事件"""
        pass
    
    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """取消事件订阅"""
        pass
    
    def publish(self, event_name: str, event_data: Dict[str, Any] = None, **kwargs) -> None:
        """同步发布事件"""
        pass
    
    async def publish_async(self, event_name: str, event_data: Dict[str, Any] = None, **kwargs) -> None:
        """异步发布事件"""
        pass

# 事件总线实现类
class EventBus(IEventBus):
    """事件总线实现，基于Blinker库提供事件发布订阅功能"""
    
    def __init__(self):
        self._namespace = _event_bus
        self._handlers_map: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
    
    def subscribe(self, event_name: str, handler: Callable) -> None:
        """订阅事件
        
        Args:
            event_name: 事件名称
            handler: 事件处理函数或IEventHandler实例
        """
        # 获取或创建事件
        event = self._namespace.signal(event_name)
            
        # 处理IEventHandler实例
        if isinstance(handler, IEventHandler):
            actual_handler = handler.handle
        else:
            actual_handler = handler
        
        with self._lock:
            event.connect(actual_handler)
            if event_name not in self._handlers_map:
                self._handlers_map[event_name] = []
            self._handlers_map[event_name].append(actual_handler)
            
        logging.info(f"Subscribed to event: {event_name}")
    
    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """取消事件订阅
        
        Args:
            event_name: 事件名称
            handler: 事件处理函数或IEventHandler实例
        """
        # 获取事件
        event = self._namespace.signal(event_name)
            
        # 处理IEventHandler实例
        if isinstance(handler, IEventHandler):
            actual_handler = handler.handle
        else:
            actual_handler = handler
        
        with self._lock:
            try:
                event.disconnect(actual_handler)
                if event_name in self._handlers_map and actual_handler in self._handlers_map[event_name]:
                    self._handlers_map[event_name].remove(actual_handler)
                logging.info(f"Unsubscribed from event: {event_name}")
            except ValueError:
                # 处理处理函数未连接的情况
                pass
    
    def publish(self, event_name: str, event_data: Dict[str, Any] = None, **kwargs) -> None:
        """同步发布事件
        
        Args:
            event_name: 事件名称
            event_data: 事件数据字典
            **kwargs: 额外的事件参数
        """
        # 获取事件
        event = self._namespace.signal(event_name)
            
        # 确保event_data是字典
        if event_data is None:
            event_data = {}
        
        try:
            event.send(None, event_data=event_data, **kwargs)
        except Exception as e:
            logging.error(f"Error publishing event {event_name}: {str(e)}")
    
    async def publish_async(self, event_name: str, event_data: Dict[str, Any] = None, **kwargs) -> None:
        """异步发布事件
        
        Args:
            event_name: 事件名称
            event_data: 事件数据字典
            **kwargs: 额外的事件参数
        """
        # 获取事件
        event = self._namespace.signal(event_name)
            
        # 确保event_data是字典
        if event_data is None:
            event_data = {}
        
        # 获取当前事件循环
        loop = asyncio.get_event_loop()
        
        try:
            # 在默认执行器中运行同步发送方法
            await loop.run_in_executor(None, lambda: event.send(None, event_data=event_data, **kwargs))
        except Exception as e:
            logging.error(f"Error publishing event {event_name} asynchronously: {str(e)}")

# 创建全局事件总线实例
event_bus = EventBus()