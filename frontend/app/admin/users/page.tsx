'use client';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { PageHeader, Card, CardHeader, EmptyState } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { roleLabel, hasCategory, categoryLabel, categoryColor, type UserWithGroups, type GroupInfo } from '@/lib/roles';
import Link from 'next/link';

export default function AdminUsersPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<UserWithGroups[]>([]);
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showGroups, setShowGroups] = useState<UserWithGroups | null>(null);
  const [showResetPwd, setShowResetPwd] = useState<UserWithGroups | null>(null);
  const [confirmMsg, setConfirmMsg] = useState('');
  const [confirmAction, setConfirmAction] = useState<(() => void) | null>(null);

  const [formEmail, setFormEmail] = useState('');
  const [formName, setFormName] = useState('');
  const [formDept, setFormDept] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formGroupIds, setFormGroupIds] = useState<string[]>([]);
  const [formBusy, setFormBusy] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [editGroupIds, setEditGroupIds] = useState<string[]>([]);

  const loadData = () => {
    api.get<UserWithGroups[]>('/users').then(setUsers).catch(e => setError(e.message));
    api.get<GroupInfo[]>('/groups').then(setGroups).catch(() => {});
  };

  useEffect(() => {
    if (!authLoading && user) {
      if (!hasCategory(user.roles, 'ADMIN')) { router.replace('/dashboard'); return; }
      loadData();
      setLoading(false);
    }
  }, [user, authLoading]);

  useEffect(() => {
    if (loading) return;
  }, [users, groups, loading]);

  const handleCreate = async () => {
    setFormBusy(true);
    try {
      await api.post('/users', { email: formEmail, display_name: formName, department: formDept, password: formPassword, group_ids: formGroupIds });
      setShowCreate(false);
      setFormEmail(''); setFormName(''); setFormDept(''); setFormPassword(''); setFormGroupIds([]);
      loadData();
    } catch (e: any) { alert(e.message); }
    finally { setFormBusy(false); }
  };

  const handleResetPwd = async () => {
    if (!showResetPwd || !newPassword) return;
    try {
      await api.post(`/users/${showResetPwd.id}/reset-password`, { new_password: newPassword });
      setShowResetPwd(null);
      setNewPassword('');
      alert('密码已重置');
    } catch (e: any) { alert(e.message); }
  };

  const handleToggleStatus = (u: UserWithGroups) => {
    const newStatus = u.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    setConfirmMsg(`确定要${newStatus === 'ACTIVE' ? '启用' : '停用'}用户「${u.display_name}」吗？`);
    setConfirmAction(() => async () => {
      try { await api.put(`/users/${u.id}`, { status: newStatus }); loadData(); } catch (e: any) { alert(e.message); }
      setConfirmMsg(''); setConfirmAction(null);
    });
  };

  const openGroups = (u: UserWithGroups) => {
    setEditGroupIds(u.groups.map(g => g.id));
    setShowGroups(u);
  };

  const handleSaveGroups = async () => {
    if (!showGroups) return;
    try {
      await api.put(`/users/${showGroups.id}/groups`, { group_ids: editGroupIds });
      setShowGroups(null);
      loadData();
    } catch (e: any) { alert(e.message); }
  };

  if (authLoading || loading) return <PageLoader />;

  return (
    <div className="max-w-7xl mx-auto py-6">
      <PageHeader title="用户管理" subtitle="管理所有用户，分配群组和权限" actions={
        <button onClick={() => { setFormEmail(''); setFormName(''); setFormDept(''); setFormPassword(''); setFormGroupIds([]); setShowCreate(true); }} className="btn-primary">新建用户</button>
      } />

      {error && <ErrorBanner message={error} />}

      <Card>
        <CardHeader title="用户列表" actions={
          <Link href="/admin/groups" className="btn-secondary">群组管理</Link>
        } />
        <div className="card-body">
          {users.length === 0 ? <EmptyState message="暂无用户" /> : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>姓名</th>
                  <th>邮箱</th>
                  <th>部门</th>
                  <th>所属群组</th>
                  <th>状态</th>
                  <th>最后登录</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td className="font-medium">{u.display_name}</td>
                    <td className="text-xs text-slate-600">{u.email}</td>
                    <td className="text-xs">{u.department || '-'}</td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {u.groups.map(g => (
                          <span key={g.id} className={`badge text-xs ${categoryColor(g.category)}`}>{g.name}</span>
                        ))}
                        {u.groups.length === 0 && <span className="text-xs text-slate-400">未分配</span>}
                      </div>
                    </td>
                    <td>
                      <span className={`badge text-xs ${u.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                        {u.status === 'ACTIVE' ? '启用' : '停用'}
                      </span>
                    </td>
                    <td className="text-xs text-slate-400">{u.last_login_at ? new Date(u.last_login_at).toLocaleString('zh-CN') : '-'}</td>
                    <td>
                      <div className="flex gap-1">
                        <button onClick={() => openGroups(u)} className="btn-secondary text-xs">群组</button>
                        <button onClick={() => setShowResetPwd(u)} className="btn-secondary text-xs">重置密码</button>
                        {u.id !== user?.id && (
                          <button onClick={() => handleToggleStatus(u)} className="text-xs text-orange-600 hover:underline">
                            {u.status === 'ACTIVE' ? '停用' : '启用'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">新建用户</h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">邮箱 *</label>
                <input className="input-field" value={formEmail} onChange={e => setFormEmail(e.target.value)} placeholder="user@example.com" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">姓名 *</label>
                <input className="input-field" value={formName} onChange={e => setFormName(e.target.value)} placeholder="输入姓名" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">部门</label>
                <input className="input-field" value={formDept} onChange={e => setFormDept(e.target.value)} placeholder="可选" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">密码 *</label>
                <input type="password" className="input-field" value={formPassword} onChange={e => setFormPassword(e.target.value)} placeholder="输入密码" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">初始群组</label>
                <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto border rounded p-2">
                  {groups.filter(g => g.status === 'ACTIVE').map(g => (
                    <label key={g.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={formGroupIds.includes(g.id)} onChange={e => {
                        if (e.target.checked) setFormGroupIds([...formGroupIds, g.id]);
                        else setFormGroupIds(formGroupIds.filter(id => id !== g.id));
                      }} />{g.name} <span className={`text-xs ${categoryColor(g.category)}`}>{categoryLabel(g.category)}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <button onClick={() => setShowCreate(false)} className="btn-secondary">取消</button>
              <button disabled={formBusy || !formEmail || !formName || !formPassword} onClick={handleCreate} className="btn-primary">{formBusy ? '创建中...' : '创建'}</button>
            </div>
          </div>
        </div>
      )}

      {showGroups && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowGroups(null)}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">用户群组 - {showGroups.display_name}</h3>
            <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto">
              {groups.filter(g => g.status === 'ACTIVE').map(g => (
                <label key={g.id} className="flex items-center gap-2 text-sm p-2 hover:bg-slate-50 rounded">
                  <input type="checkbox" checked={editGroupIds.includes(g.id)} onChange={e => {
                    if (e.target.checked) setEditGroupIds([...editGroupIds, g.id]);
                    else setEditGroupIds(editGroupIds.filter(id => id !== g.id));
                  }} />
                  <span>{g.name}</span>
                  <span className={`badge text-xs ${categoryColor(g.category)}`}>{categoryLabel(g.category)}</span>
                </label>
              ))}
            </div>
            <div className="flex gap-2 mt-4 justify-end">
              <button onClick={() => setShowGroups(null)} className="btn-secondary">取消</button>
              <button onClick={handleSaveGroups} className="btn-primary">保存</button>
            </div>
          </div>
        </div>
      )}

      {showResetPwd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowResetPwd(null)}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-sm mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">重置密码 - {showResetPwd.display_name}</h3>
            <input type="password" className="input-field mb-4" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="输入新密码" />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowResetPwd(null)} className="btn-secondary">取消</button>
              <button disabled={!newPassword} onClick={handleResetPwd} className="btn-primary">重置</button>
            </div>
          </div>
        </div>
      )}

      {confirmMsg && (
        <ConfirmDialog title="确认操作" message={confirmMsg} onConfirm={() => confirmAction?.()} onCancel={() => { setConfirmMsg(''); setConfirmAction(null); }} />
      )}
    </div>
  );
}