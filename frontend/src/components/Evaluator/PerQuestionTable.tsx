import type { EvalDetail } from '../../types/evaluation';

interface Props {
  details: EvalDetail[];
}

export default function PerQuestionTable({ details }: Props) {
  if (!details || details.length === 0) return null;

  return (
    <div>
      <h4 className="text-xs font-semibold text-[#999] uppercase mb-2">
        逐题结果
      </h4>
      <div className="border rounded overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-[#2d2d30]">
            <tr>
              <th className="text-left px-2 py-1.5 font-medium text-[#999]">#</th>
              <th className="text-left px-2 py-1.5 font-medium text-[#999]">问题</th>
              <th className="text-center px-2 py-1.5 font-medium text-[#999]">结果</th>
              <th className="text-right px-2 py-1.5 font-medium text-[#999]">延迟</th>
              <th className="text-right px-2 py-1.5 font-medium text-[#999]">Token</th>
              <th className="text-right px-2 py-1.5 font-medium text-[#999]">工具</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {details.map((d) => (
              <tr key={d.test_id} className="hover:bg-[#2d2d30]">
                <td className="px-2 py-1 text-[#999]">{d.test_id}</td>
                <td className="px-2 py-1 max-w-[150px] truncate" title={d.question}>
                  {d.question}
                </td>
                <td className="px-2 py-1 text-center">
                  {d.success ? (
                    <span className="text-green-500">✅</span>
                  ) : (
                    <span className="text-red-500" title={d.error || 'Failed'}>❌</span>
                  )}
                </td>
                <td className="px-2 py-1 text-right text-[#999]">{d.latency_ms}ms</td>
                <td className="px-2 py-1 text-right text-[#999]">{d.tokens}</td>
                <td className="px-2 py-1 text-right text-[#999]">{d.tool_calls ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
