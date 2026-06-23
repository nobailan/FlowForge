import { useCallback, useRef, useState, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls as RFControls,
  MiniMap,
  type ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useCanvasStore } from '../../store/canvasStore';
import { useAppStore } from '../../store/appStore';
import { nodeTypes } from './nodes';
import { edgeTypes } from './edges';

export default function FlowCanvas() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
  } = useCanvasStore();

  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const selectNode = useCanvasStore((s) => s.selectNode);

  // 监听连线 label 编辑事件
  useEffect(() => {
    const handler = (e: Event) => {
      const { edgeId, label } = (e as CustomEvent).detail;
      useCanvasStore.getState().updateEdgeLabel(edgeId, label);
    };
    window.addEventListener('flowforge:update-edge-label', handler);
    return () => window.removeEventListener('flowforge:update-edge-label', handler);
  }, []);

  // 监听 Agent 活动事件 → 画布节点状态联动
  useEffect(() => {
    const handler = (e: Event) => {
      const { nodeId, status, text } = (e as CustomEvent).detail;
      useCanvasStore.getState().updateNodeRuntimeData(nodeId, {
        _status: status,
        _output: text ? text.slice(0, 100) : undefined,
      });
    };
    window.addEventListener('flowforge:node-activity', handler);
    return () => window.removeEventListener('flowforge:node-activity', handler);
  }, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow-type');
      if (!type || !reactFlowInstance) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      addNode(type, position);
    },
    [reactFlowInstance, addNode]
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: any) => {
      selectNode(node.id);
      // 执行中不覆盖监控面板，只选中节点（在画布上高亮）
      const status = useAppStore.getState().executionStatus;
      if (status !== 'running') {
        setRightPanel('config');
      }
    },
    [selectNode, setRightPanel]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // 当 React Flow 删除节点时同步清理 selectedNodeId
  const handleNodesChange: typeof onNodesChange = useCallback((changes) => {
    for (const change of changes) {
      if (change.type === 'remove') {
        const removedId = change.id;
        const { selectedNodeId } = useCanvasStore.getState();
        if (removedId === selectedNodeId) {
          useCanvasStore.getState().selectNode(null);
          useAppStore.getState().setRightPanel(null);
        }
      }
    }
    onNodesChange(changes);
  }, [onNodesChange]);

  const defaultEdgeOptions = {
    markerEnd: { type: 'arrowclosed' as const, width: 16, height: 16, color: '#94a3b8' },
  };

  return (
    <div ref={reactFlowWrapper} className="flex-1 h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        snapToGrid
        snapGrid={[20, 20]}
        deleteKeyCode={['Backspace', 'Delete']}
      >
        {/* 箭头标记定义 */}
        <svg>
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={6} markerHeight={6} orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
            </marker>
            <marker id="arrow-selected" viewBox="0 0 10 10" refX={9} refY={5} markerWidth={6} markerHeight={6} orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#3b82f6" />
            </marker>
          </defs>
        </svg>
        <Background gap={20} size={1} color="#e2e8f0" />
        <RFControls position="bottom-right" />
        <MiniMap
          position="bottom-left"
          style={{ width: 140, height: 90, backgroundColor: '#1e1e1e' }}
          maskColor="rgba(30,30,30,0.7)"
          nodeColor={(node) => {
            const colors: Record<string, string> = {
              llm: '#7aa2f7',
              tool: '#e0af68',
              retriever: '#9ece6a',
              subagent: '#bb9af7',
              condition: '#f7768e',
              loop: '#ff9e64',
            };
            return colors[node.type || ''] || '#666';
          }}
          nodeStrokeColor="#333"
        />
      </ReactFlow>
    </div>
  );
}
