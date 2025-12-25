
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from application.app import Application
from application.commands.topology.topology_commands import AddDeviceCommand, CreateConnectionCommand
from domain.aggregates.topology.value_objects.topology_id import TopologyId
from domain.aggregates.topology.value_objects.device_type import DeviceTypeEnum
from domain.aggregates.topology.value_objects.position import Position
from domain.aggregates.topology.value_objects.device_properties import DeviceProperties
from domain.aggregates.topology.value_objects.connection_type import ConnectionTypeEnum

def test_connection_flow():
    app = Application()
    
    topology_id_str = "default_topology"
    topology_id = TopologyId(topology_id_str)
    
    print(f"Testing with Topology ID: {topology_id}")
    
    # 1. Add a Bus (Source)
    print("\nAdding Bus...")
    try:
        cmd_bus = AddDeviceCommand(
            topology_id=topology_id,
            device_type=DeviceTypeEnum.BUS,
            name="Bus1",
            position=Position(0, 0),
            properties=DeviceProperties({})
        )
        res_bus = app.topology_device_management_use_case.add_device(cmd_bus)
        print(f"Bus added: {res_bus.device_id}")
    except Exception as e:
        print(f"Failed to add Bus: {e}")
        return

    # 2. Add a Load (Target)
    print("\nAdding Load...")
    try:
        cmd_load = AddDeviceCommand(
            topology_id=topology_id,
            device_type=DeviceTypeEnum.LOAD,
            name="Load1",
            position=Position(100, 0),
            properties=DeviceProperties({})
        )
        res_load = app.topology_device_management_use_case.add_device(cmd_load)
        print(f"Load added: {res_load.device_id}")
    except Exception as e:
        print(f"Failed to add Load: {e}")
        return

    # 3. Create Connection
    print("\nCreating Connection...")
    try:
        cmd_conn = CreateConnectionCommand(
            topology_id=topology_id,
            source_device_id=res_bus.device_id,
            target_device_id=res_load.device_id,
            connection_type=ConnectionTypeEnum.BIDIRECTIONAL
        )
        res_conn = app.topology_connection_management_use_case.create_connection(cmd_conn)
        print(f"Connection created: {res_conn.connection_id}")
    except Exception as e:
        print(f"Failed to create connection: {e}")

if __name__ == "__main__":
    test_connection_flow()
