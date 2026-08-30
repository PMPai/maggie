'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { PageHeader, Card, CardHeader, EmptyState, formatMoney } from '@/components/ui/common';
import { PageLoader } from '@/components/ui/PageLoader';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

interface WeeklyItem {
  id: string;
  receipt_no: string;
  amount: number;
  status: string;
  date: string;
}
interface Week {
  week_key: string;
  week_start: string;
  week_end: string;
  items: WeeklyItem[];
  total: number;
}

export default function WeeklyPlanPage() {
  const { user, loading } = useAuth();
  const [projectId, setProjectId] = useState('');
  const [weeks, setWeeks] = useState<Week[]>([]);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);

  const fetchPlan = async (pid: string) => {
    if (!pid) return;
    setError('');
    try {
      const res = await api.get<{ weeks: Week[] }>(`/collections/projects/${pid}/weekly-receivables`);
      setWeeks(res.weeks || []);
    } catch (e: any) {
      setError(e?.message || '加载失败');
    } finally {
      setLoaded(true);
    }
  };

  if (loading) return <PageLoader />;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <PageHeader title="每周应收款计划" subtitle="依付款时间排程的收款计划，按周分组" />

      <div className="mb-4 flex items-center gap-3">
        <label className="text-sm text-slate-600">项目 ID:</label>
        <input
          type="text"
          value={projectId}
          onChange={e => setProjectId(e.target.value)}
          placeholder="输入项目 UUID"
          className="input-field text-sm flex-1 max-w-md"
        />
        <button onClick={() => fetchPlan(projectId)} className="btn-primary text-sm" disabled={!projectId}>
          查询
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      {loaded && weeks.length === 0 && !error && (
        <EmptyState message="该项目暂无待收款项（PLANNED/CONFIRMED）" />
      )}

      <div className="space-y-4">
        {weeks.map(week => (
          <Card key={week.week_key}>
            <CardHeader
              title={`${week.week_key}`}
              subtitle={`${week.week_start} ~ ${week.week_end} · 合计 ${formatMoney(week.total)}`}
            />
            <div className="overflow-x-auto">
              <table className="data-table text-xs">
                <thead>
                  <tr>
                    <th>收款单号</th>
                    <th>预定日期</th>
                    <th className="text-right">金额</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {week.items.map(item => (
                    <tr key={item.id}>
                      <td className="font-mono">{item.receipt_no}</td>
                      <td>{item.date}</td>
                      <td className="num">{formatMoney(item.amount)}</td>
                      <td>
                        <span className={`badge ${
                          item.status === 'PLANNED' ? 'badge-blue' :
                          item.status === 'CONFIRMED' ? 'badge-amber' :
                          'badge-green'
                        }`}>
                          {item.status === 'PLANNED' ? '已排程' :
                           item.status === 'CONFIRMED' ? '已确认' : '已收款'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
      </div>
    </main>
  );
}
