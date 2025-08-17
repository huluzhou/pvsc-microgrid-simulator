#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试应用程序启动脚本
"""

import sys
import os

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# 导入主程序
from src.main import main

if __name__ == "__main__":
    main()