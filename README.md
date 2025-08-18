# PandaPower Simulation Tool

基于PySide6和pandapower的电网仿真工具，支持通过拖拽方式构建电网拓扑图。

## 功能特点

- 直观的拖拽界面，轻松构建电网拓扑
- 基于pandapower的电网建模和分析
- 保存和加载拓扑图功能
- 电网分析和仿真功能

## 环境要求

- Python 3.10+
- PySide6 6.0+
- pandapower 2.13+

## 安装方法

使用conda创建环境并安装依赖：

```bash
# 使用environment.yml创建环境
conda env create -f environment.yml

# 激活环境
conda activate pandapower_sim
```

## 使用方法

```bash
# 启动应用
python src/main.py
```

## 项目结构

```
.
├── src/                # 源代码目录
│   ├── assets/         # 图标和资源文件
│   ├── components/     # UI组件
│   ├── models/         # 数据模型
│   └── utils/          # 工具函数
├── environment.yml     # Conda环境配置
└── requirements.txt    # 项目依赖
```