#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理器模块
实现统一的配置管理功能，支持不同配置源和格式
"""

import os
import json
import yaml
import configparser
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging


class IConfigStrategy(ABC):
    """配置加载策略接口"""
    
    @abstractmethod
    def load(self, config_path: str) -> Dict[str, Any]:
        """
        加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        pass
    
    @abstractmethod
    def save(self, config_path: str, config_data: Dict[str, Any]) -> None:
        """
        保存配置
        
        Args:
            config_path: 配置文件路径
            config_data: 配置数据
        """
        pass


class JsonConfigStrategy(IConfigStrategy):
    """JSON配置加载策略"""
    
    def load(self, config_path: str) -> Dict[str, Any]:
        """
        加载JSON配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON解析错误
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save(self, config_path: str, config_data: Dict[str, Any]) -> None:
        """
        保存JSON配置文件
        
        Args:
            config_path: 配置文件路径
            config_data: 配置数据
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)


class YamlConfigStrategy(IConfigStrategy):
    """YAML配置加载策略"""
    
    def load(self, config_path: str) -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 文件不存在
            yaml.YAMLError: YAML解析错误
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def save(self, config_path: str, config_data: Dict[str, Any]) -> None:
        """
        保存YAML配置文件
        
        Args:
            config_path: 配置文件路径
            config_data: 配置数据
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)


class IniConfigStrategy(IConfigStrategy):
    """INI配置加载策略"""
    
    def load(self, config_path: str) -> Dict[str, Any]:
        """
        加载INI配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        result = {}
        for section in config.sections():
            result[section] = dict(config[section])
        
        return result
    
    def save(self, config_path: str, config_data: Dict[str, Any]) -> None:
        """
        保存INI配置文件
        
        Args:
            config_path: 配置文件路径
            config_data: 配置数据
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        config = configparser.ConfigParser()
        for section, options in config_data.items():
            config[section] = options
        
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)


class ConfigManager:
    """
    配置管理器
    使用单例模式，集中管理系统配置
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """
        初始化配置管理器
        """
        self._config: Dict[str, Any] = {}
        self._loaded_files: List[str] = []
        self._strategies: Dict[str, IConfigStrategy] = {
            '.json': JsonConfigStrategy(),
            '.yaml': YamlConfigStrategy(),
            '.yml': YamlConfigStrategy(),
            '.ini': IniConfigStrategy()
        }
        self._logger = logging.getLogger(__name__)
        self._base_config_path: Optional[str] = None
    
    def set_base_config_path(self, path: str) -> None:
        """
        设置基础配置路径
        
        Args:
            path: 基础配置路径
        """
        self._base_config_path = path
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件格式
        """
        # 如果提供的是相对路径且设置了基础路径，则使用基础路径
        if not os.path.isabs(config_path) and self._base_config_path:
            config_path = os.path.join(self._base_config_path, config_path)
        
        # 获取文件扩展名
        _, ext = os.path.splitext(config_path)
        ext = ext.lower()
        
        # 检查是否支持该格式
        if ext not in self._strategies:
            raise ValueError(f"不支持的配置文件格式: {ext}")
        
        # 获取对应的策略
        strategy = self._strategies[ext]
        
        try:
            # 加载配置
            config_data = strategy.load(config_path)
            
            # 合并配置
            self._merge_config(config_data)
            
            # 记录已加载的文件
            if config_path not in self._loaded_files:
                self._loaded_files.append(config_path)
            
            self._logger.info(f"成功加载配置文件: {config_path}")
            return config_data
        except Exception as e:
            self._logger.error(f"加载配置文件失败: {config_path}, 错误: {str(e)}")
            raise
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        合并配置到全局配置
        
        Args:
            new_config: 新的配置数据
        """
        for key, value in new_config.items():
            if key in self._config and isinstance(self._config[key], dict) and isinstance(value, dict):
                # 递归合并字典
                self._deep_merge(self._config[key], value)
            else:
                # 直接替换
                self._config[key] = value
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        深度合并两个字典
        
        Args:
            target: 目标字典
            source: 源字典
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        支持点号分隔的嵌套键，如 "database.host"
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        支持点号分隔的嵌套键，如 "database.host"
        
        Args:
            key: 配置键名
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        # 遍历除最后一个键外的所有键
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            所有配置的字典
        """
        return self._config.copy()
    
    def save_config(self, config_path: str, config_data: Optional[Dict[str, Any]] = None) -> None:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径
            config_data: 要保存的配置数据，如果为None则保存当前所有配置
        """
        # 如果提供的是相对路径且设置了基础路径，则使用基础路径
        if not os.path.isabs(config_path) and self._base_config_path:
            config_path = os.path.join(self._base_config_path, config_path)
        
        # 获取文件扩展名
        _, ext = os.path.splitext(config_path)
        ext = ext.lower()
        
        # 检查是否支持该格式
        if ext not in self._strategies:
            raise ValueError(f"不支持的配置文件格式: {ext}")
        
        # 获取对应的策略
        strategy = self._strategies[ext]
        
        # 保存配置
        try:
            data_to_save = config_data if config_data is not None else self._config
            strategy.save(config_path, data_to_save)
            self._logger.info(f"成功保存配置文件: {config_path}")
        except Exception as e:
            self._logger.error(f"保存配置文件失败: {config_path}, 错误: {str(e)}")
            raise
    
    def validate_config(self, schema: Dict[str, Any]) -> List[str]:
        """
        验证配置是否符合模式
        
        Args:
            schema: 配置模式定义
            
        Returns:
            验证错误列表，为空表示验证通过
        """
        errors = []
        self._validate_schema(self._config, schema, [], errors)
        return errors
    
    def _validate_schema(self, config: Dict[str, Any], schema: Dict[str, Any], 
                        path: List[str], errors: List[str]) -> None:
        """
        递归验证配置模式
        
        Args:
            config: 配置数据
            schema: 模式定义
            path: 当前路径
            errors: 错误列表
        """
        for key, expected_type in schema.items():
            current_path = path + [key]
            path_str = '.'.join(current_path)
            
            if key not in config:
                errors.append(f"缺少必需的配置项: {path_str}")
                continue
            
            actual_value = config[key]
            
            # 如果期望类型是字典，则递归验证
            if isinstance(expected_type, dict):
                if not isinstance(actual_value, dict):
                    errors.append(f"配置项类型错误: {path_str} 应为字典类型")
                else:
                    self._validate_schema(actual_value, expected_type, current_path, errors)
            # 如果期望类型是类型对象，则检查类型
            elif isinstance(expected_type, type):
                if not isinstance(actual_value, expected_type):
                    errors.append(
                        f"配置项类型错误: {path_str} 应为 {expected_type.__name__} 类型，"  
                        f"实际为 {type(actual_value).__name__} 类型"
                    )


# 创建全局配置管理器实例
config_manager = ConfigManager()