import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught React Error caught by ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  private handleReload = () => {
    window.location.reload();
  };

  private toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-[400px] w-full flex items-center justify-center p-6 bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all">
          <div className="max-w-lg w-full bg-white dark:bg-slate-900 rounded-2xl p-6 sm:p-8 shadow-xl border border-slate-200/80 dark:border-slate-800/80 space-y-6">
            
            {/* Header Icon + Title */}
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-rose-100 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 flex items-center justify-center text-rose-600 dark:text-rose-400 shrink-0">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Something went wrong
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  An unexpected error occurred while rendering this section.
                </p>
              </div>
            </div>

            {/* Main Error Alert Box */}
            <div className="p-3.5 bg-rose-50/80 dark:bg-rose-950/30 border border-rose-200/70 dark:border-rose-900/50 rounded-xl text-xs font-mono text-rose-700 dark:text-rose-300 break-words leading-relaxed">
              {this.state.error?.message || 'Unknown application error'}
            </div>

            {/* Technical Stack Trace Collapse */}
            {this.state.errorInfo && (
              <div className="space-y-2">
                <button
                  onClick={this.toggleDetails}
                  className="flex items-center justify-between w-full text-xs font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 py-1 transition-colors"
                >
                  <span>Technical details</span>
                  {this.state.showDetails ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>
                {this.state.showDetails && (
                  <pre className="p-3 bg-slate-900 text-slate-200 dark:bg-slate-950 rounded-xl text-[11px] font-mono overflow-x-auto max-h-48 scrollbar-thin scrollbar-thumb-slate-700 leading-normal">
                    {this.state.error?.stack}
                    {'\n\nComponent Stack:'}
                    {this.state.errorInfo.componentStack}
                  </pre>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={this.handleReset}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-[#1b4332] hover:bg-[#2d6a4f] text-white text-xs font-semibold rounded-xl shadow-xs transition-all active:scale-[0.98]"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Try Again
              </button>
              <button
                onClick={this.handleReload}
                className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 transition-all active:scale-[0.98]"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
