import { useState, useCallback, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Node, Edge, Connection } from "reactflow";
import FlowCanvas from "../components/topology/FlowCanvas";
import DevicePropertiesPanel from "../components/topology/DevicePropertiesPanel";
import { Save, FolderOpen, Trash2 } from "lucide-react";

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

export default function TopologyDesign() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showPropertiesPanel, setShowPropertiesPanel] = useState(false);

  // 加载拓扑数据
  const loadTopology = useCallback(async () => {
    try {
      // 这里应该从文件加载，暂时使用空数据
      const topologyData: TopologyData = {
        devices: [],
        connections: [],
      };
      updateNodesAndEdges(topologyData);
    } catch (error) {
      console.error("Failed to load topology:", error);
    }
  }, []);

  // 更新节点和边
  const updateNodesAndEdges = useCallback((data: TopologyData) => {
    const newNodes: Node[] = data.devices.map((device) => ({
      id: device.id,
      type: "device",
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
      type: "connection",
      data: {
        connectionType: conn.connection_type,
        properties: conn.properties || {},
      },
    }));

    setNodes(newNodes);
    setEdges(newEdges);
  }, []);

  // 保存拓扑
  const saveTopology = useCallback(async () => {
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
          connection_type: edge.data?.connectionType || "line",
          properties: edge.data?.properties || {},
        })),
      };

      // 调用 Tauri 命令保存
      await invoke("save_topology", {
        topologyData,
        path: "topology.json",
      });

      alert("拓扑保存成功！");
    } catch (error) {
      console.error("Failed to save topology:", error);
      alert("保存失败：" + error);
    }
  }, [nodes, edges]);

  // 加载拓扑
  const loadTopologyFromFile = useCallback(async () => {
    try {
      const topologyData = await invoke<TopologyData>("load_topology", {
        path: "topology.json",
      });
      updateNodesAndEdges(topologyData);
    } catch (error) {
      console.error("Failed to load topology:", error);
      alert("加载失败：" + error);
    }
  }, [updateNodesAndEdges]);

  // 添加设备
  const addDevice = useCallback((deviceType: string) => {
    const newId = `device-${Date.now()}`;
    const newNode: Node = {
      id: newId,
      type: "device",
      position: {
        x: Math.random() * 400 + 100,
        y: Math.random() * 400 + 100,
      },
      data: {
        name: `${deviceType}-${newId.slice(-4)}`,
        deviceType,
        properties: {},
      },
    };
    setNodes((nds) => [...nds, newNode]);
  }, []);

  // 删除选中节点
  const deleteSelectedNode = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
      setEdges((eds) =>
        eds.filter(
          (e) => e.source !== selectedNode.id && e.target !== selectedNode.id
        )
      );
      setSelectedNode(null);
      setShowPropertiesPanel(false);
    }
  }, [selectedNode]);

  // 更新设备属性
  const updateDevice = useCallback(
    (deviceId: string, updates: any) => {
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
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedNode(node);
      setShowPropertiesPanel(true);
    },
    []
  );

  useEffect(() => {
    loadTopology();
  }, [loadTopology]);

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="p-4 bg-gray-800 border-b border-gray-700 flex items-center gap-2">
        <button
          onClick={saveTopology}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white flex items-center gap-2 transition-colors"
        >
          <Save className="w-4 h-4" />
          保存
        </button>
        <button
          onClick={loadTopologyFromFile}
          className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-white flex items-center gap-2 transition-colors"
        >
          <FolderOpen className="w-4 h-4" />
          加载
        </button>
        <div className="flex-1" />
        <div className="flex gap-2">
          <button
            onClick={() => addDevice("Pv")}
            className="px-3 py-2 bg-orange-600 hover:bg-orange-700 rounded text-white text-sm transition-colors"
          >
            光伏
          </button>
          <button
            onClick={() => addDevice("Storage")}
            className="px-3 py-2 bg-green-600 hover:bg-green-700 rounded text-white text-sm transition-colors"
          >
            储能
          </button>
          <button
            onClick={() => addDevice("Load")}
            className="px-3 py-2 bg-red-600 hover:bg-red-700 rounded text-white text-sm transition-colors"
          >
            负载
          </button>
          <button
            onClick={() => addDevice("Charger")}
            className="px-3 py-2 bg-cyan-600 hover:bg-cyan-700 rounded text-white text-sm transition-colors"
          >
            充电桩
          </button>
        </div>
        {selectedNode && (
          <button
            onClick={deleteSelectedNode}
            className="px-3 py-2 bg-red-600 hover:bg-red-700 rounded text-white flex items-center gap-2 transition-colors"
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
          onNodesChange={setNodes}
          onEdgesChange={setEdges}
          onConnect={(connection: Connection) => {
            if (connection.source && connection.target) {
              const newEdge: Edge = {
                ...connection,
                id: `edge-${connection.source}-${connection.target}`,
                type: "connection",
                source: connection.source,
                target: connection.target,
              };
              setEdges((eds) => [...eds, newEdge]);
            }
          }}
          onNodeClick={handleNodeClick}
        />
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
  );
}
