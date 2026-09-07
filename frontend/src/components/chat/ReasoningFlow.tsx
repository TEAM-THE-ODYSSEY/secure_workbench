import React, { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle2, Loader2, Circle } from 'lucide-react';
import type { ReasoningStep } from '../../types/session';

interface ReasoningFlowProps {
  steps: ReasoningStep[];
  isComplete: boolean;
  totalDuration?: number;
}

export const ReasoningFlow: React.FC<ReasoningFlowProps> = ({ steps, isComplete, totalDuration }) => {
  const [isExpanded, setIsExpanded] = useState(!isComplete);

  if (isComplete && !isExpanded) {
    return (
      <button
        onClick={() => setIsExpanded(true)}
        className="flex items-center gap-2 px-4 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs text-slate-700 transition-colors w-full sm:w-auto shadow-2xs font-medium cursor-pointer mb-2"
      >
        <span className="text-[#166534]">⚡</span>
        <span>Thought for {(totalDuration ? totalDuration / 1000 : 0).toFixed(1)}s</span>
        <ChevronRight className="w-3.5 h-3.5 ml-1 text-slate-400" />
      </button>
    );
  }

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden mb-2 transition-all duration-300">
      {isComplete && (
        <button
          onClick={() => setIsExpanded(false)}
          className="flex items-center justify-between w-full p-3 bg-white border-b border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <span className="text-[#166534]">⚡</span>
            <span>Thought for {(totalDuration ? totalDuration / 1000 : 0).toFixed(1)}s</span>
          </div>
          <ChevronDown className="w-4 h-4 text-slate-400" />
        </button>
      )}
      
      <div className="p-3 sm:p-4 space-y-3">
        {steps.map((step) => (
          <div
            key={step.id}
            className={`flex items-start gap-3 text-xs transition-opacity duration-300 ${
              step.status === 'pending' ? 'opacity-40' : 'opacity-100'
            }`}
          >
            <div className="flex-shrink-0 mt-0.5">
              {step.status === 'done' && (
                <CheckCircle2 className="w-4 h-4 text-[#166534]" />
              )}
              {step.status === 'active' && (
                <Loader2 className="w-4 h-4 text-[#166534] animate-spin" />
              )}
              {step.status === 'pending' && (
                <Circle className="w-4 h-4 text-slate-300" />
              )}
              {step.status === 'error' && (
                <Circle className="w-4 h-4 text-red-500 fill-red-500/20" />
              )}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                <span className="font-medium text-slate-800 truncate">
                  <span className="mr-2">{step.icon}</span>
                  {step.label}
                </span>
                {step.duration && step.status === 'done' && (
                  <span className="text-[10px] font-mono text-slate-400 shrink-0">
                    {step.duration}ms
                  </span>
                )}
              </div>
              {step.detail && step.status === 'active' && (
                <p className="text-[10px] text-slate-500 mt-1 truncate">{step.detail}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
