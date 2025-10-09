# -*- coding: utf-8 -*-

"""
全局变量存储模块
用于避免组件间的循环导入问题
"""

# 全局网络模型实例
network_model = None

# 全局网络项字典，按组件类型和索引分类存储，使用嵌套字典结构
network_items = {
    'bus': {},
    'line': {},
    'transformer': {},
    'load': {},
    'storage': {},
    'charger': {},
    'external_grid': {},
    'static_generator': {},
    'meter': {}
}