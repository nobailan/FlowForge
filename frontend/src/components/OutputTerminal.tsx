import { useState, useEffect } from 'react';
import { useAppStore } from '../store/appStore';
import { useCanvasStore } from '../store/canvasStore';

export default function OutputTerminal() {
  const executionId = useAppStore((s) => s.executionId);
  const executionStatus = useAppStore((s) => s.executionStatus);
  const [expanded, setExpanded] = useState(false);
  const [output, setOutput] = useState<Record<string, string>>({});
  const [totalTokens, setTotalTokens] = useState(0);
  const [loading, setLoading] = useState(false);

  // Fetch result when execution completes
  useEffect(() => {
    if (!executionId || executionStatus !== 'completed') return;
    setLoading(true);
    fetch(`/api/execute/${executionId}`)
      .then((r) => r.json())
      .then((d) => {
        const no = d.output_data?.node_outputs || {};
        const results: Record<string, string> = {};
        for (const [nid, nd] of Object.entries(no)) {
          const ndata = nd as any;
          results[nid] = ndata?.output || '';
        }
        setOutput(results);
        setTotalTokens(d.total_tokens || 0);
        setExpanded(true); // auto-expand on completion
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [executionId, executionStatus]);

  if (!executionId) return null;

  const nodes = useCanvasStore.getState().nodes;
  const hasOutput = Object.values(output).some((o) => o);

  return (
    <div className="border-t border-[#555] bg-[#1a1b26] text-[#eee]">
      {/* Terminal header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-1.5 text-xs hover:bg-gray-800 transition-colors"
      >
        <span className="text-[#999]">{expanded ? '▾' : '▸'}</span>
        <span className="text-[#999] font-semibold">📋 Output Terminal</span>
        {executionStatus === 'completed' && (
          <span className="text-green-400">✅</span>
        )}
        {totalTokens > 0 && (
          <span className="text-yellow-400 font-mono">{totalTokens.toLocaleString()}T</span>
        )}
        {loading && <span className="text-[#999]">Loading...</span>}
        <span className="flex-1" />
        <span className="text-[#ccc] text-[10px]">ID: {executionId.slice(0, 8)}</span>
      </button>

      {/* Terminal body */}
      {expanded && (
        <div className="border-t border-[#555] max-h-64 overflow-y-auto font-mono text-xs leading-relaxed p-3 space-y-3">
          {!hasOutput && !loading && (
            <div className="text-[#ccc] text-center py-4">
              {executionStatus === 'running'
                ? '⏳ Execution in progress...'
                : 'No output yet. Run a flow to see results here.'}
            </div>
          )}
          {nodes.map((node) => {
            const nodeOutput = output[node.id];
            if (!nodeOutput) return null;
            const label = (node.data as any)?.label || node.id;
            return (
              <div key={node.id}>
                <div className="text-blue-400 font-semibold mb-1">
                  ── {label} ──
                </div>
                <div className="text-[#ddd] whitespace-pre-wrap break-words pl-2 border-l-2 border-[#555]">
                  {nodeOutput}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
