#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用程序主入口点
"""

import sys
import os

# 首先导入logger以确保日志配置在pymodbus导入之前完成
from infrastructure.logging import logger

import warnings

# 禁用libpng警告
os.environ['PNG_SKIP_sRGB_CHECK'] = '1'

# 禁用matplotlib相关警告
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

from application.app import Application
from PySide6.QtWidgets import QApplication
from adapters.inbound.ui.pyside.main_application import MainApplication


def main():
    """主函数"""
    # 初始化应用程序
    app = Application()
    
    # 创建PySide应用程序
    qt_app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainApplication(app)
    window.show()
    
    # 运行应用程序
    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
