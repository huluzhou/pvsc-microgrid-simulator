#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
电网模型，用于处理pandapower网络模型
"""

import pandapower as pp
import pandas as pd
import numpy as np


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
            type=properties.get("type", "b"),
            zone=properties.get("zone", None),
            in_service=properties.get("in_service", True),
            max_vm_pu=properties.get("max_vm_pu", float('nan')),
            min_vm_pu=properties.get("min_vm_pu", float('nan')),
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
        
        Returns:
            int: pandapower线路索引
        """
        line_idx = pp.create_line(
            self.net,
            from_bus=from_bus,
            to_bus=to_bus,
            length_km=properties.get("length_km", 10.0),
            std_type="NAYY 4x50 SE",  # 默认线路类型
            name=properties.get("name", "Line"),
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
        trafo_idx = pp.create_transformer(
            self.net,
            hv_bus=hv_bus,
            lv_bus=lv_bus,
            std_type="160 MVA 380/110 kV",  # 默认变压器类型
            name=properties.get("name", "Transformer"),
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
            vm_pu=properties.get("vm_pu", 1.0),
            name=properties.get("name", "Generator"),
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
        load_idx = pp.create_load(
            self.net,
            bus=bus,
            p_mw=properties.get("p_mw", 10.0),
            q_mvar=properties.get("q_mvar", 5.0),
            name=properties.get("name", "Load"),
        )
        self.component_map[item_id] = {"type": "load", "idx": load_idx}
        return load_idx

    def create_storage(self, item_id, bus, properties):
        """创建储能设备
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 储能属性
        
        Returns:
            int: pandapower储能索引
        """
        storage_idx = pp.create_storage(
            self.net,
            bus=bus,
            p_mw=properties.get("p_mw", 0.0),
            max_e_mwh=properties.get("max_e_mwh", 100.0),
            soc_percent=properties.get("soc_percent", 50.0),
            name=properties.get("name", "Storage"),
        )
        self.component_map[item_id] = {"type": "storage", "idx": storage_idx}
        return storage_idx

    def create_charger(self, item_id, bus, properties):
        """创建充电站设备
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 充电站属性
        
        Returns:
            int: pandapower负载索引（充电站作为负载处理）
        """
        # 充电站作为可控负载处理
        charger_idx = pp.create_load(
            self.net,
            bus=bus,
            p_mw=properties.get("p_mw", 50.0),
            q_mvar=0.0,  # 充电站通常功率因数接近1
            name=properties.get("name", "Charger"),
            controllable=True,
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
            vm_pu=properties.get("vm_pu", 1.0),
            va_degree=properties.get("va_degree", 0.0),
            name=properties.get("name", "External Grid"),
            s_sc_max_mva=properties.get("s_sc_max_mva", 1000.0),
            s_sc_min_mva=properties.get("s_sc_min_mva", 800.0),
            rx_max=properties.get("rx_max", 0.1),
            rx_min=properties.get("rx_min", 0.1),
        )
        self.component_map[item_id] = {"type": "external_grid", "idx": ext_grid_idx}
        return ext_grid_idx

    def create_static_generator(self, item_id, bus, properties):
        """创建静态发电机
        
        Args:
            item_id: 图形项ID
            bus: 母线索引
            properties: 静态发电机属性
        
        Returns:
            int: pandapower静态发电机索引
        """
        # 根据use_power_factor参数决定使用哪种创建方式
        use_power_factor = properties.get("use_power_factor", False)
        
        if use_power_factor:
            # 使用功率因数模式
            sn_mva = properties.get("sn_mva", 1.0)
            cos_phi = properties.get("cos_phi", 0.9)
            
            # 根据功率因数计算有功功率，无功功率设为0（光伏发电通常不提供无功功率）
            p_mw = sn_mva * cos_phi
            q_mvar = 0.0
        else:
            # 直接使用有功功率，无功功率设为0
            p_mw = properties.get("p_mw", 1.0)
            q_mvar = 0.0
        
        sgen_idx = pp.create_sgen(
            self.net,
            bus=bus,
            p_mw=p_mw,
            q_mvar=q_mvar,
            name=properties.get("name", "Static Generator"),
            scaling=properties.get("scaling", 1.0),
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
            self.net.load.loc[idx, "p_mw"] = properties.get("p_mw", self.net.load.loc[idx, "p_mw"])
            self.net.load.loc[idx, "q_mvar"] = properties.get("q_mvar", self.net.load.loc[idx, "q_mvar"])
            self.net.load.loc[idx, "name"] = properties.get("name", self.net.load.loc[idx, "name"])
        
        elif component_type == "storage":
            self.net.storage.loc[idx, "p_mw"] = properties.get("p_mw", self.net.storage.loc[idx, "p_mw"])
            self.net.storage.loc[idx, "max_e_mwh"] = properties.get("max_e_mwh", self.net.storage.loc[idx, "max_e_mwh"])
            self.net.storage.loc[idx, "soc_percent"] = properties.get("soc_percent", self.net.storage.loc[idx, "soc_percent"])
            self.net.storage.loc[idx, "name"] = properties.get("name", self.net.storage.loc[idx, "name"])
        
        elif component_type == "charger":
            self.net.load.loc[idx, "p_mw"] = properties.get("p_mw", self.net.load.loc[idx, "p_mw"])
            self.net.load.loc[idx, "name"] = properties.get("name", self.net.load.loc[idx, "name"])
        
        elif component_type == "external_grid":
            self.net.ext_grid.loc[idx, "vm_pu"] = properties.get("vm_pu", self.net.ext_grid.loc[idx, "vm_pu"])
            self.net.ext_grid.loc[idx, "va_degree"] = properties.get("va_degree", self.net.ext_grid.loc[idx, "va_degree"])
            self.net.ext_grid.loc[idx, "name"] = properties.get("name", self.net.ext_grid.loc[idx, "name"])
            self.net.ext_grid.loc[idx, "s_sc_max_mva"] = properties.get("s_sc_max_mva", self.net.ext_grid.loc[idx, "s_sc_max_mva"])
            self.net.ext_grid.loc[idx, "s_sc_min_mva"] = properties.get("s_sc_min_mva", self.net.ext_grid.loc[idx, "s_sc_min_mva"])
            self.net.ext_grid.loc[idx, "rx_max"] = properties.get("rx_max", self.net.ext_grid.loc[idx, "rx_max"])
            self.net.ext_grid.loc[idx, "rx_min"] = properties.get("rx_min", self.net.ext_grid.loc[idx, "rx_min"])
        


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
            pp.drop_buses(self.net, [idx])
        elif component_type == "line":
            pp.drop_lines(self.net, [idx])
        elif component_type == "transformer":
            pp.drop_trafos(self.net, [idx])
        elif component_type == "generator":
            pp.drop_gens(self.net, [idx])
        elif component_type == "load":
            pp.drop_loads(self.net, [idx])
        elif component_type == "storage":
            pp.drop_storages(self.net, [idx])
        elif component_type == "charger":
            pp.drop_loads(self.net, [idx])  # 充电站作为负载删除
        elif component_type == "external_grid":
            pp.drop_ext_grids(self.net, [idx])

        
        # 从映射中删除
        del self.component_map[item_id]

    def run_power_flow(self):
        """运行潮流计算
        
        Returns:
            bool: 计算是否成功
        """
        try:
            pp.runpp(self.net)
            return True
        except Exception as e:
            print(f"潮流计算错误: {e}")
            return False

    def get_results(self):
        """获取潮流计算结果
        
        Returns:
            dict: 计算结果
        """
        results = {
            "bus": self.net.res_bus.copy() if hasattr(self.net, "res_bus") else None,
            "line": self.net.res_line.copy() if hasattr(self.net, "res_line") else None,
            "trafo": self.net.res_trafo.copy() if hasattr(self.net, "res_trafo") else None,
            "gen": self.net.res_gen.copy() if hasattr(self.net, "res_gen") else None,
            "load": self.net.res_load.copy() if hasattr(self.net, "res_load") else None,
        }
        return results

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