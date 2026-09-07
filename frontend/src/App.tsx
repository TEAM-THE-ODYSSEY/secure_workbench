import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SessionProvider } from './context/SessionContext';
import { AppShell } from './components/layout/AppShell';
import { AiAssistantView } from './features/assistant/AiAssistantView';
import { LoginPage } from './features/auth/LoginPage';
import { AdminDashboard } from './features/admin/AdminDashboard';
import { Loader2 } from 'lucide-react';

const AppContent: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const [adminViewMode, setAdminViewMode] = React.useState<'admin' | 'user'>('user');

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#f8fafc]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#1b4332]" />
          <span className="text-sm text-slate-500 font-medium">Initializing Workbench...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // Admin role → Admin Dashboard (with option to switch to User Chat View)
  if (user?.role === 'admin' && adminViewMode === 'admin') {
    return <AdminDashboard onSwitchToUser={() => setAdminViewMode('user')} />;
  }

  // User role or Admin in User mode → User Side AI Assistant Chat Interface
  return (
    <SessionProvider>
      <AppShell onSwitchToAdmin={user?.role === 'admin' ? () => setAdminViewMode('admin') : undefined}>
        <AiAssistantView />
      </AppShell>
    </SessionProvider>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
