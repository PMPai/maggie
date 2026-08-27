'use client';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { PageHeader, Card, CardHeader, EmptyState } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { categoryLabel, categoryColor, roleLabel, hasCategory, type GroupInfo, type GroupDetail } from '@/lib/roles';
import Link from 'next/link';

export default function AdminGroupsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState<GroupInfo | null>(null);
  const [showMembers, setShowMembers] = useState<string | null>(null);
  const [members, setMembers] = useState<GroupDetail['members']>([]);
  const [allUsers, setAllUsers] = useState<{ id: string; display_name: string; email: string }[]>([]);
  const [confirmMsg, setConfirmMsg] = useState('');
  const [confirmAction, setConfirmAction] = useState<(() => void) | null>(null);

  const [formName, setFormName] = useState('');
  const [formCategory, setFormCategory] = useState('LEADER');
  const [formDesc, setFormDesc] = useState('');
  const [formRoleIds, setFormRoleIds] = useState<string[]>([]);
  const [formBusy, setFormBusy] = useState(false);
  const [allRoles, setAllRoles] = useState<{ id: string; name: string }[]>([]);
  const [addMemberIds, setAddMemberIds] = useState<string[]>([]);

  const CAT_OPTIONS = [
    { value: 'ADMIN', label: '管理员' },
    { value: 'FINANCE', label: '财务' },
    { value: 'LEADER', label: '项目' },
    { value: 'AUDITOR', label: '审计' },
    { value: 'VIEWER', label: '只读' },
  ];

  const loadData = () => {
    api.get<GroupInfo[]>('/groups').then(setGroups).catch(e => setError(e.message)).finally(() => setLoading(false));
    api.get<any[]>('/users').then(users => setAllUsers(users.map(u => ({ id: u.id, display_name: u.display_name, email: u.email })))).catch(() => {});
    api.get<{ id: string; name: string }[]>('/auth/roles').then(setAllRoles).catch(() => {});
  };

  useEffect(() => {
    if (!authLoading && user) {
      if (!hasCategory(user.roles, 'ADMIN')) { router.replace('/dashboard'); return; }
      loadData();
    }
  }, [user, authLoading]);

  const openMembers = async (groupId: string) => {
    setShowMembers(groupId);
    try {
      const g = await api.get<GroupDetail>(`/groups/${groupId}`);
      setMembers(g.members);
    } catch {}
  };

  const handleCreate = async () => {
    setFormBusy(true);
    try {
      await api.post('/groups', { name: formName, category: formCategory, description: formDesc, role_ids: formRoleIds });
      setShowCreate(false);
      setFormName(''); setFormDesc(''); setFormRoleIds([]);
      loadData();
    } catch (e: any) { alert(e.message); }
    finally { setFormBusy(false); }
  };

  const handleEdit = async () => {
    if (!showEdit) return;
    setFormBusy(true);
    try {
      await api.put(`/groups/${showEdit.id}`, { name: formName, category: formCategory, description: formDesc, role_ids: formRoleIds });
      setShowEdit(null);
      loadData();
    } catch (e: any) { alert(e.message); }
    finally { setFormBusy(false); }
  };

  const openEdit = (g: GroupInfo) => {
    setFormName(g.name);
    setFormCategory(g.category);
    setFormDesc(g.description || '');
    setFormRoleIds(g.roles.map(r => r.id));
    setShowEdit(g);
  };

  const handleDelete = (g: GroupInfo) => {
    if (g.is_default) { alert('默认群组不可删除'); return; }
    setConfirmMsg(`确定要删除群组「${g.name}」吗？该群组的成员将被移除。`);
    setConfirmAction(() => async () => {
      try { await api.del(`/groups/${g.id}`); loadData(); } catch (e: any) { alert(e.message); }
      setConfirmMsg(''); setConfirmAction(null);
    });
  };

  const handleToggleStatus = (g: GroupInfo) => {
    if (g.is_default && g.status === 'ACTIVE') { alert('默认群组不可停用'); return; }
    const newStatus = g.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    setConfirmMsg(`确定要${newStatus === 'ACTIVE' ? '启用' : '停用'}群组「${g.name}」吗？`);
    setConfirmAction(() => async () => {
      try { await api.put(`/groups/${g.id}`, { status: newStatus }); loadData(); } catch (e: any) { alert(e.message); }
      setConfirmMsg(''); setConfirmAction(null);
    });
  };

  const handleAddMembers = async () => {
    if (!showMembers || addMemberIds.length === 0) return;
    try {
      await api.post(`/groups/${showMembers}/members`, { user_ids: addMemberIds });
      setAddMemberIds([]);
      openMembers(showMembers);
    } catch (e: any) { alert(e.message); }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!showMembers) return;
    try {
      await api.del(`/groups/${showMembers}/members/${userId}`);
      openMembers(showMembers);
    } catch (e: any) { alert(e.message); }
  };

  if (authLoading || loading) return <PageLoader />;

  return (
    <div className="max-w-6xl mx-auto py-6">
      <PageHeader title="群组管理" subtitle="管理系统群组，控制用户权限" actions={
        <button onClick={() => { setFormName(''); setFormCategory('LEADER'); setFormDesc(''); setFormRoleIds([]); setShowCreate(true); }} className="btn-primary">新建群组</button>
      } />

      {error && <ErrorBanner message={error} />}

      <Card>
        <CardHeader title="群组列表" actions={
          <Link href="/admin/users" className="btn-secondary">用户管理</Link>
        } />
        <div className="card-body">
          {groups.length === 0 ? <EmptyState message="暂无群组" /> : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>群组名称</th>
                  <th>类别</th>
                  <th>角色</th>
                  <th className="text-center">成员</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {groups.map(g => (
                  <tr key={g.id}>
                    <td className="font-medium">{g.name}{g.is_default ? <span className="ml-1 text-xs text-slate-400">(默认)</span> : ''}</td>
                    <td><span className={`badge text-xs ${categoryColor(g.category)}`}>{categoryLabel(g.category)}</span></td>
                    <td className="text-xs text-slate-500">{g.roles.map(r => roleLabel(r.name)).join('、') || '-'}</td>
                    <td className="text-center">{g.member_count}人</td>
                    <td><span className={`badge text-xs ${g.status === 'ACTIVE' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>{g.status === 'ACTIVE' ? '启用' : '停用'}</span></td>
                    <td>
                      <div className="flex gap-1">
                        <button onClick={() => openMembers(g.id)} className="btn-secondary text-xs">成员</button>
                        <button onClick={() => openEdit(g)} className="btn-secondary text-xs">编辑</button>
                        {!g.is_default && (
                          <>
                            <button onClick={() => handleDelete(g)} className="text-xs text-red-600 hover:underline">删除</button>
                            <button onClick={() => handleToggleStatus(g)} className="text-xs text-orange-600 hover:underline">{g.status === 'ACTIVE' ? '停用' : '启用'}</button>
                          </>
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

      {(showCreate || showEdit) && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => { setShowCreate(false); setShowEdit(null); }}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg mx-4" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">{showCreate ? '新建群组' : '编辑群组'}</h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-slate-500 block mb-1">群组名称</label>
                <input className="input-field" value={formName} onChange={e => setFormName(e.target.value)} placeholder="输入群组名称" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">类别</label>
                <select className="input-field" value={formCategory} onChange={e => setFormCategory(e.target.value)}>
                  {CAT_OPTIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">描述</label>
                <input className="input-field" value={formDesc} onChange={e => setFormDesc(e.target.value)} placeholder="可选" />
              </div>
              <div>
                <label className="text-xs text-slate-500 block mb-1">角色权限</label>
                <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto border rounded p-2">
                  {allRoles.map(r => (
                    <label key={r.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={formRoleIds.includes(r.id)} onChange={e => {
                        if (e.target.checked) setFormRoleIds([...formRoleIds, r.id]);
                        else setFormRoleIds(formRoleIds.filter(id => id !== r.id));
                      }} />{r.name}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <button onClick={() => { setShowCreate(false); setShowEdit(null); }} className="btn-secondary">取消</button>
              <button disabled={formBusy || !formName} onClick={showCreate ? handleCreate : handleEdit} className="btn-primary">{formBusy ? '保存中...' : '保存'}</button>
            </div>
          </div>
        </div>
      )}

      {showMembers && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => { setShowMembers(null); setAddMemberIds([]); }}>
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-semibold mb-4">群组成员</h3>
            <div className="mb-4">
              <label className="text-xs text-slate-500 block mb-1">添加成员</label>
              <div className="flex gap-2">
                <select className="input-field flex-1" multiple value={addMemberIds} onChange={e => {
                  const vals = Array.from(e.target.selectedOptions, o => o.value);
                  setAddMemberIds(vals);
                }} size={4}>
                  {allUsers.filter(u => !members.some(m => m.id === u.id)).map(u => (
                    <option key={u.id} value={u.id}>{u.display_name} ({u.email})</option>
                  ))}
                </select>
                <button onClick={handleAddMembers} disabled={addMemberIds.length === 0} className="btn-primary self-start">添加</button>
              </div>
            </div>
            <table className="data-table">
              <thead>
                <tr><th>姓名</th><th>邮箱</th><th>操作</th></tr>
              </thead>
              <tbody>
                {members.map(m => (
                  <tr key={m.id}>
                    <td>{m.display_name}</td>
                    <td className="text-xs text-slate-500">{m.email}</td>
                    <td><button onClick={() => handleRemoveMember(m.id)} className="text-xs text-red-600 hover:underline">移除</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {members.length === 0 && <EmptyState message="该群组暂无成员" />}
            <div className="flex justify-end mt-4">
              <button onClick={() => { setShowMembers(null); setAddMemberIds([]); }} className="btn-secondary">关闭</button>
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