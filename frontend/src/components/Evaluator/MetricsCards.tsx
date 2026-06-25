import type { EvalSummary } from '../../types/evaluation';

interface Props {
  summary: EvalSummary;
}

export default function MetricsCards({ summary }: Props) {
  const cards = [
    {
      label: '成功率',
      value: `${(summary.success_rate * 100).toFixed(1)}%`,
      color: summary.success_rate >= 0.7 ? 'text-green-600' : 'text-red-600',
      bg: summary.success_rate >= 0.7 ? 'bg-[#1e3a2f]' : 'bg-[#3a1e1e]',
    },
    {
      label: '平均延迟',
      value: `${summary.avg_latency_ms}ms`,
      color: 'text-blue-600',
      bg: 'bg-[#1e3a5f]',
    },
    {
      label: '平均 Token',
      value: `${summary.avg_tokens}`,
      color: 'text-purple-400',
      bg: 'bg-[#2a1e3a]',
    },
    {
      label: '预估成本',
      value: `$${summary.total_cost_estimate.toFixed(4)}`,
      color: 'text-orange-400',
      bg: 'bg-[#3a2e1e]',
    },
    {
      label: '工具调用',
      value: `${summary.total_tool_calls ?? 0}`,
      color: 'text-teal-400',
      bg: 'bg-[#1e3a3a]',
    },
    {
      label: '工具成功率',
      value: `${((summary.tool_success_rate ?? 0) * 100).toFixed(0)}%`,
      color: 'text-indigo-400',
      bg: 'bg-[#1e1e3a]',
    },
  ];

  return (
    <div>
      <h4 className="text-xs font-semibold text-[#999] uppercase mb-2">摘要</h4>
      <div className="grid grid-cols-2 gap-2">
        {cards.map((card) => (
          <div key={card.label} className={`${card.bg} rounded-lg p-2.5`}>
            <div className={`text-xl font-bold ${card.color}`}>{card.value}</div>
            <div className="text-[10px] text-[#999]">{card.label}</div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-2 text-[10px] text-[#999]">
        <span>✅ {summary.passed} 通过</span>
        <span>❌ {summary.failed} 失败</span>
        <span>📝 {summary.total_questions} 总计</span>
        <span>🔧 {summary.total_tool_calls ?? 0} 工具</span>
      </div>
    </div>
  );
}
