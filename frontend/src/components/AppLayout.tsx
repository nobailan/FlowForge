import { useRef, useState, useEffect } from 'react';
import { useCanvasStore } from '../store/canvasStore';
import { useAppStore, type RightPanelMode } from '../store/appStore';
import { graphsApi } from '../api/graphs';
import { executeApi } from '../api/execute';
import { evaluateApi } from '../api/evaluate';
import Sidebar from './Sidebar';
import FlowCanvas from './Canvas/FlowCanvas';
import ConfigDrawer from './ConfigPanel/ConfigDrawer';
import ExecutionConsole from './Monitor/ExecutionConsole';
import OutputTerminal from './OutputTerminal';
import ErrorBoundary from './ErrorBoundary';
import AutoPrompt from './AutoPrompt';
import EvalPanel from './Evaluator/EvalPanel';
import CompareView from './Evaluator/CompareView';
import LibraryPanel from './Library/LibraryPanel';

export default function AppLayout() {
  const toCanvasJSON = useCanvasStore((s) => s.toCanvasJSON);
  const architectureName = useAppStore((s) => s.architectureName);
  const currentArchitectureId = useAppStore((s) => s.currentArchitectureId);
  const isDirty = useAppStore((s) => s.isDirty);
  const setArchitectureId = useAppStore((s) => s.setArchitectureId);
  const setArchitectureName = useAppStore((s) => s.setArchitectureName);
  const markDirty = useAppStore((s) => s.markDirty);
  const rightPanelMode = useAppStore((s) => s.rightPanelMode);
  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const executionId = useAppStore((s) => s.executionId);
  const setExecutionId = useAppStore((s) => s.setExecutionId);
  const executionStatus = useAppStore((s) => s.executionStatus);
  const setExecutionStatus = useAppStore((s) => s.setExecutionStatus);
  const clearExecution = useAppStore((s) => s.clearExecution);
  const clearAllRuntimeData = useCanvasStore((s) => s.clearAllRuntimeData);

  const [runInput, setRunInput] = useState('');
  const [showRunDialog, setShowRunDialog] = useState(false);

  // 监听 AutoPrompt 的 "应用并运行" 事件
  const runDialogTriggered = useRef(false);
  useEffect(() => {
    const handler = () => {
      if (!runDialogTriggered.current) {
        runDialogTriggered.current = true;
        setShowRunDialog(true);
        setTimeout(() => { runDialogTriggered.current = false; }, 500);
      }
    };
    window.addEventListener('flowforge:open-run-dialog', handler);
    return () => window.removeEventListener('flowforge:open-run-dialog', handler);
  }, []);

  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      if (currentArchitectureId) {
        await graphsApi.update(currentArchitectureId, {
          name: architectureName,
          canvas_data: toCanvasJSON(),
        });
      } else {
        const arch = await graphsApi.create(architectureName || 'Untitled Flow', '', toCanvasJSON());
        setArchitectureId(arch.id);
        setArchitectureName(arch.name);
      }
      markDirty(false);
    } catch (e: any) {
      alert('保存失败：' + e.message);
    }
    setSaving(false);
  };

  const handleRun = async () => {
    if (!runInput.trim()) return;
    setShowRunDialog(false);
    setRunning(true);

    clearExecution();
    clearAllRuntimeData();

    console.log('[FlowForge] Sending execute request...');
    try {
      const result = await executeApi.run(toCanvasJSON(), runInput);
      console.log('[FlowForge] Execution started:', result.execution_id);
      setExecutionId(result.execution_id);
      setExecutionStatus('running');
      setRightPanel('monitor');

      // ExecutionConsole 自行管理 WebSocket 连接
      // 这里只做轮询兜底
      const pollUntilComplete = (execId: string) => {
        const poll = setInterval(async () => {
          try {
            const execResult = await executeApi.getResult(execId);
            if (execResult.status === 'completed' || execResult.status === 'failed') {
              clearInterval(poll);
              useAppStore.getState().setExecutionStatus(execResult.status);
              setRunning(false);
            }
          } catch (_) {}
        }, 2000);
        setTimeout(() => clearInterval(poll), 300000);
      };
      pollUntilComplete(result.execution_id);
    } catch (e: any) {
      console.error('[FlowForge] Execute failed:', e);
      alert('执行失败：' + e.message);
      setRunning(false);
    }
  };

  const handleEval = () => {
    setRightPanel(rightPanelMode === 'eval' ? null : 'eval');
  };

  const handleCompare = () => {
    setRightPanel(rightPanelMode === 'compare' ? null : 'compare');
  };

  const handleLibrary = () => {
    setRightPanel(rightPanelMode === 'library' ? null : 'library');
  };

  const title = isDirty ? `${architectureName} *` : architectureName;

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="h-10 border-b bg-[#252526] flex items-center px-3 gap-2 flex-shrink-0">
        <span className="font-bold text-sm text-[#ddd] mr-2">🧪 FlowForge</span>

        <input
          type="text"
          value={architectureName}
          onChange={(e) => {
            setArchitectureName(e.target.value);
            markDirty(true);
          }}
          className="px-2 py-0.5 text-sm border rounded w-48 focus:outline-none focus:border-blue-400"
          placeholder="架构名称..."
        />

        <div className="flex-1" />

        <button
          onClick={handleSave}
          disabled={saving}
          className="px-3 py-1 text-xs bg-[#1e3a5f] text-white rounded hover:bg-blue-600 transition-colors disabled:opacity-50"
        >
          {saving ? '保存中...' : '💾 保存'}
        </button>

        <button
          onClick={() => setShowRunDialog(true)}
          disabled={running}
          className="px-3 py-1 text-xs bg-[#1e3a2f] text-white rounded hover:bg-green-600 transition-colors disabled:opacity-50"
        >
          {running ? '⏳ 运行中...' : '▶ 运行'}
        </button>

        {executionId && (
          <button
            onClick={() => setRightPanel('monitor')}
            className={`px-3 py-1 text-xs rounded transition-colors ${
              rightPanelMode === 'monitor'
                ? 'bg-[#3a3a1e] text-white'
                : 'text-yellow-400 hover:bg-[#3a3a1e] border border-yellow-300'
            }`}
          >
            📡 控制台
          </button>
        )}

        <button
          onClick={handleEval}
          className={`px-3 py-1 text-xs rounded transition-colors ${
            rightPanelMode === 'eval'
              ? 'bg-[#2a1e3a] text-white'
              : 'text-purple-400 hover:bg-[#2a1e3a]'
          }`}
        >
          📊 评测
        </button>

        <button
          onClick={handleCompare}
          className={`px-3 py-1 text-xs rounded transition-colors ${
            rightPanelMode === 'compare'
              ? 'bg-[#3a2e1e] text-white'
              : 'text-orange-400 hover:bg-[#3a2e1e]'
          }`}
        >
          ⚖ 对比
        </button>

        <button
          onClick={handleLibrary}
          className={`px-3 py-1 text-xs rounded transition-colors ${
            rightPanelMode === 'library'
              ? 'bg-[#2d2d30] text-white'
              : 'text-[#ccc] hover:bg-[#3e3e42]'
          }`}
        >
          📦 架构库
        </button>

        <AutoPrompt />
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <FlowCanvas />

        {/* Right panel */}
        {rightPanelMode === 'config' && <ConfigDrawer />}
        {rightPanelMode === 'monitor' && <ExecutionConsole />}
        {rightPanelMode === 'eval' && <ErrorBoundary><EvalPanel /></ErrorBoundary>}
        {rightPanelMode === 'compare' && <CompareView />}
        {rightPanelMode === 'library' && <LibraryPanel />}
      </div>

      {/* 底部输出终端 */}
      <OutputTerminal />

      {/* Run dialog modal */}
      {showRunDialog && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-[#252526] rounded-lg shadow-xl shadow-black/30 p-6 w-96">
            <h3 className="font-semibold text-lg mb-3">▶ 运行 Flow</h3>
            <label className="block text-sm text-[#ccc] mb-1">
              输入 / 问题：
            </label>
            <textarea
              value={runInput}
              onChange={(e) => setRunInput(e.target.value)}
              rows={4}
              className="w-full px-3 py-2 border rounded text-sm focus:outline-none focus:border-blue-400 resize-none"
              placeholder="输入问题或任务描述..."
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowRunDialog(false)}
                className="px-4 py-1.5 text-sm text-[#ccc] border rounded hover:bg-[#2d2d30]"
              >
                取消
              </button>
              <button
                onClick={handleRun}
                disabled={!runInput.trim()}
                className="px-4 py-1.5 text-sm bg-[#1e3a2f] text-white rounded hover:bg-green-600 disabled:opacity-50"
              >
                执行
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
