import { useState } from 'react';
import { useAppStore } from '../../store/appStore';
import { useCanvasStore } from '../../store/canvasStore';
import { evaluateApi } from '../../api/evaluate';
import MetricsCards from './MetricsCards';
import PerQuestionTable from './PerQuestionTable';
import type { EvaluationResult } from '../../types/evaluation';

export default function EvalPanel() {
  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const currentArchitectureId = useAppStore((s) => s.currentArchitectureId);
  const canvasData = useCanvasStore((s) => {
    try {
      return s.toCanvasJSON();
    } catch {
      return { nodes: [], edges: [] };
    }
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const handleRunEval = async () => {
    setLoading(true);
    setError('');
    setMessage('正在保存架构...');

    try {
      // Save current canvas first if not saved
      let archId = currentArchitectureId;
      if (!archId) {
        const { graphsApi } = await import('../../api/graphs');
        const arch = await graphsApi.create(
          useAppStore.getState().architectureName || 'Untitled',
          '',
          canvasData
        );
        archId = arch.id;
        useAppStore.getState().setArchitectureId(archId);
        setMessage(`已保存为 "${arch.name}"。正在加载测试集...`);
      }

      // Get test sets
      const testSets = await evaluateApi.listTestSets();
      if (testSets.length === 0) {
        setError('没有可用的测试集，请先创建。');
        setLoading(false);
        return;
      }

      setMessage(`正在使用 "${testSets[0].name}" 运行评测...`);
      const evalResult = await evaluateApi.run(archId, testSets[0].id);

      // Poll for completion
      const pollInterval = setInterval(async () => {
        const updated = await evaluateApi.getResult(evalResult.id);
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(pollInterval);
          setResult(updated);
          setLoading(false);
          setMessage('');
        } else {
          setMessage(`评测中... ${updated.status}`);
        }
      }, 2000);

      setTimeout(() => {
        clearInterval(pollInterval);
        if (loading) {
          setLoading(false);
          setError('评测超时。');
        }
      }, 300000); // 5 min timeout
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  return (
    <div className="w-[400px] border-l bg-[#252526] flex flex-col h-full overflow-hidden">
      <div className="p-3 border-b flex items-center justify-between">
        <h3 className="font-semibold text-sm">📊 评测</h3>
        <button
          onClick={() => setRightPanel(null)}
          className="text-[#999] hover:text-[#ccc]"
        >
          ×
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {!result && !loading && (
          <div className="text-center py-10">
            <p className="text-sm text-[#999] mb-3">
              运行评测以衡量此架构的性能。
            </p>
            <button
              onClick={handleRunEval}
              className="px-4 py-2 bg-[#1e3a2f] text-white text-sm rounded hover:bg-green-600 transition-colors"
            >
              ▶ 运行评测
            </button>
            {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
          </div>
        )}

        {loading && (
          <div className="text-center py-10">
            <div className="animate-spin text-3xl mb-3">⏳</div>
            <p className="text-sm text-[#999]">{message || '评测中...'}</p>
          </div>
        )}

        {result && (
          <>
            <MetricsCards summary={result.summary} />
            <PerQuestionTable details={result.detail_results} />
          </>
        )}
      </div>
    </div>
  );
}
