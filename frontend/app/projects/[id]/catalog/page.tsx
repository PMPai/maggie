'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import type { StandardItem } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge } from '@/components/ui/common';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

export default function CatalogPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [items, setItems] = useState<StandardItem[]>([]);
  const [search, setSearch] = useState('');
  const [filterCat, setFilterCat] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ code: '', name: '', category: '', unit: '', description: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get<StandardItem[]>('/standard-items').then(setItems).catch(() => setItems([]));
  }, [user]);

  const categories = useMemo(() => Array.from(new Set(items.map(i => i.category).filter(Boolean))), [items]);
  const filtered = useMemo(() => {
    return items.filter(i => {
      if (filterCat && i.category !== filterCat) return false;
      if (search) {
        const s = search.toLowerCase();
        if (!i.code.toLowerCase().includes(s) && !i.name.toLowerCase().includes(s)) return false;
      }
      return true;
    });
  }, [items, search, filterCat]);

  const createItem = async () => {
    if (!createForm.code || !createForm.name) { setError('编号和名称为必填'); return; }
    setBusy(true); setError('');
    try {
      await api.post('/standard-items', createForm);
      setShowCreate(false);
      setCreateForm({ code: '', name: '', category: '', unit: '', description: '' });
      const refreshed = await api.get<StandardItem[]>('/standard-items');
      setItems(refreshed);
    } catch (e: any) { setError(e?.message || '创建失败'); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="标准项目目录" />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="flex items-center gap-3 mb-4">
        <input type="text" placeholder="搜索编号或名称..." value={search} onChange={e => setSearch(e.target.value)} className="input-field text-sm flex-1" />
        <select value={filterCat} onChange={e => setFilterCat(e.target.value)} className="input-field text-sm w-40">
          <option value="">全部类别</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <button onClick={() => setShowCreate(true)} className="btn-primary text-sm">+ 新建标准项目</button>
      </div>

      {showCreate && (
        <Card className="mb-4">
          <CardHeader title="新建标准项目" />
          <div className="card-body grid grid-cols-2 gap-3">
            <input type="text" placeholder="编号 *" value={createForm.code} onChange={e => setCreateForm({...createForm, code: e.target.value})} className="input-field text-sm" />
            <input type="text" placeholder="名称 *" value={createForm.name} onChange={e => setCreateForm({...createForm, name: e.target.value})} className="input-field text-sm" />
            <input type="text" placeholder="类别" value={createForm.category} onChange={e => setCreateForm({...createForm, category: e.target.value})} className="input-field text-sm" />
            <input type="text" placeholder="单位" value={createForm.unit} onChange={e => setCreateForm({...createForm, unit: e.target.value})} className="input-field text-sm" />
            <input type="text" placeholder="描述" value={createForm.description} onChange={e => setCreateForm({...createForm, description: e.target.value})} className="input-field text-sm col-span-2" />
            <div className="col-span-2 flex gap-2">
              <button onClick={createItem} disabled={busy} className="btn-primary text-sm">{busy ? '创建中...' : '创建'}</button>
              <button onClick={() => setShowCreate(false)} className="btn-secondary text-sm">取消</button>
            </div>
          </div>
        </Card>
      )}

      <Card>
        <CardHeader title={`标准项目 (${filtered.length}/${items.length})`} />
        <div className="overflow-x-auto">
          {filtered.length === 0 ? <EmptyState message="暂无标准项目" /> : (
            <table className="data-table">
              <thead>
                <tr><th>编号</th><th>名称</th><th>类别</th><th>单位</th><th>状态</th></tr>
              </thead>
              <tbody>
                {filtered.map(i => (
                  <tr key={i.id}>
                    <td className="font-mono">{i.code}</td>
                    <td>{i.name}</td>
                    <td>{i.category}</td>
                    <td>{i.unit}</td>
                    <td><StatusBadge status={i.is_active ? 'ACTIVE' : 'INACTIVE'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </main>
  );
}
