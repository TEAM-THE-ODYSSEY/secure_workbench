import React, { useState, useEffect } from 'react';
import { Plus, Server, Cpu, AlertCircle, Loader2, Database, ChevronUp } from 'lucide-react';

const apiFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = localStorage.getItem('mrpl_token');
  const headers: Record<string, string> = { ...Object.fromEntries(Object.entries(options.headers || {})) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
};

interface Model {
  model_id: string;
  model_name: string;
  model_type: string;
  capabilities: string;
  context_length: number;
  quantization: string;
  memory_requirement: string;
  ollama_tag: string;
}

export const ModelManager: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [submitStatus, setSubmitStatus] = useState<{type: 'success'|'error', msg: string} | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const initialFormState = {
    model_id: '',
    model_name: '',
    model_type: 'foundation',
    ollama_tag: '',
    capabilities: '',
    context_length: 8192,
    quantization: '4-bit',
    memory_requirement: '8GB'
  };
  const [formData, setFormData] = useState(initialFormState);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/models');
      if (res.ok) {
        const data = await res.json();
        setModels(data.models || []);
      } else {
        throw new Error('Failed to load models');
      }
    } catch (err) {
      console.error(err);
      setError('Could not connect to model registry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'context_length' ? parseInt(value) || 0 : value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitStatus(null);
    
    try {
      const res = await apiFetch('/api/models', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      if (res.ok) {
        setSubmitStatus({ type: 'success', msg: 'Model successfully added to registry.' });
        setFormData(initialFormState);
        fetchModels();
        setTimeout(() => setIsFormOpen(false), 2000);
      } else {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.message || 'Model not pulled in Ollama or configuration invalid.');
      }
    } catch (err: any) {
      setSubmitStatus({ type: 'error', msg: err.message || 'An error occurred while adding the model.' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Models Grid */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-slate-800">Model Registry</h2>
          <button 
            onClick={() => setIsFormOpen(!isFormOpen)}
            className="flex items-center px-4 py-2 bg-[#1b4332] text-white rounded-md hover:bg-[#2d6a4f] transition-colors shadow-sm"
          >
            {isFormOpen ? <ChevronUp className="w-4 h-4 mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
            Add New Model
          </button>
        </div>

        {/* Add Model Form */}
        {isFormOpen && (
          <div className="bg-white rounded-xl shadow-md border border-slate-200 overflow-hidden mb-8 animate-in slide-in-from-top-4 fade-in duration-300">
            <div className="bg-[#1b4332] px-6 py-4 border-b border-[#2d6a4f]">
              <h3 className="text-lg font-semibold text-white">Register New Model</h3>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Model ID</label>
                  <input required name="model_id" value={formData.model_id} onChange={handleInputChange} type="text" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-[#2d6a4f] focus:border-[#2d6a4f] outline-none" placeholder="e.g. llama-3-8b-instruct" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Model Name</label>
                  <input required name="model_name" value={formData.model_name} onChange={handleInputChange} type="text" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-[#2d6a4f] focus:border-[#2d6a4f] outline-none" placeholder="e.g. LLaMA 3 8B Instruct" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Model Type</label>
                  <select name="model_type" value={formData.model_type} onChange={handleInputChange} className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-[#2d6a4f] focus:border-[#2d6a4f] outline-none bg-white">
                    <option value="foundation">Foundation / Chat</option>
                    <option value="embedding">Embedding</option>
                    <option value="vision">Vision</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Ollama Tag</label>
                  <input required name="ollama_tag" value={formData.ollama_tag} onChange={handleInputChange} type="text" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-[#2d6a4f] focus:border-[#2d6a4f] outline-none" placeholder="e.g. llama3:8b" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Context Length</label>
                  <input required name="context_length" value={formData.context_length} onChange={handleInputChange} type="number" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-[#2d6a4f] focus:border-[#2d6a4f] outline-none" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Quantization</label>
                    <input required name="quantization" value={formData.quantization} onChange={handleInputChange} type="text" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-[#2d6a4f] focus:border-[#2d6a4f] outline-none" placeholder="e.g. 4-bit" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Memory Req.</label>
                    <input required name="memory_requirement" value={formData.memory_requirement} onChange={handleInputChange} type="text" className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-[#2d6a4f] focus:border-[#2d6a4f] outline-none" placeholder="e.g. 8GB" />
                  </div>
                </div>
              </div>
              
              <div className="mb-6">
                <label className="block text-sm font-medium text-slate-700 mb-1">Capabilities (Optional)</label>
                <textarea name="capabilities" value={formData.capabilities} onChange={handleInputChange} rows={3} className="w-full px-4 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-[#2d6a4f] focus:border-[#2d6a4f] outline-none" placeholder="Describe what this model is good at..."></textarea>
              </div>

              {submitStatus && (
                <div className={`mb-6 p-4 rounded-md flex items-start ${submitStatus.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                  <AlertCircle className="w-5 h-5 mr-3 mt-0.5" />
                  <span>{submitStatus.msg}</span>
                </div>
              )}

              <div className="flex justify-end space-x-3 border-t border-slate-100 pt-6">
                <button type="button" onClick={() => setIsFormOpen(false)} className="px-6 py-2 border border-slate-300 text-slate-700 rounded-md hover:bg-slate-50 transition-colors">
                  Cancel
                </button>
                <button type="submit" disabled={submitting} className="px-6 py-2 bg-[#1b4332] text-white rounded-md hover:bg-[#2d6a4f] transition-colors disabled:opacity-70 flex items-center shadow-sm">
                  {submitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Save Model
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Models List */}
        {loading ? (
          <div className="flex justify-center p-20">
            <Loader2 className="w-10 h-10 text-[#1b4332] animate-spin" />
          </div>
        ) : error ? (
          <div className="bg-red-50 text-red-700 p-6 rounded-xl border border-red-200 text-center">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-red-500" />
            <p>{error}</p>
          </div>
        ) : models.length === 0 ? (
          <div className="bg-white p-16 rounded-xl border border-slate-200 text-center shadow-sm">
            <Server className="w-16 h-16 mx-auto mb-4 text-slate-300" />
            <h3 className="text-xl font-medium text-slate-700 mb-2">No models registered</h3>
            <p className="text-slate-500 mb-6">Click "Add New Model" to register an Ollama model.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {models.map(model => (
              <div key={model.model_id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow">
                <div className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-slate-800">{model.model_name}</h3>
                      <p className="text-sm text-slate-500 font-mono mt-1">{model.model_id}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider
                      ${model.model_type === 'foundation' ? 'bg-blue-100 text-blue-800' : 
                        model.model_type === 'embedding' ? 'bg-purple-100 text-purple-800' : 
                        'bg-orange-100 text-orange-800'}`}>
                      {model.model_type}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-y-4 gap-x-6 mt-6">
                    <div className="flex items-center text-sm">
                      <Cpu className="w-4 h-4 text-slate-400 mr-2" />
                      <span className="text-slate-600">Context: </span>
                      <span className="ml-1 font-medium text-slate-800">{model.context_length}</span>
                    </div>
                    <div className="flex items-center text-sm">
                      <Database className="w-4 h-4 text-slate-400 mr-2" />
                      <span className="text-slate-600">Memory: </span>
                      <span className="ml-1 font-medium text-slate-800">{model.memory_requirement}</span>
                    </div>
                    <div className="flex items-center text-sm">
                      <Server className="w-4 h-4 text-slate-400 mr-2" />
                      <span className="text-slate-600">Tag: </span>
                      <span className="ml-1 font-medium text-slate-800 font-mono truncate" title={model.ollama_tag}>{model.ollama_tag}</span>
                    </div>
                    <div className="flex items-center text-sm">
                      <span className="w-4 h-4 rounded-full border border-slate-300 flex items-center justify-center text-[10px] text-slate-500 mr-2">Q</span>
                      <span className="text-slate-600">Quant: </span>
                      <span className="ml-1 font-medium text-slate-800">{model.quantization}</span>
                    </div>
                  </div>
                </div>
                {model.capabilities && (
                  <div className="bg-slate-50 px-6 py-3 border-t border-slate-100">
                    <p className="text-xs text-slate-500 italic line-clamp-2">{model.capabilities}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};
