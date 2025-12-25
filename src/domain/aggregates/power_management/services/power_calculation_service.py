"""功率计算服务模块"""
from typing import List, Optional
from src.domain.models.entities.power_data import PowerData


class PowerCalculationService:
    """功率计算服务类
    
    提供功率平衡、损耗估算、效率计算和需求预测功能
    """
    
    @staticmethod
    def calculate_power_balance(generation: float, consumption: float) -> float:
        """
        计算功率平衡
        
        Args:
            generation: 发电量
            consumption: 消耗量
            
        Returns:
            功率平衡值（正值表示盈余，负值表示不足）
        """
        return generation - consumption
    
    @staticmethod
    def estimate_losses(power_data: list[PowerData]) -> float:
        """
        估算系统损耗
        
        Args:
            power_data: 功率数据列表
            
        Returns:
            估计的损耗值
        """
        if not power_data:
            return 0.0
        
        # 简单的损耗估算逻辑（实际项目中应使用更精确的计算方法）
        total_loss = 0.0
        for data in power_data:
            # 假设5%的功率损耗
            total_loss += abs(data.power_value) * 0.05
        
        return total_loss
    
    @staticmethod
    def calculate_efficiency(input_power: float, output_power: float) -> float:
        """
        计算效率
        
        Args:
            input_power: 输入功率
            output_power: 输出功率
            
        Returns:
            效率值（0到1之间）
        """
        if input_power <= 0:
            raise ValueError("输入功率必须大于零")
        
        efficiency = output_power / input_power
        # 确保效率在合理范围内
        return max(0, min(1, efficiency))
    
    @staticmethod
    def forecast_demand(historical_data: list[PowerData], hours_ahead: int) -> list[float]:
        """
        预测未来需求
        
        Args:
            historical_data: 历史功率数据
            hours_ahead: 预测小时数
            
        Returns:
            预测的需求值列表
        """
        if not historical_data:
            return [0.0] * hours_ahead
        
        # 简单的预测逻辑（实际项目中应使用更复杂的预测算法）
        # 计算历史数据的平均值作为预测基础
        avg_demand = sum(abs(data.power_value) for data in historical_data) / len(historical_data)
        
        # 生成预测结果
        predictions = []
        for i in range(hours_ahead):
            # 简单地基于平均值进行预测，添加一些随机波动
            hour_of_day = (i % 24)
            # 模拟一天内的需求模式
            if 8 <= hour_of_day <= 10 or 17 <= hour_of_day <= 21:  # 早高峰和晚高峰
                predictions.append(avg_demand * 1.2)
            elif 0 <= hour_of_day <= 6:  # 夜间低谷
                predictions.append(avg_demand * 0.7)
            else:  # 其他时间
                predictions.append(avg_demand)
        
        return predictions