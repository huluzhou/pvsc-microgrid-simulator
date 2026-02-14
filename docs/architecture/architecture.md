# 项目架构与目录边界（六边形架构）

## 分层与职责

- `src-tauri/src/domain/`：Rust 领域模型与业务规则（实体、值对象、领域服务）。
- `src-tauri/src/commands/`：Tauri 命令接口，连接前端与后端服务。
- `src-tauri/src/services/`：后端服务层（仿真引擎、数据库、Modbus、Python 桥接等）。
- `src/`：前端 React + TypeScript 代码（页面、组件、工具等）。
- `python-kernel/`：Python 计算内核，通过 JSON-RPC 与 Rust 后端通信。

## 当前架构（Tauri + React）

### 技术栈

- **前端**：React + TypeScript + Tailwind CSS
- **后端**：Rust + Tauri
- **计算内核**：Python（pandapower、numpy、scipy 等）
- **通信协议**：Tauri Commands（前端↔后端）、JSON-RPC（后端↔Python 内核）

### 架构层次

```
前端 (React/TypeScript)
    ↓ Tauri Commands
Rust 后端 (Tauri)
    ├─ 领域层 (domain/)
    ├─ 服务层 (services/)
    └─ 命令层 (commands/)
    ↓ JSON-RPC
Python 内核 (python-kernel/)
    ├─ 仿真引擎 (simulation/)
    └─ AI 模块 (ai/)
```

### 目录结构

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
│   │   │   ├── topology.rs      # 拓扑领域模型
│   │   │   ├── device.rs        # 设备领域模型
│   │   │   └── simulation.rs    # 仿真领域模型
│   │   ├── services/            # 服务层
│   │   │   ├── simulation_engine.rs  # 仿真引擎
│   │   │   ├── python_bridge.rs      # Python 桥接
│   │   │   ├── database.rs           # 数据库服务
│   │   │   └── modbus.rs             # Modbus 服务
│   │   └── commands/            # Tauri 命令
│   │       ├── topology.rs      # 拓扑命令
│   │       ├── simulation.rs     # 仿真命令
│   │       └── ...
│   └── tauri.conf.json           # Tauri 配置
├── python-kernel/                # Python 计算内核
│   ├── main.py                   # JSON-RPC 入口
│   ├── simulation/               # 仿真模块
│   └── ai/                       # AI 模块
└── docs/                         # 文档目录
    ├── architecture/             # 架构文档
    ├── ui/                       # UI 设计文档
    └── ...
```

## 已执行的清理（2025年）

### 删除的未实现功能
- `src/domain/aggregates/analytics/` - 分析功能（未实现）
- `src/domain/aggregates/backtest/` - 回测功能（未实现）
- `src/domain/aggregates/device_control/` - 设备控制（未实现）
- `src/domain/aggregates/power_management/` - 功率管理（未实现）
- `src/adapters/external_services/protocols/` - 协议适配器（MQTT/Modbus，未实现）

### 删除的冗余内容
- `backup/` - 备份目录
- `src/components/`、`src/models/`、`src/utils/` - 空目录（已迁移到 React）
- `src/adapters/inbound/topology/` - 冗余目录
- `src/domain/`、`src/application/`、`src/infrastructure/`、`src/adapters/` - 旧的 Python 六边形架构代码（已迁移到 Rust）
- `doc/` - 旧的文档目录（已迁移到 `docs/`）
- 测试数据文件（`*.json` 拓扑文件）
- 构建产物（`dist/`、`main.build/`、`main.dist/`）
- 日志文件
- 非拓扑相关的测试文件

### 保留的核心功能
- ✅ Tauri + React 前端（完整实现）
- ✅ Rust 后端服务（完整实现）
- ✅ Python 计算内核（完整实现）
- ✅ 拓扑管理（Rust 实现）
- ✅ 仿真引擎（Rust + Python）
- ✅ 数据库服务（Rust + SQLite）
- ✅ Modbus 服务（Rust）

### 文档保留
- 所有文档已统一整理到 `docs/` 目录，按类型分类
- 详细文档导航请参考 [README.md](../README.md) 的文档导航部分

## 与功能需求的对应

### 拓扑设计模块
- **前端**：`src/pages/TopologyDesign.tsx` 和 `src/components/topology/` 提供拓扑设计界面
- **Rust 后端**：`src-tauri/src/commands/topology.rs` 提供拓扑管理命令
- **Rust 领域层**：`src-tauri/src/domain/topology.rs` 提供拓扑领域模型和验证规则

### 仿真模块
- **前端**：`src/pages/Simulation.tsx` 提供仿真控制界面
- **Rust 后端**：`src-tauri/src/services/simulation_engine.rs` 管理仿真流程
- **Python 内核**：`python-kernel/simulation/` 执行实际计算

### 数据看板模块
- **前端**：`src/pages/Dashboard.tsx` 提供数据可视化界面
- **Rust 后端**：`src-tauri/src/services/database.rs` 提供数据查询服务

## 当前架构状态

- ✅ 项目已从 PySide6 迁移到 Tauri + React 架构
- ✅ 前端使用 React + TypeScript，后端使用 Rust
- ✅ Python 内核通过 JSON-RPC 与 Rust 后端通信
- ✅ 所有文档已统一整理到 `docs/` 目录
- ✅ 旧的 Python 六边形架构代码已清理

## 数据流

### 拓扑设计流程
```
用户操作 (前端)
  → invoke('save_topology') (Tauri Command)
  → Rust 后端验证和处理
  → 保存到文件系统
  → 返回结果给前端
```

### 仿真流程
```
用户启动仿真 (前端)
  → invoke('start_simulation') (Tauri Command)
  → Rust 仿真引擎初始化
  → 设置拓扑到 Python 内核 (JSON-RPC)
  → Python 内核执行计算
  → 结果返回 Rust 后端
  → 存储到数据库
  → 前端通过事件接收更新
```
