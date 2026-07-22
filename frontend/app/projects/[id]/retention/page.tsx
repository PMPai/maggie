'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Contract, RetentionEntry } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';

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

  const num = (v: number) => Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const typeLabel: Record<string, string> = { HOLD: '保留', RELEASE: '释放', ADJUSTMENT: '调整', REVERSAL: '冲回' };

  let running = 0;
  const rows = entries.map(e => {
    const delta = e.entry_type === 'HOLD' ? -e.amount : e.amount;
    running += delta;
    return { ...e, delta, balance: running };
  });

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-blue-600 hover:underline">← 返回项目</Link>
      </div>
      <h1 className="text-2xl font-bold mb-6">保留款台账</h1>

      {error && <p className="mb-4 text-red-600">加载失败：{error}</p>}

      <div className="mb-4 rounded-lg bg-blue-50 p-4">
        <p className="text-sm text-gray-600">当前保留款余额</p>
        <p className="text-2xl font-bold text-blue-700">{num(running)}</p>
      </div>

      <div className="rounded-lg bg-white shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">类型</th>
              <th className="px-4 py-2 text-right">金额</th>
              <th className="px-4 py-2 text-right">变动</th>
              <th className="px-4 py-2 text-right">累计余额</th>
              <th className="px-4 py-2 text-left">说明</th>
              <th className="px-4 py-2 text-left">日期</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(e => (
              <tr key={e.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2">{typeLabel[e.entry_type] || e.entry_type}</td>
                <td className="px-4 py-2 text-right">{num(e.amount)}</td>
                <td className="px-4 py-2 text-right">{e.delta >= 0 ? '+' : ''}{num(e.delta)}</td>
                <td className="px-4 py-2 text-right font-medium">{num(e.balance)}</td>
                <td className="px-4 py-2">{e.description}</td>
                <td className="px-4 py-2">{e.created_at.slice(0, 10)}</td>
              </tr>
            ))}
            {entries.length === 0 && <tr><td colSpan={6} className="px-4 py-4 text-center text-gray-500">暂无保留款记录</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
