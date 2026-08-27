'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import Link from 'next/link';
import type { Application } from '@/lib/types';
import { PageHeader, Card, CardHeader, EmptyState, StatusBadge, formatMoney } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

export default function MyApplicationsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (authLoading || !user) return;
    api.get<Application[]>('/payment-applications?my=true').then(setApps).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [user, authLoading]);

  if (authLoading || loading) return <PageLoader />;

  return (
    <div className="max-w-6xl mx-auto py-6">
      <PageHeader title="我的请款" subtitle="查看您提交的所有请款申请及其审批状态" />

      {error && <ErrorBanner message={error} />}

      <Card>
        <CardHeader
          title="请款列表"
          actions={<Link href="/applications/new" className="btn-primary">新建请款</Link>}
        />
        <div className="card-body">
          {apps.length === 0 ? (
            <EmptyState message="暂无请款记录" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>请款编号</th>
                  <th>期数</th>
                  <th>状态</th>
                  <th className="text-right">请款金额</th>
                  <th className="text-right">含税金额</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {apps.map(a => (
                  <tr key={a.id}>
                    <td>
                      <Link href={`/applications/${a.id}`} className="text-orange-600 hover:underline">
                        {a.application_no}
                      </Link>
                    </td>
                    <td>第{a.period_no}期</td>
                    <td><StatusBadge status={a.status} /></td>
                    <td className="num">{formatMoney(a.gross_completed_amount)}</td>
                    <td className="num">{formatMoney(a.invoice_amount)}</td>
                    <td>
                      <Link href={`/applications/${a.id}`} className="text-blue-600 hover:underline">
                        查看详情
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
