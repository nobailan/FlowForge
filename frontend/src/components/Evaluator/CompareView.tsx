import { useState, useEffect } from 'react';
import { useAppStore } from '../../store/appStore';
import { evaluateApi } from '../../api/evaluate';
import type { CompareResult } from '../../types/evaluation';

export default function CompareView() {
  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const [compareData, setCompareData] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadComparison();
  }, []);

  const loadComparison = async () => {
    try {
      const runs = await evaluateApi.listRuns();
      if (runs.length < 2) {
        setError('Need at least 2 evaluation runs to compare. Run more evaluations first.');
        setLoading(false);
        return;
      }
      // Compare the 2 most recent runs
      const sorted = runs.sort(
        (a, b) =>
          new Date(b.completed_at || '').getTime() -
          new Date(a.completed_at || '').getTime()
      );
      const data = await evaluateApi.compare([sorted[0].id, sorted[1].id]);
      setCompareData(data);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="w-[400px] border-l bg-[#252526] p-4">
        <p className="text-sm text-[#999] text-center mt-20">Loading comparison...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-[400px] border-l bg-[#252526] p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm">📊 Architecture Compare</h3>
          <button onClick={() => setRightPanel(null)} className="text-[#999]">×</button>
        </div>
        <p className="text-sm text-[#999] text-center mt-20">{error}</p>
      </div>
    );
  }

  const table = compareData?.comparison_table || [];
  const diffs = compareData?.diffs || [];

  return (
    <div className="w-[420px] border-l bg-[#252526] flex flex-col h-full overflow-hidden">
      <div className="p-3 border-b flex items-center justify-between">
        <h3 className="font-semibold text-sm">📊 Architecture Compare</h3>
        <button onClick={() => setRightPanel(null)} className="text-[#999]">×</button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Comparison table */}
        <table className="w-full text-xs border">
          <thead className="bg-[#2d2d30]">
            <tr>
              <th className="text-left px-2 py-1.5">Metric</th>
              {table.map((row) => (
                <th key={row.name} className="text-right px-2 py-1.5">
                  {row.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {[
              { label: 'Success Rate', key: 'success_rate', format: (v: number) => `${(v * 100).toFixed(1)}%` },
              { label: 'Avg Latency', key: 'avg_latency_ms', format: (v: number) => `${v}ms` },
              { label: 'Avg Tokens', key: 'avg_tokens', format: (v: number) => `${v}` },
              { label: 'Cost', key: 'total_cost', format: (v: number) => `$${v.toFixed(4)}` },
              { label: 'Tool Calls', key: 'total_tool_calls', format: (v: number) => `${v ?? 0}` },
              { label: 'Tool Success', key: 'tool_success_rate', format: (v: number) => `${((v ?? 0) * 100).toFixed(0)}%` },
              { label: 'Passed/Failed', key: 'passed', format: (_: number, row: any) => `${row.passed}/${row.passed + row.failed}` },
            ].map((metric) => (
              <tr key={metric.label}>
                <td className="px-2 py-1.5 font-medium text-[#ccc]">{metric.label}</td>
                {table.map((row) => (
                  <td key={row.name} className="text-right px-2 py-1.5">
                    {metric.format((row as any)[metric.key], row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        {/* Diffs */}
        {diffs.map((diff, i) => (
          <div key={i} className="border rounded p-3">
            <div className="text-xs font-semibold mb-2">{diff.comparison}</div>
            <div className="grid grid-cols-2 gap-1 text-[10px] text-[#999]">
              <div>
                Success Rate Δ:{' '}
                <span className={diff.success_rate_delta >= 0 ? 'text-green-600' : 'text-red-600'}>
                  {(diff.success_rate_delta * 100).toFixed(1)}%
                </span>
              </div>
              <div>
                Latency Δ:{' '}
                <span className={diff.latency_delta_ms <= 0 ? 'text-green-600' : 'text-red-600'}>
                  {diff.latency_delta_ms}ms
                </span>
              </div>
              <div>
                Tokens Δ:{' '}
                <span className={diff.tokens_delta <= 0 ? 'text-green-600' : 'text-red-600'}>
                  {diff.tokens_delta}
                </span>
              </div>
              <div>
                Cost Δ:{' '}
                <span className={diff.cost_delta <= 0 ? 'text-green-600' : 'text-red-600'}>
                  ${diff.cost_delta.toFixed(4)}
                </span>
              </div>
              <div>
                Tools Δ:{' '}
                <span className={diff.tool_calls_delta <= 0 ? 'text-green-600' : 'text-red-600'}>
                  {diff.tool_calls_delta}
                </span>
              </div>
            </div>
            <div className="mt-1.5 pt-1.5 border-t text-[10px]">
              Winner:{' '}
              <span className="font-bold text-green-600">{diff.winner}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
