端口索引

## 领域端口

- **拓扑端口**：`src/domain/aggregates/topology/ports/`
  - `topology_use_case_ports.py`：用例端口接口
  - `topology_repository_port.py`：仓储端口接口

## 适配器

- **入站适配器**：`src/adapters/inbound/ui/pyside/`
  - PySide6 UI适配器，调用应用层用例

- **出站适配器**：可按需实现并通过端口注入
  - 存储适配器（文件、数据库等）
  - 协议适配器（MQTT、Modbus等，如需要）

## 建议

如需集中管理通用端口，可新增 `src/ports/` 统一导出。
