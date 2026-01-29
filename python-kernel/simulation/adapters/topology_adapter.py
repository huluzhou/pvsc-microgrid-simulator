"""
拓扑数据适配器抽象接口
定义标准拓扑数据格式和适配器接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class AdapterError:
    """适配器错误信息"""
    error_type: str  # "adapter" | "topology" | "validation"
    severity: str   # "error" | "warning" | "info"
    message: str
    device_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class AdapterResult:
    """适配器转换结果"""
    success: bool
    data: Any  # 转换后的数据（具体类型由实现决定）
    errors: List[AdapterError]
    warnings: List[AdapterError]


class TopologyAdapter(ABC):
    """拓扑数据适配器抽象基类"""
    
    @abstractmethod
    def convert(self, topology_data: Dict[str, Any]) -> AdapterResult:
        """
        将标准拓扑数据格式转换为计算内核所需格式
        
        Args:
            topology_data: 标准拓扑数据格式
                {
                    "devices": {
                        "device_id": {
                            "device_type": "Node|Line|Transformer|...",
                            "name": "...",
                            "properties": {...},
                            "position": {...},
                            "location": {...}
                        }
                    },
                    "connections": [
                        {
                            "id": "...",
                            "from": "device_id",
                            "to": "device_id",
                            "from_port": "...",
                            "to_port": "...",
                            "connection_type": "...",
                            "properties": {...}
                        }
                    ]
                }
        
        Returns:
            AdapterResult: 包含转换结果、错误和警告
        """
        pass
    
    @abstractmethod
    def validate(self, topology_data: Dict[str, Any]) -> List[AdapterError]:
        """
        验证拓扑数据的完整性和有效性
        
        Args:
            topology_data: 标准拓扑数据格式
        
        Returns:
            List[AdapterError]: 验证错误列表
        """
        pass
    
    def get_default_value(self, device_type: str, property_name: str) -> Any:
        """
        获取设备属性的默认值
        
        Args:
            device_type: 设备类型
            property_name: 属性名称
        
        Returns:
            默认值
        """
        defaults = {
            "Node": {
                "voltage_level": 0.4,  # kV
            },
            "ExternalGrid": {
                "voltage_level": 20.0,  # kV
            },
            "Line": {
                "length": 1.0,  # km
                "cable_type": "NAYY 4x50 SE",
            },
            "Transformer": {
                "rated_power": 0.63,  # MVA
                "high_voltage": 20.0,  # kV
                "low_voltage": 0.4,  # kV
                "std_type": "0.25 MVA 20/0.4 kV",
            },
            "Pv": {
                "rated_power": 0.0,  # kW
            },
            "Load": {
                "rated_power": 0.0,  # kW
            },
            "Storage": {
                "rated_power": 0.0,  # kW
                "capacity": 0.0,  # kWh
            },
            "Charger": {
                "rated_power": 0.0,  # kW
            },
        }
        
        return defaults.get(device_type, {}).get(property_name, None)
