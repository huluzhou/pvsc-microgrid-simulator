#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os

# 读取拓扑文件
topology_file = 'd:/pp_tool/topology_test.json'

with open(topology_file, 'r', encoding='utf-8') as f:
    topology_data = json.load(f)

# 在根上添加connections字段
connections = []

# 创建set记录和开关连接的母线
switched_buses = set()

if 'Switch' in topology_data:
    for switch in topology_data['Switch']:
        # 获取开关信息
        switch_index = switch['index']
        switch_name = f"Switch_{switch_index}"
        
        # 获取母线信息
        bus_index = switch['bus']
        bus_name = f"Bus_{bus_index}"
        
        # 将母线添加到set中
        switched_buses.add(bus_index)
        
        # 生成母线侧连接
        bus_connection = {
            "item1": bus_name,
            "item2": switch_name
        }
        connections.append(bus_connection)
        
        # 根据et判断开关另一端的设备类型
        et = switch['et']
        element_index = switch['element']
        
        # 确定设备类型和名称
        device_type = ""
        if et == 'b':
            device_type = "Bus"
        elif et == 'l':
            device_type = "Line"
        elif et == 't':
            device_type = "Transformer"
        elif et == 't3':
            device_type = "Transformer"
        
        if device_type:
            device_name = f"{device_type}_{element_index}"
            # 生成设备侧连接
            device_connection = {
                "item1": device_name,
                "item2": switch_name
            }
            connections.append(device_connection)

# 遍历变压器
if 'Transformer' in topology_data:
    for transformer in topology_data['Transformer']:
        # 获取变压器信息
        transformer_index = transformer['index']
        transformer_name = f"Transformer_{transformer_index}"
        
        # 获取高压侧母线信息
        hv_bus_index = transformer['hv_bus']
        hv_bus_name = f"Bus_{hv_bus_index}"
        
        # 获取低压侧母线信息
        lv_bus_index = transformer['lv_bus']
        lv_bus_name = f"Bus_{lv_bus_index}"
        
        # 生成高压侧连接（如果母线不在switched_buses中）
        if hv_bus_index not in switched_buses:
            hv_connection = {
                "item1": hv_bus_name,
                "item2": transformer_name
            }
            connections.append(hv_connection)
        
        # 生成低压侧连接（如果母线不在switched_buses中）
        if lv_bus_index not in switched_buses:
            lv_connection = {
                "item1": lv_bus_name,
                "item2": transformer_name
            }
            connections.append(lv_connection)

# 遍历线路
if 'Line' in topology_data:
    for line in topology_data['Line']:
        # 获取线路信息
        line_index = line['index']
        line_name = f"Line_{line_index}"
        
        # 获取起始侧母线信息
        from_bus_index = line['from_bus']
        from_bus_name = f"Bus_{from_bus_index}"
        
        # 获取终止侧母线信息
        to_bus_index = line['to_bus']
        to_bus_name = f"Bus_{to_bus_index}"
        
        # 生成起始侧连接（如果母线不在switched_buses中）
        if from_bus_index not in switched_buses:
            from_connection = {
                "item1": from_bus_name,
                "item2": line_name
            }
            connections.append(from_connection)
        
        # 生成终止侧连接（如果母线不在switched_buses中）
        if to_bus_index not in switched_buses:
            to_connection = {
                "item1": to_bus_name,
                "item2": line_name
            }
            connections.append(to_connection)

# 遍历负载、光伏、储能、充电桩
# 定义需要处理的设备类型映射：拓扑类型 -> 显示名称
device_types = {
    'Load': 'Load',
    'Static_Generator': 'Static_Generator',
    'Storage': 'Storage',
    'Charger': 'Charger',
    'External_Grid': 'External_Grid'
}

for device_type, display_name in device_types.items():
    if device_type in topology_data:
        for device in topology_data[device_type]:
            # 获取设备信息
            device_index = device['index']
            device_name = f"{display_name}_{device_index}"
            
            # 获取母线信息
            bus_index = device['bus']
            bus_name = f"Bus_{bus_index}"
            
            # 生成连接关系
            connection = {
                "item1": bus_name,
                "item2": device_name
            }
            connections.append(connection)

# 遍历电表
# 定义element_type到设备类型的映射
element_type_mapping = {
    'bus': 'Bus',
    'line': 'Line',
    'trafo': 'Transformer',
    'storage': 'Storage',
    'load': 'Load',
    'sgen': 'Static_Generator',
    'charger': 'Charger',
    'ext_grid': 'External_Grid'
}

if 'Measurement' in topology_data:
    for meter in topology_data['Measurement']:
        # 获取电表信息
        meter_index = meter['index']
        meter_name = f"Measurement_{meter_index}"
        
        # 获取测量对象信息
        element_type = meter['element_type']
        element_index = meter['element']
        
        # 映射element_type到设备类型
        if element_type in element_type_mapping:
            device_type = element_type_mapping[element_type]
            device_name = f"{device_type}_{element_index}"
            
            # 生成连接关系
            connection = {
                "item1": device_name,
                "item2": meter_name
            }
            connections.append(connection)

# 添加connections字段到拓扑数据
topology_data['connections'] = connections

# 保存修改后的拓扑文件
output_file = 'd:/pp_tool/topology_one_level_with_connections.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(topology_data, f, ensure_ascii=False, indent=2)

print(f"连接关系已生成，保存到文件: {output_file}")
print(f"共生成 {len(connections)} 条连接关系")
