/**
 * 拓扑设计页面 - 浅色主题
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Node, Edge, Connection } from 'reactflow';
import FlowCanvas from '../components/topology/FlowCanvas';
import DevicePanel from '../components/topology/DevicePanel';
import DevicePropertiesPanel from '../components/topology/DevicePropertiesPanel';
import { Save, FolderOpen, Trash2, FilePlus, FileDown, CheckCircle } from 'lucide-react';
import { DeviceType, DEVICE_TYPE_TO_CN } from '../constants/deviceTypes';

interface DeviceData {
  id: string;
  name: string;
  device_type: string;
  properties: Record<string, any>;
  position?: { x: number; y: number; z: number };
}

interface ConnectionData {
  id: string;
  from: string;
  to: string;
  connection_type: string;
  properties?: Record<string, any>;
}

interface TopologyData {
  devices: DeviceData[];
  connections: ConnectionData[];
}

// 用于在标签切换时保持状态的 sessionStorage key
const TOPOLOGY_STATE_KEY = 'topology_canvas_state';

// 从 sessionStorage 恢复状态
function loadStateFromSession(): { nodes: Node[]; edges: Edge[]; counter: number } | null {
  try {
    const saved = sessionStorage.getItem(TOPOLOGY_STATE_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (e) {
    console.error('Failed to load topology state from session:', e);
  }
  return null;
}

// 保存状态到 sessionStorage
function saveStateToSession(nodes: Node[], edges: Edge[], counter: number) {
  try {
    sessionStorage.setItem(TOPOLOGY_STATE_KEY, JSON.stringify({ nodes, edges, counter }));
  } catch (e) {
    console.error('Failed to save topology state to session:', e);
  }
}

export default function TopologyDesign() {
  // 初始化时尝试从 sessionStorage 恢复状态
  const savedState = loadStateFromSession();
  
  const [nodes, setNodes] = useState<Node[]>(savedState?.nodes || []);
  const [edges, setEdges] = useState<Edge[]>(savedState?.edges || []);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showPropertiesPanel, setShowPropertiesPanel] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');
  const deviceIdCounter = useRef(savedState?.counter || 1);

  // 更新节点和边
  const updateNodesAndEdges = useCallback((data: TopologyData) => {
    const newNodes: Node[] = data.devices.map((device) => ({
      id: device.id,
      type: 'device',
      position: device.position
        ? { x: device.position.x, y: device.position.y }
        : { x: Math.random() * 400, y: Math.random() * 400 },
      data: {
        name: device.name,
        deviceType: device.device_type,
        properties: device.properties,
      },
    }));

    const newEdges: Edge[] = data.connections.map((conn) => ({
      id: conn.id,
      source: conn.from,
      target: conn.to,
      type: 'connection',
      data: {
        connectionType: conn.connection_type,
        properties: conn.properties || {},
      },
    }));

    setNodes(newNodes);
    setEdges(newEdges);

    const maxId = data.devices.reduce((max, d) => {
      const match = d.id.match(/device-(\d+)/);
      return match ? Math.max(max, parseInt(match[1], 10)) : max;
    }, 0);
    deviceIdCounter.current = maxId + 1;
  }, []);

  // 标记是否已初始化，避免切换标签时清空画布
  const isInitialized = useRef(false);

  // 加载拓扑 - 只在首次加载时尝试恢复，不清空已有数据
  const loadTopology = useCallback(async () => {
    // 如果已经初始化过，不再重复加载（保留画布状态）
    if (isInitialized.current) {
      return;
    }
    isInitialized.current = true;
    
    // 首次加载时，可以尝试从文件恢复上次的拓扑（可选）
    // 如果不需要自动恢复，这里什么都不做，保持空画布
  }, []);

  // 保存拓扑
  const saveTopology = useCallback(async () => {
    setSaveStatus('saving');
    try {
      const topologyData: TopologyData = {
        devices: nodes.map((node) => ({
          id: node.id,
          name: node.data.name,
          device_type: node.data.deviceType,
          properties: node.data.properties || {},
          position: {
            x: node.position.x,
            y: node.position.y,
            z: 0,
          },
        })),
        connections: edges.map((edge) => ({
          id: edge.id,
          from: edge.source,
          to: edge.target,
          connection_type: edge.data?.connectionType || 'line',
          properties: edge.data?.properties || {},
        })),
      };

      await invoke('save_topology', {
        topologyData,
        path: 'topology.json',
      });

      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to save topology:', error);
      alert('保存失败：' + error);
      setSaveStatus('idle');
    }
  }, [nodes, edges]);

  // 加载拓扑文件
  const loadTopologyFromFile = useCallback(async () => {
    try {
      const topologyData = await invoke<TopologyData>('load_topology', {
        path: 'topology.json',
      });
      updateNodesAndEdges(topologyData);
    } catch (error) {
      console.error('Failed to load topology:', error);
      alert('加载失败：' + error);
    }
  }, [updateNodesAndEdges]);

  // 新建拓扑
  const newTopology = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setSelectedNode(null);
    setShowPropertiesPanel(false);
    deviceIdCounter.current = 1;
    // 清空 sessionStorage 中的状态
    sessionStorage.removeItem(TOPOLOGY_STATE_KEY);
  }, []);

  // 通过拖拽添加设备
  const handleDeviceAdd = useCallback((deviceType: DeviceType, position: { x: number; y: number }) => {
    const deviceId = deviceIdCounter.current++;
    const typeName = DEVICE_TYPE_TO_CN[deviceType] || deviceType;
    
    const newNode: Node = {
      id: `device-${deviceId}`,
      type: 'device',
      position,
      data: {
        name: `${typeName}-${deviceId}`,
        deviceType,
        properties: {},
      },
    };
    
    setNodes((nds) => [...nds, newNode]);
  }, []);

  // 通过点击添加设备
  const handleDeviceSelect = useCallback((deviceType: DeviceType) => {
    const gridSize = 20;
    const baseX = 100 + Math.floor(Math.random() * 10) * gridSize;
    const baseY = 100 + Math.floor(Math.random() * 10) * gridSize;
    handleDeviceAdd(deviceType, { x: baseX, y: baseY });
  }, [handleDeviceAdd]);

  // 删除选中节点
  const deleteSelectedNode = useCallback(() => {
    if (selectedNode) {
      const nodeId = selectedNode.id;
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) =>
        eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
      );
      setSelectedNode(null);
      setShowPropertiesPanel(false);
    }
  }, [selectedNode]);

  // 更新设备属性
  const updateDevice = useCallback(
    (deviceId: string, updates: { name: string; properties: Record<string, any> }) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === deviceId
            ? {
                ...node,
                data: {
                  ...node.data,
                  ...updates,
                },
              }
            : node
        )
      );
      setShowPropertiesPanel(false);
    },
    []
  );

  // 节点点击处理
  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
    setShowPropertiesPanel(true);
  }, []);

  // 处理连接
  const handleConnect = useCallback((_connection: Connection) => {
    // 连接已在 FlowCanvas 内部处理
  }, []);

  // 处理节点更新
  const handleNodesUpdate = useCallback((newNodes: Node[]) => {
    setNodes(newNodes);
  }, []);

  // 处理边更新
  const handleEdgesUpdate = useCallback((newEdges: Edge[]) => {
    setEdges(newEdges);
  }, []);

  // 快捷键处理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Delete' && selectedNode) {
        deleteSelectedNode();
      }
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveTopology();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNode, deleteSelectedNode, saveTopology]);

  useEffect(() => {
    loadTopology();
  }, [loadTopology]);

  // 状态变化时保存到 sessionStorage，用于标签切换时恢复
  useEffect(() => {
    saveStateToSession(nodes, edges, deviceIdCounter.current);
  }, [nodes, edges]);

  return (
    <div className="flex h-full bg-gray-50">
      {/* 左侧设备面板 */}
      <DevicePanel onDeviceSelect={handleDeviceSelect} />

      {/* 主区域 */}
      <div className="flex-1 flex flex-col">
        {/* 工具栏 */}
        <div className="px-3 py-2 bg-white border-b border-gray-200 flex items-center gap-2">
          <button
            onClick={newTopology}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors"
            title="新建拓扑"
          >
            <FilePlus className="w-4 h-4" />
            新建
          </button>
          <button
            onClick={saveTopology}
            disabled={saveStatus === 'saving'}
            className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 rounded text-white flex items-center gap-1.5 text-sm transition-colors disabled:opacity-50"
            title="保存拓扑 (Ctrl+S)"
          >
            {saveStatus === 'saved' ? (
              <CheckCircle className="w-4 h-4" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {saveStatus === 'saving' ? '保存中...' : saveStatus === 'saved' ? '已保存' : '保存'}
          </button>
          <button
            onClick={loadTopologyFromFile}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors"
            title="加载拓扑"
          >
            <FolderOpen className="w-4 h-4" />
            加载
          </button>
          <div className="w-px h-5 bg-gray-300 mx-1" />
          <button
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors"
            title="导出拓扑"
          >
            <FileDown className="w-4 h-4" />
            导出
          </button>

          <div className="flex-1" />

          <div className="text-xs text-gray-500">
            设备: {nodes.length} | 连接: {edges.length}
          </div>

          {selectedNode && (
            <button
              onClick={deleteSelectedNode}
              className="px-3 py-1.5 bg-red-500 hover:bg-red-600 rounded text-white flex items-center gap-1.5 text-sm transition-colors"
              title="删除选中设备 (Delete)"
            >
              <Trash2 className="w-4 h-4" />
              删除
            </button>
          )}
        </div>

        {/* 画布区域 */}
        <div className="flex-1 relative">
          <FlowCanvas
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesUpdate}
            onEdgesChange={handleEdgesUpdate}
            onConnect={handleConnect}
            onNodeClick={handleNodeClick}
            onDeviceAdd={handleDeviceAdd}
          />

          {/* 属性面板 */}
          {showPropertiesPanel && selectedNode && (
            <DevicePropertiesPanel
              device={{
                id: selectedNode.id,
                name: selectedNode.data.name,
                deviceType: selectedNode.data.deviceType,
                properties: selectedNode.data.properties || {},
              }}
              onClose={() => {
                setShowPropertiesPanel(false);
                setSelectedNode(null);
              }}
              onUpdate={updateDevice}
            />
          )}
        </div>
      </div>
    </div>
  );
}
