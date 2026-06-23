import { useAppStore } from '../../store/appStore';
import NodeStatusList from './NodeStatusList';
import TokenBar from './TokenBar';

export default function MonitorPanel() {
  const executionStatus = useAppStore((s) => s.executionStatus);
  const nodeEvents = useAppStore((s) => s.nodeEvents);
  const executionId = useAppStore((s) => s.executionId);
  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const clearExecution = useAppStore((s) => s.clearExecution);

  const totalTokens = nodeEvents.reduce((sum, e) => sum + (e.token_count || 0), 0);
  const totalLatency = nodeEvents.reduce((sum, e) => sum + (e.latency_ms || 0), 0);
  const completedCount = nodeEvents.filter((e) => e.status === 'completed').length;
  const errorCount = nodeEvents.filter((e) => e.status === 'error').length;
  const totalNodes = new Set(nodeEvents.map((e) => e.node_id)).size || 1;

  if (executionStatus === 'idle') {
    return (
      <div className="w-72 border-l bg-[#252526] p-4">
        <h3 className="font-semibold text-sm mb-2">Execution Monitor</h3>
        <p className="text-[#999] text-xs text-center mt-20">
          Click "Run" to execute the flow. Node status will appear here in real-time.
        </p>
      </div>
    );
  }

  return (
    <div className="w-72 border-l bg-[#252526] flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-sm">Execution Monitor</h3>
          <p className="text-[10px] text-[#999]">
            ID: {executionId?.slice(0, 8)}...
          </p>
        </div>
        <div className="flex gap-1">
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
              executionStatus === 'running'
                ? 'bg-yellow-100 text-yellow-700 animate-pulse'
                : executionStatus === 'completed'
                ? 'bg-green-100 text-green-400'
                : executionStatus === 'error'
                ? 'bg-red-100 text-red-400'
                : 'bg-[#3e3e42] text-[#999]'
            }`}
          >
            {executionStatus.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-3 py-2 border-b">
        <div className="flex justify-between text-[10px] text-[#999] mb-1">
          <span>Progress</span>
          <span>
            {completedCount}/{totalNodes} nodes
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full transition-all duration-500 ${
              executionStatus === 'error' ? 'bg-[#3a1e1e]' : 'bg-[#1e3a5f]'
            }`}
            style={{ width: `${(completedCount / totalNodes) * 100}%` }}
          />
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2 px-3 py-2 border-b text-center">
        <div className="bg-[#2d2d30] rounded p-1.5">
          <div className="text-lg font-bold text-blue-600">{totalTokens}</div>
          <div className="text-[10px] text-[#999]">Total Tokens</div>
        </div>
        <div className="bg-[#2d2d30] rounded p-1.5">
          <div className="text-lg font-bold text-purple-400">{totalLatency}ms</div>
          <div className="text-[10px] text-[#999]">Total Latency</div>
        </div>
      </div>

      {/* Token consumption bar */}
      <TokenBar events={nodeEvents} />

      {/* Per-node status */}
      <div className="flex-1 overflow-y-auto">
        <NodeStatusList events={nodeEvents} />
      </div>

      {/* Close button */}
      <div className="p-3 border-t">
        <button
          onClick={() => {
            if (executionStatus === 'completed' || executionStatus === 'error') {
              clearExecution();
            }
            setRightPanel(null);
          }}
          className="w-full py-1.5 text-xs text-[#999] border rounded hover:bg-[#2d2d30]"
        >
          Close Monitor
        </button>
      </div>
    </div>
  );
}
