端口索引

## 端口分类

### 应用层端口（入站端口）

应用层端口定义了应用层与适配器层之间的接口。这些端口由用例实现，由适配器调用。

- **拓扑用例端口**：`src/application/ports/topology/`
  - `topology_use_case_ports.py`：用例端口接口
    - `TopologyCreationPort`：拓扑创建端口
    - `TopologyDeviceManagementPort`：设备管理端口
    - `TopologyConnectionManagementPort`：连接管理端口
    - `TopologyValidationPort`：拓扑验证端口
    - `TopologyOptimizationPort`：拓扑优化端口
    - `TopologyQueryPort`：拓扑查询端口

**实现位置**：`src/application/use_cases/topology/topology_use_cases.py`

### 领域层端口（出站端口）

领域层端口定义了领域层与基础设施层之间的接口。这些端口由基础设施层实现。

- **拓扑仓储端口**：`src/domain/aggregates/topology/ports/`
  - `topology_repository_port.py`：仓储端口接口
    - `TopologyRepositoryPort`：拓扑持久化接口

**实现位置**：`src/infrastructure/third_party/di/services.py`（InMemoryTopologyRepository）

## 适配器

### 入站适配器

- **UI适配器**：`src/adapters/inbound/ui/`
  - React + TypeScript UI适配器，通过 Tauri 调用 Rust 后端

### 出站适配器

- **存储适配器**：可按需实现并通过端口注入
  - 文件存储适配器
  - 数据库存储适配器（如需要）

- **协议适配器**：可按需实现并通过端口注入
  - MQTT适配器（如需要）
  - Modbus适配器（如需要）

## 依赖方向

```
适配器层 → 应用层端口 → 用例实现 → 领域层端口 → 基础设施实现
    ↓           ↓           ↓            ↓              ↓
  调用端口    定义接口    实现端口     定义接口      实现端口
```

**重要原则**：
- 依赖方向始终向内指向领域层
- 应用层端口依赖应用层的Commands和DTOs（正确）
- 领域层端口只依赖领域层的实体和值对象（正确）
