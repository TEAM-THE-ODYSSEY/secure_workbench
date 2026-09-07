import React, { useState, useEffect } from 'react';
import { Cpu, Search, Plus, X } from 'lucide-react';

export interface ModelItem {
  model_id: string;
  model_name: string;
  ollama_tag: string;
  model_type: string;
  context_length: number;
  quantization: string;
  memory_requirement: string;
  capabilities: string[];
  is_default: boolean;
  default_tasks: string;
}

export const ModelsView: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [, setLoading] = useState(true);

  // Form state for adding model
  const [modelName, setModelName] = useState('');
  const [ollamaTag, setOllamaTag] = useState('');
  const [modelType, setModelType] = useState('LLM Reasoning & Instruction');
  const [quantization] = useState('Q4_K_M');

  const [modelsList, setModelsList] = useState<ModelItem[]>([]);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/models');
      if (res.ok) {
        const data = await res.json();
        if (data.models && Array.isArray(data.models)) {
          const mapped = data.models.map((m: any) => ({
            model_id: m.model_id,
            model_name: m.model_name,
            ollama_tag: m.ollama_tag || m.model_name,
            model_type: m.model_type || 'LLM Reasoning',
            context_length: m.context_length || 8192,
            quantization: m.quantization || 'Q4_K_M',
            memory_requirement: m.memory_requirement || '8.0 GB VRAM',
            capabilities: m.capabilities || ['chat', 'doc_qa'],
            is_default: true,
            default_tasks: (m.supported_tasks || []).join(', ') || 'chat',
          }));
          setModelsList(mapped);
        }
      }
    } catch (err) {
      console.error('Failed to fetch models from API:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleAddModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modelName.trim() || !ollamaTag.trim()) return;

    const newModelItem: ModelItem = {
      model_id: `mod-mrpl-${Math.random().toString(36).substring(2, 7)}`,
      model_name: modelName.trim(),
      ollama_tag: ollamaTag.trim(),
      model_type: modelType,
      context_length: 16384,
      quantization: quantization,
      memory_requirement: '16.0 GB VRAM',
      capabilities: ['doc_qa', 'chat'],
      is_default: false,
      default_tasks: 'doc_qa',
    };

    setModelsList((prev) => [newModelItem, ...prev]);

    // Post to API if backend supports model creation
    try {
      const token = localStorage.getItem('mrpl_token');
      await fetch('/api/models', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          model_id: newModelItem.model_id,
          model_name: newModelItem.model_name,
          model_type: newModelItem.model_type,
          capabilities: newModelItem.capabilities,
          context_length: newModelItem.context_length,
          quantization: newModelItem.quantization,
          memory_requirement: newModelItem.memory_requirement,
          supported_tasks: ['SIMPLE', 'REASONING'],
          ollama_tag: newModelItem.ollama_tag,
          is_default_for_tasks: [],
        }),
      });
    } catch (err) {
      console.warn('Backend model save notice:', err);
    }

    // Auto-log audit event
    fetch('/api/v1/admin/audit-events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'MODEL_REGISTERED',
        actor: 'operator / Admin',
        category: 'MODEL_REGISTRY',
        details: `Registered local model '${modelName}' (${ollamaTag}) in Ollama vLLM engine`,
        status: 'SUCCESS',
      }),
    }).catch(() => {});

    setModelName('');
    setOllamaTag('');
    setIsModalOpen(false);
  };

  const filteredModels = modelsList.filter((m) => {
    const matchesSearch =
      m.model_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.ollama_tag.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.model_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter ? m.model_type.includes(typeFilter) : true;
    return matchesSearch && matchesType;
  });

  return (
    <div className="space-y-6 font-sans">
      
      {/* Title Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <span>Local Model Registry & Acceleration</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Configure local vLLM and Ollama models running on local GPU accelerators.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-[#1b4332] hover:bg-[#2d6a4f] text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-xs flex items-center gap-2 transition-all cursor-pointer shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Model</span>
        </button>
      </div>

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400 dark:text-slate-500 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by model name, tag, or ID..."
            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-600 transition-colors shadow-2xs"
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="w-full sm:w-48 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs px-3.5 py-2.5 rounded-xl focus:outline-none shadow-2xs"
        >
          <option value="">All Model Types</option>
          <option value="LLM">LLM Reasoning</option>
          <option value="Vision">Vision & Multimodal</option>
          <option value="Embedding">Vector Embedding</option>
        </select>
      </div>

      {/* Model Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredModels.map((m) => (
          <div
            key={m.model_id}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-2xs flex flex-col justify-between space-y-4"
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-extrabold text-sm text-slate-800 dark:text-slate-100 flex items-center gap-2">
                    <span>{m.model_name}</span>
                    {m.is_default && (
                      <span className="bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 text-[9px] font-extrabold px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-800">
                        ACTIVE DEFAULT
                      </span>
                    )}
                  </h3>
                  <p className="text-[11px] font-mono text-slate-400 mt-0.5">{m.ollama_tag}</p>
                </div>
                <div className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 shrink-0">
                  <Cpu className="w-5 h-5" />
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap pt-1">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                  {m.model_type}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  Ctx: {m.context_length.toLocaleString()}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                  {m.quantization}
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-xs space-y-1.5">
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-slate-400">VRAM Requirement:</span>
                <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400">{m.memory_requirement}</span>
              </div>
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-slate-400">Default Tasks:</span>
                <span className="font-semibold text-slate-700 dark:text-slate-300">{m.default_tasks}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Model Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden font-sans">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-slate-100">
                Register Local Model
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddModel} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Model Display Name
                </label>
                <input
                  type="text"
                  required
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="e.g. Qwen 2.5 7B Fine-Tuned"
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  vLLM / Ollama Model Tag
                </label>
                <input
                  type="text"
                  required
                  value={ollamaTag}
                  onChange={(e) => setOllamaTag(e.target.value)}
                  placeholder="e.g. Qwen/Qwen2.5-7B-Instruct"
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Model Category
                </label>
                <select
                  value={modelType}
                  onChange={(e) => setModelType(e.target.value)}
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none"
                >
                  <option value="LLM Reasoning & Instruction">LLM Reasoning & Instruction</option>
                  <option value="Vision & Multimodal Reasoning">Vision & Multimodal Reasoning</option>
                  <option value="Reasoning & Optimization">Reasoning & Optimization</option>
                  <option value="Vector Embedding">Vector Embedding</option>
                </select>
              </div>

              <div className="pt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#1b4332] hover:bg-[#2d6a4f] text-white text-xs font-bold rounded-lg shadow-xs"
                >
                  Register Model
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
