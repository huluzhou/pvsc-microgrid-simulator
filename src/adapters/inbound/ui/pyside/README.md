目录结构优化：

- topology/：拓扑相关 UI 组件封装层，稳定导出对外 API
  - 通过简单包装保持现有组件不变，逐步迁移 main_application 引用至该子包
- components/：现有具体 PySide 组件实现（暂不改动）
- assets/：拓扑与设备图标资源

使用建议：新代码请优先从 `pyside.topology` 引用，如 `from ...pyside.topology import TopologyCanvas`。
