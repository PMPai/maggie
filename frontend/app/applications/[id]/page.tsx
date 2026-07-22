'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Application, ApplicationLine, Contract, Project } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatMoney, formatNumber } from '@/components/ui/common';

export default function ApplicationDetailPage() {
  const { user, loading } = useAuth();
  const params = useParams();
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

  const appAny = app as Application & { period_start?: string; period_end?: string; application_date?: string; created_at?: string };

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

  const sumMoney = (key: keyof ApplicationLine) =>
    lines.reduce((s, l) => s + parseFloat(l[key] as string || '0'), 0);
  const sumQty = (key: keyof ApplicationLine) =>
    lines.reduce((s, l) => s + parseFloat(l[key] as string || '0'), 0);

  const totals = {
    current_completed_amount: sumMoney('current_completed_amount'),
    retention_held: sumMoney('retention_held'),
    taxable_amount: sumMoney('taxable_amount'),
    tax_amount: sumMoney('tax_amount'),
    net_amount: sumMoney('net_amount'),
    current_approved_quantity: sumQty('current_approved_quantity'),
  };

  const totalBuckets: { label: string; value: string; emphasis?: boolean }[] = [
    { label: '本期完成金额', value: formatMoney(app.gross_completed_amount) },
    { label: '本期保留款', value: formatMoney(app.retention_held_amount) },
    { label: '本期释放保留款', value: formatMoney(app.retention_released_amount) },
    { label: '本期扣款', value: formatMoney(app.deduction_amount) },
    { label: '本期未税可开票金额', value: formatMoney(app.taxable_amount) },
    { label: '税额', value: formatMoney(app.tax_amount) },
    { label: '含税发票金额', value: formatMoney(app.invoice_amount), emphasis: true },
  ];

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="mb-3">
        <Link href={project ? `/projects/${project.id}` : '/dashboard'} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-orange-600 transition-colors">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          返回项目
        </Link>
      </div>

      <PageHeader
        title="请款详情"
        subtitle={`${app.application_no} · 第 ${app.period_no} 期`}
        actions={
          <div className="flex gap-2">
            {app.status === 'DRAFT' && (
              <button disabled={busy} onClick={() => doTransition('submit')} className="btn-primary">
                提交审批
              </button>
            )}
            {app.status === 'SUBMITTED' && (
              <button disabled={busy} onClick={() => doTransition('approve')} className="btn-primary">
                审批通过
              </button>
            )}
            {app.status === 'APPROVED' && (
              <button disabled={busy} onClick={() => doTransition('post')} className="btn-primary">
                过账
              </button>
            )}
            <Link href={project ? `/projects/${project.id}` : '/dashboard'} className="btn-secondary">
              关闭
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <Card>
          <CardHeader title="请款信息" />
          <div className="card-body grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
            <div>
              <p className="text-xs text-slate-500">请款编号</p>
              <p className="font-medium text-slate-800 mt-0.5">{app.application_no}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">期数</p>
              <p className="font-medium text-slate-800 mt-0.5">第 {app.period_no} 期</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">状态</p>
              <div className="mt-1"><StatusBadge status={app.status} /></div>
            </div>
            <div>
              <p className="text-xs text-slate-500">合同</p>
              <p className="font-medium text-slate-800 mt-0.5">
                {contract ? `${contract.external_contract_no} · ${contract.contract_name}` : '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">期间开始</p>
              <p className="font-medium text-slate-800 mt-0.5">{appAny.period_start || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">期间结束</p>
              <p className="font-medium text-slate-800 mt-0.5">{appAny.period_end || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">申请日期</p>
              <p className="font-medium text-slate-800 mt-0.5">{appAny.application_date || '—'}</p>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="金额汇总" />
          <div className="card-body grid grid-cols-2 gap-x-6 gap-y-4">
            {totalBuckets.map(b => (
              <div key={b.label} className={b.emphasis ? 'col-span-2 border-t border-slate-200 pt-3' : ''}>
                <p className="text-xs text-slate-500">{b.label}</p>
                <p className={`mt-0.5 font-mono tabular-nums text-right ${b.emphasis ? 'text-lg font-bold text-orange-600' : 'text-sm font-semibold text-slate-800'}`}>
                  {b.value}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="请款明细" actions={<span className="text-xs text-slate-400">{lines.length} 条明细</span>} />
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>项次</th>
                <th>项目名称</th>
                <th>单位</th>
                <th className="num">单价</th>
                <th className="num">前期累计</th>
                <th className="num">本期数量</th>
                <th className="num">本期累计</th>
                <th className="num">本期完成金额</th>
                <th className="num">保留款</th>
                <th className="num">未税金额</th>
                <th className="num">税额</th>
                <th className="num">净额</th>
              </tr>
            </thead>
            <tbody>
              {lines.map(l => (
                <tr key={l.id}>
                  <td className="font-mono text-slate-500">{l.contract_item_id.slice(0, 8)}</td>
                  <td>{l.description_snapshot}</td>
                  <td>{l.unit_snapshot || '—'}</td>
                  <td className="num">{formatMoney(l.unit_price_snapshot)}</td>
                  <td className="num">{formatNumber(l.previous_approved_quantity)}</td>
                  <td className="num">{formatNumber(l.current_approved_quantity)}</td>
                  <td className="num">{formatNumber(l.cumulative_approved_quantity)}</td>
                  <td className="num">{formatMoney(l.current_completed_amount)}</td>
                  <td className="num">{formatMoney(l.retention_held)}</td>
                  <td className="num">{formatMoney(l.taxable_amount)}</td>
                  <td className="num">{formatMoney(l.tax_amount)}</td>
                  <td className="num">{formatMoney(l.net_amount)}</td>
                </tr>
              ))}
              {lines.length === 0 && (
                <tr>
                  <td colSpan={12}>
                    <EmptyState message="暂无明细" />
                  </td>
                </tr>
              )}
            </tbody>
            {lines.length > 0 && (
              <tfoot>
                <tr className="font-bold text-slate-800 border-t-2 border-slate-300">
                  <td colSpan={5} className="px-4 py-3 text-right">合计</td>
                  <td className="num px-4 py-3">{formatNumber(totals.current_approved_quantity)}</td>
                  <td className="num px-4 py-3">—</td>
                  <td className="num px-4 py-3">{formatMoney(totals.current_completed_amount)}</td>
                  <td className="num px-4 py-3">{formatMoney(totals.retention_held)}</td>
                  <td className="num px-4 py-3">{formatMoney(totals.taxable_amount)}</td>
                  <td className="num px-4 py-3">{formatMoney(totals.tax_amount)}</td>
                  <td className="num px-4 py-3">{formatMoney(totals.net_amount)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </Card>
    </main>
  );
}
