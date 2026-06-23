import { useState } from 'react';
import type { NodeEvent } from '../../types/execution';

interface Props {
  events: NodeEvent[];
}

export default function NodeStatusList({ events }: Props) {
  const [expandedNode, setExpandedNode] = useState<string | null>(null);

  // Group events by node_id, keep latest status
  const nodeMap = new Map<string, NodeEvent>();
  events.forEach((e) => nodeMap.set(e.node_id, e));
  const nodeStatuses = Array.from(nodeMap.values());

  if (nodeStatuses.length === 0) {
    return (
      <div className="p-3 text-center text-xs text-[#999]">
        Waiting for node events...
      </div>
    );
  }

  return (
    <div className="divide-y">
      {nodeStatuses.map((event) => (
        <div key={event.node_id}>
          <button
            onClick={() =>
              setExpandedNode(expandedNode === event.node_id ? null : event.node_id)
            }
            className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-[#2d2d30] transition-colors"
          >
            {/* Status indicator */}
            <span
              className={`w-2 h-2 rounded-full flex-shrink-0 ${
                event.status === 'running'
                  ? 'bg-yellow-400 animate-pulse'
                  : event.status === 'completed'
                  ? 'bg-green-400'
                  : event.status === 'error'
                  ? 'bg-red-400'
                  : 'bg-gray-300'
              }`}
            />

            {/* Node info */}
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium truncate">
                {event.node_id}
              </div>
              <div className="text-[10px] text-[#999]">{event.node_type}</div>
            </div>

            {/* Metrics */}
            <div className="text-right flex-shrink-0">
              <div className="text-xs text-[#ccc]">
                {event.latency_ms}ms
              </div>
              <div className="text-[10px] text-[#999]">
                {event.token_count > 0 ? `${event.token_count} T` : ''}
              </div>
            </div>
          </button>

          {/* Expanded details */}
          {expandedNode === event.node_id && (
            <div className="px-4 py-2 bg-[#2d2d30] text-xs space-y-1">
              {event.input_summary && (
                <div>
                  <span className="text-[#999]">Input:</span>{' '}
                  <span className="text-[#ccc] break-all">{event.input_summary}</span>
                </div>
              )}
              {event.output_summary && (
                <div>
                  <span className="text-[#999]">Output:</span>{' '}
                  <span className="text-[#ccc] break-all">{event.output_summary}</span>
                </div>
              )}
              <div className="text-[#999]">
                Timestamp: {new Date(event.timestamp * 1000).toLocaleTimeString()}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
