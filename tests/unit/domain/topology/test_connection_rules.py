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

def conn(a, b):
    return Connection(f"conn-{a.id}-{b.id}", str(a.id), str(b.id), ConnectionTypeEnum.BIDIRECTIONAL)

def setup_topo():
    topo = MicrogridTopology("t-1", "t")
    return topo

def test_bus_to_bus_disallowed():
    topo = setup_topo()
    b1 = make_bus("A")
    b2 = make_bus("B")
    topo.add_device(b1)
    topo.add_device(b2)
    with pytest.raises(InvalidTopologyException):
        topo.add_connection(conn(b1, b2))

def test_line_bus_updates_properties():
    topo = setup_topo()
    b1 = make_bus("A")
    b2 = make_bus("B")
    l1 = make_line("L")
    topo.add_device(b1)
    topo.add_device(b2)
    topo.add_device(l1)
    topo.add_connection(conn(b1, l1))
    assert l1.properties.get_property("from_bus") == str(b1.id)
    topo.add_connection(conn(l1, b2))
    assert l1.properties.get_property("to_bus") == str(b2.id)

def test_line_switch_single_switch_end_only():
    topo = setup_topo()
    b1 = make_bus("A")
    l1 = make_line("L")
    s1 = make_switch("S1")
    s2 = make_switch("S2")
    topo.add_device(b1)
    topo.add_device(l1)
    topo.add_device(s1)
    topo.add_device(s2)
    topo.add_connection(conn(s1, l1))
    with pytest.raises(InvalidTopologyException):
        topo.add_connection(conn(s2, l1))

def test_switch_second_non_bus_must_be_bus():
    topo = setup_topo()
    s = make_switch("S")
    l = make_line("L")
    t = make_transformer("T")
    topo.add_device(s)
    topo.add_device(l)
    topo.add_device(t)
    topo.add_connection(conn(s, l))
    with pytest.raises(InvalidTopologyException):
        topo.add_connection(conn(s, t))

def test_switch_with_bus_then_line_updates_line_bus():
    topo = setup_topo()
    b = make_bus("B")
    s = make_switch("S")
    l = make_line("L")
    topo.add_device(b)
    topo.add_device(s)
    topo.add_device(l)
    topo.add_connection(conn(b, s))
    topo.add_connection(conn(s, l))
    fb = l.properties.get_property("from_bus")
    tb = l.properties.get_property("to_bus")
    assert fb == str(b.id) or tb == str(b.id)

def test_power_device_single_bus_and_single_meter():
    topo = setup_topo()
    b = make_bus("B")
    load = make_power("L", DeviceTypeEnum.LOAD)
    m1 = make_meter("M1")
    m2 = make_meter("M2")
    topo.add_device(b)
    topo.add_device(load)
    topo.add_device(m1)
    topo.add_device(m2)
    topo.add_connection(conn(b, load))
    with pytest.raises(InvalidTopologyException):
        topo.add_connection(conn(load, b))
    topo.add_connection(conn(load, m1))
    with pytest.raises(InvalidTopologyException):
        topo.add_connection(conn(load, m2))

def test_transformer_bus_updates_properties():
    topo = setup_topo()
    b1 = make_bus("A")
    b2 = make_bus("B")
    t = make_transformer("T")
    topo.add_device(b1)
    topo.add_device(b2)
    topo.add_device(t)
    topo.add_connection(conn(b1, t))
    assert t.properties.get_property("hv_bus") == str(b1.id)
    topo.add_connection(conn(t, b2))
    assert t.properties.get_property("lv_bus") == str(b2.id)
