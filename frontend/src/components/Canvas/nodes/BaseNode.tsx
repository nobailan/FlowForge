import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { CanvasNodeData } from '../../../types/canvas';

interface BaseNodeProps {
  id: string;
  data: CanvasNodeData;
  selected: boolean;
  children: React.ReactNode;
  color: string;
  icon: string;
}

const statusGlow: Record<string, string> = {
  running: 'shadow-[0_0_8px_rgba(234,179,8,0.4)]',
  completed: 'shadow-[0_0_4px_rgba(74,222,128,0.3)]',
  error: 'shadow-[0_0_8px_rgba(248,113,113,0.5)]',
};

export default function BaseNode({ id, data, selected, children, color, icon }: BaseNodeProps) {
  const status = data._status;

  return (
    <div
      className={`
        rounded-lg border min-w-[180px] transition-all duration-300
        ${selected ? 'border-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.3)]' : 'border-[#404040]'}
        ${status ? statusGlow[status] || '' : 'bg-[#2d2d30]'}
      `}
      style={{ backgroundColor: selected ? '#2a2d3a' : '#2d2d30' }}
    >
      {/* Header — color accent bar on left */}
      <div
        className="flex items-center gap-2 px-3 py-1.5 rounded-t-md text-xs font-semibold border-b border-[#404040]"
        style={{
          backgroundColor: color + '18',
          borderLeft: `3px solid ${color}`,
        }}
      >
        <span>{icon}</span>
        <span className="flex-1" style={{ color: color }}>{data.label || data.type}</span>
        {data._status === 'running' && (
          <span className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: color }} />
        )}
        {data._status === 'completed' && (
          <span className="text-[10px] text-gray-500">
            {data._tokens || 0}T · {data._latency_ms || 0}ms
          </span>
        )}
        {data._status === 'error' && (
          <span className="text-[10px] text-red-400">Error</span>
        )}
      </div>

      {/* Body */}
      <div className="px-3 py-2 text-xs space-y-1">{children}</div>

      {/* Handles */}
      <Handle type="target" position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-[#555] !border-[#333]" />
      <Handle type="source" position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-[#555] !border-[#333]" />
    </div>
  );
}
