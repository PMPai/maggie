'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { DashboardSummary, Project } from '@/lib/types';
import Link from 'next/link';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatMoney } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts';

// Design.md color system — only three accent colors
const INDIGO = '#355C9A';
const AMBER = '#C88719';
const GREEN = '#2F7D68';

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [cashFlow, setCashFlow] = useState<{month: string; expected: string; actual: string}[]>([]);
  const [payTrend, setPayTrend] = useState<{month: string; amount: string}[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    api.get<DashboardSummary>('/dashboard/summary').then(setSummary).catch(e => setError(e?.message || '加载失败'));
    api.get<Project[]>('/projects').then(setProjects).catch(() => {});
    api.get<{months: {month: string; expected: string; actual: string}[]}>('/dashboard/cash-flow').then(d => setCashFlow(d.months)).catch(() => {});
    api.get<{months: {month: string; amount: string}[]}>('/dashboard/payment-trend').then(d => setPayTrend(d.months)).catch(() => {});
  }, [user]);

  if (loading) return <PageLoader />;
  if (!user) return <div className="p-8 text-slate-500">加载中...</div>;

  // Design.md §A: 4 compact metric cards
  const cards = summary ? [
    { label: '合同总额', value: formatMoney(summary.total_contract_amount), href: '/reports?report=project-summary', color: INDIGO },
    { label: '累计批准请款', value: formatMoney(summary.approved_total), href: '/reports?report=uninvoiced', color: INDIGO },
    { label: '已收款', value: formatMoney(summary.collected_total), href: '/reports?report=collection-variances', color: GREEN },
    { label: '待处理事项', value: (summary.pending_variations + summary.pending_applications + summary.overclaim_exceptions), href: '/approvals', color: AMBER },
  ] : [];

  // Design.md §B: contract-claim-invoice-collect funnel bar
  const funnelData = summary ? [
    { name: '合同', value: parseFloat(summary.total_contract_amount) || 0, fill: INDIGO },
    { name: '请款', value: parseFloat(summary.approved_total) || 0, fill: AMBER },
    { name: '开票', value: parseFloat(summary.invoiced_total) || 0, fill: INDIGO },
    { name: '收款', value: parseFloat(summary.collected_total) || 0, fill: GREEN },
  ] : [];

  // Design.md §D: cash flow — 松绿 bars = actual, 靛蓝 line = expected, 琥珀 = overdue
  const cashFlowData = cashFlow.map(m => ({
    month: m.month,
    '实际收款': parseFloat(m.actual) || 0,
    '预期收入': parseFloat(m.expected) || 0,
  }));

  return (
    <div>
      <PageHeader title="管理驾驶舱" subtitle={`单一本地用户 · ${projects.length} 个项目`} />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      {/* §A: 4 compact metric cards — no more than 2 rows */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {cards.map((c, i) => (
          <Link key={i} href={c.href}>
            <div className="bg-white border border-slate-200 rounded-lg p-4 hover:border-slate-400 transition-colors cursor-pointer">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-slate-500 font-medium">{c.label}</span>
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: c.color }} />
              </div>
              <p className="text-xl font-semibold text-slate-800 tabular-nums">{c.value}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* §B: 资金进度 funnel + per-project + §C: 待办 risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Funnel bar */}
        <Card>
          <CardHeader title="资金进度：合同 → 请款 → 开票 → 收款" />
          <div className="card-body" style={{ height: 280 }}>
            {funnelData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={funnelData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#E6E8E7" />
                  <XAxis type="number" tickFormatter={(v) => formatMoney(v).replace(/\.\d+/, '')} tick={{ fontSize: 11, fill: '#66737F' }} />
                  <YAxis dataKey="name" type="category" tick={{ fontSize: 12, fill: '#24303A' }} width={50} />
                  <Tooltip formatter={(v: any) => formatMoney(v)} contentStyle={{ fontSize: 12 }} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={28}>
                    {funnelData.map((d, i) => (
                      <rect key={i} fill={d.fill} />
                    ))}
                  </Bar>
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="暂无资金进度数据" />
            )}
          </div>
        </Card>

        {/* §C: 待办与风险清单 */}
        <Card>
          <CardHeader title="待办与风险" subtitle="点击进入对应处理页" />
          <div className="card-body">
            {summary && (summary.pending_variations + summary.pending_applications + summary.overclaim_exceptions) === 0 ? (
              <p className="text-sm text-slate-400">当前无待处理事项</p>
            ) : (
              <ul className="space-y-2">
                {summary && summary.pending_variations > 0 && (
                  <li>
                    <Link href="/approvals?resource_type=variation" className="flex items-center justify-between text-sm hover:bg-slate-50 p-2 rounded">
                      <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: AMBER }} />
                        待批准变更
                      </span>
                      <span className="tabular-nums font-medium text-slate-600">{summary.pending_variations}</span>
                    </Link>
                  </li>
                )}
                {summary && summary.pending_applications > 0 && (
                  <li>
                    <Link href="/approvals?resource_type=payment_application_pm" className="flex items-center justify-between text-sm hover:bg-slate-50 p-2 rounded">
                      <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: AMBER }} />
                        待审核请款
                      </span>
                      <span className="tabular-nums font-medium text-slate-600">{summary.pending_applications}</span>
                    </Link>
                  </li>
                )}
                {summary && summary.overclaim_exceptions > 0 && (
                  <li>
                    <Link href="/approvals?resource_type=overclaim" className="flex items-center justify-between text-sm hover:bg-slate-50 p-2 rounded">
                      <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: '#9C5D08' }} />
                        超合同异常
                      </span>
                      <span className="tabular-nums font-medium text-slate-600">{summary.overclaim_exceptions}</span>
                    </Link>
                  </li>
                )}
                {summary && summary.invoice_outstanding_total !== '0' && parseFloat(summary.invoice_outstanding_total) > 0 && (
                  <li>
                    <Link href="/reports?report=invoice-outstanding" className="flex items-center justify-between text-sm hover:bg-slate-50 p-2 rounded">
                      <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: AMBER }} />
                        发票未收款余额
                      </span>
                      <span className="tabular-nums font-medium text-slate-600">{formatMoney(summary.invoice_outstanding_total)}</span>
                    </Link>
                  </li>
                )}
              </ul>
            )}
          </div>
        </Card>
      </div>

      {/* §D: 现金流趋势主图 */}
      {cashFlowData.length > 0 && (
        <Card>
          <CardHeader title="现金流趋势" subtitle="松绿 = 实际收款 · 靛蓝 = 预期收入 · 最近6月+未来6月" />
          <div className="card-body" style={{ height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={cashFlowData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E6E8E7" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#66737F' }} />
                <YAxis tickFormatter={(v) => formatMoney(v).replace(/\.\d+/, '')} tick={{ fontSize: 11, fill: '#66737F' }} />
                <Tooltip formatter={(v: any) => formatMoney(v)} contentStyle={{ fontSize: 12, border: '1px solid #E6E8E7' }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                {/* 松绿 bars = actual */}
                <Bar dataKey="实际收款" fill={GREEN} radius={[3, 3, 0, 0]} barSize={20} />
                {/* 靛蓝 line = expected */}
                <Line type="monotone" dataKey="预期收入" stroke={INDIGO} strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* §E: 项目经营表 */}
      <Card>
        <CardHeader title="项目经营表" subtitle="点击项目编号进入详情 · 金额点击进入对应明细" />
        <div className="overflow-x-auto">
          {projects.length === 0 ? (
            <EmptyState message="暂无项目数据" />
          ) : (
            <table className="data-table text-sm">
              <thead>
                <tr>
                  <th>项目编号</th>
                  <th>工程名称</th>
                  <th>状态</th>
                  <th className="text-right">合同金额</th>
                  <th className="text-right">累计请款</th>
                  <th className="text-right">保留款</th>
                </tr>
              </thead>
              <tbody>
                {projects.map(p => {
                  const pp = summary?.per_project.find(x => x.project_id === p.id);
                  return (
                    <tr key={p.id}>
                      <td>
                        <Link href={`/projects/${p.id}`} className="hover:underline" style={{ color: INDIGO }}>
                          {p.internal_project_code}
                        </Link>
                      </td>
                      <td>{p.project_name}</td>
                      <td><StatusBadge status={p.status} /></td>
                      <td className="num">{pp ? formatMoney(pp.contract_amount) : '—'}</td>
                      <td className="num">{pp ? formatMoney(pp.approved_total) : '—'}</td>
                      <td className="num">{pp ? formatMoney(pp.retention_held) : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      {/* §F: 最近动态 */}
      {summary && summary.recent_audit.length > 0 && (
        <Card>
          <CardHeader title="最近动态" subtitle="最近5条审计事件" />
          <div className="card-body">
            <ul className="space-y-2">
              {summary.recent_audit.slice(0, 5).map(a => (
                <li key={a.id} className="text-sm text-slate-600 flex justify-between border-b border-slate-100 pb-1">
                  <span>{a.action}</span>
                  <span className="text-xs text-slate-400 tabular-nums">
                    {a.created_at?.substring(0, 16).replace('T', ' ') || '—'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      )}
    </div>
  );
}
