'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Project } from '@/lib/types';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

export default function ProjectsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);

  const load = () => {
    api.get<Project[]>('/projects').then(setProjects).catch(e => setError(e?.message || '加载失败'));
  };

  useEffect(() => { if (user) load(); }, [user]);

  if (loading) return <PageLoader />;

  return (
    <div>
      <PageHeader title="项目管理" subtitle="查看与新建项目" />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="mb-4">
        <button onClick={() => setShowForm(true)} className="btn-primary">
          + 新建项目
        </button>
      </div>

      <Card>
        <CardHeader title={`项目列表 (${projects.length})`} />
        <div className="overflow-x-auto">
          {projects.length === 0 ? (
            <EmptyState message="暂无项目，请点击「新建项目」" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>项目编号</th>
                  <th>工程名称</th>
                  <th>状态</th>
                  <th>币别</th>
                  <th className="text-right">税率</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {projects.map(p => (
                  <tr key={p.id}>
                    <td>
                      <Link href={`/projects/${p.id}`} className="text-blue-600 hover:underline">
                        {p.internal_project_code}
                      </Link>
                    </td>
                    <td>{p.project_name}</td>
                    <td><StatusBadge status={p.status} /></td>
                    <td>{p.currency}</td>
                    <td className="num">{p.default_tax_rate}</td>
                    <td>
                      <Link href={`/projects/${p.id}/setup`} className="text-orange-600 text-sm hover:underline">
                        设置预算 →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      {showForm && (
        <CreateProjectModal
          onCancel={() => setShowForm(false)}
          onCreated={(projectId) => { setShowForm(false); router.push(`/projects/${projectId}/setup`); }}
          creating={creating}
          setCreating={setCreating}
        />
      )}
    </div>
  );
}

function CreateProjectModal({ onCancel, onCreated, creating, setCreating }: {
  onCancel: () => void;
  onCreated: (projectId: string) => void;
  creating: boolean;
  setCreating: (v: boolean) => void;
}) {
  const [form, setForm] = useState({
    internal_project_code: '',
    project_name: '',
    description: '',
    currency: 'TWD',
    default_tax_rate: '0.05',
    start_date: '',
    planned_end_date: '',
    special_fund_description: '',
  });
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.internal_project_code || !form.project_name) {
      setError('项目编号和工程名称为必填');
      return;
    }
    setCreating(true);
    setError('');
    try {
      const body: Record<string, any> = {
        internal_project_code: form.internal_project_code,
        project_name: form.project_name,
        currency: form.currency,
        default_tax_rate: form.default_tax_rate,
      };
      if (form.description) body.description = form.description;
      if (form.start_date) body.start_date = form.start_date;
      if (form.planned_end_date) body.planned_end_date = form.planned_end_date;
      if (form.special_fund_description) body.special_fund_description = form.special_fund_description;
      const result = await api.post<Project>('/projects', body);
      onCreated(result.id);
    } catch (e: any) {
      setError(e?.message || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onCancel}>
      <div className="bg-white rounded-lg p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-slate-800">新建项目</h3>
          <button onClick={onCancel} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>
        {error && <ErrorBanner message={error} />}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">项目编号 *</label>
            <input
              type="text" value={form.internal_project_code}
              onChange={e => setForm({ ...form, internal_project_code: e.target.value })}
              className="input-field text-sm" placeholder="例如 25-032" required
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">工程名称 *</label>
            <input
              type="text" value={form.project_name}
              onChange={e => setForm({ ...form, project_name: e.target.value })}
              className="input-field text-sm" placeholder="例如 污水工作井地改工程" required
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">说明</label>
            <input
              type="text" value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
              className="input-field text-sm" placeholder="可选"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">币别</label>
              <input
                type="text" value={form.currency}
                onChange={e => setForm({ ...form, currency: e.target.value })}
                className="input-field text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">默认税率</label>
              <input
                type="text" value={form.default_tax_rate}
                onChange={e => setForm({ ...form, default_tax_rate: e.target.value })}
                className="input-field text-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">开始日期</label>
              <input
                type="date" value={form.start_date}
                onChange={e => setForm({ ...form, start_date: e.target.value })}
                className="input-field text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">预计完工日期</label>
              <input
                type="date" value={form.planned_end_date}
                onChange={e => setForm({ ...form, planned_end_date: e.target.value })}
                className="input-field text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">特有款说明</label>
            <textarea
              value={form.special_fund_description}
              onChange={e => setForm({ ...form, special_fund_description: e.target.value })}
              className="input-field text-sm" rows={2} placeholder="如有特有款，请在此说明（可选）"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onCancel} className="btn-secondary">取消</button>
            <button type="submit" disabled={creating} className="btn-primary">
              {creating ? '创建中...' : '创建项目'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
