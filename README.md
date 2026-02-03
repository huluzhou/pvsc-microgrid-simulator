# 微电网拓扑设计工具

基于PySide6和领域驱动设计（DDD）的微电网拓扑设计工具，采用六边形架构（Hexagonal Architecture）设计，支持通过拖拽方式构建和编辑微电网拓扑图。

## 功能特点

- 🎨 直观的拖拽界面，轻松构建微电网拓扑
- 📐 完整的拓扑验证和连接规则检查
- 💾 支持拓扑图的保存和加载（JSON格式）
- 🔍 拓扑连通性分析
- ⚡ 拓扑优化服务
- 🏗️ 符合六边形架构和DDD最佳实践

## 架构设计

本项目采用**六边形架构（Hexagonal Architecture）**和**领域驱动设计（DDD）**：

- **领域层** (`src/domain/`): 核心业务逻辑，包含拓扑聚合、实体、值对象、领域服务和业务规则
- **应用层** (`src/application/`): 用例编排，包含用例、DTO和命令
- **适配器层** (`src/adapters/`): 入站适配器（UI）和出站适配器（存储、协议等）
- **基础设施层** (`src/infrastructure/`): 跨层技术能力（日志、配置、DI、事件总线等）

详细架构说明请参考 [ARCHITECTURE.md](ARCHITECTURE.md)

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
├── src/                          # 源代码目录
│   ├── domain/                   # 领域层
│   │   ├── aggregates/          # 聚合根
│   │   │   └── topology/        # 拓扑聚合（实体、值对象、服务、事件）
│   │   └── common/              # 通用领域组件
│   ├── application/             # 应用层
│   │   ├── use_cases/           # 用例
│   │   │   └── topology/        # 拓扑相关用例
│   │   ├── commands/            # 命令
│   │   └── dtos/                # 数据传输对象
│   ├── adapters/                # 适配器层
│   │   └── inbound/             # 入站适配器
│   │       └── ui/             # UI适配器
│   │           └── pyside/    # PySide6 UI实现
│   └── infrastructure/          # 基础设施层
│       ├── config/              # 配置管理
│       ├── events/              # 事件总线
│       ├── logging/             # 日志
│       └── third_party/         # 第三方集成
├── tests/                        # 测试
│   └── unit/                    # 单元测试
├── doc/                          # 文档
│   ├── architecture_design/    # 架构设计文档
│   └── ui_design/              # UI设计文档
├── config/                       # 配置文件
├── ARCHITECTURE.md              # 架构说明文档
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

- **拓扑聚合** (`src/domain/aggregates/topology/`): 包含微电网拓扑的核心业务逻辑
  - `entities/`: 实体（设备、连接、节点等）
  - `value_objects/`: 值对象（设备类型、位置、状态等）
  - `services/`: 领域服务（验证、连通性、优化等）
  - `events/`: 领域事件
  - `ports/`: 端口接口定义

- **用例** (`src/application/use_cases/topology/`): 应用层用例，编排领域服务完成业务功能

- **UI适配器** (`src/adapters/inbound/ui/pyside/`): PySide6 UI实现，调用应用层用例

## 许可证

[待添加]

## 贡献

欢迎提交Issue和Pull Request！