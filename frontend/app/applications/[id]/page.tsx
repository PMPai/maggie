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
  const [validation, setValidation] = useState<{ valid: boolean; issues: { code: string; field: string; message: string; severity: string }[] } | null>(null);
  const [validating, setValidating] = useState(false);
  const [genStatus, setGenStatus] = useState<string>('');

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

  const doValidate = async () => {
    setValidating(true);
    try {
      const result = await api.post<{ valid: boolean; issues: { code: string; field: string; message: string; severity: string }[] }>(`/payment-applications/${appId}/validate`, {});
      setValidation(result);
    } catch (e) {
      alert(`校验失败：${(e as Error).message}`);
    } finally {
      setValidating(false);
    }
  };

  const doGenerate = async () => {
    setBusy(true);
    setGenStatus('');
    try {
      const result = await api.post<{ task_id: string; status: string }>(`/payment-applications/${appId}/generate`, {});
      setGenStatus('生成中...');
      // Poll task status
      const poll = setInterval(async () => {
        try {
          const ts = await api.get<{ state: string; result: any; error: string | null }>(`/tasks/${result.task_id}/status`);
          if (ts.state === 'SUCCESS') {
            clearInterval(poll);
            setGenStatus('完成');
            setBusy(false);
          } else if (ts.state === 'FAILURE') {
            clearInterval(poll);
            setGenStatus('失败: ' + (ts.error || ''));
            setBusy(false);
          }
        } catch {
          clearInterval(poll);
          setGenStatus('查询失败');
          setBusy(false);
        }
      }, 2000);
    } catch (e) {
      alert(`生成失败：${(e as Error).message}`);
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
              <>
                <button disabled={validating} onClick={doValidate} className="btn-secondary">
                  {validating ? '校验中...' : '校验'}
                </button>
                <button disabled={busy} onClick={() => doTransition('submit')} className="btn-primary">
                  提交审批
                </button>
              </>
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
            {(app.status === 'POSTED' || app.status === 'GENERATED') && (
              <button disabled={busy} onClick={doGenerate} className="btn-primary">
                {busy ? (genStatus || '处理中...') : '生成 PDF'}
              </button>
            )}
            <Link href={project ? `/projects/${project.id}` : '/dashboard'} className="btn-secondary">
              关闭
            </Link>
          </div>
        }
      />

      {/* Approval workflow steps */}
      <Card>
        <CardHeader title="审批流程" />
        <div className="card-body">
          <div className="flex items-center gap-2 flex-wrap">
            {(() => {
              const steps = ['DRAFT', 'SUBMITTED', 'PROJECT_APPROVED', 'FINANCE_APPROVED', 'POSTED'];
              const labels: Record<string, string> = {
                DRAFT: '草稿', SUBMITTED: '已提交', PROJECT_APPROVED: '项目负责人已批',
                FINANCE_APPROVED: '财务已批', POSTED: '已过账',
              };
              const currentIdx = steps.indexOf(app.status);
              return steps.map((s, i) => {
                const done = currentIdx > i;
                const current = currentIdx === i;
                return (
                  <div key={s} className="flex items-center gap-2">
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
                      done ? 'bg-green-100 text-green-700' : current ? 'bg-orange-100 text-orange-700' : 'bg-slate-100 text-slate-400'
                    }`}>
                      <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs ${
                        done ? 'bg-green-500 text-white' : current ? 'bg-orange-500 text-white' : 'bg-slate-300 text-white'
                      }`}>
                        {done ? '✓' : i + 1}
                      </span>
                      {labels[s]}
                    </div>
                    {i < steps.length - 1 && <span className="text-slate-300">→</span>}
                  </div>
                );
              });
            })()}
          </div>
        </div>
      </Card>

      {validation && (
        <Card>
          <CardHeader title="校验结果" actions={
            <span className={validation.valid ? 'badge badge-green' : 'badge badge-red'}>
              {validation.valid ? '通过' : `${validation.issues.filter(i => i.severity === 'ERROR').length} 个错误`}
            </span>
          } />
          <div className="card-body">
            {validation.issues.length === 0 ? (
              <p className="text-sm text-green-600">所有校验规则通过 ✓</p>
            ) : (
              <ul className="space-y-2">
                {validation.issues.map((issue, i) => (
                  <li key={i} className={`flex items-start gap-2 text-sm ${issue.severity === 'ERROR' ? 'text-red-600' : 'text-orange-600'}`}>
                    <span className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                      issue.severity === 'ERROR' ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'
                    }`}>
                      {issue.severity === 'ERROR' ? '!' : '?'}
                    </span>
                    <span>{issue.message}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Card>
      )}

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
