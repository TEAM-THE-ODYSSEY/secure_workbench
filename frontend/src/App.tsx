import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { SessionProvider } from './context/SessionContext';
import { AppShell } from './components/layout/AppShell';
import { AiAssistantView } from './features/assistant/AiAssistantView';
import { LoginPage } from './features/auth/LoginPage';
import { AdminDashboard } from './features/admin/AdminDashboard';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Loader2 } from 'lucide-react';

const AppContent: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-[#f8fafc] dark:bg-[#0b0f17]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-[#1b4332] dark:text-emerald-400" />
          <span className="text-sm text-slate-500 dark:text-slate-400 font-medium">Initializing Workbench...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  // Admin role → Admin Dashboard with embedded Chat tab
  if (user?.role === 'admin') {
    return (
      <ErrorBoundary>
        <AdminDashboard />
      </ErrorBoundary>
    );
  }

  // User role → User Side AI Assistant Chat Interface
  return (
    <SessionProvider>
      <AppShell>
        <ErrorBoundary>
          <AiAssistantView />
        </ErrorBoundary>
      </AppShell>
    </SessionProvider>
  );
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;

