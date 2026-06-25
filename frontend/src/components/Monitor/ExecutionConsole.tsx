import { useEffect, useRef, useState, useMemo } from 'react';
import { useAppStore } from '../../store/appStore';
import { useCanvasStore } from '../../store/canvasStore';
import { useExecutionConsole, type StreamingEvent } from '../../hooks/useExecutionConsole';
import NodeActivityCard from './NodeActivityCard';

const CONSOLE_BG = '#1a1b26';

export default function ExecutionConsole() {
  const executionStatus = useAppStore((s) => s.executionStatus);
  const executionId = useAppStore((s) => s.executionId);
  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const { nodeActivities, totalTokens, addEvent, reset } = useExecutionConsole();
  const nodes = useCanvasStore((s) => s.nodes);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Connect WebSocket
  useEffect(() => {
    if (!executionId || executionStatus !== 'running') return;
    reset();

    // 直连后端，不走 Vite proxy（proxy 对 WS 升级支持不稳定）
    const wsUrl = `ws://localhost:8000/api/execute/${executionId}/ws`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'streaming_event' && msg.data) {
          addEvent(msg.data as StreamingEvent);
        } else if (msg.type === 'node_event' && msg.data) {
          const d = msg.data;
          if (d.status === 'running') {
            addEvent({
              execution_id: d.execution_id,
              node_id: d.node_id,
              event_type: 'thinking',
              text: d.output_summary || d.input_summary || 'Started',
              timestamp: d.timestamp || Date.now() / 1000,
            });
          } else if (d.status === 'completed' || d.status === 'error') {
            addEvent({
              execution_id: d.execution_id,
              node_id: d.node_id,
              event_type: d.status === 'error' ? 'error' : 'completed',
              tokens_input: d.token_count || 0,
              text: (d.output_summary || '').slice(0, 200),
              timestamp: d.timestamp || Date.now() / 1000,
            });
          }
        }
      } catch (_) {}
    };

    ws.onerror = () => {
      // WebSocket 失败，用轮询兜底
      pollResult();
    };
    ws.onclose = () => {};

    // 轮询兜底
    const pollResult = async () => {
      try {
        const resp = await fetch(`/api/execute/${executionId}`);
        const data = await resp.json();
        if (data.status === 'completed' || data.status === 'failed') {
          const nodeOutputs = data.output_data?.node_outputs || {};
          for (const [nid, ndata] of Object.entries(nodeOutputs)) {
            const nd = ndata as any;
            addEvent({
              execution_id: executionId,
              node_id: nid,
              event_type: nd.status === 'error' ? 'error' : 'completed',
              tokens_input: nd.tokens || 0,
              timestamp: Date.now() / 1000,
            });
          }
          useAppStore.getState().setExecutionStatus(data.status);
        }
      } catch (_) {}
    };
    const pollTimer = setInterval(pollResult, 3000);
    setTimeout(() => clearInterval(pollTimer), 300000);

    return () => {
      ws.close();
      clearInterval(pollTimer);
    };
  }, [executionId]); // 只在 executionId 变化时重连，避免重复连接

  // Timer
  useEffect(() => {
    if (executionStatus === 'running') {
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [executionStatus]);

  // Sort nodes by topology order
  const sortedNodes = useMemo(() => {
    return [...nodes].sort((a, b) => a.position.y - b.position.y);
  }, [nodes]);

  const completedCount = Object.values(nodeActivities).filter(
    (n) => n.status === 'completed' || n.status === 'error'
  ).length;
  const totalNodes = nodes.length || 1;
  const progressPct = Math.round((completedCount / totalNodes) * 100);

  if (executionStatus === 'idle') {
    return (
      <div className="w-[420px] border-l bg-[#252526] p-4">
        <h3 className="font-semibold text-sm mb-2">执行控制台</h3>
        <p className="text-[#999] text-xs text-center mt-20">
          点击 "运行" 执行流程。<br />
          实时代理活动将显示在这里。
        </p>
      </div>
    );
  }

  return (
    <div className="w-[420px] border-l flex flex-col h-full overflow-hidden" style={{ backgroundColor: CONSOLE_BG }}>
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-[#555] flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm text-[#eee]">⚡ 执行控制台</h3>
          <p className="text-[10px] text-[#999]">ID: {executionId?.slice(0, 8)}...</p>
        </div>
        <button
          onClick={() => setRightPanel(null)}
          className="text-[#999] hover:text-[#ddd] text-lg leading-none"
        >×</button>
      </div>

      {/* Global progress */}
      <div className="px-4 py-2 border-b border-[#555]">
        <div className="flex justify-between text-[10px] text-[#999] mb-1">
          <span>进度 {completedCount}/{totalNodes} 节点</span>
          <span className="text-yellow-400 font-mono">{totalTokens.toLocaleString()} token</span>
          <span className="text-[#999]">{elapsed}s</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-1.5">
          <div
            className="h-1.5 rounded-full transition-all duration-500"
            style={{
              width: `${progressPct}%`,
              backgroundColor: executionStatus === 'error' ? '#f7768e' : '#9ece6a',
            }}
          />
        </div>
      </div>

      {/* Node cards */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sortedNodes.map((node) => {
          const activity = nodeActivities[node.id];
          return (
            <NodeActivityCard
              key={node.id}
              nodeId={node.id}
              nodeLabel={(node.data as any)?.label || node.id}
              nodeType={(node.data as any)?.type || node.type || 'llm'}
              activity={activity}
            />
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-[#555] text-[10px] text-[#999]">
        {executionStatus === 'running' ? '▶ 运行中...' : '■ ' + executionStatus}
      </div>
    </div>
  );
}
