'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Deduction } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';

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

  const num = (v: number) => Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-blue-600 hover:underline">← 返回项目</Link>
      </div>
      <h1 className="text-2xl font-bold mb-6">扣款台账</h1>

      <div className="rounded-lg bg-white shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">扣款编号</th>
              <th className="px-4 py-2 text-left">类型</th>
              <th className="px-4 py-2 text-left">描述</th>
              <th className="px-4 py-2 text-right">金额</th>
              <th className="px-4 py-2 text-left">税务处理</th>
              <th className="px-4 py-2 text-right">税额</th>
              <th className="px-4 py-2 text-left">状态</th>
              <th className="px-4 py-2 text-left">生效日期</th>
            </tr>
          </thead>
          <tbody>
            {deductions.map(d => (
              <tr key={d.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2">{d.deduction_no}</td>
                <td className="px-4 py-2">{d.deduction_type}</td>
                <td className="px-4 py-2">{d.description}</td>
                <td className="px-4 py-2 text-right">{num(d.amount)}</td>
                <td className="px-4 py-2">{d.tax_treatment}</td>
                <td className="px-4 py-2 text-right">{num(d.tax_amount)}</td>
                <td className="px-4 py-2">{d.status}</td>
                <td className="px-4 py-2">{d.effective_date}</td>
              </tr>
            ))}
            {deductions.length === 0 && <tr><td colSpan={8} className="px-4 py-4 text-center text-gray-500">暂无扣款记录</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
