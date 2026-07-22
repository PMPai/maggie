'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Application, ApplicationLine, Contract, Project } from '@/lib/types';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';

export default function ApplicationDetailPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const router = useRouter();
  const appId = params.id as string;
  const [app, setApp] = useState<Application | null>(null);
  const [lines, setLines] = useState<ApplicationLine[]>([]);
  const [contract, setContract] = useState<Contract | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    api.get<Application>(`/payment-applications/${appId}`).then(async a => {
      setApp(a);
      api.get<ApplicationLine[]>(`/payment-applications/${appId}/lines`).then(setLines);
      try {
        const c = await api.get<Contract>(`/contracts/${a.contract_id}`);
        setContract(c);
        api.get<Project>(`/projects/${a.project_id}`).then(setProject);
      } catch {}
    });
  }, [user, appId]);

  if (loading || !app) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  const statusBadge = (status: string) => {
    const colors: Record<string, string> = {
      DRAFT: 'bg-gray-100 text-gray-700',
      SUBMITTED: 'bg-yellow-100 text-yellow-700',
      APPROVED: 'bg-green-100 text-green-700',
      POSTED: 'bg-blue-100 text-blue-700',
      REJECTED: 'bg-red-100 text-red-700',
    };
    return <span className={`rounded px-2 py-1 text-xs font-medium ${colors[status] || 'bg-gray-100'}`}>{status}</span>;
  };

  const doTransition = async (action: 'submit' | 'approve' | 'post') => {
    setBusy(true);
    try {
      const updated = await api.post<Application>(`/payment-applications/${appId}/${action}`, {});
      setApp(updated);
    } catch (e) {
      alert(`操作失败：${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const num = (v: string | number) => Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="mb-4 flex items-center gap-2 text-sm">
        <Link href={project ? `/projects/${project.id}` : '/dashboard'} className="text-blue-600 hover:underline">← 返回项目</Link>
      </div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{app.application_no}</h1>
          <p className="text-gray-500 mt-1">第 {app.period_no} 期 · {statusBadge(app.status)}</p>
        </div>
        <div className="flex gap-2">
          {app.status === 'DRAFT' && <button disabled={busy} onClick={() => doTransition('submit')} className="rounded bg-yellow-600 px-4 py-2 text-white hover:bg-yellow-700 disabled:opacity-50">提交</button>}
          {app.status === 'SUBMITTED' && <button disabled={busy} onClick={() => doTransition('approve')} className="rounded bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50">审批通过</button>}
          {app.status === 'APPROVED' && <button disabled={busy} onClick={() => doTransition('post')} className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50">过账</button>}
        </div>
      </div>

      {contract && (
        <p className="text-sm text-gray-500 mb-4">合同：{contract.external_contract_no} · {contract.contract_name}</p>
      )}

      <h2 className="text-lg font-semibold mb-2">请款明细</h2>
      <div className="overflow-x-auto rounded-lg bg-white shadow">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left">项次</th>
              <th className="px-3 py-2 text-left">项目名称</th>
              <th className="px-3 py-2 text-left">单位</th>
              <th className="px-3 py-2 text-right">单价</th>
              <th className="px-3 py-2 text-right">前期累计</th>
              <th className="px-3 py-2 text-right">本期数量</th>
              <th className="px-3 py-2 text-right">本期累计</th>
              <th className="px-3 py-2 text-right">本期完成金额</th>
              <th className="px-3 py-2 text-right">保留款</th>
              <th className="px-3 py-2 text-right">未税金额</th>
              <th className="px-3 py-2 text-right">税额</th>
              <th className="px-3 py-2 text-right">净额</th>
            </tr>
          </thead>
          <tbody>
            {lines.map(l => (
              <tr key={l.id} className="border-t">
                <td className="px-3 py-2">{l.contract_item_id.slice(0, 8)}</td>
                <td className="px-3 py-2">{l.description_snapshot}</td>
                <td className="px-3 py-2">{l.unit_snapshot || '—'}</td>
                <td className="px-3 py-2 text-right">{num(l.unit_price_snapshot)}</td>
                <td className="px-3 py-2 text-right">{num(l.previous_approved_quantity)}</td>
                <td className="px-3 py-2 text-right">{num(l.current_approved_quantity)}</td>
                <td className="px-3 py-2 text-right">{num(l.cumulative_approved_quantity)}</td>
                <td className="px-3 py-2 text-right">{num(l.current_completed_amount)}</td>
                <td className="px-3 py-2 text-right">{num(l.retention_held)}</td>
                <td className="px-3 py-2 text-right">{num(l.taxable_amount)}</td>
                <td className="px-3 py-2 text-right">{num(l.tax_amount)}</td>
                <td className="px-3 py-2 text-right">{num(l.net_amount)}</td>
              </tr>
            ))}
            {lines.length === 0 && <tr><td colSpan={12} className="px-3 py-4 text-center text-gray-500">暂无明细</td></tr>}
          </tbody>
        </table>
      </div>

      <h2 className="text-lg font-semibold mt-6 mb-2">金额汇总</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">本期完成金额</p>
          <p className="text-lg font-bold">{num(app.gross_completed_amount)}</p>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">本期保留款</p>
          <p className="text-lg font-bold text-red-600">-{num(app.retention_held_amount)}</p>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">本期释放保留款</p>
          <p className="text-lg font-bold text-green-600">{num(app.retention_released_amount)}</p>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">本期扣款</p>
          <p className="text-lg font-bold text-red-600">-{num(app.deduction_amount)}</p>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">本期未税可开票金额</p>
          <p className="text-lg font-bold">{num(app.taxable_amount)}</p>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">税额</p>
          <p className="text-lg font-bold">{num(app.tax_amount)}</p>
        </div>
        <div className="rounded-lg bg-blue-50 p-4 shadow">
          <p className="text-xs text-blue-600">含税发票金额</p>
          <p className="text-xl font-bold text-blue-700">{num(app.invoice_amount)}</p>
        </div>
      </div>
    </main>
  );
}
