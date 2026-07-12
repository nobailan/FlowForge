import { useState, useCallback, useEffect } from 'react';
import { useAppStore } from '../../store/appStore';
import { useCanvasStore } from '../../store/canvasStore';
import { evaluateApi } from '../../api/evaluate';
import { apiPost } from '../../api/client';
import MetricsCards from './MetricsCards';
import PerQuestionTable from './PerQuestionTable';
import type { EvaluationResult } from '../../types/evaluation';

const EMPTY_CANVAS = { nodes: [] as any[], edges: [] as any[] };

interface TestSetInfo {
  id: string;
  name: string;
  description: string;
  test_cases: any[];
}

interface TopoRecommendation {
  pattern: string;
  recommended_test_sets: string[];
  reason: string;
}

export default function EvalPanel() {
  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const currentArchitectureId = useAppStore((s) => s.currentArchitectureId);
  const kernel = useAppStore((s) => s.kernel);
  // v0.7: 结果持久化在 appStore，关掉不丢失
  const evalDetailResults = useAppStore((s) => s.evalDetailResults);
  const setEvalDetailResults = useAppStore((s) => s.setEvalDetailResults);
  const evalResults = useAppStore((s) => s.evalResults);
  const setEvalResults = useAppStore((s) => s.setEvalResults);

  const getCanvasData = useCallback(() => {
    try {
      return useCanvasStore.getState().toCanvasJSON();
    } catch {
      return EMPTY_CANVAS;
    }
  }, []);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // v0.7: 测试集列表 + 拓扑推荐
  const [testSets, setTestSets] = useState<TestSetInfo[]>([]);
  const [selectedSetId, setSelectedSetId] = useState<string>('');
  const [recommendation, setRecommendation] = useState<TopoRecommendation | null>(null);
  const [showSets, setShowSets] = useState(false);

  // 加载测试集列表 + 拓扑推荐
  useEffect(() => {
    evaluateApi.listTestSets().then((sets) => {
      setTestSets(sets as TestSetInfo[]);
      if (sets.length > 0) setSelectedSetId(sets[0].id);
    }).catch(() => {});

    const canvas = getCanvasData();
    if (canvas.nodes.length > 0) {
      apiPost<TopoRecommendation>('/eval/recommend', { canvas_data: canvas })
        .then(setRecommendation)
        .catch(() => {});
    }
  }, []);

  // 根据推荐匹配测试集
  const recommendedSets = testSets.filter((ts) =>
    recommendation?.recommended_test_sets?.some((r) =>
      ts.name.toLowerCase().includes(r.toLowerCase())
    )
  );

  const handleRunEval = async () => {
    setLoading(true);
    setError('');
    setMessage('正在保存架构...');

    try {
      let archId = currentArchitectureId;
      if (!archId) {
        const { graphsApi } = await import('../../api/graphs');
        const arch = await graphsApi.create(
          useAppStore.getState().architectureName || 'Untitled',
          '',
          getCanvasData()
        );
        archId = arch.id;
        useAppStore.getState().setArchitectureId(archId);
        setMessage(`已保存为 "${arch.name}"。正在运行评测...`);
      }

      if (!selectedSetId) {
        setError('请先选择一个测试集。');
        setLoading(false);
        return;
      }

      const selectedSet = testSets.find((t) => t.id === selectedSetId);
      setMessage(`正在使用 "${selectedSet?.name || selectedSetId}" 运行评测...`);
      const evalResult = await evaluateApi.run(archId, selectedSetId, kernel);

      const pollInterval = setInterval(async () => {
        const updated = await evaluateApi.getResult(evalResult.id);
        if (updated.status === 'completed' || updated.status === 'failed') {
          clearInterval(pollInterval);
          setEvalDetailResults(updated);
          setEvalResults(updated.summary);
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
      }, 600000);
    } catch (e: any) {
      console.error('[EvalPanel]', e);
      setError(e?.message || String(e) || '未知错误');
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
        {!evalDetailResults && !loading && (
          <>
            {/* v0.7: 拓扑推荐 */}
            {recommendation && (
              <div className="border border-purple-500/30 rounded p-2 bg-purple-900/10">
                <div className="text-[11px] text-purple-300 font-semibold mb-1">
                  🔍 拓扑分析: {recommendation.pattern}
                </div>
                <div className="text-[10px] text-[#999]">{recommendation.reason}</div>
                {recommendedSets.length > 0 && (
                  <div className="mt-1 text-[10px] text-green-400">
                    ✅ 推荐: {recommendedSets.map((s) => s.name).join(' / ')}
                  </div>
                )}
              </div>
            )}

            {/* 测试集选择 */}
            <div>
              <button
                onClick={() => setShowSets(!showSets)}
                className="w-full text-left text-xs text-[#999] hover:text-[#ddd]"
              >
                📋 测试集 ({testSets.length}) {showSets ? '▾' : '▸'}
              </button>
              {showSets && (
                <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
                  {testSets.map((ts) => {
                    const isRecommended = recommendedSets.some((r) => r.id === ts.id);
                    return (
                      <button
                        key={ts.id}
                        onClick={() => setSelectedSetId(ts.id)}
                        className={`w-full text-left px-2 py-1 rounded text-[11px] transition-colors ${
                          selectedSetId === ts.id
                            ? 'bg-purple-500/20 text-purple-300 border border-purple-500/50'
                            : 'hover:bg-[#2d2d30] text-[#ccc]'
                        }`}
                      >
                        <div className="flex items-center gap-1">
                          {isRecommended && <span className="text-[10px]">⭐</span>}
                          <span className="font-medium">{ts.name}</span>
                        </div>
                        <div className="text-[10px] text-[#999]">
                          {ts.description} · {ts.test_cases?.length || 0} 题
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {testSets.length === 0 && (
              <div className="text-center py-6">
                <p className="text-xs text-yellow-400 mb-2">暂无测试集</p>
                <p className="text-[10px] text-[#999]">
                  运行 python backend/seed_test_sets.py 导入测试集
                </p>
              </div>
            )}

            <button
              onClick={handleRunEval}
              disabled={!selectedSetId}
              className="w-full px-4 py-2 bg-[#1e3a2f] text-white text-sm rounded hover:bg-green-600 transition-colors disabled:opacity-50"
            >
              ▶ 运行评测
            </button>
            {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
          </>
        )}

        {loading && (
          <div className="text-center py-10">
            <div className="animate-spin text-3xl mb-3">⏳</div>
            <p className="text-sm text-[#999]">{message || '评测中...'}</p>
          </div>
        )}

        {evalDetailResults && (
          <>
            <button
              onClick={() => { setEvalDetailResults(null); setEvalResults(null); setError(''); }}
              className="w-full text-xs text-[#999] hover:text-[#ddd]"
            >
              ← 返回重新评测
            </button>
            <MetricsCards summary={evalResults || evalDetailResults.summary} />
            <PerQuestionTable details={evalDetailResults.detail_results} />
          </>
        )}
      </div>
    </div>
  );
}
