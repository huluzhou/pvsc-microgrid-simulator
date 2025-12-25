# 项目架构与目录边界（六边形架构）

## 分层与职责

- `src/domain/`：领域模型与业务规则（实体、值对象、领域服务、规格、事件）。
- `src/application/`：用例编排与应用服务（用例、DTO、命令）。不含基础设施和 UI 细节。
- `src/adapters/`：适配器层，连接外部世界与端口（UI、存储等）。
  - `inbound/`：入站适配器（UI、API），调用应用层用例。
  - `external_services/`：出站适配器（存储、协议等），可按需实现并通过端口注入。
- `src/infrastructure/`：跨层的技术能力（日志、配置、DI、事件中介等）。

## 端口策略

- 端口定义置于靠近核心业务的层。
  - 拓扑相关端口目前位于 `domain/aggregates/topology/ports/`，用于约束仓储与用例调用。
  - 可在后续将通用端口上移至 `src/ports/`（可选），实现更清晰的横切共享。

## UI 结构（PySide）

- 保留并优化 `src/adapters/inbound/ui/pyside/`。
  - `assets/`：设备图标资源。
  - `components/`：既有具体组件实现。
  - `topology/`：对拓扑组件的稳定封装导出（新增），供外部引用。
  - `main_application.py`：应用入口（后续可迁移引用至 `topology/`）。

## 已执行的清理（2025年）

### 删除的未实现功能
- `src/domain/aggregates/analytics/` - 分析功能（未实现）
- `src/domain/aggregates/backtest/` - 回测功能（未实现）
- `src/domain/aggregates/device_control/` - 设备控制（未实现）
- `src/domain/aggregates/power_management/` - 功率管理（未实现）
- `src/adapters/external_services/protocols/` - 协议适配器（MQTT/Modbus，未实现）

### 删除的冗余内容
- `backup/` - 备份目录
- `src/components/`、`src/models/`、`src/utils/` - 空目录
- `src/adapters/inbound/topology/` - 冗余目录
- 测试数据文件（`*.json` 拓扑文件）
- 构建产物（`dist/`、`main.build/`、`main.dist/`）
- 日志文件
- 非拓扑相关的测试文件

### 保留的核心功能
- ✅ 拓扑聚合（完整实现）
- ✅ 拓扑用例（完整实现）
- ✅ PySide6 UI适配器（完整实现）
- ✅ 基础设施层（日志、配置、DI、事件总线）

### 文档保留
- `doc/architecture_design/functional_requirements_specification.md` - 功能需求规格
- `doc/ui_design/topology_design.svg` - UI设计图
- `docs/domain_events_best_practices.md` - 领域事件最佳实践

## 与功能需求的对应（拓扑设计模块）

- 领域层：`domain/aggregates/topology/` 已包含实体、值对象、校验与连通性服务。
- 应用层：`application/use_cases/topology/` 负责用例编排与命令处理。
- 入站适配器：`adapters/inbound/ui/pyside/topology/` 提供拓扑画布、工具栏、属性/状态面板导出。
- 出站适配器：协议与存储适配器可按需实现并通过端口注入。

## 目录期望（后续演进建议）

- 将 `main_application.py` 迁移为只依赖 `topology/` 封装的入口。
- 统一端口位置或保留现状，但需提供端口索引文档，避免分散。
- 为拓扑模块新增最小仓储实现（内存/SQLite）与入站命令映射（后续迭代）。
