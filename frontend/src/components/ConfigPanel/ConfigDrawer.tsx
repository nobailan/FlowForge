import { useCanvasStore } from '../../store/canvasStore';
import { useAppStore } from '../../store/appStore';
import NodeConfigForm from './NodeConfigForm';

export default function ConfigDrawer() {
  const selectedNodeId = useCanvasStore((s) => s.selectedNodeId);
  const node = useCanvasStore((s) =>
    s.nodes.find((n) => n.id === selectedNodeId)
  );
  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const selectNode = useCanvasStore((s) => s.selectNode);

  if (!node) {
    return (
      <div className="w-72 border-l bg-[#252526] p-4">
        <p className="text-[#999] text-sm text-center mt-20">
          Select a node on the canvas to configure it.
        </p>
      </div>
    );
  }

  const handleClose = () => {
    selectNode(null);
    setRightPanel(null);
  };

  const handleDelete = () => {
    useCanvasStore.getState().deleteSelected();
    setRightPanel(null);
  };

  return (
    <div className="w-72 border-l bg-[#252526] flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-semibold text-sm">
          {node.data.type.toUpperCase()} Configuration
        </h3>
        <button
          onClick={handleClose}
          className="text-[#999] hover:text-[#ccc] text-lg leading-none"
        >
          ×
        </button>
      </div>

      {/* Node info */}
      <div className="px-3 py-2 border-b bg-[#2d2d30]">
        <div className="text-xs text-[#999]">
          ID: <code className="text-[11px]">{node.id}</code>
        </div>
        <div className="text-xs text-[#999]">
          Type: <span className="font-medium">{node.data.type}</span>
        </div>
      </div>

      {/* Config form */}
      <div className="flex-1 overflow-y-auto p-3">
        <NodeConfigForm node={node} />
      </div>

      {/* Delete button */}
      <div className="p-3 border-t">
        <button
          onClick={handleDelete}
          className="w-full py-1.5 text-xs text-red-500 border border-red-200 rounded hover:bg-[#3a1e1e] transition-colors"
        >
          🗑 Delete Node
        </button>
      </div>
    </div>
  );
}
