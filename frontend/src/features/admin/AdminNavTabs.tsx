import React from 'react';
import { Users, CloudOff, Cpu, Database, ShieldCheck, ClipboardList, MessageSquare } from 'lucide-react';

export type AdminTabKey = 'users' | 'external-api' | 'models' | 'knowledge-base' | 'sovereignty' | 'audit-logs' | 'chat';

interface AdminNavTabsProps {
  activeTab: AdminTabKey;
  onTabChange: (tab: AdminTabKey) => void;
  modelCount?: number;
  docCount?: number;
}

export const AdminNavTabs: React.FC<AdminNavTabsProps> = ({
  activeTab,
  onTabChange,
  modelCount = 4,
  docCount = 6,
}) => {
  const TABS: Array<{
    key: AdminTabKey;
    label: string;
    icon: React.ElementType;
    badge?: number;
    dot?: boolean;
  }> = [
    { key: 'users', label: 'Users', icon: Users },
    { key: 'external-api', label: 'External API Calls', icon: CloudOff },
    { key: 'models', label: 'Models', icon: Cpu, badge: modelCount },
    { key: 'knowledge-base', label: 'Knowledge Base', icon: Database, badge: docCount },
    { key: 'sovereignty', label: 'Sovereignty', icon: ShieldCheck, dot: true },
    { key: 'audit-logs', label: 'Audit Logs', icon: ClipboardList },
    { key: 'chat', label: 'Chat', icon: MessageSquare },
  ];

  return (
    <div className="bg-slate-100/90 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-6 py-2 flex items-center justify-between overflow-x-auto gap-2 shrink-0 transition-colors">
      <div className="flex items-center gap-1.5 min-w-max">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.key;
          const Icon = tab.icon;

          return (
            <button
              key={tab.key}
              onClick={() => onTabChange(tab.key)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                isActive
                  ? 'bg-white dark:bg-slate-800 text-[#1b4332] dark:text-emerald-400 shadow-2xs border border-slate-200/80 dark:border-slate-700'
                  : 'text-slate-600 dark:text-slate-400 hover:bg-white/60 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-[#1b4332] dark:text-emerald-400' : 'text-slate-500 dark:text-slate-400'}`} />
              <span>{tab.label}</span>

              {tab.badge !== undefined && (
                <span className="ml-1 text-[10px] font-mono font-extrabold px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  {tab.badge}
                </span>
              )}

              {tab.dot && (
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse ml-0.5" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
