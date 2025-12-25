from PySide6.QtWidgets import QLabel

class StatusPanel(QLabel):
    """自定义状态栏面板"""
    def __init__(self):
        super().__init__()
        self.setText("就绪")