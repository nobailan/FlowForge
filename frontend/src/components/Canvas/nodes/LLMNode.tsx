import type { NodeProps } from '@xyflow/react';
import type { CanvasNodeData } from '../../../types/canvas';
import BaseNode from './BaseNode';

const COLOR = '#7aa2f7';  // muted blue

export default function LLMNode({ id, data, selected }: NodeProps) {
  const nodeData = data as CanvasNodeData;
  return (
    <BaseNode id={id} data={nodeData} selected={selected} color={COLOR} icon="🤖">
      <div className="text-gray-400">
        Model: {nodeData.config?.model_id || 'deepseek-v4-pro'}
      </div>
      <div className="text-gray-500 truncate max-w-[200px]">
        {nodeData.config?.system_prompt?.slice(0, 60) || 'You are a helpful assistant.'}
      </div>
      {nodeData._output && (
        <div className="mt-1 p-1 rounded text-[10px] max-h-12 overflow-hidden text-gray-400" style={{backgroundColor: COLOR + '10'}}>
          {nodeData._output.slice(0, 100)}...
        </div>
      )}
    </BaseNode>
  );
}
