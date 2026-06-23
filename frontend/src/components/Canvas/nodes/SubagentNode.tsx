import type { NodeProps } from '@xyflow/react';
import type { CanvasNodeData } from '../../../types/canvas';
import BaseNode from './BaseNode';

const COLOR = '#bb9af7';  // muted purple

export default function SubagentNode({ id, data, selected }: NodeProps) {
  const nodeData = data as CanvasNodeData;
  return (
    <BaseNode id={id} data={nodeData} selected={selected} color={COLOR} icon="👥">
      <div className="text-gray-400">Max Iter: {nodeData.config?.max_iterations || 3}</div>
      <div className="text-gray-500 truncate max-w-[200px] text-[10px]">
        {nodeData.config?.agent_task?.slice(0, 60) || 'Complete assigned task'}
      </div>
    </BaseNode>
  );
}
