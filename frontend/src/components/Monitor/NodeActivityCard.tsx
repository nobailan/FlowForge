import { useState, useEffect, useRef } from 'react';
import type { NodeActivity } from '../../hooks/useExecutionConsole';
import ActivityLogEntry from './ActivityLogEntry';

const STATUS_ICONS: Record<string, string> = {
  pending: '○',
  running: '⏳',
  completed: '✅',
  error: '❌',
};

const TYPE_COLORS: Record<string, string> = {
  llm: '#7aa2f7',
  tool: '#e0af68',
  retriever: '#9ece6a',
  subagent: '#bb9af7',
  condition: '#f7768e',
  loop: '#ff9e64',
};

interface Props {
  nodeId: string;
  nodeLabel: string;
  nodeType: string;
  activity?: NodeActivity;
}

export default function NodeActivityCard({ nodeId, nodeLabel, nodeType, activity }: Props) {
  const status = activity?.status || 'pending';
  const [expanded, setExpanded] = useState(status === 'running');
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-expand when running
  useEffect(() => {
    if (status === 'running') setExpanded(true);
  }, [status]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (expanded && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activity?.logs.length, expanded]);

  const color = TYPE_COLORS[nodeType] || '#7aa2f7';
  const elapsed = activity?.startTime && activity?.endTime
    ? ((activity.endTime - activity.startTime) * 1000).toFixed(0) + 'ms'
    : activity?.startTime
      ? ((Date.now() / 1000 - activity.startTime) * 1000).toFixed(0) + 'ms'
      : '';

  return (
    <div className="rounded-lg border border-[#555] overflow-hidden" style={{ backgroundColor: '#1f2335' }}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-800/50 transition-colors"
      >
        <span className="text-xs">{STATUS_ICONS[status]}</span>
        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
        <span className="text-xs font-medium text-[#eee] flex-1 truncate">{nodeLabel}</span>
        <span className="text-[10px] text-[#999]">{nodeType}</span>
        {activity?.tokens ? (
          <span className="text-[10px] text-yellow-400 font-mono">{activity.tokens}T</span>
        ) : null}
        {elapsed ? (
          <span className="text-[10px] text-[#ccc]">{elapsed}</span>
        ) : null}
        <span className="text-[10px] text-[#ccc]">{expanded ? '▾' : '▸'}</span>
      </button>

      {/* Log area */}
      {expanded && (
        <div className="border-t border-[#555] max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed" style={{ backgroundColor: '#1a1b26' }}>
          {!activity || activity.logs.length === 0 ? (
            <div className="px-3 py-4 text-center">
              {status === 'pending' ? (
                <span className="text-[#ccc]">等待中...</span>
              ) : status === 'running' ? (
                <span className="text-yellow-400 animate-pulse">⏳ Agent 思考中...</span>
              ) : (
                <span className="text-[#ccc]">暂无活动...</span>
              )}
            </div>
          ) : (
            activity.logs.map((log, i) => (
              <ActivityLogEntry key={i} log={log} />
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      )}
    </div>
  );
}
