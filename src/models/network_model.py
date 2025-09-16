#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
电网模型，用于处理pandapower网络模型
"""

import pandapower as pp
import pandas as pd


class NetworkModel:
    """电网模型类，用于处理pandapower网络模型"""

    def __init__(self):
        """初始化电网模型"""
        self.net = pp.create_empty_network()
        self.component_map = {}  # 存储图形项与pandapower元素的映射关系

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
        self.component_map[item_id] = {"type": "bus", "idx": bus_idx}
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
        self.component_map[item_id] = {"type": "line", "idx": line_idx}
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
        self.component_map[item_id] = {"type": "transformer", "idx": trafo_idx}
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
        self.component_map[item_id] = {"type": "generator", "idx": gen_idx}
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
        
        self.component_map[item_id] = {"type": "load", "idx": load_idx}
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
        self.component_map[item_id] = {"type": "storage", "idx": storage_idx}
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
        self.component_map[item_id] = {"type": "meter", "idx": measurement_idx}
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
        self.component_map[item_id] = {"type": "charger", "idx": charger_idx}
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
        self.component_map[item_id] = {"type": "external_grid", "idx": ext_grid_idx}
        return ext_grid_idx

    def create_static_generator(self, item_id, bus, properties):
        """创建光伏
        
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
        self.component_map[item_id] = {"type": "static_generator", "idx": sgen_idx}
        return sgen_idx

    def update_component(self, item_id, properties):
        """更新组件属性
        
        Args:
            item_id: 图形项ID
            properties: 新的属性
        """
        if item_id not in self.component_map:
            return
        
        component = self.component_map[item_id]
        component_type = component["type"]
        idx = component["idx"]
        
        if component_type == "bus":
            self.net.bus.loc[idx, "vn_kv"] = properties.get("vn_kv", self.net.bus.loc[idx, "vn_kv"])
            self.net.bus.loc[idx, "name"] = properties.get("name", self.net.bus.loc[idx, "name"])
            self.net.bus.loc[idx, "type"] = properties.get("type", self.net.bus.loc[idx, "type"])
            self.net.bus.loc[idx, "zone"] = properties.get("zone", self.net.bus.loc[idx, "zone"])
            self.net.bus.loc[idx, "in_service"] = properties.get("in_service", self.net.bus.loc[idx, "in_service"])
            # 处理NaN值的特殊情况
            max_vm_pu = properties.get("max_vm_pu", self.net.bus.loc[idx, "max_vm_pu"])
            min_vm_pu = properties.get("min_vm_pu", self.net.bus.loc[idx, "min_vm_pu"])
            if not pd.isna(max_vm_pu):
                self.net.bus.loc[idx, "max_vm_pu"] = max_vm_pu
            if not pd.isna(min_vm_pu):
                self.net.bus.loc[idx, "min_vm_pu"] = min_vm_pu
        
        elif component_type == "line":
            self.net.line.loc[idx, "length_km"] = properties.get("length_km", self.net.line.loc[idx, "length_km"])
            self.net.line.loc[idx, "name"] = properties.get("name", self.net.line.loc[idx, "name"])
        
        elif component_type == "transformer":
            # 变压器属性更新
            self.net.trafo.loc[idx, "name"] = properties.get("name", self.net.trafo.loc[idx, "name"])
        
        elif component_type == "generator":
            self.net.gen.loc[idx, "p_mw"] = properties.get("p_mw", self.net.gen.loc[idx, "p_mw"])
            self.net.gen.loc[idx, "vm_pu"] = properties.get("vm_pu", self.net.gen.loc[idx, "vm_pu"])
            self.net.gen.loc[idx, "name"] = properties.get("name", self.net.gen.loc[idx, "name"])
        
        elif component_type == "load":
            # 根据use_power_factor参数决定如何更新功率值
            use_power_factor = properties.get("use_power_factor", False)
            
            if use_power_factor:
                # 使用功率因数模式 - 根据sn_mva和cos_phi计算p_mw
                sn_mva = properties.get("sn_mva", 1.0)
                cos_phi = properties.get("cos_phi", 0.9)
                
                # 根据功率因数计算有功功率
                p_mw = sn_mva * cos_phi
                self.net.load.loc[idx, "p_mw"] = p_mw
                
                # 如果存在q_mvar列，也更新无功功率
                if "q_mvar" in self.net.load.columns:
                    sin_phi = (1 - cos_phi**2)**0.5
                    q_mvar = sn_mva * sin_phi  # 负载通常消耗感性无功功率
                    self.net.load.loc[idx, "q_mvar"] = q_mvar
            else:
                # 直接使用有功功率
                self.net.load.loc[idx, "p_mw"] = properties.get("p_mw", self.net.load.loc[idx, "p_mw"])
                
                # 如果存在q_mvar列且用户提供了值，也更新无功功率
                if "q_mvar" in self.net.load.columns and "q_mvar" in properties:
                    self.net.load.loc[idx, "q_mvar"] = properties.get("q_mvar", self.net.load.loc[idx, "q_mvar"])
            
            # 更新其他属性
            self.net.load.loc[idx, "name"] = properties.get("name", self.net.load.loc[idx, "name"])
            
            # 只更新存在的列
            if "const_z_percent" in self.net.load.columns:
                self.net.load.loc[idx, "const_z_percent"] = properties.get("const_z_percent", self.net.load.loc[idx, "const_z_percent"])
            if "const_i_percent" in self.net.load.columns:
                self.net.load.loc[idx, "const_i_percent"] = properties.get("const_i_percent", self.net.load.loc[idx, "const_i_percent"])
            if "scaling" in self.net.load.columns:
                self.net.load.loc[idx, "scaling"] = properties.get("scaling", self.net.load.loc[idx, "scaling"])
            if "in_service" in self.net.load.columns:
                self.net.load.loc[idx, "in_service"] = properties.get("in_service", self.net.load.loc[idx, "in_service"])
        
        elif component_type == "storage":
            self.net.storage.loc[idx, "p_mw"] = properties.get("p_mw", self.net.storage.loc[idx, "p_mw"])
            self.net.storage.loc[idx, "max_e_mwh"] = properties.get("max_e_mwh", self.net.storage.loc[idx, "max_e_mwh"])

        elif component_type == "charger":
            # 充电桩作为负载处理，但使用独立的索引（已偏移1000）
            use_power_factor = properties.get("use_power_factor", False)
            
            # 确保索引在有效范围内（已考虑1000偏移）
            if idx < len(self.net.load)+1000:
                if use_power_factor:
                    # 使用功率因数模式 - 与负载保持一致
                    sn_mva = properties.get("sn_mva", 1.0)
                    cos_phi = properties.get("cos_phi", 0.9)
                    
                    # 根据功率因数计算有功功率
                    p_mw = sn_mva * cos_phi
                    self.net.load.loc[idx, "p_mw"] = p_mw
                    
                    # 如果存在q_mvar列，也更新无功功率
                    if "q_mvar" in self.net.load.columns:
                        sin_phi = (1 - cos_phi**2)**0.5
                        q_mvar = sn_mva * sin_phi  # 负载通常消耗感性无功功率
                        self.net.load.loc[idx, "q_mvar"] = q_mvar
                    
                    # 更新视在功率（与负载保持一致）
                    if "sn_mva" in self.net.load.columns:
                        self.net.load.loc[idx, "sn_mva"] = sn_mva
                else:
                    # 直接使用有功功率模式
                    self.net.load.loc[idx, "p_mw"] = properties.get("p_mw", self.net.load.loc[idx, "p_mw"])
                
                # 更新名称属性
                self.net.load.loc[idx, "name"] = properties.get("name", self.net.load.loc[idx, "name"])
                
                # 更新其他与负载一致的属性
                if "const_z_percent" in self.net.load.columns:
                    self.net.load.loc[idx, "const_z_percent"] = properties.get("const_z_percent", self.net.load.loc[idx, "const_z_percent"])
                if "const_i_percent" in self.net.load.columns:
                    self.net.load.loc[idx, "const_i_percent"] = properties.get("const_i_percent", self.net.load.loc[idx, "const_i_percent"])
                if "scaling" in self.net.load.columns:
                    self.net.load.loc[idx, "scaling"] = properties.get("scaling", self.net.load.loc[idx, "scaling"])
                if "in_service" in self.net.load.columns:
                    self.net.load.loc[idx, "in_service"] = properties.get("in_service", self.net.load.loc[idx, "in_service"])
        
        elif component_type == "static_generator":
            # 根据use_power_factor参数决定如何更新功率值
            use_power_factor = properties.get("use_power_factor", False)
            
            if use_power_factor:
                # 使用功率因数模式
                sn_mva = properties.get("sn_mva", 1.0)
                cos_phi = properties.get("cos_phi", 0.9)
                
                # 根据功率因数计算有功功率，无功功率设为0（光伏发电通常不提供无功功率）
                p_mw = sn_mva * cos_phi
                q_mvar = 0.0
                
                self.net.sgen.loc[idx, "p_mw"] = p_mw
                self.net.sgen.loc[idx, "q_mvar"] = q_mvar
            else:
                # 直接使用有功功率，无功功率设为0
                self.net.sgen.loc[idx, "p_mw"] = properties.get("p_mw", self.net.sgen.loc[idx, "p_mw"])
                self.net.sgen.loc[idx, "q_mvar"] = 0.0
            
            # 更新其他属性
            self.net.sgen.loc[idx, "name"] = properties.get("name", self.net.sgen.loc[idx, "name"])
            self.net.sgen.loc[idx, "scaling"] = properties.get("scaling", self.net.sgen.loc[idx, "scaling"])
            self.net.sgen.loc[idx, "in_service"] = properties.get("in_service", self.net.sgen.loc[idx, "in_service"])
        
        elif component_type == "external_grid":
            # 外部电网只需要bus参数，无需更新其他属性
            pass
        


    def delete_component(self, item_id):
        """删除组件
        
        Args:
            item_id: 图形项ID
        """
        if item_id not in self.component_map:
            return
        
        component = self.component_map[item_id]
        component_type = component["type"]
        idx = component["idx"]
        
        if component_type == "bus":
            pp.drop_elements(self.net, "bus", [idx])
        elif component_type == "line":
            pp.drop_elements(self.net, "line", [idx])
        elif component_type == "transformer":
            pp.drop_elements(self.net, "trafo", [idx])
        elif component_type == "generator":
            pp.drop_elements(self.net, "gen", [idx])
        elif component_type == "load":
            pp.drop_elements(self.net, "load", [idx])
        elif component_type == "storage":
            pp.drop_elements(self.net, "storage", [idx])
        elif component_type == "charger":
            pp.drop_elements(self.net, "load", [idx])  # 充电站作为负载删除
        elif component_type == "external_grid":
            pp.drop_elements(self.net, "ext_grid", [idx])
        elif component_type == "meter":
            pp.drop_elements(self.net, "measurement", [idx])

        
        # 从映射中删除
        del self.component_map[item_id]

    # 删除潮流计算相关方法（潮流计算功能已移除）

    def save_to_json(self, filename):
        """保存网络到JSON文件
        
        Args:
            filename: 文件名
        
        Returns:
            bool: 保存是否成功
        """
        try:
            pp.to_json(self.net, filename)
            # 保存组件映射关系
            pd.DataFrame(self.component_map).to_json(f"{filename}_map.json")
            return True
        except Exception as e:
            print(f"保存网络错误: {e}")
            return False

    def load_from_json(self, filename):
        """从JSON文件加载网络
        
        Args:
            filename: 文件名
        
        Returns:
            bool: 加载是否成功
        """
        try:
            self.net = pp.from_json(filename)
            # 加载组件映射关系
            self.component_map = pd.read_json(f"{filename}_map.json").to_dict()
            return True
        except Exception as e:
            print(f"加载网络错误: {e}")
            return False
