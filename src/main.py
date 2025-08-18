#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主程序入口文件
"""

import sys
from PySide6.QtWidgets import QApplication
from components.main_window import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()