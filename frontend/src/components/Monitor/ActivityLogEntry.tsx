import type { ActivityLogEntry as LogEntry } from '../../hooks/useExecutionConsole';

interface Props {
  log: LogEntry;
}

export default function ActivityLogEntry({ log }: Props) {
  const time = new Date(log.timestamp * 1000).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  if (log.eventType === 'thinking') {
    return (
      <div className="px-2 py-0.5 hover:bg-gray-800/30 border-l-2 border-transparent hover:border-green-600">
        <span className="text-[#ccc]">{time}</span>{' '}
        <span className="text-green-500">💭</span>{' '}
        <span className="text-[#ddd]">{log.text}</span>
      </div>
    );
  }

  if (log.eventType === 'tool_start') {
    return (
      <div className="px-2 py-0.5 hover:bg-gray-800/30 border-l-2 border-transparent hover:border-blue-600">
        <span className="text-[#ccc]">{time}</span>{' '}
        <span className="text-blue-400">🔧</span>{' '}
        <span className="text-blue-300 font-semibold">{log.toolName}</span>
        {log.toolInput && (
          <span className="text-[#999] ml-1">({log.toolInput.slice(0, 80)})</span>
        )}
      </div>
    );
  }

  if (log.eventType === 'tool_end') {
    return (
      <div className="px-2 py-0.5 hover:bg-gray-800/30 border-l-2 border-transparent hover:border-purple-600">
        <span className="text-[#ccc]">{time}</span>{' '}
        <span className="text-purple-400">✓</span>{' '}
        <span className="text-[#999]">{log.text.slice(0, 120)}</span>
      </div>
    );
  }

  if (log.eventType === 'completed') {
    return (
      <div className="px-2 py-0.5 bg-green-900/20 border-l-2 border-green-500">
        <span className="text-[#ccc]">{time}</span>{' '}
        <span className="text-green-400">✅</span>{' '}
        <span className="text-[#eee] font-medium">{log.text.slice(0, 300) || 'Done'}</span>
      </div>
    );
  }

  if (log.eventType === 'error') {
    return (
      <div className="px-2 py-0.5 bg-red-900/20 border-l-2 border-red-500">
        <span className="text-[#ccc]">{time}</span>{' '}
        <span className="text-red-400">❌</span>{' '}
        <span className="text-red-300">{log.text.slice(0, 300) || 'Error'}</span>
      </div>
    );
  }

  return null;
}
