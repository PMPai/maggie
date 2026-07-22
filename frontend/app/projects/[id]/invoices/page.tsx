'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Invoice, Collection } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, StatusBadge, EmptyState, formatMoney } from '@/components/ui/common';

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

  const totalInvoiced = invoices.reduce((s, i) => s + Number(i.amount_inc_tax || 0), 0);
  const totalCollected = collections.reduce((s, c) => s + Number(c.amount_received || 0), 0);
  const variance = totalInvoiced - totalCollected;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="发票与收款" />

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card>
          <CardHeader title="发票" />
          <div className="card-body">
            {invoices.length === 0 ? (
              <EmptyState message="暂无发票" />
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>发票编号</th>
                    <th>类型</th>
                    <th>开票日期</th>
                    <th className="text-right">未税</th>
                    <th className="text-right">税额</th>
                    <th className="text-right">含税</th>
                    <th>来源</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map(i => (
                    <tr key={i.id}>
                      <td className="font-mono">{i.invoice_no}</td>
                      <td>{i.invoice_type}</td>
                      <td>{i.issue_date}</td>
                      <td className="num">{formatMoney(i.amount_ex_tax)}</td>
                      <td className="num">{formatMoney(i.tax_amount)}</td>
                      <td className="num">{formatMoney(i.amount_inc_tax)}</td>
                      <td>{i.source}</td>
                      <td><StatusBadge status={i.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="收款" />
          <div className="card-body">
            {collections.length === 0 ? (
              <EmptyState message="暂无收款记录" />
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>收款编号</th>
                    <th>收款日期</th>
                    <th className="text-right">收款金额</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {collections.map(c => (
                    <tr key={c.id}>
                      <td className="font-mono">{c.receipt_no}</td>
                      <td>{c.receipt_date}</td>
                      <td className="num">{formatMoney(c.amount_received)}</td>
                      <td><StatusBadge status={c.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="差异" />
        <div className="card-body">
          <table className="data-table">
            <thead>
              <tr>
                <th>项目</th>
                <th className="text-right">金额</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>已开票金额(含税)</td>
                <td className="num">{formatMoney(totalInvoiced)}</td>
              </tr>
              <tr>
                <td>已收款金额</td>
                <td className="num">{formatMoney(totalCollected)}</td>
              </tr>
              <tr>
                <td className="font-semibold">差异(应收 - 已收)</td>
                <td className={`num font-semibold ${variance > 0 ? 'text-orange-600' : 'text-emerald-600'}`}>
                  {formatMoney(variance)}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </main>
  );
}
