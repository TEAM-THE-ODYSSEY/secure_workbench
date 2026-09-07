import React, { useState, useEffect } from 'react';
import { UserPlus, Search, Trash2, X, UserCheck } from 'lucide-react';

export interface UserRecord {
  username: string;
  uid: string;
  fullName: string;
  unit: string;
  subUnit: string;
  role: string;
  createdDate: string;
  status: 'Active' | 'Inactive';
}

export const UsersView: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('');

  // New user form state
  const [newUsername, setNewUsername] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newUnit, setNewUnit] = useState('Refinery Operations');
  const [newRole, setNewRole] = useState('Operations Engineer');

  const [usersList, setUsersList] = useState<UserRecord[]>([
    {
      username: 'admin_kamat',
      uid: 'MRPL-SEC-001',
      fullName: 'Suresh Kamat',
      unit: 'Refinery Automation & IT',
      subUnit: 'Central Control Building',
      role: 'Sovereign Admin',
      createdDate: '2024-01-12',
      status: 'Active',
    },
    {
      username: 'eng_nayak',
      uid: 'MRPL-ENG-044',
      fullName: 'Pooja Nayak',
      unit: 'Process Engineering (CDU-3)',
      subUnit: 'Primary Distillation Unit',
      role: 'Lead Process Engineer',
      createdDate: '2024-02-04',
      status: 'Active',
    },
    {
      username: 'proc_bhat',
      uid: 'MRPL-ENG-089',
      fullName: 'Ganesh Bhat',
      unit: 'FCC Complex Operations',
      subUnit: 'Fluid Catalytic Cracker Block',
      role: 'Shift DCS Operator',
      createdDate: '2024-02-19',
      status: 'Active',
    },
    {
      username: 'field_dias',
      uid: 'MRPL-OPS-112',
      fullName: 'Rohan Dias',
      unit: 'Safety & Compliance Audit',
      subUnit: 'Environmental & Process Safety',
      role: 'Safety & Compliance Auditor',
      createdDate: '2024-03-02',
      status: 'Inactive',
    },
  ]);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('mrpl_token');
      const res = await fetch('/api/v1/admin/users', {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          const mapped: UserRecord[] = data.map((u: any) => ({
            username: u.email || u.employee_id || u.name.toLowerCase().replace(' ', '_'),
            uid: u.employee_id || u.id,
            fullName: u.name || 'MRPL Operator',
            unit: u.department || 'Refinery Operations',
            subUnit: 'Central Control',
            role: u.role || 'Operations Engineer',
            createdDate: u.created_at ? u.created_at.substring(0, 10) : '2024-01-01',
            status: u.is_active ? 'Active' : 'Inactive',
          }));
          setUsersList(mapped);
        }
      }
    } catch (err) {
      console.error('Failed to fetch admin users:', err);
    }
  };

  const handleAddUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newFullName.trim()) return;

    setUsersList((prev) => [
      {
        username: newUsername.trim(),
        uid: `MRPL-USER-${Math.floor(100 + Math.random() * 900)}`,
        fullName: newFullName.trim(),
        unit: newUnit,
        subUnit: 'Process Control',
        role: newRole,
        createdDate: new Date().toISOString().split('T')[0],
        status: 'Active',
      },
      ...prev,
    ]);

    fetch('/api/v1/admin/audit-events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'USER_CREATED',
        actor: 'operator / Admin',
        category: 'USER_MANAGEMENT',
        details: `Created new operator '${newUsername}' (${newFullName}) in '${newUnit}' with role '${newRole}'`,
        status: 'SUCCESS'
      }),
    }).catch(() => {});

    setNewUsername('');
    setNewFullName('');
    setIsModalOpen(false);
  };

  const handleDeleteUser = (username: string) => {
    if (window.confirm(`Remove access for operator "${username}" from the sovereign directory?`)) {
      setUsersList((prev) => prev.filter((u) => u.username !== username));

      fetch('/api/v1/admin/audit-events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'ACCESS_REVOKED',
          actor: 'operator / Admin',
          category: 'USER_MANAGEMENT',
          details: `Revoked sovereign directory access permissions for operator '${username}'`,
          status: 'SUCCESS'
        }),
      }).catch(() => {});
    }
  };

  const filteredUsers = usersList.filter((u) => {
    const matchesSearch =
      u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.fullName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.unit.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRole = roleFilter ? u.role === roleFilter : true;
    return matchesSearch && matchesRole;
  });

  return (
    <div className="space-y-6 font-sans">
      
      {/* Title & Action Header Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <span>User Directory & Access Control</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Manage authorized refinery personnel, access roles, and air-gapped security permissions.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-[#1b4332] hover:bg-[#2d6a4f] text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-xs flex items-center gap-2 transition-all cursor-pointer shrink-0"
        >
          <UserPlus className="w-4 h-4" />
          <span>Add New Operator</span>
        </button>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400 dark:text-slate-500 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by operator name, username, or department..."
            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-emerald-600 transition-colors shadow-2xs"
          />
        </div>

        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="w-full sm:w-48 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-xs px-3.5 py-2.5 rounded-xl focus:outline-none shadow-2xs"
        >
          <option value="">All Access Roles</option>
          <option value="Sovereign Admin">Sovereign Admin</option>
          <option value="Lead Process Engineer">Lead Process Engineer</option>
          <option value="Shift DCS Operator">Shift DCS Operator</option>
          <option value="Safety & Compliance Auditor">Safety Auditor</option>
        </select>
      </div>

      {/* Users Table Card */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse font-sans">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-extrabold uppercase text-[10px] tracking-wider">
                <th className="px-5 py-3.5">Operator</th>
                <th className="px-5 py-3.5">UID</th>
                <th className="px-5 py-3.5">Department / Unit</th>
                <th className="px-5 py-3.5">Role</th>
                <th className="px-5 py-3.5">Created Date</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300 font-medium">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-slate-400 dark:text-slate-500 text-xs">
                    No operators match your search query.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <tr key={u.username} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-900 dark:bg-emerald-950 text-white dark:text-emerald-300 font-bold text-xs flex items-center justify-center shadow-2xs">
                          {u.fullName.slice(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-bold text-slate-800 dark:text-slate-100">{u.fullName}</p>
                          <p className="text-[10px] text-slate-400 font-mono">@{u.username}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                      {u.uid}
                    </td>
                    <td className="px-5 py-4">
                      <p className="font-semibold text-slate-800 dark:text-slate-200">{u.unit}</p>
                      <p className="text-[10px] text-slate-400">{u.subUnit}</p>
                    </td>
                    <td className="px-5 py-4">
                      <span className="font-bold text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 px-2.5 py-1 rounded-md border border-emerald-200 dark:border-emerald-800 text-[10px]">
                        {u.role}
                      </span>
                    </td>
                    <td className="px-5 py-4 font-mono text-slate-400 text-[11px]">
                      {u.createdDate}
                    </td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        u.status === 'Active'
                          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800'
                          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${u.status === 'Active' ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                        {u.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <button
                        onClick={() => handleDeleteUser(u.username)}
                        title="Delete Operator"
                        className="p-1.5 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition-colors cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Operator Modal Dialog */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden font-sans">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
              <h3 className="text-sm font-extrabold text-slate-800 dark:text-slate-100">
                Register Authorized Operator
              </h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddUser} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  placeholder="e.g. Rajesh Sharma"
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Username
                </label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="e.g. operator_sharma"
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Department / Unit
                </label>
                <input
                  type="text"
                  value={newUnit}
                  onChange={(e) => setNewUnit(e.target.value)}
                  placeholder="e.g. CDU-3 Operations"
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1">
                  Access Role
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none"
                >
                  <option value="Operations Engineer">Operations Engineer</option>
                  <option value="Lead Process Engineer">Lead Process Engineer</option>
                  <option value="Shift DCS Operator">Shift DCS Operator</option>
                  <option value="Safety & Compliance Auditor">Safety Auditor</option>
                  <option value="Sovereign Admin">Sovereign Admin</option>
                </select>
              </div>

              <div className="pt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-[#1b4332] hover:bg-[#2d6a4f] text-white text-xs font-bold rounded-lg shadow-xs"
                >
                  Save Operator
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
