'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Deduction } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatMoney } from '@/components/ui/common';

const TYPE_LABEL: Record<string, string> = {
  PENALTY: '罚款',
  BACK_CHARGE: '扣回',
  RETENTION: '保留款扣减',
  OTHER: '其他',
};

export default function DeductionsPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [deductions, setDeductions] = useState<Deduction[]>([]);

  useEffect(() => {
    if (!user) return;
    api.get<Deduction[]>(`/deductions?project_id=${projectId}`).then(setDeductions).catch(() => setDeductions([]));
  }, [user, projectId]);

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="扣款台账" />

      <Card>
        <CardHeader title="扣款记录" />
        <div className="card-body">
          {deductions.length === 0 ? (
            <EmptyState message="暂无扣款记录" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>扣款编号</th>
                  <th>类型</th>
                  <th>描述</th>
                  <th className="text-right">金额</th>
                  <th>税务处理</th>
                  <th>状态</th>
                  <th>生效日期</th>
                </tr>
              </thead>
              <tbody>
                {deductions.map(d => (
                  <tr key={d.id}>
                    <td className="font-mono">{d.deduction_no}</td>
                    <td>{TYPE_LABEL[d.deduction_type] || d.deduction_type}</td>
                    <td>{d.description}</td>
                    <td className="num">{formatMoney(d.amount)}</td>
                    <td>{d.tax_treatment}</td>
                    <td><StatusBadge status={d.status} /></td>
                    <td>{d.effective_date}</td>
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
