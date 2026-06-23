import { useEffect, useState } from 'react';
import type { Node } from '@xyflow/react';
import type { CanvasNodeData, NodeTypeInfo } from '../../types/canvas';
import { useCanvasStore } from '../../store/canvasStore';
import { templatesApi } from '../../api/templates';

interface Props {
  node: Node<CanvasNodeData>;
}

export default function NodeConfigForm({ node }: Props) {
  const [nodeTypes, setNodeTypes] = useState<NodeTypeInfo[]>([]);
  const updateNodeConfig = useCanvasStore((s) => s.updateNodeConfig);

  useEffect(() => {
    templatesApi.listNodeTypes().then(setNodeTypes).catch(console.error);
  }, []);

  const typeInfo = nodeTypes.find((nt) => nt.name === node.data.type);
  if (!typeInfo) {
    return <p className="text-xs text-[#999]">Loading config schema...</p>;
  }

  const schema = typeInfo.config_schema;
  const config = { ...typeInfo.default_config, ...node.data.config };

  const handleChange = (key: string, value: any) => {
    updateNodeConfig(node.id, { [key]: value });
  };

  return (
    <div className="space-y-3">
      {/* Label (always editable) */}
      <div>
        <label className="block text-[11px] font-medium text-[#ccc] mb-1">
          Label
        </label>
        <input
          type="text"
          value={node.data.label || ''}
          onChange={(e) => updateNodeConfig(node.id, { label: e.target.value })}
          className="w-full px-2 py-1 text-xs border rounded focus:outline-none focus:border-blue-400"
        />
      </div>

      {/* Dynamic fields from JSON Schema */}
      {schema.properties &&
        Object.entries(schema.properties).map(([key, prop]: [string, any]) => {
          if (key === 'label') return null;

          const value = config[key] ?? prop.default ?? '';

          if (prop.enum) {
            return (
              <div key={key}>
                <label className="block text-[11px] font-medium text-[#ccc] mb-1">
                  {prop.title || key}
                </label>
                <select
                  value={value}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-full px-2 py-1 text-xs border rounded focus:outline-none focus:border-blue-400"
                >
                  {prop.enum.map((opt: string) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            );
          }

          if (prop.type === 'number' || prop.type === 'integer') {
            return (
              <div key={key}>
                <label className="block text-[11px] font-medium text-[#ccc] mb-1">
                  {prop.title || key}
                  {prop.description && (
                    <span className="text-[#999] font-normal ml-1">
                      ({prop.description})
                    </span>
                  )}
                </label>
                <input
                  type="number"
                  value={value}
                  min={prop.minimum}
                  max={prop.maximum}
                  onChange={(e) =>
                    handleChange(
                      key,
                      prop.type === 'integer'
                        ? parseInt(e.target.value) || 0
                        : parseFloat(e.target.value) || 0
                    )
                  }
                  className="w-full px-2 py-1 text-xs border rounded focus:outline-none focus:border-blue-400"
                />
              </div>
            );
          }

          // Default: text / textarea
          const isLongText =
            prop.type === 'string' &&
            (value?.length > 80 || key.includes('prompt') || key.includes('description'));

          return (
            <div key={key}>
              <label className="block text-[11px] font-medium text-[#ccc] mb-1">
                {prop.title || key}
              </label>
              {isLongText ? (
                <textarea
                  value={value}
                  onChange={(e) => handleChange(key, e.target.value)}
                  rows={4}
                  className="w-full px-2 py-1 text-xs border rounded focus:outline-none focus:border-blue-400 resize-y font-mono"
                />
              ) : (
                <input
                  type="text"
                  value={value}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="w-full px-2 py-1 text-xs border rounded focus:outline-none focus:border-blue-400"
                />
              )}
              {prop.description && (
                <p className="text-[10px] text-[#999] mt-0.5">{prop.description}</p>
              )}
            </div>
          );
        })}
    </div>
  );
}
