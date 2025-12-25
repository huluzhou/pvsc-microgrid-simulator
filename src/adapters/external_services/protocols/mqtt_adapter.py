from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ports.outbound.device.device_control_port import DeviceControlPort


class MQTTAdapterInterface(ABC):
    """MQTT协议适配器接口"""
    
    @abstractmethod
    def connect(self, config: dict):
        """建立MQTT连接"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开MQTT连接"""
        pass
    
    @abstractmethod
    def subscribe(self, topic: str, qos: int = 0):
        """订阅MQTT主题"""
        pass
    
    @abstractmethod
    def unsubscribe(self, topic: str):
        """取消订阅MQTT主题"""
        pass
    
    @abstractmethod
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """发布MQTT消息"""
        pass
    
    @abstractmethod
    def get_subscribed_topics(self) -> list:
        """获取已订阅的主题列表"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查MQTT连接状态"""
        pass
    
    @abstractmethod
    def register_message_handler(self, handler):
        """注册消息处理器"""
        pass


class MQTTAdapter(MQTTAdapterInterface):
    """MQTT协议适配器实现"""
    
    def __init__(self, device_control_port: DeviceControlPort):
        """初始化MQTT适配器
        
        Args:
            device_control_port: 设备控制端口，用于与领域层交互
        """
        self.device_control_port = device_control_port
        self._connected = False
        self._subscribed_topics = []
        self._message_handlers = []
    
    def connect(self, config: dict):
        """建立MQTT连接
        
        Args:
            config: 连接配置，包含broker、port、username、password等信息
        """
        # 实际实现中，这里会使用paho-mqtt库建立连接
        self._connected = True
    
    def disconnect(self):
        """断开MQTT连接"""
        self._connected = False
        self._subscribed_topics = []
    
    def subscribe(self, topic: str, qos: int = 0):
        """订阅MQTT主题
        
        Args:
            topic: 要订阅的主题
            qos: 服务质量等级（0, 1, 2）
        """
        if topic not in self._subscribed_topics:
            self._subscribed_topics.append(topic)
    
    def unsubscribe(self, topic: str):
        """取消订阅MQTT主题
        
        Args:
            topic: 要取消订阅的主题
        """
        if topic in self._subscribed_topics:
            self._subscribed_topics.remove(topic)
    
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """发布MQTT消息
        
        Args:
            topic: 发布主题
            payload: 消息内容
            qos: 服务质量等级
            retain: 是否保留消息
        """
        # 实际实现中，这里会使用paho-mqtt库发布消息
        pass
    
    def get_subscribed_topics(self) -> list:
        """获取已订阅的主题列表
        
        Returns:
            已订阅的主题列表
        """
        return self._subscribed_topics.copy()
    
    def is_connected(self) -> bool:
        """检查MQTT连接状态
        
        Returns:
            连接状态（True/False）
        """
        return self._connected
    
    def register_message_handler(self, handler):
        """注册消息处理器
        
        Args:
            handler: 消息处理器函数
        """
        if handler not in self._message_handlers:
            self._message_handlers.append(handler)
    
    def publish_device_state(self, device_id: str, state: dict):
        """发布设备状态
        
        Args:
            device_id: 设备ID
            state: 设备状态
        """
        topic = f"devices/{device_id}/state"
        # 实际实现中，这里会将状态转换为JSON字符串并发布
        self.publish(topic, str(state))
    
    def subscribe_to_device_commands(self, device_id: str):
        """订阅设备命令主题
        
        Args:
            device_id: 设备ID
        """
        topic = f"devices/{device_id}/commands"
        self.subscribe(topic)
