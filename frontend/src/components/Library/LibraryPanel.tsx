import { useState, useEffect } from 'react';
import { useCanvasStore } from '../../store/canvasStore';
import { useAppStore } from '../../store/appStore';
import { graphsApi, type ArchitectureSummary } from '../../api/graphs';

export default function LibraryPanel() {
  const setRightPanel = useAppStore((s) => s.setRightPanel);
  const fromCanvasJSON = useCanvasStore((s) => s.fromCanvasJSON);
  const setArchitectureId = useAppStore((s) => s.setArchitectureId);
  const setArchitectureName = useAppStore((s) => s.setArchitectureName);
  const [architectures, setArchitectures] = useState<ArchitectureSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadArchitectures();
  }, []);

  const loadArchitectures = async () => {
    try {
      const list = await graphsApi.list();
      setArchitectures(list);
    } catch (e: any) {
      setError(e.message);
    }
    setLoading(false);
  };

  const handleLoad = async (id: string) => {
    try {
      const arch = await graphsApi.get(id);
      fromCanvasJSON(arch.canvas_data);
      setArchitectureId(arch.id);
      setArchitectureName(arch.name);
      setRightPanel(null); // Close library to see canvas
    } catch (e: any) {
      alert('Failed to load: ' + e.message);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"?`)) return;
    try {
      await graphsApi.delete(id);
      setArchitectures(architectures.filter((a) => a.id !== id));
    } catch (e: any) {
      alert('Failed to delete: ' + e.message);
    }
  };

  if (loading) {
    return (
      <div className="w-80 border-l bg-[#252526] p-4">
        <h3 className="font-semibold text-sm mb-3">📦 Architecture Library</h3>
        <p className="text-xs text-[#999] text-center mt-20">Loading...</p>
      </div>
    );
  }

  return (
    <div className="w-80 border-l bg-[#252526] flex flex-col h-full overflow-hidden">
      <div className="p-3 border-b flex items-center justify-between">
        <h3 className="font-semibold text-sm">📦 Architecture Library</h3>
        <button onClick={() => setRightPanel(null)} className="text-[#999]">×</button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {error && <p className="text-xs text-red-500">{error}</p>}

        {architectures.length === 0 && (
          <p className="text-xs text-[#999] text-center mt-20">
            No saved architectures yet. Create one and save it!
          </p>
        )}

        {architectures.map((arch) => (
          <div
            key={arch.id}
            className="border rounded p-2.5 hover:border-blue-300 transition-colors"
          >
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-xs font-medium truncate flex-1">{arch.name}</h4>
              <span className="text-[10px] text-[#999]">
                {arch.updated_at ? new Date(arch.updated_at).toLocaleDateString() : ''}
              </span>
            </div>
            {arch.description && (
              <p className="text-[10px] text-[#999] mb-2">{arch.description}</p>
            )}
            <div className="flex gap-1">
              <button
                onClick={() => handleLoad(arch.id)}
                className="flex-1 px-2 py-1 text-[10px] bg-[#1e3a5f] text-blue-600 rounded hover:bg-blue-100 transition-colors"
              >
                Load
              </button>
              <button
                onClick={() => handleDelete(arch.id, arch.name)}
                className="px-2 py-1 text-[10px] bg-[#3a1e1e] text-red-500 rounded hover:bg-red-100 transition-colors"
              >
                🗑
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Refresh button */}
      <div className="p-3 border-t">
        <button
          onClick={loadArchitectures}
          className="w-full py-1.5 text-xs text-[#999] border rounded hover:bg-[#2d2d30]"
        >
          🔄 Refresh
        </button>
      </div>
    </div>
  );
}
