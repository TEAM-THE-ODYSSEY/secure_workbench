import React, { useState, useEffect } from 'react';
import { Moon, Sun, LogOut, Lock } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { SessionProvider } from '../../context/SessionContext';
import { AiAssistantView } from '../assistant/AiAssistantView';
import { Sidebar } from '../../components/layout/Sidebar';
import { AdminNavTabs, type AdminTabKey } from './AdminNavTabs';
import { UsersView } from './UsersView';
import { ExternalApiView } from './ExternalApiView';
import { ModelsView } from './ModelsView';
import { KnowledgeBaseView } from './KnowledgeBaseView';
import { SovereigntyView } from './SovereigntyView';
import { AuditLogsView } from './AuditLogsView';
import { ErrorBoundary } from '../../components/common/ErrorBoundary';

interface AdminDashboardProps {
  onSwitchToUser?: () => void;
}

const getTabFromUrl = (): AdminTabKey => {
  const path = window.location.pathname;
  if (path.includes('/admin/external-api')) return 'external-api';
  if (path.includes('/admin/models')) return 'models';
  if (path.includes('/admin/knowledge-base')) return 'knowledge-base';
  if (path.includes('/admin/sovereignty')) return 'sovereignty';
  if (path.includes('/admin/audit-logs')) return 'audit-logs';
  if (path.includes('/admin/chat')) return 'chat';
  if (path.includes('/admin/users')) return 'users';
  return 'users';
};

export const AdminDashboard: React.FC<AdminDashboardProps> = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<AdminTabKey>(getTabFromUrl);

  // Synchronize URL path with tab changes
  const handleTabChange = (tab: AdminTabKey) => {
    setActiveTab(tab);
    window.history.pushState({}, '', `/admin/${tab}`);
  };

  useEffect(() => {
    const handlePopState = () => {
      setActiveTab(getTabFromUrl());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-100 dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-sans antialiased overflow-hidden select-none">
      {/* Admin Top Header */}
      <header className="h-16 px-6 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between z-20 shrink-0 transition-colors">
        {/* Left Branding */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#1b4332] to-[#2d6a4f] text-white font-black text-base flex items-center justify-center shadow-xs">
            M
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-sm text-slate-900 dark:text-white tracking-tight">MRPL</span>
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">Admin Control Center</span>
              <span className="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400 text-[10px] font-bold border border-amber-500/20 flex items-center gap-1">
                <Lock className="w-2.5 h-2.5" />
                RESTRICTED ACCESS
              </span>
            </div>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 font-normal">
              System Administration, Model Routing & Security Configuration
            </p>
          </div>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/60">
            <div className="w-7 h-7 rounded-full bg-[#1b4332] text-white flex items-center justify-center font-bold text-xs">
              {user?.username?.slice(0, 2).toUpperCase() || 'AD'}
            </div>
            <div className="flex flex-col text-left">
              <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 leading-tight">
                {user?.username || 'Admin User'}
              </span>
              <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                {user?.role?.toUpperCase() || 'ADMIN'}
              </span>
            </div>
          </div>

          <div className="h-6 w-px bg-slate-200 dark:bg-slate-800" />

          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <button
              onClick={logout}
              className="p-2 rounded-lg text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Horizontal Nav Tabs */}
      <AdminNavTabs
        activeTab={activeTab}
        onTabChange={handleTabChange}
      />

      {/* Main Tab Content Viewport */}
      <main className="flex-1 overflow-y-auto bg-slate-50 dark:bg-slate-950 p-6 transition-colors">
        <ErrorBoundary>
          {activeTab === 'users' && <UsersView />}
          {activeTab === 'external-api' && <ExternalApiView />}
          {activeTab === 'models' && <ModelsView />}
          {activeTab === 'knowledge-base' && <KnowledgeBaseView />}
          {activeTab === 'sovereignty' && <SovereigntyView />}
          {activeTab === 'audit-logs' && <AuditLogsView />}
          {activeTab === 'chat' && (
            <SessionProvider>
              <div className="flex h-full w-full rounded-2xl overflow-hidden shadow-xs border border-slate-200 dark:border-slate-800 bg-[#ffffff] dark:bg-slate-900">
                <Sidebar />
                <div className="flex-1 h-full overflow-hidden">
                  <ErrorBoundary>
                    <AiAssistantView />
                  </ErrorBoundary>
                </div>
              </div>
            </SessionProvider>
          )}
        </ErrorBoundary>
      </main>
    </div>
  );
};
