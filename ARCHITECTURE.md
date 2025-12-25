# 项目架构与目录边界（六边形架构）

## 分层与职责

- `src/domain/`：领域模型与业务规则（实体、值对象、领域服务、规格、事件）。
- `src/application/`：用例编排与应用服务（用例、DTO、命令）。不含基础设施和 UI 细节。
- `src/adapters/`：适配器层，连接外部世界与端口（UI、协议、存储等）。
  - `inbound/`：入站适配器（UI、API），调用应用层用例。
  - `external_services/`：出站适配器（协议等），实现应用/领域端口。
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

## 已执行的清理

- 删除：`backup/`、顶层 `examples/`、顶层 `ui_design/`、`src/adapters/inbound/ui/qml/`、`tests/integration/`、与拓扑无关的单元测试，以及冗余 PDF/非拓扑 UI 文档。
- 文档保留重点：`doc/architecture_design/functional_requirements_specification.md` 与 `doc/ui_design/topology_design.svg`。

## 与功能需求的对应（拓扑设计模块）

- 领域层：`domain/aggregates/topology/` 已包含实体、值对象、校验与连通性服务。
- 应用层：`application/use_cases/topology/` 负责用例编排与命令处理。
- 入站适配器：`adapters/inbound/ui/pyside/topology/` 提供拓扑画布、工具栏、属性/状态面板导出。
- 出站适配器：协议与存储适配器可按需实现并通过端口注入。

## 目录期望（后续演进建议）

- 将 `main_application.py` 迁移为只依赖 `topology/` 封装的入口。
- 统一端口位置或保留现状，但需提供端口索引文档，避免分散。
- 为拓扑模块新增最小仓储实现（内存/SQLite）与入站命令映射（后续迭代）。
