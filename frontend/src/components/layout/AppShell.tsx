import React from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { Footer } from './Footer';

export interface AppShellProps {
  children: React.ReactNode;
  onSwitchToAdmin?: () => void;
}

export const AppShell: React.FC<AppShellProps> = ({ children, onSwitchToAdmin }) => {
  return (
    <div className="h-screen w-screen overflow-hidden bg-[#f8fafc] text-slate-800 flex flex-col font-sans">
      <Header onSwitchToAdmin={onSwitchToAdmin} />
      <div className="flex flex-1 h-[calc(100vh-4rem-1.75rem)] overflow-hidden">
        <Sidebar />
        <main className="flex-1 h-full overflow-hidden p-0 bg-[#f8fafc]">
          {children}
        </main>
      </div>
      <Footer />
    </div>
  );
};
