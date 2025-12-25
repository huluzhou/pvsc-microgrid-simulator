from PySide6.QtWidgets import QToolBar
from PySide6.QtCore import Signal

class CustomTopologyToolbar(QToolBar):
    """自定义拓扑工具栏"""
    new_topology = Signal()
    open_topology = Signal()
    save_topology = Signal()
    import_topology = Signal()
    export_topology = Signal()
    undo = Signal()
    redo = Signal()
    
    def __init__(self):
        super().__init__()
        
        # 添加工具栏按钮
        self.addAction("新建").triggered.connect(self.new_topology.emit)
        self.addAction("打开").triggered.connect(self.open_topology.emit)
        self.addAction("保存").triggered.connect(self.save_topology.emit)
        self.addSeparator()
        self.addAction("导入").triggered.connect(self.import_topology.emit)
        self.addAction("导出").triggered.connect(self.export_topology.emit)
        self.addSeparator()
        self.addAction("撤销").triggered.connect(self.undo.emit)
        self.addAction("重做").triggered.connect(self.redo.emit)