'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { DashboardSummary, Project } from '@/lib/types';
import Link from 'next/link';
import { PageHeader, StatCard, Card, CardHeader, StatusBadge, EmptyState, formatMoney } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    api
      .get<DashboardSummary>('/dashboard/summary')
      .then(setSummary)
      .catch(e => setError(e?.message || '加载失败'));
    api
      .get<Project[]>('/projects')
      .then(setProjects)
      .catch(() => {});
  }, [user]);

  if (loading) return <PageLoader />;
  if (!user) return <div className="p-8 text-slate-500">请先登录</div>;

  const cards = summary
    ? [
        { label: '项目数', value: projects.length, href: '/projects', color: 'slate' as const },
        { label: '合同总金额', value: formatMoney(summary.total_contract_amount), href: '/reports?report=project-summary', color: 'blue' as const },
        { label: '累计完成金额', value: formatMoney(summary.gross_completed_total), href: '/reports?report=project-summary', color: 'blue' as const },
        { label: '累计批准请款', value: formatMoney(summary.approved_total), href: '/reports?report=uninvoiced', color: 'green' as const },
        { label: '已开票', value: formatMoney(summary.invoiced_total), href: '/reports?report=invoice-outstanding', color: 'green' as const },
        { label: '已收款', value: formatMoney(summary.collected_total), href: '/reports?report=collection-variances', color: 'green' as const },
        { label: '未释放保留款', value: formatMoney(summary.retention_held_total), href: '/reports?report=retention-balances', color: 'orange' as const },
        { label: '已开票未收款', value: formatMoney(summary.invoice_outstanding_total), href: '/reports?report=invoice-outstanding', color: 'orange' as const },
        { label: '待批准变更', value: summary.pending_variations, href: '/approvals?resource_type=variation', color: 'orange' as const },
        { label: '待审核请款', value: summary.pending_applications, href: '/approvals?resource_type=payment_application_pm', color: 'orange' as const },
        { label: '待审核映射', value: summary.pending_mappings, href: '/approvals?resource_type=item_mapping', color: 'orange' as const },
        { label: '超合同数量异常', value: summary.overclaim_exceptions, href: '/approvals?resource_type=overclaim', color: 'red' as const },
        { label: '合同金额版本差异', value: summary.contract_version_diffs, href: '/reports?report=contract-item-balances', color: 'red' as const },
      ]
    : [];

  return (
    <div>
      <PageHeader
        title="管理驾驶舱"
        subtitle={`当前用户：${user.display_name}（${user.roles.join(', ')}）`}
      />

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
        {cards.map((c, i) => (
          <Link key={i} href={c.href}>
            <StatCard
              label={c.label}
              value={c.value}
              icon="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              color={c.color}
            />
          </Link>
        ))}
      </div>

      <Card>
        <CardHeader title="项目列表" />
        <div className="overflow-x-auto">
          {projects.length === 0 ? (
            <EmptyState message="暂无项目数据" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>项目编号</th>
                  <th>工程名称</th>
                  <th>状态</th>
                  <th className="text-right">合同金额</th>
                  <th className="text-right">累计请款</th>
                </tr>
              </thead>
              <tbody>
                {projects.map(p => {
                  const pp = summary?.per_project.find(x => x.project_id === p.id);
                  return (
                    <tr key={p.id}>
                      <td>
                        <Link href={`/projects/${p.id}`} className="text-blue-600 hover:underline">
                          {p.internal_project_code}
                        </Link>
                      </td>
                      <td>{p.project_name}</td>
                      <td><StatusBadge status={p.status} /></td>
                      <td className="num">{pp ? formatMoney(pp.contract_amount) : '—'}</td>
                      <td className="num">{pp ? formatMoney(pp.approved_total) : '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Card>

      {summary && summary.recent_audit.length > 0 && (
        <Card>
          <CardHeader title="最近审计" />
          <div className="card-body">
            <ul className="space-y-2">
              {summary.recent_audit.map(a => (
                <li key={a.id} className="text-sm text-slate-600 flex justify-between">
                  <span>{a.action}</span>
                  <span className="text-xs text-slate-400">
                    {a.created_at?.substring(0, 16).replace('T', ' ')}
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
