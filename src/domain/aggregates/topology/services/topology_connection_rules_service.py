from typing import List, Any
from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.value_objects.device_type import DeviceTypeEnum
from domain.aggregates.topology.exceptions import InvalidTopologyException
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties

class TopologyConnectionRulesService:
    def enforce_and_apply(self, topology: Any, connection: Any, src: Device, tgt: Device):
        st = self._device_type(src)
        tt = self._device_type(tgt)
        if self._is_bus(st) and self._is_bus(tt):
            raise InvalidTopologyException("Bus-to-bus connection is not allowed")
        props = getattr(connection, "properties", {}) or {}
        self._validate_pair(topology, src, st, tgt, tt, props, is_src=True)
        self._validate_pair(topology, tgt, tt, src, st, props, is_src=False)
        self._update_properties_on_connect(topology, src, st, tgt, tt, props, is_src=True)
        self._update_properties_on_connect(topology, tgt, tt, src, st, props, is_src=False)

    def _device_type(self, device: Device) -> DeviceTypeEnum:
        return device.device_type.type

    def _is_bus(self, t: DeviceTypeEnum) -> bool:
        return t in {DeviceTypeEnum.NODE, DeviceTypeEnum.BUS}

    def _is_meter(self, t: DeviceTypeEnum) -> bool:
        return t == DeviceTypeEnum.METER

    def _is_power(self, t: DeviceTypeEnum) -> bool:
        return t in {
            DeviceTypeEnum.LOAD,
            DeviceTypeEnum.STORAGE,
            DeviceTypeEnum.STATIC_GENERATOR,
            DeviceTypeEnum.CHARGER,
            DeviceTypeEnum.EXTERNAL_GRID,
            DeviceTypeEnum.GENERATOR
        }

    def _adjacent_connections(self, topology: Any, device_id: str) -> List[Any]:
        return [c for c in topology._connections.values() if c.source_device_id == device_id or c.target_device_id == device_id]

    def _adjacent_peer_types(self, topology: Any, device_id: str) -> List[DeviceTypeEnum]:
        types = []
        for c in self._adjacent_connections(topology, device_id):
            peer_id = c.target_device_id if c.source_device_id == device_id else c.source_device_id
            peer = topology._devices.get(peer_id)
            if peer:
                types.append(self._device_type(peer))
        return types

    def _count_adjacent_type(self, topology: Any, device_id: str, type_enum: DeviceTypeEnum) -> int:
        return sum(1 for t in self._adjacent_peer_types(topology, device_id) if t == type_enum or (type_enum in {DeviceTypeEnum.NODE, DeviceTypeEnum.BUS} and t in {DeviceTypeEnum.NODE, DeviceTypeEnum.BUS}))

    def _count_non_meter_connections(self, topology: Any, device_id: str) -> int:
        return sum(1 for t in self._adjacent_peer_types(topology, device_id) if not self._is_meter(t))
    
    def _count_non_meter_non_bus_connections(self, topology: Any, device_id: str) -> int:
        return sum(1 for t in self._adjacent_peer_types(topology, device_id) if not self._is_meter(t) and not self._is_bus(t))
    
    def _count_connections(self, topology: Any, device_id: str) -> int:
        return len(self._adjacent_connections(topology, device_id))

    def _validate_pair(self, topology: Any, a: Device, at: DeviceTypeEnum, b: Device, bt: DeviceTypeEnum, conn_props: dict, is_src: bool):
        aid = str(a.id)
        bid = str(b.id)
        port_idx = None
        if is_src:
            port_idx = conn_props.get("source_port")
        else:
            port_idx = conn_props.get("target_port")
        b_port_idx = conn_props.get("target_port" if is_src else "source_port")
        if b_port_idx is not None:
            if self._has_connection_to_target_port_from_same_device(topology, aid, bid, b_port_idx):
                raise InvalidTopologyException("Device cannot connect multiple ports to the same target port")
        if self._is_power(at):
            if not (self._is_bus(bt) or self._is_meter(bt)):
                raise InvalidTopologyException("Power device can only connect to bus or meter")
            if self._is_bus(bt) and self._count_adjacent_type(topology, aid, DeviceTypeEnum.BUS) >= 1:
                raise InvalidTopologyException("Power device can only connect to one bus")
            if self._is_meter(bt) and self._count_adjacent_type(topology, aid, DeviceTypeEnum.METER) >= 1:
                raise InvalidTopologyException("Power device can only connect to one meter")
        if at == DeviceTypeEnum.LINE:
            if not (self._is_bus(bt) or bt == DeviceTypeEnum.SWITCH or self._is_meter(bt)):
                raise InvalidTopologyException("Line endpoint must connect to bus, switch or meter")
            if not self._is_meter(bt):
                if self._count_non_meter_connections(topology, aid) >= 2:
                    raise InvalidTopologyException("Line endpoints already occupied")
                if bt == DeviceTypeEnum.SWITCH and self._count_adjacent_type(topology, aid, DeviceTypeEnum.SWITCH) >= 1:
                    raise InvalidTopologyException("Line cannot connect to switches on both ends")
                if port_idx is not None:
                    # 每端口仅允许一个非电表连接
                    if self._port_has_non_meter(topology, aid, port_idx):
                        raise InvalidTopologyException("Line endpoint already connected on this port")
        if at == DeviceTypeEnum.TRANSFORMER:
            if not (self._is_bus(bt) or bt == DeviceTypeEnum.SWITCH or self._is_meter(bt)):
                raise InvalidTopologyException("Transformer endpoint must connect to bus, switch or meter")
            if not self._is_meter(bt):
                if self._count_non_meter_connections(topology, aid) >= 2:
                    raise InvalidTopologyException("Transformer endpoints already occupied")
                if bt == DeviceTypeEnum.SWITCH and self._count_adjacent_type(topology, aid, DeviceTypeEnum.SWITCH) >= 1:
                    raise InvalidTopologyException("Transformer cannot connect to switches on both ends")
                if port_idx is not None:
                    if self._port_has_non_meter(topology, aid, port_idx):
                        raise InvalidTopologyException("Transformer endpoint already connected on this port")
        if at == DeviceTypeEnum.SWITCH:
            allowed = self._is_bus(bt) or bt in {DeviceTypeEnum.LINE, DeviceTypeEnum.TRANSFORMER} or self._is_meter(bt)
            if not allowed:
                raise InvalidTopologyException("Switch can only connect to bus, line, transformer or meter")
            non_bus_non_meter = self._count_non_meter_non_bus_connections(topology, aid)
            bus_count = self._count_adjacent_type(topology, aid, DeviceTypeEnum.BUS)
            if bt in {DeviceTypeEnum.LINE, DeviceTypeEnum.TRANSFORMER}:
                if non_bus_non_meter >= 1 and bus_count == 0:
                    raise InvalidTopologyException("Switch second non-bus end must be bus")
        if at == DeviceTypeEnum.METER:
            allowed = self._is_bus(bt) or bt in {DeviceTypeEnum.LINE, DeviceTypeEnum.TRANSFORMER, DeviceTypeEnum.SWITCH} or self._is_power(bt)
            if not allowed:
                raise InvalidTopologyException("Meter connection target not allowed")
            if self._count_connections(topology, aid) >= 1:
                raise InvalidTopologyException("Meter can only have one connection")
            if bt == DeviceTypeEnum.LINE and self._count_adjacent_type(topology, str(b.id), DeviceTypeEnum.METER) >= 2:
                raise InvalidTopologyException("Line endpoints allow at most one meter each")
            if bt == DeviceTypeEnum.TRANSFORMER and self._count_adjacent_type(topology, str(b.id), DeviceTypeEnum.METER) >= 2:
                raise InvalidTopologyException("Transformer endpoints allow at most one meter each")

    def _update_properties_on_connect(self, topology: Any, a: Device, at: DeviceTypeEnum, b: Device, bt: DeviceTypeEnum, conn_props: dict, is_src: bool):
        if at == DeviceTypeEnum.LINE and self._is_bus(bt):
            props = a.properties.properties
            fb = props.get("from_bus")
            tb = props.get("to_bus")
            bid = str(b.id)
            port_idx = conn_props.get("source_port" if is_src else "target_port")
            if port_idx == 0:
                if fb and fb != bid:
                    raise InvalidTopologyException("Line from_bus already set")
                a.update_properties(DeviceProperties({**props, "from_bus": bid}))
            elif port_idx == 1:
                if tb and tb != bid:
                    raise InvalidTopologyException("Line to_bus already set")
                a.update_properties(DeviceProperties({**props, "to_bus": bid}))
            else:
                if not fb:
                    a.update_properties(DeviceProperties({**props, "from_bus": bid}))
                elif not tb:
                    a.update_properties(DeviceProperties({**props, "to_bus": bid}))
                else:
                    raise InvalidTopologyException("Line bus endpoints are already set")
        if at == DeviceTypeEnum.TRANSFORMER and self._is_bus(bt):
            props = a.properties.properties
            hv = props.get("hv_bus")
            lv = props.get("lv_bus")
            bid = str(b.id)
            port_idx = conn_props.get("source_port" if is_src else "target_port")
            if port_idx == 0:
                if hv and hv != bid:
                    raise InvalidTopologyException("Transformer hv_bus already set")
                a.update_properties(DeviceProperties({**props, "hv_bus": bid}))
            elif port_idx == 1:
                if lv and lv != bid:
                    raise InvalidTopologyException("Transformer lv_bus already set")
                a.update_properties(DeviceProperties({**props, "lv_bus": bid}))
            else:
                if not hv:
                    a.update_properties(DeviceProperties({**props, "hv_bus": bid}))
                elif not lv:
                    a.update_properties(DeviceProperties({**props, "lv_bus": bid}))
                else:
                    raise InvalidTopologyException("Transformer bus endpoints are already set")
        if at == DeviceTypeEnum.SWITCH and bt in {DeviceTypeEnum.LINE, DeviceTypeEnum.TRANSFORMER}:
            sp = a.properties.properties
            et = "l" if bt == DeviceTypeEnum.LINE else "t"
            eid = str(b.id)
            a.update_properties(DeviceProperties({**sp, "et": et, "element": eid}))
            bus_ids = []
            for c in self._adjacent_connections(topology, str(a.id)):
                peer_id = c.target_device_id if c.source_device_id == str(a.id) else c.source_device_id
                peer = topology._devices.get(peer_id)
                if peer and self._is_bus(self._device_type(peer)):
                    bus_ids.append(str(peer.id))
            if bus_ids:
                if bt == DeviceTypeEnum.LINE:
                    lp = b.properties.properties
                    fb = lp.get("from_bus")
                    tb = lp.get("to_bus")
                    bid = bus_ids[0]
                    if not fb:
                        b.update_properties(DeviceProperties({**lp, "from_bus": bid}))
                    elif not tb:
                        b.update_properties(DeviceProperties({**lp, "to_bus": bid}))
                if bt == DeviceTypeEnum.TRANSFORMER:
                    tp = b.properties.properties
                    hv = tp.get("hv_bus")
                    lv = tp.get("lv_bus")
                    bid = bus_ids[0]
                    if not hv:
                        b.update_properties(DeviceProperties({**tp, "hv_bus": bid}))
                    elif not lv:
                        b.update_properties(DeviceProperties({**tp, "lv_bus": bid}))
        if at == DeviceTypeEnum.SWITCH and self._is_bus(bt):
            sp = a.properties.properties
            bid = str(b.id)
            a.update_properties(DeviceProperties({**sp, "bus": bid}))
    
    def _port_has_non_meter(self, topology: Any, a_id: str, port_idx: int) -> bool:
        # 通过 connection.properties 中的端口信息来判断端口是否已有非电表连接
        for c in topology._connections.values():
            if c.source_device_id == a_id and isinstance(c.properties, dict):
                sp = c.properties.get("source_port")
                if sp == port_idx:
                    # 查找对端类型
                    peer = topology._devices.get(c.target_device_id)
                    if peer and not self._is_meter(self._device_type(peer)):
                        return True
            if c.target_device_id == a_id and isinstance(c.properties, dict):
                tp = c.properties.get("target_port")
                if tp == port_idx:
                    peer = topology._devices.get(c.source_device_id)
                    if peer and not self._is_meter(self._device_type(peer)):
                        return True
        return False

    def _has_connection_to_target_port_from_same_device(self, topology: Any, a_id: str, b_id: str, b_port_idx: int) -> bool:
        for c in topology._connections.values():
            if c.source_device_id == a_id and c.target_device_id == b_id and isinstance(c.properties, dict):
                tp = c.properties.get("target_port")
                if tp == b_port_idx:
                    return True
            if c.target_device_id == a_id and c.source_device_id == b_id and isinstance(c.properties, dict):
                sp = c.properties.get("source_port")
                if sp == b_port_idx:
                    return True
        return False
