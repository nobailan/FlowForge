import type { NodeProps } from '@xyflow/react';
import type { CanvasNodeData } from '../../../types/canvas';
import BaseNode from './BaseNode';

export default function LoopNode({ id, data, selected }: NodeProps) {
  const nodeData = data as CanvasNodeData;
  return (
    <BaseNode id={id} data={nodeData} selected={selected} color="#ec4899" icon="🔄">
      <div className="text-[#ccc]">
        Max: {nodeData.config?.max_iterations || 5} iterations
      </div>
      <div className="text-[#999] text-[10px]">
        {nodeData.config?.condition_field
          ? `Until: ${nodeData.config.condition_field} ${nodeData.config.condition_operator} "${nodeData.config.condition_value}"`
          : 'Simple counter loop'}
      </div>
      {nodeData._output && (
        <div className={`
          mt-1 px-1 rounded text-[10px] font-bold
          ${nodeData._output === 'continue' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-400'}
        `}>
          → {nodeData._output}
        </div>
      )}
    </BaseNode>
  );
}
