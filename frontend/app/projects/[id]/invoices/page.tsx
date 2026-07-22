'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Invoice, Collection } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';

export default function InvoicesPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      api.get<Invoice[]>(`/invoices?project_id=${projectId}`).catch(() => [] as Invoice[]),
      api.get<Collection[]>(`/collections?project_id=${projectId}`).catch(() => [] as Collection[]),
    ]).then(([inv, col]) => { setInvoices(inv); setCollections(col); });
  }, [user, projectId]);

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">请先登录</div>;

  const num = (v: number) => Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });

  const totalInvoiced = invoices.reduce((s, i) => s + Number(i.amount_inc_tax || 0), 0);
  const totalCollected = collections.reduce((s, c) => s + Number(c.amount_received || 0), 0);
  const variance = totalInvoiced - totalCollected;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <div className="mb-4">
        <Link href={`/projects/${projectId}`} className="text-blue-600 hover:underline">← 返回项目</Link>
      </div>
      <h1 className="text-2xl font-bold mb-6">发票与收款</h1>

      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">已开票金额(含税)</p>
          <p className="text-xl font-bold">{num(totalInvoiced)}</p>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">已收款金额</p>
          <p className="text-xl font-bold text-green-700">{num(totalCollected)}</p>
        </div>
        <div className="rounded-lg bg-white p-4 shadow">
          <p className="text-xs text-gray-500">差异(应收-已收)</p>
          <p className="text-xl font-bold text-red-600">{num(variance)}</p>
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-2">发票</h2>
      <div className="rounded-lg bg-white shadow overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">发票编号</th>
              <th className="px-4 py-2 text-left">类型</th>
              <th className="px-4 py-2 text-left">开票日期</th>
              <th className="px-4 py-2 text-right">未税</th>
              <th className="px-4 py-2 text-right">税额</th>
              <th className="px-4 py-2 text-right">含税</th>
              <th className="px-4 py-2 text-left">状态</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map(i => (
              <tr key={i.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2">{i.invoice_no}</td>
                <td className="px-4 py-2">{i.invoice_type}</td>
                <td className="px-4 py-2">{i.issue_date}</td>
                <td className="px-4 py-2 text-right">{num(i.amount_ex_tax)}</td>
                <td className="px-4 py-2 text-right">{num(i.tax_amount)}</td>
                <td className="px-4 py-2 text-right">{num(i.amount_inc_tax)}</td>
                <td className="px-4 py-2">{i.status}</td>
              </tr>
            ))}
            {invoices.length === 0 && <tr><td colSpan={7} className="px-4 py-4 text-center text-gray-500">暂无发票</td></tr>}
          </tbody>
        </table>
      </div>

      <h2 className="text-lg font-semibold mb-2">收款</h2>
      <div className="rounded-lg bg-white shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left">收款编号</th>
              <th className="px-4 py-2 text-left">收款日期</th>
              <th className="px-4 py-2 text-right">金额</th>
              <th className="px-4 py-2 text-left">付款方式</th>
              <th className="px-4 py-2 text-left">状态</th>
            </tr>
          </thead>
          <tbody>
            {collections.map(c => (
              <tr key={c.id} className="border-t hover:bg-gray-50">
                <td className="px-4 py-2">{c.receipt_no}</td>
                <td className="px-4 py-2">{c.receipt_date}</td>
                <td className="px-4 py-2 text-right">{num(c.amount_received)}</td>
                <td className="px-4 py-2">{c.payment_method}</td>
                <td className="px-4 py-2">{c.status}</td>
              </tr>
            ))}
            {collections.length === 0 && <tr><td colSpan={5} className="px-4 py-4 text-center text-gray-500">暂无收款记录</td></tr>}
          </tbody>
        </table>
      </div>
    </main>
  );
}
