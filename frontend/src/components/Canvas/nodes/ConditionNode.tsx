import type { NodeProps } from '@xyflow/react';
import type { CanvasNodeData } from '../../../types/canvas';
import BaseNode from './BaseNode';

export default function ConditionNode({ id, data, selected }: NodeProps) {
  const nodeData = data as CanvasNodeData;
  return (
    <BaseNode id={id} data={nodeData} selected={selected} color="#ef4444" icon="🔀">
      <div className="text-[#ccc] font-mono text-[11px]">
        {nodeData.config?.field || '?'} {nodeData.config?.operator || '?'}
      </div>
      <div className="text-[#999] text-[10px]">
        {nodeData.config?.value ? `"${nodeData.config.value}"` : '→ true / false'}
      </div>
      {nodeData._output && (
        <div className={`
          mt-1 px-1 rounded text-[10px] font-bold
          ${nodeData._output === 'true' ? 'bg-green-100 text-green-400' : 'bg-red-100 text-red-400'}
        `}>
          → {nodeData._output}
        </div>
      )}
    </BaseNode>
  );
}
