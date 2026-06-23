import { create } from 'zustand';
import {
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  type XYPosition,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from '@xyflow/react';
import type { CanvasNodeData, CanvasEdgeData, CanvasData } from '../types/canvas';

interface CanvasStore {
  // React Flow state
  nodes: Node<CanvasNodeData>[];
  edges: Edge<CanvasEdgeData>[];
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  addNode: (type: string, position: XYPosition) => void;
  deleteSelected: () => void;

  // Selection
  selectedNodeId: string | null;
  selectNode: (id: string | null) => void;

  // Edge label
  updateEdgeLabel: (edgeId: string, label: string) => void;

  // Serialization
  toCanvasJSON: () => CanvasData;
  fromCanvasJSON: (data: CanvasData) => void;

  // Node config update
  updateNodeConfig: (nodeId: string, config: Record<string, any>) => void;
  updateNodeRuntimeData: (nodeId: string, data: {
    _status?: string;
    _output?: string;
    _tokens?: number;
    _latency_ms?: number;
  }) => void;
  clearAllRuntimeData: () => void;

  // Tracking
  _nodeCounter: number;
}

let _nodeCounter = 0;

export const useCanvasStore = create<CanvasStore>((set, get) => ({
  nodes: [],
  edges: [],
  selectedNodeId: null,
  _nodeCounter: 0,

  onNodesChange: (changes) => {
    set({ nodes: applyNodeChanges(changes, get().nodes) as Node<CanvasNodeData>[] });
  },

  onEdgesChange: (changes) => {
    set({ edges: applyEdgeChanges(changes, get().edges) as Edge<CanvasEdgeData>[] });
  },

  onConnect: (connection) => {
    // 从 condition/loop 节点连线时自动分配 label
    const sourceNode = get().nodes.find((n) => n.id === connection.source);
    let autoLabel = '';
    if (sourceNode && (sourceNode.type === 'condition' || sourceNode.type === 'loop')) {
      const outEdges = get().edges.filter((e) => e.source === connection.source);
      if (sourceNode.type === 'condition') {
        autoLabel = outEdges.length === 0 ? 'true' : 'false';
      } else {
        autoLabel = outEdges.length === 0 ? 'continue' : 'exit';
      }
    }
    const edge: Edge<CanvasEdgeData> = {
      ...connection,
      id: `edge_${connection.source}_${connection.target}_${Date.now()}`,
      label: autoLabel,
      data: { source: connection.source, target: connection.target, label: autoLabel },
    };
    set({ edges: addEdge(edge, get().edges) as Edge<CanvasEdgeData>[] });
  },

  addNode: (type: string, position: XYPosition) => {
    _nodeCounter++;
    const id = `${type}_${_nodeCounter}`;
    const newNode: Node<CanvasNodeData> = {
      id,
      type, // React Flow will map this to custom node component
      position,
      data: {
        id,
        type,
        label: type.charAt(0).toUpperCase() + type.slice(1),
        config: {},
        position: { x: position.x, y: position.y },
      },
    };
    set({ nodes: [...get().nodes, newNode], _nodeCounter });
  },

  deleteSelected: () => {
    const { nodes, edges, selectedNodeId } = get();
    if (!selectedNodeId) return;
    set({
      nodes: nodes.filter((n) => n.id !== selectedNodeId),
      edges: edges.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId),
      selectedNodeId: null,
    });
  },

  selectNode: (id) => set({ selectedNodeId: id }),

  updateEdgeLabel: (edgeId, label) => {
    set({
      edges: get().edges.map((e) =>
        e.id === edgeId
          ? { ...e, label, data: { ...e.data, label } }
          : e
      ),
    });
  },

  toCanvasJSON: (): CanvasData => {
    const { nodes, edges } = get();
    return {
      nodes: nodes.map((n) => ({
        id: n.id,
        type: n.data.type,
        label: n.data.label,
        config: n.data.config,
        position: n.position,
      })),
      edges: edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: (e.data?.label as string) || (e.label as string) || '',
      })),
    };
  },

  fromCanvasJSON: (data: CanvasData) => {
    const nodes: Node<CanvasNodeData>[] = data.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: { ...n },
    }));
    const edges: Edge<CanvasEdgeData>[] = data.edges.map((e, i) => ({
      id: `edge_${i}_${Date.now()}`,
      source: e.source,
      target: e.target,
      label: e.label,
      data: { source: e.source, target: e.target, label: e.label },
    }));
    set({ nodes, edges });
    // Update counter to avoid ID collisions
    _nodeCounter = Math.max(_nodeCounter, data.nodes.length);
  },

  updateNodeConfig: (nodeId, config) => {
    set({
      nodes: get().nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, config: { ...n.data.config, ...config } } } : n
      ),
    });
  },

  updateNodeRuntimeData: (nodeId, data) => {
    set({
      nodes: get().nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n
      ),
    });
  },

  clearAllRuntimeData: () => {
    set({
      nodes: get().nodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          _status: undefined,
          _output: undefined,
          _tokens: undefined,
          _latency_ms: undefined,
        },
      })),
    });
  },
}));
