import type { NodeProps } from '@xyflow/react';
import type { CanvasNodeData } from '../../../types/canvas';
import BaseNode from './BaseNode';

const COLOR = '#9ece6a';  // muted green

export default function RetrieverNode({ id, data, selected }: NodeProps) {
  const nodeData = data as CanvasNodeData;
  return (
    <BaseNode id={id} data={nodeData} selected={selected} color={COLOR} icon="📚">
      <div className="text-gray-400">Top-K: {nodeData.config?.top_k || 5}</div>
      <div className="text-gray-500 text-[10px]">KB: {nodeData.config?.knowledge_base || 'default'}</div>
    </BaseNode>
  );
}
