'use client';
import { useAuth } from '@/hooks/useAuth';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { Invoice, Collection, Application, Contract } from '@/lib/types';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader, Card, CardHeader, EmptyState, formatMoney } from '@/components/ui/common';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

const INDIGO = '#355C9A';
const AMBER = '#C88719';
const GREEN = '#2F7D68';

function invoiceStatusBadge(status: string) {
  const map: Record<string, { label: string; bg: string; text: string }> = {
    PLANNED: { label: '已排程', bg: '#EAF0FA', text: INDIGO },
    ISSUED: { label: '已开票', bg: '#FFF4DB', text: AMBER },
    SENT: { label: '已寄送', bg: '#E7F3EE', text: GREEN },
    PAID: { label: '已结清', bg: '#E7F3EE', text: GREEN },
    VOID: { label: '已作废', bg: '#E6E8E7', text: '#66737F' },
  };
  const s = map[status] || { label: status, bg: '#E6E8E7', text: '#66737F' };
  return <span className="px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: s.bg, color: s.text }}>{s.label}</span>;
}

function collectionStatusBadge(status: string) {
  const map: Record<string, { label: string; bg: string; text: string }> = {
    PLANNED: { label: '已排程', bg: '#EAF0FA', text: INDIGO },
    CONFIRMED: { label: '已确认', bg: '#FFF4DB', text: AMBER },
    RECEIVED: { label: '已收款', bg: '#E7F3EE', text: GREEN },
    CANCELLED: { label: '已取消', bg: '#E6E8E7', text: '#66737F' },
  };
  const s = map[status] || { label: status, bg: '#E6E8E7', text: '#66737F' };
  return <span className="px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: s.bg, color: s.text }}>{s.label}</span>;
}

export default function InvoicesPage() {
  const { user, loading } = useAuth();
  const params = useParams();
  const projectId = params.id as string;
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [postedApps, setPostedApps] = useState<Application[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedAppId, setSelectedAppId] = useState('');
  const [invoiceNo, setInvoiceNo] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = () => {
    Promise.all([
      api.get<Invoice[]>(`/invoices?project_id=${projectId}`).catch(() => [] as Invoice[]),
      api.get<Collection[]>(`/collections?project_id=${projectId}`).catch(() => [] as Collection[]),
      api.get<Application[]>(`/payment-applications?project_id=${projectId}`).catch(() => [] as Application[]),
      api.get<Contract[]>(`/contracts?project_id=${projectId}`).catch(() => [] as Contract[]),
    ]).then(([inv, col, apps, ctr]) => {
      setInvoices(inv); setCollections(col);
      setPostedApps(apps.filter(a => a.status === 'POSTED' || a.status === 'GENERATED' || a.status === 'SENT'));
      setContracts(ctr);
    });
  };

  useEffect(() => { if (user) load(); }, [user, projectId]);

  const createFromApp = async () => {
    if (!selectedAppId || !invoiceNo) { setError('请选择请款单并输入发票编号'); return; }
    setBusy(true); setError('');
    try {
      const app = postedApps.find(a => a.id === selectedAppId);
      if (!app) throw new Error('请款单未找到');
      const contract = contracts.find(c => c.id === app.contract_id);
      if (!contract) throw new Error('合同未找到');
      await api.post('/invoices', {
        project_id: projectId,
        contract_id: app.contract_id,
        invoice_no: invoiceNo,
        amount_ex_tax: app.taxable_amount,
        tax_amount: app.tax_amount,
        amount_inc_tax: app.invoice_amount,
        tax_rate: contract.tax_rate,
        source: 'APPLICATION',
      });
      setShowCreate(false); setSelectedAppId(''); setInvoiceNo('');
      load();
    } catch (e: any) { setError(e?.message || '创建失败'); }
    finally { setBusy(false); }
  };

  const handleInvoiceAction = async (id: string, action: 'issue' | 'send') => {
    setBusy(true); setError('');
    try {
      if (action === 'issue') {
        await api.post(`/invoices/${id}/issue`);
      } else {
        await api.post(`/invoices/${id}/send`);
      }
      load();
    } catch (e: any) { setError(e?.message || '操作失败'); }
    finally { setBusy(false); }
  };

  if (loading) return <div className="p-8">加载中...</div>;
  if (!user) return <div className="p-8">加载中...</div>;

  const totalInvoiced = invoices.reduce((s, i) => s + Number(i.amount_inc_tax || 0), 0);
  const totalCollected = collections.filter(c => c.status === 'RECEIVED').reduce((s, c) => s + Number(c.amount_received || 0), 0);
  const variance = totalInvoiced - totalCollected;

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <Link href={`/projects/${projectId}`} className="text-sm text-slate-500 hover:text-slate-700">← 返回项目</Link>
      <PageHeader title="发票与收款" subtitle="发票状态流：已排程 → 已开票 → 已寄送" />
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      <div className="mb-4">
        <button onClick={() => setShowCreate(true)} className="btn-primary">+ 从已批准请款建发票</button>
      </div>

      {showCreate && (
        <Card className="mb-4">
          <CardHeader title="从已批准请款创建发票（PLANNED）" />
          <div className="card-body space-y-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">选择已过账请款单</label>
              <select value={selectedAppId} onChange={e => setSelectedAppId(e.target.value)} className="input-field text-sm">
                <option value="">请选择...</option>
                {postedApps.map(a => (
                  <option key={a.id} value={a.id}>{a.application_no} · 第{a.period_no}期 · 含税{formatMoney(a.invoice_amount)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">发票编号</label>
              <input type="text" value={invoiceNo} onChange={e => setInvoiceNo(e.target.value)} className="input-field text-sm" placeholder="如 INV-2026-001" />
            </div>
            <div className="flex gap-2">
              <button onClick={createFromApp} disabled={busy} className="btn-primary text-sm">{busy ? '创建中...' : '创建发票'}</button>
              <button onClick={() => setShowCreate(false)} className="btn-secondary text-sm">取消</button>
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card>
          <CardHeader title="发票" subtitle="PLANNED → ISSUED → SENT" />
          <div className="card-body">
            {invoices.length === 0 ? (
              <EmptyState message="暂无发票" />
            ) : (
              <table className="data-table text-xs">
                <thead>
                  <tr>
                    <th>发票编号</th>
                    <th>开票日期</th>
                    <th className="text-right">含税</th>
                    <th>状态</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map(i => (
                    <tr key={i.id}>
                      <td className="font-mono">{i.invoice_no}</td>
                      <td>{i.issue_date || '—'}</td>
                      <td className="num">{formatMoney(i.amount_inc_tax)}</td>
                      <td>{invoiceStatusBadge(i.status)}</td>
                      <td>
                        {i.status === 'PLANNED' && (
                          <button onClick={() => handleInvoiceAction(i.id, 'issue')} disabled={busy}
                            className="text-xs hover:underline" style={{ color: AMBER }}>开票</button>
                        )}
                        {i.status === 'ISSUED' && (
                          <button onClick={() => handleInvoiceAction(i.id, 'send')} disabled={busy}
                            className="text-xs hover:underline" style={{ color: GREEN }}>寄送</button>
                        )}
                        {(i.status === 'SENT' || i.status === 'PAID' || i.status === 'VOID') && (
                          <span className="text-slate-300 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader title="收款" subtitle="PLANNED → CONFIRMED → RECEIVED" />
          <div className="card-body">
            {collections.length === 0 ? (
              <EmptyState message="暂无收款记录" />
            ) : (
              <table className="data-table text-xs">
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
                      <td>{c.receipt_date || '—'}</td>
                      <td className="num">{formatMoney(c.amount_received)}</td>
                      <td>{collectionStatusBadge(c.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader title="差异" subtitle="已开票 - 已收款（RECEIVED）" />
        <div className="card-body">
          <table className="data-table text-sm">
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
                <td>已收款金额（RECEIVED）</td>
                <td className="num">{formatMoney(totalCollected)}</td>
              </tr>
              <tr>
                <td className="font-semibold">差异(应收 - 已收)</td>
                <td className={`num font-semibold ${variance > 0 ? '' : ''}`} style={{ color: variance > 0 ? AMBER : GREEN }}>
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
