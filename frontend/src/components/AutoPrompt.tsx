import { useState } from 'react';
import { useCanvasStore } from '../store/canvasStore';
import { useAppStore } from '../store/appStore';
import { apiPost } from '../api/client';

export default function AutoPrompt() {
  const [open, setOpen] = useState(false);
  const [task, setTask] = useState('');
  const [loading, setLoading] = useState(false);
  const [topoResult, setTopoResult] = useState<any>(null);
  const [prompts, setPrompts] = useState<Record<string, any>>({});
  const [error, setError] = useState('');
  const [editMode, setEditMode] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const toCanvasJSON = useCanvasStore((s) => s.toCanvasJSON);
  const updateNodeConfig = useCanvasStore((s) => s.updateNodeConfig);

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    try {
      const canvas = toCanvasJSON();
      const result = await apiPost<any>('/prompts/generate', {
        canvas_data: canvas,
        task_description: task,
      });
      setTopoResult(result.topology);
      setPrompts(result.prompts);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const handleApply = (nodeId: string) => {
    const p = prompts[nodeId];
    if (!p) return;
    const role = topoResult?.node_roles?.[nodeId] || 'worker';
    updateNodeConfig(nodeId, {
      system_prompt: p.system_prompt || '',
      user_prompt_template: p.user_prompt_template || '',
      max_steps: role === 'dispatcher' || role === 'aggregator' ? 5 : 8,
      timeout_seconds: role === 'aggregator' ? 60 : 90,
      opencode_agent: 'build',
      model_provider: 'deepseek',
      model_id: 'deepseek-v4-pro',
    });
    useAppStore.getState().markDirty(true);
  };

  const applyAllPrompts = () => {
    const roles = topoResult?.node_roles || {};
    for (const [nid, p] of Object.entries(prompts)) {
      const role = roles[nid] || 'worker';
      const maxSteps = role === 'dispatcher' || role === 'aggregator' ? 5 : 8;
      const timeout = role === 'aggregator' ? 60 : 90;
      updateNodeConfig(nid, {
        system_prompt: (p as any).system_prompt || '',
        user_prompt_template: (p as any).user_prompt_template || '',
        max_steps: maxSteps,
        timeout_seconds: timeout,
        opencode_agent: 'build',
        model_provider: 'deepseek',
        model_id: 'deepseek-v4-pro',
      });
    }
    useAppStore.getState().markDirty(true);
  };

  const handleApplyAll = () => {
    applyAllPrompts();
    setOpen(false);
  };

  const handleApplyAndRun = () => {
    applyAllPrompts();
    setOpen(false);
    // 关闭面板后触发 Run 对话框
    useAppStore.getState().setRightPanel(null);
    setTimeout(() => {
      const event = new CustomEvent('flowforge:open-run-dialog');
      window.dispatchEvent(event);
    }, 200);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="px-3 py-1 text-xs bg-purple-500 text-white rounded hover:bg-purple-600 transition-colors"
        title="根据拓扑结构自动生成 Prompt"
      >
        ✨ 自动 Prompt
      </button>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-[#252526] rounded-lg shadow-xl w-[700px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#3c3c3c]">
          <h3 className="font-semibold text-sm text-[#eee]">✨ 自动 Prompt 生成器</h3>
          <button onClick={() => setOpen(false)} className="text-[#999] hover:text-[#eee]">×</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Input */}
          <div>
            <label className="block text-xs text-[#999] mb-1">
              这个流程要完成什么任务？
            </label>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-[#3c3c3c] rounded text-sm bg-[#2d2d30] text-[#eee] focus:outline-none focus:border-purple-400"
              placeholder="例如：分析项目架构并生成报告"
            />
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50 text-sm"
          >
            {loading ? '⏳ 分析中...' : '🔍 分析拓扑并生成 Prompt'}
          </button>

          {error && (
            <div className="p-2 bg-red-900/30 border border-red-500 rounded text-xs text-red-400">{error}</div>
          )}

          {/* Topology result */}
          {topoResult && (
            <div className="border border-[#3c3c3c] rounded p-3">
              <div className="text-xs font-semibold text-[#eee] mb-2">拓扑分析</div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-[#999]">模式：</span>{' '}
                  <span className="text-purple-400 font-semibold">{topoResult.pattern}</span>
                </div>
                <div>
                  <span className="text-[#999]">有效：</span>{' '}
                  <span className={topoResult.is_valid ? 'text-green-400' : 'text-red-400'}>
                    {topoResult.is_valid ? '✓' : '✗'}
                  </span>
                </div>
              </div>
              {topoResult.warnings?.length > 0 && (
                <div className="mt-2 text-[10px] text-yellow-400">
                  ⚠ {topoResult.warnings.join('; ')}
                </div>
              )}
            </div>
          )}

          {/* Generated prompts */}
          {Object.keys(prompts).length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold text-[#eee]">生成的 Prompt</div>
                <div className="flex gap-1">
                  <button
                    onClick={handleApplyAll}
                    className="px-3 py-1 text-[10px] bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    全部应用
                  </button>
                  <button
                    onClick={handleApplyAndRun}
                    className="px-3 py-1 text-[10px] bg-green-500 text-white rounded hover:bg-green-600"
                  >
                    应用并运行 ▶
                  </button>
                </div>
              </div>

              {Object.entries(prompts).map(([nid, p]: [string, any]) => {
                const role = topoResult?.node_roles?.[nid] || 'unknown';
                return (
                  <div key={nid} className="border border-[#3c3c3c] rounded p-2">
                    <div className="flex items-center justify-between mb-1">
                      <div>
                        <span className="text-xs font-semibold text-[#eee]">{nid}</span>
                        <span className="text-[10px] text-[#999] ml-2">({role})</span>
                      </div>
                      <button
                        onClick={() => handleApply(nid)}
                        className="px-2 py-0.5 text-[10px] bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        应用
                      </button>
                    </div>

                    {editMode === nid ? (
                      <div className="space-y-1">
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          rows={3}
                          className="w-full px-2 py-1 text-[11px] border border-[#3c3c3c] rounded bg-[#2d2d30] text-[#eee]"
                        />
                        <button
                          onClick={() => {
                            prompts[nid].system_prompt = editText;
                            setEditMode(null);
                          }}
                          className="px-2 py-0.5 text-[10px] bg-green-500 text-white rounded"
                        >
                          保存修改
                        </button>
                      </div>
                    ) : (
                      <div
                        className="text-[11px] text-[#ccc] cursor-pointer hover:text-[#eee]"
                        onDoubleClick={() => { setEditMode(nid); setEditText(p.system_prompt || ''); }}
                        title="双击编辑"
                      >
                        {p.system_prompt?.slice(0, 120) || '(空)'}...
                      </div>
                    )}

                    {p.user_prompt_template && (
                      <div className="mt-1 text-[10px] text-[#999]">
                        模板: {p.user_prompt_template.slice(0, 80)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
