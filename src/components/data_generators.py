"""
数据生成器模块
提供负载、光伏等设备的动态数据生成功能
"""

import numpy as np
from abc import ABC, abstractmethod


class BaseDataGenerator(ABC):
    """数据生成基类 - 定义通用接口"""
    
    def __init__(self):
        self.is_running = False
        self.interval = 5  # 默认5秒
        self.variation = 20  # 默认20%变化幅度
    
    def set_interval(self, interval):
        """设置生成间隔
        
        Args:
            interval: 生成间隔（秒）
        """
        self.interval = max(1, min(60, interval))
    
    def set_variation(self, variation):
        """设置变化幅度
        
        Args:
            variation: 变化幅度百分比（5-50%）
        """
        self.variation = max(5, min(50, variation))
    
    def start_generation(self):
        """开始数据生成"""
        self.is_running = True
    
    def stop_generation(self):
        """停止数据生成"""
        self.is_running = False
    
    @abstractmethod
    def generate_data(self, index, network_model):
        """生成数据 - 抽象方法，由子类实现
        
        Args:
            index: 设备索引
            network_model: 网络模型
            
        Returns:
            dict: 生成的数据字典
        """
        pass


class LoadDataGenerator(BaseDataGenerator):
    """负载数据生成器 - 生成基于日负荷曲线的负载数据"""
    
    def __init__(self):
        super().__init__()
        self.load_type = 'residential'  # 默认住宅负载
    
    def set_load_type(self, load_type):
        """设置负载类型
        
        Args:
            load_type: 负载类型 ('residential', 'commercial', 'industrial')
        """
        self.load_type = load_type
    
    def generate_data(self, index, network_model):
        """生成负载数据
        
        Args:
            index: 负载索引
            network_model: 网络模型
            
        Returns:
            dict: 负载数据字典
        """
        return self.generate_load_data(index, network_model)
    
    def generate_load_data(self, index, network_model):
        """生成负载数据
        
        Args:
            index: 负载索引
            network_model: 网络模型
            
        Returns:
            dict: 负载数据字典
        """
        if not self.is_running or not network_model or not hasattr(network_model, 'net'):
            return {}
            
        load_data = {}
        
        # 24小时日负荷模式曲线
        daily_pattern = [
            0.6, 0.5, 0.4, 0.3, 0.3, 0.4,  # 0-5时
            0.5, 0.7, 0.8, 0.9, 0.95, 1.0,  # 6-11时
            1.0, 0.95, 0.9, 0.85, 0.9, 1.0,  # 12-17时
            1.1, 1.2, 1.1, 0.9, 0.8, 0.7   # 18-23时
        ]
        
        # 获取当前时间
        from datetime import datetime
        current_hour = datetime.now().hour
        pattern_index = current_hour % 24
        
        # 计算基于时间曲线的基准值
        time_based_base_value = daily_pattern[pattern_index]
        
        # 根据负载类型调整模式
        if self.load_type == 'commercial':
            # 商业负载：白天高，晚上低
            commercial_pattern = [
                0.3, 0.2, 0.2, 0.2, 0.2, 0.3,  # 0-5时
                0.5, 0.7, 0.9, 1.0, 1.0, 1.0,  # 6-11时
                1.0, 1.0, 0.9, 0.9, 0.9, 0.8,  # 12-17时
                0.6, 0.4, 0.3, 0.3, 0.3, 0.3   # 18-23时
            ]
            time_based_base_value = commercial_pattern[pattern_index]
        elif self.load_type == 'industrial':
            # 工业负载：相对平稳
            industrial_pattern = [
                0.7, 0.6, 0.6, 0.6, 0.7, 0.8,  # 0-5时
                0.9, 1.0, 1.0, 1.0, 1.0, 1.0,  # 6-11时
                1.0, 1.0, 1.0, 1.0, 1.0, 1.0,  # 12-17时
                0.9, 0.8, 0.7, 0.7, 0.7, 0.7   # 18-23时
            ]
            time_based_base_value = industrial_pattern[pattern_index]
        
        # 计算变化范围（基于用户设置的variation参数）
        variation_factor = self.variation / 100.0
        min_variation = 1.0 - variation_factor
        max_variation = 1.0 + variation_factor
        
        # 在曲线模板基础上添加随机变化
        random_variation = np.random.uniform(min_variation, max_variation)
        final_base_value = time_based_base_value * random_variation
        
        try:
            
            # 根据时间曲线和随机变化计算新的负载值
            
            load_data[index] = {
                'p_mw': final_base_value,
                'q_mvar': 0,
            }
            
        except (KeyError, AttributeError):
            print(f"负载索引 {index} 不存在")
            
        return load_data
    
    def generate_daily_load_profile(self, network_model):
        """生成日负载曲线数据
        
        Args:
            network_model: 网络模型
            
        Returns:
            dict: 日负载曲线数据
        """
        if not network_model or not hasattr(network_model, 'net'):
            return {}
            
        load_profiles = {}
        
        if not network_model.net.load.empty:
            for idx, load in network_model.net.load.iterrows():
                load_data = self.generate_load_data(idx, network_model)
                if idx in load_data:
                    load_profiles[idx] = load_data[idx]
                    
        return load_profiles


class PVDataGenerator(BaseDataGenerator):
    """光伏数据生成器 - 生成基于天气和季节的光伏发电数据"""
    
    def __init__(self):
        super().__init__()
        self.weather_type = 'sunny'  # 默认晴天
        self.season_factor = 'spring'  # 默认春季
        self.cloud_cover = 0.0  # 默认无云
    
    def set_weather_type(self, weather_type):
        """设置天气类型
        
        Args:
            weather_type: 天气类型 ('sunny', 'cloudy', 'overcast')
        """
        self.weather_type = weather_type
    
    def set_season_factor(self, season_factor):
        """设置季节因子
        
        Args:
            season_factor: 季节 ('spring', 'summer', 'autumn', 'winter')
        """
        self.season_factor = season_factor
    
    def set_cloud_cover(self, cloud_cover):
        """设置云层覆盖度
        
        Args:
            cloud_cover: 云层覆盖度 (0.0-1.0)
        """
        self.cloud_cover = max(0.0, min(1.0, cloud_cover))
    
    def generate_data(self, index, network_model):
        """生成光伏数据
        
        Args:
            index: 光伏设备索引
            network_model: 网络模型
            
        Returns:
            dict: 光伏数据字典
        """
        return self.generate_pv_data(index, network_model)
    
    def generate_pv_data(self, index, network_model):
        """生成光伏数据
        
        Args:
            index: 光伏设备索引
            network_model: 网络模型
            
        Returns:
            dict: 光伏数据字典
        """
        if not self.is_running or not network_model or not hasattr(network_model, 'net'):
            return {}
            
        pv_data = {}
        
        try:
            sgen = network_model.net.sgen.loc[index]
            
            # 获取当前时间
            from datetime import datetime
            current_hour = datetime.now().hour
            
            # 基础光伏功率曲线（MW，晴天模式下的标准1MW光伏电站输出）
            base_pv_curve = [
                0.0, 0.0, 0.0, 0.0, 0.0, 0.05,   # 0-5时
                0.2, 0.4, 0.6, 0.8, 0.95, 1.0,   # 6-11时
                1.0, 0.9, 0.8, 0.6, 0.4, 0.2,   # 12-17时
                0.05, 0.0, 0.0, 0.0, 0.0, 0.0   # 18-23时
            ]
            
            # 根据天气类型调整
            weather_factor = 1.0
            if self.weather_type == 'cloudy':
                weather_factor = 0.6 + np.random.uniform(-0.1, 0.1)
            elif self.weather_type == 'overcast':
                weather_factor = 0.3 + np.random.uniform(-0.05, 0.05)
            
            # 根据季节调整
            season_factors = {
                'spring': 0.8,
                'summer': 1.0,
                'autumn': 0.7,
                'winter': 0.5
            }
            season_multiplier = season_factors.get(self.season_factor, 1.0)
            
            # 云层影响
            cloud_factor = 1.0 - (self.cloud_cover * 0.5)
            
            # 获取基础功率（当前时段的标准输出）
            base_power_mw = base_pv_curve[current_hour]
            
            # 应用各种调整因子
            adjusted_power = base_power_mw * weather_factor * season_multiplier * cloud_factor
            
            # 添加随机变化
            variation_factor = self.variation / 100.0
            random_factor = np.random.uniform(1.0 - variation_factor, 1.0 + variation_factor)
            adjusted_power *= random_factor
            
            # 确保非负
            adjusted_power = max(0.0, adjusted_power)
            
            # 计算新的光伏值（无功功率设为0）
            new_p = adjusted_power
            new_q = 0.0
            
            pv_data[index] = {
                'p_mw': new_p,
                'q_mvar': new_q,
            }
            
        except (KeyError, AttributeError):
            pass
            
        return pv_data
    
    def generate_daily_pv_profile(self, network_model):
        """生成日光伏曲线数据
        
        Args:
            network_model: 网络模型
            
        Returns:
            dict: 日光伏曲线数据
        """
        if not network_model or not hasattr(network_model, 'net'):
            return {}
            
        pv_profiles = {}
        
        if not network_model.net.sgen.empty:
            for idx, sgen in network_model.net.sgen.iterrows():
                pv_data = self.generate_data(idx, network_model)
                if idx in pv_data:
                    pv_profiles[idx] = pv_data[idx]
                    
        return pv_profiles


class DataGeneratorManager:
    """数据生成器管理类 - 统一管理负载和光伏数据生成"""
    
    def __init__(self):
        self.load_generator = LoadDataGenerator()
        self.pv_generator = PVDataGenerator()
        self.generators = {
            'load': self.load_generator,
            'sgen': self.pv_generator
        }
    
    def set_device_type(self, device_type, **kwargs):
        """设置设备类型参数
        
        Args:
            device_type: 设备类型 ('load', 'sgen')
            **kwargs: 设备特定参数
        """
        if device_type == 'load' and 'load_type' in kwargs:
            self.load_generator.set_load_type(kwargs['load_type'])
        elif device_type == 'sgen':
            if 'weather_type' in kwargs:
                self.pv_generator.set_weather_type(kwargs['weather_type'])
            if 'season_factor' in kwargs:
                self.pv_generator.set_season_factor(kwargs['season_factor'])
            if 'cloud_cover' in kwargs:
                self.pv_generator.set_cloud_cover(kwargs['cloud_cover'])
    
    def generate_device_data(self, device_type, index, network_model):
        """生成指定设备类型的数据
        
        Args:
            device_type: 设备类型 ('load', 'sgen')
            index: 设备索引
            network_model: 网络模型
            
        Returns:
            dict: 生成的数据字典
        """
        if device_type == 'load':
            return self.load_generator.generate_load_data(index, network_model)
        elif device_type == 'sgen':
            return self.pv_generator.generate_data(index, network_model)
        return {}
    
    def start_generation(self, device_type=None):
        """开始数据生成
        
        Args:
            device_type: 设备类型，如果为None则启动所有生成器
        """
        if device_type is None:
            for generator in self.generators.values():
                generator.start_generation()
        elif device_type in self.generators:
            self.generators[device_type].start_generation()
    
    def stop_generation(self, device_type=None):
        """停止数据生成
        
        Args:
            device_type: 设备类型，如果为None则停止所有生成器
        """
        if device_type is None:
            for generator in self.generators.values():
                generator.stop_generation()
        elif device_type in self.generators:
            self.generators[device_type].stop_generation()
    
    def set_interval(self, interval, device_type=None):
        """设置生成间隔
        
        Args:
            interval: 生成间隔（秒）
            device_type: 设备类型，如果为None则应用到所有生成器
        """
        if device_type is None:
            for generator in self.generators.values():
                generator.set_interval(interval)
        elif device_type in self.generators:
            self.generators[device_type].set_interval(interval)
    
    def set_variation(self, variation, device_type=None):
        """设置变化幅度
        
        Args:
            variation: 变化幅度百分比（5-50%）
            device_type: 设备类型，如果为None则应用到所有生成器
        """
        if device_type is None:
            for generator in self.generators.values():
                generator.set_variation(variation)
        elif device_type in self.generators:
            self.generators[device_type].set_variation(variation)