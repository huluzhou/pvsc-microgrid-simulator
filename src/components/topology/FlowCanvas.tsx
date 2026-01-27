/**
 * 拓扑画布组件 - 浅色主题
 * 基于ReactFlow，支持拖拽放置、网格吸附、连接规则验证
 * 
 * 连接决策流程参考：doc/TopoRule.md
 * 连接逻辑实现：./connectionDecision.ts
 */
import { useCallback, useRef, useState, useMemo, useEffect, DragEvent } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Connection,
  Controls,
  Background,
  MiniMap,
  BackgroundVariant,
  addEdge,
  NodeChange,
  EdgeChange,
  ReactFlowProvider,
  useReactFlow,
  ConnectionLineType,
  applyNodeChanges,
  applyEdgeChanges,
} from 'reactflow';
import 'reactflow/dist/style.css';
import DeviceNode from './DeviceNode';
import ConnectionEdge from './ConnectionEdge';
import { DEVICE_TYPES, DeviceType } from '../../constants/deviceTypes';
import {
  validateConnectionPhase1,
  performLinkageUpdatePhase3,
  performReverseLinkage,
} from './connectionDecision';

// 网格大小
const GRID_SIZE = 20;

// 节点类型配置
const nodeTypes = {
  device: DeviceNode,
};

// 边类型配置
const edgeTypes = {
  connection: ConnectionEdge,
};

// 默认边配置 - 直线
const defaultEdgeOptions = {
  type: 'connection',
  style: { stroke: '#666', strokeWidth: 2 },
  selectable: true, // 允许选择边
};

interface FlowCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (nodes: Node[]) => void;
  onEdgesChange: (edges: Edge[]) => void;
  onConnect?: (connection: Connection) => void;
  onNodeClick?: (event: React.MouseEvent, node: Node) => void;
  onDeviceAdd?: (deviceType: DeviceType, position: { x: number; y: number }) => void;
  onNodesDelete?: (nodes: Node[]) => void;
  onEdgesDelete?: (edges: Edge[]) => void;
  onMouseMove?: (position: { x: number; y: number }) => void;
}

// 错误提示组件
function ErrorToast({ 
  message, 
  onClose 
}: { 
  message: string; 
  onClose: () => void;
}) {
  return (
    <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-50 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg max-w-md text-sm">
      <div className="flex items-center gap-2">
        <span>{message}</span>
        <button onClick={onClose} className="ml-2 hover:text-gray-200">✕</button>
      </div>
    </div>
  );
}

// 内部画布组件
function FlowCanvasInner({
  nodes,
  edges,
  onNodesChange: onNodesChangeExternal,
  onEdgesChange: onEdgesChangeExternal,
  onConnect: onConnectExternal,
  onNodeClick,
  onDeviceAdd,
  onNodesDelete,
  onEdgesDelete,
  onMouseMove,
}: FlowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition, getNodes, getEdges } = useReactFlow();
  
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const isDroppingRef = useRef(false);
  
  // 跟踪鼠标位置
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (onMouseMove) {
      const position = screenToFlowPosition({
        x: e.clientX,
        y: e.clientY,
      });
      onMouseMove(position);
    }
  }, [screenToFlowPosition, onMouseMove]);

  // ============================================================================
  // 节点变化处理
  // ============================================================================

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (isDroppingRef.current) return;
      const updatedNodes = applyNodeChanges(changes, nodes);
      onNodesChangeExternal(updatedNodes);
    },
    [nodes, onNodesChangeExternal]
  );

  // ============================================================================
  // 边变化处理 - 连接删除时执行反向联动
  // ============================================================================

  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      // 检查是否有删除操作，执行反向联动
      const removeChanges = changes.filter(c => c.type === 'remove');
      
      if (removeChanges.length > 0) {
        let currentNodes = nodes;
        for (const change of removeChanges) {
          if (change.type === 'remove') {
            const deletedEdge = edges.find(e => e.id === change.id);
            if (deletedEdge) {
              // 调用连接决策模块的反向联动函数
              // 传入剩余的edges（排除被删除的edge）
              const remainingEdges = edges.filter(e => e.id !== change.id);
              currentNodes = performReverseLinkage(deletedEdge, currentNodes, remainingEdges);
            }
          }
        }
        
        if (currentNodes !== nodes) {
          onNodesChangeExternal(currentNodes);
        }
      }

      const updatedEdges = applyEdgeChanges(changes, edges);
      onEdgesChangeExternal(updatedEdges);
    },
    [edges, nodes, onNodesChangeExternal, onEdgesChangeExternal]
  );

  // ============================================================================
  // 连接决策：阶段一 - 前置验证（用于 onConnect）
  // ============================================================================

  const validateConnection = useCallback(
    (connection: Connection) => {
      return validateConnectionPhase1(connection, nodes, edges);
    },
    [nodes, edges]
  );

  // ============================================================================
  // 连接决策：实时验证（用于拖拽时的视觉反馈）
  // ============================================================================
  // 注意：始终返回 true，允许所有连接点被捕获和高亮
  // 实际的连接验证在 handleConnect 中进行，这样可以先让用户看到连接点，再通过规则过滤
  const checkIsValidConnection = useCallback(
    (_connection: Connection): boolean => {
      // 始终返回 true，允许所有连接点显示高亮
      // 连接规则验证在 handleConnect 中执行
      return true;
    },
    []
  );

  // ============================================================================
  // 连接决策：完整流程（阶段一 + 阶段二 + 阶段三）
  // ============================================================================

  const handleConnect = useCallback(
    (connection: Connection) => {
      // === 阶段一：前置验证 ===
      const validation = validateConnection(connection);
      
      if (!validation.valid) {
        setErrorMessage(validation.reason || '连接不符合规则');
        setTimeout(() => setErrorMessage(null), 3000);
        return;
      }

      // 显示警告信息（但仍允许连接）
      if (validation.warning) {
        setErrorMessage(validation.warning);
        setTimeout(() => setErrorMessage(null), 5000);
      }

      // === 阶段二：创建连接 ===
      const newEdge: Edge = {
        id: `edge-${connection.source}-${connection.target}-${Date.now()}`,
        source: connection.source!,
        target: connection.target!,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        type: 'connection',
      };

      // === 阶段三：联动更新 ===
      const updatedNodes = performLinkageUpdatePhase3(connection, nodes, edges);
      if (updatedNodes !== nodes) {
        onNodesChangeExternal(updatedNodes);
      }

      onEdgesChangeExternal(addEdge(newEdge, edges));
      onConnectExternal?.(connection);
    },
    [validateConnection, edges, nodes, onNodesChangeExternal, onEdgesChangeExternal, onConnectExternal]
  );

  // 拖拽处理
  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();

      const deviceType = e.dataTransfer.getData('application/device-type') as DeviceType;
      if (!deviceType) return;

      isDroppingRef.current = true;

      // 获取画布内的位置
      const bounds = reactFlowWrapper.current?.getBoundingClientRect();
      if (!bounds) return;

      // 使用 project 函数将屏幕坐标转换为流程坐标
      const position = screenToFlowPosition({
        x: e.clientX,
        y: e.clientY,
      });

      // 网格吸附
      const snappedPosition = {
        x: Math.round(position.x / GRID_SIZE) * GRID_SIZE,
        y: Math.round(position.y / GRID_SIZE) * GRID_SIZE,
      };

      // 确保位置在视口内（如果位置无效，使用默认位置）
      const finalPosition = {
        x: isNaN(snappedPosition.x) || !isFinite(snappedPosition.x) ? 100 : snappedPosition.x,
        y: isNaN(snappedPosition.y) || !isFinite(snappedPosition.y) ? 100 : snappedPosition.y,
      };

      onDeviceAdd?.(deviceType, finalPosition);

      setTimeout(() => {
        isDroppingRef.current = false;
      }, 50);
    },
    [screenToFlowPosition, onDeviceAdd]
  );

  // MiniMap 节点颜色
  const minimapNodeColor = useCallback((node: Node) => {
    const deviceType = node.data?.deviceType as DeviceType;
    return DEVICE_TYPES[deviceType]?.color ?? '#999';
  }, []);

  // ============================================================================
  // 删除处理
  // ============================================================================

  const handleNodesDelete = useCallback(
    (deletedNodes: Node[]) => {
      if (deletedNodes.length === 0) return;
      
      // 获取被删除节点的ID
      const deletedNodeIds = new Set(deletedNodes.map(n => n.id));
      
      // 删除与这些节点相关的所有连接
      const remainingEdges = edges.filter(e => 
        !deletedNodeIds.has(e.source) && !deletedNodeIds.has(e.target)
      );
      
      // 对每个被删除的连接执行反向联动
      const edgesToDelete = edges.filter(e => 
        deletedNodeIds.has(e.source) || deletedNodeIds.has(e.target)
      );
      
      let updatedNodes = nodes.filter(n => !deletedNodeIds.has(n.id));
      
      // 执行反向联动（只对剩余的连接，因为节点已删除）
      for (const deletedEdge of edgesToDelete) {
        const remainingEdgesForLinkage = remainingEdges.filter(e => e.id !== deletedEdge.id);
        updatedNodes = performReverseLinkage(deletedEdge, updatedNodes, remainingEdgesForLinkage);
      }
      
      // 更新状态
      onNodesChangeExternal(updatedNodes);
      onEdgesChangeExternal(remainingEdges);
      onNodesDelete?.(deletedNodes);
    },
    [nodes, edges, onNodesChangeExternal, onEdgesChangeExternal, onNodesDelete]
  );

  const handleEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      if (deletedEdges.length === 0) return;
      
      const deletedEdgeIds = new Set(deletedEdges.map(e => e.id));
      const remainingEdges = edges.filter(e => !deletedEdgeIds.has(e.id));
      
      // 对每个被删除的连接执行反向联动
      let updatedNodes = nodes;
      for (const deletedEdge of deletedEdges) {
        updatedNodes = performReverseLinkage(deletedEdge, updatedNodes, remainingEdges);
      }
      
      // 更新状态
      if (updatedNodes !== nodes) {
        onNodesChangeExternal(updatedNodes);
      }
      onEdgesChangeExternal(remainingEdges);
      onEdgesDelete?.(deletedEdges);
    },
    [nodes, edges, onNodesChangeExternal, onEdgesChangeExternal, onEdgesDelete]
  );

  // 合并删除处理：同时删除节点和边
  const handleCombinedDelete = useCallback(
    (nodesToDelete: Node[], edgesToDelete: Edge[]) => {
      if (nodesToDelete.length === 0 && edgesToDelete.length === 0) return;

      // 获取被删除节点的ID
      const deletedNodeIds = new Set(nodesToDelete.map(n => n.id));

      // 计算需要删除的所有边：
      // 1. 用户选中的边
      // 2. 与删除节点相关的所有边
      const edgesToRemove = new Set([
        ...edgesToDelete.map(e => e.id),
        ...edges.filter(e => 
          deletedNodeIds.has(e.source) || deletedNodeIds.has(e.target)
        ).map(e => e.id)
      ]);

      // 计算剩余的边
      const remainingEdges = edges.filter(e => !edgesToRemove.has(e.id));

      // 计算剩余的节点
      let updatedNodes = nodes.filter(n => !deletedNodeIds.has(n.id));

      // 对所有被删除的边执行反向联动
      const allDeletedEdges = edges.filter(e => edgesToRemove.has(e.id));
      for (const deletedEdge of allDeletedEdges) {
        updatedNodes = performReverseLinkage(deletedEdge, updatedNodes, remainingEdges);
      }

      // 更新状态
      if (updatedNodes !== nodes) {
        onNodesChangeExternal(updatedNodes);
      }
      onEdgesChangeExternal(remainingEdges);
      
      if (nodesToDelete.length > 0) {
        onNodesDelete?.(nodesToDelete);
      }
      if (edgesToDelete.length > 0) {
        onEdgesDelete?.(edgesToDelete);
      }
    },
    [nodes, edges, onNodesChangeExternal, onEdgesChangeExternal, onNodesDelete, onEdgesDelete]
  );

  // 键盘事件处理 - 支持Delete键删除
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 如果焦点在输入框等元素上，不处理删除
      if (e.target instanceof HTMLInputElement || 
          e.target instanceof HTMLTextAreaElement ||
          (e.target as HTMLElement)?.isContentEditable) {
        return;
      }

      if (e.key === 'Delete' || e.key === 'Backspace') {
        const selectedNodes = getNodes().filter(n => n.selected);
        const selectedEdges = getEdges().filter(e => e.selected);
        
        if (selectedNodes.length > 0 || selectedEdges.length > 0) {
          e.preventDefault();
          handleCombinedDelete(selectedNodes, selectedEdges);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [getNodes, getEdges, handleCombinedDelete]);

  // ReactFlow 配置
  const reactFlowConfig = useMemo(() => ({
    fitView: false,
    defaultViewport: { x: 50, y: 50, zoom: 1 },
    minZoom: 0.3,
    maxZoom: 2,
    snapToGrid: true,
    snapGrid: [GRID_SIZE, GRID_SIZE] as [number, number],
    connectionLineType: ConnectionLineType.Straight,
    connectionLineStyle: { stroke: '#3b82f6', strokeWidth: 2 },
    nodesDraggable: true,
    nodesConnectable: true,
    elementsSelectable: true, // 控制节点和边的选择
    nodeDragThreshold: 5,
    selectNodesOnDrag: false,
    // 启用框选功能：禁用默认的拖拽平移，启用选择框
    panOnDrag: [1, 2], // 只有中键和右键可以平移，左键用于选择
    selectionOnDrag: true, // 启用拖拽选择框
    // 增加连接点捕获范围（类似 CAD 的捕捉功能）
    connectionRadius: 50,
  }), []);

  return (
    <div 
      ref={reactFlowWrapper}
      className="w-full h-full bg-white select-none"
      style={{ 
        userSelect: 'none', 
        WebkitUserSelect: 'none',
        // 缩放优化 - 确保子元素渲染清晰
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
      }}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onMouseMove={handleMouseMove}
    >
      {/* 错误提示 */}
      {errorMessage && (
        <ErrorToast 
          message={errorMessage} 
          onClose={() => setErrorMessage(null)} 
        />
      )}
      
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onNodesDelete={handleNodesDelete}
        onEdgesDelete={handleEdgesDelete}
        onConnect={handleConnect}
        onNodeClick={onNodeClick}
        isValidConnection={checkIsValidConnection}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        {...reactFlowConfig}
      >
        <Controls className="!bg-white !border-gray-200 !shadow-sm" />
        <MiniMap 
          nodeColor={minimapNodeColor}
          maskColor="rgba(240, 240, 240, 0.8)"
          className="!bg-gray-50 !border-gray-200"
        />
        <Background 
          variant={BackgroundVariant.Dots} 
          gap={GRID_SIZE} 
          size={1}
          color="#d1d5db"
        />
      </ReactFlow>
    </div>
  );
}

// 导出包装后的组件
export default function FlowCanvas(props: FlowCanvasProps) {
  return (
    <ReactFlowProvider>
      <FlowCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
