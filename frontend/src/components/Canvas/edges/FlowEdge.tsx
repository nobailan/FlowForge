import { useState, useCallback } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from '@xyflow/react';

export default function FlowEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}: EdgeProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition,
    targetX, targetY, targetPosition,
  });

  const label = (data?.label as string) || '';

  const handleDoubleClick = useCallback(() => {
    setDraft(label);
    setEditing(true);
  }, [label]);

  const handleSave = useCallback(() => {
    window.dispatchEvent(new CustomEvent('flowforge:update-edge-label', {
      detail: { edgeId: id, label: draft.trim() },
    }));
    setEditing(false);
  }, [id, draft]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') setEditing(false);
  }, [handleSave]);

  const showLabel = editing || label || selected;

  return (
    <>
      {/* 不可见宽路径便于点击 */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        className="cursor-pointer"
      />
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: selected ? '#3b82f6' : '#94a3b8',
          strokeWidth: selected ? 2.5 : 1.5,
          strokeDasharray: label ? '5,5' : 'none',
        }}
      />
      <EdgeLabelRenderer>
        <div
          className="absolute nodrag nopan"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: 'all',
          }}
        >
          {editing ? (
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={handleSave}
              onKeyDown={handleKeyDown}
              className="text-[10px] font-semibold px-1.5 py-0.5 rounded border border-blue-400 bg-[#252526] shadow-sm w-20 text-center outline-none"
              placeholder="label"
            />
          ) : showLabel ? (
            <div
              onDoubleClick={handleDoubleClick}
              className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[#252526] border shadow-sm cursor-pointer hover:border-blue-400 select-none"
              title="Double-click to edit label"
            >
              {label || '···'}
            </div>
          ) : null}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
