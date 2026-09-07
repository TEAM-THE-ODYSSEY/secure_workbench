import React, { useState } from 'react';
import { Plus, Search, MessageSquare, MoreHorizontal, HelpCircle, Settings, Trash2 } from 'lucide-react';
import { useSession } from '../../context/SessionContext';

export const Sidebar: React.FC = () => {
  const { sessions, activeSessionId, setActiveSessionId, createNewChat, deleteSession } = useSession();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  const filteredSessions = sessions.filter((s) =>
    s.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside className="w-72 bg-[#f8fafc] border-r border-slate-200 flex flex-col justify-between h-full shrink-0 overflow-hidden font-sans text-xs">
      
      {/* Scrollable Navigation & History Stream */}
      <div className="p-3.5 space-y-4 overflow-y-auto flex-1">
        
        {/* Top + New Chat Button */}
        <button
          onClick={createNewChat}
          className="w-full bg-[#1b4332] hover:bg-[#2d6a4f] text-white font-bold py-2.5 px-4 rounded-lg border border-emerald-900/30 flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
        </button>

        {/* Search Conversations Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full bg-white border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-600 transition-colors shadow-2xs"
          />
        </div>

        {/* Conversation Sessions List */}
        <div className="space-y-0.5">
          {filteredSessions.map((s) => {
            const isActive = activeSessionId === s.id;
            return (
              <div
                key={s.id}
                onClick={() => setActiveSessionId(s.id)}
                className={`w-full relative px-3 py-2 rounded-xl transition-all cursor-pointer flex items-center justify-between group ${
                  isActive
                    ? 'bg-slate-200/80 text-slate-900 font-bold shadow-2xs'
                    : 'text-slate-700 hover:bg-slate-200/50 hover:text-slate-900 font-medium'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-slate-800' : 'text-slate-500'}`} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs leading-snug">{s.title}</p>
                    <p className="text-[10px] font-mono text-slate-400 leading-tight">{s.time}</p>
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveMenuId(activeMenuId === s.id ? null : s.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-slate-900 transition-opacity"
                >
                  <MoreHorizontal className="w-3.5 h-3.5" />
                </button>

                {activeMenuId === s.id && (
                  <div className="absolute right-2 top-8 z-50 bg-white border border-slate-200 shadow-md rounded-lg p-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(s.id);
                        setActiveMenuId(null);
                      }}
                      className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-rose-600 hover:bg-rose-50 rounded font-medium w-full text-left"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Delete
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>

      </div>

      {/* Bottom Footer Links */}
      <div className="p-3.5 border-t border-slate-200 space-y-1 bg-slate-100/60">
        <button className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-slate-700 hover:bg-slate-200/60 transition-colors font-medium">
          <HelpCircle className="w-4 h-4 text-slate-500" />
          <span>Help & Support</span>
        </button>
        <button className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg text-slate-700 hover:bg-slate-200/60 transition-colors font-medium">
          <Settings className="w-4 h-4 text-slate-500" />
          <span>Settings</span>
        </button>
      </div>

      {/* Bottom Graphic Card */}
      <div className="p-3">
        <div className="relative rounded-xl overflow-hidden shadow-sm border border-slate-200 bg-gradient-to-br from-[#1b4332] to-[#0f2d21] p-4 text-white space-y-2">
          {/* Refinery Graphic Accent */}
          <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
          
          <div className="relative z-10 space-y-1">
            <h4 className="font-extrabold text-xs leading-tight tracking-wide text-white">
              Cleaner Energy <br /> Stronger Tomorrow
            </h4>
            <div className="flex items-center gap-1.5 pt-1">
              <div className="w-4 h-4 rounded bg-white text-[#1b4332] font-black text-[9px] flex items-center justify-center">
                M
              </div>
              <span className="text-[10px] font-extrabold tracking-widest text-emerald-200 uppercase">
                MRPL
              </span>
            </div>
          </div>
        </div>
      </div>

    </aside>
  );
};
