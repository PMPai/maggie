'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { api } from '@/lib/api';
import { hasCategory, getUserCategory, categoryLabel, categoryColor } from '@/lib/roles';

const allNavItems = [
  { href: '/dashboard', label: '驾驶舱', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6', categories: [] },
  { href: '/projects', label: '项目管理', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4', categories: [] },
  { href: '/inbox', label: '文件收件箱', icon: 'M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12', categories: ['ADMIN', 'FINANCE', 'LEADER'] },
  { href: '/approvals', label: '审批中心', icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z', categories: ['ADMIN', 'FINANCE', 'LEADER'] },
  { href: '/my-applications', label: '我的请款', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01', categories: ['ADMIN', 'FINANCE', 'LEADER'] },
  { href: '/applications/new', label: '新建请款', icon: 'M12 4v16m8-8H4', categories: ['ADMIN', 'FINANCE', 'LEADER'] },
  { href: '/admin/users', label: '用户管理', icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z', categories: ['ADMIN'] },
  { href: '/admin/groups', label: '群组管理', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z', categories: ['ADMIN'] },
  { href: '/reports', label: '报表中心', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', categories: [] },
  { href: '/audit', label: '审计日志', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', categories: ['ADMIN', 'AUDITOR'] },
];

function filterNavItems(roles: string[]) {
  return allNavItems.filter(item => {
    if (item.categories.length === 0) return true;
    return item.categories.some(cat => hasCategory(roles, cat));
  });
}

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [showPwd, setShowPwd] = useState(false);
  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [pwdMsg, setPwdMsg] = useState('');
  const [pwdBusy, setPwdBusy] = useState(false);

  const changePwd = async () => {
    if (!newPwd) { setPwdMsg('请输入新密码'); return; }
    setPwdBusy(true); setPwdMsg('');
    try {
      await api.post('/auth/change-password', { old_password: oldPwd, new_password: newPwd });
      setPwdMsg('密码修改成功'); setOldPwd(''); setNewPwd('');
      setTimeout(() => { setShowPwd(false); setPwdMsg(''); }, 2000);
    } catch (e: any) { setPwdMsg(e?.message || '修改失败'); }
    finally { setPwdBusy(false); }
  };

  if (pathname === '/') return null;

  const navItems = user ? filterNavItems(user.roles) : allNavItems;
  const userCategory = user ? getUserCategory(user.roles) : null;

  return (
    <>
    <aside className="fixed left-0 top-0 bottom-0 w-60 bg-white border-r border-slate-200 flex flex-col z-30">
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-slate-200">
        <div className="w-8 h-8 rounded-lg bg-orange-500 flex items-center justify-center text-white font-bold text-sm">M</div>
        <span className="font-semibold text-slate-800 text-sm">Maggie 请款系统</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => {
          const active = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={active ? 'nav-link-active' : 'nav-link'}
            >
              <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
              </svg>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      {user && (
        <div className="px-3 py-3 border-t border-slate-200">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-medium text-xs">
              {user.display_name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-700 truncate">{user.display_name}</p>
              {userCategory && (
                <span className={`inline-block text-xs px-1.5 py-0.5 rounded ${categoryColor(userCategory)}`}>
                  {categoryLabel(userCategory)}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={() => setShowPwd(true)}
            className="nav-link w-full mt-1"
          >
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span>修改密码</span>
          </button>
          <button
            onClick={() => { logout(); window.location.href = '/'; }}
            className="nav-link w-full mt-1"
          >
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>退出登录</span>
          </button>
        </div>
      )}
      </aside>
      {showPwd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={() => setShowPwd(false)}>
          <div className="bg-white rounded-lg p-6 max-w-sm w-full" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-slate-800">修改密码</h3>
              <button onClick={() => setShowPwd(false)} className="text-slate-400">✕</button>
            </div>
            {pwdMsg && <p className={`text-sm mb-3 ${pwdMsg.includes('成功') ? 'text-green-600' : 'text-red-600'}`}>{pwdMsg}</p>}
            <div className="space-y-3">
              <input type="password" placeholder="旧密码" value={oldPwd} onChange={e => setOldPwd(e.target.value)} className="input-field text-sm w-full" />
              <input type="password" placeholder="新密码" value={newPwd} onChange={e => setNewPwd(e.target.value)} className="input-field text-sm w-full" />
              <button onClick={changePwd} disabled={pwdBusy} className="btn-primary w-full text-sm">{pwdBusy ? '修改中...' : '确认修改'}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { loading } = useAuth();
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  if (!mounted || pathname === '/') return <>{children}</>;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 ml-60 min-h-screen">
        {loading ? (
          <div className="flex items-center justify-center h-screen">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
          </div>
        ) : (
          <div className="p-6 max-w-7xl mx-auto">
            {children}
          </div>
        )}
      </main>
    </div>
  );
}