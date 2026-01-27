/**
 * 拓扑画布组件 - 浅色主题
 * 基于ReactFlow，支持拖拽放置、网格吸附、连接规则验证
 * 
 * 连接决策流程参考：doc/TopoRule.md
 * 连接逻辑实现：./connectionDecision.ts
 */
import { useCallback, useRef, useState, useMemo, DragEvent } from 'react';
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
  isConnectionValid,
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
};

interface FlowCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (nodes: Node[]) => void;
  onEdgesChange: (edges: Edge[]) => void;
  onConnect?: (connection: Connection) => void;
  onNodeClick?: (event: React.MouseEvent, node: Node) => void;
  onDeviceAdd?: (deviceType: DeviceType, position: { x: number; y: number }) => void;
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
}: FlowCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();
  
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const isDroppingRef = useRef(false);

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
    (connection: Connection): boolean => {
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
    elementsSelectable: true,
    nodeDragThreshold: 5,
    selectNodesOnDrag: false,
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
