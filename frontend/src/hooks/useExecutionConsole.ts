import { useState, useCallback, useRef } from 'react';

export interface StreamingEvent {
  execution_id: string;
  node_id: string;
  // v0.6: 新事件格式使用 "event" 字段，旧格式使用 "event_type"
  event?: string;
  event_type?: string;
  text?: string;
  tool_name?: string;
  tool_input?: string;
  tool_output?: string;
  summary?: string;
  tokens?: number;
  tokens_input?: number;
  tokens_output?: number;
  latency_ms?: number;
  output_preview?: string;
  node_type?: string;
  node_label?: string;
  tool_call_count?: number;
  timestamp: number;
}

export interface ActivityLogEntry {
  timestamp: number;
  nodeId: string;
  eventType: string;
  text: string;
  toolName: string;
  toolInput: string;
}

export interface NodeActivity {
  nodeId: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  logs: ActivityLogEntry[];
  tokens: number;
  startTime: number | null;
  endTime: number | null;
}

export function useExecutionConsole() {
  const [nodeActivities, setNodeActivities] = useState<Record<string, NodeActivity>>({});
  const [totalTokens, setTotalTokens] = useState(0);
  const nodesRef = useRef<Record<string, NodeActivity>>({});
  const tokenRef = useRef(0);

  const getOrCreate = useCallback((nodeId: string): NodeActivity => {
    if (!nodesRef.current[nodeId]) {
      nodesRef.current[nodeId] = {
        nodeId,
        status: 'pending',
        logs: [],
        tokens: 0,
        startTime: null,
        endTime: null,
      };
    }
    return nodesRef.current[nodeId];
  }, []);

  const addEvent = useCallback((ev: StreamingEvent) => {
    const node = getOrCreate(ev.node_id);
    // v0.6: 标准化事件字段
    const etype = ev.event || ev.event_type || '';

    switch (etype) {
      // --- v0.6 新事件 ---
      case 'node:start':
        if (node.status === 'pending') {
          node.status = 'running';
          node.startTime = ev.timestamp;
          node.logs.push({
            timestamp: ev.timestamp,
            nodeId: ev.node_id,
            eventType: 'start',
            text: `Node started`,
            toolName: '',
            toolInput: '',
          });
        }
        break;

      case 'node:thinking':
        if (!ev.text || !ev.text.trim()) break;  // 跳过空文本
        if (node.status === 'pending') {
          node.status = 'running';
          node.startTime = ev.timestamp;
        }
        node.logs.push({
          timestamp: ev.timestamp,
          nodeId: ev.node_id,
          eventType: 'thinking',
          text: ev.text,
          toolName: '',
          toolInput: '',
        });
        break;

      case 'node:tool':
        node.logs.push({
          timestamp: ev.timestamp,
          nodeId: ev.node_id,
          eventType: 'tool_start',
          text: '',
          toolName: ev.tool_name || '',
          toolInput: ev.tool_input || '',
        });
        break;

      case 'node:tool_result':
        // 跳过无意义的 idle 标记
        if (!ev.summary || ev.summary === 'idle') break;
        node.logs.push({
          timestamp: ev.timestamp,
          nodeId: ev.node_id,
          eventType: 'tool_end',
          text: ev.summary || ev.tool_output || '',
          toolName: ev.tool_name || '',
          toolInput: '',
        });
        break;

      case 'node:end':
        if (node.status !== 'completed' && node.status !== 'error') {
          const isError = ev.event_type === 'error';
          node.status = isError ? 'error' : 'completed';
          node.endTime = ev.timestamp;
          // v0.6: 取精确 token 值
          const tok = ev.tokens || (ev.tokens_input || 0) + (ev.tokens_output || 0);
          if (node.tokens === 0) {
            node.tokens = tok;
            tokenRef.current += tok;
          }
          node.logs.push({
            timestamp: ev.timestamp,
            nodeId: ev.node_id,
            eventType: isError ? 'error' : 'completed',
            text: ev.output_preview || (isError ? 'Error' : 'Completed'),
            toolName: '',
            toolInput: '',
          });
        }
        break;

      // --- 兼容旧事件格式 ---
      case 'thinking':
        if (node.status === 'pending') {
          node.status = 'running';
          node.startTime = ev.timestamp;
        }
        node.logs.push({
          timestamp: ev.timestamp,
          nodeId: ev.node_id,
          eventType: 'thinking',
          text: ev.text || '',
          toolName: '',
          toolInput: '',
        });
        break;

      case 'tool_start':
        node.logs.push({
          timestamp: ev.timestamp,
          nodeId: ev.node_id,
          eventType: 'tool_start',
          text: '',
          toolName: ev.tool_name || '',
          toolInput: ev.tool_input || '',
        });
        break;

      case 'tool_end':
        node.logs.push({
          timestamp: ev.timestamp,
          nodeId: ev.node_id,
          eventType: 'tool_end',
          text: ev.tool_output || '',
          toolName: ev.tool_name || '',
          toolInput: '',
        });
        break;

      case 'completed':
        if (node.status !== 'completed') {
          node.status = 'completed';
          node.endTime = ev.timestamp;
          node.tokens = (ev.tokens_input || 0) + (ev.tokens_output || 0);
          tokenRef.current += node.tokens;
        }
        break;

      case 'error':
        if (node.status !== 'error') {
          node.status = 'error';
          node.endTime = ev.timestamp;
        }
        break;
    }

    // 触发渲染
    setNodeActivities({ ...nodesRef.current });
    setTotalTokens(tokenRef.current);
  }, [getOrCreate]);

  const reset = useCallback(() => {
    nodesRef.current = {};
    tokenRef.current = 0;
    setNodeActivities({});
    setTotalTokens(0);
  }, []);

  return {
    nodeActivities,
    totalTokens,
    addEvent,
    reset,
  };
}
