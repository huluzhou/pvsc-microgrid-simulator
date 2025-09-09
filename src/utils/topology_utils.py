#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
topology.json工具类，用于处理网络拓扑结构的导入导出
格式与topology.json保持一致
"""

import json
import os
from typing import Dict, List, Any, Optional
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QPointF
from components.network_items import BusItem, LineItem, TransformerItem, LoadItem, StorageItem, StaticGeneratorItem, ExternalGridItem, MeterItem, ChargerItem

class TopologyManager:
    """拓扑结构管理器，处理network_item的导入导出"""
    
    def __init__(self):
        # 组件类型映射
        self.type_mapping = {
            'Bus': BusItem,
            'Line': LineItem,
            'Transformer': TransformerItem,
            'Load': LoadItem,
            'Storage': StorageItem,
            'Static Generator': StaticGeneratorItem,
            'External Grid': ExternalGridItem,
            'Measurement': MeterItem,
            'Charger': ChargerItem
        }
        
        # 反向映射
        self.reverse_mapping = {
            'bus': 'Bus',
            'line': 'Line',
            'transformer': 'Transformer',
            'load': 'Load',
            'storage': 'Storage',
            'static_generator': 'Static Generator',
            'external_grid': 'External Grid',
            'measurement': 'Measurement',
            'charger': 'Charger'
        }
    
    def export_topology(self, scene, parent_window=None) -> bool:
        """导出整个场景的拓扑结构到JSON文件"""
        try:
            # 获取所有网络组件
            network_items = []
            for item in scene.items():
                if hasattr(item, 'component_type'):
                    network_items.append(item)
            
            if not network_items:
                if parent_window and hasattr(parent_window, 'show_message'):
                    print("场景中没有网络组件")
                return False
            
            # 准备数据
            topology_data = self._prepare_topology_data(network_items)
            
            # 保存到文件
            if parent_window is None:
                # 如果没有父窗口，使用默认文件名
                file_path = "topology.json"
            else:
                # 使用文件对话框
                try:
                    file_path, _ = QFileDialog.getSaveFileName(
                        parent_window,
                        "导出拓扑结构",
                        "topology.json",
                        "JSON文件 (*.json)"
                    )
                except:
                    file_path = "topology.json"
            
            if not file_path:
                return False
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(topology_data, f, ensure_ascii=False, indent=2)
            
            print(f"拓扑结构已导出到: {file_path}")
            return True
            
        except Exception as e:
            if parent_window and hasattr(parent_window, 'show_message'):
                print(f"导出失败: {str(e)}")
            return False
    
    def import_topology(self, scene, parent_window=None) -> bool:
        """从JSON文件导入拓扑结构到场景"""
        try:
            if parent_window is None:
                # 如果没有父窗口，使用默认文件名
                file_path = "topology.json"
                if not os.path.exists(file_path):
                    print("未找到topology.json文件")
                    return False
            else:
                # 使用文件对话框
                try:
                    file_path, _ = QFileDialog.getOpenFileName(
                        parent_window,
                        "导入拓扑结构",
                        "",
                        "JSON文件 (*.json)"
                    )
                except:
                    file_path = "topology.json"
            
            if not file_path or not os.path.exists(file_path):
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                topology_data = json.load(f)
            
            # 清空当前场景
            if hasattr(scene, 'clear'):
                scene.clear()
                
            # 重新绘制网格背景（如果场景支持）
            if hasattr(scene, 'parent') and scene.parent():
                canvas = scene.parent()
                if hasattr(canvas, 'draw_grid'):
                    canvas.draw_grid()
                elif hasattr(canvas, 'parent') and canvas.parent():
                    # 尝试从主窗口获取NetworkCanvas引用
                    main_window = canvas.parent()
                    if hasattr(main_window, 'canvas') and hasattr(main_window.canvas, 'draw_grid'):
                        main_window.canvas.draw_grid()
            
            # 导入组件
            self._import_components(scene, topology_data)
            
            print(f"拓扑结构已从 {file_path} 导入")
            return True
            
        except Exception as e:
            if parent_window and hasattr(parent_window, 'show_message'):
                print(f"导入失败: {str(e)}")
            return False
    
    def _prepare_topology_data(self, items: List[Any]) -> Dict[str, List[Dict[str, Any]]]:
        """准备拓扑数据"""
        topology_data = {}
        
        for item in items:
            item_type = self._get_topology_type(item.component_type)
            if item_type not in topology_data:
                topology_data[item_type] = []
            
            # 获取组件数据
            item_data = item.properties 
            topology_data[item_type].append(item_data)
        
        return topology_data
        
    def _import_components(self, scene, topology_data: Dict[str, List[Dict[str, Any]]]):
        """导入组件到场景"""
        # 创建索引映射
        index_mapping = {}
        created_items = {}  # 存储创建的所有组件
        
        # 先处理母线，建立索引映射
        if 'Bus' in topology_data:
            for bus_data in topology_data['Bus']:
                old_index = bus_data['index']
                # 使用正确的构造函数参数
                pos = bus_data.get('geodata', [100 + old_index * 100, 100])
                bus_item = BusItem(QPointF(pos[0], pos[1]))
                bus_item.component_index = old_index
                bus_item.properties['index'] = old_index
                
                # 更新属性
                for key, value in bus_data.items():
                    if key != 'index':
                        bus_item.properties[key] = value
                
                scene.addItem(bus_item)
                index_mapping[old_index] = bus_item.component_index
                created_items[('Bus', old_index)] = bus_item
                
                # 连接信号到画布
                if hasattr(scene, 'parent') and scene.parent():
                    canvas = scene.parent()
                    if hasattr(canvas, 'handle_item_selected'):
                        bus_item.signals.itemSelected.connect(canvas.handle_item_selected)
        
        # 处理其他组件
        for item_type, items_data in topology_data.items():
            if item_type == 'Bus':
                continue
            
            for item_data in items_data:
                if item_type in self.type_mapping:
                    item_class = self.type_mapping[item_type]
                    # 使用正确的构造函数参数
                    pos = item_data.get('geodata', [200 + item_data['index'] * 50, 200])
                    item = item_class(QPointF(pos[0], pos[1]))
                    item.component_index = item_data['index']
                    item.properties['index'] = item_data['index']
                    
                    # 更新属性 - 保持连接属性的原始索引值
                    for key, value in item_data.items():
                        if key != 'index':
                            item.properties[key] = value
                    
                    scene.addItem(item)
                    created_items[(item_type, item_data['index'])] = item
                    
                    # 连接信号到画布
                    if hasattr(scene, 'parent') and scene.parent():
                        canvas = scene.parent()
                        if hasattr(canvas, 'handle_item_selected'):
                            item.signals.itemSelected.connect(canvas.handle_item_selected)
        
        # 恢复组件间的连接关系
        self._restore_connections(scene, topology_data, created_items, index_mapping)
    
    def _restore_connections(self, scene, topology_data: Dict[str, List[Dict[str, Any]]], created_items: Dict, index_mapping: Dict[int, int]):
        """恢复组件间的连接关系"""
        if not hasattr(scene, 'parent') or not scene.parent():
            return
            
        canvas = scene.parent()
        if not hasattr(canvas, 'connect_items'):
            return
        
        # 遍历所有组件，根据连接属性恢复连接
        for item_type, items_data in topology_data.items():
            for item_data in items_data:
                current_index = item_data['index']
                item_key = (item_type, current_index)
                
                if item_key not in created_items:
                    continue
                    
                item = created_items[item_key]
                
                # 根据组件类型查找连接关系
                if item_type == 'Line':
                    from_bus = item_data.get('from_bus')
                    to_bus = item_data.get('to_bus')
                    if from_bus is not None and to_bus is not None:
                        try:
                            from_bus_int = int(from_bus)
                            to_bus_int = int(to_bus)
                            
                            bus1_key = ('Bus', from_bus_int)
                            bus2_key = ('Bus', to_bus_int)
                            
                            if bus1_key in created_items and bus2_key in created_items:
                                canvas.connect_items(created_items[bus1_key], item)
                                canvas.connect_items(created_items[bus2_key], item)
                        except (ValueError, TypeError):
                            pass
                            
                elif item_type == 'Transformer':
                    hv_bus = item_data.get('hv_bus')
                    lv_bus = item_data.get('lv_bus')
                    if hv_bus is not None and lv_bus is not None:
                        try:
                            hv_bus_int = int(hv_bus)
                            lv_bus_int = int(lv_bus)
                            
                            hv_key = ('Bus', hv_bus_int)
                            lv_key = ('Bus', lv_bus_int)
                            
                            if hv_key in created_items and lv_key in created_items:
                                canvas.connect_items(created_items[hv_key], item)
                                canvas.connect_items(created_items[lv_key], item)
                        except (ValueError, TypeError):
                            pass
                            
                elif item_type in ['Load', 'Generator', 'Storage', 'Static Generator', 'Charger', 'External Grid']:
                    bus = item_data.get('bus')
                    if bus is not None:
                        try:
                            bus_int = int(bus)
                            bus_key = ('Bus', bus_int)
                            
                            if bus_key in created_items:
                                canvas.connect_items(created_items[bus_key], item)
                        except (ValueError, TypeError):
                            pass
                            
                elif item_type == 'Measurement':
                    # 电表连接到具体的设备（负载、线路等）
                    element = item_data.get('element')
                    element_type = item_data.get('element_type')
                    
                    if element is not None and element_type is not None:
                        try:
                            element_int = int(element)
                            
                            # 根据element_type确定目标组件类型
                            target_type_map = {
                                'load': 'Load',
                                'line': 'Line',
                                'transformer': 'Transformer',
                                'bus': 'Bus',
                                'generator': 'Generator',
                                'storage': 'Storage',
                                'static_generator': 'Static_Generator',
                                'external_grid': 'External_Grid'
                            }
                            
                            target_type = target_type_map.get(element_type)
                            if target_type:
                                target_key = (target_type, element_int)
                                
                                if target_key in created_items:
                                    # 电表连接到目标设备
                                    canvas.connect_items(created_items[target_key], item)
                        except (ValueError, TypeError):
                            pass
    
    def _update_connection_indices(self, item, index_mapping: Dict[int, int]):
        """更新组件连接属性中的索引映射"""
        pass  # 不再更新连接属性中的索引，保持原始值
    
    def _get_topology_type(self, component_type: str) -> str:
        """获取拓扑类型"""
        type_map = {
            'bus': 'Bus',
            'line': 'Line',
            'transformer': 'Transformer',
            'load': 'Load',
            'storage': 'Storage',
            'static_generator': 'Static_Generator',
            'external_grid': 'External_Grid',
            'meter': 'Measurement',
            'charger': 'Charger'
        }
        return type_map.get(component_type, component_type)
    
    def _get_chinese_type(self, component_type: str) -> str:
        """获取中文类型名称"""
        type_map = {
            'bus': '母线',
            'line': '线路',
            'transformer': '变压器',
            'load': '负载',
            'storage': '储能',
            'static_generator': '光伏',
            'external_grid': '外部电网',
            'measurement': '电表',
            'charger': '充电站'
        }
        return type_map.get(component_type, component_type)
    
    def _clean_properties(self, properties: Dict[str, Any], component_type: str) -> Dict[str, Any]:
        """清理不需要的字段"""
        # 定义需要清理的字段
        fields_to_clean = [
            'ip_address', 'port', 'device_id', 'protocol', 'update_rate',
            'timeout', 'retry_count', 'communication_status', 'last_update',
            'connection_string', 'database_name', 'username', 'password',
            'api_key', 'endpoint', 'webhook_url', 'notification_settings',
            'display_settings', 'ui_preferences', 'custom_colors',
            'animation_enabled', 'tooltip_enabled', 'grid_snap',
            'auto_save', 'backup_enabled'
        ]
        
        cleaned = {}
        for key, value in properties.items():
            if key not in fields_to_clean:
                cleaned[key] = value
        
        return cleaned