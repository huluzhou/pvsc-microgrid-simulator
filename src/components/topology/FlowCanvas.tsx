/**
 * 拓扑画布组件 - 浅色主题
 * 基于ReactFlow，支持拖拽放置、网格吸附、连接规则验证
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
import { 
  DEVICE_TYPES, 
  DeviceType, 
  getConnectionError 
} from '../../constants/deviceTypes';

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

  // 处理节点变化 - 直接通知父组件
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      if (isDroppingRef.current) return;
      const updatedNodes = applyNodeChanges(changes, nodes);
      onNodesChangeExternal(updatedNodes);
    },
    [nodes, onNodesChangeExternal]
  );

  // 处理边变化 - 直接通知父组件
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      const updatedEdges = applyEdgeChanges(changes, edges);
      onEdgesChangeExternal(updatedEdges);
    },
    [edges, onEdgesChangeExternal]
  );

  // 连接验证
  const validateConnection = useCallback(
    (connection: Connection): { valid: boolean; reason?: string } => {
      const sourceNode = nodes.find((n) => n.id === connection.source);
      const targetNode = nodes.find((n) => n.id === connection.target);

      if (!sourceNode || !targetNode) {
        return { valid: false, reason: '节点不存在' };
      }

      const sourceType = sourceNode.data.deviceType as DeviceType;
      const targetType = targetNode.data.deviceType as DeviceType;

      // 不允许自连接
      if (connection.source === connection.target) {
        return { valid: false, reason: '不允许自连接' };
      }

      // 检查是否已存在连接
      const existingConnection = edges.find(
        (e) =>
          (e.source === connection.source && e.target === connection.target) ||
          (e.source === connection.target && e.target === connection.source)
      );
      if (existingConnection) {
        return { valid: false, reason: '连接已存在' };
      }

      // 使用连接规则检查
      const error = getConnectionError(sourceType, targetType);
      if (error) {
        return { valid: false, reason: error };
      }

      return { valid: true };
    },
    [nodes, edges]
  );

  // 处理连接
  const handleConnect = useCallback(
    (connection: Connection) => {
      const validation = validateConnection(connection);
      
      if (!validation.valid) {
        setErrorMessage(validation.reason || '连接不符合规则');
        setTimeout(() => setErrorMessage(null), 3000);
        return;
      }

      const newEdge: Edge = {
        id: `edge-${connection.source}-${connection.target}-${Date.now()}`,
        source: connection.source!,
        target: connection.target!,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        type: 'connection',
      };

      onEdgesChangeExternal(addEdge(newEdge, edges));
      onConnectExternal?.(connection);
    },
    [validateConnection, edges, onEdgesChangeExternal, onConnectExternal]
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

      const position = screenToFlowPosition({
        x: e.clientX,
        y: e.clientY,
      });

      // 网格吸附
      const snappedPosition = {
        x: Math.round(position.x / GRID_SIZE) * GRID_SIZE,
        y: Math.round(position.y / GRID_SIZE) * GRID_SIZE,
      };

      onDeviceAdd?.(deviceType, snappedPosition);

      setTimeout(() => {
        isDroppingRef.current = false;
      }, 100);
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
  }), []);

  return (
    <div 
      ref={reactFlowWrapper}
      className="w-full h-full bg-white select-none"
      style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
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
