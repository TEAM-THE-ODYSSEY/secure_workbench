import React, { useRef, useEffect, useState } from 'react';
import {
  Send,
  Paperclip,
  ThumbsUp,
  ThumbsDown,
  Copy,
  FileText,
  ChevronDown,
  CheckCircle2,
  FileCheck,
  ArrowRight,
  ListOrdered,
  MessageCircle,
} from 'lucide-react';
import { useSession } from '../../context/SessionContext';
import { ReasoningFlow } from '../../components/chat/ReasoningFlow';

export const AiAssistantView: React.FC = () => {
  const { activeSession, sendMessage, isProcessing, reasoningSteps } = useSession();
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<{ name: string; size: string } | undefined>(undefined);
  const actualFileRef = useRef<File | null>(null);

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      actualFileRef.current = file;
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
      setSelectedFile({ name: file.name, size: `${sizeMb} MB` });
    }
  };

  return (
    <div className="h-full flex flex-col justify-between overflow-hidden bg-[#f8fafc] p-4 md:p-6 font-sans">
      
      {/* Scrollable Center Feed */}
      <div className="flex-1 overflow-y-auto max-w-5xl w-full mx-auto space-y-6 pr-2">
        
        {/* Welcome Header (Always shown when 0 messages or at top of new conversation) */}
        {messages.length === 0 && (
          <div className="text-center pt-8 pb-4 space-y-2">
            <h2 className="text-3xl font-extrabold text-slate-800 tracking-tight">
              Good evening, <span className="text-[#166534]">operator</span>
            </h2>
            <p className="text-lg font-bold text-slate-700">
              How can I help you today?
            </p>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Ask about equipment, SOPs, P&IDs, maintenance, incidents or any refinery knowledge.
            </p>

            {/* Prompt Suggestions Pills Row */}
            <div className="flex items-center justify-center gap-2 flex-wrap pt-4">
              <button
                onClick={() => handlePillClick('Why did P-101A fail?')}
                className="bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs px-4 py-2 rounded-full shadow-2xs cursor-pointer transition-colors font-medium"
              >
                Why did P-101A fail?
              </button>
              <button
                onClick={() => handlePillClick('Plant shutdown procedure')}
                className="bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs px-4 py-2 rounded-full shadow-2xs cursor-pointer transition-colors font-medium"
              >
                Plant shutdown procedure
              </button>
              <button
                onClick={() => handlePillClick('What is downstream of P-101A?')}
                className="bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs px-4 py-2 rounded-full shadow-2xs cursor-pointer transition-colors font-medium"
              >
                What is downstream of P-101A?
              </button>
              <button
                onClick={() => handlePillClick('Show me safety guidelines')}
                className="bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs px-4 py-2 rounded-full shadow-2xs cursor-pointer transition-colors font-medium"
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
                  <div className="bg-[#e8f5e9] border border-[#c8e6c9] text-slate-900 text-xs p-4 rounded-2xl max-w-xl shadow-2xs space-y-2">
                    <div className="flex items-center justify-between gap-4">
                      <p className="font-semibold text-slate-900 leading-relaxed">{msg.text}</p>
                      <span className="text-[10px] font-mono text-slate-400 shrink-0">{msg.timestamp}</span>
                    </div>

                    {/* Attached File Card */}
                    {msg.attachedFile && (
                      <div className="bg-white border border-slate-200 rounded-xl p-2.5 flex items-center gap-3 shadow-2xs max-w-xs">
                        <div className="p-2 rounded-lg bg-blue-50 text-blue-600 shrink-0">
                          <FileText className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-slate-800 text-xs truncate">{msg.attachedFile.name}</p>
                          <p className="text-[10px] text-slate-400 font-mono">{msg.attachedFile.size}</p>
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

                /* ASSISTANT RESPONSE CARD (EXACT SCREENSHOT UI) */
                <div className="flex items-start gap-3">
                  {/* ONGC MRPL Logo Avatar */}
                  <div className="w-8 h-8 rounded-full bg-[#1b4332] text-white flex items-center justify-center font-bold text-[10px] shrink-0 shadow-xs border border-emerald-800/40 mt-0.5">
                    <div className="text-center leading-none">
                      <span className="block text-[6px] tracking-tighter opacity-80">ONGC</span>
                      <span className="block font-black text-[9px]">MRPL</span>
                    </div>
                  </div>

                  {/* Pure White Response Container Card */}
                  <div className="flex-1 bg-white border border-slate-200 rounded-2xl p-5 space-y-4 shadow-xs text-xs leading-relaxed text-slate-700">
                    
                    {/* Top Row: Timestamp & Feedback Icons */}
                    <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                      <span className="font-mono text-slate-400 text-[11px]">{msg.timestamp}</span>
                      <div className="flex items-center gap-3 text-slate-400">
                        <button className="hover:text-slate-700 transition-colors"><ThumbsUp className="w-3.5 h-3.5" /></button>
                        <button className="hover:text-slate-700 transition-colors"><ThumbsDown className="w-3.5 h-3.5" /></button>
                        <button className="hover:text-slate-700 transition-colors"><Copy className="w-3.5 h-3.5" /></button>
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
                    <p className="text-slate-700 leading-relaxed font-sans">{msg.text}</p>

                    {/* Findings list if present */}
                    {msg.findings && msg.findings.length > 0 && (
                      <div className="space-y-2 pt-1">
                        <h4 className="font-bold text-slate-800 text-xs">Key Findings</h4>
                        <div className="space-y-2">
                          {msg.findings.map((f) => (
                            <div key={f.id} className="flex items-start gap-3">
                              <div className="w-5 h-5 rounded bg-blue-600 text-white font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                                {f.id}
                              </div>
                              <p className="text-slate-800 font-medium pt-0.5">{f.text}</p>
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
                            <p className="text-slate-800 font-medium pt-0.5">{stepText}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Sources Section */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="pt-3 border-t border-slate-100 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 font-bold text-slate-800 text-xs">
                            <FileCheck className="w-4 h-4 text-emerald-700" />
                            <span>Sources</span>
                          </div>
                          <button className="text-xs text-blue-600 hover:underline font-semibold flex items-center gap-1">
                            <span>View all ({msg.sources.length})</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        {/* Source Cards Row */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          {msg.sources.map((src, sIdx) => (
                            <div key={sIdx} className="p-3 rounded-xl bg-slate-50 border border-slate-200 hover:border-slate-300 transition-colors space-y-2">
                              <div className="flex items-start justify-between gap-2">
                                <div className="p-2 rounded-lg bg-blue-50 text-blue-600 shrink-0">
                                  <FileText className="w-4 h-4" />
                                </div>
                                <span
                                  className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                                    src.badgeType === 'uploaded'
                                      ? 'bg-blue-50 text-blue-600 border border-blue-200'
                                      : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  }`}
                                >
                                  {src.badge}
                                </span>
                              </div>
                              <div>
                                <h5 className="font-bold text-slate-800 text-xs truncate">{src.title}</h5>
                                <p className="text-[10px] text-slate-400">{src.category}</p>
                                <p className="text-[10px] text-slate-400 font-mono mt-1">{src.meta}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Action Buttons Row */}
                    <div className="flex items-center gap-2.5 pt-2 flex-wrap">
                      <button className="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors cursor-pointer">
                        <FileText className="w-3.5 h-3.5 text-slate-500" />
                        <span>Generate Report</span>
                      </button>

                      <button className="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors cursor-pointer">
                        <ListOrdered className="w-3.5 h-3.5 text-slate-500" />
                        <span>Summarize</span>
                      </button>

                      <button className="bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-colors cursor-pointer">
                        <MessageCircle className="w-3.5 h-3.5 text-slate-500" />
                        <span>Ask Follow-up</span>
                      </button>
                    </div>

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
          <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1 text-xs text-slate-700 w-fit shadow-2xs">
            <FileText className="w-3.5 h-3.5 text-blue-600" />
            <span className="font-semibold">{selectedFile.name}</span>
            <span className="text-[10px] text-slate-400 font-mono">({selectedFile.size})</span>
            <button onClick={() => {
              setSelectedFile(undefined);
              actualFileRef.current = null;
            }} className="ml-1 text-slate-400 hover:text-slate-700 font-bold">×</button>
          </div>
        )}

        <form
          onSubmit={handleSendMessage}
          className="bg-white border border-slate-300 rounded-2xl p-3 shadow-md flex items-center gap-3"
        >
          <label className="p-2 hover:bg-slate-100 rounded-full text-slate-500 hover:text-slate-800 transition-colors cursor-pointer shrink-0">
            <Paperclip className="w-4 h-4" />
            <input type="file" onChange={handleFileChange} className="hidden" />
          </label>

          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Type your message here..."
            className="flex-1 bg-transparent text-xs text-slate-800 placeholder-slate-400 focus:outline-none font-sans"
          />

          {/* Send Button Group with Green Square Arrow & Chevron Dropdown */}
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="submit"
              disabled={!prompt.trim() || isLoading}
              className="bg-[#1b4332] hover:bg-[#2d6a4f] disabled:opacity-40 text-white p-2 rounded-lg transition-colors shadow-2xs cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
            <button
              type="button"
              className="p-1.5 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-700 transition-colors"
            >
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>

        {/* Subtext Disclaimer */}
        <p className="text-[11px] text-slate-400 font-sans text-center mt-2 flex items-center justify-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />
          <span>Responses are generated from trusted internal knowledge sources.</span>
        </p>
      </div>

    </div>
  );
};
