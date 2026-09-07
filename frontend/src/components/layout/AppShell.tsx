import React, { useState } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';
import { SettingsModal } from '../modals/SettingsModal';

export interface AppShellProps {
  children: React.ReactNode;
  onSwitchToAdmin?: () => void;
}

export const AppShell: React.FC<AppShellProps> = ({ children, onSwitchToAdmin }) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#f8fafc] dark:bg-[#0b0f17] text-slate-800 dark:text-slate-100 flex flex-col font-sans transition-colors">
      <Header 
        onSwitchToAdmin={onSwitchToAdmin} 
        onOpenSettings={() => setIsSettingsOpen(true)} 
      />
      <div className="flex flex-1 h-[calc(100vh-4rem-1.75rem)] overflow-hidden">
        <Sidebar 
          onOpenSettings={() => setIsSettingsOpen(true)} 
        />
        <main className="flex-1 h-full overflow-hidden p-0 bg-[#f8fafc] dark:bg-[#0b0f17]">
          {children}
        </main>
      </div>
      <Footer />

      {/* Interactive Settings Modal Dialog */}
      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)} 
      />
    </div>
  );
};


