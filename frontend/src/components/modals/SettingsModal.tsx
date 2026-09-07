import React from 'react';
import { X, Sun, Moon, Shield, Sparkles, Check } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';


interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { theme, setTheme } = useTheme();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      
      {/* Modal Container */}
      <div 
        className="w-full max-w-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden font-sans transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
          <div>
            <h3 className="text-base font-extrabold text-slate-800 dark:text-slate-100">
              Workbench Settings
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Customize your workspace theme and model preferences
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          
          {/* Section: Appearance / Theme */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Appearance & Theme</span>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              
              {/* Light Mode Option Card */}
              <button
                onClick={() => setTheme('light')}
                className={`p-4 rounded-xl border text-left flex flex-col justify-between transition-all cursor-pointer ${
                  theme === 'light'
                    ? 'border-emerald-600 dark:border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/20 ring-2 ring-emerald-500/20'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-3">
                  <div className="p-2 rounded-lg bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400">
                    <Sun className="w-5 h-5" />
                  </div>
                  {theme === 'light' && (
                    <div className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center">
                      <Check className="w-3.5 h-3.5" />
                    </div>
                  )}
                </div>
                <div>
                  <h4 className="font-extrabold text-xs text-slate-800 dark:text-slate-200">Light Mode</h4>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Clean, bright workspace interface</p>
                </div>
              </button>

              {/* Dark Mode Option Card */}
              <button
                onClick={() => setTheme('dark')}
                className={`p-4 rounded-xl border text-left flex flex-col justify-between transition-all cursor-pointer ${
                  theme === 'dark'
                    ? 'border-emerald-600 dark:border-emerald-500 bg-emerald-50/40 dark:bg-emerald-950/20 ring-2 ring-emerald-500/20'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-3">
                  <div className="p-2 rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
                    <Moon className="w-5 h-5" />
                  </div>
                  {theme === 'dark' && (
                    <div className="w-5 h-5 rounded-full bg-emerald-600 text-white flex items-center justify-center">
                      <Check className="w-3.5 h-3.5" />
                    </div>
                  )}
                </div>
                <div>
                  <h4 className="font-extrabold text-xs text-slate-800 dark:text-slate-200">Dark Mode</h4>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Sleek dark slate theme for low light</p>
                </div>
              </button>

            </div>
          </div>

          <hr className="border-slate-100 dark:border-slate-800" />

          {/* Section: Air-Gapped Security Info */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
              <Shield className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Air-Gapped Sovereign AI Status</span>
            </div>

            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-200 dark:border-slate-800 space-y-2 text-xs text-slate-600 dark:text-slate-300">
              <div className="flex justify-between items-center">
                <span className="font-medium">Primary Inference Model:</span>
                <span className="font-mono text-emerald-700 dark:text-emerald-400 font-bold bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">
                  Qwen2.5-VL-7B (vLLM GPU)
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-medium">Vector Knowledge Base:</span>
                <span className="font-mono text-slate-700 dark:text-slate-300 font-semibold">ChromaDB (Local RAG)</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-medium">Network Environment:</span>
                <span className="font-mono text-emerald-700 dark:text-emerald-400 font-bold">100% Air-Gapped / Isolated</span>
              </div>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-slate-50 dark:bg-slate-900/80 border-t border-slate-100 dark:border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-[#1b4332] hover:bg-[#2d6a4f] text-white text-xs font-bold rounded-xl transition-colors cursor-pointer shadow-xs"
          >
            Done
          </button>
        </div>

      </div>
    </div>
  );
};
