import { useEffect, useState, useRef, type DragEvent } from 'react';
import { useCanvasStore } from '../store/canvasStore';
import { useAppStore } from '../store/appStore';
import { templatesApi } from '../api/templates';
import type { NodeTypeInfo } from '../types/canvas';
import type { TemplateInfo } from '../types/evaluation';

// 内置兜底数据 — 后端不可用时仍然显示节点面板
const BUILTIN_NODE_TYPES: NodeTypeInfo[] = [
  {
    name: 'llm', display_name: 'LLM', description: '调用大语言模型',
    category: 'llm', icon: '🤖',
    config_schema: {}, default_config: {},
    input_ports: ['input'], output_ports: ['output'],
  },
  {
    name: 'tool', display_name: 'Tool', description: '调用外部工具',
    category: 'tool', icon: '🔧',
    config_schema: {}, default_config: {},
    input_ports: ['input'], output_ports: ['output'],
  },
  {
    name: 'retriever', display_name: 'Retriever', description: '检索知识库',
    category: 'retrieval', icon: '📚',
    config_schema: {}, default_config: {},
    input_ports: ['input'], output_ports: ['output'],
  },
  {
    name: 'subagent', display_name: 'Subagent', description: '启动子 Agent',
    category: 'control', icon: '👥',
    config_schema: {}, default_config: {},
    input_ports: ['input'], output_ports: ['output'],
  },
  {
    name: 'condition', display_name: 'Condition', description: '条件分支路由',
    category: 'control', icon: '🔀',
    config_schema: {}, default_config: {},
    input_ports: ['input'], output_ports: ['output'],
  },
  {
    name: 'loop', display_name: 'Loop', description: '循环控制',
    category: 'control', icon: '🔄',
    config_schema: {}, default_config: {},
    input_ports: ['input'], output_ports: ['output'],
  },
];

const BUILTIN_TEMPLATES: TemplateInfo[] = [
  { name: 'supervisor_worker', display_name: 'Supervisor-Worker', description: '主管-执行者模式', node_count: 5, edge_count: 6 },
  { name: 'sequential_chain', display_name: 'Sequential Chain', description: '顺序链模式', node_count: 4, edge_count: 3 },
  { name: 'parallel', display_name: 'Parallel', description: '并行模式', node_count: 5, edge_count: 6 },
  { name: 'conditional_branch', display_name: 'Conditional Branch', description: '条件分支模式', node_count: 5, edge_count: 4 },
  { name: 'reflection_loop', display_name: 'Reflection Loop', description: '反思循环模式', node_count: 4, edge_count: 3 },
];

const CATEGORY_NAMES: Record<string, string> = {
  llm: '🤖 LLM',
  tool: '🔧 Tools',
  retrieval: '📚 Retrieval',
  control: '🔀 Control',
};

const NODE_ICONS: Record<string, string> = {
  llm: '🤖', tool: '🔧', retriever: '📚',
  subagent: '👥', condition: '🔀', loop: '🔄',
};

export default function Sidebar() {
  const [nodeTypes, setNodeTypes] = useState<NodeTypeInfo[]>(BUILTIN_NODE_TYPES);
  const [templates, setTemplates] = useState<TemplateInfo[]>(BUILTIN_TEMPLATES);
  const [showTemplates, setShowTemplates] = useState(false);
  const loaded = useRef(false);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;

    // 尝试从后端获取最新节点类型，失败则用内置兜底
    templatesApi.listNodeTypes()
      .then(setNodeTypes)
      .catch(() => {}); // 静默回退到 BUILTIN_NODE_TYPES

    templatesApi.list()
      .then(setTemplates)
      .catch(() => {}); // 静默回退到 BUILTIN_TEMPLATES
  }, []);

  const onDragStart = (event: DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow-type', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  const categories = groupBy(nodeTypes, (t) => t.category);

  const handleLoadTemplate = async (name: string) => {
    try {
      const template = await templatesApi.get(name);
      useCanvasStore.getState().fromCanvasJSON(template.canvas_data);
      useAppStore.getState().setArchitectureName(template.display_name);
      useAppStore.getState().markDirty(false);
      setShowTemplates(false);
    } catch (e) {
      console.error('Failed to load template:', e);
    }
  };

  return (
    <div className="w-56 border-r bg-[#2d2d30] flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-3 border-b bg-[#252526]">
        <h2 className="font-bold text-sm text-[#ddd]">🧪 FlowForge</h2>
        <p className="text-[10px] text-[#999]">Agent Architecture Workbench</p>
      </div>

      {/* Node Palette */}
      <div className="p-2">
        <h3 className="text-[11px] font-semibold text-[#999] uppercase px-1 mb-1">
          Node Palette
        </h3>
        {Object.entries(categories).map(([category, types]) => (
          <div key={category} className="mb-2">
            <div className="text-[10px] text-[#999] px-1 mb-1">
              {CATEGORY_NAMES[category] || category}
            </div>
            {types.map((nt) => (
              <div
                key={nt.name}
                draggable
                onDragStart={(e) => onDragStart(e, nt.name)}
                className="flex items-center gap-2 px-2 py-1.5 mb-0.5 rounded cursor-grab hover:bg-[#1e3a5f] hover:text-blue-400 text-xs border border-transparent hover:border-blue-200 transition-colors"
                title={nt.description}
              >
                <span className="text-sm">{NODE_ICONS[nt.name] || '📦'}</span>
                <span>{nt.display_name}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Divider */}
      <div className="border-t border-[#3c3c3c] mx-2" />

      {/* Templates */}
      <div className="p-2">
        <button
          onClick={() => setShowTemplates(!showTemplates)}
          className="w-full text-left text-[11px] font-semibold text-[#999] uppercase px-1 py-1 hover:text-[#ddd]"
        >
          📋 Templates {showTemplates ? '▾' : '▸'}
        </button>
        {showTemplates && (
          <div className="mt-1 space-y-0.5">
            {templates.map((t) => (
              <button
                key={t.name}
                onClick={() => handleLoadTemplate(t.name)}
                className="w-full text-left px-2 py-1.5 rounded text-xs hover:bg-[#1e3a2f] hover:text-green-400 transition-colors"
                title={t.description}
              >
                <div className="font-medium">{t.display_name}</div>
                <div className="text-[10px] text-[#999]">
                  {t.node_count} nodes · {t.edge_count} edges
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function groupBy<T>(items: T[], fn: (item: T) => string): Record<string, T[]> {
  const result: Record<string, T[]> = {};
  for (const item of items) {
    const key = fn(item);
    (result[key] ||= []).push(item);
  }
  return result;
}
