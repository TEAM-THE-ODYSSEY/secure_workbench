import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  Paperclip,
  ThumbsUp,
  ThumbsDown,
  Copy,
  FileText,
  CheckCircle2,
  FileCheck,
  ArrowRight,
  ListOrdered,
  MessageCircle,
  Sparkles,
  HelpCircle,
  CornerDownRight,
} from 'lucide-react';
import { useSession } from '../../context/SessionContext';
import { ReasoningFlow } from '../../components/chat/ReasoningFlow';
import { FormattedMessageResponse } from '../../components/chat/FormattedMessageResponse';
import { ExportReportModal } from '../../components/modals/ExportReportModal';

export const AiAssistantView: React.FC = () => {
  const { activeSession, sendMessage, isProcessing, reasoningSteps } = useSession();
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<{ name: string; size: string } | undefined>(undefined);
  const actualFileRef = useRef<File | null>(null);

  const [activeSummaries, setActiveSummaries] = useState<Record<string, boolean>>({});
  const [activeFollowups, setActiveFollowups] = useState<Record<string, boolean>>({});

  const [exportModalConfig, setExportModalConfig] = useState<{
    isOpen: boolean;
    mode: 'report' | 'summary';
    text: string;
    sources?: any[];
  }>({
    isOpen: false,
    mode: 'report',
    text: '',
    sources: [],
  });

  const generateInlineSummary = (text: string) => {
    const lines = text
      .split('\n')
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    const bulletPoints: string[] = [];
    for (const l of lines) {
      if (l.startsWith('#')) continue;
      if (l.startsWith('- ') || l.startsWith('* ') || /^\d+\./.test(l)) {
        const clean = l.replace(/^[-*\d.]+\s*/, '').replace(/\*\*/g, '');
        if (clean.length > 8) bulletPoints.push(clean);
      } else if (l.includes(':') && l.length > 15) {
        const clean = l.replace(/\*\*/g, '');
        bulletPoints.push(clean);
      }
    }

    return bulletPoints.length > 0 ? bulletPoints.slice(0, 6) : lines.slice(0, 4);
  };

  const generateFollowupQuestions = (text: string): string[] => {
    const tLower = text.toLowerCase();
    const questions: string[] = [];

    if (tLower.includes('p-101a') || tLower.includes('pump') || tLower.includes('cdu')) {
      questions.push('What are the SOP steps to switch over from P-101A to standby P-101B?');
      questions.push('What is the maximum allowable vibration and operating temperature for P-101A?');
      questions.push('Show safety interlock trip logic for XV-101 emergency shutdown.');
    } else if (tLower.includes('diagram') || tLower.includes('pipeline') || tLower.includes('p&id')) {
      questions.push('Detail the suction header line 12"-CR-101 specifications.');
      questions.push('What safety valves and flow transmitters monitor this line?');
      questions.push('Explain the minimum flow bypass loop to the surge vessel.');
    } else if (tLower.includes('health') || tLower.includes('safety') || tLower.includes('oisd')) {
      questions.push('Summarize OISD guidelines and H2S monitoring regulations.');
      questions.push('What SCBA compliance standards apply during maintenance?');
      questions.push('What are the National Safety Council Apex Safety Award criteria?');
    } else {
      questions.push('Provide specific operational SOP guidelines for this topic.');
      questions.push('What safety precautions and interlocks apply here?');
      questions.push('List relevant maintenance inspection schedules.');
    }

    return questions;
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messages = activeSession?.messages || [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!prompt.trim() || isLoading) return;

    const userText = prompt.trim();
    const fileToAttach = selectedFile;

    setPrompt('');
    setSelectedFile(undefined);
    setIsLoading(true);

    try {
      await sendMessage(userText, fileToAttach, actualFileRef.current || undefined);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePillClick = (suggestion: string) => {
    setPrompt(suggestion);
  };


  return (
    <div className="h-full flex flex-col justify-between overflow-hidden bg-[#f8fafc] dark:bg-[#0b0f17] p-4 md:p-6 font-sans transition-colors">
      
      {/* Scrollable Center Feed */}
      <div className="flex-1 overflow-y-auto max-w-5xl w-full mx-auto space-y-6 pr-2">
        
        {/* Welcome Header (Always shown when 0 messages or at top of new conversation) */}
        {messages.length === 0 && (
          <div className="text-center pt-8 pb-4 space-y-2">
            <h2 className="text-3xl font-extrabold text-slate-800 dark:text-slate-100 tracking-tight">
              Good evening, <span className="text-[#166534] dark:text-emerald-400">operator</span>
            </h2>
            <p className="text-lg font-bold text-slate-700 dark:text-slate-300">
              How can I help you today?
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
              Ask about equipment, SOPs, P&IDs, maintenance, incidents or any refinery knowledge.
            </p>

            {/* Prompt Suggestions Pills Row */}
            <div className="flex items-center justify-center gap-2 flex-wrap pt-4">
              <button
                onClick={() => handlePillClick('Why did P-101A fail?')}
                className="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs px-4 py-2 rounded-full shadow-2xs cursor-pointer transition-colors font-medium"
              >
                Why did P-101A fail?
              </button>
              <button
                onClick={() => handlePillClick('Plant shutdown procedure')}
                className="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs px-4 py-2 rounded-full shadow-2xs cursor-pointer transition-colors font-medium"
              >
                Plant shutdown procedure
              </button>
              <button
                onClick={() => handlePillClick('What is downstream of P-101A?')}
                className="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs px-4 py-2 rounded-full shadow-2xs cursor-pointer transition-colors font-medium"
              >
                What is downstream of P-101A?
              </button>
              <button
                onClick={() => handlePillClick('Show me safety guidelines')}
                className="bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs px-4 py-2 rounded-full shadow-2xs cursor-pointer transition-colors font-medium"
              >
                Show me safety guidelines
              </button>
            </div>
          </div>
        )}

        {/* Message Stream */}
        <div className="space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className="space-y-3">
              
              {/* USER BUBBLE */}
              {msg.sender === 'user' ? (
                <div className="flex justify-end items-start gap-3">
                  <div className="bg-[#e8f5e9] dark:bg-emerald-950/70 border border-[#c8e6c9] dark:border-emerald-800/80 text-slate-900 dark:text-emerald-100 text-xs p-4 rounded-2xl max-w-xl shadow-2xs space-y-2">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-semibold text-slate-900 dark:text-emerald-100 leading-relaxed">{msg.text}</p>
                      <span className="text-[10px] font-mono text-slate-400 dark:text-emerald-300/60 shrink-0">{msg.timestamp}</span>
                    </div>

                    {/* Attached File Card */}
                    {msg.attachedFile && (
                      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-2.5 flex items-center gap-3 shadow-2xs max-w-xs">
                        <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-slate-800 dark:text-slate-200 text-xs truncate">{msg.attachedFile.name}</p>
                          <p className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">{msg.attachedFile.size}</p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* User Avatar Circle */}
                  <div className="w-7 h-7 rounded-full bg-[#1b4332] text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-2xs">
                    OP
                  </div>
                </div>
              ) : (

                /* ASSISTANT RESPONSE CARD */
                <div className="flex items-start gap-3">
                  {/* ONGC MRPL Logo Avatar */}
                  <div className="w-8 h-8 rounded-full bg-[#1b4332] text-white flex items-center justify-center font-bold text-[10px] shrink-0 shadow-xs border border-emerald-800/40 mt-0.5">
                    <div className="text-center leading-none">
                      <span className="block text-[6px] tracking-tighter opacity-80">ONGC</span>
                      <span className="block font-black text-[9px]">MRPL</span>
                    </div>
                  </div>

                  {/* Pure White / Dark Container Card */}
                  <div className="flex-1 bg-white dark:bg-[#151c28] border border-slate-200 dark:border-slate-800 rounded-2xl p-5 space-y-4 shadow-xs text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                    
                    {/* Top Row: Timestamp & Feedback Icons */}
                    <div className="flex items-center justify-between text-xs border-b border-slate-100 dark:border-slate-800/80 pb-2">
                      <span className="font-mono text-slate-400 dark:text-slate-500 text-[11px]">{msg.timestamp}</span>
                      <div className="flex items-center gap-3 text-slate-400 dark:text-slate-500">
                        <button className="hover:text-slate-700 dark:hover:text-slate-200 transition-colors"><ThumbsUp className="w-3.5 h-3.5" /></button>
                        <button className="hover:text-slate-700 dark:hover:text-slate-200 transition-colors"><ThumbsDown className="w-3.5 h-3.5" /></button>
                        <button className="hover:text-slate-700 dark:hover:text-slate-200 transition-colors"><Copy className="w-3.5 h-3.5" /></button>
                      </div>
                    </div>

                    {/* Reasoning Steps */}
                    {msg.reasoningSteps && msg.reasoningSteps.length > 0 && (
                      <ReasoningFlow 
                        steps={msg.reasoningSteps} 
                        isComplete={true} 
                        totalDuration={msg.reasoningDuration} 
                      />
                    )}

                    {/* Synthesized Response Text */}
                    <FormattedMessageResponse content={msg.text} />

                    {/* Findings list if present */}
                    {msg.findings && msg.findings.length > 0 && (
                      <div className="space-y-2 pt-1">
                        <h4 className="font-bold text-slate-800 dark:text-slate-100 text-xs">Key Findings</h4>
                        <div className="space-y-2">
                          {msg.findings.map((f) => (
                            <div key={f.id} className="flex items-start gap-3">
                              <div className="w-5 h-5 rounded bg-blue-600 text-white font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                                {f.id}
                              </div>
                              <p className="text-slate-800 dark:text-slate-200 font-medium pt-0.5">{f.text}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Numbered Green Steps List if present */}
                    {msg.steps && msg.steps.length > 0 && (
                      <div className="space-y-2 pl-0.5">
                        {msg.steps.map((stepText, idx) => (
                          <div key={idx} className="flex items-start gap-3">
                            <div className="w-5 h-5 rounded bg-[#2d6a4f] text-white font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                              {idx + 1}
                            </div>
                            <p className="text-slate-800 dark:text-slate-200 font-medium pt-0.5">{stepText}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Sources Section */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-100 text-xs">
                            <FileCheck className="w-4 h-4 text-emerald-700 dark:text-emerald-400" />
                            <span>Sources</span>
                          </div>
                          <button className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-semibold flex items-center gap-1">
                            <span>View all ({msg.sources.length})</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        {/* Source Cards Row */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          {msg.sources.map((src, sIdx) => (
                            <div key={sIdx} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-colors space-y-2">
                              <div className="flex items-start justify-between gap-2">
                                <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 shrink-0">
                                  <FileText className="w-4 h-4" />
                                </div>
                                <span
                                  className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                                    src.badgeType === 'uploaded'
                                      ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                                      : 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                                  }`}
                                >
                                  {src.badge}
                                </span>
                              </div>
                              <div>
                                <h5 className="font-bold text-slate-800 dark:text-slate-200 text-xs truncate">{src.title}</h5>
                                <p className="text-[10px] text-slate-400 dark:text-slate-500">{src.category}</p>
                                <p className="text-[10px] text-slate-400 dark:text-slate-500 font-mono mt-1">{src.meta}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Inline Executive Summary Box */}
                    {activeSummaries[msg.id] && (
                      <div className="mt-3 p-4 bg-emerald-50/90 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 rounded-xl text-xs space-y-2 animate-in fade-in duration-200 shadow-xs">
                        <div className="flex items-center justify-between font-bold text-emerald-950 dark:text-emerald-300 text-xs pb-1 border-b border-emerald-200/60 dark:border-emerald-800/60">
                          <div className="flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                            <span>Executive Summary</span>
                          </div>
                          <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-normal">Extracted from above response</span>
                        </div>
                        <ul className="space-y-1.5 text-slate-800 dark:text-slate-200 pl-1 pt-1">
                          {generateInlineSummary(msg.text).map((pt, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-emerald-600 dark:text-emerald-400 font-bold shrink-0">•</span>
                              <span className="leading-snug">{pt}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Action Buttons Row */}
                    <div className="flex items-center gap-2.5 pt-2 flex-wrap">
                      <button
                        onClick={async () => {
                          try {
                            const token = localStorage.getItem('token');
                            await fetch('/api/v1/workspaces/notes', {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json',
                                ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                              },
                              body: JSON.stringify({
                                title: msg.text.slice(0, 30) + '...',
                                content: msg.text,
                                citations: msg.sources || []
                              })
                            });
                            alert('Note saved to active Workspace!');
                          } catch (err) {
                            console.error('Save note error', err);
                          }
                        }}
                        className="bg-emerald-50 dark:bg-emerald-950/60 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors cursor-pointer"
                      >
                        <FileCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                        <span>Save as Note</span>
                      </button>

                      <button
                        onClick={() =>
                          setExportModalConfig({
                            isOpen: true,
                            mode: 'report',
                            text: msg.text,
                            sources: msg.sources || [],
                          })
                        }
                        className="bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors cursor-pointer"
                      >
                        <FileText className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                        <span>Generate Report</span>
                      </button>

                      <button
                        onClick={() => {
                          setActiveSummaries((prev) => ({
                            ...prev,
                            [msg.id]: !prev[msg.id],
                          }));
                        }}
                        className={`text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors cursor-pointer border ${
                          activeSummaries[msg.id]
                            ? 'bg-emerald-100 dark:bg-emerald-900/80 border-emerald-300 dark:border-emerald-700 text-emerald-900 dark:text-emerald-200'
                            : 'bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        <ListOrdered className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                        <span>{activeSummaries[msg.id] ? 'Hide Summary' : 'Summarize'}</span>
                      </button>

                      <button
                        onClick={() => {
                          setActiveFollowups((prev) => ({
                            ...prev,
                            [msg.id]: !prev[msg.id],
                          }));
                        }}
                        className={`text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors cursor-pointer border ${
                          activeFollowups[msg.id]
                            ? 'bg-[#1b4332] text-white border-[#1b4332]'
                            : 'bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        <MessageCircle className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                        <span>{activeFollowups[msg.id] ? 'Hide Follow-ups' : 'Ask Follow-up'}</span>
                      </button>
                    </div>

                    {/* Interactive Follow-up Suggestions Card */}
                    {activeFollowups[msg.id] && (
                      <div className="mt-3 p-3 bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/80 rounded-xl text-xs space-y-2 animate-in fade-in duration-200 shadow-xs">
                        <div className="flex items-center gap-1.5 font-bold text-blue-950 dark:text-blue-300 text-xs pb-1 border-b border-blue-200/60 dark:border-blue-800/60">
                          <HelpCircle className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                          <span>Suggested Follow-up Questions (Click to Ask)</span>
                        </div>
                        <div className="flex flex-col gap-1.5 pt-1">
                          {generateFollowupQuestions(msg.text).map((q, qIdx) => (
                            <button
                              key={qIdx}
                              type="button"
                              onClick={() => {
                                setPrompt(q);
                                sendMessage(q);
                              }}
                              className="text-left py-1.5 px-3 bg-white dark:bg-slate-900 border border-blue-200 dark:border-blue-800/80 hover:bg-blue-100/60 dark:hover:bg-blue-900/60 rounded-lg text-slate-800 dark:text-slate-200 font-medium transition-colors flex items-center justify-between group cursor-pointer"
                            >
                              <span className="flex items-center gap-2">
                                <CornerDownRight className="w-3 h-3 text-blue-500 shrink-0" />
                                <span>{q}</span>
                              </span>
                              <ArrowRight className="w-3.5 h-3.5 text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                  </div>
                </div>

              )}
            </div>
          ))}

          {isProcessing && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-[#1b4332] text-white flex items-center justify-center font-bold text-[10px] shrink-0 shadow-xs border border-emerald-800/40 mt-0.5">
                <div className="text-center leading-none">
                  <span className="block text-[6px] tracking-tighter opacity-80">ONGC</span>
                  <span className="block font-black text-[9px]">MRPL</span>
                </div>
              </div>
              <div className="flex-1 max-w-2xl">
                <ReasoningFlow steps={reasoningSteps} isComplete={false} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

      </div>

      {/* Floating Bottom Input Capsule Bar */}
      <div className="max-w-5xl w-full mx-auto pt-3 shrink-0 space-y-1">
        {selectedFile && (
          <div className="flex items-center gap-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1 text-xs text-slate-700 dark:text-slate-300 w-fit shadow-2xs">
            <FileText className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span className="font-semibold">{selectedFile.name}</span>
            <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">({selectedFile.size})</span>
            <button onClick={() => {
              setSelectedFile(undefined);
              actualFileRef.current = null;
            }} className="ml-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 font-bold">×</button>
          </div>
        )}

        <form
          onSubmit={handleSendMessage}
          className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-2xl p-3 shadow-md flex items-center gap-3 transition-colors"
        >
          <label className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer shrink-0">
            <Paperclip className="w-4 h-4" />
            <input
              type="file"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  actualFileRef.current = file;
                  setSelectedFile({
                    name: file.name,
                    size: `${(file.size / 1024).toFixed(1)} KB`,
                  });
                }
              }}
            />
          </label>

          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask anything about MRPL or your files..."
            className="flex-1 text-xs text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none bg-transparent"
          />

          {isLoading || isProcessing ? (
            <button
              type="button"
              onClick={async () => {
                setIsLoading(false);
                try {
                  const token = localStorage.getItem('token');
                  await fetch(`/api/v1/tasks/${activeSession?.id}/cancel`, {
                    method: 'POST',
                    headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
                  });
                } catch (e) {
                  console.error('Cancel task error', e);
                }
              }}
              className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-3.5 rounded-xl flex items-center gap-1.5 text-xs shadow-sm transition-all cursor-pointer"
            >
              <span className="w-2 h-2 rounded-xs bg-white animate-pulse"></span>
              <span>Stop</span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={!prompt.trim()}
              className="bg-[#1b4332] hover:bg-[#2d6a4f] disabled:opacity-40 text-white font-bold py-2 px-3.5 rounded-xl flex items-center gap-1.5 text-xs shadow-sm transition-all cursor-pointer shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          )}
        </form>


        {/* Subtext Disclaimer */}
        <p className="text-[11px] text-slate-400 dark:text-slate-500 font-sans text-center mt-2 flex items-center justify-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
          <span>Responses are generated from trusted MRPL knowledge sources.</span>
        </p>
      </div>

      <ExportReportModal
        isOpen={exportModalConfig.isOpen}
        onClose={() => setExportModalConfig((prev) => ({ ...prev, isOpen: false }))}
        initialMode={exportModalConfig.mode}
        messageText={exportModalConfig.text}
        sources={exportModalConfig.sources}
      />
    </div>
  );
};

