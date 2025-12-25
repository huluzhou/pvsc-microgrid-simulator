import pytest
from domain.aggregates.topology.entities.microgrid_topology import MicrogridTopology
from domain.aggregates.topology.entities.node import Node
from domain.aggregates.topology.entities.line import Line
from domain.aggregates.topology.entities.transformer import Transformer
from domain.aggregates.topology.entities.switch import Switch
from domain.aggregates.topology.entities.device import Device
from domain.aggregates.topology.entities.connection import Connection
from domain.aggregates.topology.exceptions import InvalidTopologyException
from domain.aggregates.topology.value_objects.device_type import DeviceType, DeviceTypeEnum
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
from domain.aggregates.topology.value_objects.connection_type import ConnectionTypeEnum
from domain.aggregates.topology.services.topology_connection_rules_service import TopologyConnectionRulesService

def make_bus(name):
    return Node(f"node-{name}", DeviceProperties({"name": name}))

def make_line(name):
    return Line(f"line-{name}", DeviceProperties({"name": name}))

def make_transformer(name):
    return Transformer(f"transformer-{name}", DeviceProperties({"name": name}))

def make_switch(name):
    return Switch(f"switch-{name}", DeviceProperties({"name": name, "is_closed": False}))

def make_power(name, dtype: DeviceTypeEnum):
    return Device(f"{dtype.name.lower()}-{name}", DeviceType(dtype), DeviceProperties({"name": name}))

def make_meter(name):
    return Device(f"meter-{name}", DeviceType(DeviceTypeEnum.METER), DeviceProperties({"name": name}))

def setup_topo():
    topo = MicrogridTopology("t-2", "t2")
    return topo

def test_service_disallow_bus_to_bus():
    topo = setup_topo()
    b1 = make_bus("A")
    b2 = make_bus("B")
    topo.add_device(b1)
    topo.add_device(b2)
    svc = TopologyConnectionRulesService()
    with pytest.raises(InvalidTopologyException):
        svc.enforce_and_apply(
            topo,
            Connection(f"conn-{b1.id}-{b2.id}", str(b1.id), str(b2.id), ConnectionTypeEnum.BIDIRECTIONAL, {}),
            b1,
            b2
        )

def test_service_updates_line_bus():
    topo = setup_topo()
    b1 = make_bus("A")
    l1 = make_line("L")
    topo.add_device(b1)
    topo.add_device(l1)
    svc = TopologyConnectionRulesService()
    svc.enforce_and_apply(
        topo,
        Connection(f"conn-{b1.id}-{l1.id}", str(b1.id), str(l1.id), ConnectionTypeEnum.BIDIRECTIONAL, {"target_port": 0}),
        b1,
        l1
    )
    assert l1.properties.get_property("from_bus") == str(b1.id)

def test_service_switch_requires_bus_on_second_non_bus_end():
    topo = setup_topo()
    s = make_switch("S")
    l = make_line("L")
    t = make_transformer("T")
    topo.add_device(s)
    topo.add_device(l)
    topo.add_device(t)
    svc = TopologyConnectionRulesService()
    topo.add_connection(Connection(f"conn-{s.id}-{l.id}", str(s.id), str(l.id), ConnectionTypeEnum.BIDIRECTIONAL))
    with pytest.raises(InvalidTopologyException):
        svc.enforce_and_apply(
            topo,
            Connection(f"conn-{s.id}-{t.id}", str(s.id), str(t.id), ConnectionTypeEnum.BIDIRECTIONAL, {}),
            s,
            t
        )

def test_disallow_same_device_multiple_ports_to_same_target_port():
    topo = setup_topo()
    b = make_bus("B")
    l = make_line("L")
    topo.add_device(b)
    topo.add_device(l)
    svc = TopologyConnectionRulesService()
    c1 = Connection("c1", str(l.id), str(b.id), ConnectionTypeEnum.BIDIRECTIONAL, {"target_port": 0})
    svc.enforce_and_apply(topo, c1, l, b)
    topo._connections[c1.id] = c1
    c2 = Connection("c2", str(l.id), str(b.id), ConnectionTypeEnum.BIDIRECTIONAL, {"target_port": 0})
    with pytest.raises(InvalidTopologyException):
        svc.enforce_and_apply(topo, c2, l, b)

def test_meter_can_only_have_one_connection():
    topo = setup_topo()
    b1 = make_bus("B1")
    b2 = make_bus("B2")
    m = make_meter("M")
    topo.add_device(b1)
    topo.add_device(b2)
    topo.add_device(m)
    svc = TopologyConnectionRulesService()
    c1 = Connection("m1", str(m.id), str(b1.id), ConnectionTypeEnum.BIDIRECTIONAL, {})
    svc.enforce_and_apply(topo, c1, m, b1)
    topo._connections[c1.id] = c1
    c2 = Connection("m2", str(m.id), str(b2.id), ConnectionTypeEnum.BIDIRECTIONAL, {})
    with pytest.raises(InvalidTopologyException):
        svc.enforce_and_apply(topo, c2, m, b2)
