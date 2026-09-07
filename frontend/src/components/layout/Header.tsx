import React, { useState, useRef, useEffect } from 'react';
import { Bell, ChevronDown, LogOut, LayoutDashboard } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export interface HeaderProps {
  onSwitchToAdmin?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onSwitchToAdmin }) => {
  const { user, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : 'OP';

  const roleLabel = user?.role === 'admin' ? 'System Administrator' : 'Operations Engineer';

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-16 bg-white border-b border-slate-200 z-50 flex items-center justify-between px-6 shrink-0 shadow-xs">
      
      {/* Left: ONGC MRPL Logo & Branding */}
      <div className="flex items-center gap-3">
        {/* MRPL Green Emblem Icon */}
        <div className="w-9 h-9 rounded-full bg-[#1b4332] text-white flex items-center justify-center shadow-sm border border-emerald-800/40">
          <span className="font-black text-xs">MRPL</span>
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-extrabold text-slate-800 text-sm tracking-wide font-sans">
              <span className="font-black">MRPL</span> Sovereign AI Workbench
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 hidden md:inline">
              Ask. Analyze. Get Trusted Answers.
            </span>
          </div>
        </div>
      </div>

      {/* Center: AIR-GAPPED Security Pill */}
      <div className="hidden lg:flex flex-col items-center">
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-2xs">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="font-extrabold text-xs tracking-wider">AIR-GAPPED</span>
        </div>
        <span className="text-[10px] text-slate-400 font-sans mt-0.5">
          Secure • Private • MRPL
        </span>
      </div>

      {/* Right: Notifications & User Profile */}
      <div className="flex items-center gap-4">
        {/* Notification Bell with red count badge 3 */}
        <button className="relative p-2 rounded-full hover:bg-slate-100 text-slate-600 transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center border border-white">
            5
          </span>
        </button>

        {/* User Profile Component with Dropdown */}
        <div className="relative flex items-center gap-2" ref={dropdownRef}>
          {onSwitchToAdmin && (
            <button
              onClick={onSwitchToAdmin}
              className="hidden md:flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-white bg-[#1b4332] hover:bg-[#2d6a4f] rounded-lg transition-colors shadow-xs"
            >
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span>Admin Panel</span>
            </button>
          )}

          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-3 pl-3 border-l border-slate-200 hover:bg-slate-50 rounded-lg px-2 py-1 transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs shadow-sm">
              {initials}
            </div>
            <div className="text-left hidden sm:block">
              <div className="text-xs font-extrabold text-slate-800 leading-tight">{user?.username || 'operator'}</div>
              <div className="text-[10px] text-slate-500 leading-tight font-medium">{roleLabel}</div>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 text-slate-400 hidden sm:block transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
          </button>

          {/* Dropdown Menu */}
          {showDropdown && (
            <div className="absolute right-0 top-full mt-2 w-48 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50">
              <div className="px-3 py-2 border-b border-slate-100">
                <div className="text-xs font-bold text-slate-800">{user?.username}</div>
                <div className="text-[10px] text-slate-500 capitalize">{user?.role} account</div>
              </div>

              {onSwitchToAdmin && (
                <button
                  onClick={() => {
                    setShowDropdown(false);
                    onSwitchToAdmin();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-emerald-800 hover:bg-emerald-50 transition-colors"
                >
                  <LayoutDashboard className="w-3.5 h-3.5" />
                  Admin Panel
                </button>
              )}

              <button
                onClick={() => {
                  setShowDropdown(false);
                  logout();
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-rose-600 hover:bg-rose-50 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>

    </header>
  );
};
