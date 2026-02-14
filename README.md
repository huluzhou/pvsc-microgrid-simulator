# 微电网拓扑设计工具

基于 Tauri + React 的微电网拓扑设计与仿真工具，支持通过拖拽方式构建和编辑微电网拓扑图，并进行实时仿真计算。

## 功能特点

- 🎨 直观的拖拽界面，轻松构建微电网拓扑
- 📐 完整的拓扑验证和连接规则检查
- 💾 支持拓扑图的保存和加载（JSON格式）
- 🔍 拓扑连通性分析
- ⚡ 拓扑优化服务
- 🏗️ 符合六边形架构和DDD最佳实践

## 架构设计

本项目采用**Tauri + React**架构，前端使用 React + TypeScript，后端使用 Rust，计算内核使用 Python：

- **前端** (`src/`): React + TypeScript 前端代码（页面、组件、工具等）
- **后端** (`src-tauri/`): Rust 后端服务（领域层、服务层、命令层）
- **计算内核** (`python-kernel/`): Python 计算内核（仿真、AI 等）

详细架构说明请参考 [架构文档](docs/architecture/architecture.md)

## 文档导航

项目文档已统一整理到 `docs/` 目录，按类型分类：

### 架构设计文档
- [项目架构](docs/architecture/architecture.md) - 项目整体架构与目录结构说明
- [架构审查](docs/architecture/architecture_review.md) - 六边形架构最佳实践与重构记录
- [领域事件最佳实践](docs/architecture/domain_events_best_practices.md) - 领域事件的设计与实现
- [功能需求规格](docs/architecture/functional_requirements_specification.md) - 系统功能需求详细说明

### UI 设计文档
- [拓扑 UI 设计说明](docs/ui/topology_ui_spec.md) - 拓扑设计模块的 UI 组件与交互规范
- [拓扑 UI 示意图](docs/ui/topology_design.svg) - 拓扑设计界面示意图

### 规则文档
- [拓扑连接规则](docs/rules/topology_rule.md) - 基于 pandapower 的拓扑连接规则与约束

### 构建文档
- [构建与发布指南](docs/build/BUILD.md) - 本地构建、打包和发布流程

### 端口文档
- [端口索引](docs/ports/PORTS_README.md) - 应用层和领域层端口定义与使用说明

### 分析文档
- [数据分析实现评估](docs/analytics/ANALYTICS_IMPLEMENTATION_EVALUATION.md) - 数据分析功能的实现位置评估与方案对比

## 环境要求

- Python 3.10+
- PySide6 6.0+

## 安装方法

### 使用虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 使用conda（如果提供environment.yml）

```bash
conda env create -f environment.yml
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
├── src/                          # 前端代码（React + TypeScript）
│   ├── pages/                    # 页面组件
│   ├── components/               # UI 组件
│   ├── stores/                   # 状态管理
│   └── utils/                    # 工具函数
├── src-tauri/                    # Rust 后端
│   ├── src/
│   │   ├── domain/              # 领域层
│   │   ├── services/            # 服务层
│   │   └── commands/            # Tauri 命令
│   └── tauri.conf.json          # Tauri 配置
├── python-kernel/                # Python 计算内核
│   ├── main.py                  # JSON-RPC 入口
│   ├── simulation/              # 仿真模块
│   └── ai/                      # AI 模块
├── tests/                        # 测试
│   └── unit/                    # 单元测试
├── docs/                        # 文档目录
│   ├── architecture/           # 架构设计文档
│   ├── ui/                     # UI设计文档
│   ├── rules/                  # 规则文档
│   ├── build/                  # 构建文档
│   ├── ports/                  # 端口文档
│   └── analytics/              # 分析文档
├── README.md                    # 本文件
└── requirements.txt             # Python依赖
```

## 数据看板（Tauri 应用）

在 Tauri 桌面应用中，「数据看板」支持三种数据源：

- **当前应用数据库**：从本应用默认 `data.db` 读取 `device_data` 表中的设备列表与时间序列。
- **选择本地数据库**：选择本地 SQLite 文件（与 `device_data` 表结构一致），按设备查询时间序列。
- **CSV 文件**：导入长表 CSV。支持列名：`device_id`（必填）、`timestamp` 或 `local_timestamp`（必填）、`p_active` 或 `p_mw`、`p_reactive` 或 `q_mvar`、可选 `data_json`。时间戳可为 Unix 秒、毫秒或 ISO/RFC3339 字符串。与 remote-tool 导出的长表格式兼容。
- **远程 SSH**：通过 SSH 连接远端主机，在远端执行对 `device_data` 表的查询（需远端表结构与本地一致）。

## 开发

### 运行测试

```bash
pytest
```

### 代码结构说明

- **前端** (`src/`): React + TypeScript 前端代码
  - `pages/`: 页面组件（拓扑设计、仿真、数据看板等）
  - `components/`: UI 组件（拓扑画布、设备面板等）
  - `stores/`: 状态管理
  - `utils/`: 工具函数

- **Rust 后端** (`src-tauri/src/`): Rust 后端服务
  - `domain/`: 领域层（拓扑、设备、仿真等）
  - `services/`: 服务层（仿真引擎、数据库、Modbus 等）
  - `commands/`: Tauri 命令接口

- **Python 内核** (`python-kernel/`): Python 计算内核
  - `simulation/`: 仿真模块（pandapower 集成）
  - `ai/`: AI 模块

## 许可证

[待添加]

## 贡献

欢迎提交Issue和Pull Request！