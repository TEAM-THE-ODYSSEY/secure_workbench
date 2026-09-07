import React, { useState, useEffect } from 'react';
import { LayoutDashboard, Database, Cpu, Activity, AlertCircle, Loader2, MessageSquare, LogOut } from 'lucide-react';
import { KnowledgeManager } from './KnowledgeManager';
import { ModelManager } from './ModelManager';
import { SystemHealth } from './SystemHealth';
import { useAuth } from '../../context/AuthContext';

const apiFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = localStorage.getItem('mrpl_token');
  const headers: Record<string, string> = { ...Object.fromEntries(Object.entries(options.headers || {})) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
};

type Tab = 'dashboard' | 'knowledge' | 'models' | 'system';

interface DashboardStats {
  documentsCount: number;
  modelsCount: number;
  systemStatus: string;
}

interface AdminDashboardProps {
  onSwitchToUser?: () => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ onSwitchToUser }) => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === 'dashboard') {
      fetchDashboardStats();
    }
  }, [activeTab]);

  const fetchDashboardStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const [docsRes, modelsRes, healthRes] = await Promise.all([
        apiFetch('/api/knowledge/documents'),
        apiFetch('/api/models'),
        apiFetch('/api/health')
      ]);

      let documentsCount = 0;
      let modelsCount = 0;
      let systemStatus = 'unknown';

      if (docsRes.ok) {
        const docsData = await docsRes.json();
        documentsCount = Array.isArray(docsData) ? docsData.length : (docsData.documents?.length || 0);
      }
      
      if (modelsRes.ok) {
        const modelsData = await modelsRes.json();
        modelsCount = Array.isArray(modelsData.models) ? modelsData.models.length : 0;
      }

      if (healthRes.ok) {
        const healthData = await healthRes.json();
        systemStatus = healthData.status || 'online';
      }

      setStats({ documentsCount, modelsCount, systemStatus });
    } catch (err) {
      console.error('Failed to fetch dashboard stats', err);
      setError('Failed to load dashboard statistics.');
    } finally {
      setLoading(false);
    }
  };

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'knowledge', label: 'Knowledge Base', icon: Database },
    { id: 'models', label: 'Models', icon: Cpu },
    { id: 'system', label: 'System', icon: Activity },
  ] as const;

  return (
    <div className="flex h-screen w-full bg-slate-50 overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-[#1b4332] text-white flex flex-col shadow-xl z-10">
        <div className="p-6">
          <h1 className="text-xl font-bold tracking-wider">MRPL SOVEREIGN</h1>
          <p className="text-sm text-green-200 mt-1 opacity-80">Admin Workbench</p>
        </div>
        
        <nav className="flex-1 px-4 py-4 space-y-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center px-4 py-3 rounded-md transition-all duration-200 ${
                activeTab === item.id 
                  ? 'bg-[#2d6a4f] text-white shadow-md border-l-4 border-green-400' 
                  : 'text-green-100 hover:bg-[#2d6a4f]/50 hover:text-white border-l-4 border-transparent'
              }`}
            >
              <item.icon className="w-5 h-5 mr-3" />
              <span className="font-medium">{item.label}</span>
            </button>
          ))}
        </nav>
        
        <div className="p-4 border-t border-[#2d6a4f] space-y-2">
          {onSwitchToUser && (
            <button
              onClick={onSwitchToUser}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-600 rounded-md transition-colors shadow-sm"
            >
              <MessageSquare className="w-4 h-4" />
              <span>User Assistant View</span>
            </button>
          )}
          <button
            onClick={() => logout()}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-red-200 hover:bg-red-900/40 hover:text-white rounded-md transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
          <div className="flex items-center space-x-3 text-xs text-green-200 pt-2">
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
            <span>System Active ({user?.username})</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white shadow-sm h-16 flex items-center justify-between px-8 z-0 border-b border-slate-200">
          <h2 className="text-xl font-semibold text-slate-800 capitalize">
            {activeTab.replace('-', ' ')}
          </h2>
          <div className="flex items-center gap-3">
            {onSwitchToUser && (
              <button
                onClick={onSwitchToUser}
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-[#1b4332] bg-emerald-50 border border-emerald-300 hover:bg-emerald-100 rounded-lg transition-colors shadow-xs"
              >
                <MessageSquare className="w-4 h-4 text-emerald-700" />
                <span>Go to User Chat View</span>
              </button>
            )}
            <button
              onClick={() => logout()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign Out</span>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-8">
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              {loading && (
                <div className="flex items-center justify-center p-12">
                  <Loader2 className="w-8 h-8 text-[#1b4332] animate-spin" />
                </div>
              )}
              
              {error && (
                <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-md flex items-start">
                  <AlertCircle className="w-5 h-5 text-red-500 mr-3 mt-0.5" />
                  <p className="text-red-700">{error}</p>
                </div>
              )}
              
              {!loading && !error && stats && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 flex items-center">
                    <div className="bg-green-100 p-4 rounded-lg mr-4">
                      <Database className="w-8 h-8 text-[#166534]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">Documents Indexed</p>
                      <h3 className="text-3xl font-bold text-slate-800">{stats.documentsCount}</h3>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 flex items-center">
                    <div className="bg-blue-100 p-4 rounded-lg mr-4">
                      <Cpu className="w-8 h-8 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">Active Models</p>
                      <h3 className="text-3xl font-bold text-slate-800">{stats.modelsCount}</h3>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 flex items-center">
                    <div className="bg-indigo-100 p-4 rounded-lg mr-4">
                      <Activity className="w-8 h-8 text-indigo-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">System Status</p>
                      <h3 className="text-xl font-bold text-slate-800 capitalize flex items-center">
                        <span className={`w-3 h-3 rounded-full mr-2 ${stats.systemStatus.toLowerCase() === 'online' ? 'bg-green-500' : 'bg-amber-500'}`}></span>
                        {stats.systemStatus}
                      </h3>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'knowledge' && <KnowledgeManager />}
          {activeTab === 'models' && <ModelManager />}
          {activeTab === 'system' && <SystemHealth />}
        </main>
      </div>
    </div>
  );
};
