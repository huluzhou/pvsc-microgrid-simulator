#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主程序入口文件
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from components.main_window import MainWindow


def get_resource_path(relative_path):
    """获取资源文件的绝对路径，支持PyInstaller打包后的路径"""
    try:
        # PyInstaller创建临时文件夹，并将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境下使用当前文件的目录
        base_path = os.path.dirname(os.path.abspath(__file__))
        # 如果是在src目录下，需要回到上级目录
        if os.path.basename(base_path) == 'src':
            base_path = os.path.dirname(base_path)
        # 在开发环境下，assets在src目录中
        if not relative_path.startswith('src/') and os.path.exists(os.path.join(base_path, 'src', relative_path)):
            relative_path = os.path.join('src', relative_path)
    
    return os.path.join(base_path, relative_path)


# 设置全局资源路径函数
MainWindow.get_resource_path = staticmethod(get_resource_path)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()