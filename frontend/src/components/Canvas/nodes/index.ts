import LLMNode from './LLMNode';
import ToolNode from './ToolNode';
import RetrieverNode from './RetrieverNode';
import SubagentNode from './SubagentNode';
import ConditionNode from './ConditionNode';
import LoopNode from './LoopNode';

export const nodeTypes = {
  llm: LLMNode,
  tool: ToolNode,
  retriever: RetrieverNode,
  subagent: SubagentNode,
  condition: ConditionNode,
  loop: LoopNode,
};
