'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Variation } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatMoney, formatNumber } from '@/components/ui/common';

const TYPE_LABEL: Record<string, string> = {
  SCOPE: '范围变更',
  PRICE: '价格调整',
  QUANTITY: '数量变更',
  OTHER: '其他',
};

export default function VariationsPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [variations, setVariations] = useState<Variation[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ variation_no: '', variation_type: 'SCOPE', description: '', amount_ex_tax: 0, quantity_delta: 0, effective_date: '' });

  useEffect(() => {
    if (!user) return;
    api.get<Variation[]>(`/variations?project_id=${projectId}`).then(setVariations).catch(() => {});
  }, [user, projectId]);

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  const handleCreate = async () => {
    try {
      const created = await api.post<Variation>('/variations', { ...form, project_id: projectId });
      setVariations([...variations, created]);
      setShowForm(false);
      setForm({ variation_no: '', variation_type: 'SCOPE', description: '', amount_ex_tax: 0, quantity_delta: 0, effective_date: '' });
    } catch (e) {
      alert(`创建失败：${(e as Error).message}`);
    }
  };

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader
        title="变更台账"
        actions={
          <button onClick={() => setShowForm(!showForm)} className={showForm ? 'btn-secondary' : 'btn-primary'}>
            {showForm ? '取消' : '新建变更'}
          </button>
        }
      />

      {showForm && (
        <Card className="mb-6">
          <CardHeader title="新建变更" />
          <div className="card-body">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">变更编号</label>
                <input value={form.variation_no} onChange={e => setForm({ ...form, variation_no: e.target.value })} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">类型</label>
                <select value={form.variation_type} onChange={e => setForm({ ...form, variation_type: e.target.value })} className="select-field">
                  <option value="SCOPE">范围变更</option>
                  <option value="PRICE">价格调整</option>
                  <option value="QUANTITY">数量变更</option>
                  <option value="OTHER">其他</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">描述</label>
                <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">金额(未税)</label>
                <input type="number" step="0.01" value={form.amount_ex_tax} onChange={e => setForm({ ...form, amount_ex_tax: parseFloat(e.target.value) || 0 })} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">数量变动</label>
                <input type="number" step="0.01" value={form.quantity_delta} onChange={e => setForm({ ...form, quantity_delta: parseFloat(e.target.value) || 0 })} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">生效日期</label>
                <input type="date" value={form.effective_date} onChange={e => setForm({ ...form, effective_date: e.target.value })} className="input-field" />
              </div>
            </div>
            <div className="mt-4">
              <button onClick={handleCreate} disabled={!form.variation_no} className="btn-primary disabled:opacity-50">保存</button>
            </div>
          </div>
        </Card>
      )}

      <Card>
        <CardHeader title="变更记录" />
        <div className="card-body">
          {variations.length === 0 ? (
            <EmptyState message="暂无变更记录" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>变更编号</th>
                  <th>类型</th>
                  <th>描述</th>
                  <th className="text-right">数量变动</th>
                  <th className="text-right">金额(未税)</th>
                  <th className="text-right">金额(含税)</th>
                  <th>状态</th>
                  <th>生效日期</th>
                </tr>
              </thead>
              <tbody>
                {variations.map(v => (
                  <tr key={v.id}>
                    <td className="font-mono">{v.variation_no}</td>
                    <td>{TYPE_LABEL[v.variation_type] || v.variation_type}</td>
                    <td>{v.description}</td>
                    <td className="num">{formatNumber(v.quantity_delta)}</td>
                    <td className="num">{formatMoney(v.amount_ex_tax)}</td>
                    <td className="num">{formatMoney(v.amount_inc_tax)}</td>
                    <td><StatusBadge status={v.status} /></td>
                    <td>{v.effective_date}</td>
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
