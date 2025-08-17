#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试断开连接功能的脚本
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PyQt5.QtWidgets import QApplication
from components.main_window import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 在状态栏显示使用说明
    window.statusBar().showMessage(
        "使用说明: 1) 从左侧拖拽组件到画布 2) 选中设备后右键选择'断开连接' 3) 或使用菜单'编辑->断开连接'(Ctrl+D)"
    )
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()