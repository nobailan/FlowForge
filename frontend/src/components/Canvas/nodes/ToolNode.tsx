import type { NodeProps } from '@xyflow/react';
import type { CanvasNodeData } from '../../../types/canvas';
import BaseNode from './BaseNode';

const COLOR = '#e0af68';  // muted amber

export default function ToolNode({ id, data, selected }: NodeProps) {
  const nodeData = data as CanvasNodeData;
  return (
    <BaseNode id={id} data={nodeData} selected={selected} color={COLOR} icon="🔧">
      <div className="text-gray-300 font-medium">
        {nodeData.config?.tool_name || 'Tool'}
      </div>
      <div className="text-gray-500 text-[10px]">
        {nodeData.config?.tool_task?.slice(0, 60) || 'Execute tool call'}
      </div>
    </BaseNode>
  );
}
