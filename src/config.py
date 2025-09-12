#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件，统一管理资源路径和其他配置
兼容PyInstaller的one_dir打包方式
"""

import os
import sys

# 资源目录配置
ASSETS_DIR = "assets"

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