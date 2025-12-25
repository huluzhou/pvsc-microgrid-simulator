端口索引

- 领域拓扑端口：`src/domain/aggregates/topology/ports/`
  - `topology_use_case_ports.py`：用例端口接口
  - `topology_repository_port.py`：仓储端口接口

- 入站适配器：`src/adapters/inbound/topology/ui/topology_ui_adapter.py`
- 出站适配器：`src/adapters/external_services/protocols/`

- 建议：如需集中管理通用端口，可新增 `src/ports/` 统一导出。
