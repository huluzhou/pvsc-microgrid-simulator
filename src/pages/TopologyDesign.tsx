/**
 * 拓扑设计页面 - 浅色主题
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { invoke } from '@tauri-apps/api/core';
import { open, save } from '@tauri-apps/plugin-dialog';
import { Node, Edge, Connection } from 'reactflow';
import FlowCanvas, { FlowCanvasRef } from '../components/topology/FlowCanvas';
import DevicePanel from '../components/topology/DevicePanel';
import DevicePropertiesPanel from '../components/topology/DevicePropertiesPanel';
import { Save, FolderOpen, Trash2, FilePlus, FileDown, CheckCircle, Undo2, Redo2, Copy, Clipboard, Scissors } from 'lucide-react';
import { DeviceType, DEVICE_TYPE_TO_CN } from '../constants/deviceTypes';
import { HistoryManager } from '../utils/historyManager';
import { performLinkageUpdatePhase3 } from '../components/topology/connectionDecision';

// 拓扑验证结果接口
interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

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
  from_port?: string | null;
  to_port?: string | null;
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
  // 获取当前路由位置，用于检测标签页切换
  const location = useLocation();
  
  // 初始化时尝试从 sessionStorage 恢复状态
  const savedState = loadStateFromSession();
  
  const [nodes, setNodes] = useState<Node[]>(savedState?.nodes || []);
  const [edges, setEdges] = useState<Edge[]>(savedState?.edges || []);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showPropertiesPanel, setShowPropertiesPanel] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');
  const deviceIdCounter = useRef(savedState?.counter || 1);
  
  // 历史记录管理器
  const historyManager = useRef(new HistoryManager());
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  
  // 剪贴板（用于复制/粘贴）
  const clipboardRef = useRef<{ nodes: Node[]; edges: Edge[] } | null>(null);
  
  // 是否正在从历史记录恢复（避免触发新的历史记录）
  const isRestoringRef = useRef(false);
  
  // 鼠标位置（用于粘贴时定位）
  const mousePositionRef = useRef<{ x: number; y: number } | null>(null);
  
  // FlowCanvas ref（用于调用 fitView）
  const flowCanvasRef = useRef<FlowCanvasRef>(null);
  
  // 标记是否已经适配过视图（避免重复适配）
  const hasFittedViewRef = useRef(false);
  
  // 处理鼠标移动
  const handleMouseMove = useCallback((position: { x: number; y: number }) => {
    mousePositionRef.current = position;
  }, []);

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

    const newEdges: Edge[] = data.connections.map((conn) => {
      // 修复 Handle ID 匹配问题：
      // - source Handle 的 ID 格式是 `${portId}-source`（例如 "top-source"）
      // - target Handle 的 ID 格式是 `${portId}`（例如 "center"）
      const sourceHandle = conn.from_port 
        ? (conn.from_port.includes('-source') ? conn.from_port : `${conn.from_port}-source`)
        : undefined;
      const targetHandle = conn.to_port || undefined;
      
      return {
        id: conn.id,
        source: conn.from,
        target: conn.to,
        sourceHandle,
        targetHandle,
        type: 'connection',
        data: {
          connectionType: conn.connection_type,
          properties: conn.properties || {},
        },
      };
    });

    // 导入后触发联动更新，确保设备属性正确设置
    // 对每个连接执行联动更新
    let updatedNodes = newNodes;
    for (const edge of newEdges) {
      const sourceNode = updatedNodes.find(n => n.id === edge.source);
      const targetNode = updatedNodes.find(n => n.id === edge.target);
      
      if (sourceNode && targetNode) {
        const connection: Connection = {
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.sourceHandle ? edge.sourceHandle : null,
          targetHandle: edge.targetHandle ? edge.targetHandle : null,
        };
        
        // 执行联动更新
        updatedNodes = performLinkageUpdatePhase3(connection, updatedNodes, newEdges);
      }
    }

    setNodes(updatedNodes);
    setEdges(newEdges);

    const maxId = data.devices.reduce((max, d) => {
      const match = d.id.match(/device-(\d+)/);
      return match ? Math.max(max, parseInt(match[1], 10)) : max;
    }, 0);
    deviceIdCounter.current = maxId + 1;
    
    // 导入后自动适配视图，确保所有设备可见
    // 使用更长的延迟确保 ReactFlow 完全渲染
    // 使用 requestAnimationFrame 确保在下一帧渲染后再适配
    requestAnimationFrame(() => {
      setTimeout(() => {
        if (flowCanvasRef.current && updatedNodes.length > 0) {
          flowCanvasRef.current.fitView({ 
            padding: 0.1, // 10% 的边距
            duration: 300, // 300ms 的动画时长
          });
          // 标记已经适配过，避免路由切换时重复适配
          hasFittedViewRef.current = true;
        }
      }, 300); // 增加到 300ms，确保 ReactFlow 完全渲染
    });
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

  // 当前文件路径
  const [currentFilePath, setCurrentFilePath] = useState<string | null>(null);

  // 保存拓扑（弹出文件选择对话框）
  const saveTopology = useCallback(async () => {
    setSaveStatus('saving');
    try {
      // 弹出保存文件对话框
      const filePath = await save({
        defaultPath: currentFilePath || 'topology.json',
        filters: [
          { name: 'JSON 文件', extensions: ['json'] },
          { name: '所有文件', extensions: ['*'] },
        ],
        title: '保存拓扑文件',
      });

      if (!filePath) {
        setSaveStatus('idle');
        return; // 用户取消了保存
      }

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
          from_port: edge.sourceHandle || null,
          to_port: edge.targetHandle || null,
          connection_type: edge.data?.connectionType || 'line',
          properties: edge.data?.properties || {},
        })),
      };

      await invoke('save_topology', {
        topologyData,
        path: filePath,
      });

      setCurrentFilePath(filePath);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to save topology:', error);
      alert('保存失败：' + error);
      setSaveStatus('idle');
    }
  }, [nodes, edges, currentFilePath]);

  // 快速保存（如果有当前文件路径，直接保存；否则弹出对话框）
  const quickSaveTopology = useCallback(async () => {
    if (!currentFilePath) {
      // 没有当前文件，弹出保存对话框
      saveTopology();
      return;
    }

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
          from_port: edge.sourceHandle || null,
          to_port: edge.targetHandle || null,
          connection_type: edge.data?.connectionType || 'line',
          properties: edge.data?.properties || {},
        })),
      };

      await invoke('save_topology', {
        topologyData,
        path: currentFilePath,
      });

      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to save topology:', error);
      alert('保存失败：' + error);
      setSaveStatus('idle');
    }
  }, [nodes, edges, currentFilePath, saveTopology]);

  // 加载拓扑文件（弹出文件选择对话框）
  const loadTopologyFromFile = useCallback(async () => {
    try {
      // 弹出打开文件对话框
      const filePath = await open({
        multiple: false,
        filters: [
          { name: 'JSON 文件', extensions: ['json'] },
          { name: '所有文件', extensions: ['*'] },
        ],
        title: '选择拓扑文件',
      });

      if (!filePath) {
        return; // 用户取消了选择
      }

      // 加载并验证拓扑文件
      const result = await invoke<{ data: TopologyData; validation: ValidationResult }>('load_and_validate_topology', {
        path: filePath,
      });

      // 显示验证结果
      if (!result.validation.valid) {
        // 仍然加载数据，但显示警告
        if (!confirm(`拓扑文件存在以下问题：\n\n${result.validation.errors.join('\n')}\n\n是否继续加载？`)) {
          return;
        }
      } else if (result.validation.warnings.length > 0) {
        console.warn('拓扑加载警告:', result.validation.warnings);
      }

      updateNodesAndEdges(result.data);
      setCurrentFilePath(filePath as string);
    } catch (error) {
      console.error('Failed to load topology:', error);
      alert('加载失败：' + error);
    }
  }, [updateNodesAndEdges]);

  // 导出拓扑为旧格式（pandapower 格式）
  const exportTopologyLegacy = useCallback(async () => {
    try {
      // 弹出保存文件对话框
      const filePath = await save({
        defaultPath: 'topology_pandapower.json',
        filters: [
          { name: 'JSON 文件', extensions: ['json'] },
          { name: '所有文件', extensions: ['*'] },
        ],
        title: '导出为 pandapower 格式',
      });

      if (!filePath) {
        return; // 用户取消了保存
      }

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
          from_port: edge.sourceHandle || null,
          to_port: edge.targetHandle || null,
          connection_type: edge.data?.connectionType || 'line',
          properties: edge.data?.properties || {},
        })),
      };

      await invoke('save_topology_legacy', {
        topologyData,
        path: filePath,
      });

      alert('导出成功！');
    } catch (error) {
      console.error('Failed to export topology:', error);
      alert('导出失败：' + error);
    }
  }, [nodes, edges]);

  // 新建拓扑
  const newTopology = useCallback(() => {
    setNodes([]);
    setEdges([]);
    deviceIdCounter.current = 1;
    isInitialized.current = false; // 重置初始化标志，允许重新加载
    // 重置视图到默认位置
    setTimeout(() => {
      if (flowCanvasRef.current) {
        flowCanvasRef.current.fitView({ 
          padding: 0.1,
          duration: 300,
        });
      }
    }, 100);
    setSelectedNode(null);
    setShowPropertiesPanel(false);
    setCurrentFilePath(null);
    deviceIdCounter.current = 1;
    // 清空 sessionStorage 中的状态
    sessionStorage.removeItem(TOPOLOGY_STATE_KEY);
  }, []);

  // 通过拖拽添加设备
  const handleDeviceAdd = useCallback((deviceType: DeviceType, position: { x: number; y: number }) => {
    // === 全局约束检查 ===
    // 外部电网设备数量限制（最多1个）
    if (deviceType === 'external_grid') {
      const existingExternalGrid = nodes.find(n => n.data.deviceType === 'external_grid');
      if (existingExternalGrid) {
        alert('外部电网设备数量已达上限（1个），无法继续添加');
        return;
      }
    }

    const deviceId = deviceIdCounter.current++;
    const typeName = DEVICE_TYPE_TO_CN[deviceType] || deviceType;
    
    const newNode: Node = {
      id: `device-${deviceId}`,
      type: 'device',
      position: {
        x: position.x || 100,
        y: position.y || 100,
      },
      data: {
        name: `${typeName}-${deviceId}`,
        deviceType,
        properties: {},
      },
    };
    
    // 使用函数式更新，确保立即应用
    setNodes((nds) => {
      const updated = [...nds, newNode];
      // 保存状态
      saveStateToSession(updated, edges, deviceIdCounter.current);
      return updated;
    });
  }, [nodes, edges]);

  // 通过点击添加设备
  const handleDeviceSelect = useCallback((deviceType: DeviceType) => {
    const gridSize = 20;
    const baseX = 100 + Math.floor(Math.random() * 10) * gridSize;
    const baseY = 100 + Math.floor(Math.random() * 10) * gridSize;
    handleDeviceAdd(deviceType, { x: baseX, y: baseY });
  }, [handleDeviceAdd]);

  // 删除选中的元素（节点和边）
  const deleteSelectedElements = useCallback(() => {
    // 获取所有选中的节点和边
    const selectedNodes = nodes.filter(n => n.selected);
    const selectedEdges = edges.filter(e => e.selected);
    
    if (selectedNodes.length === 0 && selectedEdges.length === 0) {
      // 如果没有选中的元素，尝试删除最后选中的节点（向后兼容）
      if (selectedNode) {
        const nodeId = selectedNode.id;
        setNodes((nds) => nds.filter((n) => n.id !== nodeId));
        setEdges((eds) =>
          eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
        );
        setSelectedNode(null);
        setShowPropertiesPanel(false);
      }
      return;
    }

    // 删除选中的节点
    if (selectedNodes.length > 0) {
      const selectedNodeIds = new Set(selectedNodes.map(n => n.id));
      setNodes((nds) => nds.filter((n) => !selectedNodeIds.has(n.id)));
      // 删除与这些节点相关的所有连接
      setEdges((eds) =>
        eds.filter((e) => !selectedNodeIds.has(e.source) && !selectedNodeIds.has(e.target))
      );
      
      // 如果当前选中的节点被删除，清除选中状态
      if (selectedNode && selectedNodeIds.has(selectedNode.id)) {
        setSelectedNode(null);
        setShowPropertiesPanel(false);
      }
    }

    // 删除选中的边
    if (selectedEdges.length > 0) {
      const selectedEdgeIds = new Set(selectedEdges.map(e => e.id));
      setEdges((eds) => eds.filter((e) => !selectedEdgeIds.has(e.id)));
    }
  }, [nodes, edges, selectedNode]);

  // 更新设备属性
  const updateDevice = useCallback(
    async (deviceId: string, updates: { name: string; properties: Record<string, any> }) => {
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
      
      // 保存历史记录
      setTimeout(() => {
        if (!isRestoringRef.current) {
          historyManager.current.snapshot({
            nodes,
            edges,
            counter: deviceIdCounter.current,
          });
          setCanUndo(historyManager.current.canUndo());
          setCanRedo(historyManager.current.canRedo());
        }
      }, 150);
    },
    [nodes, edges]
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

  // 初始化历史记录
  useEffect(() => {
    historyManager.current.initialize({
      nodes,
      edges,
      counter: deviceIdCounter.current,
    });
    setCanUndo(false);
    setCanRedo(false);
  }, []); // 只在组件挂载时初始化一次

  // 处理节点更新
  const handleNodesUpdate = useCallback((newNodes: Node[]) => {
    setNodes(newNodes);
    // 延迟保存历史记录，避免频繁操作时产生过多历史
    setTimeout(() => {
      if (!isRestoringRef.current) {
        historyManager.current.snapshot({
          nodes: newNodes,
          edges,
          counter: deviceIdCounter.current,
        });
        setCanUndo(historyManager.current.canUndo());
        setCanRedo(historyManager.current.canRedo());
      }
    }, 100);
  }, [edges]);

  // 处理边更新
  const handleEdgesUpdate = useCallback((newEdges: Edge[]) => {
    setEdges(newEdges);
    // 延迟保存历史记录
    setTimeout(() => {
      if (!isRestoringRef.current) {
        historyManager.current.snapshot({
          nodes,
          edges: newEdges,
          counter: deviceIdCounter.current,
        });
        setCanUndo(historyManager.current.canUndo());
        setCanRedo(historyManager.current.canRedo());
      }
    }, 100);
  }, [nodes]);

  // 处理节点删除（由FlowCanvas的onNodesDelete触发）
  const handleNodesDelete = useCallback((deletedNodes: Node[]) => {
    // 如果删除的节点中包含当前选中的节点，清除选中状态
    if (selectedNode && deletedNodes.some(n => n.id === selectedNode.id)) {
      setSelectedNode(null);
      setShowPropertiesPanel(false);
    }
  }, [selectedNode]);

  // 处理边删除（由FlowCanvas的onEdgesDelete触发）
  const handleEdgesDelete = useCallback((_deletedEdges: Edge[]) => {
    // 边删除不需要额外处理，状态已由FlowCanvas更新
  }, []);

  // 撤销操作
  const handleUndo = useCallback(() => {
    if (!historyManager.current.canUndo()) return;
    
    isRestoringRef.current = true;
    const state = historyManager.current.undo();
    if (state) {
      setNodes(state.nodes);
      setEdges(state.edges);
      deviceIdCounter.current = state.counter;
      setCanUndo(historyManager.current.canUndo());
      setCanRedo(historyManager.current.canRedo());
    }
    setTimeout(() => {
      isRestoringRef.current = false;
    }, 200);
  }, []);

  // 恢复操作
  const handleRedo = useCallback(() => {
    if (!historyManager.current.canRedo()) return;
    
    isRestoringRef.current = true;
    const state = historyManager.current.redo();
    if (state) {
      setNodes(state.nodes);
      setEdges(state.edges);
      deviceIdCounter.current = state.counter;
      setCanUndo(historyManager.current.canUndo());
      setCanRedo(historyManager.current.canRedo());
    }
    setTimeout(() => {
      isRestoringRef.current = false;
    }, 200);
  }, []);

  // 复制选中的元素
  const handleCopy = useCallback(() => {
    const selectedNodes = nodes.filter(n => n.selected);
    const selectedEdges = edges.filter(e => e.selected);
    
    if (selectedNodes.length === 0 && selectedEdges.length === 0) {
      // 如果没有选中的元素，尝试复制最后选中的节点
      if (selectedNode) {
        clipboardRef.current = {
          nodes: [selectedNode],
          edges: edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id),
        };
      }
      return;
    }

    // 只复制选中的节点之间的连接
    const selectedNodeIds = new Set(selectedNodes.map(n => n.id));
    const copiedEdges = selectedEdges.filter(e => 
      selectedNodeIds.has(e.source) && selectedNodeIds.has(e.target)
    );

    clipboardRef.current = {
      nodes: selectedNodes,
      edges: copiedEdges,
    };
  }, [nodes, edges, selectedNode]);

  // 剪切选中的元素（复制+删除）
  const handleCut = useCallback(() => {
    handleCopy();
    // 删除选中的元素
    deleteSelectedElements();
  }, [handleCopy, deleteSelectedElements]);

  // 粘贴元素
  const handlePaste = useCallback(() => {
    if (!clipboardRef.current) return;

    const { nodes: copiedNodes, edges: copiedEdges } = clipboardRef.current;
    if (copiedNodes.length === 0) return;

    // 检查是否有外部电网，如果画布中已存在外部电网，则不允许粘贴外部电网
    const hasExternalGridInClipboard = copiedNodes.some(n => n.data.deviceType === 'external_grid');
    if (hasExternalGridInClipboard) {
      const existingExternalGrid = nodes.find(n => n.data.deviceType === 'external_grid');
      if (existingExternalGrid) {
        alert('画布中已存在外部电网设备，无法粘贴外部电网（最多只能有1个外部电网）');
        return;
      }
    }

    // 计算粘贴位置
    // 如果有鼠标位置，使用鼠标位置；否则使用第一个节点的位置
    const pastePosition: { x: number; y: number } = mousePositionRef.current || 
      (copiedNodes[0]?.position || { x: 100, y: 100 });

    // 计算所有复制节点的中心点
    const copiedCenter = copiedNodes.reduce(
      (acc, node) => ({
        x: acc.x + node.position.x,
        y: acc.y + node.position.y,
      }),
      { x: 0, y: 0 }
    );
    const centerX = copiedCenter.x / copiedNodes.length;
    const centerY = copiedCenter.y / copiedNodes.length;

    // 生成新的节点ID映射
    const nodeIdMap = new Map<string, string>();
    const newNodes: Node[] = copiedNodes.map((node) => {
      const newDeviceId = deviceIdCounter.current++;
      const newId = `device-${newDeviceId}`;
      nodeIdMap.set(node.id, newId);
      
      // 获取设备类型的中文名称
      const deviceType = node.data.deviceType as DeviceType;
      const typeName = DEVICE_TYPE_TO_CN[deviceType] || deviceType;
      
      // 清除连接相关的属性（这些会在重新连接时更新）
      const cleanProperties = { ...node.data.properties };
      // 根据设备类型清除相应的连接属性
      if (deviceType === 'bus') {
        // 母线没有连接属性需要清除
      } else if (deviceType === 'line') {
        delete cleanProperties.from_bus;
        delete cleanProperties.to_bus;
      } else if (deviceType === 'transformer') {
        delete cleanProperties.hv_bus;
        delete cleanProperties.lv_bus;
      } else if (deviceType === 'switch') {
        delete cleanProperties.bus;
        delete cleanProperties.element_type;
        delete cleanProperties.element;
      } else if (deviceType === 'meter') {
        delete cleanProperties.element_type;
        delete cleanProperties.element;
        delete cleanProperties.side;
      } else {
        // 其他电力设备（static_generator, storage, load, charger, external_grid）
        delete cleanProperties.bus;
      }
      
      // 计算新位置：相对于原中心点的偏移，然后平移到鼠标位置
      const offsetX = node.position.x - centerX;
      const offsetY = node.position.y - centerY;
      return {
        ...node,
        id: newId,
        position: {
          x: pastePosition.x + offsetX,
          y: pastePosition.y + offsetY,
        },
        data: {
          ...node.data,
          name: `${typeName}-${newDeviceId}`, // 使用新的设备ID更新名称
          properties: cleanProperties, // 使用清理后的属性
        },
        selected: false, // 取消选中状态
      };
    });

    // 生成新的边，更新source和target ID
    // 只保留连接两个已粘贴节点的边
    const newEdges: Edge[] = copiedEdges
      .filter((edge) => {
        // 确保边的source和target都在粘贴的节点中
        return nodeIdMap.has(edge.source) && nodeIdMap.has(edge.target);
      })
      .map((edge) => {
        const newId = `edge-${nodeIdMap.get(edge.source)}-${nodeIdMap.get(edge.target)}-${Date.now()}`;
        return {
          ...edge,
          id: newId,
          source: nodeIdMap.get(edge.source)!,
          target: nodeIdMap.get(edge.target)!,
          selected: false,
        };
      });

    // 添加到画布
    const updatedNodes = [...nodes, ...newNodes];
    const updatedEdges = [...edges, ...newEdges];
    
    setNodes(updatedNodes);
    setEdges(updatedEdges);

    // 保存历史记录（使用更新后的状态）
    setTimeout(() => {
      if (!isRestoringRef.current) {
        historyManager.current.snapshot({
          nodes: updatedNodes,
          edges: updatedEdges,
          counter: deviceIdCounter.current,
        });
        setCanUndo(historyManager.current.canUndo());
        setCanRedo(historyManager.current.canRedo());
      }
    }, 150);
  }, [nodes, edges]);

  // 快捷键处理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 如果焦点在输入框等元素上，不处理快捷键
      if (e.target instanceof HTMLInputElement || 
          e.target instanceof HTMLTextAreaElement ||
          (e.target as HTMLElement)?.isContentEditable) {
        return;
      }

      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 's':
            e.preventDefault();
            quickSaveTopology();
            break;
          case 'z':
            e.preventDefault();
            if (e.shiftKey) {
              handleRedo();
            } else {
              handleUndo();
            }
            break;
          case 'y':
            e.preventDefault();
            handleRedo();
            break;
          case 'c':
            e.preventDefault();
            handleCopy();
            break;
          case 'v':
            e.preventDefault();
            handlePaste();
            break;
          case 'x':
            e.preventDefault();
            handleCut();
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [quickSaveTopology, handleUndo, handleRedo, handleCopy, handlePaste, handleCut]);

  useEffect(() => {
    loadTopology();
  }, [loadTopology]);

  // 状态变化时保存到 sessionStorage，用于标签切换时恢复
  useEffect(() => {
    saveStateToSession(nodes, edges, deviceIdCounter.current);
  }, [nodes, edges]);

  // 当路由切换到拓扑设计页面时，如果有设备，自动适配视图
  useEffect(() => {
    // 检查是否在拓扑设计页面
    if (location.pathname === '/topology' || location.pathname === '/') {
      // 如果有设备，延迟一点后适配视图（确保 ReactFlow 已经渲染完成）
      if (nodes.length > 0 && flowCanvasRef.current) {
        // 重置适配标记，允许重新适配
        hasFittedViewRef.current = false;
        
        let timer: ReturnType<typeof setTimeout> | null = null;
        let rafId: number | null = null;
        
        // 使用 requestAnimationFrame 确保在下一帧渲染后再适配
        rafId = requestAnimationFrame(() => {
          timer = setTimeout(() => {
            if (flowCanvasRef.current && !hasFittedViewRef.current) {
              flowCanvasRef.current.fitView({ 
                padding: 0.1,
                duration: 300,
              });
              hasFittedViewRef.current = true;
            }
          }, 300); // 300ms 延迟，确保 ReactFlow 完全渲染
        });
        
        return () => {
          if (rafId !== null) {
            cancelAnimationFrame(rafId);
          }
          if (timer !== null) {
            clearTimeout(timer);
          }
        };
      }
    }
  }, [location.pathname, nodes.length]);

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
            onClick={exportTopologyLegacy}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors"
            title="导出为 pandapower 格式"
          >
            <FileDown className="w-4 h-4" />
            导出
          </button>

          <div className="w-px h-5 bg-gray-300 mx-1" />

          {/* 撤销/恢复 */}
          <button
            onClick={handleUndo}
            disabled={!canUndo}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="撤销 (Ctrl+Z)"
          >
            <Undo2 className="w-4 h-4" />
            撤销
          </button>
          <button
            onClick={handleRedo}
            disabled={!canRedo}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="恢复 (Ctrl+Y 或 Ctrl+Shift+Z)"
          >
            <Redo2 className="w-4 h-4" />
            恢复
          </button>

          <div className="w-px h-5 bg-gray-300 mx-1" />

          {/* 复制/粘贴/剪切 */}
          <button
            onClick={handleCopy}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors"
            title="复制 (Ctrl+C)"
          >
            <Copy className="w-4 h-4" />
            复制
          </button>
          <button
            onClick={handlePaste}
            disabled={!clipboardRef.current}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="粘贴 (Ctrl+V)"
          >
            <Clipboard className="w-4 h-4" />
            粘贴
          </button>
          <button
            onClick={handleCut}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 flex items-center gap-1.5 text-sm transition-colors"
            title="剪切 (Ctrl+X)"
          >
            <Scissors className="w-4 h-4" />
            剪切
          </button>

          <div className="flex-1" />

          <div className="text-xs text-gray-500 flex items-center gap-2">
            <span>设备: {nodes.length} | 连接: {edges.length}</span>
            <span className="text-gray-400">|</span>
            <span className="text-gray-400">提示: 框选或点击选择，按 Delete 键删除</span>
          </div>

          {(selectedNode || nodes.some(n => n.selected) || edges.some(e => e.selected)) && (
            <button
              onClick={deleteSelectedElements}
              className="px-3 py-1.5 bg-red-500 hover:bg-red-600 rounded text-white flex items-center gap-1.5 text-sm transition-colors"
              title="删除选中元素 (Delete)"
            >
              <Trash2 className="w-4 h-4" />
              删除
            </button>
          )}
        </div>

        {/* 画布区域 */}
        <div className="flex-1 relative">
          <FlowCanvas
            ref={flowCanvasRef}
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesUpdate}
            onEdgesChange={handleEdgesUpdate}
            onNodesDelete={handleNodesDelete}
            onEdgesDelete={handleEdgesDelete}
            onConnect={handleConnect}
            onNodeClick={handleNodeClick}
            onDeviceAdd={handleDeviceAdd}
            onMouseMove={handleMouseMove}
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
              allNodes={nodes}
            />
          )}
        </div>
      </div>
    </div>
  );
}
