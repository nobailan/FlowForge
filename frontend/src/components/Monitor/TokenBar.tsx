import type { NodeEvent } from '../../types/execution';

interface Props {
  events: NodeEvent[];
}

export default function TokenBar({ events }: Props) {
  const nodesWithTokens = events.filter((e) => e.token_count > 0);
  const maxTokens = Math.max(...nodesWithTokens.map((e) => e.token_count), 1);

  if (nodesWithTokens.length === 0) return null;

  return (
    <div className="px-3 py-2 border-b">
      <div className="text-[10px] text-[#999] mb-1">Token Consumption by Node</div>
      <div className="space-y-1">
        {nodesWithTokens.map((event) => (
          <div key={event.node_id} className="flex items-center gap-2">
            <span className="text-[10px] text-[#999] w-16 truncate">{event.node_id}</span>
            <div className="flex-1 bg-[#3e3e42] rounded-full h-2">
              <div
                className="bg-blue-400 h-2 rounded-full transition-all"
                style={{ width: `${(event.token_count / maxTokens) * 100}%` }}
              />
            </div>
            <span className="text-[10px] text-[#999] w-10 text-right">
              {event.token_count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
