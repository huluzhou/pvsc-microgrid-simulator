from typing import Dict, Any

class UnitConversionService:
    """单位转换服务"""
    
    # 基本转换因子
    _conversion_factors: Dict[str, Dict[str, float]] = {
        "power": {
            "W": 1.0,
            "kW": 1000.0,
            "MW": 1000000.0,
            "GW": 1000000000.0
        },
        "energy": {
            "Wh": 1.0,
            "kWh": 1000.0,
            "MWh": 1000000.0,
            "GWh": 1000000000.0
        },
        "voltage": {
            "V": 1.0,
            "kV": 1000.0,
            "MV": 1000000.0
        },
        "current": {
            "A": 1.0,
            "kA": 1000.0
        },
        "time": {
            "s": 1.0,
            "min": 60.0,
            "h": 3600.0,
            "d": 86400.0
        }
    }
    
    @staticmethod
    def convert(value: float, from_unit: str, to_unit: str, quantity_type: str = None) -> float:
        """执行单位转换"""
        if from_unit == to_unit:
            return value
        
        # 如果没有指定数量类型，尝试自动检测
        if quantity_type is None:
            quantity_type = UnitConversionService._detect_quantity_type(from_unit)
            if quantity_type is None:
                raise ValueError(f"Unable to detect quantity type for unit {from_unit}")
        
        if quantity_type not in UnitConversionService._conversion_factors:
            raise ValueError(f"Unsupported quantity type: {quantity_type}")
        
        factors = UnitConversionService._conversion_factors[quantity_type]
        
        if from_unit not in factors:
            raise ValueError(f"Unsupported from unit: {from_unit} for quantity type {quantity_type}")
        if to_unit not in factors:
            raise ValueError(f"Unsupported to unit: {to_unit} for quantity type {quantity_type}")
        
        # 转换为基本单位，然后转换为目标单位
        base_value = value * factors[from_unit]
        return base_value / factors[to_unit]
    
    @staticmethod
    def _detect_quantity_type(unit: str) -> str:
        """自动检测数量类型"""
        for quantity_type, units in UnitConversionService._conversion_factors.items():
            if unit in units:
                return quantity_type
        return None
    
    @staticmethod
    def get_supported_units(quantity_type: str) -> list:
        """获取支持的单位列表"""
        if quantity_type not in UnitConversionService._conversion_factors:
            raise ValueError(f"Unsupported quantity type: {quantity_type}")
        return list(UnitConversionService._conversion_factors[quantity_type].keys())
    
    @staticmethod
    def is_supported_conversion(from_unit: str, to_unit: str, quantity_type: str = None) -> bool:
        """检查转换是否支持"""
        try:
            UnitConversionService.convert(1.0, from_unit, to_unit, quantity_type)
            return True
        except ValueError:
            return False
