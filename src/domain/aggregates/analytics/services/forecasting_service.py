"""预测服务模块"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.domain.models.entities.load_curve import LoadCurve
from src.domain.models.entities.power_data import PowerData
from src.domain.models.value_objects.load_profile import LoadProfile
from src.domain.models.value_objects.weather_forecast import WeatherForecast
from src.domain.models.value_objects.forecast_result import ForecastResult
from src.domain.models.entities.network_topology import NetworkTopology


class ForecastingService:
    """预测服务类
    
    提供负载预测、发电量预测和场景分析功能
    """
    
    def __init__(self):
        """初始化预测服务"""
        pass
    
    def validate_forecast_parameters(self, historical_data: List[float], forecast_horizon: int) -> Dict[str, Any]:
        """
        验证预测参数
        
        Args:
            historical_data: 历史数据
            forecast_horizon: 预测时间范围
            
        Returns:
            验证结果
        """
        validation_result = {
            "is_valid": True,
            "errors": []
        }
        
        # 验证历史数据
        if not historical_data:
            validation_result["is_valid"] = False
            validation_result["errors"].append("历史数据不能为空")
        elif len(historical_data) < 7:
            validation_result["is_valid"] = False
            validation_result["errors"].append("历史数据至少需要7个数据点")
        
        # 验证预测时间范围
        if forecast_horizon <= 0:
            validation_result["is_valid"] = False
            validation_result["errors"].append("预测时间范围必须大于0")
        elif forecast_horizon > 168:  # 最多预测一周
            validation_result["is_valid"] = False
            validation_result["errors"].append("预测时间范围不能超过168小时")
        
        return validation_result
    
    def preprocess_historical_data(self, historical_data: List[float]) -> List[float]:
        """
        预处理历史数据
        
        Args:
            historical_data: 原始历史数据
            
        Returns:
            预处理后的数据
        """
        # 移除异常值 (简化实现)
        if not historical_data:
            return []
        
        # 计算平均值和标准差
        avg_value = sum(historical_data) / len(historical_data)
        std_value = (sum((x - avg_value) ** 2 for x in historical_data) / len(historical_data)) ** 0.5 if len(historical_data) > 1 else 0
        
        # 移除超出3个标准差的数据
        processed_data = [x for x in historical_data if abs(x - avg_value) <= 3 * std_value]
        
        # 如果移除后数据太少，使用原始数据
        if len(processed_data) < 3:
            return historical_data
        
        return processed_data

    def forecast_load(self, load_profile: LoadProfile, forecast_horizon: int, 
                     weather_forecast: Optional[WeatherForecast] = None) -> ForecastResult:
        """预测负载曲线
        
        Args:
            load_profile: 负载配置文件
            forecast_horizon: 预测时间范围（小时）
            weather_forecast: 天气预报（可选）
            
        Returns:
            ForecastResult: 预测结果
        """
        # 获取历史负载数据
        historical_loads = load_profile.get_historical_data()
        
        # 验证参数
        validation = self.validate_forecast_parameters(historical_loads, forecast_horizon)
        if not validation["is_valid"]:
            return ForecastResult(
                timestamp=datetime.now(),
                forecast_values=[0.0] * forecast_horizon,
                confidence_intervals=[(0, 0)] * forecast_horizon,
                is_successful=False,
                error_messages=validation["errors"]
            )
        
        # 预处理数据
        processed_data = self.preprocess_historical_data(historical_loads)
        
        # 简单预测实现
        if not processed_data:
            predicted_values = [0.0] * forecast_horizon
        else:
            # 计算历史数据的平均值作为简单预测
            avg_load = sum(processed_data) / len(processed_data)
            predicted_values = [avg_load] * forecast_horizon
        
        # 添加天气因子调整（如果提供）
        if weather_forecast:
            # 简化的天气影响模型
            temperature = weather_forecast.get_temperature()
            if temperature > 30:
                # 高温增加制冷负荷
                predicted_values = [v * 1.2 for v in predicted_values]
            elif temperature < 10:
                # 低温增加供暖负荷
                predicted_values = [v * 1.15 for v in predicted_values]
        
        # 生成置信区间（简化实现）
        confidence_intervals = [(v * 0.9, v * 1.1) for v in predicted_values]
        
        # 创建预测结果
        return ForecastResult(
            timestamp=datetime.now(),
            forecast_values=predicted_values,
            confidence_intervals=confidence_intervals,
            is_successful=True,
            error_messages=[]
        )

    def forecast_power_generation(self, device_type: str, capacity: float, 
                                historical_data: List[PowerData], 
                                weather_forecast: WeatherForecast) -> ForecastResult:
        """预测可再生能源发电量
        
        Args:
            device_type: 设备类型（如'solar', 'wind'等）
            capacity: 设备容量
            historical_data: 历史发电量数据
            weather_forecast: 天气预报
            
        Returns:
            ForecastResult: 预测结果
        """
        # 提取历史有功功率数据
        historical_values = [data.active_power for data in historical_data]
        
        # 验证参数
        validation = self.validate_forecast_parameters(historical_values, 24)  # 预测24小时
        if not validation["is_valid"]:
            return ForecastResult(
                timestamp=datetime.now(),
                forecast_values=[0.0] * 24,
                confidence_intervals=[(0, 0)] * 24,
                is_successful=False,
                error_messages=validation["errors"]
            )
        
        # 预处理数据
        processed_data = self.preprocess_historical_data(historical_values)
        
        # 简单预测实现
        if not processed_data:
            predicted_values = [0.0] * 24
        else:
            # 计算平均容量因子
            avg_capacity_factor = sum(processed_data) / (len(processed_data) * capacity) if capacity > 0 else 0
            
            # 根据设备类型和天气条件调整
            if device_type.lower() == 'solar':
                # 基于阳光强度调整
                sunlight_intensity = weather_forecast.get_sunlight_intensity()
                predicted_values = [capacity * avg_capacity_factor * sunlight_intensity for _ in range(24)]
            elif device_type.lower() == 'wind':
                # 基于风速调整
                wind_speed = weather_forecast.get_wind_speed()
                predicted_values = [capacity * avg_capacity_factor * wind_speed / 10.0 for _ in range(24)]  # 假设额定风速10m/s
            else:
                predicted_values = [capacity * avg_capacity_factor for _ in range(24)]
        
        # 生成置信区间
        confidence_intervals = [(v * 0.85, v * 1.15) for v in predicted_values]
        
        return ForecastResult(
            timestamp=datetime.now(),
            forecast_values=predicted_values,
            confidence_intervals=confidence_intervals,
            is_successful=True,
            error_messages=[]
        )

    def generate_scenario_analysis(self, scenarios: List[str], 
                                 topology: NetworkTopology, 
                                 forecast_results: Dict[str, ForecastResult]) -> Dict[str, Dict[str, Any]]:
        """生成场景分析
        
        Args:
            scenarios: 场景列表
            topology: 网络拓扑
            forecast_results: 预测结果字典
            
        Returns:
            Dict[str, Dict]: 场景分析结果
        """
        results = {}
        
        for scenario in scenarios:
            if scenario.lower() == 'peak_load':
                # 高峰负载场景分析
                load_forecast = forecast_results.get('load', None)
                results[scenario] = self._analyze_peak_load_scenario(load_forecast, topology)
            
            elif scenario.lower() == 'renewable_max':
                # 可再生能源最大化场景
                gen_forecasts = {k: v for k, v in forecast_results.items() if k != 'load'}
                results[scenario] = self._analyze_renewable_max_scenario(gen_forecasts, topology)
            
            elif scenario.lower() == 'grid_failure':
                # 电网故障场景
                results[scenario] = self._analyze_grid_failure_scenario(topology)
            
            elif scenario.lower() == 'congestion_risk':
                # 线路拥堵风险场景
                results[scenario] = self._analyze_congestion_risk_scenario(forecast_results, topology)
            
            else:
                results[scenario] = {
                    "description": f"未知场景: {scenario}",
                    "error": "不支持的场景类型"
                }
        
        return results
    
    def postprocess_forecast_results(self, forecast_result: ForecastResult, 
                                   constraints: Dict[str, Any]) -> ForecastResult:
        """
        后处理预测结果，应用系统约束
        
        Args:
            forecast_result: 原始预测结果
            constraints: 系统约束
            
        Returns:
            后处理后的预测结果
        """
        # 应用上限约束
        if 'max_value' in constraints:
            forecast_result.forecast_values = [
                min(v, constraints['max_value']) for v in forecast_result.forecast_values
            ]
        
        # 应用下限约束
        if 'min_value' in constraints:
            forecast_result.forecast_values = [
                max(v, constraints['min_value']) for v in forecast_result.forecast_values
            ]
        
        # 更新置信区间
        forecast_result.confidence_intervals = [
            (max(l, constraints.get('min_value', 0)), 
             min(u, constraints.get('max_value', float('inf')))) 
            for l, u in forecast_result.confidence_intervals
        ]
        
        return forecast_result
    
    def _analyze_peak_load_scenario(self, load_forecast: Optional[ForecastResult], 
                                  topology: NetworkTopology) -> Dict[str, Any]:
        """分析高峰负载场景"""
        result = {
            "description": "高峰负载场景",
            "peak_demand": 0.0,
            "generation_capacity": 0.0,
            "generation_shortfall": 0.0,
            "recommendations": []
        }
        
        # 计算峰值需求
        if load_forecast and load_forecast.is_successful:
            result["peak_demand"] = max(load_forecast.forecast_values)
        
        # 计算发电容量
        for device in topology.get_all_devices():
            if device.device_type in ['PV', 'Wind', 'Generator']:
                result["generation_capacity"] += device.capacity
        
        # 计算发电缺口
        result["generation_shortfall"] = max(0, result["peak_demand"] - result["generation_capacity"])
        
        # 生成建议
        if result["generation_shortfall"] > 0:
            result["recommendations"] = [
                "启动备用机组",
                "实施需求响应",
                "优化储能放电",
                "考虑削减非关键负载"
            ]
        
        return result
    
    def _analyze_renewable_max_scenario(self, gen_forecasts: Dict[str, ForecastResult], 
                                      topology: NetworkTopology) -> Dict[str, Any]:
        """分析可再生能源最大化场景"""
        result = {
            "description": "可再生能源最大化场景",
            "total_renewable_generation": 0.0,
            "curtailment_needed": 0.0,
            "recommendations": []
        }
        
        # 计算预测的可再生能源发电总量
        for forecast_name, forecast in gen_forecasts.items():
            if forecast.is_successful and forecast_name.lower() in ['solar', 'wind']:
                result["total_renewable_generation"] += sum(forecast.forecast_values)
        
        # 生成建议
        result["recommendations"] = [
            "优化储能充电",
            "调整负载曲线",
            "最大化本地消纳",
            "考虑功率因数优化"
        ]
        
        return result
    
    def _analyze_grid_failure_scenario(self, topology: NetworkTopology) -> Dict[str, Any]:
        """分析电网故障场景"""
        island_capacity = 0.0
        critical_load = 0.0
        
        # 计算孤岛运行能力
        for device in topology.get_all_devices():
            if device.device_type in ['PV', 'Wind', 'Generator', 'Battery']:
                island_capacity += device.capacity
            elif device.device_type == 'Load' and hasattr(device, 'is_critical') and device.is_critical:
                critical_load += device.capacity
        
        return {
            "description": "电网故障场景",
            "island_capacity": island_capacity,
            "critical_load": critical_load,
            "critical_load_served": min(critical_load, island_capacity),
            "recommendations": [
                "隔离关键负载",
                "启动黑启动程序",
                "优化微网运行",
                "实施负载优先级控制"
            ]
        }
    
    def _analyze_congestion_risk_scenario(self, forecast_results: Dict[str, ForecastResult], 
                                        topology: NetworkTopology) -> Dict[str, Any]:
        """分析线路拥堵风险场景"""
        result = {
            "description": "线路拥堵风险场景",
            "congestion_risk_level": "low",
            "critical_connections": [],
            "recommendations": []
        }
        
        # 简化实现 - 实际应基于功率流计算
        result["recommendations"] = [
            "优化功率调度",
            "考虑网络重构",
            "调整分布式发电出力",
            "实施需求侧管理"
        ]
        
        return result