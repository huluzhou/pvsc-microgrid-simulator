#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主程序入口文件
"""

import sys
import os

# 首先导入logger以确保日志配置在pymodbus导入之前完成
from utils.logger import logger

from PySide6.QtWidgets import QApplication
from components.main_window import MainWindow
from config import get_resource_path

# 设置全局资源路径函数
MainWindow.get_resource_path = staticmethod(get_resource_path)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()