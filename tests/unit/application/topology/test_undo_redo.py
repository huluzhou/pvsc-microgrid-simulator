from application.use_cases.topology.topology_file_use_cases import UndoRedoUseCase


def test_undo_redo_flow():
    u = UndoRedoUseCase()
    u.snapshot({"devices": []})
    u.snapshot({"devices": [{"type": "bus", "id": 1, "x": 0, "y": 0}]})
    prev = u.undo()
    assert prev["devices"] == []
    curr = u.redo()
    assert len(curr["devices"]) == 1
