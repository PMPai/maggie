'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Variation } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';

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

  const num = (v: number) => Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

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
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-blue-600 hover:underline">← 返回项目</Link>
      </div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">变更台账</h1>
        <button onClick={() => setShowForm(!showForm)} className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">{showForm ? '取消' : '新建变更'}</button>
      </div>

      {showForm && (
        <div className="mb-6 rounded-lg bg-white p-4 shadow space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">变更编号</label>
              <input value={form.variation_no} onChange={e => setForm({ ...form, variation_no: e.target.value })} className="w-full rounded border px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">类型</label>
              <select value={form.variation_type} onChange={e => setForm({ ...form, variation_type: e.target.value })} className="w-full rounded border px-3 py-2">
                <option value="SCOPE">范围变更</option>
                <option value="PRICE">价格调整</option>
                <option value="QUANTITY">数量变更</option>
                <option value="OTHER">其他</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium mb-1">描述</label>
              <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} className="w-full rounded border px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">金额(未税)</label>
              <input type="number" step="0.01" value={form.amount_ex_tax} onChange={e => setForm({ ...form, amount_ex_tax: parseFloat(e.target.value) || 0 })} className="w-full rounded border px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">数量变动</label>
              <input type="number" step="0.01" value={form.quantity_delta} onChange={e => setForm({ ...form, quantity_delta: parseFloat(e.target.value) || 0 })} className="w-full rounded border px-3 py-2" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">生效日期</label>
              <input type="date" value={form.effective_date} onChange={e => setForm({ ...form, effective_date: e.target.value })} className="w-full rounded border px-3 py-2" />
            </div>
          </div>
          <button onClick={handleCreate} disabled={!form.variation_no} className="rounded bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50">保存</button>
        </div>
      )}

      <div className="rounded-lg bg-white shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">变更编号</th>
              <th className="px-4 py-2 text-left">类型</th>
              <th className="px-4 py-2 text-left">描述</th>
              <th className="px-4 py-2 text-right">金额(未税)</th>
              <th className="px-4 py-2 text-right">金额(含税)</th>
              <th className="px-4 py-2 text-right">数量变动</th>
              <th className="px-4 py-2 text-left">状态</th>
              <th className="px-4 py-2 text-left">生效日期</th>
            </tr>
          </thead>
          <tbody>
            {variations.map(v => (
              <tr key={v.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2">{v.variation_no}</td>
                <td className="px-4 py-2">{v.variation_type}</td>
                <td className="px-4 py-2">{v.description}</td>
                <td className="px-4 py-2 text-right">{num(v.amount_ex_tax)}</td>
                <td className="px-4 py-2 text-right">{num(v.amount_inc_tax)}</td>
                <td className="px-4 py-2 text-right">{num(v.quantity_delta)}</td>
                <td className="px-4 py-2">{v.status}</td>
                <td className="px-4 py-2">{v.effective_date}</td>
              </tr>
            ))}
            {variations.length === 0 && <tr><td colSpan={8} className="px-4 py-4 text-center text-gray-500">暂无变更记录</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
