from application.commands.topology.topology_commands import (
    NewTopologyCommand,
    OpenTopologyCommand,
    SaveTopologyCommand,
    ImportTopologyCommand,
    ExportTopologyCommand,
    UndoCommand,
    RedoCommand,
)
from domain.aggregates.topology.value_objects.topology_id import TopologyId


def test_command_classes_instantiation():
    new_cmd = NewTopologyCommand(name="t1", description="d")
    assert new_cmd.name == "t1"

    open_cmd = OpenTopologyCommand(file_path="topology.json")
    assert open_cmd.file_path.endswith(".json")

    save_cmd = SaveTopologyCommand(topology_id=TopologyId("t1"), file_path="topology.json")
    assert str(save_cmd.topology_id) == "t1"

    import_cmd = ImportTopologyCommand(file_path="topology.json")
    assert import_cmd.file_path

    export_cmd = ExportTopologyCommand(topology_id=TopologyId("t1"), file_path="topology.json")
    assert export_cmd.file_path

    assert UndoCommand().topology_id is None
    assert RedoCommand().topology_id is None
