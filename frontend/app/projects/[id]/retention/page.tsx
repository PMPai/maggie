'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Contract, RetentionEntry } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatCard, EmptyState, formatMoney } from '@/components/ui/common';

const TYPE_BADGE: Record<string, string> = {
  HOLD: 'badge-orange',
  RELEASE: 'badge-green',
  ADJUSTMENT: 'badge-blue',
  REVERSAL: 'badge-red',
};
const TYPE_LABEL: Record<string, string> = {
  HOLD: '保留',
  RELEASE: '释放',
  ADJUSTMENT: '调整',
  REVERSAL: '冲回',
};

export default function RetentionPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [entries, setEntries] = useState<RetentionEntry[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const contracts = await api.get<Contract[]>(`/contracts?project_id=${projectId}`);
        if (contracts.length === 0) { setEntries([]); return; }
        const all: RetentionEntry[] = [];
        for (const c of contracts) {
          try {
            const e = await api.get<RetentionEntry[]>(`/retention-entries?contract_id=${c.id}`);
            all.push(...e);
          } catch {}
        }
        all.sort((a, b) => a.created_at.localeCompare(b.created_at));
        setEntries(all);
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, [user, projectId]);

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  let running = 0;
  const rows = entries.map(e => {
    const delta = e.entry_type === 'HOLD' ? -e.amount : e.amount;
    running += delta;
    return { ...e, delta, balance: running };
  });

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="保留款台账" />

      {error && <p className="mb-4 text-sm text-red-600">加载失败：{error}</p>}

      <div className="mb-6">
        <StatCard
          label="当前保留款余额"
          value={formatMoney(running)}
          color="orange"
          icon="M3 10h18M7 15h1m4 0h1m4 0h1M3 5h18a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z"
        />
      </div>

      <Card>
        <CardHeader title="保留款记录" />
        <div className="card-body">
          {entries.length === 0 ? (
            <EmptyState message="暂无保留款记录" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th className="text-right">金额</th>
                  <th className="text-right">变动</th>
                  <th className="text-right">累计余额</th>
                  <th>说明</th>
                  <th>日期</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(e => (
                  <tr key={e.id}>
                    <td>
                      <span className={`badge ${TYPE_BADGE[e.entry_type] || 'badge-gray'}`}>
                        {TYPE_LABEL[e.entry_type] || e.entry_type}
                      </span>
                    </td>
                    <td className="num">{formatMoney(e.amount)}</td>
                    <td className="num">{e.delta >= 0 ? '+' : ''}{formatMoney(e.delta)}</td>
                    <td className="num font-semibold">{formatMoney(e.balance)}</td>
                    <td>{e.description}</td>
                    <td>{e.created_at.slice(0, 10)}</td>
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
