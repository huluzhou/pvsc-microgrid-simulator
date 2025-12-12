#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件，统一管理资源路径和其他配置
兼容PyInstaller的one_dir打包方式
"""

import os
import sys
import functools

# 资源目录配置
ASSETS_DIR = "assets"

# 条件编译宏定义
# 可以在这里定义全局的条件编译标志
# 使用方式类似C语言的#define
# 例如：FEATURE_SIMULATION = True表示启用仿真功能
#       FEATURE_MODBUS = False表示禁用Modbus功能

# 默认配置值
_DEFAULT_FEATURE_SIMULATION = True  # 仿真功能
_DEFAULT_FEATURE_MODBUS = True      # Modbus通信功能
_DEFAULT_FEATURE_REPORT = True      # 报告生成功能
_DEFAULT_FEATURE_EXPORT = True      # 数据导出功能
_DEFAULT_DEBUG_MODE = False          # 调试模式
_DEFAULT_VERBOSE_LOGGING = True     # 详细日志

# 实际使用的配置值，将从TOML文件加载
FEATURE_SIMULATION = _DEFAULT_FEATURE_SIMULATION
FEATURE_MODBUS = _DEFAULT_FEATURE_MODBUS
FEATURE_REPORT = _DEFAULT_FEATURE_REPORT
FEATURE_EXPORT = _DEFAULT_FEATURE_EXPORT
DEBUG_MODE = _DEFAULT_DEBUG_MODE
VERBOSE_LOGGING = _DEFAULT_VERBOSE_LOGGING



# 默认功率单位配置
_DEFAULT_POWER_UNIT = 1.0

# 实际使用的功率单位配置，将从TOML文件加载
POWER_UNIT = _DEFAULT_POWER_UNIT

# 尝试从TOML配置文件加载配置
import os
import sys

# 检查Python版本，选择合适的TOML库
if sys.version_info >= (3, 11):
    import tomllib
    import tomli_w
else:
    try:
        import tomli as tomllib
        import tomli_w
    except ImportError:
        # 如果没有安装tomli，使用默认配置
        tomllib = None
        tomli_w = None

# 获取配置文件路径
if hasattr(sys, 'frozen'):
    # 打包后环境
    config_dir = os.path.dirname(sys.executable)
else:
    # 开发环境
    config_dir = os.path.dirname(os.path.abspath(__file__))

# 创建配置文件路径
config_file_path = os.path.join(config_dir, 'app_config.toml')

# 默认配置
DEFAULT_CONFIG = {
    'features': {
        'simulation': _DEFAULT_FEATURE_SIMULATION,
        'modbus': _DEFAULT_FEATURE_MODBUS,
        'report': _DEFAULT_FEATURE_REPORT,
        'export': _DEFAULT_FEATURE_EXPORT
    },
    'debug': {
        'mode': _DEFAULT_DEBUG_MODE,
        'verbose_logging': _DEFAULT_VERBOSE_LOGGING
    },
    'power': {
        'unit': _DEFAULT_POWER_UNIT
    }
}

# 读取配置文件
if tomllib and os.path.exists(config_file_path):
    try:
        with open(config_file_path, 'rb') as f:
            app_config = tomllib.load(f)
        
        # 更新功能模块配置
        if 'features' in app_config:
            if 'simulation' in app_config['features']:
                FEATURE_SIMULATION = app_config['features']['simulation']
            if 'modbus' in app_config['features']:
                FEATURE_MODBUS = app_config['features']['modbus']
            if 'report' in app_config['features']:
                FEATURE_REPORT = app_config['features']['report']
            if 'export' in app_config['features']:
                FEATURE_EXPORT = app_config['features']['export']
        
        # 更新调试模式配置
        if 'debug' in app_config:
            if 'mode' in app_config['debug']:
                DEBUG_MODE = app_config['debug']['mode']
            if 'verbose_logging' in app_config['debug']:
                VERBOSE_LOGGING = app_config['debug']['verbose_logging']
        
        # 更新功率单位配置
        if 'power' in app_config and 'unit' in app_config['power']:
            POWER_UNIT = app_config['power']['unit']
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        # 使用当前配置并创建配置文件
        if tomli_w:
            try:
                # 使用当前配置创建配置文件
                current_config = {
                    'features': {
                        'simulation': FEATURE_SIMULATION,
                        'modbus': FEATURE_MODBUS,
                        'report': FEATURE_REPORT,
                        'export': FEATURE_EXPORT
                    },
                    'debug': {
                        'mode': DEBUG_MODE,
                        'verbose_logging': VERBOSE_LOGGING
                    },
                    'power': {
                        'unit': POWER_UNIT
                    }
                }
                with open(config_file_path, 'wb') as f:
                    tomli_w.dump(current_config, f)
            except Exception as e:
                print(f"创建配置文件失败: {e}")
else:
    # 配置文件不存在，使用当前配置并创建配置文件
    if tomli_w:
        try:
            # 使用当前配置创建配置文件
            current_config = {
                'features': {
                    'simulation': FEATURE_SIMULATION,
                    'modbus': FEATURE_MODBUS,
                    'report': FEATURE_REPORT,
                    'export': FEATURE_EXPORT
                },
                'debug': {
                    'mode': DEBUG_MODE,
                    'verbose_logging': VERBOSE_LOGGING
                },
                'power': {
                    'unit': POWER_UNIT
                }
            }
            with open(config_file_path, 'wb') as f:
                tomli_w.dump(current_config, f)
        except Exception as e:
            print(f"创建配置文件失败: {e}")


# 条件编译辅助函数

def is_feature_enabled(feature_flag):
    """
    检查指定功能是否启用
    
    Args:
        feature_flag: 功能标志变量
        
    Returns:
        bool: True - 功能已启用, False - 功能已禁用
    """
    return bool(feature_flag)

# 条件执行装饰器
def conditional_compile(condition):
    """
    条件编译装饰器，根据条件决定是否执行函数
    
    使用方式:
        @conditional_compile(FEATURE_SIMULATION)
        def simulation_function():
            # 只有当FEATURE_SIMULATION为True时，才会执行此函数
    
    Args:
        condition: 条件表达式，为True时执行被装饰函数
        
    Returns:
        function: 装饰后的函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if condition:
                return func(*args, **kwargs)
            # 功能禁用时，返回None或根据需要返回其他默认值
            return None
        return wrapper
    return decorator

# 条件导入辅助函数
def import_if_enabled(module_name, condition):
    """
    条件导入模块
    
    Args:
        module_name: 模块名称字符串
        condition: 条件表达式，为True时导入模块
        
    Returns:
        module or None: 导入的模块或None
    """
    if condition:
        try:
            return __import__(module_name)
        except ImportError:
            # 如果模块不存在，返回None
            return None
    return None


def _get_base_path():
    """
    获取基础路径，兼容PyInstaller打包和非打包环境
    
    Returns:
        str: 基础路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后的路径
        return sys._MEIPASS
    else:
        # 开发环境路径
        return os.path.dirname(os.path.abspath(__file__))

# 获取基础路径
BASE_DIR = _get_base_path()

# 资源路径定义（相对于基础路径）
RESOURCES = {
    'bus': os.path.join(ASSETS_DIR, 'bus.svg'),
    'line': os.path.join(ASSETS_DIR, 'line.svg'),
    'transformer': os.path.join(ASSETS_DIR, 'transformer.svg'),
    'static_generator': os.path.join(ASSETS_DIR, 'static_generator.svg'),
    'load': os.path.join(ASSETS_DIR, 'load.svg'),
    'storage': os.path.join(ASSETS_DIR, 'storage.svg'),
    'charger': os.path.join(ASSETS_DIR, 'charger.svg'),
    'external_grid': os.path.join(ASSETS_DIR, 'external_grid.svg'),
    'meter': os.path.join(ASSETS_DIR, 'meter.svg'),
    'switch': os.path.join(ASSETS_DIR, 'switch.svg'),
    'shunt': os.path.join(ASSETS_DIR, 'shunt.svg'),
    'sectioning_point': os.path.join(ASSETS_DIR, 'sectioning_point.svg'),
}

def get_resource_path(resource_name):
    """
    获取资源的绝对路径，兼容PyInstaller打包
    
    Args:
        resource_name: 资源名称或相对路径
    
    Returns:
        str: 资源的绝对路径
    """
    if resource_name in RESOURCES:
        return os.path.join(BASE_DIR, RESOURCES[resource_name])
    else:
        return os.path.join(BASE_DIR, ASSETS_DIR, resource_name)

def get_assets_directory():
    """
    获取资源目录的绝对路径，兼容PyInstaller打包
    
    Returns:
        str: assets目录的绝对路径
    """
    return os.path.join(BASE_DIR, ASSETS_DIR)

# 获取当前工作目录（用于非资源文件）
WORKING_DIR = os.getcwd()