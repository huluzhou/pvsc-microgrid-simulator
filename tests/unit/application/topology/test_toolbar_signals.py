from PySide6.QtWidgets import QApplication
from adapters.inbound.ui.pyside.topology import TopologyToolbar


def test_topology_toolbar_signals_available():
    app = QApplication.instance() or QApplication([])
    toolbar = TopologyToolbar()
    assert hasattr(toolbar, "new_topology")
    assert hasattr(toolbar, "open_topology")
    assert hasattr(toolbar, "save_topology")
    assert hasattr(toolbar, "import_topology")
    assert hasattr(toolbar, "export_topology")
    assert hasattr(toolbar, "undo")
    assert hasattr(toolbar, "redo")
