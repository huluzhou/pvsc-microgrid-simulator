#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
电网模型，用于处理pandapower网络模型
"""

import pandapower as pp
import pandas as pd
from components.globals import network_model, network_items
import os
class NetworkModel:
    """电网模型类，用于处理pandapower网络模型"""

    def __init__(self):
        """初始化电网模型"""
        self.net = pp.create_empty_network()
        import components.globals
        components.globals.network_model = self

    def create_bus(self, item_id, properties):
        """创建母线
        
        Args:
            item_id: 图形项ID
            properties: 母线属性
        
        Returns:
            int: pandapower母线索引
        """
        bus_idx = pp.create_bus(
            self.net,
            vn_kv=properties.get("vn_kv", 10.0),
            name=properties.get("name", "Bus"),
            index=properties.get("index", None),
            type=properties.get("type", "b"),
            in_service=properties.get("in_service", True),
            max_vm_pu=properties.get("max_vm_pu", float("nan")),
            min_vm_pu=properties.get("min_vm_pu", float("nan")),
        )
        # self.component_map[item_id] = {"type": "bus", "idx": bus_idx}
        return bus_idx

    def create_line(self, item_id, from_bus, to_bus, properties):
        """创建线路
        
        Args:
            item_id: 图形项ID
            from_bus: 起始母线索引
            to_bus: 终止母线索引
            properties: 线路属性
            is_std: 是否使用标准线路类型
        
        Returns:
            int: pandapower线路索引
        """
        is_std = properties.get("use_standard_type", True)
        if is_std:
            # 使用用户选择的标准类型，而不是硬编码的默认值
            std_type = properties.get("std_type", "NAYY 4x50 SE")
            line_idx = pp.create_line(
                self.net,
                from_bus=from_bus,
                to_bus=to_bus,
                length_km=properties.get("length_km", 10.0),
                std_type=std_type,
                name=properties.get("name", "Line"),
                index=properties.get("index", None),
            )
        else:
            line_idx = pp.create_line_from_parameters(
                self.net,
                from_bus=from_bus,
                to_bus=to_bus,
                length_km=properties.get("length_km", 10.0),
                r_ohm_per_km=properties.get("r_ohm_per_km", 0.1),
                x_ohm_per_km=properties.get("x_ohm_per_km", 0.1),
                c_nf_per_km=properties.get("c_nf_per_km", 0.0),
                r0_ohm_per_km=properties.get("r0_ohm_per_km", 0.0),
                x0_ohm_per_km=properties.get("x0_ohm_per_km", 0.0),
                c0_nf_per_km=properties.get("c0_nf_per_km", 0.0),
                max_i_ka=properties.get("max_i_ka", 1.0),
                name=properties.get("name", "Line"),
                index=properties.get("index", None),
            )
        # self.component_map[item_id] = {"type": "line", "idx": line_idx}
        return line_idx
        
    def create_transformer(self, item_id, hv_bus, lv_bus, properties):
        """创建变压器
        
        Args:
            item_id: 图形项ID
            hv_bus: 高压侧母线索引
            lv_bus: 低压侧母线索引
            properties: 变压器属性
        
        Returns:
            int: pandapower变压器索引
        """
        is_std = properties.get("use_standard_type", True)
        if is_std:
            # 使用用户选择的标准类型，而不是硬编码的默认值
            std_type = properties.get("std_type", "25 MVA 110/20 kV")
            trafo_idx = pp.create_transformer(
                self.net,
                hv_bus=hv_bus,
                lv_bus=lv_bus,
                std_type=std_type,
                name=properties.get("name", "Transformer"),
                index=properties.get("index", None),
            )
        else:
            trafo_idx = pp.create_transformer_from_parameters(
                self.net,
                hv_bus=hv_bus,
                lv_bus=lv_bus,
                sn_mva=properties.get("sn_mva", 160.0),
                vn_hv_kv=properties.get("vn_hv_kv", 380.0),
                vn_lv_kv=properties.get("vn_lv_kv", 110.0),
                vkr_percent=properties.get("vkr_percent", 0.0),
                vk_percent=properties.get("vk_percent", 0.0),
                pfe_kw=properties.get("pfe_kw", 0.0),
                i0_percent=properties.get("i0_percent", 0.0),
                name=properties.get("name", "Transformer"),
                index=properties.get("index", None),
            )
        # self.component_map[item_id] = {"type": "transformer", "idx": trafo_idx}
        return trafo_idx

    def create_generator(self, item_id, bus, properties):
        """创建发电机
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 发电机属性
        
        Returns:
            int: pandapower发电机索引
        """
        gen_idx = pp.create_gen(
            self.net,
            bus=bus,
            p_mw=properties.get("p_mw", 100.0),
            name=properties.get("name", "Generator"),
            index=properties.get("index", None),
            in_service=properties.get("in_service", True),
        )
        # self.component_map[item_id] = {"type": "generator", "idx": gen_idx}
        return gen_idx

    def create_load(self, item_id, bus, properties):
        """创建负载
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 负载属性
        
        Returns:
            int: pandapower负载索引
        """
        # 根据use_power_factor参数决定使用哪种创建方式
        use_power_factor = properties.get("use_power_factor", False)
        
        if use_power_factor:
            # 使用功率因数模式 - 调用create_load_from_cosphi
            sn_mva = properties.get("sn_mva", 1.0)
            cos_phi = properties.get("cos_phi", 0.9)
            mode = properties.get("mode", "underexcited")
            
            load_idx = pp.create_load_from_cosphi(
                self.net,
                bus=bus,
                sn_mva=sn_mva,
                cos_phi=cos_phi,
                mode=mode,
                name=properties.get("name", "Load"),
                index=properties.get("index", None),
                in_service=properties.get("in_service", True),
            )
        else:
            # 直接使用有功功率模式 - 调用create_load
            p_mw = properties.get("p_mw", 1.0)
            
            load_idx = pp.create_load(
                self.net,
                bus=bus,
                p_mw=p_mw,
                name=properties.get("name", "Load"),
                index=properties.get("index", None),
                in_service=properties.get("in_service", True),
            )
        
        # self.component_map[item_id] = {"type": "load", "idx": load_idx}
        return load_idx

    def create_storage(self, item_id, bus, properties):
        """创建储能设备
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 储能设备属性
        
        Returns:
            int: pandapower储能设备索引
        """
        storage_idx = pp.create_storage(
            self.net,
            bus=bus,
            p_mw=properties.get("p_mw", 0.0),
            max_e_mwh=properties.get("max_e_mwh", 1.0),
            name=properties.get("name", "Storage"),
            index=properties.get("index", None),
            in_service=properties.get("in_service", True),
        )
        # self.component_map[item_id] = {"type": "storage", "idx": storage_idx}
        return storage_idx

    def create_measurement(self, item_id, properties):
        """创建电表测量设备
        
        Args:
            item_id: 图形项ID
            properties: 电表属性
        
        Returns:
            int: pandapower测量索引
        """
        # 创建电表测量
        measurement_idx = pp.create_measurement(
            self.net,
            meas_type=properties.get("meas_type", "p"),  # 默认测量有功功率
            element_type=properties.get("element_type", "bus"),  # 默认测量母线
            value=properties.get("value", 0.0),  # 测量值
            std_dev=properties.get("std_dev", 0.0),  # 标准偏差
            element=properties.get("element", 0),  # 元件索引
            side=properties.get("side", None),  # 测量侧
            name=properties.get("name", "Meter"),
            index=properties.get("index", None),
        )
        # self.component_map[item_id] = {"type": "meter", "idx": measurement_idx}
        return measurement_idx

    def create_charger(self, item_id, bus, properties):
        """创建充电站设备
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 充电站属性
        
        Returns:
            int: pandapower负载索引（充电站作为负载处理，但使用独立的索引）
        """
        # 充电站作为可控负载处理，但为了避免与负载索引冲突，使用特殊前缀
        use_power_factor = properties.get("use_power_factor", False)
        
        # 为充电桩分配独立的索引，避免与负载冲突
        charger_index = properties.get("index", None)
        
        if use_power_factor:
            # 使用功率因数模式 - 调用create_load_from_cosphi
            sn_mva = properties.get("sn_mva", 1.0)
            cos_phi = properties.get("cos_phi", 0.9)
            mode = properties.get("mode", "underexcited")  # 默认为欠励磁模式（吸收无功功率）
            
            charger_idx = pp.create_load_from_cosphi(
                self.net,
                bus=bus,
                sn_mva=sn_mva,
                cos_phi=cos_phi,
                mode=mode,
                name=properties.get("name", f"Charger_{charger_index-1000}"),
                index=charger_index,
                in_service=properties.get("in_service", True),
            )
        else:
            # 直接使用有功功率模式 - 调用create_load
            p_mw = properties.get("p_mw", 1.0)
            sn_mva = properties.get("sn_mva", 1.0)  # 默认为1MVA
            charger_idx = pp.create_load(
                self.net,
                bus=bus,
                sn_mva=sn_mva,
                p_mw=p_mw,
                name=properties.get("name", f"Charger_{charger_index-1000}"),
                index=charger_index,
                in_service=properties.get("in_service", True),
            )
        # self.component_map[item_id] = {"type": "charger", "idx": charger_idx}
        return charger_idx

    def create_external_grid(self, item_id, bus, properties):
        """创建外部电网
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 外部电网属性
        
        Returns:
            int: pandapower外部电网索引
        """
        ext_grid_idx = pp.create_ext_grid(
            self.net,
            bus=bus,
            name=properties.get("name", "External Grid"),
        )
        # self.component_map[item_id] = {"type": "external_grid", "idx": ext_grid_idx}
        return ext_grid_idx

    def create_static_generator(self, item_id, bus, properties):
        """创建光伏设备
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 光伏属性
        
        Returns:
            int: pandapower光伏索引
        """
        # 根据use_power_factor参数决定使用哪种创建方式
        use_power_factor = properties.get("use_power_factor", False)
        
        if use_power_factor:
            # 使用功率因数模式
            sn_mva = properties.get("sn_mva", 1.0)
            cos_phi = properties.get("cos_phi", 0.9)
            sgen_idx = pp.create_sgen_from_cosphi(
                self.net,
                bus=bus,
                sn_mva=sn_mva,
                cos_phi=cos_phi,
                mode = properties.get("mode", "underexcited"),
                name=properties.get("name", "Static Generator"),
                index = properties.get("index", None),
            )
        else:
            # 直接使用有功功率，无功功率设为0
            p_mw = properties.get("p_mw", 1.0)
        
            sgen_idx = pp.create_sgen(
            self.net,
            bus=bus,
            p_mw=p_mw,
            name=properties.get("name", "Static Generator"),
            index = properties.get("index", None),
            in_service=properties.get("in_service", True),
        )
        # self.component_map[item_id] = {"type": "static_generator", "idx": sgen_idx}
        return sgen_idx

    def create_switch(self, item_id, bus, properties):
        """创建开关设备
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 开关属性
        
        Returns:
            int: pandapower开关索引
        """
        switch_idx = pp.create_switch(
            self.net,
            bus=bus,
            element=properties.get("element", 0),
            et=properties.get("et", "b"),
            closed=properties.get("closed", True),
            in_ka=properties.get("in_ka", 1000.0),
            name=properties.get("name", "Switch"),
            index = properties.get("index", None),
        )
        return switch_idx

    def create_from_network_items(self, canvas):
        """从canvas中的组件创建pandapower网络模型
        
        Args:
            canvas: Canvas对象，包含connections
        
        Returns:
            bool: 创建是否成功
        """
        try:
            # 检查是否有组件
            if not network_items or not any(network_items.values()):
                print("没有组件，无法创建网络模型")
                return False
            
            # 第一步：创建所有母线
            bus_map = {}  # 存储图形项到pandapower母线索引的映射
            
            if 'bus' in network_items:
                # 遍历嵌套字典中的所有母线（每个索引直接对应一个BusItem对象）
                for idx, bus_item in network_items['bus'].items():
                    try:
                        bus_idx = self.create_bus(
                            id(bus_item),  # 使用对象ID作为唯一标识
                            bus_item.properties if hasattr(bus_item, 'properties') else {}
                        )
                        bus_map[bus_item] = bus_idx
                        print(f"创建母线: {bus_item.component_name} -> 索引 {bus_idx}")
                    except Exception as e:
                        print(f"创建母线 {bus_item.component_name} 时出错: {str(e)}")
                        return False
            
            if not bus_map:
                print("没有有效的母线组件，无法创建网络模型")
                return False
            
            # 第二步：创建连接到母线的组件（负载、发电机等，但不包括电表）
            non_meter_items = []
            for comp_type, comp_dict in network_items.items():
                if comp_type != 'bus' and comp_type != 'meter':
                    # 遍历嵌套字典中的所有组件（每个索引直接对应一个组件对象）
                    for idx, item in comp_dict.items():
                        non_meter_items.append(item)
            
            for item in non_meter_items:
                try:
                    # 查找该组件连接的母线
                    connected_buses = canvas.get_connected_buses(item, bus_map)
                    
                    if item.component_type == 'load':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.create_load(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建负载: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'external_grid':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.create_external_grid(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建外部电网: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'static_generator':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.create_static_generator(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建光伏: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'storage':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.create_storage(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建储能: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'charger':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            self.create_charger(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建充电站: {item.component_name} -> 母线 {bus_idx}")
                    
                    elif item.component_type == 'transformer':
                        if len(connected_buses) >= 2:
                            hv_bus = connected_buses[0]
                            lv_bus = connected_buses[1]
                            self.create_transformer(
                                id(item),
                                hv_bus,
                                lv_bus,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建变压器: {item.component_name} -> 母线 {hv_bus}-{lv_bus}")
                    
                    elif item.component_type == 'line':
                        if len(connected_buses) >= 2:
                            from_bus = connected_buses[0]
                            to_bus = connected_buses[1]
                            self.create_line(
                                id(item),
                                from_bus,
                                to_bus,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            print(f"创建线路: {item.component_name} -> 母线 {from_bus}-{to_bus}")
                    
                    elif item.component_type == 'switch':
                        if connected_buses:
                            bus_idx = connected_buses[0]
                            switch_idx = self.create_switch(
                                id(item),
                                bus_idx,
                                item.properties if hasattr(item, 'properties') else {}
                            )
                            item.model_index = switch_idx
                            print(f"创建开关: {item.component_name} -> 母线 {bus_idx}")
                
                except Exception as e:
                    print(f"创建组件 {item.component_name} 时出错: {str(e)}")
                    # 继续处理其他组件，不中断整个过程

            # 第三步：最后创建电表设备（确保所有其他设备已创建）
            meter_items = []
            if 'meter' in network_items:
                # 遍历嵌套字典中的所有电表（每个索引直接对应一个电表对象）
                for idx, item in network_items['meter'].items():
                    meter_items.append(item)
            
            for item in meter_items:
                try:
                    meter_idx = self.create_measurement(
                        id(item),
                        item.properties if hasattr(item, 'properties') else {}
                    )
                    print(f"创建电表: {item.component_name} -> 测量索引 {meter_idx}")
                except Exception as e:
                    print(f"创建组件 {item.component_name} 时出错: {str(e)}")
                    # 继续处理其他组件，不中断整个过程
            
            print(f"网络模型创建完成，包含 {len(self.net.bus)} 个母线")
            
            # 保存网络模型到JSON文件
            import os
            from pandapower.file_io import to_json
            file_path = "network.json"
            to_json(self.net, file_path)
            # 获取完整保存路径
            full_path = os.path.abspath(file_path)
            print(f"网络模型已保存到: {full_path}")
            
            return True
        except Exception as e:
            print(f"创建网络模型时出错: {str(e)}")
            return False

    def run_power_flow(self):
        """运行潮流计算
        
        Returns:
            bool: 计算是否成功
        """
        try:
            pp.runpp(self.net)
            print("潮流计算完成")
            return True
        except Exception as e:
            print(f"潮流计算失败: {str(e)}")
            return False

    def get_bus_voltage(self, bus_idx):
        """获取母线电压
        
        Args:
            bus_idx: 母线索引
        
        Returns:
            float: 电压幅值
        """
        if hasattr(self.net, 'res_bus') and not self.net.res_bus.empty:
            if bus_idx in self.net.res_bus.index:
                return self.net.res_bus.loc[bus_idx, 'vm_pu']
        return None

    def get_line_power(self, line_idx):
        """获取线路功率
        
        Args:
            line_idx: 线路索引
        
        Returns:
            tuple: (有功功率, 无功功率)
        """
        if hasattr(self.net, 'res_line') and not self.net.res_line.empty:
            if line_idx in self.net.res_line.index:
                p_from = self.net.res_line.loc[line_idx, 'p_from_mw']
                q_from = self.net.res_line.loc[line_idx, 'q_from_mvar']
                return (p_from, q_from)
        return (None, None)

    def get_transformer_power(self, trafo_idx):
        """获取变压器功率
        
        Args:
            trafo_idx: 变压器索引
        
        Returns:
            tuple: (高压侧有功功率, 高压侧无功功率, 低压侧有功功率, 低压侧无功功率)
        """
        if hasattr(self.net, 'res_trafo') and not self.net.res_trafo.empty:
            if trafo_idx in self.net.res_trafo.index:
                p_hv = self.net.res_trafo.loc[trafo_idx, 'p_hv_mw']
                q_hv = self.net.res_trafo.loc[trafo_idx, 'q_hv_mvar']
                p_lv = self.net.res_trafo.loc[trafo_idx, 'p_lv_mw']
                q_lv = self.net.res_trafo.loc[trafo_idx, 'q_lv_mvar']
                return (p_hv, q_hv, p_lv, q_lv)
        return (None, None, None, None)

    def get_load_power(self, load_idx):
        """获取负载功率
        
        Args:
            load_idx: 负载索引
        
        Returns:
            tuple: (有功功率, 无功功率)
        """
        if hasattr(self.net, 'res_load') and not self.net.res_load.empty:
            if load_idx in self.net.res_load.index:
                p_mw = self.net.res_load.loc[load_idx, 'p_mw']
                q_mvar = self.net.res_load.loc[load_idx, 'q_mvar']
                return (p_mw, q_mvar)
        return (None, None)

    def get_generator_power(self, gen_idx):
        """获取发电机功率
        
        Args:
            gen_idx: 发电机索引
        
        Returns:
            tuple: (有功功率, 无功功率)
        """
        if hasattr(self.net, 'res_gen') and not self.net.res_gen.empty:
            if gen_idx in self.net.res_gen.index:
                p_mw = self.net.res_gen.loc[gen_idx, 'p_mw']
                q_mvar = self.net.res_gen.loc[gen_idx, 'q_mvar']
                return (p_mw, q_mvar)
        return (None, None)

    def save_network(self, filename="network.json"):
        """保存网络模型到JSON文件
        
        Args:
            filename: 文件名
        
        Returns:
            bool: 保存是否成功
        """
        try:
            pp.to_json(self.net, filename)
            print(f"网络模型已保存到: {os.path.abspath(filename)}")
            return True
        except Exception as e:
            print(f"保存网络模型时出错: {str(e)}")
            return False

    def load_network(self, filename="network.json"):
        """从JSON文件加载网络模型
        
        Args:
            filename: 文件名
        
        Returns:
            bool: 加载是否成功
        """
        try:
            self.net = pp.from_json(filename)
            print(f"网络模型已从: {os.path.abspath(filename)} 加载")
            return True
        except Exception as e:
            print(f"加载网络模型时出错: {str(e)}")
            return False
