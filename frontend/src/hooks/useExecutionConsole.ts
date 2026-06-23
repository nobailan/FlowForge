import { useState, useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '../store/appStore';

export interface StreamingEvent {
  execution_id: string;
  node_id: string;
  event_type: 'thinking' | 'tool_start' | 'tool_end' | 'completed' | 'error';
  text?: string;
  tool_name?: string;
  tool_input?: string;
  tool_output?: string;
  tokens_input?: number;
  tokens_output?: number;
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

    switch (ev.event_type) {
      case 'thinking':
        if (node.status === 'pending') {
          node.status = 'running';
          node.startTime = ev.timestamp;
          // 通知画布：节点开始运行
          window.dispatchEvent(new CustomEvent('flowforge:node-activity', {
            detail: { nodeId: ev.node_id, status: 'running', text: ev.text }
          }));
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
        node.status = 'completed';
        node.endTime = ev.timestamp;
        node.tokens = (ev.tokens_input || 0) + (ev.tokens_output || 0);
        tokenRef.current += node.tokens;
        break;

      case 'error':
        node.status = 'error';
        node.endTime = ev.timestamp;
        break;
    }

    // Trigger re-render (shallow copy to break reference equality)
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
