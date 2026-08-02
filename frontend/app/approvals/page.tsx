'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import Link from 'next/link';
import type { PendingApproval } from '@/lib/types';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge, formatMoney } from '@/components/ui/common';
import { FilterBar } from '@/components/ui/FilterBar';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';

const TYPE_LABELS: Record<string, string> = {
  variation: '变更',
  contract_version: '合同版本',
  payment_application_pm: '请款(项目)',
  payment_application_finance: '请款(财务)',
  deduction: '扣款',
  item_mapping: '项目映射',
  matching_review: '匹配审核',
  collection_variance: '收款差异',
  overclaim: '超量异常',
};

const ROLE_OPTIONS = [
  { value: 'PROJECT_MANAGER', label: '项目负责人' },
  { value: 'FINANCE_REVIEWER', label: '财务复核' },
  { value: 'CONTRACT_ADMIN', label: '合同管理员' },
  { value: 'COST_REVIEWER', label: '造价复核' },
  { value: 'FINANCE_USER', label: '财务人员' },
];

const ROLE_LABELS: Record<string, string> = Object.fromEntries(ROLE_OPTIONS.map(r => [r.value, r.label]));

// approve_url/reject_url from backend start with "/api/..."; api.post prepends "/api" already,
// so strip the leading "/api" to avoid a double "/api/api/..." prefix.
function stripApiPrefix(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith('/api/')) return url.slice('/api'.length);
  if (url.startsWith('/api')) return url.slice('/api'.length);
  return url;
}

export default function ApprovalsPage() {
  const { user, loading } = useAuth();
  const [items, setItems] = useState<PendingApproval[]>([]);
  const [error, setError] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterRole, setFilterRole] = useState('');
  const [confirm, setConfirm] = useState<{ kind: 'approve' | 'reject'; item: PendingApproval } | null>(null);

  const load = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (filterType) params.resource_type = filterType;
      if (filterRole) params.waiting_for_role = filterRole;
      const data = await api.get<{ items: PendingApproval[] }>(
        Object.keys(params).length === 0
          ? '/approvals/pending'
          : '/approvals/pending?' + new URLSearchParams(params).toString(),
      );
      setItems(data.items);
      setError('');
    } catch (e: any) {
      setError(e?.message || '加载失败');
    }
  }, [filterType, filterRole]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const doAction = async (reason?: string) => {
    if (!confirm) return;
    const { kind, item } = confirm;
    try {
      if (kind === 'approve') {
        const url = stripApiPrefix(item.approve_url);
        if (url) await api.post(url);
      } else {
        const url = stripApiPrefix(item.reject_url);
        if (url) await api.post(url, reason ? { reason } : undefined);
      }
      setItems(prev => prev.filter(i => i !== item));
      setError('');
    } catch (e: any) {
      setError(e?.message || '操作失败');
    }
    setConfirm(null);
  };

  if (loading) return <PageLoader />;

  const userRoles: string[] = user?.roles || [];

  return (
    <>
      <PageHeader title="审批与异常中心" subtitle="集中处理合同/请款/映射/扣款/差异等审批事项" />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <FilterBar
        filters={[
          {
            label: '类型',
            value: filterType,
            options: Object.entries(TYPE_LABELS).map(([v, l]) => ({ value: v, label: l })),
            onChange: setFilterType,
          },
          { label: '等待角色', value: filterRole, options: ROLE_OPTIONS, onChange: setFilterRole },
        ]}
      />
      <Card>
        <CardHeader
          title="待处理事项"
          actions={
            <button onClick={load} className="btn-secondary text-sm px-3 py-1">刷新</button>
          }
        />
        <div className="overflow-x-auto scrollbar-thin">
          {items.length === 0 ? (
            <EmptyState message="暂无待处理事项" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th>描述</th>
                  <th>项目</th>
                  <th className="text-right">金额</th>
                  <th>等待角色</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => {
                  const canApprove =
                    userRoles.includes(it.waiting_for_role) ||
                    userRoles.includes('SYSTEM_ADMIN');
                  return (
                    <tr key={`${it.resource_type}:${it.resource_id}`}>
                      <td>
                        <StatusBadge status={it.resource_type} />
                      </td>
                      <td className="text-sm">{it.description}</td>
                      <td className="text-sm">{it.project_code || '—'}</td>
                      <td className="num">{it.amount ? formatMoney(it.amount) : '—'}</td>
                      <td className="text-sm">{ROLE_LABELS[it.waiting_for_role] || it.waiting_for_role}</td>
                      <td className="text-sm text-slate-500">
                        {it.created_at ? it.created_at.substring(0, 16).replace('T', ' ') : '—'}
                      </td>
                      <td>
                        {it.approve_url && (
                          <button
                            disabled={!canApprove}
                            onClick={() => setConfirm({ kind: 'approve', item: it })}
                            className="text-green-600 text-sm hover:underline disabled:opacity-30 mr-2"
                          >
                            批准
                          </button>
                        )}
                        {it.reject_url && (
                          <button
                            disabled={!canApprove}
                            onClick={() => setConfirm({ kind: 'reject', item: it })}
                            className="text-red-600 text-sm hover:underline disabled:opacity-30 mr-2"
                          >
                            拒绝
                          </button>
                        )}
                        {it.detail_url && (
                          <Link href={it.detail_url} className="text-blue-600 text-sm hover:underline">
                            查看
                          </Link>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Card>
      {confirm && (
        <ConfirmDialog
          title={confirm.kind === 'approve' ? '确认批准' : '确认拒绝'}
          message={
            confirm.kind === 'approve'
              ? `将批准: ${confirm.item.description}`
              : `将拒绝: ${confirm.item.description}`
          }
          requireReason={confirm.kind === 'reject'}
          confirmLabel={confirm.kind === 'approve' ? '批准' : '拒绝'}
          onConfirm={(reason) => doAction(reason)}
          onCancel={() => setConfirm(null)}
        />
      )}
    </>
  );
}
