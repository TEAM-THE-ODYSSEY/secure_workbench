import React, { useState, useEffect } from 'react';
import { Activity, Server, Database, HardDrive, RefreshCw, AlertCircle, Clock } from 'lucide-react';

const apiFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = localStorage.getItem('mrpl_token');
  const headers: Record<string, string> = { ...Object.fromEntries(Object.entries(options.headers || {})) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
};

interface HealthData {
  backend: {
    status: string;
    uptime?: string;
  };
  vllm: {
    status: string;
    active_model?: string;
    is_fallback?: boolean;
  };
  postgres: {
    status: string;
    connected: boolean;
  };
  minio: {
    status: string;
    fallback_local?: boolean;
  };
}

export const SystemHealth: React.FC = () => {
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const fetchHealth = async (isManualRefresh = false) => {
    if (isManualRefresh) setRefreshing(true);
    else if (!healthData) setLoading(true);
    
    try {
      const res = await apiFetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        // Fallback default structure if API doesn't perfectly match
        setHealthData({
          backend: data.backend || { status: data.status || 'unknown' },
          vllm: data.vllm || { status: 'unknown' },
          postgres: data.postgres || { status: 'unknown', connected: false },
          minio: data.minio || { status: 'unknown' }
        });
        setError(null);
        setLastChecked(new Date());
      } else {
        throw new Error('Health check failed');
      }
    } catch (err) {
      console.error(err);
      setError('Unable to reach monitoring services.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      fetchHealth();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string, isWarning = false) => {
    if (isWarning) return 'bg-amber-500';
    const s = status.toLowerCase();
    if (s === 'online' || s === 'connected' || s === 'healthy') return 'bg-green-500';
    if (s === 'offline' || s === 'disconnected' || s === 'error') return 'bg-red-500';
    return 'bg-slate-400';
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 mb-1">System Health</h2>
          <p className="text-slate-500 text-sm flex items-center">
            <Clock className="w-4 h-4 mr-1.5" />
            Last checked: {lastChecked.toLocaleTimeString()}
          </p>
        </div>
        <button 
          onClick={() => fetchHealth(true)}
          disabled={refreshing || loading}
          className="flex items-center px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-md hover:bg-slate-50 hover:text-[#1b4332] transition-colors shadow-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh Status
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-md flex items-start mb-6">
          <AlertCircle className="w-5 h-5 text-red-500 mr-3 mt-0.5" />
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {loading && !healthData ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-white h-32 rounded-xl shadow-sm border border-slate-100 animate-pulse"></div>
          ))}
        </div>
      ) : healthData ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Backend API */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col h-full relative overflow-hidden">
            <div className={`absolute top-0 left-0 w-1 h-full ${healthData.backend.status.toLowerCase() === 'online' ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center">
                <div className="bg-indigo-50 p-2.5 rounded-lg mr-3">
                  <Activity className="w-6 h-6 text-indigo-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800">Backend API</h3>
              </div>
              <div className="flex items-center bg-slate-50 px-3 py-1 rounded-full border border-slate-100">
                <span className={`w-2.5 h-2.5 rounded-full mr-2 ${getStatusColor(healthData.backend.status)}`}></span>
                <span className="text-xs font-medium text-slate-600 uppercase tracking-wide">{healthData.backend.status}</span>
              </div>
            </div>
            <div className="mt-auto pt-4 border-t border-slate-100">
              <p className="text-sm text-slate-500">
                Core API services and authentication.
                {healthData.backend.uptime && <span className="ml-2 block mt-1 font-mono text-xs">Uptime: {healthData.backend.uptime}</span>}
              </p>
            </div>
          </div>

          {/* vLLM Engine */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col h-full relative overflow-hidden">
            <div className={`absolute top-0 left-0 w-1 h-full ${healthData.vllm.status.toLowerCase() === 'online' ? (healthData.vllm.is_fallback ? 'bg-amber-500' : 'bg-green-500') : 'bg-red-500'}`}></div>
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center">
                <div className="bg-blue-50 p-2.5 rounded-lg mr-3">
                  <Server className="w-6 h-6 text-blue-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800">Inference Engine</h3>
              </div>
              <div className="flex items-center bg-slate-50 px-3 py-1 rounded-full border border-slate-100">
                <span className={`w-2.5 h-2.5 rounded-full mr-2 ${getStatusColor(healthData.vllm.status, healthData.vllm.is_fallback)}`}></span>
                <span className="text-xs font-medium text-slate-600 uppercase tracking-wide">
                  {healthData.vllm.is_fallback ? 'Fallback' : healthData.vllm.status}
                </span>
              </div>
            </div>
            <div className="mt-auto pt-4 border-t border-slate-100">
              <p className="text-sm text-slate-500 flex items-center justify-between">
                <span>Active Model:</span>
                <span className="font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-700">{healthData.vllm.active_model || 'None'}</span>
              </p>
            </div>
          </div>

          {/* PostgreSQL */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col h-full relative overflow-hidden">
            <div className={`absolute top-0 left-0 w-1 h-full ${healthData.postgres.status.toLowerCase() === 'online' || healthData.postgres.connected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center">
                <div className="bg-emerald-50 p-2.5 rounded-lg mr-3">
                  <Database className="w-6 h-6 text-emerald-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800">PostgreSQL</h3>
              </div>
              <div className="flex items-center bg-slate-50 px-3 py-1 rounded-full border border-slate-100">
                <span className={`w-2.5 h-2.5 rounded-full mr-2 ${getStatusColor(healthData.postgres.status || (healthData.postgres.connected ? 'connected' : 'disconnected'))}`}></span>
                <span className="text-xs font-medium text-slate-600 uppercase tracking-wide">
                  {healthData.postgres.status || (healthData.postgres.connected ? 'Connected' : 'Error')}
                </span>
              </div>
            </div>
            <div className="mt-auto pt-4 border-t border-slate-100">
              <p className="text-sm text-slate-500">
                Relational database for users and document metadata.
              </p>
            </div>
          </div>

          {/* MinIO Storage */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col h-full relative overflow-hidden">
            <div className={`absolute top-0 left-0 w-1 h-full ${healthData.minio.status.toLowerCase() === 'online' ? (healthData.minio.fallback_local ? 'bg-amber-500' : 'bg-green-500') : 'bg-red-500'}`}></div>
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center">
                <div className="bg-orange-50 p-2.5 rounded-lg mr-3">
                  <HardDrive className="w-6 h-6 text-orange-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800">MinIO Storage</h3>
              </div>
              <div className="flex items-center bg-slate-50 px-3 py-1 rounded-full border border-slate-100">
                <span className={`w-2.5 h-2.5 rounded-full mr-2 ${getStatusColor(healthData.minio.status, healthData.minio.fallback_local)}`}></span>
                <span className="text-xs font-medium text-slate-600 uppercase tracking-wide">
                  {healthData.minio.fallback_local ? 'Local Fallback' : healthData.minio.status}
                </span>
              </div>
            </div>
            <div className="mt-auto pt-4 border-t border-slate-100">
              <p className="text-sm text-slate-500">
                Object storage for knowledge base documents.
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
