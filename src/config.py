#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件，统一管理资源路径和其他配置
"""

import os

# 资源目录配置
ASSETS_DIR = "assets"

# 获取当前工作目录
WORKING_DIR = os.getcwd()

# 资源路径
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
    获取资源的绝对路径
    
    Args:
        resource_name: 资源名称或相对路径
    
    Returns:
        str: 资源的绝对路径
    """
    if resource_name in RESOURCES:
        return os.path.join(WORKING_DIR, RESOURCES[resource_name])
    else:
        return os.path.join(WORKING_DIR, ASSETS_DIR, resource_name)

def get_assets_directory():
    """
    获取资源目录的绝对路径
    
    Returns:
        str: assets目录的绝对路径
    """
    return os.path.join(WORKING_DIR, ASSETS_DIR)